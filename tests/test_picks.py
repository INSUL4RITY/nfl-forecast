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
    assert g["lean"]["win"] == 1 and g["lean"]["push"] == 1 and g["lean"]["loss"] == 1 and g["retro_winner"] == 1
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


# ---------------- locked pick: "original-pick" from 1 Oct 2026 (week 4 on), "final-pregame" before ----------------
KO4 = datetime(2026, 10, 4, 17, 0, tzinfo=timezone.utc)      # a week 4 kickoff (original-pick rule)


def _rel(run, t, entry):
    return {"run_id": run, "generated_at_utc": t.isoformat()}, entry


def _ev(*pairs):
    return {"files": {f"releases/2026/week_04/{run}.json": {"first_public_evidence_utc": t.isoformat()} for run, t in pairs}}


def _two_versions(ko):
    t0, t1 = ko - timedelta(days=3), ko - timedelta(hours=2)
    vs = [_rel("rel_a", t0, {"status": "ok", "forecast": fc(6.4), "market": {"home_spread": -7.5}, "game_type": "REG"}),
          _rel("rel_b", t1, {"status": "ok", "forecast": fc(6.2), "market": {"home_spread": -6.0}, "game_type": "REG"})]
    return vs, _ev(("rel_a", t0 + timedelta(minutes=1)), ("rel_b", t1 + timedelta(minutes=1)))


def test_original_pick_is_locked_when_the_line_moves():
    # The user's example: BUF opens -7.5 with BUF projected by 6.4 -> pick MIA +7.5. An injury moves the line to BUF -6.0
    # and the forecast to BUF by 6.2 (now the BUF side). The model pick stays MIA +7.5 and is graded against +7.5.
    from nflcast.predict.export_web import locked_pick_for
    vs, ev = _two_versions(KO4)
    lk = locked_pick_for(vs, KO4, "BUF", "MIA", ev)
    assert lk["rule"] == "original-pick" and lk["run_id"] == "rel_a"
    assert lk["lean"]["side"] == "MIA" and lk["lean"]["side_spread"] == 7.5 and lk["line_home_spread"] == -7.5
    assert lk["verification"] == "publicly_verifiable_pregame"
    final = pick_for(vs[1][1], "BUF", "MIA")
    assert final["lean"]["side"] == "BUF" and final["line_home_spread"] == -6.0       # latest would pick BUF -6
    g = PK.grade_game(final, lk, 27, 20, "BUF", "MIA")                               # BUF by 7: MIA +7.5 covers
    assert g["lean"] == "win" and g["winner"] == "win" and abs(g["abs_margin_error"] - 0.8) < 1e-9
    assert PK.grade_game(final, lk, 30, 20, "BUF", "MIA")["lean"] == "loss"          # BUF by 10: MIA +7.5 loses


def test_games_before_the_rule_start_keep_the_final_pregame_pick():
    # Finished weeks are never regraded: a week 3 game keeps the rule in force when it was played.
    from nflcast.predict.export_web import locked_pick_for
    assert PK.lock_rule(PK.RULE_START - timedelta(seconds=1)) == "final-pregame"
    assert PK.lock_rule(PK.RULE_START) == "original-pick"
    vs, ev = _two_versions(KO)                                   # KO = 28 Sep 2026 (week 3)
    lk = locked_pick_for(vs, KO, "BUF", "MIA", ev)
    assert lk["rule"] == "final-pregame" and lk["run_id"] == "rel_b" and lk["line_home_spread"] == -6.0
    assert lk["lean"]["side"] == "BUF"


def test_original_skips_no_line_invalid_and_post_kickoff_versions():
    no_line = {"status": "ok", "forecast": fc(3.0), "market": None, "game_type": "REG"}
    invalid = {"status": "rejected_validation_failed", "forecast": fc(3.0), "market": {"home_spread": -3.0}, "game_type": "REG"}
    good = {"status": "ok", "forecast": fc(3.4), "market": {"home_spread": -3.5}, "game_type": "REG"}
    later = {"status": "ok", "forecast": fc(3.6), "market": {"home_spread": -2.5}, "game_type": "REG"}
    post = {"status": "ok", "forecast": fc(9.0), "market": {"home_spread": -7.0}, "game_type": "REG"}
    t = lambda h: (KO4 - timedelta(hours=h)).isoformat()
    vs = [(t(80), no_line), (t(70), invalid), (t(60), good), (t(1), later), ((KO4 + timedelta(minutes=1)).isoformat(), post)]
    assert PK.select_original(vs, KO4)[1] is good and PK.select_locked(vs, KO4)[1] is good
    assert PK.select_original([(t(80), no_line), ((KO4 + timedelta(minutes=1)).isoformat(), post)], KO4) is None
    assert PK.select_original(list(reversed(vs)), KO4)[1] is good                    # order of input does not matter


