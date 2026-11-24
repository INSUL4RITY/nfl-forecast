"""What does each headline edge predict: the margin, the total points, or only that unit's own result? Backtest on 2021-25.

Rules fixed before the run (24 Nov 2026, after CIN at WAS, where the largest edge on the page, CIN passing, came true as
a unit result while CIN lost 22-20):

Inputs are the pre-game matchup predictions of backtest_matchups.predictions (each season, cut weeks 4-16, predicting
week W + 1 from weeks 1..W), calibrated exactly as the page calibrates them (matchup_calibration.json). For a team's
offence against the opponent's defence, f = the edge score on the page in the offence's favour (pressure sign-flipped).
For each game: base_net = f(home, EPA per play) - f(away, EPA per play), the overall efficiency gap; base_sum = their sum.
  * margin:  home margin ~ home-field + base_net + (f_home,m - f_away,m)
  * total:   total points ~ season + base_sum + (f_home,m + f_away,m)
  * points:  a team's points ~ its own f(EPA per play) + its f_m
An edge predicts the margin (or the total, or that team's points) when the 95% bootstrap interval (games resampled) of
its coefficient lies above zero, i.e. it adds to what the overall efficiency gap already says. Leave-one-season-out
error with and without the edge is reported alongside.

Flag "one-dimensional favourite": the favourite by the overall efficiency gap (expected margin of 5+ points from
the margin model without the measure, fitted out of sample by season) whose own season-to-date EPA per designed rush
ranks in the bottom five. It is shown on the page only if favourites like that fell short of the expected margin by
more than other 5+ point favourites, with the 95% interval of the difference below zero.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_edge_targets.py --write
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import backtest_matchups as bm  # noqa: E402
import compute as cp  # noqa: E402

OUT = HERE / "edge_targets.json"
CACHE = HERE.parents[1] / "data" / "cache" / "team_analytics" / "matchup_predictions_2021_25.parquet"
SIGN = {"pressure": -1}
MEASURES = ["epa_db", "epa_rush", "pressure", "expl_pass", "expl_run"]
FAV_MIN = 5.0
BOTTOM = 5
B = 500


def ols(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    return np.linalg.lstsq(X, y, rcond=None)[0]


def game_frame(R: pd.DataFrame) -> pd.DataFrame:
    C = json.loads(bm.CAL_FILE.read_text(encoding="utf-8"))
    R = R[R.metric.isin(MEASURES + ["epa_play"])].copy()
    R["f"] = R.z * [C["factor"][m][str(int(w))] for m, w in zip(R.metric, R.W)] * R.metric.map(SIGN).fillna(1)
    wide = R.pivot_table(index=["season", "W", "game_id", "posteam", "defteam"], columns="metric", values="f").reset_index()
    sch = cp.fetch("schedules/games.parquet")
    sch = sch[sch.game_id.isin(wide.game_id)].set_index("game_id")
    wide["home"] = wide.game_id.map(sch.home_team)
    h = wide[wide.posteam == wide.home].set_index("game_id")
    a = wide[wide.posteam != wide.home].set_index("game_id")
    ids = h.index.intersection(a.index)
    h, a, s = h.loc[ids], a.loc[ids], sch.loc[ids]
    G = pd.DataFrame({"season": h.season, "W": h.W, "home": h.posteam, "away": a.posteam,
                      "hfa": (s.location != "Neutral").astype(float), "margin": s.home_score - s.away_score,
                      "total": s.home_score + s.away_score, "pts_h": s.home_score, "pts_a": s.away_score,
                      "base_net": h.epa_play - a.epa_play, "base_sum": h.epa_play + a.epa_play,
                      "base_h": h.epa_play, "base_a": a.epa_play}, index=ids)
    for m in MEASURES:
        G[f"h_{m}"], G[f"a_{m}"] = h[m], a[m]
    return G.dropna(subset=["margin", "base_net"]).reset_index()


def design(G: pd.DataFrame, target: str, m: str | None) -> tuple[np.ndarray, np.ndarray]:
    if target == "margin":
        cols = [G.hfa.values, G.base_net.values] + ([(G[f"h_{m}"] - G[f"a_{m}"]).values] if m else [])
        return np.column_stack(cols), G.margin.values
    if target == "total":
        seas = [(G.season == s).astype(float).values for s in sorted(G.season.unique())]
        cols = seas + [G.base_sum.values] + ([(G[f"h_{m}"] + G[f"a_{m}"]).values] if m else [])
        return np.column_stack(cols), G.total.values
    # points: one row per team-game
    X = np.column_stack([np.ones(2 * len(G)), np.r_[G.hfa.values, np.zeros(len(G))], np.r_[G.base_h.values, G.base_a.values]]
                        + ([np.r_[G[f"h_{m}"].values, G[f"a_{m}"].values]] if m else []))
    return X, np.r_[G.pts_h.values, G.pts_a.values]


def test(G: pd.DataFrame, target: str, m: str, rng) -> dict:
    g = G.dropna(subset=[f"h_{m}", f"a_{m}"]).reset_index(drop=True)
    X, y = design(g, target, m)
    coef = float(ols(X, y)[-1])
    boots = []
    for _ in range(B):
        i = rng.integers(0, len(g), len(g))
        Xb, yb = design(g.iloc[i].reset_index(drop=True), target, m)
        boots.append(ols(Xb, yb)[-1])
    lo, hi = np.percentile(boots, [2.5, 97.5])
    err = {True: [], False: []}
    for s in sorted(g.season.unique()):
        tr, te = g[g.season != s], g[g.season == s]
        for flag in (True, False):
            Xtr, ytr = design(tr, target, m if flag else None)
            Xte, yte = design(te, target, m if flag else None)
            if target == "total":          # the season effect of a held-out season is not known: use the mean of the others
                k = tr.season.nunique()
                b = ols(Xtr, ytr)
                pred = b[:k].mean() + Xte[:, -(2 if flag else 1):] @ b[k:]
            else:
                pred = Xte @ ols(Xtr, ytr)
            err[flag].append(np.abs(yte - pred))
    sd = float(np.std(X[:, -1]))
    return {"coef_per_unit": round(coef, 3), "ci": [round(float(lo), 3), round(float(hi), 3)], "points_per_sd": round(coef * sd, 2),
            "games": int(len(g)), "oos_mae_with": round(float(np.concatenate(err[True]).mean()), 3),
            "oos_mae_without": round(float(np.concatenate(err[False]).mean()), 3), "passes": bool(lo > 0)}


def run_rank(seasons) -> pd.DataFrame:
    """Each team's season-to-date raw EPA per designed rush through each cut week, ranked (1 = best)."""
    out = []
    for S in seasons:
        P = cp.add_unit_flags(cp.load_pbp(S))
        x = P[P.drush.astype(bool) & P.epa.notna()]
        for W in bm.WEEKS:
            r = x[x.week <= W].groupby("posteam").epa.mean()
            out.append(pd.DataFrame({"season": S, "W": W, "team": r.index, "run_rank": r.rank(ascending=False).values, "n_teams": len(r)}))
    return pd.concat(out, ignore_index=True)


