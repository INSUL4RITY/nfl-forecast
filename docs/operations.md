# Operations (Milestone 7)

## One cycle

```powershell
.\scripts\operate.ps1          # or: .\.venv\Scripts\python.exe -m nflcast operate
```

Each cycle:
1. `ingest`: refreshes schedules (market lines), current-season play-by-play, injuries, depth charts and weekly rosters.
   Every changed file is stored as a new append-only raw snapshot (this is the as-of archive).
2. `build`: rebuilds games, team-games, QB games and feature tables.
3. `score`: scores the frozen pregame versions of finished games (`reports/prospective/`).
4. Publishes a release **only if due** (see `src/nflcast/predict/operate.py`):
   - a routine release if none in the last 20 hours (this produces the "early" ≥72 h versions), and
   - a final-pregame release when a game kicks off within 60 minutes and none has been made in that window.
5. `export-web` and `next build`, so `web/out/` holds the up-to-date static site.

Failures are written to `logs/operate.log`; the previous release and site stay in place.

## Scheduling (enabled 2026-09-25)

Windows Task Scheduler task **`nflcast-operate`** runs `scripts/operate.ps1` every 30 minutes (hidden window). It runs only
**while you are logged in to Windows**: running while logged out needs administrator rights (S4U logon was refused). The PC
must be on, online and signed in for releases to be timely.

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
