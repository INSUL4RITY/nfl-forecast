"""Referee crews: accepted penalties per game in games each referee worked (crew = the referee's crew).

The referee for each game comes from the nflverse schedules (`referee`), which are complete for 2023-25 and, this
season, cover only the games listed there. This week's assignments are not in nflverse: they are read from the
hand-kept referees_<season>.json (same pattern as win_rates_<season>.json, with source and date) or shown as
"assignment not loaded". Penalty counts use the same rules as the team tables: one penalty per play (nflfastR),
declined and offsetting penalties excluded.
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

POOL = (2024, 2025)


def game_penalties(p: pd.DataFrame, presnap: set) -> pd.DataFrame:
    x = p[(p.penalty == 1) & p.penalty_team.notna()].copy()
    desc = x.desc.fillna("")
    x = x[~desc.str.contains(r"PENALTY on [^,]+, [^,]+, declined", case=False, regex=True) & ~desc.str.contains("offsetting", case=False)]
    games = p.groupby("game_id").agg(home=("home_team", "first"))
    g = pd.DataFrame(index=games.index)
    g["total"] = x.groupby("game_id").size()
    g["off_holding"] = x[x.penalty_type == "Offensive Holding"].groupby("game_id").size()
    g["dpi"] = x[x.penalty_type == "Defensive Pass Interference"].groupby("game_id").size()
    g["presnap"] = x[x.penalty_type.isin(presnap)].groupby("game_id").size()
    g["on_home"] = x[x.penalty_team == x.home_team].groupby("game_id").size()
    g["on_away"] = x[x.penalty_team != x.home_team].groupby("game_id").size()
    g["yards"] = x.groupby("game_id").penalty_yards.sum()
    return g.fillna(0)


def build(seasons_pbp: dict, sched_all: pd.DataFrame, season: int, week: int, presnap: set) -> dict:
    ref = sched_all.set_index("game_id").referee
    rows = []
    for s in list(POOL) + [season]:
        if s not in seasons_pbp:
            continue
        g = game_penalties(seasons_pbp[s], presnap)
        g["referee"] = g.index.map(ref)
        g["season"] = s
        rows.append(g.dropna(subset=["referee"]))
    G = pd.concat(rows)
    cols = ["total", "off_holding", "dpi", "presnap", "on_home", "on_away", "yards"]
    pool = G[G.season.isin(POOL)]
    cur = G[G.season == season]
    by = pool.groupby("referee")[cols].mean()
    by["games"] = pool.groupby("referee").size()
    by["games_cur"] = cur.groupby("referee").size().reindex(by.index).fillna(0).astype(int)
    by["total_cur"] = cur.groupby("referee").total.mean().reindex(by.index)
    for r in set(cur.referee) - set(by.index):      # a referee new in this season
        by.loc[r, ["games", "games_cur", "total_cur"]] = [0, int((cur.referee == r).sum()), cur[cur.referee == r].total.mean()]
    by["home_minus_away"] = by.on_home - by.on_away
    league = {c: float(pool[c].mean()) for c in cols}
    league["total_cur"] = float(cur.total.mean()) if len(cur) else None
    sched_cur = sched_all[(sched_all.season == season) & (sched_all.game_type == "REG") & (sched_all.week <= week)]
    # this week's assignments: hand-kept file first, then the schedule's own column if nflverse adds it
    f = Path(__file__).resolve().parent / f"referees_{season}.json"
    hand = json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}
    assign = dict((hand.get("weeks") or {}).get(str(week + 1), {}))
    nxt = sched_all[(sched_all.season == season) & (sched_all.week == week + 1)]
    for gid, r in zip(nxt.game_id, nxt.referee):
        if gid not in assign and isinstance(r, str) and r:
            assign[gid] = r
    out_rows = [{"referee": r, **{k: (None if pd.isna(v) else (int(v) if k.startswith("games") else float(v))) for k, v in x.items()}}
                for r, x in by.sort_values("total", ascending=False).iterrows()]
    return {"refs": out_rows, "league": league, "pool": f"{POOL[0]}-{str(POOL[1])[-2:]}", "season": season,
            "cur_games_with_ref": int(sched_cur.referee.notna().sum()), "cur_games": int(len(sched_cur)),
            "cur_weeks_with_ref": sorted(int(w) for w in sched_cur[sched_cur.referee.notna()].week.unique()),
            "assign": assign, "assign_source": hand.get("source"), "assign_loaded": bool(assign)}
