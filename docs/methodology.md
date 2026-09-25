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

## Known limitations
- The historical market line is untimed (≈ closing), so market-based models are validated only at the final horizon.
- Early-week injury state, historical operational weather, and coordinator/play-caller data are unavailable. See data_sources.md.
- The combined model uses a single observed line, so it cannot react to QB news the market has not yet priced.
