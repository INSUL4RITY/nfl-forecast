"""Benchmark and baseline point-forecast models.

All models return expected home/away points; margin and total are derived as M = H - A, T = H + A
at full precision. The same non-negativity policy (`coherent`) is applied in backtests and releases.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.linear_model import LinearRegression, Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nflcast.data.policy import assert_no_banned
from nflcast.features.asof import METRICS

MIN_EXPECTED_POINTS = 0.0


def coherent(M: np.ndarray, T: np.ndarray) -> dict[str, np.ndarray]:
    """Recover team scores from margin/total; project onto the feasible set H, A >= 0.

    If a projection is needed (never observed so far in practice), the total is kept and the margin is
    clipped to |M| <= T, which is the nearest feasible point along the margin axis. Flags are returned.
    """
    T = np.maximum(T, 2 * MIN_EXPECTED_POINTS)
    Mc = np.clip(M, -T, T)
    H = (T + Mc) / 2
    A = (T - Mc) / 2
    return {"home_pts": H, "away_pts": A, "margin": H - A, "total": H + A, "projected": Mc != M}


# ---------------- Model A: market only ----------------
class MarketRaw:
    name = "A_market_raw"

    def fit(self, df: pl.DataFrame) -> "MarketRaw":
        return self

    def predict(self, df: pl.DataFrame) -> dict[str, np.ndarray]:
        M0 = -df["home_spread"].to_numpy().astype(float)
        T0 = df["total"].to_numpy().astype(float)
        return coherent(M0, T0)


class MarketCalibrated:
    """Affine correction of the quoted lines learned from earlier seasons only."""
    name = "A_market_cal"

    def fit(self, df: pl.DataFrame) -> "MarketCalibrated":
        M0 = -df["home_spread"].to_numpy().reshape(-1, 1)
        T0 = df["total"].to_numpy().reshape(-1, 1)
        self.m = LinearRegression().fit(M0, df["margin"].to_numpy())
        self.t = LinearRegression().fit(T0, df["total_points"].to_numpy())
        return self

    def predict(self, df: pl.DataFrame) -> dict[str, np.ndarray]:
        M = self.m.predict(-df["home_spread"].to_numpy().reshape(-1, 1))
        T = self.t.predict(df["total"].to_numpy().reshape(-1, 1))
        return coherent(M, T)

    def params(self) -> dict:
        return {"margin_intercept": float(self.m.intercept_), "margin_slope": float(self.m.coef_[0]),
                "total_intercept": float(self.t.intercept_), "total_slope": float(self.t.coef_[0])}


# ---------------- Naive floor ----------------
class NaiveHome:
    """Training-period average home and away points (non-neutral), half-split for neutral sites."""
    name = "N_naive_home"

    def fit(self, df: pl.DataFrame) -> "NaiveHome":
        nn = df.filter(~pl.col("neutral_site"))
        self.h = float(nn["home_score"].mean())
        self.a = float(nn["away_score"].mean())
        return self

    def predict(self, df: pl.DataFrame) -> dict[str, np.ndarray]:
        neu = df["neutral_site"].to_numpy()
        H = np.where(neu, (self.h + self.a) / 2, self.h)
        A = np.where(neu, (self.h + self.a) / 2, self.a)
        return coherent(H - A, H + A)


# ---------------- Model B: football-only ----------------
TEAM_FEATS = [f"off_{m[0]}" for m in METRICS] + ["adj_off_epa", "adj_off_pts"]
OPP_FEATS = [f"def_{m[0]}" for m in METRICS] + ["adj_def_epa", "adj_def_pts"]
CONTEXT = ["venue", "rest_adv", "is_playoff", "own_games_this_season", "opp_games_this_season"]


def stack_team_rows(df: pl.DataFrame, feature_set: dict | None = None) -> tuple[np.ndarray, list[str]]:
    """Two rows per game: (home offence vs away defence) then (away offence vs home defence)."""
    fs = feature_set or {}
    team_feats = fs.get("team", TEAM_FEATS)
    opp_feats = fs.get("opp", OPP_FEATS)
    ctx = fs.get("context", CONTEXT)
    neu = df["neutral_site"].to_numpy().astype(bool)

    def side(me: str, them: str, venue_sign: float) -> np.ndarray:
        cols = [df[f"{me}_{f}"].to_numpy() for f in team_feats] + [df[f"{them}_{f}"].to_numpy() for f in opp_feats]
        cmap = {
            "venue": np.where(neu, 0.0, venue_sign),
            "rest_adv": venue_sign * df["rest_diff"].fill_null(0).to_numpy(),
            "is_playoff": df["is_playoff"].to_numpy().astype(float),
            "own_games_this_season": df[f"{me}_games_this_season"].to_numpy(),
            "opp_games_this_season": df[f"{them}_games_this_season"].to_numpy(),
        }
        cols += [cmap[c] for c in ctx]
        return np.column_stack(cols).astype(float)

    names = [f"team_{f}" for f in team_feats] + [f"opp_{f}" for f in opp_feats] + list(ctx)
    X = np.vstack([side("home", "away", 1.0), side("away", "home", -1.0)])
    assert_no_banned(names, context="Model B features")
    return X, names


class FootballRidge:
    name = "B_football_ridge"

    def __init__(self, alpha: float = 10.0, feature_set: dict | None = None):
        self.alpha = alpha
        self.feature_set = feature_set

    def fit(self, df: pl.DataFrame) -> "FootballRidge":
        X, self.names = stack_team_rows(df, self.feature_set)
        y = np.concatenate([df["home_score"].to_numpy(), df["away_score"].to_numpy()]).astype(float)
        self.pipe = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha)).fit(X, y)
        return self

    def predict(self, df: pl.DataFrame) -> dict[str, np.ndarray]:
        X, _ = stack_team_rows(df, self.feature_set)
        p = self.pipe.predict(X)
        n = df.height
        H, A = p[:n], p[n:]
        return coherent(H - A, H + A)

    def coefficients(self) -> dict[str, float]:
        r = self.pipe[-1]
        return dict(zip(self.names, map(float, r.coef_)))


def select_alpha_chronologically(train: pl.DataFrame, grid=(1, 3, 10, 30, 100, 300, 1000, 3000, 10000, 30000), feature_set=None) -> tuple[float, dict]:
    """Choose ridge alpha on the LAST training season, fitting on the earlier training seasons only."""
    last = train["season"].max()
    inner_tr, inner_va = train.filter(pl.col("season") < last), train.filter(pl.col("season") == last)
    scores = {}
    for a in grid:
        m = FootballRidge(alpha=a, feature_set=feature_set).fit(inner_tr)
        p = m.predict(inner_va)
        err = np.concatenate([p["home_pts"] - inner_va["home_score"].to_numpy(), p["away_pts"] - inner_va["away_score"].to_numpy()])
        scores[a] = float(np.sqrt(np.mean(err ** 2)))
    best = min(scores, key=scores.get)
    return float(best), scores
