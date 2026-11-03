"""New arrivals: the mirror image of absences.

A player is an arrival when his latest weekly-roster team differs from his team in an earlier 2026 week (trade,
waiver claim, signing from another team), or when he joined the team during the season (from its practice squad,
another practice squad or free agency) and now plays 40%+ of its snaps. To keep the list to players who matter, an
arrival is shown when he is on the active roster now and was a regular elsewhere (40%+ of snaps in at least two games for
his previous team, the same line as for the new team) or plays 40%+ of snaps in his games for the new team.

Departures are the other half: former regulars of a team who are now on another team's roster, whatever their status
there. Only the weekly rosters show a move, so a trade appears after the next roster update; refresh_status.py
re-downloads the rosters and rebuilds this file.

His 2026 sample comes from the play-by-play (sacks, QB hits, targets, carries, dropbacks), PFR pressures (games with
PFR data only), and for linemen and defensive backs the new team's unit numbers in games he played 50%+ of snaps.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

ROLE = {"QB": "qb", "RB": "skill", "FB": "skill", "WR": "skill", "TE": "skill", "T": "ol", "G": "ol", "C": "ol", "OL": "ol",
        "DE": "rush", "DT": "rush", "NT": "rush", "DL": "rush", "OLB": "rush", "LB": "rush", "ILB": "rush", "MLB": "rush",
        "CB": "db", "S": "db", "FS": "db", "SS": "db", "DB": "db"}
SHARE_MIN = REG_SHARE = 0.40


def _f(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)


def build(S: int, W: int, p: pd.DataFrame, fetch) -> dict:
    ros = fetch(f"weekly_rosters/roster_weekly_{S}.parquet").dropna(subset=["gsis_id"]).copy()
    ros["team"] = ros.team.replace({"LAR": "LA"})
    sn = fetch(f"snap_counts/snap_counts_{S}.parquet")
    sn = sn[(sn.week <= W) & (sn.game_type == "REG")].copy()
    sn["team"] = sn.team.replace({"LAR": "LA"})
    sn["share"] = sn[["offense_pct", "defense_pct"]].max(axis=1)
    sn["snaps"] = sn[["offense_snaps", "defense_snaps"]].max(axis=1)
    plist = fetch("players/players.parquet")
    g2p = plist.dropna(subset=["pfr_id", "gsis_id"]).drop_duplicates("gsis_id").set_index("gsis_id").pfr_id.to_dict()
    g2p.update(ros.dropna(subset=["pfr_id"]).drop_duplicates("gsis_id").set_index("gsis_id").pfr_id.to_dict())
    pfr = fetch(f"pfr_advstats/advstats_week_def_{S}.parquet")
    pfr = pfr[(pfr.week <= W) & (pfr.game_type == "REG")]
    press = pfr.groupby("pfr_player_id").agg(pressures=("def_pressures", "sum"), pfr_games=("game_id", "nunique"))
    team_games = sn.groupby("team").game_id.nunique()
    team_weeks = sn.groupby("team").week.apply(lambda w: sorted(w.unique())).to_dict()

    r = ros[ros.week <= W + 1].sort_values("week")
    out, dep, n_former, n_recent = {}, {}, 0, 0
    for g, x in r.groupby("gsis_id"):
        last = x.iloc[-1]
        t_now = last.team
        if last.status in ("CUT", "RET", "TRD", "TRT"):
            continue
        others = x[x.team != t_now]
        mine = x[x.team == t_now]
        if len(others):
            prev = others.iloc[-1]
            stint = mine[mine.week > prev.week]
            if stint.empty:
                continue
            first_week, prev_team, kind = int(stint.week.min()), prev.team, "trade or move"
        else:
            # joined during the season: no roster row for the team in week 1, or practice squad (DEV) before
            # becoming active
            first_row = mine.iloc[0]
            act = mine[mine.status == "ACT"]
            if first_row.week > 1:
                first_week, prev_team, kind = int(first_row.week), None, "signed in season"
            elif first_row.status == "DEV" and len(act):
                first_week, prev_team, kind = int(act.week.min()), None, "promoted from the practice squad"
            else:
                continue
        pid = g2p.get(g)
        ps = sn[sn.pfr_player_id == pid] if pid else sn.iloc[0:0]
        new = ps[(ps.team == t_now) & (ps.week >= first_week)]
        old = ps[(ps.team == prev_team)] if prev_team else ps.iloc[0:0]
        former_reg = bool(len(old) >= 2 and old.share.mean() >= REG_SHARE)
        new_share = float(new.share.mean()) if len(new) else None
        pos = str(last.position)
        if former_reg:
            lw = int(old.week.max())
            since = sum(1 for w in team_weeks.get(prev_team, []) if w > lw)
            dep.setdefault(prev_team, []).append({
                "team": prev_team, "name": str(last.full_name), "pos": pos, "new_team": t_now, "first_week_new": first_week, "last_week": lw,
                "share": float(old.share.mean()), "games": int(len(old)), "team_games": int(team_games.get(prev_team, 0)),
                "games_since": since, "new": since <= 1, "status_now": str(last.status)})
        # arrivals are players on the active roster now (not the practice squad, reserve list or game-day inactives)
        if last.status != "ACT" or not (former_reg or (new_share is not None and new_share >= SHARE_MIN)):
            continue
        role = ROLE.get(pos, "other")
        rec = {"team": t_now, "name": str(last.full_name), "pos": pos, "kind": kind, "prev_team": prev_team,
               "first_week": first_week, "status": str(last.status), "games_new": int(len(new)), "snaps_new": int(new.snaps.sum()),
               "share_new": new_share, "last_share": float(new.sort_values("week").share.iloc[-1]) if len(new) else None,
               "games_prev": int(len(old)), "share_prev": float(old.share.mean()) if len(old) else None,
               "former_regular": former_reg, "role": role,
               "recent": first_week >= W - 1}
        rec.update(sample(g, pid, role, p, sn, new, t_now, press))
        rec["text"] = text(rec)
        out.setdefault(t_now, []).append(rec)
        n_former += former_reg
        n_recent += rec["recent"]
    for t in out:
        out[t].sort(key=lambda a: (-a["first_week"], -(a["share_new"] or 0)))
    for t in dep:
        for x in dep[t]:
            x["text"] = dep_text(x)
        dep[t].sort(key=lambda a: (-a["last_week"], -a["share"]))
    return {"teams": out, "departures": dep, "n": sum(len(v) for v in out.values()), "n_former_regular": int(n_former), "n_recent": int(n_recent),
            "n_departures": sum(len(v) for v in dep.values()), "n_new_departures": sum(x["new"] for v in dep.values() for x in v),
            "share_min": SHARE_MIN, "through_week": W, "roster_week": int(r.week.max())}


def qc_line(A: dict, W: int) -> str:
    return (f"Arrivals: {A['n']} active players on a new team since week 1 who were regulars elsewhere or play 40%+ of snaps "
            f"({A['n_former_regular']} former regulars elsewhere, {A['n_recent']} arrived in weeks {W - 1}-{W + 1}). "
            f"Departures: {A['n_departures']} former regulars now on another team ({A['n_new_departures']} new). Rosters through week {A['roster_week']}.")


def dep_text(d: dict) -> str:
    return (f"{d['name']} ({d['pos']}, to {d['new_team']}): last game for {d['team']} week {d['last_week']}, {100 * d['share']:.0f}% of snaps, "
            f"played {d['games']} of its {d['team_games']} games")


def sample(g, pid, role, p, sn, new, team, press):
    """His 2026 sample, all teams, from the play-by-play (plus PFR pressures, and unit splits for OL/DB)."""
    sc = p[p.sc]
    q = {}
    if role == "rush":
        sacks = (p.sack_player_id == g).sum() + 0.5 * ((p.half_sack_1_player_id == g).sum() + (p.half_sack_2_player_id == g).sum())
        hits = ((p.qb_hit_1_player_id == g) | (p.qb_hit_2_player_id == g)).sum()
        pr = press.loc[pid] if pid in press.index else None
        q.update({"sacks": float(sacks), "qb_hits": int(hits), "pressures": None if pr is None else int(pr.pressures),
                  "pfr_games": None if pr is None else int(pr.pfr_games)})
    elif role == "skill":
        t = sc[sc.att & (sc.receiver_player_id == g)]
        c = sc[sc.drush & (sc.rusher_player_id == g)]
        q.update({"targets": int(len(t)), "epa_tgt": _f(t.epa.mean()) if len(t) else None, "rec_yds": int(t.yards_gained.where(t.complete_pass == 1, 0).sum()),
                  "carries": int(len(c)), "epa_car": _f(c.epa.mean()) if len(c) else None})
    elif role == "qb":
        d = sc[sc.db & (sc.passer_id == g)]
        q.update({"dropbacks": int(len(d)), "epa_db": _f(d.epa.mean()) if len(d) else None})
    elif role in ("ol", "db"):
        started = set(new[new.share >= 0.5].game_id)
        db = p[p.db & ((p.posteam if role == "ol" else p.defteam) == team)]
        a, b = db[db.game_id.isin(started)], db[~db.game_id.isin(started)]
        q.update({"starts_new": len(started), "db_with": int(len(a)), "db_without": int(len(b)),
                  "epa_db_with": _f(a.epa.mean()) if len(a) else None, "epa_db_without": _f(b.epa.mean()) if len(b) else None})
    return q


def text(a: dict) -> str:
    e = lambda v: "n/a" if v is None else f"{v:+.3f}"   # noqa: E731
    pc = lambda v: "n/a" if v is None else f"{100 * v:.0f}%"   # noqa: E731
    src = f"from {a['prev_team']}" if a["prev_team"] else a["kind"]
    head = (f"{a['name']} ({a['pos']}, {src}, first week {a['first_week']}): " + (
        f"{a['games_new']} game{'' if a['games_new'] == 1 else 's'} and {a['snaps_new']} snaps for {a['team']} ({pc(a['share_new'])} of snaps)"
        if a["games_new"] else f"no games yet for {a['team']}"))
    if a["former_regular"]:
        head += f"; a regular for {a['prev_team']} ({pc(a['share_prev'])} of snaps in {a['games_prev']} games)"
    r = a["role"]
    if r == "rush":
        pl = lambda n, w: f"{n:g} {w}" + ("" if n == 1 else "s")   # noqa: E731
        tail = f"2026: {pl(a['sacks'], 'sack')}, {pl(a['qb_hits'], 'QB hit')}" + (
            f", {pl(a['pressures'], 'PFR pressure')} in {pl(a['pfr_games'], 'game')} with PFR data" if a.get("pressures") is not None else "")
    elif r == "skill":
        bits = []
        if a["targets"]:
            bits.append(f"{a['targets']} targets" + (f" ({e(a['epa_tgt'])} EPA/target)" if a["targets"] >= 10 else " (too few for a rate)"))
        if a["carries"]:
            bits.append(f"{a['carries']} carries" + (f" ({e(a['epa_car'])} EPA/carry)" if a["carries"] >= 10 else " (too few for a rate)"))
        tail = "2026: " + (", ".join(bits) if bits else "no targets or carries")
    elif r == "qb":
        tail = f"2026: {a['dropbacks']} dropbacks ({e(a['epa_db'])} EPA/dropback)" if a["dropbacks"] else "2026: no dropbacks"
    elif r in ("ol", "db"):
        unit = "offence" if r == "ol" else "defence"
        if a["db_with"] >= 100 and a["db_without"] >= 100:
            tail = (f"{a['team']} {unit} EPA/dropback{' allowed' if r == 'db' else ''} in his {a['starts_new']} starts {e(a['epa_db_with'])} "
                    f"({a['db_with']} dropbacks) vs other games {e(a['epa_db_without'])} ({a['db_without']})")
        else:
            tail = f"{a['starts_new']} start{'' if a['starts_new'] == 1 else 's'} for {a['team']}; too few dropbacks for a with/without split ({a['db_with']} with, {a['db_without']} without)"
    else:
        tail = ""
    return head + (". " + tail if tail else "") + "."
