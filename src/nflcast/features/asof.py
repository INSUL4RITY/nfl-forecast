"""As-of team features for every (game, forecast horizon).

Leakage rule: a completed game contributes to a forecast only if its data would have been available
before that forecast's cutoff: kickoff_utc + pbp_available_after_kickoff_hours <= cutoff_utc.
This holds for team form, the league means used for shrinkage, and opponent-adjusted ratings.

Team form = exponentially weighted (by games ago) volume-weighted rates, with prior-season games
down-weighted by `season_carryover` per season boundary, shrunk toward the as-of league mean with
provisional pseudo-counts (configurable; to be tuned on chronological folds).
Week 1 works naturally: its features come from prior-season games at carryover weight.
"""

from __future__ import annotations

from datetime import timedelta

import numpy as np
import polars as pl
from sklearn.linear_model import Ridge

from nflcast.config import settings

# (feature name, numerator column, denominator column or None for per-game, shrink pseudo-count in denom units)
METRICS: list[tuple[str, str, str | None, float]] = [
    ("epa_play", "epa_play_sum", "plays", 120.0),
    ("epa_db", "epa_db_sum", "dropbacks", 80.0),
    ("epa_rush", "epa_rush_sum", "rushes", 60.0),
    ("succ_play", "succ_play_sum", "plays", 120.0),
    ("expl_db", "expl_db", "dropbacks", 80.0),
    ("expl_rush", "expl_rush", "rushes", 60.0),
    ("sack_rate", "sacks", "dropbacks", 80.0),
    ("int_rate", "ints", "dropbacks", 150.0),
    ("fum_rate", "fumbles_lost", "plays", 200.0),
    ("neutral_pass", "neutral_db", "neutral_plays", 60.0),
    ("pts_drive", "drive_pts", "drives", 20.0),
    ("rz_td", "rz_tds", "rz_trips", 12.0),
    ("start_fp", "start_yl100_sum", "start_yl100_n", 20.0),
    ("plays_pg", "plays", None, 2.0),
    ("points_pg", "points", None, 2.0),
]
MAX_HISTORY_GAMES = 48
LEAGUE_WINDOW_ROWS = 544  # ~ one season of team-games, used for as-of league means


def team_long(tg: pl.DataFrame) -> pl.DataFrame:
    """One row per (game, team) with offensive sums (off_*) and allowed sums (def_*)."""
    num_cols = sorted({m[1] for m in METRICS} | {m[2] for m in METRICS if m[2]})
    base = tg.select(["game_id", "season", "kickoff_utc", "team", "opp", "is_home", "neutral_site"] + num_cols)
    opp = tg.select(["game_id", pl.col("team").alias("opp")] + [pl.col(c).alias(f"def_{c}") for c in num_cols])
    out = base.rename({c: f"off_{c}" for c in num_cols}).join(opp, on=["game_id", "opp"], how="left")
    return out.sort(["kickoff_utc", "game_id", "team"])


