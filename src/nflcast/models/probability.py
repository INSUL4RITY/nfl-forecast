"""Milestone 5: outcome probabilities and prediction intervals on top of point forecasts.

Outcome model (regular season):
    P(tie)                = as-of base rate of regular-season ties since the 2017 overtime rule change
                            (constant; ties are too rare, ~0.3%, to model conditionally with any reliability)
    P(home win | no tie)  = logistic(a + b * predicted_margin), fitted on OUT-OF-FOLD predictions
                            from earlier seasons only
    P(home) = (1 - P(tie)) * p,  P(away) = (1 - P(tie)) * (1 - p)
Playoffs: P(tie) = 0 and the no-tie probabilities are used directly.

Intervals for margin and total:
    "residual":  predicted value + empirical quantiles of earlier out-of-fold residuals
    "quantile":  linear quantile regression of the residual on the predicted value (heteroscedasticity)
Both are calibrated on earlier seasons only and scored on later seasons for coverage and width.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LogisticRegression, QuantileRegressor

TIE_RULE_START = 2017


class OutcomeModel:
    def fit(self, oof: pl.DataFrame, games: pl.DataFrame) -> "OutcomeModel":
        """oof: pred_margin + margin for earlier seasons (one row per game)."""
        dec = oof.filter(pl.col("margin") != 0)
        X = dec["pred_margin"].to_numpy().reshape(-1, 1)
        y = (dec["margin"].to_numpy() > 0).astype(int)
        self.lr = LogisticRegression(C=1e4).fit(X, y)
        max_season = int(oof["season"].max())
        reg = games.filter((pl.col("game_type") == "REG") & (pl.col("status") == "final")
                           & (pl.col("season") >= TIE_RULE_START) & (pl.col("season") <= max_season))
        ties, n = int((reg["margin"] == 0).sum()), reg.height
        self.p_tie = (ties + 0.5) / (n + 1.0)  # Jeffreys-style smoothing
        self.tie_counts = {"ties": ties, "games": n, "through_season": max_season}
        return self

    def predict(self, pred_margin: np.ndarray, is_playoff: np.ndarray) -> dict[str, np.ndarray]:
        p = self.lr.predict_proba(np.asarray(pred_margin, float).reshape(-1, 1))[:, 1]
        pt = np.where(is_playoff, 0.0, self.p_tie)
        return {"p_home": (1 - pt) * p, "p_away": (1 - pt) * (1 - p), "p_tie": pt}

    def params(self) -> dict:
        return {"intercept": float(self.lr.intercept_[0]), "slope": float(self.lr.coef_[0, 0]),
                "p_tie_regular_season": self.p_tie, **self.tie_counts}


class IntervalModel:
    def __init__(self, method: str = "residual", levels=(0.8, 0.95)):
        self.method, self.levels = method, tuple(levels)

    def fit(self, pred: np.ndarray, actual: np.ndarray) -> "IntervalModel":
        r = actual - pred
        self.q = {}
        for lv in self.levels:
            lo, hi = (1 - lv) / 2, 1 - (1 - lv) / 2
            if self.method == "residual":
                self.q[lv] = (float(np.quantile(r, lo)), float(np.quantile(r, hi)))
            else:
                X = pred.reshape(-1, 1)
                self.q[lv] = tuple(QuantileRegressor(quantile=qq, alpha=0.0, solver="highs").fit(X, r) for qq in (lo, hi))
        return self

    def predict(self, pred: np.ndarray) -> dict[float, tuple[np.ndarray, np.ndarray]]:
        out = {}
        for lv, (a, b) in self.q.items():
            if self.method == "residual":
                out[lv] = (pred + a, pred + b)
            else:
                X = pred.reshape(-1, 1)
                lo, hi = pred + a.predict(X), pred + b.predict(X)
                out[lv] = (np.minimum(lo, hi), np.maximum(lo, hi))  # enforce valid ordering
        return out


# ------------------------------------------------------------------ scoring
def outcome_scores(p_home, p_away, p_tie, margin) -> dict:
    y_h, y_a, y_t = (margin > 0).astype(float), (margin < 0).astype(float), (margin == 0).astype(float)
    eps = 1e-12
    p_obs = np.where(y_h == 1, p_home, np.where(y_a == 1, p_away, p_tie))
    return {
        "log_loss": float(-np.mean(np.log(np.clip(p_obs, eps, 1)))),
        "brier_3class": float(np.mean((p_home - y_h) ** 2 + (p_away - y_a) ** 2 + (p_tie - y_t) ** 2)),
        "brier_home_win": float(np.mean((p_home - y_h) ** 2)),
        "n": int(len(margin)), "n_ties": int(y_t.sum()),
    }


def calibration_table(p_home, margin, bins: int = 10) -> list[dict]:
    edges = np.linspace(0, 1, bins + 1)
    idx = np.clip(np.digitize(p_home, edges) - 1, 0, bins - 1)
    rows = []
    for b in range(bins):
        m = idx == b
        if m.sum() == 0:
            continue
        rows.append({"bin_lo": float(edges[b]), "bin_hi": float(edges[b + 1]), "n": int(m.sum()),
                     "mean_pred": float(p_home[m].mean()), "obs_home_win": float((margin[m] > 0).mean())})
    return rows


def interval_scores(lo, hi, actual) -> dict:
    return {"coverage": float(np.mean((actual >= lo) & (actual <= hi))), "mean_width": float(np.mean(hi - lo))}
