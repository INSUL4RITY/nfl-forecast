"""Reserve lists (display only; predict/reserve_list.py) on hand-made rosters and snap counts."""

import re
from pathlib import Path

import polars as pl

from nflcast.predict import reserve_list as RL


def _ros(rows, season=2026):
    return pl.DataFrame([{"season": season, "week": w, "team": t, "gsis_id": g, "full_name": n, "position": p, "status": s,
                          "status_description_abbr": c} for w, t, g, n, p, s, c in rows])


def _snaps(rows, season=2026):
    return pl.DataFrame([{"season": season, "game_type": "REG", "week": w, "team": t, "pfr_player_id": pid, "player": pid,
                          "offense_snaps": o, "offense_pct": o / 60, "defense_snaps": d, "defense_pct": d / 60,
                          "st_snaps": st, "st_pct": st / 20} for w, t, pid, o, d, st in rows])


PLAYERS = pl.DataFrame({"gsis_id": ["g1", "g2", "g3", "g4", "g5", "g6", "k1", "f1"],
                        "pfr_id": ["p1", "p2", "p3", "p4", "p5", "p6", "pk1", "pf1"]})
FILLER = [(w, "IND", "pf1", 60, 60, 20) for w in (1, 2, 3, 4)]          # a full-time player who fixes the team's snaps


def _tables():
    ros = _ros([
        # starter: played weeks 1-2, out week 3, injured reserve from week 4 (week 3 file still active)
        (1, "IND", "g1", "Tackle One", "OL", "ACT", "A01"), (2, "IND", "g1", "Tackle One", "OL", "ACT", "A01"),
        (3, "IND", "g1", "Tackle One", "OL", "ACT", "A01"), (4, "IND", "g1", "Tackle One", "OL", "RES", "R01"),
        (5, "IND", "g1", "Tackle One", "OL", "RES", "R48"),
        # hurt in training camp: on the list from week 1, played for another team last season
        *[(w, "IND", "g2", "Corner Two", "DB", "RES", "R01") for w in range(1, 6)],
        # suspended weeks 4-5 (a league suspension code)
        *[(w, "IND", "g3", "Edge Three", "DL", "ACT", "A01") for w in (1, 2, 3)],
        (4, "IND", "g3", "Edge Three", "DL", "RES", "R40"), (5, "IND", "g3", "Edge Three", "DL", "RES", "R40"),
        # backup with a small role: counted, not listed
        *[(w, "IND", "g4", "Backup Four", "LB", "ACT", "A01") for w in (1, 2, 3, 4)], (5, "IND", "g4", "Backup Four", "LB", "RES", "R01"),
        # code the mapping does not know yet: shown as "Other reserve list", never raw
        *[(w, "IND", "g5", "Odd Five", "WR", "ACT", "A01") for w in (1, 2, 3, 4)], (5, "IND", "g5", "Odd Five", "WR", "RES", "R77"),
        # kicker on injured reserve (snap shares on offence / defence are zero)
        *[(w, "IND", "k1", "Kicker K", "K", "ACT", "A01") for w in (1, 2, 3, 4)], (5, "IND", "k1", "Kicker K", "K", "RES", "R01"),
        # returned from the list: not on it now
        (1, "IND", "g6", "Back Six", "RB", "RES", "R04"), *[(w, "IND", "g6", "Back Six", "RB", "ACT", "A01") for w in (2, 3, 4, 5)],
        # another team with a bye in week 5 (no file that week)
        *[(w, "SEA", "x1", "Sea Guy", "OL", "ACT", "A01") for w in (1, 2, 3, 4)],
    ])
    snaps = _snaps(FILLER + [
        (1, "IND", "p1", 60, 0, 2), (2, "IND", "p1", 60, 0, 2),          # weeks 1-2: 100% of offence; out week 3
        (1, "IND", "p3", 0, 30, 0), (2, "IND", "p3", 0, 30, 0), (3, "IND", "p3", 0, 30, 0),
        (1, "IND", "p4", 0, 6, 15), (2, "IND", "p4", 0, 6, 15), (3, "IND", "p4", 0, 6, 15), (4, "IND", "p4", 0, 6, 15),
        (1, "IND", "p5", 30, 0, 0), (2, "IND", "p5", 30, 0, 0), (3, "IND", "p5", 30, 0, 0), (4, "IND", "p5", 30, 0, 0),
        (1, "IND", "pk1", 0, 0, 8), (2, "IND", "pk1", 0, 0, 8), (3, "IND", "pk1", 0, 0, 8), (4, "IND", "pk1", 0, 0, 8),
    ])
    prev = _snaps([(w, "BUF", "pf1", 60, 60, 20) for w in (1, 2)] + [(w, "BUF", "p2", 0, 45, 0) for w in (1, 2)], 2025)
    return RL.prepare(ros, snaps, PLAYERS, 2026, prev)


