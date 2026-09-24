# Methodology (living document)

## Forecast contract
- Targets: home points and away points (including overtime), margin M = H − A, total T = H + A, and
  (Milestone 5) home/away/tie probabilities. Playoff tie probability is 0.
- Outputs are **expected** values (decimals), not most-likely scorelines.
- Horizons: `early` = 72 h and `final` = 1 h before scheduled kickoff (`configs/settings.yaml`). Each is
  evaluated separately. Live releases use the generation time as the information cutoff and are labelled
  by hours-to-kickoff (`early` ≥ 72 h, `final` ≤ 1 h, otherwise `update`).
- Sign convention: home spread `s` is negative when home is favoured. Raw market benchmark
  `M0 = −s`, `T0 = total`, `H0 = (T0+M0)/2`, `A0 = (T0−M0)/2`.
- Non-negativity: `models/core.py::coherent` keeps T and clips M to |M| ≤ T. The same function runs
  in backtests and releases, and projected rows are flagged.

## Leakage controls
- A completed game is usable only when `kickoff_utc + 12h ≤ cutoff` (team form, league means for
  shrinkage and opponent-adjusted ratings all obey this).
- Opponent-adjusted ratings are re-fitted for every distinct information state, never with
  end-of-season ratings.
- Outcomes live in separate columns and are joined only for training targets and scoring.
- Market price columns are dropped at ingestion, and every feature matrix passes `assert_no_banned`.
  nflfastR `vegas_*` win probabilities (spread-derived) are also banned. "Neutral situation" is defined
  from the pre-play score differential (|diff| ≤ 10, quarters 1–3), not from a market-informed win probability.

## Core features (`core_v1`)
Per team, from its own available games: exponentially weighted (half-life 8 games; prior-season games
× 0.6 per season boundary), volume-weighted rates, shrunk toward the as-of league mean with provisional
pseudo-counts. Offence and defence-allowed versions of: EPA/play, EPA/dropback, EPA/designed rush,
success rate, explosive pass (≥ 20 yd) and rush (≥ 10 yd) rates, sack rate, INT rate, fumble-lost rate,
neutral-situation pass rate, points/drive (TD = 7, FG = 3 approximation), red-zone TD rate, starting field
position, plays/game and points/game. Also opponent-adjusted ridge ratings for EPA/play and points,
the effective sample size, and games played this season. Context: venue (+1 home / −1 away /
0 neutral), rest advantage and playoff flag.

Half-life, carry-over and pseudo-counts are **provisional** settings. They will be tuned on the development folds.

## Models so far
- **N**: naive training-period average home/away points.
- **A_raw**: the quoted line mapped to scores. **A_cal**: affine correction of spread and total learned on earlier seasons.
- **B**: football-only ridge on stacked team rows (own offence vs opponent defence → own points).
  Alpha is chosen by fitting on training seasons before the last one and validating on the last training
  season (never on the test season).

## Validation
Walk-forward expanding window: train 2016..S−1, test S for S in {2022, 2023, 2024}. **2025 is the
locked test season and has not been evaluated.** Paired differences use a season-week block
bootstrap. Historical market comparisons apply only to the final horizon (see `data_sources.md`).
