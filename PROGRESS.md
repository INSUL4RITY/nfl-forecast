# Progress log

Specification: `NFL_Forecasting_Claude_Build_Brief.md` (Downloads folder, 24 Sep 2026).
Update this file at the end of every working session.

## Current status (2026-09-25 00:10 UTC, end of session 1)

| Milestone | Status |
|---|---|
| 1. Data audit | **Done.** `docs/data_sources.md`, `reports/audit/audit_latest.json` |
| 2. Benchmarks | **Done.** Market raw/calibrated, naive, football-only; walk-forward |
| 3. Personnel & context | **Done.** QB ratings/expected starter, injury availability, schedule context, ablations, window tuning |
| 4. Combined model | **Done.** Residual ridge (selected), direct ridge, residual HGB. Frozen in `configs/production.yaml` |
| 5. Probabilities & intervals | **Done.** Calibrated on out-of-fold predictions; locked 2025 test run **once** |
| 6. Website | **Done (local).** Next.js 16 static site in `web/`, built to `web/out/`. **Not yet hosted publicly** |
| 7. Prospective operation | **Built.** `nflcast operate` + `scripts/operate.ps1`. **Not yet scheduled** (needs your OK) |

## Environment
- Python 3.12.10 (venv `.venv`, pins in `requirements.lock.txt`), Node.js 24.19, Next.js 16.3.6, TypeScript 5.9, git 2.55.
- Git repository initialised; commits per milestone.
- `pytest`: 18 tests pass (leakage, signs, coherence, DST, market policy, probabilities, intervals, scoring).

## Results (real outputs of the code in this repo)

Final-pregame horizon, margin/total RMSE (MAE in reports):

| Model | 2019–21 tune | 2022–24 dev | 2025 locked |
|---|---|---|---|
| Market only | 13.12 / 13.26 | 12.48 / 12.95 | **12.24 / 13.24** |
| Combined (selected, C_resid core_qb) | 13.13 / 13.27 | **12.47 / 12.90** | 12.29 / 13.32 |
| Football only (+QB) | 13.34 / 13.50 | 12.72 / 13.13 | 12.70 / 13.28 |
| Naive home average | 14.83 / 13.98 | 13.80 / 13.66 | 14.11 / 13.83 |

- Combined vs market: every paired 95% CI includes zero (dev and locked). **The market line is not beaten**; this is the honest headline.
- QB features: margin RMSE 12.85 → 12.72 (dev, football-only); in QB-change games margin MAE 10.11 → 9.77 (market 9.68).
- Injury (non-QB) features: small gain for football-only, none once the market is included → not in the production model.
- Probabilities (locked 2025): log loss combined 0.6327, market-only 0.6286, football-only 0.6444. Calibration table in the report.
- Intervals (locked 2025, combined): 80% → 80.7% coverage; 95% → 97.2% (margin). Total: 80% ≈ 80%, 95% ≈ 95%.
- Reports: `reports/backtest/LATEST.md`, `reports/locked_test/LATEST.md`, `reports/tuning/`.

## Releases (prospective, immutable)
- `releases/2026/week_03/rel_20260924T232247Z.json`: Milestone-2 baseline (schema v1, not scored, kept as a record).
- `rel_20260924T235129Z.json`, `rel_20260925T000247Z.json`: production schema v2, all 16 Week 3 games, generated before
  the first kickoff (ATL@GB 00:15 UTC 25 Sep). These are the first genuinely live forecasts; they will be scored after the games.

## Decisions made (routine, recorded)
- Production = residual-to-market ridge with QB features (tie on the selection criterion; simplest of the tied options).
  Early releases apply it to the line observed at release time (validated only at final horizon; labelled).
- Locked 2025 result (market marginally better) did **not** change the choice; the 2026 live record is the next untouched test.
- Window settings kept at half-life 8 / carry 0.6 (grid flat).
- Tie probability = smoothed REG tie rate since 2017 (~0.36%); interval method = OOF residual quantiles.
- Site: static export; the displayed verdict text on /performance summarises current results and must be revisited if results change.

## Needs from you
1. **Scheduling:** OK to register a Windows scheduled task running `scripts/operate.ps1` every 30 minutes? (It creates a
   standing background job on your PC. Command in `docs/operations.md`.) Without it, run `.\scripts\operate.ps1` manually before
   game days (at minimum ~once a day and in the hour before kickoffs).
2. **Public hosting:** the site in `web/out/` needs a host account in your name (GitHub Pages, Cloudflare Pages, Netlify or Vercel,
   all free). Tell me which, once you have an account, and I'll set up deployment.
3. Optional/paid: historical timestamped lines (e.g. The Odds API) would enable a historical 72 h market benchmark. Not needed.

## Next steps
- Keep releases running through the season; after ~4 weeks, review live scoring (small samples: don't over-read).
- Advanced model track (FTN charting 2022+, PFR pressure 2018+) evaluated on its own date range, as an ablation.
- Maintain `data/manual/staff_history.csv` (coordinators/play-callers) if you want coaching features.
- Early-horizon market evaluation once enough archived line snapshots exist.
- Optional: a team-ratings history chart and a per-week results view on the site.

## Session log
- **S1 (2026-09-24/25):** installed Python, Node.js and git; built M1–M7. Ran audit, backtests, tuning, locked test (once),
  3 releases (1 baseline + 2 production for Week 3), website build and mobile/desktop check in the browser pane, one `operate` cycle.
