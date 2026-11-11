from datetime import datetime, timedelta, timezone

import polars as pl

from nflcast.predict import play_callers as PC

T0 = datetime(2026, 9, 10, 17, tzinfo=timezone.utc)


def _frames():
    ko = [T0 + timedelta(days=7 * i) for i in range(5)]
    games = pl.DataFrame({"game_id": [f"2026_0{i + 1}_X_DEN" for i in range(5)], "kickoff_utc": ko,
                          "status": ["final", "final", "final", "final", "scheduled"]})
    pc = pl.DataFrame({"season": [2026] * 5, "week": [1, 2, 3, 4, 5], "team": ["DEN"] * 5,
                       "game_id": games["game_id"].to_list(),
                       "off_play_caller": ["Davis Webb", "Davis Webb", "Sean Payton", "Sean Payton", "Someone Else"],
                       "def_play_caller": ["Vance Joseph"] * 5, "head_coach": ["Sean Payton"] * 5},
                      schema_overrides={"season": pl.Int32, "week": pl.Int32})
    return pc, games, ko


def test_finished_game_uses_its_own_row_and_marks_the_switch():
    pc, games, ko = _frames()
    P = PC.prepare(pc, games)
    r = PC.for_game(P, "DEN", 2026, "2026_04_X_DEN", ko[3])
    assert r["based_on"] == "this_game" and r["as_of_week"] == 4
    assert r["offence"] == {"name": "Sean Payton", "head_coach": True, "since_week": 3, "replaced": "Davis Webb"}
    assert r["defence"] == {"name": "Vance Joseph", "head_coach": False, "since_week": None, "replaced": None}


def test_upcoming_game_uses_the_last_finished_game_never_the_files_future_rows():
    pc, games, ko = _frames()
    r = PC.for_game(PC.prepare(pc, games), "DEN", 2026, "2026_05_X_DEN", ko[4])
    assert r["based_on"] == "last_game" and r["as_of_week"] == 4
    assert r["offence"]["name"] == "Sean Payton"          # not the file's assumed week-5 caller


def test_first_game_and_unknown_team():
    pc, games, ko = _frames()
    P = PC.prepare(pc, games)
    first = PC.for_game(P, "DEN", 2026, "2026_01_X_DEN", ko[0])
    assert first["offence"]["since_week"] is None and first["based_on"] == "this_game"
    assert PC.for_game(P, "KC", 2026, "2026_01_X_DEN", ko[0]) is None
    assert PC.for_game(P, "DEN", 2026, "2026_01_X_DEN", ko[0] - timedelta(days=1)) is None
