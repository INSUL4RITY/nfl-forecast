# Deserved margin: method fixed before weeks 10-18 (written 2026-11-10)

Display and analysis only. It never changes a forecast, the pick, the pick rule or any grade, and it is never used to
regrade a game. User decision 2026-11-10. Method follows dgrifka/nfl_simulator (MIT), refit on our own data.
Code: `src/nflcast/predict/deserved.py`; fixed values: `configs/deserved.yaml`.

## Definition (fixed)
- Plays: nflverse play-by-play, `play_type` pass or run with non-null `epa`, excluding two-point tries (sacks count as
  passes, scrambles as runs, garbage time kept; penalty-only plays and special teams excluded).
- Per team and game: own plays N, successes K (`epa > 0`), yards Y (`yards_gained`). Takeaways by that team's defence
  (interception or lost fumble on the opponent's pass/run plays): T, of which T_s with `epa < 0` for the offence, and
  return yards R (`return_yards` for interceptions, `fumble_recovery_1_yards` for lost fumbles; nflverse leaves
  `return_yards` at 0 on lost fumbles).
- success rate = (K + T_s) / (N + T); yards per play = (Y + R) / N.
- Deserved home margin = 55.429 x (home rate - away rate) + 4.050 x (home ypp - away ypp). No intercept.
  Weights: least squares on 2016-2023 regular-season games (n = 2,095), old nflfastR EP scale; residual SD 8.87.
  2024-2025 out of sample (n = 544): residual SD 8.47, R^2 0.649. (With an intercept: +1.04 points home, R^2 unchanged.)
- Against the official Model pick's locked line: edge = (deserved margin + home line), signed toward the picked side.
  |edge| < 1.5 points = "close on play quality"; otherwise "ahead" or "behind". The scoreboard result is the official
  grade (`result_grade.lean`).
- Groups: won and ahead (right, and deserved); won and behind (right, but fortunate); lost and ahead (wrong, but
  unlucky); lost and behind (wrong, and deserved); close; level with the line (push). Season counts use publicly
  verifiable locked picks only, like the official record.

## Known limits (stated wherever it is shown)
- Leaves out special teams, field position, penalties and red-zone finishing, so those count as "luck".
- The stats-only model rates teams on similar play-quality numbers, so it looks better on deserved margin than on the
  scoreboard partly by construction (backfill below: the model line 55-37 on play quality vs market-adjusted 40-52).
  Not a substitute for the official record and not evidence that one line is better.
- Uses the old EP scale (`success` depends on `epa`). If nflverse moves to the revised EP valuation (nflfastR PR 618) the
  export pauses it (`alerts.ep_scale_problem`) rather than apply these weights to the new scale.

## Check made before fixing (2026-11-10)
- First draft credited lost-fumble returns from `return_yards` (always 0 for fumbles); corrected to
  `fumble_recovery_1_yards` and refit before anything was published (weights were 56.686 / 3.972; residual SD 8.53 ->
  8.47 out of sample).
- Reconciled with the published record: the official record on the site (47-51-4 through week 9 Sunday) plus Monday
  night's BUF@MIN gives the 47-52-4 below.

## Backfill, weeks 3-9 incl. BUF@MIN (computed 2026-11-10, before any week-10 game)
- Official Model pick as published: 47-52-4 on the scoreboard; on play quality 44 ahead, 48 behind, 11 close (these
  play-quality counts include the 4 level games; the site's two-by-two table leaves them out);
  unlucky 12, fortunate 11.
- Model line (stats-only), all weeks: 54-45 (excluding level); play quality 55-37, 11 close; unlucky 14, fortunate 9.
- Market-adjusted: 47-52; play quality 40-52, 11 close; unlucky 10, fortunate 13.
- v2 trial (weeks 8-9): 15-13; play quality 16-9, 3 close; unlucky 5, fortunate 3.

## Addendum, 2026-11-10 (user request; written before any week-10 game and before computing any chance)
Two display-only additions. Neither changes the deserved margin, the groups, the close band or any grade.

1. **Chance on play quality.** For the official pick's side: the share of 2,000 re-samples in which the deserved margin
   puts that side ahead of the locked line (edge > 0). Each re-sample draws each team's own pass/run plays with
   replacement (same count as played); every drawn play keeps its success flag, yards, takeaway flag, takeaway-success
   flag and return yards, so takeaways move with the opponent's resampled plays. Weights fixed (no weight uncertainty).
   Random seed = first 8 bytes of sha256(game_id), so a game always shows the same value. This measures how firmly the
   plays support the verdict, not a forecast; a game near 50% is genuinely ambiguous.
2. **What made the difference** (descriptive, no weights, no fitting), per team from the same play-by-play:
   giveaways on its pass/run plays (interceptions thrown, fumbles lost); field goals made / attempted; red-zone
   touchdowns / drives that reached the opponent's 20 (`drive_inside20`, result Touchdown); enforced penalties and
   yards (rows with `penalty` = 1 charged to the team; nflverse records the enforced penalty, declined ones only
   appear in the play description); average drive start (own yard line of each drive's first scrimmage play);
   4th-down conversions / attempts (go-for-it plays); explosive plays (passes of 20+ yards, runs of 10+); special teams
   net expected points (EPA on special-teams plays as the kicking or receiving side, team minus opponent).
