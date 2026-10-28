"""Depth charts and Next Gen receiving for the team analytics report.

Depth charts (nflverse `depth_charts`, daily ESPN snapshots) are used for two things only, both cross-checked
against snap counts because team-published charts are often stale:
  - next man up: for each absent regular, the next player listed in his depth-chart slot (skipping other absent
    regulars), with that player's snaps so far;
  - starter checks: the listed QB1 and five OL starters against who actually played the team's latest game.
Next Gen receiving (nflverse `nextgen_stats/ngs_receiving`, season rows) gives target-weighted receiver separation,
cushion and YAC over expected per team.

Run on its own (downloads fresh copies with --refresh):
    python scripts/team_analytics/depth.py --season 2026 --through-week 7 [--refresh]
compute.py also calls build() and writes depth.json with the rest of the bundle.
"""
from __future__ import annotations

import argparse
import json
import re

import numpy as np
import pandas as pd

OFF_GRP = "3WR 1TE"
DEF_GRPS = ("Base 3-4 D", "Base 4-3 D")
OL_SLOTS = ["LT", "LG", "C", "RG", "RT"]
OL_POS = {"T", "G", "C", "OL", "OT", "OG"}
OUT_CLASSES = ("confirmed: reserve list", "listed Out/Doubtful")


SUFFIX = {"jr", "sr", "ii", "iii", "iv", "v"}


def _norm(name: str) -> str:
    toks = re.sub(r"[^a-z ]", "", str(name).lower().replace("-", " ")).split()
    return " ".join(t for t in toks if t not in SUFFIX)


def _initial(name: str) -> str:
    toks = _norm(name).split()
    return f"{toks[0][0]} {toks[-1]}" if len(toks) >= 2 else _norm(name)


def _ids(snaps: pd.DataFrame, ros: pd.DataFrame):
    """Link snap-count players (PFR ids, PFR names) to gsis ids. The rosters carry pfr_id for most players but not
    offensive linemen, so fall back to the team plus a normalised name (suffixes dropped), then first initial + last name
    when that is unique on the team."""
    r = ros.dropna(subset=["gsis_id"]).copy()
    r["team"] = r.team.replace({"LAR": "LA"})
    pfr_gsis = r.dropna(subset=["pfr_id"]).drop_duplicates("pfr_id").set_index("pfr_id").gsis_id.to_dict()
    by_name, by_init = {}, {}
    for t, g, full, fb, last in zip(r.team, r.gsis_id, r.full_name, r.football_name, r.last_name):
        for n in {full, f"{fb} {last}"}:
            by_name.setdefault((t, _norm(n)), set()).add(g)
        by_init.setdefault((t, _initial(full)), set()).add(g)
    snap_gsis = {}
    for t, n, pid in snaps.drop_duplicates(["team", "player"])[["team", "player", "pfr_player_id"]].itertuples(index=False):
        g = pfr_gsis.get(pid)
        if g is None:
            c = by_name.get((t, _norm(n))) or by_init.get((t, _initial(n))) or set()
            g = next(iter(c)) if len(c) == 1 else None
        if g is not None:
            snap_gsis[(t, n)] = g
    gsis_pfr = {g: pid for (t, n), g in snap_gsis.items()
                for pid in snaps[(snaps.team == t) & (snaps.player == n)].pfr_player_id.head(1)}
    pid_gsis = {pid: snap_gsis[(t, n)] for t, n, pid in
                snaps.drop_duplicates(["team", "player"])[["team", "player", "pfr_player_id"]].itertuples(index=False)
                if (t, n) in snap_gsis}
    return snap_gsis, pid_gsis, gsis_pfr, by_name


def _snaps_summary(snaps: pd.DataFrame, pfr: str | None, unit: str) -> dict:
    col, pct = ("offense_snaps", "offense_pct") if unit == "off" else ("defense_snaps", "defense_pct")
    s = snaps[snaps.pfr_player_id == pfr] if pfr else snaps.iloc[0:0]
    if s.empty:
        return {"snaps": 0, "games": 0, "last_share": None}
    s = s.sort_values("week")
    return {"snaps": int(s[col].sum()), "games": int((s[col] > 0).sum()), "last_share": float(s[pct].iloc[-1])}


