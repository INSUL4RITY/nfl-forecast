"""Roster moves (display only; predict/roster_moves.py) on hand-made rosters and snap counts."""

import polars as pl

from nflcast.predict import roster_moves as RM


def _ros(rows):
    return pl.DataFrame([{"season": 2026, "week": w, "team": t, "gsis_id": g, "full_name": n, "position": p, "status": s}
                         for w, t, g, n, p, s in rows])


def _snaps(rows):
    return pl.DataFrame([{"season": 2026, "game_type": "REG", "week": w, "team": t, "pfr_player_id": pid, "player": n,
                          "offense_snaps": o, "offense_pct": o / 60, "defense_snaps": 0, "defense_pct": 0.0}
                         for w, t, pid, n, o in rows])


PLAYERS = pl.DataFrame({"gsis_id": ["g1", "g2", "g3", "k1", "k2"], "pfr_id": ["p1", "p2", "p3", "pk1", "pk2"]})


def test_departures_arrivals_and_kicker_change():
    ros = _ros([
        (1, "IND", "g1", "Guard One", "OL", "ACT"), (2, "IND", "g1", "Guard One", "OL", "ACT"),
        (3, "SEA", "g1", "Guard One", "OL", "ACT"),                                   # traded to SEA in week 3
        (1, "IND", "g2", "Edge Two", "DL", "ACT"), (2, "IND", "g2", "Edge Two", "DL", "RES"),
        (3, "IND", "g2", "Edge Two", "DL", "RES"),                                    # reserve list from week 2
        (1, "IND", "g3", "Backup Three", "OL", "ACT"), (2, "IND", "g3", "Backup Three", "OL", "ACT"),
        (3, "IND", "g3", "Backup Three", "OL", "ACT"),
        (1, "LA", "k1", "Old Kicker", "K", "ACT"), (2, "LA", "k1", "Old Kicker", "K", "CUT"),
        (2, "LA", "k2", "New Kicker", "K", "ACT"), (3, "LA", "k2", "New Kicker", "K", "ACT"),
        (3, "IND", "k3", "Ind Kicker", "K", "ACT")])
    snaps = _snaps([(1, "IND", "p1", "Guard One", 60), (2, "IND", "p1", "Guard One", 60),
                    (1, "IND", "p2", "Edge Two", 30), (1, "IND", "p3", "Backup Three", 6),
                    (2, "IND", "p3", "Backup Three", 6)])
    P = RM.prepare(ros, snaps, PLAYERS, 2026)
    ind = RM.team_moves(P, "IND", 3)
    moves = {d["player"]: d["move"] for d in ind["departures"]}
    assert moves == {"Guard One": "Now with SEA", "Edge Two": "Reserve list (IR, suspension or PUP)"}   # backup < 20%
    sea = RM.team_moves(P, "SEA", 3)
    assert [(a["player"], a["from"]) for a in sea["arrivals"]] == [("Guard One", "IND")]
    la = RM.team_moves(P, "LA", 3)
    assert la["specialists"][0]["now"] == "New Kicker" and la["specialists"][0]["before"][0]["player"] == "Old Kicker"
    # as of week 2 only the reserve-list move had happened (the trade comes in week 3)
    assert [d["player"] for d in RM.team_moves(P, "IND", 2)["departures"]] == ["Edge Two"]
