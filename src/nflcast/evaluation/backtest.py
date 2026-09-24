"""Walk-forward (expanding window) backtest of benchmark and baseline models.

For each development fold season S: train on completed games from core_start..S-1, predict S.
The locked test season (settings.validation.locked_test) is excluded unless explicitly requested.
Every model in a comparison is scored on the same games at the same horizon.

Market availability by horizon (see docs/data_sources.md):
  * final (60 min pre-kick): the single historical schedule line, labelled approx_closing.
  * early (72 h): no free timestamped historical lines exist, so market-based models are NOT
    evaluated at this horizon historically. Only football-only and naive models are compared.
"""

from __future__ import annotations

import json

import numpy as np
import polars as pl

from nflcast.config import settings
from nflcast.evaluation.metrics import block_bootstrap_diff, per_game_losses, point_metrics
from nflcast.models.core import FootballRidge, MarketCalibrated, MarketRaw, NaiveHome, select_alpha_chronologically

OUTCOMES = ["home_score", "away_score", "margin", "total_points"]


def assemble(games: pl.DataFrame, feats: pl.DataFrame, market: pl.DataFrame) -> pl.DataFrame:
    g = games.filter(pl.col("status") == "final").select(["game_id", "game_type"] + OUTCOMES)
    m = market.select("game_id", "horizon", "home_spread", "total", "market_timing", "market_available")
    return feats.join(g, on="game_id", how="inner").join(m, on=["game_id", "horizon"], how="left")


def _pred_frame(test: pl.DataFrame, p: dict, model: str, fold: int, horizon: str) -> pl.DataFrame:
    return test.select(["game_id", "season", "week", "is_playoff", "neutral_site"] + OUTCOMES).with_columns(
        model=pl.lit(model), fold=pl.lit(fold), horizon=pl.lit(horizon),
        pred_home=pl.Series(p["home_pts"]), pred_away=pl.Series(p["away_pts"]),
        pred_margin=pl.Series(p["margin"]), pred_total=pl.Series(p["total"]),
        projected=pl.Series(p["projected"]))


def run(data: pl.DataFrame, folds: list[int], horizons: list[str], feature_set: dict | None = None,
        model_suffix: str = "") -> tuple[pl.DataFrame, dict]:
    cfg = settings()
    core_start = cfg["seasons"]["core_start"]
    preds, fold_info = [], []
    for h in horizons:
        dh = data.filter(pl.col("horizon") == h)
        for S in folds:
            train = dh.filter((pl.col("season") >= core_start) & (pl.col("season") < S))
            test = dh.filter(pl.col("season") == S)
            if test.height == 0:
                continue
            info = {"horizon": h, "fold": S, "n_train": train.height, "n_test": test.height}
            naive = NaiveHome().fit(train)
            preds.append(_pred_frame(test, naive.predict(test), NaiveHome.name, S, h))
            alpha, scores = select_alpha_chronologically(train, feature_set=feature_set)
            b = FootballRidge(alpha=alpha, feature_set=feature_set).fit(train)
            preds.append(_pred_frame(test, b.predict(test), FootballRidge.name + model_suffix, S, h))
            info.update({"B_alpha": alpha, "B_alpha_scores": scores})
            if h == "final":
                tr_m = train.filter(pl.col("market_available"))
                te_m = test.filter(pl.col("market_available"))
                info["market_rows_test"] = te_m.height
                preds.append(_pred_frame(te_m, MarketRaw().predict(te_m), MarketRaw.name, S, h))
                cal = MarketCalibrated().fit(tr_m)
                preds.append(_pred_frame(te_m, cal.predict(te_m), MarketCalibrated.name, S, h))
                info["A_cal_params"] = cal.params()
            fold_info.append(info)
    return pl.concat(preds), {"folds": fold_info}


