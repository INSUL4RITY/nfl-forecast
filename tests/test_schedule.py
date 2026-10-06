"""Weekly publication time: Wednesday 18:00 UK before the week's first game (from 6 Oct 2026; week 5 opened early)."""

from datetime import datetime, timezone

from nflcast.predict import schedule as SCHED

utc = lambda *a: datetime(*a, tzinfo=timezone.utc)


def test_week_5_was_opened_early_on_the_users_request():
    tnf = utc(2026, 10, 9, 0, 15)                      # week 5 TNF: Thu 8 Oct 20:15 ET = Fri 01:15 UK
    assert SCHED.publish_open_at(tnf) == utc(2026, 10, 6, 20, 40)
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 0, 30), False) == utc(2026, 10, 6, 20, 40)   # after MNF: held
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 20, 40), False) is None                     # opened
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 0, 30), True) is None                       # already released


def test_thursday_night_week_opens_wednesday_evening_uk():
    tnf = utc(2026, 10, 16, 0, 15)                     # week 6 TNF: Thu 15 Oct 20:15 ET = Fri 01:15 UK
    assert SCHED.publish_open_at(tnf) == utc(2026, 10, 14, 17, 0)        # Wed 14 Oct 18:00 BST
    assert SCHED.held_back(tnf, utc(2026, 10, 14, 16, 59), False) == utc(2026, 10, 14, 17, 0)
    assert SCHED.held_back(tnf, utc(2026, 10, 14, 17, 0), False) is None


def test_winter_time_and_sunday_first_games_use_the_wednesday_before():
    sunday = utc(2026, 11, 8, 18, 0)                   # Sunday game; UK on GMT in November
    assert SCHED.publish_open_at(sunday) == utc(2026, 11, 4, 18, 0)       # Wed 4 Nov 18:00 GMT


def test_earlier_weeks_are_not_held_and_evening_uk_kickoffs_use_the_week_before():
    assert SCHED.publish_open_at(utc(2026, 10, 2, 0, 15)) is None          # week 4: before the decision
    wed_evening = utc(2026, 10, 21, 17, 30)            # hypothetical Wednesday 18:30 UK kickoff
    assert SCHED.publish_open_at(wed_evening) == utc(2026, 10, 14, 17, 0)
