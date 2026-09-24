"""Tune feature-window settings on the TUNE folds only (never on dev or locked seasons).

Grid over the team-form half-life (games) and prior-season carry-over. For each setting the as-of
features are rebuilt, then football-only ridge models are scored walk-forward on the tune seasons.
The selected values are written to reports/tuning/ and must be copied into configs/settings.yaml
deliberately (the pipeline does not change its own configuration).
"""

from __future__ import annotations

import itertools
import json

import numpy as np
import polars as pl

from nflcast.config import PROCESSED_DIR, REPORTS_DIR, settings, utc_stamp
from nflcast.evaluation import backtest as BT
from nflcast.evaluation.metrics import point_metrics
from nflcast.features import personnel as P
from nflcast.features.asof import build_feature_snapshots


def run(half_lives=(4, 6, 8, 12, 16), carries=(0.4, 0.6, 0.8)) -> dict:
    from nflcast.pipeline import personnel_objects  # local import to avoid a cycle

    cfg = settings()
    tune = list(cfg["validation"]["tune_folds"])
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    tg = pl.read_parquet(PROCESSED_DIR / "team_games.parquet")
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet")
    market = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")
    seasons = list(range(cfg["seasons"]["core_start"], max(tune) + 1))
    orig = dict(cfg["features"])
    results = []
    qbm, dcs, avail = personnel_objects(games, tg, qbg)
    try:
        for hl, ca in itertools.product(half_lives, carries):
            cfg["features"]["half_life_games"], cfg["features"]["season_carryover"] = hl, ca
            feats = P.add_personnel_features(build_feature_snapshots(games, tg, seasons), games, qbm, dcs, avail)
            data = BT.assemble(games, feats, market)
            specs = [("B_qb", "core_qb", ("early", "final")), ("B_qb_inj", "core_qb_inj", ("final",))]
            preds, _ = BT.run(data, tune, ["early", "final"], specs=specs, combined=False)
            for (h, m), g in preds.filter(pl.col("model") != "N_naive_home").group_by(["horizon", "model"]):
                r = point_metrics(g)
                results.append({"half_life": hl, "carry": ca, "horizon": h, "model": m,
                                "margin_rmse": r["margin_rmse"], "total_rmse": r["total_rmse"], "n": r["n_games"]})
            print(f"[tune] hl={hl} carry={ca} done")
    finally:
        cfg["features"].update(orig)
    df = pl.DataFrame(results).with_columns(score=(pl.col("margin_rmse") + pl.col("total_rmse")) / 2)
    agg = df.group_by(["half_life", "carry"]).agg(pl.col("score").mean(), pl.col("margin_rmse").mean(),
                                                  pl.col("total_rmse").mean()).sort("score")
    best = agg.row(0, named=True)
    out = REPORTS_DIR / "tuning"
    out.mkdir(parents=True, exist_ok=True)
    stamp = utc_stamp()
    df.write_csv(out / f"window_grid_{stamp}.csv")
    summary = {"tune_folds": tune, "criterion": "mean of margin and total RMSE, averaged over horizons/models",
               "best": best, "grid": agg.to_dicts(), "current_settings": orig}
    (out / f"window_grid_{stamp}.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    print(agg)
    return summary
