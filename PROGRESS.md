# Progress log

Specification: `NFL_Forecasting_Claude_Build_Brief.md` (Downloads folder, 24 Sep 2026).
Update this file at the end of every working session.

## Session 2 (2026-09-25): reliability fixes from independent review

All five review findings were reproduced and fixed. Details are in `docs/methodology.md` (new sections).

| Finding | Reproduced | Fix |
|---|---|---|
| 1. QB availability | Yes: CHI had no Week 3 injury report yet; the code treated "no report" as healthy, so Caleb Williams was 100%. QB2 could be promoted without checking his own status (Bagent was Questionable/DNP in Week 1 and relieved Williams in Week 2) | `features/qb_availability.py`: every QB resolved with evidence and timestamp; missing/stale report and stale depth chart are flagged, never treated as available; historical start rates (daily charts where n≥30, else weekly); sequential scenarios; documented overrides (`data/manual/qb_overrides.csv`). Williams is now 96.7% with the "report not available" flag |
| 2. Validation | Yes: `pending_validation_failed` entries could be written, displayed and scored | `predict/validation.py` shared by release/export/score; failed combined → labelled football-only fallback; nothing valid → `rejected_validation_failed`, never current or scored; newest valid version wins |
| 3. Input-driven updates | Yes: only 20 h heartbeat + final hour | Per-game input fingerprints (market, QBs, injury report, team form, model); `operate` publishes on any change; no updates after kickoff |
| 4. Publication records | Yes: ATL@GB releases generated 23:22/23:51/00:02 UTC, kickoff 00:15, repo created 00:30:49, first public push 00:31:03 | `predict/publication.py`: evidence only from GitHub server timestamps (`releases/publication_evidence.json`); append-only `releases/corrections.jsonl` (3 ATL@GB corrections); release files untouched; scoring split by verification |
| 5. Labels/explanations | Yes: future games showed "frozen (scored)" | States latest pregame / locked at kickoff / scored; methodology explains actual-starter proxy, untimed closing lines, display-only non-QB injuries, no weather/coaching |

Also: the `locked-test` command now refuses a second untouched run (`--revision-label` needed; writes `reports/revised_evaluations/`).
The production model and the original 2025 evaluation are unchanged.

Tests: 38 passing (was 18). New regression tests: QB1 and QB2 both out, QB2 availability checked, missing report,
early-exit rate, stale report, stale/missing depth chart, overrides (timing and required source), leader never inflated,
invalid newer version cannot replace valid older one (selection, export, scoring), state labels, verification labels,
input-change triggers, final window and no updates after kickoff.

Remaining limitations: live QB availability depends on nflverse's refresh cadence (no official NFL feed); the
rates for Questionable/Doubtful QBs rest on small samples (n=193/31, weekly charts); overrides require manual entry
with a public source; the historical backtest still uses the actual-starter proxy and untimed closing lines; non-QB
injuries are display-only; weather and coaching are not modelled; publication evidence depends on GitHub Actions records.

## Status at end of session 1 (2026-09-25 00:10 UTC)

| Milestone | Status |
|---|---|
| 1. Data audit | **Done.** `docs/data_sources.md`, `reports/audit/audit_latest.json` |
| 2. Benchmarks | **Done.** Market raw/calibrated, naive, football-only; walk-forward |
| 3. Personnel & context | **Done.** QB ratings/expected starter, injury availability, schedule context, ablations, window tuning |
| 4. Combined model | **Done.** Residual ridge (selected), direct ridge, residual HGB. Frozen in `configs/production.yaml` |
| 5. Probabilities & intervals | **Done.** Calibrated on out-of-fold predictions; locked 2025 test run **once** |
| 6. Website | **Live** at https://insul4rity.github.io/nfl-forecast/ (GitHub Pages, repo INSUL4RITY/nfl-forecast) |
| 7. Prospective operation | **Running.** Task Scheduler `nflcast-operate` every 30 min (while logged in); auto-publishes to GitHub |

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
- Keep the PC on and signed in to Windows on game days (the scheduled task only runs while you are logged in).
- If `logs/operate.log` shows push failures, the GitHub login may have expired: run `gh auth login --web`.
- Optional/paid: historical timestamped lines (e.g. The Odds API) would enable a historical 72 h market benchmark. Not needed.

## Session log (continued)
- **S1b (2026-09-25):** registered Task Scheduler job (Interactive logon; S4U needs admin). Installed GitHub CLI, user signed in
  (INSUL4RITY). Rewrote local commit authors to the GitHub noreply address before the first push. Created the public repo
  nfl-forecast, enabled Pages (Actions build), first deploy succeeded, live site verified (styles, base-path links, navigation).

## Next steps
- Keep releases running through the season; after ~4 weeks, review live scoring (small samples: don't over-read).
- Advanced model track (FTN charting 2022+, PFR pressure 2018+) evaluated on its own date range, as an ablation.
- Maintain `data/manual/staff_history.csv` (coordinators/play-callers) if you want coaching features.
- Early-horizon market evaluation once enough archived line snapshots exist.
- Optional: a team-ratings history chart and a per-week results view on the site.

## Session log
- **S1 (2026-09-24/25):** installed Python, Node.js and git; built M1–M7. Ran audit, backtests, tuning, locked test (once),
  3 releases (1 baseline + 2 production for Week 3), website build and mobile/desktop check in the browser pane, one `operate` cycle.
