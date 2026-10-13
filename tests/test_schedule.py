"""Weekly publication time: Tuesday 18:00 UK before the week's first game (from week 6 of 2026; week 5 opened early),
plus the hold while the previous week's games are missing from the processed data."""

from datetime import datetime, timezone

from nflcast.predict import schedule as SCHED

utc = lambda *a: datetime(*a, tzinfo=timezone.utc)


def test_week_5_opening_and_an_already_released_week_is_never_held():
    tnf = utc(2026, 10, 9, 0, 15)                      # week 5 TNF: Thu 8 Oct 20:15 ET = Fri 01:15 UK
    # under today's Tuesday rule week 5 would open Tue 6 Oct 18:00 BST (earlier than its one-off 21:40 BST opening)
    assert SCHED.publish_open_at(tnf) == utc(2026, 10, 6, 17, 0)
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 0, 30), False) == utc(2026, 10, 6, 17, 0)    # after MNF: held
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 17, 0), False) is None                      # opened
    assert SCHED.held_back(tnf, utc(2026, 10, 6, 0, 30), True) is None                       # already released


def test_thursday_night_week_opens_tuesday_evening_uk():
    tnf = utc(2026, 10, 16, 0, 15)                     # week 6 TNF: Thu 15 Oct 20:15 ET = Fri 01:15 UK
    assert SCHED.publish_open_at(tnf) == utc(2026, 10, 13, 17, 0)        # Tue 13 Oct 18:00 BST
    assert SCHED.held_back(tnf, utc(2026, 10, 13, 16, 59), False) == utc(2026, 10, 13, 17, 0)
    assert SCHED.held_back(tnf, utc(2026, 10, 13, 17, 0), False) is None


def test_winter_time_and_sunday_first_games_use_the_tuesday_before():
    sunday = utc(2026, 11, 8, 18, 0)                   # Sunday game; UK on GMT in November
    assert SCHED.publish_open_at(sunday) == utc(2026, 11, 3, 18, 0)       # Tue 3 Nov 18:00 GMT


def test_earlier_weeks_are_not_held_and_evening_uk_kickoffs_use_the_week_before():
    assert SCHED.publish_open_at(utc(2026, 10, 2, 0, 15)) is None          # week 4: before the decision
    tue_evening = utc(2026, 10, 20, 17, 30)            # hypothetical Tuesday 18:30 UK kickoff
    assert SCHED.publish_open_at(tue_evening) == utc(2026, 10, 13, 17, 0)


def test_waits_for_missing_previous_week_data_but_never_too_long():
    tnf = utc(2026, 10, 16, 0, 15)                     # opens Tue 13 Oct 17:00 UTC
    at = utc(2026, 10, 13, 17, 30)
    assert SCHED.waiting_for_data(tnf, at, False, 0) is None                               # data complete
    assert SCHED.waiting_for_data(tnf, at, False, 1) == utc(2026, 10, 14, 17, 0)           # wait up to 24 h
    assert SCHED.waiting_for_data(tnf, utc(2026, 10, 14, 17, 0), False, 1) is None         # cap reached: publish
    assert SCHED.waiting_for_data(tnf, at, True, 1) is None                                # already released
    close = utc(2026, 10, 14, 10, 0)                   # a first game only 17 h after the opening time
    assert SCHED.waiting_for_data(close, utc(2026, 10, 13, 17, 30), False, 2) == utc(2026, 10, 14, 9, 0)
