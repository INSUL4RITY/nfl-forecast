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
from nflcast.models.combined import DirectRidge, ResidualHGB, ResidualRidge, select_resid_alphas
from nflcast.models.core import (FootballRidge, MarketCalibrated, MarketRaw, NaiveHome, feature_set,
                                 select_alpha_chronologically)

OUTCOMES = ["home_score", "away_score", "margin", "total_points"]


def assemble(games: pl.DataFrame, feats: pl.DataFrame, market: pl.DataFrame) -> pl.DataFrame:
    g = games.filter(pl.col("status") == "final").select(["game_id", "game_type"] + OUTCOMES)
    m = market.select("game_id", "horizon", "home_spread", "total", "market_timing", "market_available")
    return feats.join(g, on="game_id", how="inner").join(m, on=["game_id", "horizon"], how="left")


def _pred_frame(test: pl.DataFrame, p: dict, model: str, fold: int, horizon: str) -> pl.DataFrame:
    qbc = ((pl.col("home_qb_change") + pl.col("away_qb_change")) > 0) if "home_qb_change" in test.columns else pl.lit(False)
    return test.select(["game_id", "season", "week", "is_playoff", "neutral_site"] + OUTCOMES + [qbc.alias("qb_changed")]).with_columns(
        model=pl.lit(model), fold=pl.lit(fold), horizon=pl.lit(horizon),
        pred_home=pl.Series(p["home_pts"]), pred_away=pl.Series(p["away_pts"]),
        pred_margin=pl.Series(p["margin"]), pred_total=pl.Series(p["total"]),
        projected=pl.Series(p["projected"]))


# Football-only specifications: (model name, feature-set name, horizons it is valid for)
FOOTBALL_SPECS = [
    ("B_core", "core", ("early", "final")),
    ("B_qb", "core_qb", ("early", "final")),
    ("B_qb_noadj", "core_qb_noadj", ("early", "final")),
    ("B_qb_inj", "core_qb_inj", ("final",)),
]


COMBINED_SPECS = [
    ("C_resid", "core_qb_inj"),
    ("C_resid_noinj", "core_qb"),
    ("C_resid_nopersonnel", "core"),
]


def run(data: pl.DataFrame, folds: list[int], horizons: list[str], specs=None, combined: bool = True,
        combined_specs=None, train_start: int | None = None) -> tuple[pl.DataFrame, dict]:
    cfg = settings()
    core_start = train_start or cfg["seasons"]["core_start"]
    specs = specs if specs is not None else FOOTBALL_SPECS
    cspecs = combined_specs if combined_specs is not None else COMBINED_SPECS
    preds, fold_info = [], []
    for h in horizons:
        dh = data.filter(pl.col("horizon") == h)
        for S in folds:
            train = dh.filter((pl.col("season") >= core_start) & (pl.col("season") < S))
            test = dh.filter(pl.col("season") == S)
            if test.height == 0:
                continue
            info = {"horizon": h, "fold": S, "n_train": train.height, "n_test": test.height, "alphas": {}}
            naive = NaiveHome().fit(train)
            preds.append(_pred_frame(test, naive.predict(test), NaiveHome.name, S, h))
            for name, fs_name, valid in specs:
                if h not in valid:
                    continue
                fs = feature_set(fs_name)
                alpha, _ = select_alpha_chronologically(train, feature_set=fs)
                b = FootballRidge(alpha=alpha, feature_set=fs).fit(train)
                preds.append(_pred_frame(test, b.predict(test), name, S, h))
                info["alphas"][name] = alpha
            if h == "final":
                tr_m = train.filter(pl.col("market_available"))
                te_m = test.filter(pl.col("market_available"))
                info["market_rows_test"] = te_m.height
                preds.append(_pred_frame(te_m, MarketRaw().predict(te_m), MarketRaw.name, S, h))
                cal = MarketCalibrated().fit(tr_m)
                preds.append(_pred_frame(te_m, cal.predict(te_m), MarketCalibrated.name, S, h))
                info["A_cal_params"] = cal.params()
                if combined:
                    for cname, fs_name in cspecs:
                        am, at = select_resid_alphas(tr_m, fs_name)
                        c = ResidualRidge(fs_name, am, at).fit(tr_m)
                        preds.append(_pred_frame(te_m, c.predict(te_m), cname, S, h))
                        info["alphas"][cname] = [am, at]
                        if cname == "C_resid" and combined_specs is None:
                            info["C_resid_top_coefs"] = c.top_coefficients()
                            hgb = ResidualHGB(fs_name, seed=cfg["validation"]["seed"]).fit(tr_m)
                            preds.append(_pred_frame(te_m, hgb.predict(te_m), "C_resid_hgb", S, h))
                            d = DirectRidge(fs_name)
                            a_d, _ = select_alpha_chronologically(DirectRidge.with_market_points(tr_m), feature_set=d.feature_set)
                            d = DirectRidge(fs_name, a_d).fit(tr_m)
                            preds.append(_pred_frame(te_m, d.predict(te_m), "C_direct", S, h))
                            info["alphas"]["C_direct"] = a_d
            fold_info.append(info)
    return pl.concat(preds), {"folds": fold_info}


def period_of(season_expr: pl.Expr, tune_folds: list[int], locked_folds: list[int] | None = None) -> pl.Expr:
    return (pl.when(season_expr.is_in(tune_folds)).then(pl.lit("tune"))
            .when(season_expr.is_in(locked_folds or [])).then(pl.lit("locked"))
            .otherwise(pl.lit("dev")))


