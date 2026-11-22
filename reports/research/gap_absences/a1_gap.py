"""A1: how much of each big 2026 gap could absences account for, and the IND @ HOU breakdown. No fitting, no game results.

For every 2026 locked pick whose stats-only line was >= 3 points from its line (the site's "Big gap"), at the LOCK and
at the FINAL pre-game version, per team:
  (1) the shadow line's injury inputs (frozen rule) and their margin effect at the frozen per-unit costs;
  (2) the same rows with P(play) taken from the descriptive 2021-25 table by final status x recent snap-share band
      (a1_penalty.json) instead of status alone: an ILLUSTRATION of the B8 correction, not a fitted model;
  (3) regulars missing from every input: players on reserve lists and players who left the team (trade, release),
      from the same weekly-roster logic as the site (predict/reserve_list.py, predict/roster_moves.py) with the roster
      and snap files as of the lock. Each is counted by his weight in the team's current rating: the team-form weight
      (half-life 8 games, season carry 0.6, last 48 games; features/asof.py) on the games he played times his snap
      share there, i.e. the part of the team's rating that still contains him. Priced at the frozen unit costs
      (ILLUSTRATION: those costs were fitted on injury-report absences, not on these).
"Toward the gap" = the effect moves the stats-only line further from the market line (positive) or back toward it.
Writes a1_gap.json, a1_gap_teams.parquet and a1_ind_hou.json (player-level detail for 2026_11_IND_HOU).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from common import (OUT, SEASON, UNITS, final_pregame, injury_snapshots, live_player_losses, locked_games,  # noqa: E402
                    margin_points, save, shadow_unit_points, slot, snapshot_at)
from nflcast.config import PROCESSED_DIR, settings  # noqa: E402
from nflcast.data import sources as S  # noqa: E402
from nflcast.features import personnel as P  # noqa: E402
from nflcast.predict import reserve_list as RL, roster_moves as RM  # noqa: E402

CASE = "2026_11_IND_HOU"
last_snap = injury_snapshots()[-1]["observed_at"]
G = (locked_games().filter((pl.col("kickoff_utc") < last_snap) & ~pl.col("provisional") & pl.col("stats_margin").is_not_null())
     .with_columns(gap=pl.col("stats_margin") + pl.col("line_home_spread")))
BIG = G.filter(pl.col("gap").abs() >= 3).sort("kickoff_utc")

# ---- descriptive participation table (status x band), 2021-25
pen = json.loads((OUT / "a1_penalty.json").read_text(encoding="utf-8"))
P_SB = {(r["status"], r["band"]): r["played"] for r in pen["participation_status_band_2021_25"]}


def band(x: float) -> str:
    return "a <0.2" if x < 0.2 else "b 0.2-0.5" if x < 0.5 else "c 0.5-0.8" if x < 0.8 else "d 0.8+"


def b8_lost(df: pl.DataFrame) -> pl.DataFrame:
    p = [1.0 - P_SB.get((s, band(r)), 1.0 - pm) for s, r, pm in zip(df["status"], df["recent_share"], df["p_miss"])]
    return df.with_columns(lost_b8=pl.Series(p, dtype=pl.Float64) * pl.col("recent_share"))


# ---- team-form weight of each player (rating share)
games_all = pl.read_parquet(PROCESSED_DIR / "games.parquet")
TG = (pl.read_parquet(PROCESSED_DIR / "team_games.parquet").select("game_id", "team", "kickoff_utc")
      .join(games_all.select("game_id", "season"), on="game_id").sort("kickoff_utc"))
HL = float(settings()["features"]["half_life_games"])
CARRY = float(settings()["features"]["season_carryover"])
SN = P.snap_shares([SEASON - 2, SEASON - 1, SEASON], games_all)
p2g = S.fetch("players").select(pl.col("pfr_id").alias("pfr_player_id"), "gsis_id").drop_nulls().unique("gsis_id")
SN = SN.join(p2g, on="pfr_player_id", how="left")


def rating_share(team: str, gsis: str, kickoff, max_games: int = 48) -> float:
    """Team-form-weighted snap share of a player over the team's games before kickoff (zeros where he did not play)."""
    tg = TG.filter((pl.col("team") == team) & (pl.col("kickoff_utc") < kickoff)).tail(max_games)
    if tg.height == 0:
        return 0.0
    k = np.arange(tg.height)[::-1]
    w = 0.5 ** (k / HL) * CARRY ** np.clip(SEASON - tg["season"].to_numpy(), 0, None)
    me = SN.filter((pl.col("team") == team) & (pl.col("gsis_id") == gsis)).select("game_id", "share")
    sh = tg.select("game_id").join(me, on="game_id", how="left")["share"].fill_null(0.0).to_numpy()
    return float((w * sh).sum() / w.sum())


