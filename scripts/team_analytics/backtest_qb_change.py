"""What does a team's offence lose when someone other than its opening quarterback starts? Backtest on 2021-25.

Pre-game definition: the starter is the passer of the team's first dropback (context.qb_starts), so a quarterback hurt
during a game is not a change; a change game is one started by anyone other than the team's opening starter of that
season. The replacement is classed from the weekly roster and the season's starts:
  * rookie            - in his rookie season;
  * traded in         - already started for another team earlier that season;
  * veteran backup    - anyone else (a non-rookie who did not open the season as this team's starter).
For every team-game from week 3 where the team has 2+ earlier games started by its opening quarterback, the game's EPA per
dropback (and per play) is regressed on the team's EPA per dropback in those opening-starter games, the opponent's
season-to-date EPA per dropback allowed, and one indicator per class, weighted by dropbacks. The class coefficients are
the cost of the change beyond what the team and the opponent predict; bootstrap intervals resample games. Out of sample
(each season from the other four): does adding the class cost lower the error on change games? Writes qb_change.json;
the report's quarterback caution and matchup summary quote it.

    .venv\\Scripts\\python.exe scripts\\team_analytics\\backtest_qb_change.py --write
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
OUT = HERE / "qb_change.json"
SEASONS = range(2021, 2026)
CLASSES = ("rookie", "traded in", "veteran backup")
FIX = {"LAR": "LA", "OAK": "LV", "SD": "LAC", "STL": "LA"}


def season_rows(s: int) -> pd.DataFrame:
    p = cp.add_unit_flags(cp.load_pbp(s))
    p = p[p.season_type == "REG"] if "season_type" in p else p
    st = ctx.qb_starts(p).sort_values(["posteam", "week"])
    opener = st.drop_duplicates("posteam").set_index("posteam").passer_id
    ros = cp.fetch(f"weekly_rosters/roster_weekly_{s}.parquet")
    rookie = set(ros.loc[(ros.rookie_year == s) | (ros.years_exp == 0), "gsis_id"].dropna())
    first_team = st.sort_values("week").drop_duplicates("passer_id").set_index("passer_id").posteam
    first_week = st.groupby("passer_id").week.min()
    db = p[p.db]
    g = db.groupby(["game_id", "posteam", "defteam"]).agg(n=("epa", "size"), epa_db=("epa", "mean"), week=("week", "first")).reset_index()
    pl = p[p.sc].groupby(["game_id", "posteam"]).agg(epa_play=("epa", "mean"), plays=("epa", "size")).reset_index()
    g = g.merge(pl, on=["game_id", "posteam"]).merge(st[["game_id", "posteam", "passer_id"]], on=["game_id", "posteam"])
    rows = []
    for r in g.itertuples():
        if r.week < 3:
            continue
        op = opener.get(r.posteam)
        base = g[(g.posteam == r.posteam) & (g.week < r.week) & (g.passer_id == op)]
        opp = g[(g.defteam == r.defteam) & (g.week < r.week)]
        if len(base) < 2 or opp.empty:
            continue
        cls = None
        if r.passer_id != op:
            if r.passer_id in rookie:
                cls = "rookie"
            elif first_team.get(r.passer_id) != r.posteam and first_week.get(r.passer_id, 99) < r.week:
                cls = "traded in"
            else:
                cls = "veteran backup"
        rows.append({"season": s, "game_id": r.game_id, "team": r.posteam, "week": r.week, "n": r.n, "plays": r.plays,
                     "epa_db": r.epa_db, "epa_play": r.epa_play, "cls": cls,
                     "base_db": np.average(base.epa_db, weights=base.n), "base_play": np.average(base.epa_play, weights=base.plays),
                     "opp_db": np.average(opp.epa_db, weights=opp.n), "opp_play": np.average(opp.epa_play, weights=opp.plays)})
    return pd.DataFrame(rows)


def design(R: pd.DataFrame, y: str, with_cls: bool = True) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    base, opp = ("base_db", "opp_db") if y == "epa_db" else ("base_play", "opp_play")
    cols = [np.ones(len(R)), R[base].values, R[opp].values]
    if with_cls:
        cols += [(R.cls == c).astype(float).values for c in CLASSES]
    w = np.sqrt((R.n if y == "epa_db" else R.plays).values.astype(float))
    return np.column_stack(cols), R[y].values, w


def fit(R: pd.DataFrame, y: str, with_cls: bool = True) -> np.ndarray:
    X, v, w = design(R, y, with_cls)
    return np.linalg.lstsq(X * w[:, None], v * w, rcond=None)[0]


def run() -> dict:
    R = pd.concat([season_rows(s) for s in SEASONS], ignore_index=True)
    out = {"fitted_on": [SEASONS[0], SEASONS[-1]], "team_games": int(len(R)),
           "change_games": {c: int((R.cls == c).sum()) for c in CLASSES},
           "definition": ("starter = passer of the team's first dropback; change = a start by anyone but the team's opening starter; "
                          "baseline = the team's EPA in earlier games started by its opening quarterback; opponent = its season-to-date EPA allowed")}
    games = R.game_id.unique()
    rng = np.random.default_rng(1)
    for y in ("epa_db", "epa_play"):
        b = fit(R, y)
        boots = []
        for _ in range(400):
            pick = rng.choice(games, len(games))
            boots.append(fit(R.set_index("game_id").loc[pick].reset_index(), y))
        boots = np.array(boots)
        out[y] = {c: {"cost": round(float(b[3 + i]), 4),
                      "ci": [round(float(x), 4) for x in np.percentile(boots[:, 3 + i], [2.5, 97.5])]} for i, c in enumerate(CLASSES)}
        # out of sample: each season's change games predicted from the other four, with and without the class cost
        err_with, err_without = [], []
        for s in SEASONS:
            tr, te = R[R.season != s], R[(R.season == s) & R.cls.notna()]
            if te.empty:
                continue
            for flag, sink in ((True, err_with), (False, err_without)):
                bb = fit(tr, y, flag)
                X, v, _ = design(te, y, flag)
                sink.append(np.abs(v - X @ bb) * (te.n if y == "epa_db" else te.plays).values)
        wsum = float(sum((R[R.cls.notna()].n if y == "epa_db" else R[R.cls.notna()].plays)))
        out[y]["oos_mae_with_cost"] = round(float(np.concatenate(err_with).sum() / wsum), 4)
        out[y]["oos_mae_without"] = round(float(np.concatenate(err_without).sum() / wsum), 4)
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