def depth_build(dc: pd.DataFrame, snaps: pd.DataFrame, ros: pd.DataFrame, absences: pd.DataFrame) -> dict:
    snap_gsis, pfr_gsis, gsis_pfr, by_name = _ids(snaps, ros)
    dc = dc.dropna(subset=["gsis_id"]).copy()
    # the chart occasionally carries a stale gsis id (e.g. an old player's); prefer the roster's id for the same
    # team and name when the roster has exactly one match
    fix = {}
    for t, n, g in dc[["team", "player_name", "gsis_id"]].drop_duplicates().itertuples(index=False):
        c = by_name.get((t, _norm(n)), set())
        if len(c) == 1 and g not in c:
            fix[(t, n, g)] = next(iter(c))
    if fix:
        dc["gsis_id"] = [fix.get((t, n, g), g) for t, n, g in zip(dc.team, dc.player_name, dc.gsis_id)]
    dc["day"] = dc.dt.str[:10]
    latest_dt = dc.groupby("team").dt.max()
    cur = dc[dc.dt == dc.team.map(latest_dt)]
    gsis_of = lambda team, name: snap_gsis.get((team, name))   # noqa: E731
    absent = absences[absences.status_class.isin(OUT_CLASSES)].copy()
    absent["gsis"] = [gsis_of(t, n) for t, n in zip(absent.team, absent.player)]
    out_ids = absent.groupby("team").gsis.apply(lambda s: set(s.dropna())).to_dict()

    rows = []
    for a in absences.itertuples():
        g = gsis_of(a.team, a.player)
        grps = (OFF_GRP,) if a.unit == "off" else DEF_GRPS
        rec = {"team": a.team, "player": a.player, "slot": None, "next_up": None, "next_up_rank": None,
               "still_first": False, "note": ""}
        if g is None:
            rec["note"] = "not matched to a depth-chart id"
            rows.append(rec)
            continue
        mine = cur[(cur.team == a.team) & (cur.gsis_id == g) & cur.pos_grp.isin(grps)]
        if mine.empty:                                   # dropped from the chart (e.g. reserve list): use his last listing
            hist = dc[(dc.team == a.team) & (dc.gsis_id == g) & dc.pos_grp.isin(grps)]
            if hist.empty:
                rec["note"] = "never listed on the team's depth chart"
                rows.append(rec)
                continue
            mine = hist[hist.dt == hist.dt.max()]
            rec["note"] = f"no longer listed (last listed {mine.day.iloc[0]})"
        top = mine.sort_values("pos_rank").iloc[0]
        slot = cur[(cur.team == a.team) & (cur.pos_grp == top.pos_grp) & (cur.pos_slot == top.pos_slot)].sort_values("pos_rank")
        if slot.empty:                                   # formation changed: fall back to the same position label
            slot = cur[(cur.team == a.team) & cur.pos_grp.isin(grps) & (cur.pos_abb == top.pos_abb)].sort_values("pos_rank")
        rec["slot"] = str(top.pos_abb)
        rec["still_first"] = bool(len(slot) and slot.gsis_id.iloc[0] == g)
        skip = out_ids.get(a.team, set()) | {g}
        nxt = slot[~slot.gsis_id.isin(skip)]
        if nxt.empty:
            rec["note"] = (rec["note"] + "; " if rec["note"] else "") + "no other player listed in the slot"
        else:
            n = nxt.iloc[0]
            rec["next_up"], rec["next_up_rank"] = str(n.player_name), int(slot.gsis_id.tolist().index(n.gsis_id) + 1)
            rec.update({f"next_up_{k}": v for k, v in _snaps_summary(snaps, gsis_pfr.get(n.gsis_id), a.unit).items()})
        rows.append(rec)

    checks = {}
    for team, c in cur.groupby("team"):
        off = c[c.pos_grp == OFF_GRP]
        s = snaps[snaps.team == team]
        last = s[s.week == s.week.max()]
        qb = off[off.pos_abb == "QB"].sort_values("pos_rank")
        qb_listed = str(qb.player_name.iloc[0]) if len(qb) else None
        lq = last[last.position == "QB"].sort_values("offense_snaps", ascending=False)
        qb_last = str(lq.player.iloc[0]) if len(lq) else None
        qb_match = bool(len(qb) and len(lq) and pfr_gsis.get(lq.pfr_player_id.iloc[0]) == qb.gsis_id.iloc[0])
        ol = off[off.pos_abb.isin(OL_SLOTS)].sort_values("pos_rank").drop_duplicates("pos_abb")
        ol_ids = dict(zip(ol.gsis_id, ol.pos_abb + " " + ol.player_name))
        lo = last[last.position.isin(OL_POS)].sort_values("offense_snaps", ascending=False).head(5)
        lo_ids = {pfr_gsis.get(p): n for p, n in zip(lo.pfr_player_id, lo.player)}
        checks[team] = {"qb_listed": qb_listed, "qb_last": qb_last, "qb_match": qb_match, "last_week": int(s.week.max()),
                        "ol_new": [v for k, v in ol_ids.items() if k not in lo_ids],
                        "ol_dropped": [v for k, v in lo_ids.items() if k not in ol_ids]}
    return {"as_of": str(dc.dt.max()), "absences": rows, "checks": checks, "ids_repaired": len(fix)}


