"""Offensive player usage, game logs and position rankings for the team analytics report.

Everything comes from the same nflverse play-by-play as the rest of the report (rbsdm.com's box scores are built from it
too), plus the weekly rosters (position, name), snap counts (offensive snap share) and Next Gen weekly rows (rush yards
over expected, receiver separation). Per player and team, so a traded player appears under each team with that team's
games only.
  - targets: pass attempts with a receiver (sacks, scrambles and spikes excluded); receiving yards and TDs on completions
  - carries: designed rushes (scrambles excluded); shares are of the team's designed rushes, QB runs included
  - last 3: the team's last three games in the window
Rankings use minimum volumes (RB_MIN carries, REC_MIN targets) and are season figures only (no shrinkage). Receiver EPA
includes the quarterback's throw and the play call, so it is a usage-and-production measure, not a pure receiver grade.

compute.py calls build() and writes usage.json with the rest of the bundle.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from depth import OUT_CLASSES, STATUS_TEXT, _norm

RB_MIN, REC_MIN = 40, 20
OUT, STATUS = OUT_CLASSES, STATUS_TEXT
TGT_FLAG, CAR_FLAG = 0.20, 0.35   # a caution when players now out had this share of targets / carries


def _f(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)


def build(p: pd.DataFrame, season: int, through_week: int, absences: pd.DataFrame, fetch) -> dict:
    ros = fetch(f"weekly_rosters/roster_weekly_{season}.parquet").dropna(subset=["gsis_id"]).copy()
    ros["team"] = ros.team.replace({"LAR": "LA"})
    last = ros.sort_values("week").drop_duplicates("gsis_id", keep="last").set_index("gsis_id")
    pos = last.position.replace({"FB": "RB"})
    name = last.full_name

    # snap counts: PFR ids -> gsis through the roster, else team + name
    sn = fetch(f"snap_counts/snap_counts_{season}.parquet")
    sn = sn[(sn.week <= through_week) & (sn.game_type == "REG")].copy()
    sn["team"] = sn.team.replace({"LAR": "LA"})
    pfr_g = ros.dropna(subset=["pfr_id"]).drop_duplicates("pfr_id").set_index("pfr_id").gsis_id.to_dict()
    nm_g = {}
    for t, n, g in ros[["team", "full_name", "gsis_id"]].drop_duplicates().itertuples(index=False):
        nm_g.setdefault((t, _norm(n)), set()).add(g)
    def gsis_of(t, n, pid):
        g = pfr_g.get(pid)
        if g is None:
            c = nm_g.get((t, _norm(n)), set())
            g = next(iter(c)) if len(c) == 1 else None
        return g
    sn["gsis"] = [gsis_of(t, n, pid) for t, n, pid in zip(sn.team, sn.player, sn.pfr_player_id)]
    snp = sn[sn.offense_snaps > 0].groupby(["team", "gsis"]).agg(snap_pct=("offense_pct", "mean"), snap_games=("game_id", "nunique"))

    # status from the report's absences (snap-count names)
    st = {}
    for a in absences.itertuples():
        pid = sn[(sn.team == a.team) & (sn.player == a.player)].pfr_player_id.head(1)
        g = gsis_of(a.team, a.player, pid.iloc[0] if len(pid) else None)
        if g:
            st[(a.team, g)] = a.status_class

    tg = p[p.att & p.receiver_player_id.notna()].copy()
    tg["rec_yds"] = np.where(tg.complete_pass == 1, tg.yards_gained, 0)
    tg["rec_td"] = (tg.pass_touchdown == 1).astype(int)   # not `touchdown`, which also marks a defensive return after a catch
    tg["rz"] = tg.yardline_100 <= 20
    ca = p[p.drush & p.rusher_player_id.notna()].copy()
    ca["rz"] = ca.yardline_100 <= 20
    ca["gl"] = ca.yardline_100 <= 5
    ca["rush_td"] = (ca.rush_touchdown == 1).astype(int)

    # last three games per team
    gw = p.groupby(["posteam", "week"]).size().reset_index()[["posteam", "week"]]
    last3 = {t: set(g.week.nlargest(3)) for t, g in gw.groupby("posteam")}
    tg["l3"] = [w in last3[t] for t, w in zip(tg.posteam, tg.week)]
    ca["l3"] = [w in last3[t] for t, w in zip(ca.posteam, ca.week)]

    team_tgt, team_air = tg.groupby("posteam").size(), tg.groupby("posteam").air_yards.sum()
    team_car = ca.groupby("posteam").size()
    team_tgt3, team_car3 = tg[tg.l3].groupby("posteam").size(), ca[ca.l3].groupby("posteam").size()
    team_rzt, team_rzc = tg[tg.rz].groupby("posteam").size(), ca[ca.rz].groupby("posteam").size()

    r = tg.groupby(["posteam", "receiver_player_id"]).agg(
        targets=("epa", "size"), rec=("complete_pass", "sum"), rec_yds=("rec_yds", "sum"), rec_td=("rec_td", "sum"),
        air=("air_yards", "sum"), adot=("air_yards", "mean"), epa_tgt=("epa", "mean"), epa_rec_total=("epa", "sum"),
        sr_tgt=("success", "mean"), rz_tgt=("rz", "sum"), tgt_games=("game_id", "nunique"))
    r["yac_pr"] = tg[tg.complete_pass == 1].groupby(["posteam", "receiver_player_id"]).yards_after_catch.mean()
    r["yacoe_pr"] = tg[tg.comp].groupby(["posteam", "receiver_player_id"]).yacoe.mean()
    r["tgt_l3"] = tg[tg.l3].groupby(["posteam", "receiver_player_id"]).size()
    r.index.names = ["team", "gsis"]
    c = ca.groupby(["posteam", "rusher_player_id"]).agg(
        carries=("epa", "size"), rush_yds=("yards_gained", "sum"), rush_td=("rush_td", "sum"), epa_car=("epa", "mean"),
        epa_rush_total=("epa", "sum"), sr_car=("success", "mean"), stuff=("stuffed", "mean"),
        expl_run=("expl_run", "mean"), rz_car=("rz", "sum"), gl_car=("gl", "sum"), car_games=("game_id", "nunique"))
    c["car_l3"] = ca[ca.l3].groupby(["posteam", "rusher_player_id"]).size()
    c.index.names = ["team", "gsis"]
    U = r.join(c, how="outer").reset_index()
    U = U.join(snp, on=["team", "gsis"])

    # Next Gen weekly rows: rush yards over expected, separation
    nr = fetch("nextgen_stats/ngs_rushing.parquet")
    nr = nr[(nr.season == season) & nr.week.between(1, through_week) & (nr.season_type == "REG")]
    ng_r = nr.groupby("player_gsis_id").agg(ryoe=("rush_yards_over_expected", "sum"), ngs_att=("rush_attempts", "sum"))
    nv = fetch("nextgen_stats/ngs_receiving.parquet")
    nv = nv[(nv.season == season) & nv.week.between(1, through_week) & (nv.season_type == "REG")].copy()
    nv["sep_x"] = nv.avg_separation * nv.targets
    ng_v = nv.groupby("player_gsis_id").agg(sep_x=("sep_x", "sum"), ngs_tgt=("targets", "sum"))

    rows = []
    for x in U.itertuples(index=False):
        t, g = x.team, x.gsis
        tgt, car = (x.targets if x.targets == x.targets else 0), (x.carries if x.carries == x.carries else 0)
        pp = pos.get(g, "other")
        sc = st.get((t, g))
        rr = ng_r.loc[g] if g in ng_r.index else None
        vv = ng_v.loc[g] if g in ng_v.index else None
        rows.append({
            "id": g, "name": str(name.get(g, g)), "team": t, "pos": pp,
            "games": int(max(x.tgt_games if x.tgt_games == x.tgt_games else 0, x.car_games if x.car_games == x.car_games else 0)),
            "snap_pct": _f(x.snap_pct), "status": STATUS.get(sc, ""), "out": sc in OUT,
            "targets": int(tgt), "tgt_share": _f(tgt / team_tgt.get(t, np.nan)),
            "air_share": _f(x.air / team_air.get(t, np.nan)) if tgt else None,
            "rec": int(x.rec) if tgt else 0, "rec_yds": int(x.rec_yds) if tgt else 0, "rec_td": int(x.rec_td) if tgt else 0,
            "ypt": _f(x.rec_yds / tgt) if tgt else None, "epa_tgt": _f(x.epa_tgt) if tgt else None,
            "sr_tgt": _f(x.sr_tgt) if tgt else None, "adot": _f(x.adot) if tgt else None,
            "catch_rate": _f(x.rec / tgt) if tgt else None, "yac_pr": _f(x.yac_pr), "yacoe_pr": _f(x.yacoe_pr),
            "rz_tgt": int(x.rz_tgt) if tgt else 0, "rz_tgt_share": _f(x.rz_tgt / team_rzt.get(t, np.nan)) if tgt else None,
            "tgt_share_l3": _f((x.tgt_l3 if x.tgt_l3 == x.tgt_l3 else 0) / team_tgt3.get(t, np.nan)) if tgt else None,
            "carries": int(car), "car_share": _f(car / team_car.get(t, np.nan)),
            "rush_yds": int(x.rush_yds) if car else 0, "rush_td": int(x.rush_td) if car else 0,
            "ypc": _f(x.rush_yds / car) if car else None, "epa_car": _f(x.epa_car) if car else None,
            "sr_car": _f(x.sr_car) if car else None, "stuff": _f(x.stuff) if car else None,
            "expl_run": _f(x.expl_run) if car else None,
            "rz_car": int(x.rz_car) if car else 0, "gl_car": int(x.gl_car) if car else 0,
            "rz_car_share": _f(x.rz_car / team_rzc.get(t, np.nan)) if car else None,
            "car_share_l3": _f((x.car_l3 if x.car_l3 == x.car_l3 else 0) / team_car3.get(t, np.nan)) if car else None,
            "epa_total": _f((x.epa_rec_total if tgt else 0) + (x.epa_rush_total if car else 0)),
            "ryoe_att": _f(rr.ryoe / rr.ngs_att) if rr is not None and rr.ngs_att else None,
            "sep": _f(vv.sep_x / vv.ngs_tgt) if vv is not None and vv.ngs_tgt else None,
            "yds_total": int((x.rec_yds if tgt else 0) + (x.rush_yds if car else 0)),
            "td_total": int((x.rec_td if tgt else 0) + (x.rush_td if car else 0)),
        })
    P = pd.DataFrame(rows)

    # game logs: per team, per game, each player with a target or carry
    tg_g = tg.groupby(["posteam", "week", "receiver_player_id"]).agg(t=("epa", "size"), c=("complete_pass", "sum"), y=("rec_yds", "sum"), td=("rec_td", "sum"))
    ca_g = ca.groupby(["posteam", "week", "rusher_player_id"]).agg(n=("epa", "size"), y=("yards_gained", "sum"), td=("rush_td", "sum"))
    opp = p.groupby(["posteam", "week"]).agg(opp=("defteam", "first"), home=("is_home", "first"))
    logs = {}
    for t in sorted(p.posteam.dropna().unique()):
        wks = sorted(gw[gw.posteam == t].week)
        games = [{"week": int(w), "opp": ("vs " if opp.loc[(t, w)].home >= 0 else "at ") + opp.loc[(t, w)].opp} for w in wks]
        pl = P[(P.team == t) & ((P.targets > 0) | (P.carries > 0)) & P.pos.isin(["WR", "TE", "RB", "QB"])]
        pl = pl.sort_values(["targets", "carries"], ascending=False)
        prow = []
        for x in pl.itertuples():
            cells = []
            for w in wks:
                a = tg_g.loc[(t, w, x.id)] if (t, w, x.id) in tg_g.index else None
                b = ca_g.loc[(t, w, x.id)] if (t, w, x.id) in ca_g.index else None
                cells.append({"t": int(a.t) if a is not None else 0, "c": int(a.c) if a is not None else 0,
                              "ry": int(a.y) if a is not None else 0, "rtd": int(a.td) if a is not None else 0,
                              "n": int(b.n) if b is not None else 0, "uy": int(b.y) if b is not None else 0,
                              "utd": int(b.td) if b is not None else 0})
            if x.pos == "QB" and not x.carries:
                continue
            prow.append({"name": x.name, "pos": x.pos, "status": x.status, "cells": cells})
        logs[t] = {"games": games, "players": prow}

    teams = {}
    for t, x in P.groupby("team"):
        o = x[x.out]
        teams[t] = {"tgt_out_share": float(o.tgt_share.fillna(0).sum()), "car_out_share": float(o.car_share.fillna(0).sum()),
                    "tgt_out_names": [f"{r.name} ({r.tgt_share:.0%} of targets)" for r in o[o.targets > 0].itertuples()],
                    "car_out_names": [f"{r.name} ({r.car_share:.0%} of carries)" for r in o[o.carries > 0].itertuples()]}

    def rank_rows(m):
        out = P[m].replace({np.nan: None}).to_dict("records")
        for r in out:
            r["label"], r["sub"] = r["name"], r["team"]
        return out
    skill = P[P.pos.isin(["WR", "TE", "RB"]) | ((P.pos == "QB") & (P.carries > 0))]
    team_players = {t: x.sort_values(["targets", "carries"], ascending=False).replace({np.nan: None}).to_dict("records")
                    for t, x in skill.groupby("team")}
    rb = rank_rows((P.pos == "RB") & (P.carries >= RB_MIN))
    wr = rank_rows((P.pos == "WR") & (P.targets >= REC_MIN))
    te = rank_rows((P.pos == "TE") & (P.targets >= REC_MIN))
    usage_by = {(r["team"], r["id"]): r for r in P.replace({np.nan: None}).to_dict("records")}
    return {"rb": rb, "wr": wr, "te": te, "logs": logs, "teams": teams, "team_players": team_players, "rb_min": RB_MIN, "rec_min": REC_MIN,
            "tgt_flag": TGT_FLAG, "car_flag": CAR_FLAG,
            "absent_usage": [{"team": t, "player": a_name, **{k: usage_by.get((t, g), {}).get(k) for k in
                              ("tgt_share", "car_share", "targets", "carries", "tgt_share_l3", "car_share_l3")}}
                             for t, a_name, g in _absent_ids(absences, sn, gsis_of)]}


def _absent_ids(absences, sn, gsis_of):
    out = []
    for a in absences[absences.unit == "off"].itertuples():
        pid = sn[(sn.team == a.team) & (sn.player == a.player)].pfr_player_id.head(1)
        g = gsis_of(a.team, a.player, pid.iloc[0] if len(pid) else None)
        out.append((a.team, a.player, g))
    return out
