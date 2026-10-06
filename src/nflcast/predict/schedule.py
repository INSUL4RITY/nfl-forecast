"""Weekly publication time (user decisions; operational only, no model change).

A week's forecasts, lines and model picks are first published at a fixed weekly time before that week's first game, not
as soon as the previous week ends. The model pick locks at that first publication (picks rule "original-pick"). If the
PC is off at that time, the first cycle after login publishes, as long as games remain; games that kicked off meanwhile
are never back-filled. Weeks whose first game kicks off before GATE_FROM, or that already have a release, are not held.

- 2026-10-05: Thursday 09:00 UK (from week 5).
- 2026-10-06: Wednesday 18:00 UK instead (lines had moved a lot by Thursday), and week 5 released at once (EARLY_OPENS).
"""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

PUBLISH_TZ = ZoneInfo("Europe/London")
PUBLISH_WEEKDAY = 2                    # Wednesday
PUBLISH_TIME = time(18, 0)
GATE_FROM = datetime(2026, 10, 6, tzinfo=timezone.utc)   # week 5 of 2026 onward
SCHEDULE_TEXT = "Wednesday 18:00 UK"

# One-off earlier openings asked for by the user: (first kickoff from, first kickoff before, opens at), all UTC.
EARLY_OPENS = [
    (datetime(2026, 10, 8, tzinfo=timezone.utc), datetime(2026, 10, 13, tzinfo=timezone.utc),
     datetime(2026, 10, 6, 20, 40, tzinfo=timezone.utc)),     # week 5: user asked on Tue 6 Oct to publish now
]


def publish_open_at(first_kickoff: datetime) -> datetime | None:
    """When the week whose first game kicks off at `first_kickoff` may first be published (None = not held back):
    the latest Wednesday 18:00 UK at least one hour before that kickoff (earlier if listed in EARLY_OPENS)."""
    if first_kickoff < GATE_FROM:
        return None
    d = first_kickoff.astimezone(PUBLISH_TZ).date()
    wed = d - timedelta(days=(d.weekday() - PUBLISH_WEEKDAY) % 7)
    opens = datetime.combine(wed, PUBLISH_TIME, PUBLISH_TZ)
    if opens > first_kickoff - timedelta(hours=1):          # e.g. a Wednesday-evening (UK) kickoff: use the week before
        opens = datetime.combine(wed - timedelta(days=7), PUBLISH_TIME, PUBLISH_TZ)
    opens = opens.astimezone(timezone.utc)
    for lo, hi, early in EARLY_OPENS:
        if lo <= first_kickoff < hi:
            opens = min(opens, early)
    return opens


def held_back(first_kickoff: datetime, now: datetime, week_already_released: bool) -> datetime | None:
    """The publication time if the week must not be published yet, else None."""
    opens = publish_open_at(first_kickoff)
    return opens if opens is not None and now < opens and not week_already_released else None
