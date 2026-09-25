# Methodology (living document)

## Forecast contract
- Targets: home and away points (including OT), margin M = H − A, total T = H + A, P(home/away/tie), and
  80%/95% intervals for M and T. Playoff tie probability = 0.
- Outputs are **expected** values (decimals), not most-likely scorelines.
- Releases use the generation time as the information cutoff and are labelled by hours to kickoff
  (`early` ≥ 72 h, `final` ≤ 1 h, otherwise `update`). Scoring uses the last version before kickoff (final_pregame) and the
  last version ≥ 72 h before kickoff (early). Each is scored once per game.
- Sign convention: home spread `s` < 0 when home is favoured; nflverse `spread_line` = −s (verified). M0 = −s, T0 = t.
- Non-negativity: `models/core.py::coherent`, applied identically in backtests and releases.

## Leakage controls
- A completed game is usable only once `kickoff_utc + 12h ≤ cutoff`. This applies to team form, the league means used for shrinkage,
  opponent-adjusted ratings (re-fitted per information state), and QB ratings.
- Outcomes are stored in separate columns. Price columns are dropped at ingestion, and every model matrix passes `assert_no_banned`
  (which also bans the spread-derived nflfastR `vegas_*` probabilities).
- Walk-forward folds by season; calibration and intervals are fitted on earlier seasons' out-of-fold predictions only.

## Features
- **core_v1 team form:** see `features/asof.py` (15 metrics × offence/defence, EW half-life 8 games, prior season × 0.6,
  shrunk toward the as-of league mean) plus opponent-adjusted ridge ratings for EPA/play and points.
  A window grid (half-life 4–16, carry-over 0.4–0.8) on the 2019–21 tuning seasons was flat (best 13.353 vs current 13.358
  mean RMSE), so the settings were kept. Short windows (4 games) were clearly worse.
- **QB layer (`features/personnel.py`):** shrunk EPA/dropback that follows the player across teams, with a learned newcomer prior;
  expected starter (early: depth-chart QB1, weekly before 2025 and daily snapshots after; final: actual starter as an approximation of
  inactives knowledge; live: latest daily depth chart plus injury report); qb_delta relative to the QBs behind the team's
  recent stats; QB-change flag.
- **Availability:** expected lost snap share by unit (OL, skill, front, DB) = P(miss | final-report status, learned from earlier
  seasons) × recent snap share. Final horizon only.
- **Context:** venue (+1/−1/0 neutral), rest difference, bye and short-week flags, playoff flag, dome.

## Models and results (see reports/backtest/LATEST.md and reports/locked_test/LATEST.md)
| Family | Model | Notes |
|---|---|---|
| A | market raw / affine-calibrated | calibration adds nothing |
| B | football-only ridge (core, +QB, +QB+injury, no-opponent-adjustment) | QB features help, notably in QB-change games |
| C | residual ridge (selected, feature set core_qb), residual + injuries, residual without personnel, direct, residual HGB | all within noise of market; HGB and direct are worse |

Selection rule and frozen choice: `configs/production.yaml`. The locked 2025 test was run once after freezing:
combined margin RMSE 12.29 vs market 12.24 (difference not significant). The choice was not changed after seeing it.

## Probabilities and intervals
- P(home | no tie) = logistic(predicted margin), fitted on out-of-fold predictions; P(tie) = smoothed REG tie rate since 2017.
- Intervals = empirical out-of-fold residual quantiles (they matched linear quantile regression). Measured coverage in 2025:
  80% range covered 80.7% of margins; the 95% range covered 97.2% (slightly conservative).
- Uncertain QB: two-scenario mixture weighted by the historical P(played | Questionable); intervals from the mixture of
  scenario-shifted residual distributions.

## Quarterback availability in live releases (added 2026-09-25, `features/qb_availability.py`)
- Every relevant QB is resolved: depth-chart QB1–QB3 from the latest daily snapshot at or before the cutoff, plus the
  most recent actual starter. Each has a status (injury-report designation, not on a *published* report, no report yet,
  stale report, or a documented override), its evidence, and the observation time of that evidence.