def summarise(preds: pl.DataFrame, reps: int, seed: int, tune_folds: list[int] | None = None,
              baselines=("A_market_raw", "B_core", "N_naive_home"), locked_folds: list[int] | None = None) -> dict:
    """Metrics by (period, horizon, model). `tune` seasons were used to make modelling choices; `dev` seasons
    are the walk-forward development report; `locked` is the untouched test. Paired comparisons are within
    period and horizon."""
    tune_folds = tune_folds or []
    preds = preds.with_columns(period=period_of(pl.col("season"), tune_folds, locked_folds))
    out = {"overall": [], "per_season": [], "subgroups": [], "paired": []}
    for (h, m), grp in preds.group_by(["horizon", "model"], maintain_order=True):
        for (per,), gp in grp.group_by(["period"], maintain_order=True):
            out["overall"].append({"period": per, "horizon": h, "model": m, **point_metrics(gp)})
        for (s,), g2 in grp.group_by(["season"], maintain_order=True):
            out["per_season"].append({"horizon": h, "model": m, "season": s, **point_metrics(g2)})
        grp = grp.filter(pl.col("period") == ("locked" if locked_folds else "dev"))
        groups = {
            "weeks_1_4": grp.filter((pl.col("week") <= 4) & ~pl.col("is_playoff")),
            "weeks_5_plus_reg": grp.filter((pl.col("week") > 4) & ~pl.col("is_playoff")),
            "playoffs": grp.filter(pl.col("is_playoff")),
            "neutral_site": grp.filter(pl.col("neutral_site")),
            "expected_qb_changed": grp.filter(pl.col("qb_changed")),
        }
        for name, g2 in groups.items():
            if g2.height:
                r = point_metrics(g2)
                out["subgroups"].append({"horizon": h, "model": m, "group": name,
                                         "exploratory_small_n": g2.height < 100, **r})
    losses = per_game_losses(preds)
    models = preds["model"].unique().to_list()
    for (per, h), lh in losses.group_by(["period", "horizon"], maintain_order=True):
        present = set(lh["model"].unique().to_list())
        for b in baselines:
            if b not in present:
                continue
            for a in sorted(models):
                if a == b or a not in present or (b == "N_naive_home" and a != "B_core"):
                    continue
                la, lb = lh.filter(pl.col("model") == a), lh.filter(pl.col("model") == b)
                for loss in ("ae_margin", "ae_total", "se_margin", "se_total"):
                    out["paired"].append({"period": per, "horizon": h, "a": a, "b": b, "loss": loss,
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
         "", "Periods: `tune` = seasons used to make modelling choices (feature sets, settings); "
         "`dev` = walk-forward development report seasons.", "",
         "## Overall (pooled over folds)", "",
         "| period | horizon | model | n | margin MAE | margin RMSE | total MAE | total RMSE | home MAE | away MAE | winner acc |",
         "|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in sorted(summary["overall"], key=lambda r: (r["period"] != "dev", r["horizon"], r["margin_rmse"])):
        L.append(f"| {r['period']} | {r['horizon']} | {r['model']} | {r['n_games']} | {fmt(r['margin_mae'])} | {fmt(r['margin_rmse'])} | "
                 f"{fmt(r['total_mae'])} | {fmt(r['total_rmse'])} | {fmt(r['home_pts_mae'])} | {fmt(r['away_pts_mae'])} | "
                 f"{fmt(r['winner_accuracy'], 3)} |")
    L += ["", "## Paired differences (model a minus model b; negative = a better)", "",
          "Season-week block bootstrap 95% intervals. Few independent seasons: treat as limited evidence.", "",
          "| period | horizon | a | b | loss | n | mean diff | 95% CI |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(summary["paired"], key=lambda r: (r["period"] != "dev", r["horizon"], r["b"], r["a"])):
        L.append(f"| {r['period']} | {r['horizon']} | {r['a']} | {r['b']} | {r['loss']} | {r['n_games']} | {r['mean_diff']:+.3f} | "
                 f"[{r['ci95'][0]:+.3f}, {r['ci95'][1]:+.3f}] |")
    L += ["", "## Per season", "", "| horizon | model | season | n | margin MAE | total MAE | winner acc |", "|---|---|---|---|---|---|---|"]
    for r in summary["per_season"]:
        L.append(f"| {r['horizon']} | {r['model']} | {r['season']} | {r['n_games']} | {fmt(r['margin_mae'])} | "
                 f"{fmt(r['total_mae'])} | {fmt(r['winner_accuracy'], 3)} |")
    L += ["", "## Subgroups, reported period (dev, or locked when included; prespecified; small groups are exploratory)", "",
          "| horizon | model | group | n | margin MAE | total MAE | exploratory |", "|---|---|---|---|---|---|---|"]
    for r in summary["subgroups"]:
        L.append(f"| {r['horizon']} | {r['model']} | {r['group']} | {r['n_games']} | {fmt(r['margin_mae'])} | "
                 f"{fmt(r['total_mae'])} | {'yes' if r['exploratory_small_n'] else ''} |")
    L += ["", "## Fold details", "", "```json", json.dumps(fold_info, indent=1, default=str), "```"]
    return "\n".join(L)
