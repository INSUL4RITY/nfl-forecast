"""Backtest of the matchup expectations (research tool; changes no report).

For every season 2021-25 and every cut week W from 4 to 16, the play-level matchup models are fitted on weeks 1..W
exactly as in compute.matchup_models, and each offence-against-defence pairing of week W+1 is predicted. Compared:
the league average, the unshrunk team effects, and the report's shrunk expectation. Also reported: the calibration
slope (1.0 = the size of the expected gap is right; below 1 = too extreme), by cut week, and how often a headline
edge of a given size pointed the right way.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_matchups.py

Result on 2021-25 (1,918 team-games per measure, run 2026-11-10): the shrunk expectation beat the league average on 12 of
13 measures (success rate 5.5%, EPA/play 4.7%, EPA/dropback 2.5% lower error; rushing EPA 0.1%; 10+ yard run rate
0.1% worse) and beat the unshrunk effects on all 13. Calibration slope for EPA/play: 0.38 at weeks 4-5, 0.70 at
6-7, 0.73 at 8-9, 0.87 at 10-11, about 1.1 from week 12, so early-season expectations are too extreme. Edges of
1.5+ pointed the right way 63% of the time (661 cases), edges under 0.5 52%. A game-clustered sampling variance
was tried in place of resid_var / n and was worse on every measure.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compute as cp  # noqa: E402

SEASONS = range(2021, 2026)
WEEKS = range(4, 17)
EDGE_METRICS = ["epa_db", "epa_rush", "expl_pass", "expl_run"]
BUCKETS = ([3, 5, 7, 9, 11, 13, 16], ["4-5", "6-7", "8-9", "10-11", "12-13", "14-16"])


def predictions() -> pd.DataFrame:
    rows = []
    for S in SEASONS:
        P = cp.add_unit_flags(cp.load_pbp(S))
        teams = sorted(P.posteam.dropna().unique())
        for W in WEEKS:
            p, nx = P[P.week <= W], P[P.week == W + 1]
            if nx.empty:
                continue
            for name, fr, mask, y in cp.MATCHUP_METRICS:
                if fr != "plays":
                    continue
                d = p[p[mask].astype(bool) & p[y].notna()].copy()
                d[y] = d[y].astype(float)
                a = cp.adjust(d, y, teams)
                side = {}
                for s, key, eff in (("off", "posteam", "off_eff"), ("def", "defteam", "def_eff")):
                    e = a[eff].reindex(teams)
                    noise = a["resid_var"] / d.groupby(key).size().reindex(teams)
                    tau2 = max(float(e.var(ddof=1) - noise.mean()), 1e-9)
                    side[s] = (e, tau2 / (tau2 + noise), tau2)
                x = nx[nx[mask].astype(bool) & nx[y].notna()]
                g = x.groupby(["game_id", "posteam", "defteam"]).agg(actual=(y, "mean"), n=(y, "size"), is_home=("is_home", "first")).reset_index()
                (eo, wo, t2o), (ed, wd, t2d) = side["off"], side["def"]
                for r in g.itertuples():
                    home = a["home"] * r.is_home
                    rows.append({"season": S, "W": W, "metric": name, "n": r.n, "actual": r.actual - a["mean"],
                                 "raw": eo[r.posteam] + ed[r.defteam] + home,
                                 "shr": wo[r.posteam] * eo[r.posteam] + wd[r.defteam] * ed[r.defteam] + home,
                                 "z": wo[r.posteam] * eo[r.posteam] / np.sqrt(t2o) + wd[r.defteam] * ed[r.defteam] / np.sqrt(t2d)})
        print(S, "done", flush=True)
    return pd.DataFrame(rows)


def slope(g: pd.DataFrame, col: str = "shr") -> float:
    return float(np.sum(g.n * g[col] * g.actual) / np.sum(g.n * g[col] * g[col]))


def main():
    pd.set_option("display.width", 200)
    R = predictions()
    R["weeks"] = pd.cut(R.W, BUCKETS[0], labels=BUCKETS[1])
    rmse = lambda g, c: float(np.sqrt(np.average((g.actual - (g[c] if c else 0)) ** 2, weights=g.n)))   # noqa: E731
    out = pd.DataFrame({m: {"games": len(g), "rmse_league": rmse(g, None), "rmse_unshrunk": rmse(g, "raw"), "rmse_report": rmse(g, "shr"),
                            "slope_unshrunk": slope(g, "raw"), "slope_report": slope(g)} for m, g in R.groupby("metric")}).T
    out["report_vs_league_%"] = (1 - out.rmse_report / out.rmse_league) * 100
    print(out.round(4).to_string())
    print("\nCalibration slope of the report's expectation by cut week (1.0 = right size):")
    print(R.groupby(["metric", "weeks"], observed=True).apply(slope, include_groups=False).unstack().round(2).to_string())
    E = R[R.metric.isin(EDGE_METRICS)]
    print("\nHeadline edges: share pointing the right way")
    for lab, q in (("1.5 or more", E.z.abs() >= 1.5), ("1.0 to 1.5", E.z.abs().between(1.0, 1.5, inclusive="left")), ("under 0.5", E.z.abs() < 0.5)):
        g = E[q]
        print(f"  {lab}: {len(g)} cases, {(np.sign(g.z) == np.sign(g.actual)).mean():.1%}")


if __name__ == "__main__":
    main()
