"""What does a line starter known to be out BEFORE kickoff cost? Backtest on 2021-25 (pre-game definition).

The first line-absence backtest (backtest_line_absences.py, line_absence_backtest.json, kept for history) counted a
starter as missing when he played under half of that game's offensive snaps. That includes in-game injuries and
benchings, which nobody knows before kickoff, so it is not the cost of an absence on the injury report.

This version counts a starter as missing only when that was knowable before kickoff:
  * he took no offensive snap in the game (inactive, or dressed but not used on offence), or
  * he was listed Out or Doubtful on that week's final injury report.
A starter who played some snaps and left hurt is NOT counted (column `in_game_only` keeps those for comparison).
Everything else is as before: starters = the five offensive linemen with the most offensive snaps in earlier weeks of
the season; team-games from week 4; the game's hit-or-sack rate and EPA per dropback regressed on the offence's and the
opponent's season-to-date hit-or-sack rates, the number of missing starters and missing x strong rush (opponent in the
top third), weighted by dropbacks; bootstrap intervals resample games. Writes line_absence_pregame.json; the report's
line caution quotes it from week 11 on.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_line_absences_pregame.py --write
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

import compute as cp
from backtest_line_absences import FIX, OL, SEASONS, fit

HERE = Path(__file__).resolve().parent
OUT = HERE / "line_absence_pregame.json"
OLD = HERE / "line_absence_backtest.json"
OUT_STATUS = {"Out", "Doubtful"}


def season_rows(s: int, pfr2gsis: dict) -> pd.DataFrame:
    p = cp.add_unit_flags(cp.load_pbp(s))
    p = p[p.season_type == "REG"] if "season_type" in p else p
    db = p[p.db]
    gm = db.groupby(["game_id", "posteam", "defteam"]).agg(n=("epa", "size"), hs=("hit_sack", "mean"), epa=("epa", "mean"),
                                                          week=("week", "first")).reset_index()
    sn = cp.fetch(f"snap_counts/snap_counts_{s}.parquet")
    sn = sn[(sn.game_type == "REG") & sn.position.isin(OL)].assign(team=lambda x: x.team.replace(FIX))
    inj = cp.fetch(f"injuries/injuries_{s}.parquet")
    inj = inj[(inj.game_type == "REG") & inj.report_status.isin(OUT_STATUS)].assign(team=lambda x: x.team.replace(FIX))
    listed = set(zip(inj.team, inj.week, inj.gsis_id))
    rows = []
    for (t, w), g in gm.groupby(["posteam", "week"]):
        if w < 4:
            continue
        r = g.iloc[0]
        prior = sn[(sn.team == t) & (sn.week < w)]
        if prior.week.nunique() < 3:
            continue
        starters = prior.groupby("pfr_player_id").offense_snaps.sum().nlargest(5).index
        now = sn[(sn.team == t) & (sn.week == w)].set_index("pfr_player_id")
        pre = in_game = 0
        for pid in starters:
            snaps = float(now.offense_snaps.get(pid, 0.0) or 0.0)
            on_report = (t, w, pfr2gsis.get(pid)) in listed
            if snaps == 0 or on_report:
                pre += 1
            elif float(now.offense_pct.get(pid, 0.0)) < 0.5:
                in_game += 1
        own = gm[(gm.posteam == t) & (gm.week < w)]
        opp = gm[(gm.defteam == r.defteam) & (gm.week < w)]
        if own.empty or opp.empty:
            continue
        rows.append({"season": s, "game_id": r.game_id, "team": t, "opp": r.defteam, "week": w, "n": r.n, "hs": r.hs, "epa": r.epa,
                     "missing": pre, "in_game_only": in_game,
                     "own_hs": np.average(own.hs, weights=own.n), "opp_hs": np.average(opp.hs, weights=opp.n)})
    R = pd.DataFrame(rows)
    R["strong_rush"] = R.groupby("week").opp_hs.transform(lambda x: x >= x.quantile(2 / 3)).astype(float)
    return R


def run() -> dict:
    pl = cp.fetch("players/players.parquet")
    pfr2gsis = dict(zip(pl.pfr_id, pl.gsis_id))
    R = pd.concat([season_rows(s, pfr2gsis) for s in SEASONS], ignore_index=True)
    out = {"fitted_on": [SEASONS[0], SEASONS[-1]], "team_games": int(len(R)),
           "missing_share": {str(k): int(v) for k, v in R.missing.clip(upper=3).value_counts().sort_index().items()},
           "in_game_only_team_games": int((R.in_game_only > 0).sum()),
           "definition": ("pre-game: starters = five OL with most offensive snaps in earlier weeks; missing = took no offensive snap "
                          "in the game or was listed Out/Doubtful on that week's injury report; starters hurt during the game are not counted")}
    games = R.game_id.unique()
    rng = np.random.default_rng(1)
    for y in ("hs", "epa"):
        b = fit(R, y)
        boots = []
        for _ in range(400):
            pick = rng.choice(games, len(games))
            boots.append(fit(R.set_index("game_id").loc[pick].reset_index(), y))
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
    if OLD.exists():
        old = json.loads(OLD.read_text(encoding="utf-8"))
        out["vs_in_game_definition"] = {"epa_per_missing_old": old["epa"]["per_missing_starter"],
                                        "epa_per_missing_old_ci": old["epa"]["per_missing_ci"],
                                        "hs_per_missing_old": old["hs"]["per_missing_starter"]}
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