# ---- roster-based regulars (reserve lists, departures) as of a time
_rt: dict = {}


def roster_tables(t):
    ros, rm = S.snapshot_asof("rosters_weekly", SEASON, t)
    sn, _ = S.snapshot_asof("snap_counts", SEASON, t)
    key = (rm or {}).get("content_sha256")
    if key not in _rt:
        pls = S.fetch("players")
        _rt[key] = (RL.prepare(ros, sn, pls, SEASON, S.fetch("snap_counts", SEASON - 1)), RM.prepare(ros, sn, pls, SEASON))
    return _rt[key]


def unit_of(pos: str | None) -> str | None:
    return P.UNIT_OF_POSITION.get(pos or "", None)


def missing_regulars(team: str, week: int, t, kickoff) -> list[dict]:
    rl, rm = roster_tables(t)
    out = []
    for x in RL.team_list(rl, team, week)["players"]:
        u = unit_of(x["pos"])
        if u is None or x.get("specialist"):
            continue
        gid = rl["r"].filter((pl.col("team") == team) & (pl.col("full_name") == x["player"]))["gsis_id"]
        gid = gid[0] if gid.len() else None
        out.append({"player": x["player"], "pos": x["pos"], "unit": u, "kind": x["list"], "since_week": x["since_week"],
                    "season_share": (x["this_season"] or {}).get("share"),
                    "rating_share": rating_share(team, gid, kickoff) if gid else None})
    for d in RM.team_moves(rm, team, week)["departures"]:
        u = unit_of(d["pos"])
        if u is None or not (d["move"].startswith("Now with") or d["move"] == "Released"):
            continue
        gid = rm["s"].filter((pl.col("team") == team) & (pl.col("player") == d["player"]))["gsis_id"].drop_nulls()
        gid = gid[0] if gid.len() else None
        out.append({"player": d["player"], "pos": d["pos"], "unit": u, "kind": d["move"], "since_week": d["last_active_week"],
                    "season_share": d["share"], "rating_share": rating_share(team, gid, kickoff) if gid else None})
    return out


def team_block(L: pl.DataFrame, game_id: str, team: str) -> dict:
    d = L.filter((pl.col("game_id") == game_id) & (pl.col("team") == team))
    u = {x: float(d.filter(pl.col("unit") == x)["lost"].sum()) for x in UNITS}
    ub = {x: float(d.filter(pl.col("unit") == x)["lost_b8"].sum()) for x in UNITS}
    return {"units": u, "points": margin_points(u), "units_b8": ub, "points_b8": margin_points(ub)}


_L: dict = {}


def losses_at(snap, week, rows):
    k = (snap["sha"], str(snap["path"]), week, tuple(r["game_id"] for r in rows))
    if k not in _L:
        _L[k] = b8_lost(live_player_losses(snap, week, rows))
    return _L[k]