class AsOfFeatureBuilder:
    def __init__(self, tg: pl.DataFrame):
        cfg = settings()
        self.lag = timedelta(hours=cfg["pbp_available_after_kickoff_hours"])
        self.half_life = float(cfg["features"]["half_life_games"])
        self.carry = float(cfg["features"]["season_carryover"])
        self.alpha = float(cfg["features"]["ridge_rating_alpha"])
        long = team_long(tg).with_columns(avail_utc=pl.col("kickoff_utc") + self.lag).sort(["avail_utc", "game_id", "team"])
        self.long = long
        self.avail = long["avail_utc"].dt.epoch("us").to_numpy()
        self.season = long["season"].to_numpy()
        self.team = long["team"].to_numpy()
        self.opp = long["opp"].to_numpy()
        self.venue = np.where(long["neutral_site"].to_numpy(), 0.0, np.where(long["is_home"].to_numpy(), 1.0, -1.0))
        self.teams = sorted(set(self.team.tolist()))
        self.tidx = {t: i for i, t in enumerate(self.teams)}
        # numerators / denominators per side
        self.num, self.den = {}, {}
        for side in ("off", "def"):
            N = np.column_stack([long[f"{side}_{m[1]}"].fill_null(0).to_numpy().astype(float) for m in METRICS])
            D = np.column_stack([
                long[f"{side}_{m[2]}"].fill_null(0).to_numpy().astype(float) if m[2] else np.ones(long.height)
                for m in METRICS])
            self.num[side], self.den[side] = N, D
        self.cum_num = {s: np.vstack([np.zeros(len(METRICS)), np.cumsum(self.num[s], axis=0)]) for s in ("off", "def")}
        self.cum_den = {s: np.vstack([np.zeros(len(METRICS)), np.cumsum(self.den[s], axis=0)]) for s in ("off", "def")}
        self.rows_by_team = {t: np.where(self.team == t)[0] for t in self.teams}
        self._rating_cache: dict[int, dict] = {}

    # ---------- helpers ----------
    def _n_available(self, cutoff_us: int) -> int:
        return int(np.searchsorted(self.avail, cutoff_us, side="right"))

    def _league_mean(self, side: str, n_av: int) -> np.ndarray:
        lo = max(0, n_av - LEAGUE_WINDOW_ROWS)
        num = self.cum_num[side][n_av] - self.cum_num[side][lo]
        den = self.cum_den[side][n_av] - self.cum_den[side][lo]
        with np.errstate(invalid="ignore", divide="ignore"):
            return np.where(den > 0, num / den, np.nan)

    def _ratings(self, n_av: int, season: int) -> dict:
        """Opponent-adjusted ratings from games available at this information state (cached)."""
        key = (n_av, season)
        if key in self._rating_cache:
            return self._rating_cache[key]
        lo = max(0, n_av - 2 * LEAGUE_WINDOW_ROWS)
        idx = np.arange(lo, n_av)
        res = {}
        if len(idx) < 64:
            self._rating_cache[key] = res
            return res
        # weight: exponential decay by position in the available sequence (~16 team-games per week per 32 teams)
        games_ago = (n_av - 1 - idx) / 32.0
        w = 0.5 ** (games_ago / self.half_life) * self.carry ** np.clip(season - self.season[idx], 0, None)
        T = len(self.teams)
        X = np.zeros((len(idx), 2 * T + 1))
        X[np.arange(len(idx)), [self.tidx[t] for t in self.team[idx]]] = 1.0
        X[np.arange(len(idx)), [T + self.tidx[t] for t in self.opp[idx]]] = -1.0
        X[:, -1] = self.venue[idx]
        for name, col in (("epa", 0), ("pts", 14)):  # METRICS[0]=epa_play, METRICS[14]=points_pg
            y = self.num["off"][idx, col] / np.maximum(self.den["off"][idx, col], 1.0)
            sw = w * (self.den["off"][idx, col] if col == 0 else 1.0)
            sw = sw / sw.mean()
            m = Ridge(alpha=self.alpha, fit_intercept=True).fit(X, y, sample_weight=sw)
            res[name] = (m.coef_[:T], m.coef_[T:2 * T], float(m.coef_[-1]))
        self._rating_cache[key] = res
        return res

    # ---------- main ----------
    def team_features(self, team: str, cutoff_us: int, season: int) -> dict:
        n_av = self._n_available(cutoff_us)
        rows = self.rows_by_team.get(team, np.array([], dtype=int))
        rows = rows[rows < n_av][-MAX_HISTORY_GAMES:]
        out: dict[str, float] = {}
        k = np.arange(len(rows))[::-1]  # 0 = most recent
        seasons_back = np.clip(season - self.season[rows], 0, None) if len(rows) else np.array([])
        w = 0.5 ** (k / self.half_life) * self.carry ** seasons_back if len(rows) else np.array([])
        out["games_hist"] = float(len(rows))
        out["games_this_season"] = float((self.season[rows] == season).sum()) if len(rows) else 0.0
        out["ess_games"] = float(w.sum() ** 2 / (w ** 2).sum()) if len(rows) else 0.0
        for side in ("off", "def"):
            mu = self._league_mean(side, n_av)
            for j, (name, _, _, m) in enumerate(METRICS):
                if len(rows):
                    wn = float((w * self.num[side][rows, j]).sum())
                    wd = float((w * self.den[side][rows, j]).sum())
                else:
                    wn = wd = 0.0
                prior = mu[j] if np.isfinite(mu[j]) else 0.0
                out[f"{side}_{name}"] = (wn + m * prior) / (wd + m)
        rt = self._ratings(n_av, season)
        ti = self.tidx.get(team)
        for name in ("epa", "pts"):
            if name in rt and ti is not None:
                o, d, _ = rt[name]
                out[f"adj_off_{name}"] = float(o[ti])
                out[f"adj_def_{name}"] = float(d[ti])  # positive = suppresses opponent offence
            else:
                out[f"adj_off_{name}"] = 0.0
                out[f"adj_def_{name}"] = 0.0
        return out


def forecast_cutoffs(games: pl.DataFrame, seasons: list[int]) -> pl.DataFrame:
    """One row per (game, horizon) with the release cutoff time."""
    hz = settings()["horizons"]
    g = games.filter(pl.col("season").is_in(seasons))
    frames = [g.select("game_id", pl.lit(h).alias("horizon"),
                       (pl.col("kickoff_utc") - pl.duration(hours=hours)).alias("cutoff_utc"))
              for h, hours in hz.items()]
    return pl.concat(frames).sort(["cutoff_utc", "game_id"])


def build_feature_snapshots(games: pl.DataFrame, tg: pl.DataFrame, seasons: list[int]) -> pl.DataFrame:
    """feature_snapshots: game_id x horizon, home_* / away_* team features and context (no outcomes)."""
    b = AsOfFeatureBuilder(tg)
    cuts = forecast_cutoffs(games, seasons).join(
        games.select("game_id", "season", "week", "home_id", "away_id", "neutral_site", "is_playoff", "div_game",
                     "home_rest", "away_rest", "kickoff_utc"), on="game_id")
    recs = []
    for r in cuts.iter_rows(named=True):
        c_us = int(r["cutoff_utc"].timestamp() * 1_000_000)
        hf = b.team_features(r["home_id"], c_us, r["season"])
        af = b.team_features(r["away_id"], c_us, r["season"])
        rec = {"game_id": r["game_id"], "horizon": r["horizon"], "cutoff_utc": r["cutoff_utc"]}
        rec.update({f"home_{k}": v for k, v in hf.items()})
        rec.update({f"away_{k}": v for k, v in af.items()})
        recs.append(rec)
    feats = pl.DataFrame(recs)
    ctx = cuts.select("game_id", "horizon", "season", "week", "home_id", "away_id", "neutral_site", "is_playoff",
                      "div_game", (pl.col("home_rest") - pl.col("away_rest")).alias("rest_diff"))
    return ctx.join(feats, on=["game_id", "horizon"], how="left").with_columns(
        feature_version=pl.lit("core_v1"))
