"""Milestone 4: combined market + football models (Model C).

C_resid (residual-to-market):   M_hat = M0 + g_M(X, M0, T0),  T_hat = T0 + g_T(X, M0, T0)
    g_M, g_T are ridge regressions on game-level features, trained on (M - M0) and (T - T0).
    Heavy regularisation shrinks g toward 0, i.e. toward the market benchmark.
C_resid_hgb: the same residual targets with a constrained histogram gradient boosting model
    (sklearn), no internal random validation split (early_stopping disabled).
C_direct: the stacked team-row football ridge with the market-implied own/opponent points added
    as features (a direct prediction rather than a residual).

Only home_spread and total enter as market numbers. Everything is fitted on training seasons only;
alpha is chosen on later training seasons (chronological), never on the test season.
"""

from __future__ import annotations

import numpy as np
import polars as pl
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from nflcast.data.policy import assert_no_banned
from nflcast.models.core import FootballRidge, coherent, feature_set

GRID = (10, 30, 100, 300, 1000, 3000, 10000, 30000, 100000)


def game_matrix(df: pl.DataFrame, fs: dict, with_market: bool = True) -> tuple[np.ndarray, list[str]]:
    """Game-level design: home/away versions of team and opponent-facing features + context + market."""
    cols, names = [], []
    for f in fs["team"]:
        for side in ("home", "away"):
            cols.append(df[f"{side}_{f}"].to_numpy()); names.append(f"{side}_{f}")
    for f in fs["opp"]:
        for side in ("home", "away"):
            name = f"{side}_{f}"
            if name not in names:
                cols.append(df[name].to_numpy()); names.append(name)
    neu = df["neutral_site"].to_numpy().astype(float)
    cols += [1.0 - neu, df["rest_diff"].fill_null(0).to_numpy(), df["is_playoff"].to_numpy().astype(float)]
    names += ["home_field", "rest_diff", "is_playoff"]
    if "dome" in fs.get("context", []):
        cols.append(df["dome"].to_numpy().astype(float)); names.append("dome")
    if with_market:
        cols += [-df["home_spread"].to_numpy(), df["total"].to_numpy()]
        names += ["market_margin", "market_total"]
    assert_no_banned(names, context="Model C features")
    return np.column_stack(cols).astype(float), names


class ResidualRidge:
    name = "C_resid"

    def __init__(self, fs_name: str, alpha_m: float = 1000.0, alpha_t: float = 1000.0):
        self.fs = feature_set(fs_name)
        self.alpha_m, self.alpha_t = alpha_m, alpha_t

    def fit(self, df: pl.DataFrame) -> "ResidualRidge":
        X, self.names = game_matrix(df, self.fs)
        M0, T0 = -df["home_spread"].to_numpy(), df["total"].to_numpy()
        self.gm = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha_m)).fit(X, df["margin"].to_numpy() - M0)
        self.gt = make_pipeline(StandardScaler(), Ridge(alpha=self.alpha_t)).fit(X, df["total_points"].to_numpy() - T0)
        return self

    def predict(self, df: pl.DataFrame) -> dict[str, np.ndarray]:
        X, _ = game_matrix(df, self.fs)
        M0, T0 = -df["home_spread"].to_numpy(), df["total"].to_numpy()
        return coherent(M0 + self.gm.predict(X), T0 + self.gt.predict(X))

    def top_coefficients(self, k: int = 8) -> dict:
        out = {}
        for tgt, p in (("margin", self.gm), ("total", self.gt)):
            c = p[-1].coef_
            idx = np.argsort(-np.abs(c))[:k]
            out[tgt] = [(self.names[i], float(c[i])) for i in idx]
        return out


class ResidualHGB:
    name = "C_resid_hgb"

    def __init__(self, fs_name: str, seed: int = 0):
        self.fs = feature_set(fs_name)
        self.seed = seed

    def _model(self):
        return HistGradientBoostingRegressor(max_depth=3, learning_rate=0.03, max_iter=150, min_samples_leaf=80,
                                             l2_regularization=10.0, early_stopping=False, random_state=self.seed)

    def fit(self, df: pl.DataFrame) -> "ResidualHGB":
        X, _ = game_matrix(df, self.fs)
        M0, T0 = -df["home_spread"].to_numpy(), df["total"].to_numpy()
        self.gm = self._model().fit(X, df["margin"].to_numpy() - M0)
        self.gt = self._model().fit(X, df["total_points"].to_numpy() - T0)
        return self

    def predict(self, df: pl.DataFrame) -> dict[str, np.ndarray]:
        X, _ = game_matrix(df, self.fs)
        M0, T0 = -df["home_spread"].to_numpy(), df["total"].to_numpy()
        return coherent(M0 + self.gm.predict(X), T0 + self.gt.predict(X))


def select_resid_alphas(train: pl.DataFrame, fs_name: str, n_val: int = 2) -> tuple[float, float]:
    seasons = sorted(train["season"].unique().to_list())
    vals = seasons[-n_val:] if len(seasons) > n_val else seasons[-1:]
    sm, st = {}, {}
    for a in GRID:
        em, et = [], []
        for vs in vals:
            tr, va = train.filter(pl.col("season") < vs), train.filter(pl.col("season") == vs)
            if tr.height == 0:
                continue
            p = ResidualRidge(fs_name, a, a).fit(tr).predict(va)
            em.append(np.sqrt(np.mean((p["margin"] - va["margin"].to_numpy()) ** 2)))
            et.append(np.sqrt(np.mean((p["total"] - va["total_points"].to_numpy()) ** 2)))
        sm[a], st[a] = float(np.mean(em)), float(np.mean(et))
    return float(min(sm, key=sm.get)), float(min(st, key=st.get))


# ---- direct formulation: football ridge + market-implied points as team-row features
class DirectRidge(FootballRidge):
    name = "C_direct"

    def __init__(self, fs_name: str, alpha: float = 100.0):
        fs = feature_set(fs_name)
        fs = {"team": fs["team"] + ["mkt_pts"], "opp": fs["opp"] + ["mkt_pts"], "context": fs["context"]}
        super().__init__(alpha=alpha, feature_set=fs)

    @staticmethod
    def with_market_points(df: pl.DataFrame) -> pl.DataFrame:
        M0, T0 = -pl.col("home_spread"), pl.col("total")
        return df.with_columns(home_mkt_pts=(T0 + M0) / 2, away_mkt_pts=(T0 - M0) / 2)

    def fit(self, df):
        return super().fit(self.with_market_points(df))

    def predict(self, df):
        return super().predict(self.with_market_points(df))
