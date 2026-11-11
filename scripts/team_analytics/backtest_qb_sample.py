"""How much of a quarterback's early EPA per dropback carries forward? Backtest on 2021-25 and the fitted QB shrinkage.

For every passer-season, the first K dropbacks (K = 30, 60, 120, 200) are the sample and the rest of his season (150+
dropbacks) is the target. The team-level shrinkage in the matchup models keeps too much of a quarterback's early number
(at 120 dropbacks it keeps 38%, while only 27% carried forward), so quarterback expectations use their own between-QB
variance tau2, fitted here: predicted = league mean + w (sample - league mean), w = tau2 / (tau2 + s2 / K), with s2 the
per-dropback EPA variance. Capping big plays, success rate and dropping the best quarter were also tested; none beat raw
EPA by more than noise (bootstrap 95% intervals of the correlation gain include zero), so they are not used.

Selection: only passers who went on to 150+ more dropbacks that season, so mostly starters; a backup who loses the job
early is under-represented.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_qb_sample.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp

HERE = Path(__file__).resolve().parent
OUT = HERE / "qb_shrinkage.json"
KS = (30, 60, 120, 200)
SEASONS = range(2021, 2026)


def samples() -> pd.DataFrame:
    rows = []
    for s in SEASONS:
        p = cp.add_unit_flags(cp.load_pbp(s))
        d = p[p.db & p.passer_id.notna()].sort_values(["game_id", "play_id"])
        for pid, g in d.groupby("passer_id"):
            for K in KS:
                if len(g) < K + 150:
                    continue
                a, b = g.iloc[:K], g.iloc[K:]
                rows.append({"season": s, "pid": pid, "K": K, "raw": a.epa.mean(), "cap": a.epa.clip(-1.5, 1.5).mean(),
                             "sr": a.success.mean(), "fut": b.epa.mean(), "s2": a.epa.var()})
    return pd.DataFrame(rows)


def predict(g: pd.DataFrame, tau2: float, s2: float, mu: float) -> np.ndarray:
    w = tau2 / (tau2 + s2 / g.K)
    return mu + w * (g.raw - mu)


def fit_tau2(g: pd.DataFrame, s2: float) -> float:
    mu = g.fut.mean()
    grid = np.linspace(0.0005, 0.03, 300)
    sse = [float(np.square(g.fut - predict(g, t, s2, mu)).sum()) for t in grid]
    return float(grid[int(np.argmin(sse))])


def run(team_tau2: float | None = None, team_rv: float | None = None) -> dict:
    """team_tau2/team_rv: the team-level values the matchup models used before (for comparison only)."""
    R = samples()
    s2 = float(R.s2.mean())
    tau2 = fit_tau2(R, s2)
    loso = []
    for s in SEASONS:
        tr, te = R[R.season != s], R[R.season == s]
        t = fit_tau2(tr, s2)
        loso += list(te.fut - predict(te, t, s2, tr.fut.mean()))
    old = None
    if team_tau2:
        old = round(float(np.sqrt(np.mean(np.square(R.fut - (R.fut.mean() + team_tau2 / (team_tau2 + team_rv / R.K) * (R.raw - R.fut.mean())))))), 4)
    by_k = []
    for K, g in R.groupby("K"):
        slope = float(np.polyfit(g.raw - g.raw.mean(), g.fut, 1)[0])
        by_k.append({"K": int(K), "passer_seasons": int(len(g)), "carried_forward": round(slope, 3),
                     "fitted_weight": round(tau2 / (tau2 + s2 / K), 3),
                     "corr_raw": round(float(g.raw.corr(g.fut)), 3), "corr_capped": round(float(g.cap.corr(g.fut)), 3),
                     "corr_success": round(float(g.sr.corr(g.fut)), 3)})
    return {"tau2": round(tau2, 5), "s2": round(s2, 4), "fitted_on": [SEASONS[0], SEASONS[-1]], "passers": int(R.pid.nunique()),
            "rows": int(len(R)), "loso_rmse": round(float(np.sqrt(np.mean(np.square(loso)))), 4),
            "mean_only_rmse": round(float(R.fut.std(ddof=0)), 4),
            "team_weight_rmse": old, "team_weight_from": {"tau2": team_tau2, "resid_var": team_rv}, "by_sample": by_k,
            "note": "Per-quarterback shrinkage of EPA per dropback; see backtest_qb_sample.py."}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    rep = sorted((cp.ROOT / "reports" / "team_analytics").glob("20*_week*"))[-1] / "matchup_models.json"
    m = json.loads(rep.read_text())["epa_db"] if rep.exists() else None
    res = run(m["off"]["tau2"] if m else None, m["resid_var"] if m else None)
    print(json.dumps(res, indent=1))
    if a.write:
        OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", OUT)
