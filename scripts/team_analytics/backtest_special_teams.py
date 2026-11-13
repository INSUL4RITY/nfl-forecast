"""How much of a team's special-teams EPA per game lasts? Backtest on 2021-25 and the shrinkage the combined rating uses.

Special-teams EPA per game (kicks, punts, returns; for minus against) is noisy: its first-half to second-half correlation is
about 0.24. For every team-season and cut week W (4-16), the mean over games through W is the sample and the mean over the
rest of the season the target. The rating keeps w = tau2 / (tau2 + s2 / games) of a team's figure (league mean is 0 by
construction), with s2 the per-game variance and tau2 fitted so that w * sample best predicts the rest of the season.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_special_teams.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp

HERE = Path(__file__).resolve().parent
OUT = HERE / "st_shrinkage.json"
SEASONS = range(2021, 2026)
CUTS = range(4, 17)


def team_games(s: int) -> pd.DataFrame:
    p = cp.add_unit_flags(cp.load_pbp(s))
    p = p[p.season_type == "REG"] if "season_type" in p else p
    st = p[cp.st_mask(p)]
    f = st.groupby(["game_id", "posteam"]).epa.sum().rename_axis(["game_id", "team"])
    a = st.groupby(["game_id", "defteam"]).epa.sum().rename_axis(["game_id", "team"])
    games = pd.concat([p[["game_id", "week", "posteam"]].rename(columns={"posteam": "team"}),
                       p[["game_id", "week", "defteam"]].rename(columns={"defteam": "team"})]).dropna().drop_duplicates(["game_id", "team"])
    g = games.set_index(["game_id", "team"]).join(f.rename("f")).join(a.rename("a")).fillna(0.0)
    return g.assign(st=g.f - g.a, season=s).reset_index()


def samples(G: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (s, t), g in G.groupby(["season", "team"]):
        for W in CUTS:
            a, b = g[g.week <= W], g[g.week > W]
            if len(a) >= 2 and len(b) >= 2:
                rows.append({"season": s, "team": t, "W": W, "n": len(a), "x": a.st.mean(), "y": b.st.mean(), "m": len(b)})
    return pd.DataFrame(rows)


def fit_tau2(R: pd.DataFrame, s2: float) -> float:
    grid = np.linspace(0.01, 3.0, 600)
    sse = [float(np.sum(R.m * (R.y - t / (t + s2 / R.n) * R.x) ** 2)) for t in grid]
    return float(grid[int(np.argmin(sse))])


def run() -> dict:
    G = pd.concat([team_games(s) for s in SEASONS])
    s2 = float(G.groupby(["season", "team"]).st.var().mean())
    R = samples(G)
    tau2 = fit_tau2(R, s2)
    err = {"shrunk": [], "full": [], "zero": []}
    wts = []
    for s in SEASONS:
        tr, te = R[R.season != s], R[R.season == s]
        t = fit_tau2(tr, s2)
        w = t / (t + s2 / te.n)
        err["shrunk"] += list(te.y - w * te.x)
        err["full"] += list(te.y - te.x)
        err["zero"] += list(te.y)
        wts += list(te.m)
    w8 = np.array(wts, dtype=float)
    rm = {k: round(float(np.sqrt(np.average(np.square(v), weights=w8))), 4) for k, v in err.items()}
    h = G.assign(half=np.where(G.week <= 9, 1, 2)).groupby(["season", "team", "half"]).st.mean().unstack().dropna()
    corr = float(np.mean([g[1].corr(g[2]) for _, g in h.groupby(level=0)]))
    slope = float(np.polyfit(h[1] - h[1].mean(), h[2], 1)[0])
    return {"tau2": round(tau2, 4), "s2": round(s2, 3), "fitted_on": [SEASONS[0], SEASONS[-1]], "samples": int(len(R)),
            "split_half_corr": round(corr, 3), "split_half_slope": round(slope, 3),
            "weight_by_games": {str(n): round(tau2 / (tau2 + s2 / n), 3) for n in (2, 4, 6, 8, 9, 12, 16)},
            "loso_rmse": rm, "note": "Special-teams EPA per game kept in the combined rating: w = tau2 / (tau2 + s2 / games)."}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    res = run()
    print(json.dumps(res, indent=1))
    if a.write:
        OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", OUT)