cost = shadow_unit_points()
team_rows, game_rows = [], []
case = {}
for g in BIG.iter_rows(named=True):
    rows = [{"game_id": g["game_id"], "home": g["home"], "away": g["away"], "kickoff_utc": g["kickoff_utc"]}]
    fp = final_pregame(g["game_id"], g["kickoff_utc"])
    snaps_before = [s for s in injury_snapshots() if s["observed_at"] < g["kickoff_utc"]]
    ver = {"lock": (g["lock_at"], snapshot_at(g["lock_at"])), "final": (fp["generated_at"] if fp else None, snapshot_at(fp["generated_at"]) if fp else None)}
    eff = {}
    for which, (t, snap) in ver.items():
        if snap is None:
            continue
        L = losses_at(snap, g["week"], rows)
        for side, team in (("home", g["home"]), ("away", g["away"])):
            b = team_block(L, g["game_id"], team)
            miss = missing_regulars(team, g["week"], t, g["kickoff_utc"])
            mu = {x: sum((m["rating_share"] or 0.0) for m in miss if m["unit"] == x) for x in UNITS}
            rec = {"game_id": g["game_id"], "which": which, "side": side, "team": team, "slot": slot(g["kickoff_utc"]),
                   "gap": g["gap"], **{f"inj_{x}": b["units"][x] for x in UNITS}, "inj_points": b["points"],
                   **{f"b8_{x}": b["units_b8"][x] for x in UNITS}, "b8_points": b["points_b8"],
                   **{f"roster_{x}": mu[x] for x in UNITS}, "roster_points": margin_points(mu),
                   "roster_players": len(miss)}
            team_rows.append(rec)
            if g["game_id"] == CASE:
                det = L.filter((pl.col("game_id") == g["game_id"]) & (pl.col("team") == team)).sort("lost", descending=True)
                case.setdefault(which, {})[team] = {
                    "snapshot_observed": snap["observed_at"], "provider_last_modified": snap["last_modified"],
                    "units": b["units"], "points_by_unit": {x: cost[x] * b["units"][x] for x in UNITS},
                    "points": b["points"], "units_b8": b["units_b8"], "points_b8": b["points_b8"],
                    "players": det.select("full_name", "position", "unit", "status", "practice_status", "recent_share",
                                          "p_miss", "lost", "lost_b8").to_dicts(),
                    "missing_regulars": miss, "missing_points": margin_points(mu)}
T = pl.DataFrame(team_rows, infer_schema_length=None)
T.write_parquet(OUT / "a1_gap_teams.parquet")

# game level: home-margin effects, then signed toward the gap (gap > 0: stats-only line above the market for home)
sgn = lambda c: pl.when(pl.col("side") == "home").then(pl.col(c)).otherwise(-pl.col(c))
Gm = (T.group_by("game_id", "which", "slot").agg(gap=pl.col("gap").first(), inj=sgn("inj_points").sum(),
                                                 b8=sgn("b8_points").sum(), roster=sgn("roster_points").sum())
      .with_columns(inj_toward=pl.col("inj") * pl.col("gap").sign(), b8_toward=pl.col("b8") * pl.col("gap").sign(),
                    roster_toward=pl.col("roster") * pl.col("gap").sign()).sort("game_id", "which"))


def summ(d):
    return {"n": d.height, "mean_abs_gap": float(d["gap"].abs().mean()),
            **{f"mean_{c}_toward": float(d[f"{c}_toward"].mean()) for c in ("inj", "b8", "roster")},
            **{f"mean_abs_{c}": float(d[c].abs().mean()) for c in ("inj", "b8", "roster")},
            "share_inj_toward_gap": float((d["inj_toward"] > 0).mean()),
            "share_roster_toward_gap": float((d["roster_toward"] > 0).mean()),
            "mean_all_three_toward": float((d["b8_toward"] + d["roster_toward"]).mean()),
            "games_where_b8_plus_roster_reverse_gap": int(((d["b8_toward"] + d["roster_toward"]) <= -d["gap"].abs()).sum()),
            "games_where_b8_plus_roster_halve_gap": int(((d["b8_toward"] + d["roster_toward"]) <= -0.5 * d["gap"].abs()).sum())}


res = {"n_big_gap_games": BIG.height, "big_gap_by_rule": BIG.group_by("rule").len().to_dicts(),
       "lock": summ(Gm.filter(pl.col("which") == "lock")), "final": summ(Gm.filter(pl.col("which") == "final")),
       "games": Gm.to_dicts(), "costs_per_starter_equivalent": {x: cost[x] for x in UNITS}}
save("a1_gap", res)
(OUT / "a1_ind_hou.json").write_text(json.dumps(case, indent=1, default=str), encoding="utf-8")
print("big-gap games", BIG.height)
for k in ("lock", "final"):
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in res[k].items()})
for which, teams in case.items():
    for t, b in teams.items():
        print(which, t, "inj units", {k: round(v, 2) for k, v in b["units"].items()}, "pts", round(b["points"], 2),
              "| B8", round(b["points_b8"], 2), "| roster", round(b["missing_points"], 2), [(m["player"], m["kind"], m["unit"], m["rating_share"] and round(m["rating_share"], 2)) for m in b["missing_regulars"]])
