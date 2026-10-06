# nflcast — persistent project rules

Read `PROGRESS.md` first (status, model version, schedule, data locations, next steps). Specification:
`C:\Users\Craig\Downloads\NFL_Forecasting_Claude_Build_Brief.md`. Live site: https://insul4rity.github.io/nfl-forecast/
(public repo INSUL4RITY/nfl-forecast). Public name: **Insularity NFL Forecast** (dark theme only); the internal package and
CLI stay `nflcast`; keep the URL and repo name (published evidence and links point at them).

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
- **Model pick = rule "original-pick" for games from 2026-10-01 (user decision):** the spread pick is locked at the earliest
  valid pregame version with a line and graded on that line; earlier games keep "final-pregame"; projected winner and margin
  error use final_pregame (`predict/picks.py`). Never regrade finished games under a new rule; record any rule change in
  PROGRESS.md and state it on the Method page.
- **Final for 2026 (user, 2026-10-05):** after the carry-over test (no variant passed) the model, the pick rule and the
  publication schedule are final for the season. Only data refreshes and bug fixes; no model, rule or design changes.
  Exception the user asked for (2026-10-06): stats-only line, "Big gap" tag, edge size and the stats-only breakdown
  (display only; see PROGRESS.md).
- **Weekly publication (user decision 2026-10-05):** from week 5 a week is first published at Thursday 09:00 UK before its
  first game (`predict/schedule.py`); the model pick locks then. Operational only; do not move it without the user.

## How things run
- Venv: `.\.venv\Scripts\python.exe -m nflcast <cmd>` from the project folder (refresh PATH from User+Machine env first in
  PowerShell), or `nflcast.cmd <cmd>` from any folder (give the user this form).
- Public pages must never show internal codes or player IDs; map them to plain English in `web/` (verify-claims checks this).
- After any display change, run `scripts/layout_audit.js` in the browser on the local build (widths 1280, 768, 414, 375, 320)
  and on the live site after deploy: 0 issues required. Wrap every table in `.table-wrap` (cells do not wrap by default).
- The user accepts that updates pause while the PC is off; never recreate or back-date missed forecasts.
- Desktop alerts (`predict/alerts.py`, `scripts/toast.ps1`) tell the user when a human is needed; never let alert code block a
  cycle; never send real toasts from tests (use a fake `send`); re-alert on substance, never on the countdown text.
- Windows Task Scheduler `nflcast-operate` runs `scripts/operate.ps1` every 30 min while the user is logged in.
  Pause it (`Disable-ScheduledTask -TaskName nflcast-operate`) before development work; re-enable afterwards. For longer
  work, develop in a separate git worktree (copy `data/raw` + `data/processed` into it, `npm ci` in its `web/`; never link
  folders out of the worktree) so forecasts keep publishing, and pause only to merge.
- Tests: `.\.venv\Scripts\python.exe -m pytest -q` (all must pass before pushing). Site: `cd web; npx next build`.
- PowerShell 5.1 mangles native args with quotes/spaces (use Python subprocess or files); Git's openssl needs relative paths.
- Scratch scripts go in `.scratch/` (git-ignored) — the session scratchpad path is too long for Windows.
