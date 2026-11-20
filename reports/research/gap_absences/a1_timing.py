"""A1 timing: was each team's final injury information in our data when its 2026 pick locked? (no fitting, no outcomes)

For every 2026 game with a locked pick that kicked off before the last archived injury snapshot:
  * the injury snapshot in use at the lock (newest observed at or before the lock version's generation time; checked
    against the release's recorded content sha256) and the last snapshot before kickoff ("final");
  * per team: game designations (Out/Doubtful/Questionable) at the lock and at the final; whether the final rows (all
    rows incl. practice status, and designations only) were already present at the lock; when they first appeared in
    our data and the provider's Last-Modified time of that file;
  * the shadow line's injury inputs (expected lost snaps by unit; predict/shadow.live_losses rule, frozen P(play)) at
    the lock and at the final, player-matched, and their margin effect at the frozen shadow costs. From week 7 the
    recomputed lock inputs are checked against the inputs stored in the lock release.
Writes a1_timing.parquet (team rows) and a1_timing.json (summaries).
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from common import (OUT, UNITS, first_seen_final, injury_snapshots, key_rows, live_player_losses, locked_games,  # noqa: E402
                    margin_points, release, save, slot, snapshot_at, team_rows, final_pregame, GAME_STATUSES)

last_snap = injury_snapshots()[-1]["observed_at"]
G = locked_games().filter((pl.col("kickoff_utc") < last_snap) & ~pl.col("provisional")).sort("kickoff_utc")

# ---- per-player losses, cached per (snapshot, week): every game of that week at once
_cache: dict = {}


def losses(snap: dict, week: int) -> pl.DataFrame:
    k = (snap["sha"], str(snap["path"]), week)
    if k not in _cache:
        rows = G.filter(pl.col("week") == week).select("game_id", "home", "away", "kickoff_utc").to_dicts()
        _cache[k] = live_player_losses(snap, week, rows)
    return _cache[k]


def units(df: pl.DataFrame, game_id: str, team: str) -> dict:
    d = df.filter((pl.col("game_id") == game_id) & (pl.col("team") == team))
    return {u: float(d.filter(pl.col("unit") == u)["lost"].sum()) for u in UNITS}


def by_status(df: pl.DataFrame, game_id: str, team: str) -> dict:
    d = df.filter((pl.col("game_id") == game_id) & (pl.col("team") == team))
    tot = float(d["lost"].sum())
    return {s: float(d.filter(pl.col("status") == s)["lost"].sum()) for s in ("None", "Questionable", "Doubtful", "Out")} | {"total": tot}


rows, checks = [], []
for g in G.iter_rows(named=True):
    ko, wk = g["kickoff_utc"], g["week"]
    lock_snap = snapshot_at(g["lock_at"])
    fin_snaps = [s for s in injury_snapshots() if s["observed_at"] < ko]
    fin_snap = fin_snaps[-1] if fin_snaps else None
    rel = release(g["lock_run_id"])
    sha_ok = bool(rel["inj"]) and lock_snap is not None and rel["inj"].get("content_sha256") == lock_snap["sha"]
    Ll = losses(lock_snap, wk) if lock_snap else pl.DataFrame()
    Lf = losses(fin_snap, wk) if fin_snap else pl.DataFrame()
    fp = final_pregame(g["game_id"], ko)
    for side, team, opp in (("home", g["home"], g["away"]), ("away", g["away"], g["home"])):
        rl, rf = team_rows(lock_snap, team, wk), team_rows(fin_snap, team, wk)
        full_final = first_seen_final(team, wk, ko, designated_only=False)
        des_final = first_seen_final(team, wk, ko, designated_only=True)
        ul, uf = units(Ll, g["game_id"], team), units(Lf, g["game_id"], team)
        # player-matched: expected lost snaps present at the lock = min(lock, final) per player
        pl_l = Ll.filter((pl.col("game_id") == g["game_id"]) & (pl.col("team") == team)).select("gsis_id", lost_l="lost")
        pl_f = Lf.filter((pl.col("game_id") == g["game_id"]) & (pl.col("team") == team)).select("gsis_id", lost_f="lost")
        mm = pl_l.join(pl_f, on="gsis_id", how="full", coalesce=True).fill_null(0.0)
        present = float(np.minimum(mm["lost_l"], mm["lost_f"]).sum()) if mm.height else 0.0
        over = float(np.maximum(mm["lost_l"] - mm["lost_f"], 0).sum()) if mm.height else 0.0
        row = {"game_id": g["game_id"], "week": wk, "slot": slot(ko), "kickoff_utc": ko, "rule": g["rule"],
               "lock_at": g["lock_at"], "hours_lock_before_kickoff": (ko - g["lock_at"]).total_seconds() / 3600,
               "side": side, "team": team, "opp": opp, "lock_snapshot_matches_release": sha_ok,
               "lock_snapshot_observed": lock_snap["observed_at"] if lock_snap else None,
               "lock_snapshot_last_modified": lock_snap["last_modified"] if lock_snap else None,
               "n_designated_lock": len(key_rows(rl, True)), "n_designated_final": len(key_rows(rf, True)),
               "n_rows_lock": rl.height, "n_rows_final": rf.height,
               "final_rows_at_lock": key_rows(rl) == key_rows(rf),
               "final_designations_at_lock": key_rows(rl, True) == key_rows(rf, True),
               "final_rows_first_seen": full_final["first_seen"], "final_rows_provider_lm": full_final.get("provider_last_modified"),
               "designations_first_seen": des_final["first_seen"], "designations_provider_lm": des_final.get("provider_last_modified"),
               **{f"lock_{u}": v for u, v in ul.items()}, **{f"final_{u}": v for u, v in uf.items()},
               "lock_total": sum(ul.values()), "final_total": sum(uf.values()), "present_matched": present,
               "overstated_at_lock": over, "lock_points": margin_points(ul), "final_points": margin_points(uf),
               **{f"lock_from_{k}": v for k, v in by_status(Ll, g["game_id"], team).items()},
               **{f"final_from_{k}": v for k, v in by_status(Lf, g["game_id"], team).items()},
               "stats_margin_home": g["stats_margin"], "stats_inj_margin_home": g["stats_inj_margin"],
               "line_home_spread": g["line_home_spread"], "final_pregame_run": fp["run_id"] if fp else None}
        rows.append(row)
        # check recomputation against stored inputs (week 7+ releases store injury_inputs)
        for tag, run, u in (("lock", g["lock_run_id"], ul), ("final", fp["run_id"] if fp else None, uf)):
            if run is None:
                continue
            ii = (release(run)["games"].get(g["game_id"]) or {}).get("injury_inputs")
            if ii:
                checks.append({"game_id": g["game_id"], "team": team, "which": tag,
                               "max_abs_diff": max(abs(ii[side][f"lost_{k}"] - u[k]) for k in UNITS)})

T = pl.DataFrame(rows, infer_schema_length=None)
T.write_parquet(OUT / "a1_timing.parquet")
C = pl.DataFrame(checks, infer_schema_length=None)

# ---- summaries
T = T.with_columns(hours_final_rows_before_ko=(pl.col("kickoff_utc") - pl.col("final_rows_first_seen")).dt.total_seconds() / 3600,
                   hours_desig_before_ko=(pl.col("kickoff_utc") - pl.col("designations_first_seen")).dt.total_seconds() / 3600,
                   share_present=pl.when(pl.col("final_total") > 0).then(pl.col("present_matched") / pl.col("final_total")),
                   points_change=pl.col("final_points") - pl.col("lock_points"))


def summ(d: pl.DataFrame) -> dict:
    return {"team_games": d.height, "games": d["game_id"].n_unique(),
            "final_rows_at_lock": int(d["final_rows_at_lock"].sum()),
            "final_designations_at_lock": int(d["final_designations_at_lock"].sum()),
            "designations_at_lock_when_final_has_some": int(d.filter(pl.col("n_designated_final") > 0)["final_designations_at_lock"].sum()),
            "teams_with_final_designations": int((d["n_designated_final"] > 0).sum()),
            "median_hours_lock_before_ko": float(d["hours_lock_before_kickoff"].median()),
            "median_hours_designations_first_seen_before_ko": float(d["hours_desig_before_ko"].median()) if d["hours_desig_before_ko"].drop_nulls().len() else None,
            "median_hours_final_rows_first_seen_before_ko": float(d["hours_final_rows_before_ko"].median()),
            "share_of_final_inputs_present_at_lock": float(d["present_matched"].sum() / d["final_total"].sum()) if d["final_total"].sum() else None,
            "overstated_at_lock_total": float(d["overstated_at_lock"].sum()),
            "lock_total": float(d["lock_total"].sum()), "final_total": float(d["final_total"].sum()),
            "mean_abs_points_change_team": float(d["points_change"].abs().mean()),
            "max_abs_points_change_team": float(d["points_change"].abs().max())}


res = {"last_injury_snapshot": last_snap, "n_games": G.height,
       "lock_snapshot_matches_release_sha": int(T["lock_snapshot_matches_release"].sum()), "n_team_rows": T.height,
       "recompute_check": {"n": C.height, "max_abs_diff_lock": float(C.filter(pl.col("which") == "lock")["max_abs_diff"].max()) if C.height else None,
                           "max_abs_diff_final": float(C.filter(pl.col("which") == "final")["max_abs_diff"].max()) if C.height else None,
                           "n_over_0.001": int((C["max_abs_diff"] > 1e-3).sum()) if C.height else None,
                           "worst": C.sort("max_abs_diff", descending=True).head(8).to_dicts() if C.height else []},
       "by_rule": {r: summ(T.filter(pl.col("rule") == r)) for r in T["rule"].unique().sort().to_list()},
       "lock24_by_slot": {s: summ(T.filter((pl.col("rule") == "lock-24h") & (pl.col("slot") == s))) for s in
                          T.filter(pl.col("rule") == "lock-24h")["slot"].unique().sort().to_list()},
       "all": summ(T)}
# game-level injury effect on the margin (home view) at lock and final, lock-24h games
gm = (T.group_by("game_id", "slot", "rule").agg(
    lock_inj_home=(pl.when(pl.col("side") == "home").then(pl.col("lock_points")).otherwise(-pl.col("lock_points"))).sum(),
    final_inj_home=(pl.when(pl.col("side") == "home").then(pl.col("final_points")).otherwise(-pl.col("final_points"))).sum(),
    stats=pl.col("stats_margin_home").first(), line=pl.col("line_home_spread").first()))
gm = gm.with_columns(change=pl.col("final_inj_home") - pl.col("lock_inj_home"),
                     gap=pl.col("stats") + pl.col("line"))
res["game_level_lock24"] = {
    "n": gm.filter(pl.col("rule") == "lock-24h").height,
    "mean_abs_injury_effect_lock": float(gm.filter(pl.col("rule") == "lock-24h")["lock_inj_home"].abs().mean()),
    "mean_abs_injury_effect_final": float(gm.filter(pl.col("rule") == "lock-24h")["final_inj_home"].abs().mean()),
    "mean_abs_change_lock_to_final": float(gm.filter(pl.col("rule") == "lock-24h")["change"].abs().mean()),
    "max_abs_change_lock_to_final": float(gm.filter(pl.col("rule") == "lock-24h")["change"].abs().max()),
    "sign_flips_injury_effect": int(gm.filter((pl.col("rule") == "lock-24h") & (pl.col("lock_inj_home") * pl.col("final_inj_home") < 0)
                                              & (pl.col("final_inj_home").abs() > 0.1)).height),
    "toward_gap_side_at_final_big_gaps": None}
big = gm.filter((pl.col("gap").abs() >= 3) & pl.col("gap").is_not_null())
res["big_gap_games_all_rules"] = big.with_columns(
    inj_toward_gap_lock=pl.col("lock_inj_home") * pl.col("gap").sign(),
    inj_toward_gap_final=pl.col("final_inj_home") * pl.col("gap").sign()).sort("gap").to_dicts()
save("a1_timing", res)
gm.write_parquet(OUT / "a1_timing_games.parquet")

print("games", G.height, "team rows", T.height, "lock sha matches", res["lock_snapshot_matches_release_sha"])
print("recompute check", res["recompute_check"]["n"], res["recompute_check"]["max_abs_diff_lock"], res["recompute_check"]["max_abs_diff_final"], res["recompute_check"]["n_over_0.001"])
for k, v in res["by_rule"].items():
    print(k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
for k, v in res["lock24_by_slot"].items():
    print("  ", k, {a: (round(b, 3) if isinstance(b, float) else b) for a, b in v.items()})
print(res["game_level_lock24"])