def receiving_build(ngs: pd.DataFrame, season: int) -> dict:
    s = ngs[(ngs.season == season) & (ngs.season_type == "REG") & (ngs.week == 0)].copy()
    out = {}
    for team, g in s.groupby("team_abbr"):
        w, rec = g.targets, g.receptions
        top = g.sort_values("targets", ascending=False).iloc[0]
        out[team] = {"players": int(len(g)), "targets": int(w.sum()),
                     "separation": float(np.average(g.avg_separation, weights=w)),
                     "cushion": float(np.average(g.avg_cushion, weights=w)),
                     "air_yards": float(np.average(g.avg_intended_air_yards, weights=w)),
                     "yacoe": float(np.average(g.avg_yac_above_expectation, weights=rec)) if rec.sum() else None,
                     "catch_pct": float(rec.sum() / w.sum() * 100),
                     "top": f"{top.player_display_name} ({top.player_position}, {top.avg_separation:.1f} yd)"}
    lg = {k: float(np.average(s[c], weights=s.targets)) for k, c in
          (("separation", "avg_separation"), ("cushion", "avg_cushion"), ("air_yards", "avg_intended_air_yards"))}
    return {"teams": out, "league": lg, "min_note": "Next Gen season rows cover qualifying receivers only"}


def build(season: int, through_week: int, absences: pd.DataFrame, fetch) -> dict:
    snaps = fetch(f"snap_counts/snap_counts_{season}.parquet")
    snaps = snaps[(snaps.week <= through_week) & (snaps.game_type == "REG")].copy()
    snaps["team"] = snaps.team.replace({"LAR": "LA"})
    ros = fetch(f"weekly_rosters/roster_weekly_{season}.parquet")
    dc = fetch(f"depth_charts/depth_charts_{season}.parquet")
    dc["team"] = dc.team.replace({"LAR": "LA"})
    ngs = fetch("nextgen_stats/ngs_receiving.parquet")
    ngs["team_abbr"] = ngs.team_abbr.replace({"LAR": "LA"})
    return {"depth": depth_build(dc, snaps, ros, absences), "receiving": receiving_build(ngs, season)}


def main():
    import compute as cp  # noqa: E402 (re-uses the cached, policy-checked downloads)
    ap = argparse.ArgumentParser()
    ap.add_argument("--season", type=int, default=2026)
    ap.add_argument("--through-week", type=int, default=7)
    ap.add_argument("--refresh", action="store_true", help="download fresh depth charts and Next Gen receiving")
    a = ap.parse_args()
    d = cp.ROOT / "reports" / "team_analytics" / f"{a.season}_week{a.through_week + 1:02d}"
    fresh = {f"depth_charts/depth_charts_{a.season}.parquet", "nextgen_stats/ngs_receiving.parquet"}
    fetch = lambda rel: cp.fetch(rel, refresh=a.refresh and rel in fresh)   # noqa: E731
    out = build(a.season, a.through_week, pd.read_csv(d / "absences.csv"), fetch)
    out["sources"] = [m for m in cp.MANIFEST if any(k in m["url"] for k in ("depth_charts", "ngs_receiving"))]
    (d / "depth.json").write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")
    print("wrote", d / "depth.json", len(out["depth"]["absences"]), "absences,", len(out["receiving"]["teams"]), "receiving teams")


if __name__ == "__main__":
    main()
