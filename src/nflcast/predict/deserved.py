"""Deserved margin: what each team's plays usually produce, compared with the scoreboard (display and analysis only).

User request 2026-11-10; method fixed before any week-10 game (reports/research/deserved_margin_spec_2026-11-10.md,
configs/deserved.yaml). It never changes a forecast, the pick, the pick rule or any grade, and finished games are never
regraded with it. Method follows dgrifka/nfl_simulator (MIT), refit on this project's data.

Per team and game, from nflverse play-by-play: pass and run plays with EPA (no two-point tries). Success rate counts the
team's takeaways (interceptions and lost fumbles by its defence) as extra plays, successful when the offence lost
expected points; yards per play credits the takeaway return yards but does not add plays. The deserved home margin is
a fixed linear combination of the two differences. Against the locked line, the official Model pick's side was ahead,
behind, or close (within the close band) on play quality, which with the scoreboard result gives the group.

Addendum (same spec, written before any week-10 game): the chance on play quality (play re-sampling, fixed seed per
game) and a descriptive "what made the difference" ledger (no weights).
"""

from __future__ import annotations

import hashlib
from functools import lru_cache

import numpy as np
import polars as pl
import yaml

from nflcast.config import ROOT

PBP_COLS = ["game_id", "posteam", "defteam", "play_type", "epa", "yards_gained", "interception", "fumble_lost",
            "return_yards", "fumble_recovery_1_yards", "two_point_attempt"]
LEDGER_COLS = PBP_COLS + ["special_teams_play", "field_goal_attempt", "field_goal_result", "penalty", "penalty_team",
                          "penalty_yards", "fixed_drive", "fixed_drive_result", "drive_inside20", "yardline_100",
                          "fourth_down_converted", "fourth_down_failed"]
GROUPS = ("right_deserved", "right_fortunate", "wrong_unlucky", "wrong_deserved", "close", "level")
DRAWS = 2000
SCRIMMAGE = ["pass", "run", "punt", "field_goal", "qb_kneel", "qb_spike", "no_play"]


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load((ROOT / "configs" / "deserved.yaml").read_text(encoding="utf-8"))


def _offence(pbp: pl.DataFrame) -> pl.DataFrame:
    """The plays the deserved margin reads, with each play's contribution columns."""
    p = pbp.filter(pl.col("play_type").is_in(["pass", "run"]) & pl.col("epa").is_not_null()
                   & (pl.col("two_point_attempt").fill_null(0) == 0) & pl.col("posteam").is_not_null())
    take = (pl.col("interception").fill_null(0) == 1) | (pl.col("fumble_lost").fill_null(0) == 1)
    ret = (pl.when(pl.col("interception").fill_null(0) == 1).then(pl.col("return_yards").fill_null(0))
           .otherwise(pl.col("fumble_recovery_1_yards").fill_null(0)))
    return p.select("game_id", "posteam", "defteam",
                    s=(pl.col("epa") > 0).cast(pl.Float64), y=pl.col("yards_gained").fill_null(0).cast(pl.Float64),
                    tk=take.cast(pl.Float64), ts=(take & (pl.col("epa") < 0)).cast(pl.Float64),
                    r=pl.when(take).then(ret).otherwise(0).cast(pl.Float64))


def team_quality(pbp: pl.DataFrame) -> dict[tuple[str, str], dict]:
    """{(game_id, team): {plays, success_rate, yards_per_play, takeaways, _draw}} for every team-game.
    `_draw` holds the team's own plays (for the re-sampling chance); it is never exported."""
    o = _offence(pbp)
    rows: dict[tuple[str, str], np.ndarray] = {}
    for (gid, team), g in o.group_by(["game_id", "posteam"]):
        rows[(gid, team)] = g.select("s", "y", "tk", "ts", "r").to_numpy()
    out = {}
    for (gid, team), own in rows.items():
        opp = next((v for (g2, t2), v in rows.items() if g2 == gid and t2 != team), np.zeros((0, 5)))
        n, t = len(own), opp[:, 2].sum()
        out[(gid, team)] = {"plays": int(n), "takeaways": int(t),
                            "success_rate": (own[:, 0].sum() + opp[:, 3].sum()) / (n + t),
                            "yards_per_play": (own[:, 1].sum() + opp[:, 4].sum()) / n,
                            "_draw": own}
    return out


