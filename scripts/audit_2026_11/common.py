"""Shared helpers for the 2026-11 model audit (Phase 1: audit only; nothing here changes the model, data or site).

Reuses the project's own backtest pieces (evaluation/backtest.py, models/core.py, evaluation/metrics.py):
  * data      = BT.assemble(games, feature_snapshots, market_asof), final horizon (60 min before kickoff)
  * model     = FootballRidge on the production fallback feature set core_qb (the published "Model line"), with the
                ridge alpha chosen chronologically inside each fold exactly as the existing backtest does
  * folds     = walk-forward 2019-2024 (train on 2016..S-1, predict S). 2025 (locked test) is never a test fold.

DECISION RULE (fixed before any audit experiment was run, from the audit brief, 2026-11-19):
  A change counts as an improvement only if (a) the paired per-game difference in absolute margin error versus the
  current model has a 95% season-week block-bootstrap CI that excludes zero (below zero) over 2019-2024, and (b) it
  improves margin MAE in at least 4 of the 6 seasons. Everything else is "no demonstrated improvement".
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import polars as pl

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.stdout.reconfigure(encoding="utf-8")

from nflcast.config import PROCESSED_DIR  # noqa: E402
from nflcast.evaluation import backtest as BT  # noqa: E402
from nflcast.evaluation.metrics import block_bootstrap_diff, per_game_losses, point_metrics  # noqa: E402
from nflcast.models.core import FootballRidge, feature_set, select_alpha_chronologically  # noqa: E402

FOLDS = [2019, 2020, 2021, 2022, 2023, 2024]
REPS, SEED = 2000, 20261119
OUT = ROOT / "reports" / "audit_2026_11"
OUT.mkdir(parents=True, exist_ok=True)


def load(horizon: str = "final") -> pl.DataFrame:
    games = pl.read_parquet(PROCESSED_DIR / "games.parquet")
    feats = pl.read_parquet(PROCESSED_DIR / "feature_snapshots.parquet")
    market = pl.read_parquet(PROCESSED_DIR / "market_asof.parquet")
    d = BT.assemble(games, feats, market).filter(pl.col("horizon") == horizon)
    return d


def games() -> pl.DataFrame:
    return pl.read_parquet(PROCESSED_DIR / "games.parquet")


def frame(test: pl.DataFrame, p: dict, model: str) -> pl.DataFrame:
    return test.select("game_id", "season", "week", "is_playoff", "neutral_site", "home_score", "away_score", "margin",
                       "total_points").with_columns(
        model=pl.lit(model), pred_home=pl.Series(p["home_pts"]), pred_away=pl.Series(p["away_pts"]),
        pred_margin=pl.Series(p["margin"]), pred_total=pl.Series(p["total"]))


def walk_forward(data: pl.DataFrame, name: str, fs: dict, folds=FOLDS, train_start: int = 2016,
                 fit_hook=None, pred_hook=None, alpha: float | None = None, info: dict | None = None) -> pl.DataFrame:
    """Football-only ridge, walk-forward. fit_hook(train)->(train', state); pred_hook(test, pred, state)->pred."""
    out = []
    for S in folds:
        tr = data.filter((pl.col("season") >= train_start) & (pl.col("season") < S))
        te = data.filter(pl.col("season") == S)
        state = None
        if fit_hook:
            tr, state = fit_hook(tr)
        a = alpha if alpha is not None else select_alpha_chronologically(tr, feature_set=fs)[0]
        m = FootballRidge(alpha=a, feature_set=fs).fit(tr)
        p = m.predict(te)
        if pred_hook:
            p = pred_hook(te, p, state)
        if info is not None:
            info.setdefault(name, {})[S] = {"alpha": a, "n_train": tr.height, "n_test": te.height,
                                            **({"state": state.get("report")} if isinstance(state, dict) and "report" in state else {})}
        out.append(frame(te, p, name))
    return pl.concat(out)


def live_2026(data: pl.DataFrame, name: str, fs: dict, fit_hook=None, pred_hook=None) -> pl.DataFrame:
    """Small extra out-of-sample check: train 2016-2024 (2025 is not used in this phase), predict 2026 weeks 3-10."""
    te_all = data.filter((pl.col("season") == 2026) & pl.col("week").is_between(3, 10) & pl.col("margin").is_not_null())
    d = pl.concat([data.filter(pl.col("season") <= 2024), te_all])
    return walk_forward(d, name, fs, folds=[2026], fit_hook=fit_hook, pred_hook=pred_hook)


def decide(preds: pl.DataFrame, cand: str, base: str, loss: str = "ae_margin") -> dict:
    """Decision rule above, plus RMSE and per-season detail. Paired on identical games."""
    L = per_game_losses(preds)
    a, b = L.filter(pl.col("model") == cand), L.filter(pl.col("model") == base)
    bb = block_bootstrap_diff(a, b, loss, REPS, SEED)
    seasons = []
    for S in sorted(a["season"].unique().to_list()):
        ma, mb = point_metrics(a.filter(pl.col("season") == S)), point_metrics(b.filter(pl.col("season") == S))
        key = "margin_mae" if loss == "ae_margin" else "total_mae"
        seasons.append({"season": S, "n": ma["n_games"], "cand_mae": ma[key], "base_mae": mb[key],
                        "better": ma[key] < mb[key]})
    se = block_bootstrap_diff(a, b, loss.replace("ae_", "se_"), REPS, SEED)
    ma, mb = point_metrics(a), point_metrics(b)
    n_better = sum(s["better"] for s in seasons)
    improved = bb["ci95"][1] < 0 and n_better >= 4
    return {"cand": cand, "base": base, "loss": loss, "n_games": bb["n_games"], "n_blocks": bb["n_blocks"],
            "mean_diff_ae": bb["mean_diff"], "ci95_ae": bb["ci95"], "mean_diff_se": se["mean_diff"], "ci95_se": se["ci95"],
            "cand_mae": ma["margin_mae" if loss == "ae_margin" else "total_mae"],
            "base_mae": mb["margin_mae" if loss == "ae_margin" else "total_mae"],
            "cand_rmse": ma["margin_rmse" if loss == "ae_margin" else "total_rmse"],
            "base_rmse": mb["margin_rmse" if loss == "ae_margin" else "total_rmse"],
            "seasons_better": n_better, "per_season": seasons,
            "verdict": "IMPROVEMENT" if improved else ("worse (CI above zero)" if bb["ci95"][0] > 0
                                                       else "no demonstrated improvement")}


def fmt_decision(d: dict) -> str:
    return (f"{d['cand']} vs {d['base']} ({d['loss']}): n={d['n_games']} games / {d['n_blocks']} weeks; "
            f"MAE {d['base_mae']:.3f} -> {d['cand_mae']:.3f}; diff {d['mean_diff_ae']:+.3f} "
            f"[{d['ci95_ae'][0]:+.3f}, {d['ci95_ae'][1]:+.3f}]; RMSE {d['base_rmse']:.3f} -> {d['cand_rmse']:.3f}; "
            f"better in {d['seasons_better']}/6 seasons -> {d['verdict']}")


def save(name: str, obj) -> Path:
    p = OUT / f"{name}.json"
    p.write_text(json.dumps(obj, indent=1, default=str), encoding="utf-8")
    return p


def base_fs() -> dict:
    return feature_set("core_qb")
