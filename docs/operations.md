# Operations (Milestone 7)

**Model frozen** (v1.0-2026-rest-of-season, `configs/model_freeze.yaml`): every release loads the frozen artifact; a
changed artifact or config blocks publishing. Weekly health checks:

The launcher `nflcast.cmd` works from **any** folder (it switches to the project folder first). Running
`.\.venv\Scripts\python.exe ...` from another folder (e.g. `C:\Users\Craig`) fails with "not recognized": that relative path
only exists inside the project folder.

```powershell
& "C:\Users\Craig\NFL MODEL PROJECTIONS\nflcast.cmd" freeze-check     # frozen artifact + configs unchanged
& "C:\Users\Craig\NFL MODEL PROJECTIONS\nflcast.cmd" verify-claims    # labels, public-page wording, GitHub evidence, archive
& "C:\Users\Craig\NFL MODEL PROJECTIONS\nflcast.cmd" backup           # private off-PC backup sync + verification
Get-Content "C:\Users\Craig\NFL MODEL PROJECTIONS\logs\operate.log" -Tail 5   # healthy run ends with "operate: done"
```

Off-PC backup: private GitHub repository `INSUL4RITY/nfl-forecast-data` (weather snapshots, injury snapshots/versions,
schedule/market-line snapshots). Pushed every cycle; verified against the GitHub API (privacy + identical blob hashes).

**PC off / asleep / logged out:** updates simply pause; the public site stays up with the last published forecasts. After you
log in to Windows, the task catches up within minutes (missed runs start when available) and then runs every 30 minutes.
Claude (the app or chat) does not need to be open. Anything that should have happened while the PC was off (e.g. a
final-hour update) is not recreated afterwards.

## Full slate before the first kickoff
A release covers every unplayed game of the upcoming week. As soon as the last game of a week kicks off, the next cycle
publishes the whole next week (dry run 2026-09-25: all 16 week-4 games, ~3 days before the Thursday game). Missing or stale
optional inputs never block a forecast: QB availability falls back to documented historical start rates (flagged
"designation pending" / "report not published yet"), weather is display-only, and the page states what was incomplete.
Only a failed validation can withhold a combined forecast, and then the football-only fallback is published instead.

## Desktop alerts (from 2026-09-29)
Each cycle checks games kicking off within 48 h and raises a Windows notification (`src/nflcast/predict/alerts.py`,
`scripts/toast.ps1`) when a human should look: no QB identified or no valid new forecast; injury report not current within
36 h (one combined alert if many teams); designations still pending within 24 h; an official Out kept despite unconfirmed
data; lead QB below 90%; no market line within 24 h; The Odds API credits low; a failed or blocked run; and a "caught up"
notice after >= 6 h without a completed run. Clicking opens the game page. Each issue alerts once, again if it changes (at
most every 2 h) or is still open after 12 h. Everything is also written to `logs/alerts.log` ("shown" / "NOT SHOWN").
**Windows notifications must be on** (Settings > System > Notifications, and allow "Windows PowerShell" in the list of
senders); otherwise alerts are only logged, marked NOT SHOWN, and retried.

## After the PC has been off
Nothing to type. The first cycle after login fetches the current state of every source in one pass (about 2 minutes):
nflverse schedules/scores, play-by-play for every completed game, the current injury file (latest report for every
player-week), depth charts (nflverse appends each daily update with a timestamp, so their history is complete), weekly
rosters, one The Odds API request for the whole slate, and weather. It then scores finished games and publishes a new
forecast for every game whose inputs changed. What cannot be recovered: market lines and injury-report versions that came
and went while the PC was off (the free API has no line history), and forecasts that would have been made in that time
(never recreated or back-dated). Games that kicked off while the PC was off keep their last pre-kickoff forecast.

## Market feed (The Odds API, from 2026-09-25)
The key lives only in the git-ignored project file `.env` (`ODDS_API_KEY=...`), which every nflcast process loads at start,
including the scheduled task after a restart. To enter or replace it: open `C:\Users\Craig\NFL MODEL PROJECTIONS\.env` in
Notepad and set the line `ODDS_API_KEY=<your key>` (no quotes), then save. Never paste it into chat, commits or the site.
Each cycle logs `operate: odds fetched=... reason=... credits_remaining=...` (never the key). Rules and budget:
`docs/data_sources.md`, settings: `configs/market_feed.yaml`. If the API is unavailable, stale or low on credits, the nflverse
line is used automatically and the game page names the source.

## One cycle

```powershell
.\scripts\operate.ps1          # or: .\.venv\Scripts\python.exe -m nflcast operate
```

Each cycle:
1. `ingest`: refreshes schedules (market lines), current-season play-by-play, injuries, depth charts and weekly rosters.
   Every changed file is stored as a new append-only raw snapshot (this is the as-of archive).
2. `build`: rebuilds games, team-games, QB games and feature tables.
3. `score`: scores the frozen pregame versions of finished games (`reports/prospective/`).
4. Updates publication evidence (`releases/publication_evidence.json`) and appends any late-publication corrections.
5. Builds a candidate release in memory and publishes it **only if due** (see `src/nflcast/predict/operate.py`):
   - any unplayed game's inputs changed (market spread/total, quarterback availability, injury report, team form, model), or
   - a game kicks off within 60 minutes and no release has been made in that window (final-pregame version), or
   - no release in the last 20 hours (heartbeat; also provides the ≥72 h "early" versions).
   Games that have kicked off are never updated. Forecasts failing validation never become current.
6. `export-web`, push (then evidence for the pushed files is recorded and pushed), and `next build` for the local copy.

Manual QB override (only with a public source): add a row to `data/manual/qb_overrides.csv`, including
`source_published_at_utc`. It affects only forecasts made after that time. Check `python -m nflcast verify-publication`
to record publication evidence on demand.

Failures are written to `logs/operate.log`; the previous release and site stay in place.

## Scheduling (enabled 2026-09-25)

Windows Task Scheduler task **`nflcast-operate`** runs `scripts/operate.ps1` every 30 minutes (hidden window). It runs only
**while you are logged in to Windows**: running while logged out needs administrator rights (S4U logon was refused). Updates
pause while the PC is off or asleep and resume after login (catch-up run, then every 30 minutes).

```powershell
Get-ScheduledTaskInfo -TaskName nflcast-operate      # last/next run and result (0 = OK)
Disable-ScheduledTask -TaskName nflcast-operate      # pause (e.g. off-season)
Enable-ScheduledTask  -TaskName nflcast-operate      # resume
Unregister-ScheduledTask -TaskName nflcast-operate   # remove completely
```

## Publishing (GitHub Pages)

- Repository: https://github.com/INSUL4RITY/nfl-forecast (public). Live site: **https://insul4rity.github.io/nfl-forecast/**
- `.github/workflows/pages.yml` builds `web/` with `NEXT_BASE_PATH=/nfl-forecast` and deploys on every push that touches `web/`.
- `operate` auto-publishes: when a new release or newly scored result appears, it commits `releases/`, `reports/prospective/`
  and `web/public/data/`, then pushes to `main`. Git authenticates through the GitHub CLI login (`gh auth status`).
- Commits use the GitHub noreply address `333550074+INSUL4RITY@users.noreply.github.com` (set in this repo's git config).
- If the GitHub login expires, run `gh auth login --web` again. Pushes then resume at the next cycle.

## Rules
- Never edit or delete files in `releases/`: they are the published record.
- Re-running the full backtest is fine; do **not** change `configs/production.yaml` without recording why in PROGRESS.md.
- The 2025 locked test has been used once (2026-09-24). The next untouched evaluation is the prospective 2026 record.
