"""Picks and weekly results: spread-lean signs, pushes, ties, no-lean, record counts, locking against line moves."""

from datetime import datetime, timedelta, timezone

from nflcast.predict import picks as PK
from nflcast.predict.export_web import pick_for
from nflcast.predict.validation import select_frozen

KO = datetime(2026, 9, 28, 17, 0, tzinfo=timezone.utc)


def fc(margin, p_home=None):
    p_home = p_home if p_home is not None else (0.6 if margin > 0 else 0.4)
    return {"margin": margin, "p_home": p_home, "p_away": 1 - p_home - 0.004, "p_tie": 0.004,
            "home_pts": 22 + margin / 2, "away_pts": 22 - margin / 2, "total": 44.0,
            "intervals": {"margin_80": [margin - 10, margin + 10], "margin_95": [margin - 20, margin + 20],
                          "total_80": [34, 54], "total_95": [28, 60]}}


def test_lean_sign_home_favourite():
    # BUF -3 at home: line margin +3. Model +3.4 -> BUF side (beats the line by 0.4, tiny); model +2 -> NE +3 side.
    p = PK.derive(fc(3.4), {"home_spread": -3.0}, "BUF", "NE")
    assert p["winner"] == "BUF" and p["lean"]["side"] == "BUF" and p["lean"]["side_spread"] == -3.0
    assert abs(p["lean"]["difference"] - 0.4) < 1e-9 and p["lean"]["strength"] == "tiny"
    p = PK.derive(fc(2.0), {"home_spread": -3.0}, "BUF", "NE")
    assert p["winner"] == "BUF" and p["lean"]["side"] == "NE" and p["lean"]["side_spread"] == 3.0
    assert p["lean"]["strength"] == "small"


def test_lean_sign_home_underdog_and_exact_match():
    p = PK.derive(fc(-6.0), {"home_spread": 2.5}, "CLE", "PIT")        # PIT -2.5; model PIT by 6 -> PIT side, 3.5 pts
    assert p["winner"] == "PIT" and p["lean"]["side"] == "PIT" and p["lean"]["side_spread"] == -2.5
    assert p["lean"]["strength"] == "large"
    assert PK.derive(fc(-2.5), {"home_spread": 2.5}, "CLE", "PIT")["lean"]["status"] == "no_lean"
    assert PK.derive(fc(1.0), None, "CLE", "PIT")["lean"]["status"] == "no_line"
    assert PK.derive({**fc(0.0), "p_home": 0.498, "p_away": 0.498}, {"home_spread": 0.0}, "CLE", "PIT")["winner"] is None


def test_grading_pushes_ties_and_no_lean():
    home_lean = PK.derive(fc(3.4), {"home_spread": -3.0}, "BUF", "NE")
    assert PK.grade(home_lean, 24, 20, "BUF", "NE")["lean"] == "win"      # won by 4 > 3
    assert PK.grade(home_lean, 23, 20, "BUF", "NE")["lean"] == "push"     # exactly 3
    assert PK.grade(home_lean, 22, 20, "BUF", "NE")["lean"] == "loss"
    g = PK.grade(home_lean, 20, 20, "BUF", "NE")                          # actual tie
    assert g["winner"] == "tie" and g["lean"] == "loss" and g["abs_margin_error"] == 3.4
    away_lean = PK.derive(fc(2.0), {"home_spread": -3.0}, "BUF", "NE")
    assert PK.grade(away_lean, 22, 20, "BUF", "NE") == {"winner": "win", "lean": "win", "abs_margin_error": 0.0, "actual_margin": 2}
    no_lean = PK.derive(fc(-2.5), {"home_spread": 2.5}, "CLE", "PIT")
    assert PK.grade(no_lean, 10, 20, "CLE", "PIT")["lean"] == "no_lean"
    toss = PK.derive({**fc(0.0), "p_home": 0.498, "p_away": 0.498}, {"home_spread": 0.0}, "CLE", "PIT")
    assert toss["winner"] is None and PK.grade(toss, 21, 20, "CLE", "PIT")["winner"] == "no_pick"


def _item(verif, final, pick, hs=None, as_=None, retro=False):
    it = {"status": "final" if final else "scheduled", "forecast_verification": verif,
          "pick": {**pick, "retrospectively_derived": retro} if pick else None}
    it["result_grade"] = PK.grade(pick, hs, as_, "H", "A") if final and pick else None
    return it


def test_weekly_counts_and_groups():
    pv, late = "publicly_verifiable_pregame", "generated_pregame_published_after_kickoff"
    home3 = PK.derive(fc(3.4), {"home_spread": -3.0}, "H", "A")
    items = [_item(pv, True, home3, 24, 20), _item(pv, True, home3, 23, 20, retro=True), _item(pv, True, home3, 17, 20),
             _item(late, True, home3, 30, 20, retro=True), _item(pv, False, home3), _item(pv, True, None)]
    s = PK.weekly_summary(items)
    assert s["state"] == "week_to_date" and s["pending"] == 1 and s["no_forecast"] == 1 and s["graded"] == 4
    g = s["groups"][pv]
    assert g["graded"] == 3 and g["winner"] == {"win": 2, "loss": 1, "tie": 0, "no_pick": 0}
    assert g["lean"]["win"] == 1 and g["lean"]["push"] == 1 and g["lean"]["loss"] == 1 and g["retrospectively_derived"] == 1
    assert abs(g["mean_abs_margin_error"] - (0.6 + 0.4 + 6.4) / 3) < 1e-9
    assert s["groups"][late]["graded"] == 1                                # kept separate from publicly verifiable
    assert PK.weekly_summary([_item(pv, True, home3, 24, 20)])["state"] == "final"


def test_line_moves_after_kickoff_cannot_rewrite_the_locked_pick():
    early = {"status": "ok", "forecast": fc(3.4), "market": {"home_spread": -3.0}, "game_type": "REG"}
    late_pre = {"status": "ok", "forecast": fc(3.6), "market": {"home_spread": -3.5}, "game_type": "REG"}
    post = {"status": "ok", "forecast": fc(9.0), "market": {"home_spread": -7.0}, "game_type": "REG"}
    vs = [((KO - timedelta(hours=30)).isoformat(), early), ((KO - timedelta(minutes=30)).isoformat(), late_pre),
          ((KO + timedelta(minutes=5)).isoformat(), post)]
    t, locked = select_frozen(vs, KO)
    p = pick_for(locked, "BUF", "NE")
    assert t == vs[1][0] and p["line_home_spread"] == -3.5            # final pregame version with ITS OWN line
    assert p["lean"]["side"] == "BUF" and p["retrospectively_derived"] is True


def test_stored_pick_is_used_verbatim_and_not_recomputed():
    stored = {**PK.derive(fc(3.4), {"home_spread": -3.0}, "BUF", "NE"), "published_with_forecast": True}
    entry = {"status": "ok", "forecast": fc(3.4), "market": {"home_spread": -3.5}, "picks": stored}
    p = pick_for(entry, "BUF", "NE")
    assert p["line_home_spread"] == -3.0 and p["retrospectively_derived"] is False
