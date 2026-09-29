"""Desktop alerts: what needs a human, no spam, re-alert on change, retries, robustness. No real toasts are shown."""

import json
from datetime import datetime, timedelta, timezone

import pytest

from nflcast.predict import alerts as AL

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)


def side(team, flags=(), scen=(("QB One", 0.97), ("QB Two", 0.03)), overrides=()):
    return {"team": team, "flags": list(flags), "scenarios": [{"qb": q, "p": p} for q, p in scen], "overrides_used": list(overrides)}


def game(hours, home=None, away=None, market=True, gid="2026_04_PIT_CLE", status="ok", home_team="CLE", away_team="PIT"):
    return {"game_id": gid, "kickoff_utc": (NOW + timedelta(hours=hours)).isoformat(), "home_team": home_team,
            "away_team": away_team, "status": status, "market": {"home_spread": 2.5} if market else None,
            "lineup": {"home": home or side(home_team), "away": away or side(away_team, scen=(("Aaron Rodgers", 0.99),))}}


@pytest.fixture(autouse=True)
def files(tmp_path, monkeypatch):
    monkeypatch.setattr(AL, "LOG", tmp_path / "alerts.log")
    monkeypatch.setattr(AL, "STATE", tmp_path / "alerts_state.json")
    monkeypatch.setattr(AL, "toast", lambda *a, **k: pytest.fail("a real toast was attempted in a test"))


def texts(items):
    return " | ".join(i["text"] for i in items)


def test_nothing_to_flag_for_healthy_or_distant_games():
    assert AL.attention_items({"games": [game(30)]}, NOW) == []
    far = game(80, home=side("CLE", ("report_stale",), (("A", 0.5), ("B", 0.5))))
    assert AL.attention_items({"games": [far]}, NOW) == []
    assert AL.attention_items({"games": [game(-1, home=side("CLE", ("report_stale",)))]}, NOW) == []


def test_flags_that_need_a_human():
    g = game(20, home=side("CLE", ("report_stale", "listed_out_despite_stale_report"), (("Case Keenum", 0.54), ("Tyson Bagent", 0.46))),
             market=False)
    t = texts(AL.attention_items({"games": [g]}, NOW))
    assert "no current injury report" in t and "QB listed Out is kept out" in t
    assert "starting QB uncertain" in t and "Case Keenum 54%" in t and "no market line" in t
    assert all(i["url"].endswith("/game/2026_04_PIT_CLE/") for i in AL.attention_items({"games": [g]}, NOW))


def test_no_qb_and_failed_forecast_are_flagged():
    g = game(20, home=side("CLE", ("no_candidate_qb_prior_used",), ((None, 1.0),)), status="rejected_validation_failed", market=False)
    t = texts(AL.attention_items({"games": [g]}, NOW))
    assert "no starting QB could be identified" in t and "failed its checks" in t and "no market line" not in t


def test_override_in_effect_suppresses_report_nagging():
    ov = [{"status": "starting", "source": "https://example.org"}]
    g = game(20, home=side("CLE", ("report_stale",), (("Case Keenum", 1.0),), overrides=ov))
    assert AL.attention_items({"games": [g]}, NOW) == []


def test_timing_thresholds():
    assert AL.attention_items({"games": [game(40, home=side("CLE", ("report_not_available",)))]}, NOW) == []
    assert AL.attention_items({"games": [game(30, home=side("CLE", ("designation_pending",)))]}, NOW) == []
    assert len(AL.attention_items({"games": [game(20, home=side("CLE", ("designation_pending",)))]}, NOW)) == 1


def test_feed_wide_problem_is_one_item_not_one_per_team():
    teams = ["BUF", "MIA", "NYJ", "NE", "BAL", "CIN", "CLE", "PIT"]
    games = [game(20, gid=f"g{k}", home_team=teams[k], away_team=teams[k + 4],
                  home=side(teams[k], ("report_stale",)), away=side(teams[k + 4], ("report_stale",))) for k in range(4)]
    items = AL.attention_items({"games": games}, NOW)
    assert [i["key"] for i in items] == ["injury_feed_not_current"] and "8 teams" in items[0]["text"]


def test_one_bad_game_does_not_hide_the_others():
    bad = {"game_id": "broken", "kickoff_utc": (NOW + timedelta(hours=5)).isoformat()}
    items = AL.attention_items({"games": [bad, game(20, home=side("CLE", ("designation_pending",)))]}, NOW)
    assert {i["key"] for i in items} == {"broken:unreadable", "2026_04_PIT_CLE:CLE:designation_pending"}


