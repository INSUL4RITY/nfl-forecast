"""v3-C: leverage-weighted QB rating vs the frozen v1.0 stats-only model (reports/research/qb_v3c_preregistration_2026-11-16.md).

Walk-forward, final horizon (actual starter as the retrospective proxy), identical games in both arms. Only the four QB
columns per side change; team form, alpha rule and everything else are the v1.0 specification (`core_qb`).
"""

from __future__ import annotations

import json
from types import MethodType

import numpy as np
import polars as pl

from nflcast.config import PROCESSED_DIR, REPORTS_DIR, settings, utc_now, utc_stamp
from nflcast.data import sources as S
from nflcast.data.games import franchise
from nflcast.evaluation import backtest as BT
from nflcast.evaluation.metrics import block_bootstrap_diff, per_game_losses, point_metrics
from nflcast.evaluation.v2_eval import side_agreement, walk
from nflcast.features import personnel as P
from nflcast.models.core import feature_set

TUNE = [2019, 2020, 2021]
TEST = [2022, 2023, 2024, 2025]
GRID = [(c, f) for c in (0.05, 0.10, 0.15, 0.20, 0.30) for f in (0.0, 0.25, 0.5)]
COMPETITIVE_M = 0.10            # diagnostics: competitive = offence win probability between 0.10 and 0.90
QB_COLS = ["qb_rating", "qb_log_db", "qb_delta"]


def leverage_weight(wp: pl.Expr, c: float, f: float) -> pl.Expr:
    """w = f + (1 - f) * min(1, min(wp, 1 - wp) / c); missing wp -> 1."""
    m = pl.min_horizontal(wp, 1 - wp)
    return pl.when(wp.is_null()).then(1.0).otherwise(f + (1 - f) * pl.min_horizontal(pl.lit(1.0), m / c))


def dropbacks(last_season: int) -> pl.DataFrame:
    """Every rated dropback (same filter as personnel.qb_games) with its pre-snap offensive win probability."""
    start = settings()["seasons"]["warmup_start"]
    cols = ["game_id", "play_id", "posteam", "passer_id", "qb_dropback", "qb_spike", "play_type", "epa", "wp"]
    frames = [S.fetch("pbp", s).select(cols) for s in range(start, last_season + 1)]
    p = pl.concat(frames, how="vertical_relaxed")
    return (p.filter((pl.col("qb_dropback") == 1) & (pl.col("qb_spike").fill_null(0) == 0)
                     & pl.col("passer_id").is_not_null() & (pl.col("play_type") != "no_play"))
            .select("game_id", franchise(pl.col("posteam")).alias("team"), pl.col("passer_id").alias("qb_id"),
                    pl.col("epa").fill_null(0.0).alias("epa"), "wp"))


def weighted_qbg(qbg: pl.DataFrame, db: pl.DataFrame, c: float, f: float) -> pl.DataFrame:
    """qb_games with db / epa replaced by leverage-weighted sums (rows without play data keep their values)."""
    w = (db.with_columns(w=leverage_weight(pl.col("wp"), c, f))
         .group_by("game_id", "team", "qb_id").agg(db_w=pl.col("w").sum(), epa_w=(pl.col("w") * pl.col("epa")).sum()))
    return (qbg.join(w, on=["game_id", "team", "qb_id"], how="left")
            .with_columns(db=pl.coalesce("db_w", pl.col("db").cast(pl.Float64)), epa=pl.coalesce("epa_w", "epa"))
            .drop("db_w", "epa_w"))


def qb_model(qbg_w: pl.DataFrame, base: P.QBModel) -> P.QBModel:
    """Weighted QB model whose prior is the unchanged (unweighted) prior, as pre-registered."""
    m = P.QBModel(qbg_w)
    m.prior = MethodType(lambda self, cutoff_us: base.prior(cutoff_us), m)
    return m


def recompute_qb(feats: pl.DataFrame, qbm: P.QBModel) -> pl.DataFrame:
    """Replace the QB columns of final-horizon rows, keeping each row's QB (the actual starter for final games)."""
    cfg = settings()["features"]
    hl, carry = float(cfg["half_life_games"]), float(cfg["season_carryover"])
    recs = []
    for r in feats.iter_rows(named=True):
        c_us = int(r["cutoff_utc"].timestamp() * 1_000_000)
        rec = {"game_id": r["game_id"]}
        for side in ("home", "away"):
            rating, wdb = qbm.rating(r[f"{side}_qb_id"], c_us, r["season"])
            base = qbm.baseline_rating(r[f"{side}_id"], c_us, r["season"], hl, carry)
            rec.update({f"{side}_qb_rating": rating, f"{side}_qb_log_db": float(np.log1p(wdb)), f"{side}_qb_delta": rating - base})
        recs.append(rec)
    drop = [f"{s}_{c}" for s in ("home", "away") for c in QB_COLS]
    return feats.drop(drop).join(pl.DataFrame(recs), on="game_id", how="left")


def diagnostics(db: pl.DataFrame, qbg: pl.DataFrame, season: int, min_db: int = 150) -> list[dict]:
    """Per QB in `season`: full, competitive and low-leverage EPA per dropback (descriptive)."""
    g = qbg.filter(pl.col("season") == season).select("game_id").unique()
    d = db.join(g, on="game_id").with_columns(m=pl.min_horizontal(pl.col("wp"), 1 - pl.col("wp")))
    t = (d.group_by("qb_id").agg(
        n=pl.len(), full=pl.col("epa").mean(),
        competitive=pl.col("epa").filter(pl.col("m") >= COMPETITIVE_M).mean(),
        low=pl.col("epa").filter(pl.col("m") < COMPETITIVE_M).mean(),
        low_share=(pl.col("m") < COMPETITIVE_M).mean())
         .filter(pl.col("n") >= min_db).sort("full", descending=True))
    names = S.fetch("players").select(pl.col("gsis_id").alias("qb_id"), pl.col("display_name").alias("qb")).unique("qb_id")
    return t.join(names, on="qb_id", how="left").to_dicts()


