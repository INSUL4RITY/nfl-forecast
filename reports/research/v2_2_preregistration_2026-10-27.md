# Model v2.2 (trial line): fatigue and time of possession, pre-registration 2026-10-27

Written before any v2.2 result was computed. User request 2026-10-27: before the trial line's clean test (weeks 8-18)
starts, add fatigue spots and time of possession. The v2.1 trial has no locked or tracked pick yet (its only published
forecasts are three versions of week 7's Monday game, which stay in the immutable releases as v2.1).

## What changes (v2.2 = v2.1 + this group; nothing else)

- **Time of possession** (recency-weighted like every team stat, minutes per game from nflverse drive
  `drive_time_of_possession`): own offence's time of possession, and the opponent defence's average time on the field
  (= its opponents' possession time).
- **Fatigue from the previous game** (that team's last game before this one, any game type): the opponent defence's
  plays faced in that game, whether it went to overtime, plays faced above 65 on a short week (rest <= 5 days),
  and its plays faced per game over its last 3 games.

## Rule (fixed now)

Same walk-forward as the v2 test: final horizon, train 2016..S-1, predict S for S = 2019..2025, identical games for
both arms, ridge alpha by the same chronological rule. **v2.2 replaces v2.1 as the trial line if its pooled mean squared
margin error is <= v2.1's** (point estimate; 95% interval reported). Otherwise the trial stays v2.1 and the group goes to
the 2027 test list as "tested, not added". Either way the trial line stays display and tracking only, never the pick.