def favourite_flag(G: pd.DataFrame, rng) -> dict:
    pred = pd.Series(np.nan, index=G.index)
    for s in sorted(G.season.unique()):
        tr, te = G.season != s, G.season == s
        X, y = design(G[tr], "margin", None)
        Xt, _ = design(G[te], "margin", None)
        pred[te] = Xt @ ols(X, y)
    RR = run_rank(sorted(G.season.unique())).set_index(["season", "W", "team"]).run_rank
    fav_home = pred >= 0
    F = pd.DataFrame({"season": G.season, "W": G.W, "fav": np.where(fav_home, G.home, G.away), "exp": pred.abs(),
                      "act": np.where(fav_home, G.margin, -G.margin)})
    F = F[F.exp >= FAV_MIN].copy()
    F["run_rank"] = [RR.get((s, w, t), np.nan) for s, w, t in zip(F.season, F.W, F.fav)]
    F["flag"] = F.run_rank > 32 - BOTTOM
    F["resid"] = F.act - F.exp
    a, b = F[F.flag].resid.values, F[~F.flag].resid.values
    d = a.mean() - b.mean()
    boots = [rng.choice(a, len(a)).mean() - rng.choice(b, len(b)).mean() for _ in range(2000)]
    lo, hi = np.percentile(boots, [2.5, 97.5])
    win = lambda x: float((x.act > 0).mean())   # noqa: E731
    return {"favourite_min_points": FAV_MIN, "bottom": BOTTOM, "flagged_games": int(len(a)), "other_games": int(len(b)),
            "flagged_resid": round(float(a.mean()), 2), "other_resid": round(float(b.mean()), 2), "difference": round(float(d), 2),
            "ci": [round(float(lo), 2), round(float(hi), 2)], "flagged_won": round(win(F[F.flag]), 3), "other_won": round(win(F[~F.flag]), 3),
            "flagged_abs_margin": round(float(F[F.flag].act.abs().mean()), 1), "other_abs_margin": round(float(F[~F.flag].act.abs().mean()), 1),
            "passes": bool(hi < 0)}


def run() -> dict:
    R = pd.read_parquet(CACHE) if CACHE.exists() else bm.predictions()
    if not CACHE.exists():
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        R.to_parquet(CACHE)
    G = game_frame(R)
    rng = np.random.default_rng(7)
    out = {"fitted_on": [int(G.season.min()), int(G.season.max())], "games": int(len(G)), "rules": __doc__.split("    .venv")[0].strip()}
    X, y = design(G, "margin", None)
    b = ols(X, y)
    out["base"] = {"margin_per_unit_gap": round(float(b[1]), 2), "home_field": round(float(b[0]), 2),
                   "r_margin": round(float(np.corrcoef(X @ b, y)[0, 1]), 3)}
    out["measures"] = {m: {t: test(G, t, m, rng) for t in ("margin", "total", "points")} for m in MEASURES}
    for m, r in out["measures"].items():
        r["group"] = "margin" if r["margin"]["passes"] else "total" if r["total"]["passes"] else "unit"
    out["one_dimensional_favourite"] = favourite_flag(G, rng)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    res = run()
    print(json.dumps({k: v for k, v in res.items() if k != "rules"}, indent=1))
    if a.write:
        OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", OUT)
