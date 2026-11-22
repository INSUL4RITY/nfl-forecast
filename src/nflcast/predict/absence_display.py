"""Who is missing, for Big and Biggest gap games (display only; user authorisation 2026-11-20, brief item B1).

For a game whose model line (stats only) was >= 3 points from the market line at the pick's lock (or, while the pick is
provisional, now), each team's missing regulars:
  * players on the injury report for the game with a game status (Out / Doubtful / Questionable), or, while the team
    has no game statuses in the data yet, players who did not practise or were limited;
  * players on a reserve list (predict/reserve_list.py) and players who left the team this season (traded or released;
    predict/roster_moves.py): neither appears on the weekly injury report, so the model's injury inputs never see them.
Shown: name, position, unit in plain words, status (or practice status, reserve list, "Now with X", "Released") and
this season's snap share with the team. Regulars only (>= 20% of the unit's snaps, as on the reserve-list panel);
the rest are counted. Quarterbacks are left out (the card's QB line covers them). No point values (none has passed a
test: reports/research/absences_v1_evaluation_2026-11-21.md).
`final_at_lock` is False when either team's final game designations were not yet in our data when the pick locked
(features/injury_versions.final_statuses_at); the site then says "Measured before final injury reports reached the data".
Built at export time only: never in the release JSON or "notable" (the injury_report fingerprint must not change).
"""

from __future__ import annotations

from datetime import datetime

import polars as pl

from nflcast.data import sources as S
from nflcast.data.games import franchise
from nflcast.features import injury_versions as IV
from nflcast.features.personnel import UNIT_OF_POSITION
from nflcast.predict import picks as PK
from nflcast.predict import reserve_list as RL
from nflcast.predict import roster_moves as RM

MIN_SHARE = 0.20
UNIT_TEXT = {"ol": "Offensive line", "skill": "Running backs, receivers and tight ends", "front": "Defensive front",
             "db": "Secondary"}
PRACTICE_TEXT = {"Did Not Participate In Practice": "Did not practise (no game status yet)",
                 "Limited Participation in Practice": "Limited in practice (no game status yet)"}


def gap_of(lp: dict | None) -> float | None:
    """Model line (stats only) margin minus the line margin of the locked (or provisional) pick."""
    if not lp or lp.get("line_home_spread") is None or not lp.get("stats_only"):
        return None
    return float(lp["stats_only"]["margin"]) + float(lp["line_home_spread"])


def _share(rl: dict, team: str, gsis: str | None, week: int) -> float | None:
    if not gsis or week <= 1:
        return None
    s = RL._share(rl["s"], rl["unit"], team, gsis, (1, week - 1))
    return None if s is None else round(float(s["share"]), 3)


def team_absences(team: str, week: int, inj: pl.DataFrame | None, rl: dict, rm: dict) -> dict:
    players, others = [], 0
    seen = set()
    if inj is not None:
        rows = inj.filter((pl.col("week") == week) & (franchise(pl.col("team")) == team))
        has_status = rows.filter(pl.col("report_status").is_in(list(IV.GAME_STATUSES))).height > 0
        for r in rows.iter_rows(named=True):
            unit = UNIT_OF_POSITION.get(r.get("position") or "")
            if unit is None:
                continue
            st = r.get("report_status")
            if st in IV.GAME_STATUSES:
                text = st
            elif not has_status and r.get("practice_status") in PRACTICE_TEXT:
                text = PRACTICE_TEXT[r["practice_status"]]
            else:
                continue
            share = _share(rl, team, r.get("gsis_id"), week)
            seen.add(r["full_name"])
            if share is None or share < MIN_SHARE:
                others += 1
                continue
            players.append({"player": r["full_name"], "pos": r.get("position"), "unit": UNIT_TEXT[unit], "status": text,
                            "kind": "injury report", "share": share})
    for x in RL.team_list(rl, team, week)["players"]:
        unit = UNIT_OF_POSITION.get(x.get("pos") or "")
        if unit is None or x.get("specialist") or x["player"] in seen:
            continue
        sh = max([s["share"] for s in (x.get("this_season"), x.get("last_season")) if s], default=None)
        players.append({"player": x["player"], "pos": x.get("pos"), "unit": UNIT_TEXT[unit], "status": x["list"],
                        "kind": "reserve list", "share": round(float((x.get("this_season") or {}).get("share") or 0.0), 3),
                        "last_season_share": (x.get("last_season") or {}).get("share"), "_sort": sh or 0.0})
    for d in RM.team_moves(rm, team, week)["departures"]:
        unit = UNIT_OF_POSITION.get(d.get("pos") or "")
        if unit is None or not (d["move"].startswith("Now with") or d["move"] == "Released") or d["player"] in seen:
            continue
        players.append({"player": d["player"], "pos": d.get("pos"), "unit": UNIT_TEXT[unit], "status": d["move"],
                        "kind": "left the team", "share": round(float(d["share"]), 3)})
    order = {"injury report": 0, "reserve list": 1, "left the team": 2}
    players.sort(key=lambda p: (order[p["kind"]], -(p.get("_sort") or p["share"] or 0.0)))
    for p in players:
        p.pop("_sort", None)
    return {"players": players, "others": others}


def game_absences(g: dict, lp: dict | None, now: datetime, rl: dict | None, rm: dict | None, cache: dict) -> dict | None:
    """The B1 block for one game, or None when it is not a Big/Biggest gap game (or the tables are missing)."""
    gap = gap_of(lp)
    if gap is None or abs(gap) < PK.BIG_GAP or rl is None or rm is None:
        return None
    when = min(now, g["kickoff_utc"])
    key = ("inj", g["season"], when)
    if key not in cache:
        cache[key] = S.snapshot_asof("injuries", g["season"], when)[0]
    inj = cache[key]
    lock_at = datetime.fromisoformat(lp["generated_at"])
    at = min(lock_at, when) if not lp.get("provisional") else when
    final_at = {s: IV.final_statuses_at(g["season"], g["week"], g[f"{s}_id"], at, when) for s in ("away", "home")}
    return {"gap": round(gap, 2), "measured_at": when.isoformat(), "provisional": bool(lp.get("provisional")),
            "final_at_lock": all(final_at.values()), "min_share": MIN_SHARE,
            **{s: team_absences(g[f"{s}_id"], g["week"], inj, rl, rm) for s in ("away", "home")}}
