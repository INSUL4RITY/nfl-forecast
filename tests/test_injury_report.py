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
                     "practice_status": "Full Participation in Practice", "game_status": None}]
    assert injury_rows(inj, 5, {"LA": "LAR", "PHI": "PHI"}) == []
