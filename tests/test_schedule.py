"""Weekly publication time: Thursday 09:00 UK before the week's first game, from week 5 of 2026."""

from datetime import datetime, timezone

from nflcast.predict import schedule as SCHED

utc = lambda *a: datetime(*a, tzinfo=timezone.utc)


def test_thursday_night_week_opens_thursday_morning_uk():
    tnf = utc(2026, 10, 9, 0, 15)                      # week 5 TNF: Thu 8 Oct 20:15 ET = Fri 01:15 UK
    assert SCHED.publish_open_at(tnf) == utc(2026, 10, 8, 8, 0)          # Thu 8 Oct 09:00 BST
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 0, 30), False) == utc(2026, 10, 8, 8, 0)   # after MNF: held
    assert SCHED.held_back(tnf, utc(2026, 10, 8, 8, 0), False) is None                     # 09:00 UK: open
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 0, 30), True) is None                     # already released: never held


def test_after_tnf_the_sunday_games_use_the_same_thursday_and_winter_time():
    sunday = utc(2026, 11, 8, 18, 0)                   # Sunday game; UK on GMT in November
    assert SCHED.publish_open_at(sunday) == utc(2026, 11, 5, 9, 0)        # Thu 5 Nov 09:00 GMT


def test_earlier_weeks_are_not_held_and_morning_uk_kickoffs_use_the_week_before():
    assert SCHED.publish_open_at(utc(2026, 10, 2, 0, 15)) is None          # week 4: before the decision
    thu_morning = utc(2026, 10, 15, 8, 30)             # hypothetical Thursday 09:30 UK kickoff
    assert SCHED.publish_open_at(thu_morning) == utc(2026, 10, 8, 8, 0)
