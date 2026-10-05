"""Weekly publication time (user decision 2026-10-05; operational only, no model change).

From week 5 of 2026 a week's forecasts, lines and model picks are first published at Thursday 09:00 UK time before
that week's first game (after Monday night's game and the week's first practice reports), not as soon as the previous
week ends. The model pick locks at that first publication (picks rule "original-pick"). If the PC is off at 09:00, the
first cycle after login publishes, as long as games remain; games that kicked off meanwhile are never back-filled.
Weeks whose first game kicks off before GATE_FROM, or that already have a release, are not held back.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

PUBLISH_TZ = ZoneInfo("Europe/London")
PUBLISH_WEEKDAY = 3                    # Thursday
PUBLISH_TIME = time(9, 0)
GATE_FROM = datetime(2026, 10, 6, tzinfo=timezone.utc)   # week 5 of 2026 onward


def publish_open_at(first_kickoff: datetime) -> datetime | None:
    """When the week whose first game kicks off at `first_kickoff` may first be published (None = not held back):
    the latest Thursday 09:00 UK at least one hour before that kickoff."""
    if first_kickoff < GATE_FROM:
        return None
    d = first_kickoff.astimezone(PUBLISH_TZ).date()
    thu = d - timedelta(days=(d.weekday() - PUBLISH_WEEKDAY) % 7)
    opens = datetime.combine(thu, PUBLISH_TIME, PUBLISH_TZ)
    if opens > first_kickoff - timedelta(hours=1):          # e.g. a Thursday-morning (UK) kickoff: use the week before
        opens = datetime.combine(thu - timedelta(days=7), PUBLISH_TIME, PUBLISH_TZ)
    return opens.astimezone(timezone.utc)


def held_back(first_kickoff: datetime, now: datetime, week_already_released: bool) -> datetime | None:
    """The publication time if the week must not be published yet, else None."""
    opens = publish_open_at(first_kickoff)
    return opens if opens is not None and now < opens and not week_already_released else None