- **Missing or stale information is not confirmed availability.** "No report yet" (a team with no rows for the week) and
  "stale report" (injury snapshot not confirmed within 36 h) use historical base rates. A depth chart older than 4 days or
  older than the team's last game is "stale", and the last actual starter leads.
- **Evidence-based rates**, estimated from seasons before the forecast season (`reports/qb_availability/start_rates.json`):
  P(depth-chart QB1 starts | final-report status), P(QB1 starts | no report) split by whether he took ≥75% of the team's
  dropbacks last game, and P(QB2 starts | QB1 does not, QB2's status). Daily depth charts (2025) are used per category when
  n ≥ 30; otherwise weekly depth charts (2016–2024). Examples: not listed 416/417 (daily); Questionable 112/193 (weekly);
  Doubtful 0/31; Out 0/153; no report and finished last game 468/481; no report and left early 55/89 (daily, final horizon).
- Scenarios are sequential (QB1 with his probability, otherwise the next available QB, …). Small alternatives are merged
  into the most likely alternative, never into the leading QB, so a 96.7% starter is never displayed as 100%.
- "Lineup uncertain" = leading QB < 90%, or missing/stale evidence, or QB1 left the previous game early.
- Documented overrides: `data/manual/qb_overrides.csv` (source URL and source publication time required; applied only
  when the forecast cutoff is at or after that time; logged in the release).

## Historical approximations (backtests)
- **Actual-starter proxy:** the final-horizon backtest uses the QB who actually started (starters are usually known from
  inactives ~90 min before kickoff). This is optimistic compared with live forecasting, which uses the availability model above.
- **Untimed closing lines:** historical spreads/totals are one untimed line per game (≈ closing). Market-based models are
  validated only at the final horizon and may benefit from late information.
- **Non-QB injuries are display-only** (tested; no gain once the market is included). **Weather and coaching are not modelled.**

## Validation, versions, states and publication (added 2026-09-25)
- `predict/validation.py` checks every forecast (finite, non-negative scores, M = H − A, T = H + A, probabilities in [0,1]
  summing to 1, zero playoff tie probability, ordered and nested intervals containing the point forecast). A failed combined
  forecast is replaced by a validated football-only fallback (labelled `fallback_after_validation_failure`); if nothing passes,
  the entry is stored as `rejected_validation_failed` with no forecast. Display, export and scoring select only the latest
  **valid** version before kickoff, so a failed newer version can never replace a valid older one.
- Releases are triggered by input changes: each game carries fingerprints of market (spread/total), quarterbacks
  (statuses, evidence, scenarios, overrides), injury report, team form and model version. The 30-minute job publishes when
  any fingerprint changes, in the final hour before kickoff, and at least daily. Games that have kicked off are never updated.
- States: `latest_pregame` → `locked_at_kickoff` → `scored`; older versions `superseded`; `rejected_failed_validation`;
  `generated_after_kickoff_not_used`.
- Times: information cutoff and generation time are recorded by the pipeline; **publication time comes only from independent
  evidence** (GitHub Actions push-run creation time, `releases/publication_evidence.json`). Verification labels:
  publicly verifiable pregame / generated pregame, published after kickoff / not yet evidenced. Live scoring reports all
  generated-pregame forecasts and the publicly verifiable subset separately.
- Corrections are appended to `releases/corrections.jsonl`; release files are never edited. First entries: the three Week 3
  releases containing ATL @ GB were generated before its 00:15 UTC kickoff but first public at 00:31 UTC (repository created 00:30:49 UTC).
- The 2025 locked test was run once (2026-09-24). `locked-test` now refuses to run again without `--revision-label`, which
  writes to `reports/revised_evaluations/` labelled as a re-evaluation (not an untouched test). The production model is unchanged
  by these reliability fixes.

## Known limitations
- The historical market line is untimed (≈ closing), so market-based models are validated only at the final horizon.
- Early-week injury state, historical operational weather, and coordinator/play-caller data are unavailable. See data_sources.md.
- The combined model uses a single observed line, so it cannot react to QB news the market has not yet priced.
