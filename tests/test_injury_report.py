"""Game-page injury report (display only): every listed player for the game's two teams and week, most serious first."""

import polars as pl

from nflcast.predict.export_web import injury_rows


def _inj(rows):
    cols = ["team", "week", "full_name", "position", "report_primary_injury", "practice_primary_injury", "practice_status",
            "report_status"]
    return pl.DataFrame([dict(zip(cols, r)) for r in rows], schema={c: (pl.Int64 if c == "week" else pl.Utf8) for c in cols})


def test_practice_only_players_are_listed_and_sorted_by_status():
    inj = _inj([
        ("PIT", 4, "Joey Porter Jr.", "CB", None, "Back", "Limited Participation in Practice", None),
        ("CLE", 4, "Elgton Jenkins", "C", "Concussion", "Concussion", "Did Not Participate In Practice", "Out"),
        ("PIT", 4, "Jalen Ramsey", "CB", "Wrist", "Wrist", "Limited Participation in Practice", "Questionable"),
        ("PIT", 4, "Rico Dowdle", "RB", "Toe", "Toe", "Did Not Participate In Practice", "Out"),
        ("PIT", 3, "Old Week", "WR", "Knee", "Knee", None, "Out"),                     # another week: excluded
        ("BAL", 4, "Other Team", "QB", None, None, "Full Participation in Practice", None),  # another team: excluded
    ])
    rows = injury_rows(inj, 4, {"PIT": "PIT", "CLE": "CLE"})              # away (PIT) first
    assert [r["full_name"] for r in rows] == ["Rico Dowdle", "Elgton Jenkins", "Jalen Ramsey", "Joey Porter Jr."]
    porter = rows[-1]
    assert porter["game_status"] is None and porter["injury"] == "Back"     # practice-only: injury from the practice field
    assert porter["practice_status"] == "Limited Participation in Practice"


def test_team_ids_are_shown_with_the_site_abbreviation():
    inj = _inj([("LA", 4, "Some Player", "WR", "Hamstring", "Hamstring", "Full Participation in Practice", None)])
    rows = injury_rows(inj, 4, {"LA": "LAR", "PHI": "PHI"})
    assert rows == [{"team": "LAR", "full_name": "Some Player", "position": "WR", "injury": "Hamstring",
                     "practice_status": "Full Participation in Practice", "game_status": None, "depth": None}]
    assert injury_rows(inj, 5, {"LA": "LAR", "PHI": "PHI"}) == []


def test_practice_participation_breaks_ties_when_no_game_status():
    inj = _inj([
        ("PIT", 4, "A Full", "CB", None, "Back", "Full Participation in Practice", None),
        ("PIT", 4, "B Limited", "CB", None, "Wrist", "Limited Participation in Practice", None),
        ("PIT", 4, "C Did Not", "RB", None, "Toe", "Did Not Participate In Practice", None),
        ("CLE", 4, "D Questionable", "WR", "Knee", "Knee", "Full Participation in Practice", "Questionable"),
    ])
    assert [r["full_name"] for r in injury_rows(inj, 4, {"PIT": "PIT", "CLE": "CLE"})] == \
        ["D Questionable", "C Did Not", "B Limited", "A Full"]


def test_game_status_due_day_by_kickoff_weekday():
    from datetime import date, datetime, timezone

    from nflcast.predict.export_web import status_due
    utc = lambda *a: datetime(*a, tzinfo=timezone.utc)
    assert status_due(utc(2026, 10, 2, 0, 15)) == date(2026, 9, 30)    # Thursday 20:15 ET -> Wednesday
    assert status_due(utc(2026, 10, 4, 17, 0)) == date(2026, 10, 2)    # Sunday -> Friday
    assert status_due(utc(2026, 10, 6, 0, 15)) == date(2026, 10, 3)    # Monday 20:15 ET -> Saturday
    assert status_due(utc(2026, 11, 27, 20, 0)) == date(2026, 11, 25)  # Friday (Black Friday) -> Wednesday
    assert status_due(utc(2026, 12, 19, 21, 0)) == date(2026, 12, 17)  # Saturday -> Thursday
    assert status_due(utc(2026, 9, 10, 0, 20)) == date(2026, 9, 7)     # Wednesday 20:20 ET -> Monday


def test_depth_labels_use_each_teams_latest_chart_and_best_rank():
    from nflcast.predict.export_web import depth_labels
    dc = pl.DataFrame({"dt": ["2026-10-01", "2026-10-03", "2026-10-03", "2026-10-03", "2026-10-03"],
                       "team": ["PHI"] * 5, "gsis_id": ["a", "a", "b", "b", "c"],
                       "pos_abb": ["WR", "WR", "LT", "RT", "TE"], "pos_rank": [2, 1, 3, 1, 2]})
    assert depth_labels(dc) == {"a": "WR1", "b": "RT1", "c": "TE2"}   # older chart row ignored
    assert depth_labels(None) == {}
