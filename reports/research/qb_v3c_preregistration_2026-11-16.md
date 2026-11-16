# Pre-registration: v3-C leverage-weighted QB rating (2026-11-16)

Written before any leverage-weighted rating was computed or evaluated. Plan context:
`reports/research/qb_v3_audit_2026-11-16.md` (experiments A and C). User decision 2026-11-16: build it as a private
trial: logged with trusted timestamps, never shown on the site, never sets the model pick, never changes the frozen
v1.0 Model line or the v2 trial line, and a failure never blocks a release.

## Hypothesis
Quarterback EPA per dropback earned when the game is already one-sided predicts future results less well than EPA in
competitive situations. Down-weighting low-leverage dropbacks **in the QB rating only** (team form unchanged) lowers the
stats-only margin error. (A hard 10-90% win-probability filter on team efficiency already failed in v2.0; this tests a
smooth weight on the QB rating instead.)

## Definitions
* Dropbacks: exactly as the current rating (`personnel.qb_games`): `qb_dropback == 1`, spikes and no-plays excluded,
  sacks and scrambles included, `epa` from nflfastR play-by-play.
* Leverage: m = min(wp, 1 - wp), with `wp` the offence's pre-snap nflfastR win probability (non-market; `vegas_wp` is
  never used). Missing `wp`: weight 1.
* Weight: w = f + (1 - f) x min(1, m / c). Full weight while the offence's win probability is between c and 1 - c,
  falling linearly to the floor f at 0 or 1.
* Weighted rating: the current formula with weighted sums: rating = (sum over games of g_k x sum(w x epa) + 250 x prior)
  / (sum of g_k x sum(w) + 250), where g_k are the existing recency weights (16-game half-life, 0.8 per season back).
  `qb_log_db` = log(1 + weighted dropbacks), `qb_delta` = rating minus the team baseline computed with the same weighted
  model. The prior, starter rule, half-life, carry and 250 pseudo-count are unchanged.
* Grid (15 curves): c in {0.05, 0.10, 0.15, 0.20, 0.30} x f in {0, 0.25, 0.5}. (f = 1 is the current rating, arm A.)

## Arms and data
* **A (baseline):** frozen v1.0 stats-only specification (`core_qb` feature set), final horizon (actual starter as the
  proxy, labelled retrospective), refit in the same harness. Must reproduce the existing walk-forward results.
* **C:** identical, with the four QB columns per side recomputed from the weighted rating. Nothing else changes.
* Training starts 2016 (core start); ratings are warmed up from 2011; ridge alpha chosen by the existing chronological
  rule inside each training window; same games in both arms.

## Selection (tune folds only)
Choose (c, f) by pooled mean squared margin error over the tune folds **2019, 2020, 2021** (train 2016..S-1, predict S).
Ties within 0.01 squared points: the larger f, then the larger c (closer to the current rating).

## Test (one comparison)
Folds **2022, 2023, 2024, 2025** (train 2016..S-1, predict S), chosen curve vs A, paired on identical games.
* **Pass** if C's pooled mean squared margin error is lower than A's **and** the 95% interval of the difference
  (C - A; existing week-block bootstrap, 2,000 reps, seed 20260924) is entirely below zero.
* These seasons were used by earlier work (v1.0 tuning and the 2025 locked test; v2 tests), but leverage weighting was
  never evaluated on them. A pass here is therefore evidence, not proof.
* Reported, not gating: MAE, RMSE, win-probability Brier score and log loss where the harness supports them, side vs
  untimed (~closing) lines, and splits for games with a starter change, QBs with < 200 career dropbacks, regular season
  vs playoffs; plus each QB's full, competitive (m >= 0.10) and low-leverage (m < 0.10) EPA per dropback as diagnostics.

## Private prospective trial (decisive)
After the test, whatever its result, the chosen curve is fitted once on all games through the latest finished week and
frozen (sha256 recorded). From the first scheduled cycle after that, every forecast release also writes a **private**
v3-C prediction for each game (margin, total, win probability, QB ratings used) to a git-ignored folder, timestamped
with RFC 3161 and mirrored to the private backup repository. It is judged on the rest of 2026 and on 2027 against the
v1.0 Model line on the same games and locks. Promotion to any public line needs this pre-registered test passed **and**
no worse prospective margin error, decided by the user.
