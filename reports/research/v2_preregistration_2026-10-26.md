# Model v2.0 (stats-only line): pre-registration, 2026-10-26

Written before any v2.0 result was computed. User decision 2026-10-26: build v2.0 now with the feature groups below and
make it the official stats-only "Model line" / "Model pick" from week 8 **only if it tests at least as accurate as v1.0**;
otherwise v2.0 runs as a trial line next to v1.0. Weeks 1-7 stay graded as v1.0 (never regraded). The market-adjusted
(combined) line stays v1.0. The frozen v1.0 artifact and its configs are not touched.

## What changes (v1.0 stats-only = B_qb, feature set core_qb; v2.0 = B_v2, feature set v2)

1. **Garbage-time filter.** Efficiency stats (EPA/play, success rate, EPA/dropback, EPA/carry, explosive pass and run
   rates) and the opponent-adjusted EPA rating use only plays with the offence's pre-snap nflfastR win probability
   (`wp`, the non-market model) between 0.10 and 0.90. Scoring stats (points, points per drive, red zone) are unchanged.
2. **Penalties.** EPA of accepted penalties that cancel the play (`no_play` rows, currently excluded): offensive
   penalties committed, defensive penalties committed (and drawn), per play.
3. **Luck / regression inputs.** All fumbles per play (next to fumbles lost, so recovery luck can regress), 3rd-down and
   4th-down conversion rates, one-score results (+1 win / -1 loss by <= 8).
4. **QB.** Scramble EPA per dropback (offence and allowed); QB rating x experience term.
5. **Coaching decision proxy.** 4th-down go rate on 4th and <= 3 between the offence's own 40 and the opponent's 1
   (win probability 0.10-0.90).
6. **Non-QB injuries.** The existing lost-snap-share inputs (lost_ol, lost_skill, opponent lost_front, lost_db).
7. **Travel and body clock.** Distance from home venue (1,000 km), time-zone shift (hours, east positive), kickoff
   time in the team's home time zone (hours before 13:00 and after 20:00), consecutive road games (cap 3).
8. **Special teams.** Net special-teams EPA per game (kickoffs, punts, field goals, extra points).
9. **Divisional game** flag.
10. **Weather** (exposure-weighted wind, gusts, cold, precipitation). Retrospective for history (labelled).

Not included (no adequate free, dated data): pressure, blitz and coverage charting; coaching quality beyond the
4th-down proxy. Ridge alpha is chosen by the same chronological rule as v1.0 (`select_alpha_chronologically`).

## Test and go-live rule (fixed now)

* Walk-forward, expanding window, final horizon, identical games for both arms: train on 2016..S-1, predict S, for
  S = 2019..2025. 2025 is a re-evaluation (no longer untouched). Also reported: 2026 weeks 1-7 (trained 2016-2025).
* **Primary metric:** pooled squared error of the margin over 2019-2025. **Pass if v2.0's mean squared margin error
  is <= v1.0's** (point estimate; the 95% season-week block-bootstrap interval is reported, not required).
* Reported, not gating: margin MAE, total RMSE, per-season results, side-of-the-historical-line agreement, 2026 weeks
  1-7, and each feature group's drop-one effect.
* If it passes: v2.0 is fitted on all completed games through week 7 of 2026, frozen (sha256 recorded), and sets the
  "Model line" / "Model pick" for games from week 8. If it fails: v2.0 is shown and tracked as a trial line only.