def summarise(preds: pl.DataFrame, reps: int, seed: int) -> dict:
    out = {"overall": [], "per_season": [], "subgroups": [], "paired": []}
    for (h, m), grp in preds.group_by(["horizon", "model"], maintain_order=True):
        out["overall"].append({"horizon": h, "model": m, **point_metrics(grp)})
        for (s,), g2 in grp.group_by(["season"], maintain_order=True):
            out["per_season"].append({"horizon": h, "model": m, "season": s, **point_metrics(g2)})
        groups = {
            "weeks_1_4": grp.filter((pl.col("week") <= 4) & ~pl.col("is_playoff")),
            "weeks_5_plus_reg": grp.filter((pl.col("week") > 4) & ~pl.col("is_playoff")),
            "playoffs": grp.filter(pl.col("is_playoff")),
            "neutral_site": grp.filter(pl.col("neutral_site")),
        }
        for name, g2 in groups.items():
            if g2.height:
                r = point_metrics(g2)
                out["subgroups"].append({"horizon": h, "model": m, "group": name,
                                         "exploratory_small_n": g2.height < 100, **r})
    losses = per_game_losses(preds)
    pairs = [("B_football_ridge", "A_market_raw"), ("B_football_ridge", "A_market_cal"),
             ("A_market_cal", "A_market_raw"), ("B_football_ridge", "N_naive_home")]
    for h in preds["horizon"].unique().to_list():
        lh = losses.filter(pl.col("horizon") == h)
        for a, b in pairs:
            la, lb = lh.filter(pl.col("model") == a), lh.filter(pl.col("model") == b)
            if la.height == 0 or lb.height == 0:
                continue
            for loss in ("ae_margin", "ae_total", "se_margin", "se_total"):
                out["paired"].append({"horizon": h, "a": a, "b": b, "loss": loss,
                                      **block_bootstrap_diff(la, lb, loss, reps, seed)})
    return out


def to_markdown(summary: dict, fold_info: dict, manifest: dict) -> str:
    def fmt(x, nd=2):
        return "" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))

    L = [f"# Backtest report `{manifest['run_id']}`", "",
         f"Generated {manifest['generated_at_utc']} (UTC). Code hash `{manifest['code_hash'][:12]}`. "
         f"Folds (walk-forward, expanding window): {manifest['folds']}. Locked test season "
         f"{manifest['locked_test']} {'INCLUDED' if manifest['locked_included'] else 'not evaluated'}.", "",
         "All numbers below were produced by `python -m nflcast backtest` on real nflverse data. "
         "Lower is better for MAE/RMSE. Historical market lines are the single nflverse schedule line "
         "(timing unknown, treated as approximately closing), so market comparisons apply only to the final-pregame horizon.",
         "", "## Overall (pooled over folds)", "",
         "| horizon | model | n | margin MAE | margin RMSE | total MAE | total RMSE | home MAE | away MAE | winner acc |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(summary["overall"], key=lambda r: (r["horizon"], r["margin_rmse"])):
        L.append(f"| {r['horizon']} | {r['model']} | {r['n_games']} | {fmt(r['margin_mae'])} | {fmt(r['margin_rmse'])} | "
                 f"{fmt(r['total_mae'])} | {fmt(r['total_rmse'])} | {fmt(r['home_pts_mae'])} | {fmt(r['away_pts_mae'])} | "
                 f"{fmt(r['winner_accuracy'], 3)} |")
    L += ["", "## Paired differences (model a minus model b; negative = a better)", "",
          "Season-week block bootstrap 95% intervals. Only three development seasons: treat as limited evidence.", "",
          "| horizon | a | b | loss | n | mean diff | 95% CI |", "|---|---|---|---|---|---|---|"]
    for r in summary["paired"]:
        L.append(f"| {r['horizon']} | {r['a']} | {r['b']} | {r['loss']} | {r['n_games']} | {r['mean_diff']:+.3f} | "
                 f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}] |")
    L += ["", "## Per season", "", "| horizon | model | season | n | margin MAE | total MAE | winner acc |", "|---|---|---|---|---|---|---|"]
    for r in summary["per_season"]:
        L.append(f"| {r['horizon']} | {r['model']} | {r['season']} | {r['n_games']} | {fmt(r['margin_mae'])} | "
                 f"{fmt(r['total_mae'])} | {fmt(r['winner_accuracy'], 3)} |")
    L += ["", "## Subgroups (prespecified; small groups are exploratory)", "",
          "| horizon | model | group | n | margin MAE | total MAE | exploratory |", "|---|---|---|---|---|---|---|"]
    for r in summary["subgroups"]:
        L.append(f"| {r['horizon']} | {r['model']} | {r['group']} | {r['n_games']} | {fmt(r['margin_mae'])} | "
                 f"{fmt(r['total_mae'])} | {'yes' if r['exploratory_small_n'] else ''} |")
    L += ["", "## Fold details", "", "```json", json.dumps(fold_info, indent=1, default=str), "```"]
    return "\n".join(L)
