"""Line movement after the lock, valued with key numbers (display only; predict/linemove.py)."""

import pytest

from nflcast.predict import linemove as LM


def test_key_numbers_make_a_move_through_3_worth_more():
    through_3 = LM.move_for(-2.5, -3.5, True)          # home side locked at -2.5, later -3.5: one point toward
    plain = LM.move_for(-5.5, -6.5, True)
    assert through_3["points_toward"] == plain["points_toward"] == 1.0
    assert through_3["chance_gained"] > 1.5 * plain["chance_gained"] > 0
    assert LM.move_for(-3.0, -2.5, True)["points_toward"] == -0.5          # moved away from the home side
    assert LM.move_for(-3.0, -2.5, False)["chance_gained"] > 0             # ... which favours the away side
    assert LM.move_for(-3.0, -3.0, True) == {"points_toward": 0.0, "chance_gained": 0.0}


def test_side_chance_counts_a_push_as_half():
    dist = LM.margin_dist(3.0)
    home, away = LM.side_chance(-3.0, True, dist), LM.side_chance(-3.0, False, dist)
    assert home + away == pytest.approx(1.0)


def _item(lean_side, stats_margin, lock, last, verification="publicly_verifiable_pregame"):
    return {"status": "final", "home": "CHI", "away": "NE",
            "locked_pick": {"line_home_spread": lock, "verification": verification,
                            "lean": {"status": "lean", "side": lean_side, "difference": abs(stats_margin + lock)},
                            "stats_only": {"margin": stats_margin}, "stats_v2": None},
            "forecast": {"market": {"home_spread": last}}}


def test_game_moves_and_summary_bands():
    a = _item("NE", 1.96, -3.0, -2.5)                   # NE side at +3, later +2.5: moved toward NE
    mv = LM.game_moves(a)
    assert mv["sides"]["model_pick"]["points_toward"] == 0.5 and mv["sides"]["model_line"]["gap"] == pytest.approx(1.04)
    assert "v2_trial" not in mv["sides"]
    assert LM.game_moves(_item("NE", 1.96, -3.0, -2.5, "generated_pregame_published_after_kickoff")) is None
    b = _item("CHI", 8.0, -3.0, -4.0)                  # model line 5 pts from the line, moved toward CHI
    s = LM.summary([{**a, "line_move": mv}, {**b, "line_move": LM.game_moves(b)}])
    assert s["model_line"]["n"] == 2 and s["model_line"]["toward"] == 2
    assert s["model_line_bands"]["under_1_5"]["n"] == 1 and s["model_line_bands"]["3_plus"]["n"] == 1
