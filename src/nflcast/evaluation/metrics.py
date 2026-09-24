"""Point-forecast metrics and time-aware paired comparisons."""

from __future__ import annotations

import numpy as np
import polars as pl


def point_metrics(df: pl.DataFrame) -> dict:
    """df needs pred_home, pred_away, pred_margin, pred_total, home_score, away_score, margin, total_points."""
    em = df["pred_margin"] - df["margin"]
    et = df["pred_total"] - df["total_points"]
    eh = df["pred_home"] - df["home_score"]
    ea = df["pred_away"] - df["away_score"]
    decided = df.filter(pl.col("margin") != 0)
    # A predicted margin of exactly 0 counts as a miss (no winner projected).
    win_acc = float((np.sign(decided["pred_margin"]) == np.sign(decided["margin"])).mean()) if decided.height else None
    return {
        "n_games": df.height,
        "margin_mae": float(em.abs().mean()), "margin_rmse": float(np.sqrt((em ** 2).mean())),
        "total_mae": float(et.abs().mean()), "total_rmse": float(np.sqrt((et ** 2).mean())),
        "home_pts_mae": float(eh.abs().mean()), "away_pts_mae": float(ea.abs().mean()),
        "margin_bias": float(em.mean()), "total_bias": float(et.mean()),
        "winner_accuracy": win_acc, "n_decided": decided.height,
    }


def per_game_losses(df: pl.DataFrame) -> pl.DataFrame:
    return df.with_columns(
        ae_margin=(pl.col("pred_margin") - pl.col("margin")).abs(),
        se_margin=(pl.col("pred_margin") - pl.col("margin")) ** 2,
        ae_total=(pl.col("pred_total") - pl.col("total_points")).abs(),
        se_total=(pl.col("pred_total") - pl.col("total_points")) ** 2,
    )


def block_bootstrap_diff(a: pl.DataFrame, b: pl.DataFrame, loss: str, reps: int, seed: int) -> dict:
    """Paired difference mean(loss_a - loss_b) with a season-week block bootstrap 95% CI.

    Games in the same week share league-wide conditions, so weeks (not games) are resampled.
    Negative values mean model `a` has lower loss than `b`.
    """
    j = a.select("game_id", "season", "week", pl.col(loss).alias("la")).join(
        b.select("game_id", pl.col(loss).alias("lb")), on="game_id", how="inner")
    j = j.with_columns(d=pl.col("la") - pl.col("lb"), block=pl.format("{}-{}", "season", "week"))
    blocks = j.group_by("block").agg(s=pl.col("d").sum(), n=pl.len())
    s, n = blocks["s"].to_numpy(), blocks["n"].to_numpy()
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(s), size=(reps, len(s)))
    boot = s[idx].sum(axis=1) / n[idx].sum(axis=1)
    return {"n_games": j.height, "n_blocks": len(s), "mean_diff": float(j["d"].mean()),
            "ci95": [float(np.quantile(boot, 0.025)), float(np.quantile(boot, 0.975))]}
