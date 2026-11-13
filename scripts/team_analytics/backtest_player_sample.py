"""How much of a running back's or receiver's early efficiency carries forward? Backtest on 2021-25 and the fitted shrinkage.

For every player-season, his first K opportunities (carries for EPA per carry; targets for EPA per target, split into
WR, TE and RB targets) are the sample and the rest of his season (50+ more opportunities) the target. As for
quarterbacks (backtest_qb_sample.py), each measure gets a between-player variance tau2 fitted so that
league mean + tau2 / (tau2 + s2 / K) x (sample - league mean) best predicts the rest of the season, with s2 the
per-opportunity variance. Success rate and capped EPA are reported for comparison, and target share (a usage measure)
shows how much faster usage settles than efficiency.

Selection: only players who went on to 50+ more opportunities that season, so mostly regulars.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_player_sample.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp

HERE = Path(__file__).resolve().parent
OUT = HERE / "player_shrinkage.json"
KS = (10, 20, 40, 80)
REST = 50
SEASONS = range(2021, 2026)


def samples() -> pd.DataFrame:
    pos = cp.fetch("players/players.parquet").set_index("gsis_id").position
    rows = []
    for s in SEASONS:
        p = cp.add_unit_flags(cp.load_pbp(s)).sort_values(["game_id", "play_id"])
        tg = p[p.att & p.receiver_player_id.notna()]
        ca = p[p.drush & p.rusher_player_id.notna()]
        team_tgt = tg.groupby(["posteam", "game_id"]).size()
        groups = [("carry", ca, "rusher_player_id")] + [(f"target_{x}", tg[tg.receiver_player_id.map(pos).eq(x)], "receiver_player_id")
                                                      for x in ("WR", "TE", "RB")]
        for kind, d, col in groups:
            for pid, g in d.groupby(col):
                for K in KS:
                    if len(g) < K + REST:
                        continue
                    a, b = g.iloc[:K], g.iloc[K:]
                    r = {"season": s, "pid": pid, "kind": kind, "K": K, "raw": a.epa.mean(), "fut": b.epa.mean(),
                         "s2": a.epa.var(), "sr": a.success.mean(), "cap": a.epa.clip(-1.5, 1.5).mean()}
                    if kind.startswith("target"):           # usage: his share of team targets in the games of each part
                        ga, gb = a.game_id.unique(), b.game_id.unique()
                        ta = team_tgt[team_tgt.index.get_level_values(1).isin(ga)].sum()
                        tb = team_tgt[team_tgt.index.get_level_values(1).isin(gb)].sum()
                        r["share"], r["share_fut"] = len(a) / ta if ta else np.nan, len(b) / tb if tb else np.nan
                    rows.append(r)
    return pd.DataFrame(rows)


def fit_tau2(g: pd.DataFrame, s2: float) -> float:
    mu = g.fut.mean()
    grid = np.linspace(0.0001, 0.08, 800)
    sse = [float(np.square(g.fut - (mu + t / (t + s2 / g.K) * (g.raw - mu))).sum()) for t in grid]
    return float(grid[int(np.argmin(sse))])


def run() -> dict:
    R = samples()
    out = {"fitted_on": [SEASONS[0], SEASONS[-1]], "rest_min": REST, "measures": {}}
    for kind, g in R.groupby("kind"):
        s2 = float(g.s2.mean())
        tau2 = fit_tau2(g, s2)
        loso = []
        for s in SEASONS:
            tr, te = g[g.season != s], g[g.season == s]
            if not len(te) or not len(tr):
                continue
            t, mu = fit_tau2(tr, s2), tr.fut.mean()
            loso += list(te.fut - (mu + t / (t + s2 / te.K) * (te.raw - mu)))
        fwd, fwd_mean = [], []
        for s in list(SEASONS)[1:]:        # forward only: fit on earlier seasons, predict this one
            tr, te = g[g.season < s], g[g.season == s]
            if not len(te) or not len(tr):
                continue
            t, mu = fit_tau2(tr, s2), tr.fut.mean()
            fwd += list(te.fut - (mu + t / (t + s2 / te.K) * (te.raw - mu)))
            fwd_mean += list(te.fut - mu)
        by_k = []
        for K, h in g.groupby("K"):
            row = {"K": int(K), "player_seasons": int(len(h)),
                   "carried_forward": round(float(np.polyfit(h.raw - h.raw.mean(), h.fut, 1)[0]), 3),
                   "fitted_weight": round(tau2 / (tau2 + s2 / K), 3), "corr_raw": round(float(h.raw.corr(h.fut)), 3),
                   "corr_success": round(float(h.sr.corr(h.fut)), 3), "corr_capped": round(float(h.cap.corr(h.fut)), 3)}
            if "share" in h:
                row["share_corr"] = round(float(h.share.corr(h.share_fut)), 3)
            by_k.append(row)
        out["measures"][kind] = {"tau2": round(tau2, 5), "s2": round(s2, 4), "mean": round(float(g.fut.mean()), 4),
                                 "players": int(g.pid.nunique()), "rows": int(len(g)),
                                 "loso_rmse": round(float(np.sqrt(np.mean(np.square(loso)))), 4),
                                 "mean_only_rmse": round(float(g.fut.std(ddof=0)), 4), "by_sample": by_k,
                                 "forward_only": {"rmse": round(float(np.sqrt(np.mean(np.square(fwd)))), 4) if fwd else None,
                                                  "mean_only_rmse": round(float(np.sqrt(np.mean(np.square(fwd_mean)))), 4) if fwd else None}}
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    res = run()
    print(json.dumps(res, indent=1))
    if a.write:
        OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", OUT)