def deserved_margin(home: dict, away: dict) -> float:
    w = config()["weights"]
    return (w["success_rate"] * (home["success_rate"] - away["success_rate"])
            + w["yards_per_play"] * (home["yards_per_play"] - away["yards_per_play"]))


def _seed(game_id: str) -> int:
    return int.from_bytes(hashlib.sha256(game_id.encode("utf-8")).digest()[:8], "big")


def resampled_margins(game_id: str, home_plays: np.ndarray, away_plays: np.ndarray, draws: int = DRAWS) -> np.ndarray:
    """Deserved home margin in each re-sample of both teams' own plays (columns s, y, tk, ts, r)."""
    rng = np.random.default_rng(_seed(game_id))
    w = config()["weights"]
    nh, na = len(home_plays), len(away_plays)
    h = home_plays[rng.integers(0, nh, size=(draws, nh))].sum(axis=1)       # (draws, 5) column sums
    a = away_plays[rng.integers(0, na, size=(draws, na))].sum(axis=1)
    h_rate = (h[:, 0] + a[:, 3]) / (nh + a[:, 2])
    a_rate = (a[:, 0] + h[:, 3]) / (na + h[:, 2])
    h_ypp = (h[:, 1] + a[:, 4]) / nh
    a_ypp = (a[:, 1] + h[:, 4]) / na
    return w["success_rate"] * (h_rate - a_rate) + w["yards_per_play"] * (h_ypp - a_ypp)


def team_ledger(pbp: pl.DataFrame) -> dict[tuple[str, str], dict]:
    """Descriptive per team-game numbers the deserved margin leaves out (no weights): giveaways, kicking, red zone,
    penalties, field position, 4th downs, explosive plays, special teams expected points."""
    p = pbp.filter(pl.col("posteam").is_not_null())
    out: dict[tuple[str, str], dict] = {}
    pairs = p.select("game_id", "posteam").unique().iter_rows()
    for gid, team in pairs:
        g = pbp.filter(pl.col("game_id") == gid)       # all rows: some penalties and kicks have no possession team
        own = g.filter(pl.col("posteam") == team)
        off = own.filter(pl.col("play_type").is_in(["pass", "run"]) & (pl.col("two_point_attempt").fill_null(0) == 0))
        fg = own.filter(pl.col("field_goal_attempt").fill_null(0) == 1)
        drives = (own.filter(pl.col("fixed_drive").is_not_null() & pl.col("play_type").is_in(SCRIMMAGE))
                  .group_by("fixed_drive").agg(start=pl.col("yardline_100").drop_nulls().first(),
                                               inside20=pl.col("drive_inside20").max(),
                                               result=pl.col("fixed_drive_result").first()))
        rz = drives.filter(pl.col("inside20").fill_null(0) == 1)
        # nflverse marks the enforced penalty on each play (a declined one is only mentioned in the description)
        pen = g.filter((pl.col("penalty").fill_null(0) == 1) & (pl.col("penalty_team") == team))
        st = g.filter(pl.col("special_teams_play").fill_null(0) == 1)
        st_net = (st.filter(pl.col("posteam") == team)["epa"].fill_null(0).sum()
                  - st.filter(pl.col("defteam") == team)["epa"].fill_null(0).sum())
        starts = drives["start"].drop_nulls()
        out[(gid, team)] = {
            "interceptions": int(off["interception"].fill_null(0).sum()),
            "fumbles_lost": int(off["fumble_lost"].fill_null(0).sum()),
            "fg_made": int((fg["field_goal_result"] == "made").sum()), "fg_att": fg.height,
            "rz_td": int((rz["result"] == "Touchdown").sum()), "rz_trips": rz.height,
            "penalties": pen.height, "penalty_yards": int(pen["penalty_yards"].fill_null(0).sum()),
            "avg_start": float(100 - starts.mean()) if len(starts) else None,
            "fourth_conv": int(own["fourth_down_converted"].fill_null(0).sum()),
            "fourth_att": int(own["fourth_down_converted"].fill_null(0).sum() + own["fourth_down_failed"].fill_null(0).sum()),
            "explosive": int(off.filter(((pl.col("play_type") == "pass") & (pl.col("yards_gained") >= 20))
                                        | ((pl.col("play_type") == "run") & (pl.col("yards_gained") >= 10))).height),
            "st_epa": float(st_net),
        }
    return out


