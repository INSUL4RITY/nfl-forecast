"""Pre-registered v2.0 vs v1.0 stats-only comparison (reports/research/v2_preregistration_2026-10-26.md).

Walk-forward, expanding window, final horizon: train 2016..S-1, predict S for S in FOLDS; both arms on identical games
with the same ridge-alpha rule. Pass if v2.0's pooled mean squared margin error is <= v1.0's (point estimate).
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl

from nflcast.config import PROCESSED_DIR, REPORTS_DIR, settings, utc_now, utc_stamp
from nflcast.evaluation import backtest as BT
from nflcast.evaluation.metrics import block_bootstrap_diff, per_game_losses, point_metrics
from nflcast.features import v2 as V2
from nflcast.models.core import FootballRidge, feature_set, select_alpha_chronologically

FOLDS = [2019, 2020, 2021, 2022, 2023, 2024, 2025]
GROUPS = {   # drop-one ablations (reported, not gating)
    "penalties": ["off_pen_off", "off_pen_def", "def_pen_off", "def_pen_def"],
    "luck_regression": ["off_fum_all", "def_fum_all", "off_third", "def_third", "off_fourth", "def_fourth", "off_close"],
    "qb_extra": ["off_scr_epa", "def_scr_epa", "qb_exp"],
    "coaching_go_rate": ["off_go_rate"],
    "injuries": ["lost_ol", "lost_skill", "lost_front", "lost_db"],
    "travel_body_clock": V2.TRAVEL,
    "special_teams": ["off_st"],
    "divisional": ["div_game"],
    "weather": V2.WX,
}
EFF = ["epa_play", "epa_db", "epa_rush", "succ_play", "expl_db", "expl_rush"]


def load() -> tuple[pl.DataFrame, pl.DataFrame]:
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    market = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")
    v1 = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet"), market).filter(pl.col("horizon") == "final")
    v2 = BT.assemble(games, pl.read_parquet(PROCESSED_DIR / "feature_snapshots_v2.parquet"), market).filter(pl.col("horizon") == "final")
    ids = set(v1["game_id"].to_list()) & set(v2["game_id"].to_list())
    return (v1.filter(pl.col("game_id").is_in(list(ids))).sort("game_id"),
            v2.filter(pl.col("game_id").is_in(list(ids))).sort("game_id"))


def without(fs: dict, drop: list[str]) -> dict:
    return {k: [f for f in v if f not in drop] for k, v in fs.items()}


def walk(data: pl.DataFrame, fs: dict, name: str, folds=FOLDS) -> pl.DataFrame:
    out = []
    start = settings()["seasons"]["core_start"]
    for S in folds:
        train = data.filter((pl.col("season") >= start) & (pl.col("season") < S))
        test = data.filter(pl.col("season") == S)
        if test.height == 0:
            continue
        alpha, _ = select_alpha_chronologically(train, feature_set=fs)
        p = FootballRidge(alpha=alpha, feature_set=fs).fit(train).predict(test)
        out.append(BT._pred_frame(test, p, name, S, "final").with_columns(
            alpha=pl.lit(alpha), home_spread=test["home_spread"], market_available=test["market_available"]))
    return pl.concat(out)


def side_agreement(df: pl.DataFrame) -> dict:
    d = df.filter(pl.col("market_available").fill_null(False)).with_columns(
        res=pl.col("margin") + pl.col("home_spread"), pr=pl.col("pred_margin") + pl.col("home_spread"))
    d = d.filter((pl.col("res") != 0) & (pl.col("pr") != 0))
    right = int((np.sign(d["res"].to_numpy()) == np.sign(d["pr"].to_numpy())).sum())
    return {"n": d.height, "right": right, "rate": right / d.height if d.height else None}


def run(reps: int | None = None) -> dict:
    v = settings()["validation"]
    reps, seed = reps or v["bootstrap_reps"], v["seed"]
    v1, v2 = load()
    fs1, fs2 = feature_set("core_qb"), feature_set("v2")
    p1, p2 = walk(v1, fs1, "B_qb_v1"), walk(v2, fs2, "B_v2")
    L1, L2 = per_game_losses(p1), per_game_losses(p2)
    primary = block_bootstrap_diff(L2, L1, "se_margin", reps, seed)
    res = {"rule": "pass if pooled mean squared margin error (2019-2025) of v2.0 <= v1.0", "folds": FOLDS,
           "n_games": p1.height, "primary_se_margin_diff_v2_minus_v1": primary, "pass": primary["mean_diff"] <= 0,
           "v1": {**point_metrics(p1), "side": side_agreement(p1)}, "v2": {**point_metrics(p2), "side": side_agreement(p2)},
           "paired": {loss: block_bootstrap_diff(L2, L1, loss, reps, seed) for loss in ("ae_margin", "se_total")},
           "per_season": [], "ablations": {}, "alphas": {"v1": p1.group_by("fold").agg(pl.col("alpha").first()).sort("fold").rows(),
                                                        "v2": p2.group_by("fold").agg(pl.col("alpha").first()).sort("fold").rows()}}
    for S in FOLDS:
        a, b = p1.filter(pl.col("season") == S), p2.filter(pl.col("season") == S)
        res["per_season"].append({"season": S, "v1_margin_rmse": point_metrics(a)["margin_rmse"],
                                  "v2_margin_rmse": point_metrics(b)["margin_rmse"],
                                  "v1_side": side_agreement(a)["rate"], "v2_side": side_agreement(b)["rate"]})
    # 2026 so far (weeks 1-7), both trained on 2016-2025
    q1, q2 = walk(v1, fs1, "B_qb_v1", [2026]), walk(v2, fs2, "B_v2", [2026])
    res["season_2026"] = {"v1": {**point_metrics(q1), "side": side_agreement(q1)},
                          "v2": {**point_metrics(q2), "side": side_agreement(q2)}}
    # ablations: v2 minus one group (positive = removing the group hurts, i.e. the group helps)
    base_se = float(L2["se_margin"].mean())
    for g, cols in GROUPS.items():
        pa = per_game_losses(walk(v2, without(fs2, cols), f"v2_minus_{g}"))
        res["ablations"][g] = float(pa["se_margin"].mean()) - base_se
    v2_eff = v2.drop([f"{s}_{p}_{m}" for s in ("home", "away") for p in ("off", "def") for m in EFF]
                     + [f"{s}_adj_{p}_epa" for s in ("home", "away") for p in ("off", "def")]).join(
        v1.select(["game_id"] + [f"{s}_{p}_{m}" for s in ("home", "away") for p in ("off", "def") for m in EFF]
                  + [f"{s}_adj_{p}_epa" for s in ("home", "away") for p in ("off", "def")]), on="game_id")
    pa = per_game_losses(walk(v2_eff, fs2, "v2_no_garbage_filter"))
    res["ablations"]["garbage_time_filter"] = float(pa["se_margin"].mean()) - base_se
    res["generated_at_utc"] = utc_now().isoformat()
    d = REPORTS_DIR / "research"
    stamp = utc_stamp()
    (d / f"v2_evaluation_{stamp}.json").write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    pl.concat([p1, p2]).write_parquet(d / f"v2_evaluation_{stamp}_predictions.parquet")
    return res
