"""Walk-forward evaluation of outcome probabilities and prediction intervals.

For each test season S, the probability and interval models are fitted on the out-of-fold point
predictions of the same model for seasons < S (never on S), then scored on S.
"""

from __future__ import annotations

import numpy as np
import polars as pl

from nflcast.evaluation.metrics import block_bootstrap_diff
from nflcast.models.probability import (IntervalModel, OutcomeModel, calibration_table, interval_scores,
                                        outcome_scores)

PROB_MODELS = [("final", "C_resid_noinj"), ("final", "A_market_raw"), ("final", "B_qb"), ("early", "B_qb")]


def evaluate(preds: pl.DataFrame, games: pl.DataFrame, tune_folds: list[int], levels=(0.8, 0.95),
             reps: int = 2000, seed: int = 0, locked_folds: list[int] | None = None) -> dict:
    out = {"outcome": [], "calibration": [], "intervals": [], "paired_logloss": [], "per_game": []}
    per_game = []
    for h, model in PROB_MODELS:
        p = preds.filter((pl.col("horizon") == h) & (pl.col("model") == model)).sort("season")
        seasons = sorted(p["season"].unique().to_list())
        for S in seasons[1:]:
            oof, te = p.filter(pl.col("season") < S), p.filter(pl.col("season") == S)
            om = OutcomeModel().fit(oof, games)
            pr = om.predict(te["pred_margin"].to_numpy(), te["is_playoff"].to_numpy())
            margin = te["margin"].to_numpy()
            p_obs = np.where(margin > 0, pr["p_home"], np.where(margin < 0, pr["p_away"], pr["p_tie"]))
            g = te.select("game_id", "season", "week", "margin", "total_points", "pred_margin", "pred_total").with_columns(
                horizon=pl.lit(h), model=pl.lit(model), p_home=pl.Series(pr["p_home"]), p_away=pl.Series(pr["p_away"]),
                p_tie=pl.Series(pr["p_tie"]), ll=pl.Series(-np.log(np.clip(p_obs, 1e-12, 1))))
            for method in ("residual", "quantile"):
                for tgt, pcol, acol in (("margin", "pred_margin", "margin"), ("total", "pred_total", "total_points")):
                    im = IntervalModel(method, levels).fit(oof[pcol].to_numpy(), oof[acol].to_numpy())
                    for lv, (lo, hi) in im.predict(te[pcol].to_numpy()).items():
                        g = g.with_columns(pl.Series(f"{tgt}_{method}_{int(lv*100)}_lo", lo),
                                           pl.Series(f"{tgt}_{method}_{int(lv*100)}_hi", hi))
            per_game.append(g)
    from nflcast.evaluation.backtest import period_of
    pg = pl.concat(per_game, how="diagonal_relaxed").with_columns(
        period=period_of(pl.col("season"), tune_folds, locked_folds))
    cal_period = "locked" if locked_folds else "dev"
    for (per, h, m), g in pg.group_by(["period", "horizon", "model"], maintain_order=True):
        s = outcome_scores(g["p_home"].to_numpy(), g["p_away"].to_numpy(), g["p_tie"].to_numpy(), g["margin"].to_numpy())
        out["outcome"].append({"period": per, "horizon": h, "model": m, **s})
        if per == cal_period:
            out["calibration"].append({"horizon": h, "model": m,
                                       "table": calibration_table(g["p_home"].to_numpy(), g["margin"].to_numpy())})
        for method in ("residual", "quantile"):
            for tgt, acol in (("margin", "margin"), ("total", "total_points")):
                for lv in levels:
                    k = f"{tgt}_{method}_{int(lv*100)}"
                    sc = interval_scores(g[f"{k}_lo"].to_numpy(), g[f"{k}_hi"].to_numpy(), g[acol].to_numpy())
                    out["intervals"].append({"period": per, "horizon": h, "model": m, "target": tgt, "method": method,
                                             "level": lv, **sc})
    for (per,), g in pg.filter(pl.col("horizon") == "final").group_by(["period"]):
        for a, b in (("C_resid_noinj", "A_market_raw"), ("B_qb", "A_market_raw"), ("C_resid_noinj", "B_qb")):
            la, lb = g.filter(pl.col("model") == a), g.filter(pl.col("model") == b)
            out["paired_logloss"].append({"period": per, "a": a, "b": b, **block_bootstrap_diff(la, lb, "ll", reps, seed)})
    out["per_game_frame"] = pg
    return out


def to_markdown(res: dict) -> str:
    L = ["", "## Outcome probabilities (walk-forward; calibrated on earlier seasons' out-of-fold predictions)", "",
         "Tie probability = smoothed regular-season tie rate since 2017 (as of the training seasons); 0 in playoffs.", "",
         "| period | horizon | model | n | ties | log loss | Brier (3-class) | Brier (home win) |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(res["outcome"], key=lambda r: (r["period"] != "dev", r["horizon"], r["log_loss"])):
        L.append(f"| {r['period']} | {r['horizon']} | {r['model']} | {r['n']} | {r['n_ties']} | {r['log_loss']:.4f} | "
                 f"{r['brier_3class']:.4f} | {r['brier_home_win']:.4f} |")
    L += ["", "Paired log-loss differences (a − b; negative = a better), season-week block bootstrap:", "",
          "| period | a | b | n | mean diff | 95% CI |", "|---|---|---|---|---|---|"]
    for r in res["paired_logloss"]:
        L.append(f"| {r['period']} | {r['a']} | {r['b']} | {r['n_games']} | {r['mean_diff']:+.4f} | "
                 f"[{r['ci95'][0]:+.4f}, {r['ci95'][1]:+.4f}] |")
    L += ["", "### Calibration (latest reported period, P(home win) bins, with counts)", ""]
    for c in res["calibration"]:
        L += [f"**{c['horizon']} / {c['model']}**", "", "| bin | n | mean predicted | observed home-win rate |", "|---|---|---|---|"]
        for b in c["table"]:
            L.append(f"| {b['bin_lo']:.1f}–{b['bin_hi']:.1f} | {b['n']} | {b['mean_pred']:.3f} | {b['obs_home_win']:.3f} |")
        L.append("")
    L += ["## Prediction intervals (coverage should be close to the nominal level)", "",
          "| period | horizon | model | target | method | level | coverage | mean width |", "|---|---|---|---|---|---|---|---|"]
    for r in sorted(res["intervals"], key=lambda r: (r["period"] != "dev", r["horizon"], r["model"], r["target"], r["method"], r["level"])):
        L.append(f"| {r['period']} | {r['horizon']} | {r['model']} | {r['target']} | {r['method']} | {r['level']:.2f} | "
                 f"{r['coverage']:.3f} | {r['mean_width']:.1f} |")
    return "\n".join(L)
