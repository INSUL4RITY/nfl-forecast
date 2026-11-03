"""Unusual games and multi-interception games: results a season average should not be read without.

A game is flagged when the play-by-play weather text shows rain, snow or wind of 15+ mph (outdoors or an open roof) AND
the two teams' combined dropbacks are in the bottom 2% of all 2021-25 regular-season games. For each team in such a
game the opponent-adjusted season and last-four figures are given with and without it, using the same play-level
method as Recent form, plus its leading passer's line in that game.

A quarterback line is added when he threw 2+ interceptions in his team's latest game: FTN interception-worthy and
uncatchable counts, against his earlier games. Interception-worthy charting cannot separate a wet ball from a bad
decision. Display only: no rating or matchup figure changes.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

BAD = re.compile(r"rain|snow|shower|sleet|storm|drizzle|flurr|flakes", re.I)
WIND_MIN = 15
PCTL = 2
INT_MIN = 2
CAVEAT = "Interception-worthy charting cannot separate a wet ball from a bad decision."


def weather(text, roof) -> tuple[bool, str]:
    """(bad weather?, plain label) from the pbp weather text, e.g. 'Rain Temp: 78 F, Humidity: 81%, Wind: E 9 mph'."""
    if not isinstance(text, str) or str(roof) in ("dome", "closed"):
        return False, ""
    cond = text.split("Temp")[0].strip(" ,;")
    t = re.search(r"Temp:\s*(\d+)", text)
    w = re.search(r"(\d+)\s*mph", text)
    wind = int(w.group(1)) if w else None
    wet = bool(BAD.search(cond))
    label = ", ".join(x for x in (cond, f"{t.group(1)}F" if t else "", f"wind {wind} mph" if wind is not None else "") if x)
    return wet or (wind is not None and wind >= WIND_MIN), label


def combined_dropbacks(p: pd.DataFrame) -> pd.Series:
    return p[p.db].groupby("game_id").size()


def _splits(sc, t, gid, last4, a):
    """Team t's adjusted EPA/play, season and last four, with and without game gid."""
    o, d = sc[sc.posteam == t], sc[sc.defteam == t]
    mo = lambda x: float(x.o_res.mean()) if len(x) else None   # noqa: E731
    md = lambda x: float(x.d_res.mean()) if len(x) else None   # noqa: E731
    r = {"off_season": mo(o), "def_season": md(d), "off_season_wo": mo(o[o.game_id != gid]), "def_season_wo": md(d[d.game_id != gid])}
    o4, d4 = o[o.game_id.isin(last4)], d[d.game_id.isin(last4)]
    r.update({"in_last4": gid in last4, "off_l4": mo(o4), "def_l4": md(d4), "off_l4_wo": mo(o4[o4.game_id != gid]), "def_l4_wo": md(d4[d4.game_id != gid])})
    for k in ("season", "season_wo", "l4", "l4_wo"):
        x, y = r[f"off_{k}"], r[f"def_{k}"]
        r[f"net_{k}"] = None if x is None or y is None else x - y
    return r