def group_for(result: str, quality: str) -> str:
    """result: the official grade (win/loss/push); quality: ahead/behind/close."""
    if result == "push":
        return "level"
    if quality == "close":
        return "close"
    return {("win", "ahead"): "right_deserved", ("win", "behind"): "right_fortunate",
            ("loss", "ahead"): "wrong_unlucky", ("loss", "behind"): "wrong_deserved"}[(result, quality)]


def _public(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


def game_deserved(quality: dict, game_id: str, home: str, away: str, locked_pick: dict | None,
                  result_grade: dict | None, ledger: dict | None = None) -> dict | None:
    """Deserved margin for a finished game, where the official Model pick's side was on play quality, the chance on
    play quality (re-sampling) and the descriptive ledger."""
    h, a = quality.get((game_id, home)), quality.get((game_id, away))
    if not h or not a or not h["plays"] or not a["plays"]:
        return None
    dm = deserved_margin(h, a)
    led = None
    if ledger is not None and (game_id, home) in ledger and (game_id, away) in ledger:
        led = {"home": ledger[(game_id, home)], "away": ledger[(game_id, away)]}
    out = {"home": _public(h), "away": _public(a), "margin": dm, "pick": None, "ledger": led}
    lean = (locked_pick or {}).get("lean") or {}
    line, side, res = (locked_pick or {}).get("line_home_spread"), lean.get("side"), (result_grade or {}).get("lean")
    if line is not None and side in (home, away) and res in ("win", "loss", "push"):
        sgn = 1 if side == home else -1
        edge = sgn * (dm + line)                                  # > 0: the picked side was ahead of the line on play quality
        q = "close" if abs(edge) < config()["close_band"] else ("ahead" if edge > 0 else "behind")
        chance = None
        if "_draw" in h and "_draw" in a:
            chance = float((sgn * (resampled_margins(game_id, h["_draw"], a["_draw"]) + line) > 0).mean())
        out["pick"] = {"side": side, "line_home_spread": line, "edge": edge, "quality": q, "result": res,
                       "group": group_for(res, q), "chance": chance,
                       "publicly_verifiable": locked_pick.get("verification") == "publicly_verifiable_pregame"}
    return out


def summary(items: list[dict]) -> dict:
    """Season counts for the official Model pick (publicly verifiable locked versions only, like the official record)."""
    counts = {g: 0 for g in GROUPS}
    by_week: dict[int, dict] = {}
    games = []
    for it in items:
        d = it.get("deserved") or {}
        pk = d.get("pick")
        if not pk or not pk["publicly_verifiable"]:
            continue
        counts[pk["group"]] += 1
        by_week.setdefault(it["week"], {g: 0 for g in GROUPS})[pk["group"]] += 1
        games.append({"game_id": it["game_id"], "week": it["week"], "home": it["home"], "away": it["away"],
                      "side": pk["side"], "line_home_spread": pk["line_home_spread"], "result": pk["result"],
                      "actual_margin": it["score"]["home"] - it["score"]["away"], "deserved_margin": d["margin"],
                      "edge": pk["edge"], "chance": pk.get("chance"), "group": pk["group"]})
    return {"counts": counts, "n": sum(counts.values()),
            "by_week": [{"week": w, **c} for w, c in sorted(by_week.items())],
            "games": sorted(games, key=lambda g: (-g["week"], g["game_id"])),
            "close_band": config()["close_band"], "credit": config()["credit"]}
