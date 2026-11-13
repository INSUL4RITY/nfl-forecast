"""How much of a quarterback's early EPA per dropback carries forward? Backtest on 2021-25 and the fitted QB shrinkage.

For every passer-season, the first K dropbacks (K = 30, 60, 120, 200) are the sample and the rest of his season (150+
dropbacks) is the target. The team-level shrinkage in the matchup models keeps too much of a quarterback's early number
(at 120 dropbacks it keeps 38%, while only 27% carried forward), so quarterback expectations use their own between-QB
variance tau2, fitted here: predicted = league mean + w (sample - league mean), w = tau2 / (tau2 + s2 / K), with s2 the
per-dropback EPA variance. Capping big plays, success rate and dropping the best quarter were also tested; none beat raw
EPA by more than noise (bootstrap 95% intervals of the correlation gain include zero), so they are not used.

Selection: only passers who went on to 150+ more dropbacks that season, so mostly starters; a backup who loses the job
early is under-represented.

Role: a second fit (passers with 50+ more dropbacks, so backups are included) adds whether the passer opened the season as
his team's starter (he threw the first dropback of the team's first game). Backups fell short of what their own shrunk
numbers suggested, so the report's quarterback expectations add the fitted starter or backup offset. A passer's previous
two seasons were also tested: they barely helped overall and made backups' predictions worse, so they are not used.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_qb_sample.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp
import context as ctx

HERE = Path(__file__).resolve().parent
OUT = HERE / "qb_shrinkage.json"
KS = (30, 60, 120, 200)
SEASONS = range(2021, 2026)
ROLE_REST = 50


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


def role_samples() -> pd.DataFrame:
    rows = []
    for s in SEASONS:
        p = cp.add_unit_flags(cp.load_pbp(s))
        st = ctx.qb_starts(p)
        first = st.sort_values("week").drop_duplicates("posteam")
        opened = set(first.passer_id)
        d = p[p.db & p.passer_id.notna()].sort_values(["game_id", "play_id"])
        for pid, g in d.groupby("passer_id"):
            for K in KS:
                if len(g) < K + ROLE_REST:
                    continue
                a, b = g.iloc[:K], g.iloc[K:]
                rows.append({"season": s, "pid": pid, "K": K, "raw": a.epa.mean(), "fut": b.epa.mean(), "n_fut": len(b),
                             "backup": pid not in opened})
    return pd.DataFrame(rows)


def _role_lsq(R, tau2, s2, mu, role=True):
    X = [np.ones(len(R)), tau2 / (tau2 + s2 / R.K) * (R.raw - mu)] + ([R.backup.astype(float)] if role else [])
    X, w = np.column_stack(X), np.sqrt(R.n_fut.values)
    return np.linalg.lstsq(X * w[:, None], R.fut * w, rcond=None)[0], X


def role_fit(tau2: float, s2: float) -> dict:
    R = role_samples()
    mu = float(R.fut.mean())
    b, _ = _role_lsq(R, tau2, s2, mu)
    err = {True: [], False: []}
    errb = {True: [], False: []}
    for s in SEASONS:
        tr, te = R[R.season != s], R[R.season == s]
        m = float(tr.fut.mean())
        for role in (True, False):
            bb, _ = _role_lsq(tr, tau2, s2, m, role)
            _, X = _role_lsq(te, tau2, s2, m, role)
            e = te.fut - X @ bb
            err[role] += list(e)
            errb[role] += list(e[te.backup])
    rng = np.random.default_rng(1)
    pids = R.pid.unique()
    boot = []
    for _ in range(500):
        pick = rng.choice(pids, len(pids))
        boot.append(_role_lsq(pd.concat([R[R.pid == x] for x in pick]), tau2, s2, mu)[0][2])
    rm = lambda e: round(float(np.sqrt(np.mean(np.square(e)))), 4)   # noqa: E731
    return {"definition": "backup = did not throw the first dropback of his team's first game of the season",
            "rest_min": ROLE_REST, "rows": int(len(R)), "backup_seasons": int(R[R.backup].drop_duplicates(["season", "pid"]).shape[0]),
            "cur_coef": round(float(b[1]), 3), "starter_adj": round(float(b[0] - mu), 4), "backup_adj": round(float(b[0] + b[2] - mu), 4),
            "backup_gap": round(float(b[2]), 4), "backup_gap_ci": [round(float(x), 3) for x in np.percentile(boot, [2.5, 97.5])],
            "loso_rmse_with_role": rm(err[True]), "loso_rmse_without": rm(err[False]),
            "loso_rmse_backups_with_role": rm(errb[True]), "loso_rmse_backups_without": rm(errb[False])}


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
    fwd, fwd_mean, fwd_old = [], [], []
    for s in list(SEASONS)[1:]:            # forward only: fit on earlier seasons, predict this one
        tr, te = R[R.season < s], R[R.season == s]
        t, mu = fit_tau2(tr, s2), tr.fut.mean()
        fwd += list(te.fut - predict(te, t, s2, mu))
        fwd_mean += list(te.fut - mu)
        if team_tau2:
            fwd_old += list(te.fut - (mu + team_tau2 / (team_tau2 + team_rv / te.K) * (te.raw - mu)))
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
            "forward_only": {"seasons": [int(x) for x in list(SEASONS)[1:]], "rmse": round(float(np.sqrt(np.mean(np.square(fwd)))), 4),
                             "mean_only_rmse": round(float(np.sqrt(np.mean(np.square(fwd_mean)))), 4),
                             "team_weight_rmse": round(float(np.sqrt(np.mean(np.square(fwd_old)))), 4) if fwd_old else None},
            "role": role_fit(tau2, s2),
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
