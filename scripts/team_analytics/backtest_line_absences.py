"""Does a line missing starters give up more pressure, and more so against a strong pass rush? Backtest on 2021-25.

For every team-game from week 4: the offence's starting five are its five offensive linemen with the most offensive snaps
in earlier weeks of the season; a starter is missing when he plays under half of this game's offensive snaps (absent
included). The game's hit-or-sack rate (pbp sacks and QB hits per dropback) and EPA per dropback are regressed on the
offence's season-to-date hit-or-sack rate allowed, the opponent's season-to-date hit-or-sack rate, the number of missing
starters, and missing x strong rush (opponent in the top third by season-to-date rate), weighted by dropbacks. Bootstrap
intervals resample games. Writes line_absence_backtest.json; the report's depleted-line flag quotes it.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_line_absences.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp

HERE = Path(__file__).resolve().parent
OUT = HERE / "line_absence_backtest.json"
SEASONS = range(2021, 2026)
OL = {"T", "G", "C", "OL", "OT", "OG"}
FIX = {"LAR": "LA", "OAK": "LV", "SD": "LAC", "STL": "LA"}


def season_rows(s: int) -> pd.DataFrame:
    p = cp.add_unit_flags(cp.load_pbp(s))
    p = p[p.season_type == "REG"] if "season_type" in p else p
    db = p[p.db]
    gm = db.groupby(["game_id", "posteam", "defteam"]).agg(n=("epa", "size"), hs=("hit_sack", "mean"), epa=("epa", "mean"),
                                                          week=("week", "first")).reset_index()
    sn = cp.fetch(f"snap_counts/snap_counts_{s}.parquet")
    sn = sn[(sn.game_type == "REG") & sn.position.isin(OL)].assign(team=lambda x: x.team.replace(FIX))
    rows = []
    for (t, w), g in gm.groupby(["posteam", "week"]):
        if w < 4:
            continue
        r = g.iloc[0]
        prior = sn[(sn.team == t) & (sn.week < w)]
        if prior.week.nunique() < 3:
            continue
        starters = prior.groupby("pfr_player_id").offense_snaps.sum().nlargest(5).index
        now = sn[(sn.team == t) & (sn.week == w)].set_index("pfr_player_id").offense_pct
        missing = int(sum(now.get(pid, 0.0) < 0.5 for pid in starters))
        own = gm[(gm.posteam == t) & (gm.week < w)]
        opp = gm[(gm.defteam == r.defteam) & (gm.week < w)]
        if own.empty or opp.empty:
            continue
        rows.append({"season": s, "game_id": r.game_id, "team": t, "opp": r.defteam, "week": w, "n": r.n, "hs": r.hs, "epa": r.epa,
                     "missing": missing, "own_hs": np.average(own.hs, weights=own.n), "opp_hs": np.average(opp.hs, weights=opp.n)})
    R = pd.DataFrame(rows)
    R["strong_rush"] = R.groupby("week").opp_hs.transform(lambda x: x >= x.quantile(2 / 3)).astype(float)
    return R


def fit(R: pd.DataFrame, y: str) -> np.ndarray:
    X = np.column_stack([np.ones(len(R)), R.own_hs, R.opp_hs, R.missing, R.missing * R.strong_rush])
    w = np.sqrt(R.n.values)
    return np.linalg.lstsq(X * w[:, None], R[y].values * w, rcond=None)[0]


def run() -> dict:
    R = pd.concat([season_rows(s) for s in SEASONS], ignore_index=True)
    out = {"fitted_on": [SEASONS[0], SEASONS[-1]], "team_games": int(len(R)),
           "missing_share": {str(k): int(v) for k, v in R.missing.clip(upper=3).value_counts().sort_index().items()},
           "definition": "starters = five OL with most offensive snaps in earlier weeks; missing = under 50% of this game's snaps"}
    games = R.game_id.unique()
    rng = np.random.default_rng(1)
    for y in ("hs", "epa"):
        b = fit(R, y)
        boots = []
        for _ in range(400):
            pick = rng.choice(games, len(games))
            sub = R.set_index("game_id").loc[pick].reset_index()
            boots.append(fit(sub, y))
        boots = np.array(boots)
        ci = lambda j: [round(float(x), 4) for x in np.percentile(boots[:, j], [2.5, 97.5])]   # noqa: E731
        out[y] = {"per_missing_starter": round(float(b[3]), 4), "per_missing_ci": ci(3),
                  "extra_vs_strong_rush": round(float(b[4]), 4), "extra_vs_strong_rush_ci": ci(4),
                  "opp_rush_coef": round(float(b[2]), 3), "own_line_coef": round(float(b[1]), 3)}
    out["league_hs"] = round(float(np.average(R.hs, weights=R.n)), 4)
    out["league_epa"] = round(float(np.average(R.epa, weights=R.n)), 4)
    for k in (0, 1, 2):
        m = R.missing == k if k < 2 else R.missing >= 2
        out[f"raw_{'2plus' if k == 2 else k}"] = {"team_games": int(m.sum()), "hs": round(float(np.average(R[m].hs, weights=R[m].n)), 4),
                                                  "epa": round(float(np.average(R[m].epa, weights=R[m].n)), 4)}
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
