"""Deserved margin: what each team's plays usually produce, compared with the scoreboard (display and analysis only).

User request 2026-11-10; method fixed before any week-10 game (reports/research/deserved_margin_spec_2026-11-10.md,
configs/deserved.yaml). It never changes a forecast, the pick, the pick rule or any grade, and finished games are never
regraded with it. Method follows dgrifka/nfl_simulator (MIT), refit on this project's data.

Per team and game, from nflverse play-by-play: pass and run plays with EPA (no two-point tries). Success rate counts the
team's takeaways (interceptions and lost fumbles by its defence) as extra plays, successful when the offence lost
expected points; yards per play credits the takeaway return yards but does not add plays. The deserved home margin is
a fixed linear combination of the two differences. Against the locked line, the official Model pick's side was ahead,
behind, or close (within the close band) on play quality, which with the scoreboard result gives the group.
"""

from __future__ import annotations

from functools import lru_cache

import polars as pl
import yaml

from nflcast.config import ROOT

PBP_COLS = ["game_id", "posteam", "defteam", "play_type", "epa", "yards_gained", "interception", "fumble_lost",
            "return_yards", "fumble_recovery_1_yards", "two_point_attempt"]
GROUPS = ("right_deserved", "right_fortunate", "wrong_unlucky", "wrong_deserved", "close", "level")


@lru_cache(maxsize=1)
def config() -> dict:
    return yaml.safe_load((ROOT / "configs" / "deserved.yaml").read_text(encoding="utf-8"))


def team_quality(pbp: pl.DataFrame) -> dict[tuple[str, str], dict]:
    """{(game_id, team): {plays, success_rate, yards_per_play, takeaways}} for every team-game in the play-by-play."""
    p = pbp.filter(pl.col("play_type").is_in(["pass", "run"]) & pl.col("epa").is_not_null()
                   & (pl.col("two_point_attempt").fill_null(0) == 0) & pl.col("posteam").is_not_null())
    p = p.with_columns(take=(pl.col("interception").fill_null(0) == 1) | (pl.col("fumble_lost").fill_null(0) == 1))
    own = p.group_by(["game_id", "posteam"]).agg(N=pl.len(), K=(pl.col("epa") > 0).sum(),
                                                 Y=pl.col("yards_gained").fill_null(0).sum())
    ret = (pl.when(pl.col("interception").fill_null(0) == 1).then(pl.col("return_yards").fill_null(0))
           .otherwise(pl.col("fumble_recovery_1_yards").fill_null(0)))
    tk = (p.filter(pl.col("take")).group_by(["game_id", "defteam"])
          .agg(T=pl.len(), Ts=(pl.col("epa") < 0).sum(), R=ret.sum()).rename({"defteam": "posteam"}))
    t = own.join(tk, on=["game_id", "posteam"], how="left").fill_null(0)
    out = {}
    for r in t.iter_rows(named=True):
        out[(r["game_id"], r["posteam"])] = {
            "plays": int(r["N"]), "takeaways": int(r["T"]),
            "success_rate": (r["K"] + r["Ts"]) / (r["N"] + r["T"]),
            "yards_per_play": (r["Y"] + r["R"]) / r["N"]}
    return out


def deserved_margin(home: dict, away: dict) -> float:
    w = config()["weights"]
    return (w["success_rate"] * (home["success_rate"] - away["success_rate"])
            + w["yards_per_play"] * (home["yards_per_play"] - away["yards_per_play"]))


def group_for(result: str, quality: str) -> str:
    """result: the official grade (win/loss/push); quality: ahead/behind/close."""
    if result == "push":
        return "level"
    if quality == "close":
        return "close"
    return {("win", "ahead"): "right_deserved", ("win", "behind"): "right_fortunate",
            ("loss", "ahead"): "wrong_unlucky", ("loss", "behind"): "wrong_deserved"}[(result, quality)]


def game_deserved(quality: dict, game_id: str, home: str, away: str, locked_pick: dict | None,
                  result_grade: dict | None) -> dict | None:
    """Deserved margin for a finished game, and where the official Model pick's side was on play quality."""
    h, a = quality.get((game_id, home)), quality.get((game_id, away))
    if not h or not a or not h["plays"] or not a["plays"]:
        return None
    dm = deserved_margin(h, a)
    out = {"home": h, "away": a, "margin": dm, "pick": None}
    lean = (locked_pick or {}).get("lean") or {}
    line, side, res = (locked_pick or {}).get("line_home_spread"), lean.get("side"), (result_grade or {}).get("lean")
    if line is not None and side in (home, away) and res in ("win", "loss", "push"):
        edge = (1 if side == home else -1) * (dm + line)          # > 0: the picked side was ahead of the line on play quality
        q = "close" if abs(edge) < config()["close_band"] else ("ahead" if edge > 0 else "behind")
        out["pick"] = {"side": side, "line_home_spread": line, "edge": edge, "quality": q, "result": res,
                       "group": group_for(res, q), "publicly_verifiable": locked_pick.get("verification") == "publicly_verifiable_pregame"}
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
                      "edge": pk["edge"], "group": pk["group"]})
    return {"counts": counts, "n": sum(counts.values()),
            "by_week": [{"week": w, **c} for w, c in sorted(by_week.items())],
            "games": sorted(games, key=lambda g: (-g["week"], g["game_id"])),
            "close_band": config()["close_band"], "credit": config()["credit"]}