def test_dedupe_resend_change_and_forget():
    shown = []
    send = lambda t, b, u: shown.append(b) or True
    items = AL.attention_items({"games": [game(20, home=side("CLE", ("designation_pending",), (("A", 0.6), ("B", 0.4))))]}, NOW)
    assert len(AL.notify(items, NOW, send)) == 2 and len(shown) == 1                     # one toast per cycle
    assert AL.notify(items, NOW + timedelta(minutes=30), send) == []                     # no repeat
    assert len(AL.notify(items, NOW + timedelta(hours=12), send)) == 2                   # still open after 12 h
    changed = AL.attention_items({"games": [game(20, home=side("CLE", ("designation_pending",), (("A", 0.8), ("B", 0.2))))]}, NOW)
    assert AL.notify(changed, NOW + timedelta(hours=13), send) == []                     # changed, but < 2 h since last sent
    assert [i["key"] for i in AL.notify(changed, NOW + timedelta(hours=14), send)] == [changed[1]["key"]]
    AL.notify([], NOW + timedelta(hours=14, minutes=30), send)                           # absent 30 min: remembered
    assert AL.notify(changed, NOW + timedelta(hours=15), send) == []
    AL.notify([], NOW + timedelta(hours=16, minutes=30), send)                           # absent > 1 h: forgotten
    assert len(AL.notify(changed, NOW + timedelta(hours=17), send)) == 2


def test_countdown_in_text_is_not_a_change():
    # regression (week-3 replay): "kickoff in N h" changes every hour; that alone must never re-alert (33 toasts -> spam)
    shown = []
    send = lambda t, b, u: shown.append(b) or True
    for k in range(0, 11):                                             # 10 hours of cycles, same QB split
        g = game(40 - k, home=side("CLE", (), (("A", 0.7), ("B", 0.3))))
        AL.notify(AL.attention_items({"games": [g]}, NOW + timedelta(hours=k)), NOW + timedelta(hours=k), send)
    assert len(shown) == 1


def test_failed_toast_is_retried_and_not_counted_as_shown():
    items = [AL._item("x", "something", None)]
    fail = lambda t, b, u: False
    assert AL.notify(items, NOW, fail) == []
    assert "NOT SHOWN" in AL.LOG.read_text(encoding="utf-8")
    ok = lambda t, b, u: True
    assert AL.notify(items, NOW + timedelta(minutes=30), ok) == items                  # retried next cycle


def test_failed_toast_retries_are_capped():
    items, fail = [AL._item("x", "something", None)], (lambda t, b, u: False)
    calls = []
    counting = lambda t, b, u: calls.append(1) or False
    for k in range(6):
        AL.notify(items, NOW + timedelta(minutes=30 * k), counting)
    assert len(calls) == 3                                                               # MAX_TRIES, then wait 12 h


def test_failure_kinds_do_not_hide_each_other():
    ok = lambda t, b, u: True
    AL.notify([AL._item("run_failed:error", "generic failure", None)], NOW, ok, forget_resolved=False)
    serious = [AL._item("run_failed:integrity", "publishing is stopped", None)]
    assert AL.notify(serious, NOW + timedelta(minutes=30), ok, forget_resolved=False) == serious


def test_malformed_state_file_never_silences_alerts():
    items, ok = [AL._item("x", "something", None)], (lambda t, b, u: True)
    for bad in ("[1, 2]", "null", "7", '{"x": "garbage"}', '{"x": {"last_seen": "2026-10-01T12:00:00"}}', "{truncated"):
        AL.STATE.write_text(bad, encoding="utf-8")
        assert AL.notify(items, NOW, ok) == items
        assert isinstance(json.loads(AL.STATE.read_text(encoding="utf-8")), dict)


def test_credits_caught_up_text_and_last_completed_run(tmp_path):
    assert AL.credit_items(80) == [] and AL.credit_items(None) == []
    assert "credits low (41 left" in AL.credit_items(41)[0]["text"]
    assert "published to the site" in AL.caught_up_text(9, 15, True)[1]
    assert "upload to the site failed" in AL.caught_up_text(9, 15, False)[1]
    assert "No forecast inputs had changed" in AL.caught_up_text(9, None, None)[1]
    assert "since the last completed run" in AL.caught_up_text(9, None, None)[0]
    log = tmp_path / "operate.log"
    log.write_text("2026-09-29T04:00:00+00:00 operate: start\n2026-09-29T04:01:00+00:00 operate: done\n"
                   "2026-09-29T04:30:00+00:00 operate: start\n2026-09-29T04:31:00+00:00 operate: FAILED\n", encoding="utf-8")
    assert AL.last_completed_run(log) == datetime(2026, 9, 29, 4, 1, tzinfo=timezone.utc)


def test_operate_wrappers_never_raise_and_use_distinct_failure_keys(monkeypatch):
    from nflcast.predict import operate as OP
    shown = []
    monkeypatch.setattr(AL, "toast", lambda t, b, u="": shown.append((t, b)) or True)
    monkeypatch.setattr(OP, "_log", lambda msg: None)
    OP._alert_failure("error", "generic failure")
    OP._alert_failure("integrity", "publishing is stopped")
    assert [b for _, b in shown] == ["generic failure", "publishing is stopped"]
    monkeypatch.setattr(AL, "attention_items", lambda *a: 1 / 0)
    OP._alerts({"games": []}, NOW)                                                       # swallowed, logged
    from nflcast.config import utc_now
    OP._caught_up_notice(utc_now() - timedelta(hours=9), 3, True)          # the notice measures the gap on the real clock
    assert "published to the site" in shown[-1][1] and "9 h since the last completed run" in shown[-1][0]
    n = len(shown)
    OP._caught_up_notice(utc_now() - timedelta(hours=2), 3, True)          # short gap: no notice
    assert len(shown) == n
