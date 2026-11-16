"""Hot and cold teams: is a streak real? Backtest on 2021-25 and the thresholds the hot/cold verdict uses.

For every team-season and cut week W (6-13), with games through W as the sample and the rest of the season as the target:
  1. Recent form: does the change in net EPA per play over the last four games (against the season to date) predict the
     rest-of-season net EPA per play beyond the season-to-date figure? The coefficient is the share of a recent change
     that lasted (0 = noise, 1 = fully real).
  2. Luck: wins minus EPA-expected wins (a logistic of game net EPA, fitted on the other seasons). Does it persist into
     the rest of the season, and does it predict rest-of-season wins beyond the season's net EPA?
  3. One-score record: wins minus losses in games decided by 8 points or fewer. Does it persist?
Writes streak_backtest.json; the report's hot/cold table quotes it.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_streaks.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression

import compute as cp

HERE = Path(__file__).resolve().parent
OUT = HERE / "streak_backtest.json"
SEASONS = range(2021, 2026)
CUTS = range(6, 14)


def team_games(s: int) -> pd.DataFrame:
    p = cp.add_unit_flags(cp.load_pbp(s))
    p = p[p.season_type == "REG"] if "season_type" in p else p
    G = cp.game_net_epa(p)
    plays = p[p.sc].groupby(["game_id", "posteam"]).size().rename("plays").reset_index().rename(columns={"posteam": "team"})
    G = G.merge(plays, on=["game_id", "team"], how="left")
    G = G.merge(p.groupby("game_id").week.first().rename("week"), left_on="game_id", right_index=True)
    G["margin"] = G.pf - G.pa
    G["season"] = s
    return G


def samples(G: pd.DataFrame, coef: float) -> pd.DataFrame:
    G = G.assign(xw=1 / (1 + np.exp(-coef * G.net_epa)))
    rows = []
    for (s, t), g in G.sort_values("week").groupby(["season", "team"]):
        for W in CUTS:
            a, b = g[g.week <= W], g[g.week > W]
            if len(a) < 5 or len(b) < 3:
                continue
            net_pp = lambda x: x.net_epa.sum() / x.plays.sum()   # noqa: E731
            l4 = a.tail(4)
            close = a[a.margin.abs() <= 8]
            rows.append({"season": s, "team": t, "W": W, "games": len(a),
                         "season_net": net_pp(a), "change": net_pp(l4) - net_pp(a), "last4_wins": float(l4.win.sum()),
                         "luck_pg": float((a.win - a.xw).mean()), "close_net_pg": float(((close.win - 0.5) * 2).sum() / len(a)),
                         "fut_net": net_pp(b), "fut_win": float(b.win.mean()), "fut_luck_pg": float((b.win - b.xw).mean()),
                         "fut_close_net_pg": float((((b[b.margin.abs() <= 8].win) - 0.5) * 2).sum() / len(b))})
    return pd.DataFrame(rows)


def ols(y, X):
    X = np.column_stack([np.ones(len(y))] + [np.asarray(c, float) for c in X])
    b, *_ = np.linalg.lstsq(X, np.asarray(y, float), rcond=None)
    return b


def boot_ci(R, f, n=500, seed=1):
    rng = np.random.default_rng(seed)
    keys = R[["season", "team"]].drop_duplicates().values
    vals = []
    for _ in range(n):
        pick = keys[rng.integers(0, len(keys), len(keys))]
        idx = pd.MultiIndex.from_arrays([pick[:, 0], pick[:, 1]])
        sub = R.set_index(["season", "team"]).loc[idx].reset_index()
        vals.append(f(sub))
    return [round(float(x), 3) for x in np.percentile(vals, [2.5, 97.5])]


def run() -> dict:
    G = pd.concat([team_games(s) for s in SEASONS])
    coef = float(LogisticRegression(fit_intercept=False, C=1e6).fit(G[G.win != 0.5][["net_epa"]], G[G.win != 0.5].win).coef_[0][0])
    R = samples(G, coef)
    form = lambda r: ols(r.fut_net, [r.season_net, r.change])[2]               # noqa: E731
    luck_persist = lambda r: float(r.luck_pg.corr(r.fut_luck_pg))               # noqa: E731
    luck_wins = lambda r: ols(r.fut_win, [r.season_net, r.luck_pg])[2]          # noqa: E731
    close_persist = lambda r: float(r.close_net_pg.corr(r.fut_close_net_pg))   # noqa: E731
    lucky, unlucky = R[R.luck_pg >= 0.75 / 9], R[R.luck_pg <= -0.75 / 9]
    return {"fitted_on": [SEASONS[0], SEASONS[-1]], "cut_weeks": [CUTS[0], CUTS[-1]], "samples": int(len(R)), "xw_coef": round(coef, 3),
            "form_change_kept": round(float(form(R)), 3), "form_change_kept_ci": boot_ci(R, form),
            "luck_persistence_corr": round(luck_persist(R), 3), "luck_persistence_ci": boot_ci(R, luck_persist),
            "luck_effect_on_future_win_pct": round(float(luck_wins(R)), 3), "luck_effect_ci": boot_ci(R, luck_wins),
            "close_record_persistence_corr": round(close_persist(R), 3), "close_record_persistence_ci": boot_ci(R, close_persist),
            "lucky_teams": {"n": int(len(lucky)), "luck_pg": round(float(lucky.luck_pg.mean()), 3), "future_luck_pg": round(float(lucky.fut_luck_pg.mean()), 3)},
            "unlucky_teams": {"n": int(len(unlucky)), "luck_pg": round(float(unlucky.luck_pg.mean()), 3), "future_luck_pg": round(float(unlucky.fut_luck_pg.mean()), 3)},
            "note": "luck_pg is wins minus EPA-expected wins per game; 0.75 over nine games is the report's over/underperformer line."}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    res = run()
    print(json.dumps(res, indent=1))
    if a.write:
        OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", OUT)