def test_no_locked_line_grades_as_no_line_and_winner_still_counts():
    final = PK.derive(fc(3.4), None, "BUF", "NE")
    g = PK.grade_game(final, None, 24, 20, "BUF", "NE")
    assert g["winner"] == "win" and g["lean"] == "no_line"
    assert PK.grade_game(None, None, 24, 20, "BUF", "NE") is None


def test_weekly_summary_groups_and_retro_counts_per_label():
    pv, nyet = "publicly_verifiable_pregame", "generated_pregame_not_yet_evidenced_public"
    final = {**PK.derive(fc(3.4), {"home_spread": -3.0}, "H", "A"), "retrospectively_derived": False}
    lk = {**PK.derive(fc(2.0), {"home_spread": -3.0}, "H", "A"), "retrospectively_derived": True, "verification": nyet,
          "rule": "original-pick"}
    it = {"status": "final", "forecast_verification": pv, "pick": final, "locked_pick": lk,
          "result_grade": PK.grade_game(final, lk, 24, 20, "H", "A")}
    s = PK.weekly_summary([it])
    assert s["grading_rule"] == "original-pick"
    assert s["groups"][pv]["graded"] == 1 and s["groups"][pv]["pick_graded"] == 0
    assert s["groups"][pv]["retro_winner"] == 0 and s["groups"][nyet]["retro_pick"] == 1      # the winner label was published
    assert s["groups"][nyet]["graded"] == 0 and s["groups"][nyet]["pick_graded"] == 1
    assert s["groups"][nyet]["lean"]["loss"] == 1                                      # A +3 loses when H wins by 4


def test_locked_pick_carries_the_stats_only_numbers_of_the_same_version():
    from nflcast.predict.export_web import locked_pick_for
    vs, ev = _two_versions(KO4)
    vs[0][1]["football_only"] = {"margin": 3.1, "total": 44.0}
    vs[1][1]["football_only"] = {"margin": 5.0, "total": 46.0}
    lk = locked_pick_for(vs, KO4, "BUF", "MIA", ev)
    assert lk["run_id"] == "rel_a" and lk["stats_only"] == {"margin": 3.1, "total": 44.0, "line_total": None}
    del vs[0][1]["football_only"]
    assert locked_pick_for(vs, KO4, "BUF", "MIA", ev)["stats_only"] is None


def test_stats_only_tracking_grade_uses_the_locked_line_and_total():
    lk = {"line_home_spread": -8.0, "stats_only": {"margin": 4.9, "total": 48.8, "line_total": 49.5}}
    g = PK.grade_stats_only(lk, 16, 24)            # TB @ DAL: DAL -8, stats DAL by 4.9 -> TB side; 40 pts -> under
    assert g == {"spread": "win", "big_gap": True, "total": "win", "total_side": "under"}
    assert PK.grade_stats_only(lk, 30, 20)["spread"] == "loss"           # DAL by 10 covers -8
    assert PK.grade_stats_only(lk, 28, 20)["spread"] == "push"
    assert PK.grade_stats_only({**lk, "stats_only": {**lk["stats_only"], "margin": 6.0}}, 16, 24)["big_gap"] is False
    assert PK.grade_stats_only({**lk, "stats_only": {"margin": 8.0, "total": 49.5, "line_total": 49.5}}, 16, 24) == \
        {"spread": None, "big_gap": False, "total": None, "total_side": None}
    assert PK.grade_stats_only({"line_home_spread": None, "stats_only": lk["stats_only"]}, 16, 24) is None
    assert PK.grade_stats_only({**lk, "stats_only": {"margin": 4.9, "total": 48.8, "line_total": None}}, 16, 24)["total"] is None
