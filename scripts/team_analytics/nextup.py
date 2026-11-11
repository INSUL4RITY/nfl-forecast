"""Next-man-up quality: each absent regular's depth-chart replacement, judged on his own 2026 sample.

  - skill players (WR, TE, RB): his snaps, targets and EPA/target, carries and EPA/carry (play-by-play usage);
  - pass rushers and linebackers: his defensive snaps and PFR pressures (and sacks);
  - offensive linemen: the team's dropback EPA, sack rate and hit-or-sack rate in games he started (50%+ of
    offensive snaps) against games he did not;
  - defensive backs: his PFR coverage line, and the defence's EPA per dropback allowed in games he started (50%+ of
    defensive snaps) against games he did not.
Started/not splits mix in every other change between those games (opponents, other injuries), so they are context.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from depth import _initial, _norm

MIN_TGT, MIN_CAR, MIN_SPLIT_DB = 10, 10, 100     # below these a rate is not shown
_PS = Path(__file__).resolve().parent / "player_shrinkage.json"
PLAYER_SHRINK = json.loads(_PS.read_text(encoding="utf-8")) if _PS.exists() else None


def rate_range(kind: str, n: int) -> float | None:
    """Half-width of a 95% interval for a per-opportunity EPA rate on n opportunities (kind: 'carry', 'target_WR', ...),
    from the 2021-25 per-opportunity variance in player_shrinkage.json."""
    m = (PLAYER_SHRINK or {}).get("measures", {}).get(kind) or (PLAYER_SHRINK or {}).get("measures", {}).get("target_WR")
    return 1.96 * math.sqrt(m["s2"] / n) if m and n else None


def _match(d: dict, name: str):
    if not name:
        return None
    n = _norm(name)
    if n in d:
        return d[n]
    c = [v for k, v in d.items() if _initial(k) == _initial(n)]
    return c[0] if len(c) == 1 else None


def _f(v):
    return None if v is None or (isinstance(v, float) and np.isnan(v)) else float(v)


def build(depth_rows: list[dict], absences: pd.DataFrame, snaps: pd.DataFrame, p: pd.DataFrame, PL: dict, US: dict) -> dict:
    snaps = snaps.copy()
    snaps["nn"] = snaps.player.map(_norm)
    db = p[p.db]
    off_g = db.groupby(["posteam", "game_id"]).agg(n=("epa", "size"), epa=("epa", "sum"), sacks=("sackp", "sum"),
                                                     hs=("hit_sack", "sum"))
    def_g = db.groupby(["defteam", "game_id"]).agg(n=("epa", "size"), epa=("epa", "sum"))
    grp = {(a.team, a.player): a.group for a in absences.itertuples()}
    out = {}
    for r in depth_rows:
        nu = r.get("next_up")
        if not nu:
            continue
        t, g = r["team"], grp.get((r["team"], r["player"]))
        q = {"group": g}
        if g in ("WR/TE", "RB"):
            up = _match({_norm(x["name"]): x for x in US["team_players"].get(t, [])}, nu)
            if up:
                q.update({"kind": "skill", "pos": up.get("pos"), "games": up["games"], "snap_pct": _f(up["snap_pct"]), "targets": up["targets"],
                          "epa_tgt": _f(up["epa_tgt"]), "carries": up["carries"], "epa_car": _f(up["epa_car"])})
        elif g in ("DL/EDGE", "LB"):
            up = _match(PL["all"].get(t, {}), nu)
            if up:
                q.update({"kind": "rush", "games": up["games"], "snaps": up["snaps"], "pressures": up["pressures"],
                          "sacks": up["sacks"], "per100": up["pressures"] / up["snaps"] * 100 if up["snaps"] else None})
        elif g in ("OL", "DB"):
            col, pct = ("offense_snaps", "offense_pct") if g == "OL" else ("defense_snaps", "defense_pct")
            s = snaps[(snaps.team == t)]
            mine = s[s.nn == _norm(nu)]
            if mine.empty:
                mine = s[s.nn.map(_initial) == _initial(nu)]
                mine = mine if mine.pfr_player_id.nunique() == 1 else mine.iloc[0:0]
            started = set(mine[mine[pct] >= 0.5].game_id)
            allg = set(s.game_id)
            gt = off_g.loc[t] if g == "OL" else def_g.loc[t]
            a, b = gt[gt.index.isin(started)], gt[gt.index.isin(allg - started)]
            rate = lambda x, c: float(x[c].sum() / x.n.sum()) if len(x) and x.n.sum() else None   # noqa: E731
            q.update({"kind": "ol" if g == "OL" else "db", "snaps": int(mine[col].sum()), "starts": len(started),
                      "other_games": len(allg - started),
                      "epa_db_started": rate(a, "epa"), "epa_db_not": rate(b, "epa"), "db_started": int(a.n.sum()),
                      "db_not": int(b.n.sum())})
            if g == "OL":
                q.update({"sack_started": rate(a, "sacks"), "sack_not": rate(b, "sacks"),
                          "hs_started": rate(a, "hs"), "hs_not": rate(b, "hs")})
            else:
                up = _match(PL["all"].get(t, {}), nu)
                if up:
                    q.update({"targets": up["targets"], "rating": up["rating"]})
        if q.get("kind"):
            q["text"] = text(nu, q)
            out[f"{t}|{r['player']}"] = q
    return out


def _pl(n, word):
    return f"{n:g} {word}" + ("" if n == 1 else "s")


def text(nu: str, q: dict) -> str:
    k = q["kind"]
    e = lambda v: "n/a" if v is None else f"{v:+.3f}"   # noqa: E731
    pc = lambda v: "n/a" if v is None else f"{100 * v:.1f}%"   # noqa: E731
    if k == "skill":
        parts = [f"{nu}: {_pl(q['games'], 'game')}, {pc(q['snap_pct'])} of snaps"]
        rated = False
        if q["targets"]:
            rt = rate_range(f"target_{q.get('pos')}", q["targets"])
            rated |= q["targets"] >= MIN_TGT
            parts.append(_pl(q['targets'], 'target') + (f" ({e(q['epa_tgt'])} EPA/target" + (f", ±{rt:.2f}" if rt else "") + ")"
                                                         if q["targets"] >= MIN_TGT else " (too few for a rate)"))
        if q["carries"]:
            rc = rate_range("carry", q["carries"])
            rated |= q["carries"] >= MIN_CAR
            parts.append(("1 carry" if q['carries'] == 1 else f"{q['carries']} carries") + (f" ({e(q['epa_car'])} EPA/carry" + (f", ±{rc:.2f}" if rc else "") + ")"
                                                                                           if q["carries"] >= MIN_CAR else " (too few for a rate)"))
        return ", ".join(parts) + (". Per-target and per-carry rates are mostly noise at this volume; his share of the work is the steadier guide"
                                   if rated and PLAYER_SHRINK else "")
    if k == "rush":
        return (f"{nu}: {_pl(q['snaps'], 'defensive snap')} in {_pl(q['games'], 'game')}, {_pl(q['pressures'], 'pressure')}"
                + (f" ({q['per100']:.1f} per 100 snaps)" if q["per100"] is not None else "") + f", {_pl(q['sacks'], 'sack')}")
    if k == "ol":
        if not q["starts"]:
            return f"{nu}: {q['snaps']} offensive snaps, no starts yet"
        if min(q["db_started"], q["db_not"]) < MIN_SPLIT_DB:
            return (f"{nu}: {q['snaps']} snaps, {q['starts']} start{'' if q['starts'] == 1 else 's'}; too few dropbacks for a with/without split "
                    f"({q['db_started']} in his starts, {q['db_not']} in other games)")
        return (f"{nu}: {q['snaps']} snaps, {q['starts']} starts. Team in his starts: {e(q['epa_db_started'])} EPA/dropback, "
                f"sack rate {pc(q['sack_started'])} ({q['db_started']} dropbacks); other games {e(q['epa_db_not'])}, "
                f"{pc(q['sack_not'])} ({q['db_not']} dropbacks)")
    cov = f", {q['targets']} targets as nearest defender (rating {q['rating']:.0f})" if q.get("rating") is not None and q.get("targets", 0) >= MIN_TGT else ""
    if not q["starts"]:
        return f"{nu}: {q['snaps']} defensive snaps, no starts yet{cov}"
    if min(q["db_started"], q["db_not"]) < MIN_SPLIT_DB:
        return (f"{nu}: {q['snaps']} snaps, {q['starts']} start{'' if q['starts'] == 1 else 's'}{cov}; too few dropbacks for a with/without split "
                f"({q['db_started']} in his starts, {q['db_not']} in other games)")
    return (f"{nu}: {q['snaps']} snaps, {q['starts']} starts{cov}. Defence in his starts: {e(q['epa_db_started'])} EPA/dropback "
            f"allowed ({q['db_started']} dropbacks); other games {e(q['epa_db_not'])} ({q['db_not']})")
