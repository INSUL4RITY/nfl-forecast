"""Expected touchdowns from where a player gets the ball, and whether they predict touchdowns better than touchdowns do.

2021-25 regular seasons. Every target (pass attempt with a receiver, sacks and scrambles excluded) and every designed carry
(scrambles excluded) is placed in a field-position bucket (yards from the end zone at the snap). The touchdown rate per
bucket and type is the league share of those opportunities that scored (a receiving touchdown for a target, a rushing
touchdown for a carry). A player's expected touchdowns = the sum of those rates over his opportunities.

Test (out of sample, each season with rates fitted on the other four): players with 20+ opportunities in weeks 1-9 and
3+ games in weeks 10-18. Predict touchdowns per game in weeks 10-18 from weeks 1-9 with (a) actual touchdowns per game,
(b) expected touchdowns per game, (c) the best mix of the two; report the error of each and how much of the gap
(touchdowns minus expected) carried into the second half. Writes td_expectation.json; usage.py and the report read it.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_td_expectation.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp

HERE = Path(__file__).resolve().parent
OUT = HERE / "td_expectation.json"
SEASONS = range(2021, 2026)
EDGES = [0, 2, 5, 10, 20, 40, 100]            # yards from the end zone: 1-2, 3-5, 6-10, 11-20, 21-40, 41+
LABELS = ["1-2", "3-5", "6-10", "11-20", "21-40", "41+"]
SPLIT = 9                                      # weeks 1-9 sample, weeks 10-18 target


def bucket(yl: pd.Series) -> pd.Series:
    return pd.cut(yl, EDGES, labels=LABELS, right=True)


def opportunities(p: pd.DataFrame) -> pd.DataFrame:
    """One row per target or designed carry: player, team, week, game, kind, bucket, touchdown."""
    tg = p[p.att & p.receiver_player_id.notna()]
    ca = p[p.drush & p.rusher_player_id.notna()]
    a = pd.DataFrame({"player": tg.receiver_player_id, "team": tg.posteam, "week": tg.week, "game_id": tg.game_id, "kind": "target",
                      "yl": tg.yardline_100, "td": (tg.pass_touchdown == 1).astype(int)})
    b = pd.DataFrame({"player": ca.rusher_player_id, "team": ca.posteam, "week": ca.week, "game_id": ca.game_id, "kind": "carry",
                      "yl": ca.yardline_100, "td": (ca.rush_touchdown == 1).astype(int)})
    o = pd.concat([a, b], ignore_index=True).dropna(subset=["yl"])
    o["bucket"] = bucket(o.yl).astype(str)
    return o


def rates(o: pd.DataFrame) -> dict:
    r = o.groupby(["kind", "bucket"]).td.agg(["mean", "size"])
    return {k: {b: {"rate": round(float(r.loc[(k, b), "mean"]), 4), "n": int(r.loc[(k, b), "size"])} for b in LABELS if (k, b) in r.index}
            for k in ("target", "carry")}


def x_td(o: pd.DataFrame, R: dict) -> pd.Series:
    return pd.Series([R[k][b]["rate"] if b in R[k] else 0.0 for k, b in zip(o.kind, o.bucket)], index=o.index)


def per_player(o: pd.DataFrame) -> pd.DataFrame:
    g = o.groupby("player")
    return pd.DataFrame({"opps": g.size(), "td": g.td.sum(), "xtd": g.xtd.sum(), "games": g.game_id.nunique()})


def run() -> dict:
    O = {s: opportunities(cp.add_unit_flags(cp.load_pbp(s)).query("season_type == 'REG'")) for s in SEASONS}
    rows = []
    for s in SEASONS:
        R = rates(pd.concat([O[t] for t in SEASONS if t != s]))           # rates from the other four seasons
        o = O[s].copy()
        o["xtd"] = x_td(o, R)
        a, b = per_player(o[o.week <= SPLIT]), per_player(o[o.week > SPLIT])
        j = a.join(b, rsuffix="_f", how="inner")
        j = j[(j.opps >= 20) & (j.games_f >= 3)]
        rows.append(j.assign(season=s, td_pg=j.td / j.games, xtd_pg=j.xtd / j.games, fut=j.td_f / j.games_f))
    P = pd.concat(rows)
    mae = lambda pred: float((P.fut - pred).abs().mean())                    # noqa: E731
    X = np.column_stack([np.ones(len(P)), P.xtd_pg, P.td_pg - P.xtd_pg])
    beta = np.linalg.lstsq(X, P.fut, rcond=None)[0]
    # out of sample mix: fit the gap weight on four seasons, score the fifth
    oos = []
    for s in SEASONS:
        tr, te = P[P.season != s], P[P.season == s]
        Xt = np.column_stack([np.ones(len(tr)), tr.xtd_pg, tr.td_pg - tr.xtd_pg])
        bt = np.linalg.lstsq(Xt, tr.fut, rcond=None)[0]
        oos.append((te.fut - (bt[0] + bt[1] * te.xtd_pg + bt[2] * (te.td_pg - te.xtd_pg))).abs())
    allR = rates(pd.concat(O.values()))
    return {"fitted_on": [SEASONS[0], SEASONS[-1]], "buckets": LABELS, "rates": allR,
            "test": {"players": int(len(P)), "split_week": SPLIT, "min_opps": 20,
                     "mae_actual_td_pg": round(mae(P.td_pg), 4), "mae_expected_td_pg": round(mae(P.xtd_pg), 4),
                     "mae_mix_oos": round(float(pd.concat(oos).mean()), 4),
                     "corr_actual": round(float(P.td_pg.corr(P.fut)), 3), "corr_expected": round(float(P.xtd_pg.corr(P.fut)), 3),
                     "gap_kept": round(float(beta[2]), 3), "xtd_coef": round(float(beta[1]), 3)},
            "note": ("rates: league touchdown share per opportunity by yards from the end zone; test: weeks 1-9 predict weeks 10-18, "
                     "rates fitted without the tested season; gap_kept = share of (touchdowns - expected) per game that carried into "
                     "the second half beyond expected touchdowns")}


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    res = run()
    print(json.dumps(res, indent=1))
    if a.write:
        OUT.write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
        print("wrote", OUT)