def build(seasons_pbp: dict, hist: list, p: pd.DataFrame, pf: pd.DataFrame, adj: dict, G: pd.DataFrame, Q: pd.DataFrame, S: int, W: int) -> dict:
    hist_db = pd.concat([combined_dropbacks(seasons_pbp[s]) for s in hist])
    cut = float(np.percentile(hist_db, PCTL))
    hist_bad = 0
    for s in hist:
        x = seasons_pbp[s]
        g = x.groupby("game_id").agg(w=("weather", "first"), r=("roof", "first"))
        db = combined_dropbacks(x)
        hist_bad += sum(weather(a, b)[0] and db.get(i, 999) < cut for i, a, b in zip(g.index, g.w, g.r))
    names = Q.set_index("passer_id").name_full.to_dict()
    ae = adj["epa"]
    sc = p[p.sc].copy()
    sc["o_res"] = sc.epa - ae["home"] * sc.is_home - sc.defteam.map(ae["def_eff"])
    sc["d_res"] = sc.epa - ae["home"] * sc.is_home - sc.posteam.map(ae["off_eff"])
    last4 = G.sort_values("week").groupby("team").tail(4).groupby("team").game_id.apply(set).to_dict()
    gm = p.groupby("game_id").agg(w=("weather", "first"), r=("roof", "first"), week=("week", "first"), home=("home_team", "first"), away=("away_team", "first"),
                                  hs=("home_score", "first"), a_s=("away_score", "first"))
    db26 = combined_dropbacks(p)
    db_tm = p[p.db].groupby(["game_id", "posteam"]).size()
    flagged = {}
    for gid, r in gm.iterrows():
        bad, label = weather(r.w, r.r)
        n = int(db26.get(gid, 0))
        if not (bad and n < cut):
            continue
        base = {"game_id": gid, "week": int(r.week), "weather": label, "dropbacks": n, "cut": cut,
                "label": f"{r.away} {int(r.a_s)} at {r.home} {int(r.hs)}, week {int(r.week)}"}
        for t, o in ((r.home, r.away), (r.away, r.home)):
            d = p[p.db & (p.game_id == gid) & (p.posteam == t)]
            lead = d.passer_id.value_counts()
            pid = lead.index[0] if len(lead) else None
            x = d[d.passer_id == pid]
            xa = x[x.att]
            flagged.setdefault(t, []).append({**base, "team": t, "opp": o, "team_dropbacks": int(db_tm.get((gid, t), 0)), "opp_dropbacks": int(db_tm.get((gid, o), 0)),
                                              "qb": names.get(pid, pid), "qb_dropbacks": int(len(x)), "qb_epa_db": float(x.epa.mean()) if len(x) else None,
                                              "qb_att": int(len(xa)), "qb_epa_att": float(xa.epa.mean()) if len(xa) else None,
                                              "qb_ints": int(x.int_.sum()), **_splits(sc, t, gid, last4.get(t, set()), ae)})
    # 2+ interceptions in the team's latest game
    latest = G.sort_values("week").groupby("team").tail(1).set_index("team").game_id.to_dict()
    ints = {}
    a = pf[pf.att & pf.passer_id.notna()]
    for t, gid in latest.items():
        x = a[(a.game_id == gid) & (a.posteam == t)]
        for pid, y in x.groupby("passer_id"):
            n_int = int(y.int_.sum())
            if n_int < INT_MIN:
                continue
            ch = y[y.is_catchable_ball.notna()]
            b = a[(a.passer_id == pid) & (a.game_id != gid)]
            bc = b[b.is_catchable_ball.notna()]
            week = int(y.week.iloc[0])
            rec = {"team": t, "qb": names.get(pid, pid), "week": week, "opp": str(y.defteam.iloc[0]), "ints": n_int, "charted": bool(len(ch)),
                   "worthy_ints": int((y.int_ & (y.is_interception_worthy == True)).sum()), "worthy_all": int((y.is_interception_worthy == True).sum()),
                   "att": int(len(ch)), "uncatchable": int((ch.is_catchable_ball == False).sum()),
                   "att_before": int(len(bc)), "uncatchable_before": int((bc.is_catchable_ball == False).sum()),
                   "worthy_before": int((bc.is_interception_worthy == True).sum())}
            rec["text"] = int_text(rec)
            ints.setdefault(t, []).append(rec)
    return {"flagged": flagged, "ints": ints, "cut": cut, "pctl": PCTL, "wind_min": WIND_MIN, "hist_games": int(len(hist_db)), "hist_seasons": [hist[0], hist[-1]],
            "hist_median": float(hist_db.median()), "hist_min": int(hist_db.min()), "hist_flagged": int(hist_bad), "caveat": CAVEAT}


def int_text(r: dict) -> str:
    head = f"{r['qb']} threw {r['ints']} interceptions in week {r['week']} against {r['opp']}"
    if not r["charted"]:
        return f"{head}; FTN has not charted that game yet."
    pc = lambda a, b: f"{a} of {b}"   # noqa: E731
    return (f"{head}: {pc(r['worthy_ints'], r['ints'])} charted interception-worthy; {pc(r['uncatchable'], r['att'])} attempts uncatchable, "
            f"against {pc(r['uncatchable_before'], r['att_before'])} in his earlier games "
            f"({r['worthy_all']} interception-worthy throws in that game, {r['worthy_before']} before). {CAVEAT}")


def qc_line(U: dict) -> str:
    n = len({x["game_id"] for v in U["flagged"].values() for x in v})
    return (f"Unusual games: rain, snow or {U['wind_min']}+ mph wind and under {U['cut']:.0f} combined dropbacks (bottom {U['pctl']}% of {U['hist_games']} "
            f"{U['hist_seasons'][0]}-{str(U['hist_seasons'][1])[-2:]} games, median {U['hist_median']:.0f}, lowest {U['hist_min']}): {n} flagged this season, "
            f"{U['hist_flagged']} met both tests in {U['hist_seasons'][0]}-{str(U['hist_seasons'][1])[-2:]}. "
            f"{sum(len(v) for v in U['ints'].values())} quarterbacks threw 2+ interceptions in their team's latest game.")
