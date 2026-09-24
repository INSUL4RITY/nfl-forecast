# Progress log

Specification: `NFL_Forecasting_Claude_Build_Brief.md` (Downloads folder, 24 Sep 2026).
Update this file at the end of every working session.

## Current status (2026-09-24 UTC, session 1)

| Milestone | Status |
|---|---|
| 1. Data audit | **Done** (first pass). `docs/data_sources.md`, `reports/audit/audit_latest.json` |
| 2. Reproducible benchmarks | **Done** (baseline). Market raw/calibrated, naive, football-only ridge. Walk-forward 2022–24 |
| 3. Personnel & context | Not started |
| 4. Combined model | Not started |
| 5. Probabilities & uncertainty | Not started |
| 6. Website | Not started (no Node.js installed yet) |
| 7. Prospective operation | Snapshot archiving has begun; one baseline release written |

## Environment (what actually ran)
- Windows 11. Python 3.12.10 installed per-user via winget (session 1). Project venv at `.venv`.
- Packages pinned in `requirements.lock.txt` (nflreadpy 0.1.5, polars 1.44.2, scikit-learn 1.9.1 …).
- No Node.js and no git on this machine yet.
- `pytest`: 14 tests pass (leakage, sign convention, coherence, DST kickoff conversion, market policy).

## Results so far (real, produced by code in this repo)

Backtest `reports/backtest/bt_20260924T232335Z` (walk-forward; test seasons 2022, 2023, 2024; n = 854 games;
**2025 locked, not evaluated**):

| horizon | model | margin MAE | margin RMSE | total MAE | total RMSE | winner acc |
|---|---|---|---|---|---|---|
| final | A_market_raw | 9.49 | 12.48 | 10.11 | 12.95 | 0.681 |
| final | A_market_cal | 9.50 | 12.50 | 10.11 | 12.95 | 0.681 |
| final | B_football_ridge | 9.81 | 12.86 | 10.48 | 13.32 | 0.647 |
| final | N_naive_home | 10.63 | 13.80 | 10.80 | 13.66 | 0.546 |
| early | B_football_ridge | 9.81 | 12.86 | 10.48 | 13.32 | 0.644 |

Plain English: the market line is the best single predictor so far. The football-only model is clearly
better than naive (margin MAE −0.82, 95% CI [−1.08, −0.53]) but worse than the market (margin MAE +0.32,
CI [+0.16, +0.49]; total MAE +0.37, CI [+0.17, +0.57]). The affine market correction adds nothing
over the raw line. The early- and final-horizon football-only results are near-identical because
historically the only information difference is whether a few late games are available (no injuries yet).

Caveats: the historical market line has an unknown timestamp (treated as approximately closing).
nflfastR EPA values are current versions, not the versions available at the time (approximate reconstruction).
Ridge alpha selection is unstable across folds (1000 / 1 / 100).

## Releases
- `releases/2026/week_03/rel_20260924T232247Z.json`: generated 2026-09-24 23:22:47 UTC, **before** the
  ATL@GB kickoff (00:15 UTC 25 Sep) and all other Week 3 games. Baseline point forecasts
  (football-only + market raw/calibrated), no probabilities. It also contains 2026_04_PIT_CLE, because the
  window was 8 days at the time. The window is now one week per release. The alpha grid was widened after this release,
  so its code hash differs from the latest backtest. It is kept unchanged (releases are immutable).

## Key audit findings (details in docs/data_sources.md)
1. Schedule lines: one untimed line per game. **No free timestamped/72 h historical lines.**
2. Injuries: only the final weekly record per player. `date_modified` is gone from 2025 onward.
   **Early-horizon injury state cannot be reconstructed historically.**
3. Depth charts: weekly (no timestamps) 2016–2024; daily timestamped snapshots from 2025.
4. Participation (pressure/coverage) is released after the season, so it is excluded from live features.
5. FTN charting 2022+ (CC-BY-SA 4.0, attribute "FTN Data via nflverse").
6. Operational weather forecast runs are archived only from ~2026-04-07, so weather is prospective only.
7. Coordinator/play-caller history is not in any free feed; it needs a manual table.

## Blockers / needs from you
- **None blocking right now.** Optional decisions for later:
  - Paid historical market snapshots (e.g. The Odds API historical plan) would allow a historical 72 h
    market benchmark. Without it, early-horizon market comparisons accumulate prospectively.
    Your call; there is no need to decide now.
  - Milestone 6 needs **Node.js** (installable via `winget install OpenJS.NodeJS.LTS --scope user`). I will ask
    before installing.
  - Optional: **git** for version control (`winget install Git.Git`). I will ask before installing.

## Next steps (Milestone 3)
1. Starting-QB layer: QB identity per game from pbp (done in team-games), QB EPA/dropback history with
   shrinkage following the player across teams, and "QB change" flags. Expected starter at cutoff from depth charts
   (week-level before 2025) and the final injury report (final horizon only).
2. Non-QB availability: snap-share-weighted "missing expected snaps" by position group from the final injury
   report (final horizon), labelled with its horizon limitation.
3. Tune half-life / carry-over / pseudo-counts on dev folds; stabilise alpha (e.g. average of fold choices).
4. Ablations: no opponent adjustment, no personnel, short/long windows. Report failure cases.
5. Start the manual `data/manual/staff_history.csv` (HC/OC/DC/play-caller with effective dates).
6. Run `python -m nflcast ingest` regularly (ideally before each release) to grow the prospective
   injury/depth-chart/line archive.

## Session log
- **S1 (2026-09-24)**: installed Python; built the package skeleton, append-only snapshot store, market-price policy,
  audit (M1), games/market tables, pbp team-game aggregation, as-of features and ratings, models A/N/B,
  walk-forward backtest with block bootstrap, and the release writer; 14 tests; first baseline release.
