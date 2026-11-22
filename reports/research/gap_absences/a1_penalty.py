"""A1: the no-status penalty (research B8) and what the injury inputs are made of. Descriptive only: no model fitting and no
game results. Uses player participation (did a listed player take an offensive/defensive snap) as the B8 measurement did.

Historical rows = nflverse FINAL weekly injury reports 2019-2025 (the only version kept), joined to snap counts; the
injury input is rebuilt exactly as the frozen shadow/B_qb_inj training rule builds it (features/personnel.Availability:
as-of P(play | status) from the 5 seasons before, mean snap share over the team's previous 6 games incl. zeros).
Outputs:
  1. P(played) by final status x final practice status x recent snap-share band (2021-25, the shadow's rate window),
     against the rate the input assumes.
  2. Composition of the inputs (2019-25 final horizon): share of expected lost snaps, and of each unit's variance across
     team-games, from no-status / Questionable / Doubtful / Out rows.
  3. Calibration: realised lost snaps (recent share x did not play) / expected lost snaps, by status and band.
  4. Typical team-game totals (mean, sd per unit), to read per-unit costs against.
Writes a1_penalty.json and a1_penalty_rows.parquet.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from common import OUT, UNITS, PlayerAvailability, save  # noqa: E402
from nflcast.config import PROCESSED_DIR  # noqa: E402
from nflcast.data import sources as S  # noqa: E402
from nflcast.data.games import franchise  # noqa: E402
from nflcast.features import personnel as P  # noqa: E402

games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
SEASONS = list(range(2014, 2026))           # 2014+ so 2019's as-of P(play) has its 5 earlier seasons
EVAL = list(range(2019, 2026))


def injury_rows(seasons):
    """personnel.injury_player_weeks + practice status (final weekly report)."""
    idmap = S.fetch("players").select("gsis_id", pl.col("pfr_id").alias("pfr_player_id")).drop_nulls().unique("gsis_id")
    fr = [S.fetch("injuries", s).select(
        pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32), franchise(pl.col("team")).alias("team"),
        "gsis_id", "position", P._status_key(pl.col("report_status")).alias("status"),
        pl.col("practice_status").fill_null("None")) for s in seasons]
    inj = pl.concat(fr).unique(["season", "week", "team", "gsis_id"], keep="last").join(idmap, on="gsis_id", how="left")
    inj = inj.with_columns(unit=pl.col("position").replace_strict(P.UNIT_OF_POSITION, default=None))
    g = pl.concat([games.select("game_id", "season", "week", pl.col("home_id").alias("team"), "kickoff_utc"),
                   games.select("game_id", "season", "week", pl.col("away_id").alias("team"), "kickoff_utc")])
    return inj.join(g.with_columns(pl.col("season").cast(pl.Int32), pl.col("week").cast(pl.Int32)),
                    on=["season", "week", "team"], how="inner")


inj = injury_rows(SEASONS)
snaps = P.snap_shares(list(range(2012, 2026)), games)
av = PlayerAvailability(inj, snaps, tg)
gids = games.filter(pl.col("season").is_in(EVAL) & (pl.col("status") == "final"))["game_id"].to_list()
R = av.player_losses(gids)
this = snaps.select("game_id", "pfr_player_id", "team", game_share="share")
R = (R.join(this, on=["game_id", "pfr_player_id", "team"], how="left")
     .with_columns(pl.col("game_share").fill_null(0.0))
     .with_columns(played=(pl.col("game_share") > 0).cast(pl.Int8),
                   realised=pl.col("recent_share") * (pl.col("game_share") <= 0).cast(pl.Float64),
                   band=pl.when(pl.col("recent_share") < 0.2).then(pl.lit("a <0.2")).when(pl.col("recent_share") < 0.5)
                   .then(pl.lit("b 0.2-0.5")).when(pl.col("recent_share") < 0.8).then(pl.lit("c 0.5-0.8")).otherwise(pl.lit("d 0.8+")),
                   practice=pl.col("practice_status").str.replace(r"(?i).*did not.*", "DNP")
                   .str.replace(r"(?i).*limited.*", "Limited").str.replace(r"(?i).*full.*", "Full")))
R = R.with_columns(practice=pl.when(pl.col("practice").is_in(["DNP", "Limited", "Full"])).then(pl.col("practice"))
                   .otherwise(pl.lit("none/other")))
R.write_parquet(OUT / "a1_penalty_rows.parquet")
res = {"rows": R.height, "seasons": EVAL, "note": "played = took >= 1 offensive or defensive snap; special-teams-only = not played"}

# 1. participation by status x practice x band, 2021-25 (the frozen shadow's P(play) window)
W = R.filter(pl.col("season").is_between(2021, 2025))
tab = (W.group_by("status", "practice", "band").agg(n=pl.len(), played=pl.col("played").mean(),
                                                     assumed=1 - pl.col("p_miss").mean())
       .filter(pl.col("n") >= 30).sort("status", "practice", "band"))
res["participation_2021_25"] = tab.to_dicts()
res["participation_status_band_2021_25"] = (W.group_by("status", "band").agg(n=pl.len(), played=pl.col("played").mean(),
                                                                            assumed=1 - pl.col("p_miss").mean())
                                            .sort("status", "band").to_dicts())
reg = W.filter(pl.col("recent_share") >= 0.5)
res["b8_check_regulars_0.5plus"] = {s: {"n": d.height, "played": float(d["played"].mean())}
                                    for (s,), d in reg.group_by(["status"])}

# 2. composition of the inputs, 2019-25
TG = (R.group_by("game_id", "team", "season").agg(
    [pl.col("lost").filter((pl.col("unit") == u) & (pl.col("status") == s)).sum().alias(f"{u}|{s}")
     for u in UNITS for s in ("None", "Questionable", "Doubtful", "Out")]
    + [pl.col("realised").filter(pl.col("unit") == u).sum().alias(f"{u}|realised") for u in UNITS]))
# team-games with no listed players in a unit have 0 everywhere: add all team-games of the eval seasons
allteams = tg.join(games.select("game_id", "season", "status"), on="game_id").filter(
    pl.col("season").is_in(EVAL) & (pl.col("status") == "final")).select("game_id", "team", "season")
TG = allteams.join(TG.drop("season"), on=["game_id", "team"], how="left").fill_null(0.0)
comp = {}
for u in UNITS:
    parts = {s: TG[f"{u}|{s}"].to_numpy() for s in ("None", "Questionable", "Doubtful", "Out")}
    tot = sum(parts.values())
    v = tot.var()
    comp[u] = {"mean_total": float(tot.mean()), "sd_total": float(tot.std()),
               "share_of_expected": {s: float(p.sum() / tot.sum()) for s, p in parts.items()},
               "share_of_variance": {s: float(np.cov(p, tot)[0, 1] / v) for s, p in parts.items()},
               "realised_mean": float(TG[f"{u}|realised"].mean()),
               "corr_expected_realised": float(np.corrcoef(tot, TG[f"{u}|realised"].to_numpy())[0, 1])}
res["composition_2019_25"] = comp
res["team_games"] = TG.height

# 3. calibration: realised / expected by status and band
res["calibration_2019_25"] = (R.group_by("status", "band").agg(n=pl.len(), expected=pl.col("lost").sum(),
                                                                realised=pl.col("realised").sum())
                              .with_columns(ratio=pl.col("realised") / pl.col("expected")).sort("status", "band").to_dicts())
res["calibration_by_unit_2019_25"] = (R.group_by("unit").agg(expected=pl.col("lost").sum(), realised=pl.col("realised").sum())
                                      .with_columns(ratio=pl.col("realised") / pl.col("expected")).sort("unit").to_dicts())
# no-status rows: what share of all expected lost snaps, and how much of it was realised
ns = R.filter(pl.col("status") == "None")
res["no_status"] = {"share_of_expected_lost": float(ns["lost"].sum() / R["lost"].sum()),
                    "expected": float(ns["lost"].sum()), "realised": float(ns["realised"].sum()),
                    "regulars_0.5plus_expected": float(ns.filter(pl.col("recent_share") >= 0.5)["lost"].sum()),
                    "regulars_0.5plus_realised": float(ns.filter(pl.col("recent_share") >= 0.5)["realised"].sum())}
save("a1_penalty", res)

print("rows", R.height, "team-games", TG.height)
for s, d in sorted(res["b8_check_regulars_0.5plus"].items()):
    print("regulars", s, d)
for r in res["participation_status_band_2021_25"]:
    print(f"  {r['status']:12s} {r['band']:10s} n={r['n']:6d} played {r['played']:.3f} assumed {r['assumed']:.3f}")
for u, c in comp.items():
    print(u, {k: (round(v, 3) if isinstance(v, float) else {a: round(b, 3) for a, b in v.items()}) for k, v in c.items()})
print("no-status", {k: round(v, 3) for k, v in res["no_status"].items()})
for r in res["calibration_2019_25"]:
    print(f"  cal {r['status']:12s} {r['band']:10s} n={r['n']:6d} exp {r['expected']:8.1f} real {r['realised']:8.1f} ratio {r['ratio']:.2f}")
