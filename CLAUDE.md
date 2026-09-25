# nflcast — persistent project rules

Read `PROGRESS.md` first (status, model version, schedule, data locations, next steps). Specification:
`C:\Users\Craig\Downloads\NFL_Forecasting_Claude_Build_Brief.md`. Live site: https://insul4rity.github.io/nfl-forecast/
(public repo INSUL4RITY/nfl-forecast).

## Non-negotiable rules
- **Market inputs: point spread and total only.** Never moneylines, prices, implied odds, betting splits, stakes or returns.
  `data/policy.py` enforces this; do not weaken it.
- **Never fabricate** data, forecasts, metrics, publication times or claims that code ran. Report failures as failures.
- **Releases are immutable.** Never edit/delete `releases/<season>/week_<nn>/rel_*.json`, `releases/archive/*`,
  `releases/corrections.jsonl` (append-only), `releases/publication_evidence.json` (add-only). Record errors as corrections.
- **Publication times come only from independent evidence** (GitHub Actions push-run creation time, RFC 3161 timestamps,
  Internet Archive captures). Local clocks/commit dates are never publication evidence. Never back-date evidence.
- **The model is FROZEN for the rest of the 2026 season** (`configs/model_freeze.yaml`). Do not retrain, retune, change
  features or production choices. Scheduled runs may only refresh inputs (data, market lines, QB availability, injuries,
  weather display) and publish forecasts from the frozen artifact. A model change requires a new version, recorded in
  PROGRESS.md, and must not be evaluated as "untouched" on already-seen seasons.
- **2025 locked test was used once (2026-09-24).** `locked-test` refuses to re-run without `--revision-label`.
- **Market feed v2 (user-authorised 2026-09-25):** The Odds API (free plan) supplies spreads/totals when valid, nflverse is the
  fallback (`src/nflcast/data/odds_api.py`, `configs/market_feed.yaml`). Key only in git-ignored `.env`; never print, log,
  commit or publish it (verify-claims checks). Stay under the 500-credit free allowance; no paid plan.
- **No new features this season.** Weather and non-QB injuries are display-only (did not pass the pre-specified rule).
  Coaching is deferred. Collection continues for future evaluation.
- **Chronological validation only**; tune/dev/locked separation; paired comparisons on identical games.
- **Retrospective data must be labelled** (historical weather = stitched forecasts; historical lines = untimed ≈ closing;
  final-horizon backtest uses the actual starter as a proxy).
- **Privacy:** never commit secrets; commits use the GitHub noreply address; the data backup repo is PRIVATE.
- Ask the user before paid services, new external accounts, or changing the scheduled task/system settings.

## How things run
- Venv: `.\.venv\Scripts\python.exe -m nflcast <cmd>` from the project folder (refresh PATH from User+Machine env first in
  PowerShell), or `nflcast.cmd <cmd>` from any folder (give the user this form).
- Public pages must never show internal codes or player IDs; map them to plain English in `web/` (verify-claims checks this).
- The user accepts that updates pause while the PC is off; never recreate or back-date missed forecasts.
- Windows Task Scheduler `nflcast-operate` runs `scripts/operate.ps1` every 30 min while the user is logged in.
  Pause it (`Disable-ScheduledTask -TaskName nflcast-operate`) before development work; re-enable afterwards.
- Tests: `.\.venv\Scripts\python.exe -m pytest -q` (all must pass before pushing). Site: `cd web; npx next build`.
- PowerShell 5.1 mangles native args with quotes/spaces (use Python subprocess or files); Git's openssl needs relative paths.
- Scratch scripts go in `.scratch/` (git-ignored) — the session scratchpad path is too long for Windows.