def splits(p: pl.DataFrame, feats: pl.DataFrame) -> dict:
    """Margin MAE/RMSE for starter-change games, inexperienced starters (< 200 career dropbacks), playoffs."""
    x = p.join(feats.select("game_id", "home_qb_log_db", "away_qb_log_db"), on="game_id", how="left")
    out = {}
    for name, cond in (("starter_change", pl.col("qb_changed")), ("playoffs", pl.col("is_playoff") == 1),
                       ("regular_season", pl.col("is_playoff") != 1)):
        s = x.filter(cond)
        if s.height:
            e = (s["pred_margin"] - s["margin"]).to_numpy()
            out[name] = {"n": s.height, "mae": float(np.abs(e).mean()), "rmse": float(np.sqrt((e ** 2).mean()))}
    return out


def run(reps: int | None = None) -> dict:
    v = settings()["validation"]
    reps, seed = reps or v["bootstrap_reps"], v["seed"]
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    market = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")
    snaps = pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet").filter(pl.col("horizon") == "final")
    data_a = BT.assemble(games, snaps, market).filter((pl.col("horizon") == "final") & (pl.col("season") <= TEST[-1])).sort("game_id")
    feats = snaps.filter(pl.col("game_id").is_in(data_a["game_id"].to_list()))
    qbg = pl.read_parquet(PROCESSED_DIR / "qb_games.parquet").filter(pl.col("season") <= TEST[-1])
    db = dropbacks(TEST[-1])
    base = P.QBModel(qbg)
    fs = feature_set("core_qb")

    # reproduction check: weight 1 everywhere must give back the stored QB columns (arm A)
    one = recompute_qb(feats, qb_model(weighted_qbg(qbg, db, 0.5, 1.0), base))
    chk = feats.select("game_id", *[f"{s}_{c}" for s in ("home", "away") for c in QB_COLS]).join(
        one.select("game_id", *[pl.col(f"{s}_{c}").alias(f"n_{s}_{c}") for s in ("home", "away") for c in QB_COLS]), on="game_id")
    repro = max(float((chk[f"{s}_{c}"] - chk[f"n_{s}_{c}"]).abs().max()) for s in ("home", "away") for c in QB_COLS)

    def arm(c: float, f: float) -> pl.DataFrame:
        qf = recompute_qb(feats, qb_model(weighted_qbg(qbg, db, c, f), base))
        return BT.assemble(games, qf, market).filter((pl.col("horizon") == "final") & (pl.col("season") <= TEST[-1])).sort("game_id")

    tune_a = walk(data_a, fs, "A", TUNE)
    mse = lambda p: float(((p["pred_margin"] - p["margin"]) ** 2).mean())
    tune = [{"c": None, "f": 1.0, "mse": mse(tune_a)}]
    arms = {}
    for c, f in GRID:
        arms[(c, f)] = arm(c, f)
        tune.append({"c": c, "f": f, "mse": mse(walk(arms[(c, f)], fs, f"C_{c}_{f}", TUNE))})
    grid = sorted(tune[1:], key=lambda r: r["mse"])
    best = grid[0]["mse"]
    chosen = sorted([r for r in grid if r["mse"] <= best + 0.01], key=lambda r: (-r["f"], -r["c"]))[0]
    c, f = chosen["c"], chosen["f"]

    pa, pc = walk(data_a, fs, "A", TEST), walk(arms[(c, f)], fs, "C", TEST)
    La, Lc = per_game_losses(pa), per_game_losses(pc)
    primary = block_bootstrap_diff(Lc, La, "se_margin", reps, seed)
    passed = primary["mean_diff"] < 0 and primary["ci95"][1] < 0
    res = {
        "preregistration": "reports/research/qb_v3c_preregistration_2026-11-16.md",
        "rule": "pass if pooled MSE(C) < MSE(A) over 2022-2025 and the 95% week-block bootstrap interval of C - A is below 0",
        "reproduction_max_abs_diff": repro,
        "tune_folds": TUNE, "test_folds": TEST, "tune_results": tune, "chosen": {"c": c, "f": f},
        "primary_se_margin_diff_C_minus_A": primary, "pass": passed,
        "A": point_metrics(pa), "C": point_metrics(pc),
        "secondary": {"ae_margin_diff_C_minus_A": block_bootstrap_diff(Lc, La, "ae_margin", reps, seed),
                      "side_vs_untimed_line": {"A": side_agreement(pa), "C": side_agreement(pc)},
                      "splits": {"A": splits(pa, data_a), "C": splits(pc, arms[(c, f)])},
                      "per_season_mse": {str(s): {"A": mse(pa.filter(pl.col("season") == s)),
                                                  "C": mse(pc.filter(pl.col("season") == s))} for s in TEST}},
        "diagnostics_2025": diagnostics(db, qbg, 2025),
        "generated_at_utc": utc_now().isoformat(),
    }
    out = REPORTS_DIR / "research" / f"qb_v3c_evaluation_{utc_stamp()}.json"
    out.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8")
    pl.concat([pa, pc]).write_parquet(out.with_name(out.stem + "_predictions.parquet"))
    print(f"[qb-v3c] reproduction max |diff| {repro:.2e}; chosen c={c} f={f}; "
          f"MSE A {mse(pa):.3f} C {mse(pc):.3f}; diff {primary['mean_diff']:+.3f} CI {primary['ci95']}; pass={passed}")
    print(f"[qb-v3c] wrote {out}")
    return res


if __name__ == "__main__":
    run()