def test_reserve_list_types_shares_and_threshold():
    L = RL.team_list(_tables(), "IND", 6)
    assert L["roster_week"] == 5
    by = {p["player"]: p for p in L["players"]}
    assert set(by) == {"Tackle One", "Corner Two", "Edge Three", "Odd Five", "Kicker K"}
    assert L["others"] == 1                                                          # Backup Four (10% of defence)
    t = by["Tackle One"]
    assert (t["list"], t["group"], t["since_week"]) == ("Injured reserve, designated to return", "injured", 4)
    # share over the team's games up to his last game (weeks 1-2), not diluted by the week he sat out
    assert t["this_season"] == {"share": 1.0, "unit": "offence", "games": 2} and t["last_season"] is None
    c = by["Corner Two"]
    assert c["this_season"] is None and c["since_week"] == 1
    assert c["last_season"] == {"share": 0.75, "unit": "defence", "games": 2, "team": "BUF"}
    e = by["Edge Three"]
    assert (e["list"], e["group"], e["since_week"]) == ("Suspended", "suspended", 4)
    assert e["this_season"]["share"] == 0.5
    assert by["Odd Five"]["list"] == "Other reserve list"
    k = by["Kicker K"]
    assert k["specialist"] and k["this_season"]["games"] == 4
    assert [p["player"] for p in L["players"]][-1] == "Kicker K"                     # specialists last, else by share
    assert [p["player"] for p in L["players"]][:2] == ["Tackle One", "Corner Two"]


def test_roster_week_follows_the_game_week_and_byes():
    P = _tables()
    early = RL.team_list(P, "IND", 4)                                                # as of week 4: the week-4 file
    assert early["roster_week"] == 4
    assert {p["player"] for p in early["players"]} == {"Tackle One", "Corner Two", "Edge Three"}
    assert {p["list"] for p in early["players"]} == {"Injured reserve", "Suspended"}
    assert RL.team_list(P, "SEA", 6)["roster_week"] == 4                             # bye in week 5: latest file is week 4
    assert RL.team_list(P, "NYJ", 6) == {"roster_week": None, "players": [], "others": 0}
    g = RL.game_list(P, {"away_id": "SEA", "home_id": "IND", "week": 6})
    assert g["min_share"] == RL.MIN_SHARE and g["home"]["roster_week"] == 5


def test_labels_are_plain_english_and_no_ids_leak():
    for code in list(RL.KIND) + ["R59", "R23", "", None, "XYZ"]:
        group, label = RL.kind(code)
        assert group in {"injured", "pup", "nfi", "suspended", "other", "pending"}
        assert not re.search(r"\b[A-Z]\d{2}\b|\bRES\b", label)
    out = str(RL.game_list(_tables(), {"away_id": "SEA", "home_id": "IND", "week": 6}))
    assert not re.search(r"\b[A-Z]\d{2}\b|\bRES\b|\bg\d\b|\bp\d\b|pk1|gsis|pfr", out)


def test_reserve_list_stays_out_of_releases():
    """Export only: the release builder (and so the injury fingerprint / notable list) never sees it."""
    src = Path(__file__).resolve().parents[1] / "src" / "nflcast" / "predict"
    assert "reserve_list" not in (src / "release.py").read_text(encoding="utf-8")
    assert "reserve_list" in (src / "export_web.py").read_text(encoding="utf-8-sig")
