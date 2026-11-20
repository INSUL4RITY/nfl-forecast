"""A1: why do the project's cost estimates for a missing offensive lineman differ by about four times? No model fitting,
no game results: frozen coefficients are read, and the rest is counting.

  (a) Frozen shadow ridge (configs/shadow_injury.yaml artifact): points per 1.0 starter-equivalent of EXPECTED lost
      snaps, per unit; the ridge penalty in the orthogonal case; the calibration of the expected input against the
      snaps actually lost (from a1_penalty_rows.parquet).
  (b) The team-analytics OL figure (origin/team-analytics scripts/team_analytics/line_absence_backtest.json):
      -0.047 EPA per dropback per "missing" starter, where missing = under 50% of THAT game's offensive snaps. Here:
      how many of those missing starters were known absent before kickoff (final report Out/Doubtful) and how many
      were in-game exits, benchings or rotation (descriptive, 2021-25, same starter definition).
  (c) B11's 0.39 and the 19 Nov hand estimate are restated with their definitions.
Writes a1_costs.json.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from common import OUT, save, shadow_unit_points  # noqa: E402
from nflcast.config import PROCESSED_DIR  # noqa: E402
from nflcast.data import sources as S  # noqa: E402
from nflcast.data.games import franchise  # noqa: E402
from nflcast.features import personnel as P  # noqa: E402

res = {}
c = shadow_unit_points()
res["shadow_points_per_starter_equivalent"] = {u: c[u] for u in ("ol", "skill", "front", "db")}
res["shadow_alpha"] = c["alpha"]
n_rows = 2 * 2793
res["ridge_orthogonal_shrink_factor"] = n_rows / (n_rows + c["alpha"])   # standardised X, X'X ~ n I

# (a) calibration slope of realised on expected lost, per unit and team-game (2019-25 final reports)
R = pl.read_parquet(OUT / "a1_penalty_rows.parquet")
TG = R.group_by("game_id", "team", "unit").agg(exp=pl.col("lost").sum(), real=pl.col("realised").sum())
cal = {}
for (u,), d in TG.group_by(["unit"]):
    x, y = d["exp"].to_numpy(), d["real"].to_numpy()
    b = float(np.cov(x, y)[0, 1] / x.var())
    cal[u] = {"slope_realised_on_expected": b, "team_games_with_listing": d.height}
res["calibration_slope"] = cal

# (b) team-analytics definition vs pre-game knowledge, 2021-25
games = pl.read_parquet(PROCESSED_DIR / "games.parquet").filter(pl.col("game_type") == "REG")
idmap = S.fetch("players").select("gsis_id", pl.col("pfr_id").alias("pfr_player_id")).drop_nulls().unique("gsis_id")
OL = {"T", "G", "C", "OL", "OT", "OG"}
rows = []
for s in range(2021, 2026):
    sn = (S.fetch("snap_counts", s).filter((pl.col("game_type") == "REG") & pl.col("position").is_in(list(OL)))
          .select("game_id", "week", franchise(pl.col("team")).alias("team"), "pfr_player_id", "offense_snaps", "offense_pct"))
    inj = (S.fetch("injuries", s).select(pl.col("week").cast(pl.Int32), franchise(pl.col("team")).alias("team"), "gsis_id",
                                          P._status_key(pl.col("report_status")).alias("status"))
           .unique(["week", "team", "gsis_id"], keep="last").join(idmap, on="gsis_id", how="inner"))
    gm = games.filter(pl.col("season") == s)
    tw = pl.concat([gm.select("game_id", "week", pl.col("home_id").alias("team")), gm.select("game_id", "week", pl.col("away_id").alias("team"))])
    for r in tw.filter(pl.col("week") >= 4).iter_rows(named=True):
        prior = sn.filter((pl.col("team") == r["team"]) & (pl.col("week") < r["week"]))
        top5 = prior.group_by("pfr_player_id").agg(sn=pl.col("offense_snaps").sum()).sort("sn", descending=True).head(5)["pfr_player_id"].to_list()
        this = sn.filter(pl.col("game_id") == r["game_id"])
        pct = dict(zip(this["pfr_player_id"], this["offense_pct"]))
        st = inj.filter((pl.col("team") == r["team"]) & (pl.col("week") == r["week"]))
        stat = dict(zip(st["pfr_player_id"], st["status"]))
        for p in top5:
            share = float(pct.get(p, 0.0) or 0.0)
            if share < 0.5:
                rows.append({"season": s, "game_id": r["game_id"], "team": r["team"], "pfr": p, "share": share,
                             "status": stat.get(p, "not listed")})
M = pl.DataFrame(rows)
tot = M.height
kinds = (M.with_columns(kind=pl.when(pl.col("status").is_in(["Out", "Doubtful"])).then(pl.lit("known absent (Out/Doubtful)"))
                        .when((pl.col("share") == 0) & (pl.col("status") == "Questionable")).then(pl.lit("Questionable, did not play"))
                        .when(pl.col("share") == 0).then(pl.lit("no game status, did not play (late scratch, reserve list, trade, benched)"))
                        .otherwise(pl.lit("played some snaps (in-game exit, benching, rotation)")))
         .group_by("kind").agg(n=pl.len()).with_columns(share=pl.col("n") / tot).sort("n", descending=True))
# the "no game status, did not play" group: same-week roster status (rosters_weekly, game week)
p2g = S.fetch("players").select(pl.col("pfr_id").alias("pfr"), "gsis_id").drop_nulls().unique("pfr")
ros = pl.concat([S.fetch("rosters_weekly", s).select(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32),
                                                      franchise(pl.col("team")).alias("team"), "gsis_id", "status")
                 for s in range(2021, 2026)]).unique(["season", "week", "team", "gsis_id"], keep="last")
ns = (M.filter((pl.col("share") == 0) & (pl.col("status") == "not listed"))
      .join(games.select("game_id", pl.col("week").cast(pl.Int32)), on="game_id").join(p2g, on="pfr", how="left")
      .with_columns(pl.col("season").cast(pl.Int32)))
ns = ns.join(ros.rename({"status": "roster"}), on=["season", "week", "team", "gsis_id"], how="left").with_columns(
    roster=pl.col("roster").fill_null("not on this team's roster that week"))
res["no_status_did_not_play_roster"] = ns.group_by("roster").agg(n=pl.len()).sort("n", descending=True).to_dicts()
res["analytics_missing_starters_2021_25"] = {"n_missing": tot, "kinds": kinds.to_dicts(),
                                              "analytics_json": {"team_games": 2238, "missing_counts": {"0": 737, "1": 927, "2": 440, "3+": 134},
                                                                 "epa_per_missing": -0.047, "ci": [-0.0609, -0.0318],
                                                                 "controls": "own season-to-date hit-or-sack rate allowed, opponent's rate; NOT own offensive efficiency"}}
res["conversions"] = {
    "analytics_per_missing_starter_epa_35_40_db": [-0.047 * 35, -0.047 * 40],
    "analytics_ci_per_game_37db": [-0.0609 * 37, -0.0318 * 37],
    "shadow_per_full_time_ol_starter_out": c["ol"] * 0.95,
    "b11_note": "0.39 pts = how far the Model line sits from the market line per extra starter-equivalent missing (weeks 3-10 2026, 118 games, corr 0.14): a model-vs-market difference, not a cost",
    "hand_estimate_note": "1.25-1.5 pts per starting tackle (19 Nov): a position-specific value assumed, not estimated; ~3x the OL unit mean"}
save("a1_costs", res)
print({k: v for k, v in res.items() if k != "analytics_missing_starters_2021_25"})
print("missing starters (team-analytics definition):", tot)
print("no-status did-not-play roster:", res["no_status_did_not_play_roster"])
for r in res["analytics_missing_starters_2021_25"]["kinds"]:
    print(f"  {r['n']:5d} {r['share']:.3f}  {r['kind']}")
