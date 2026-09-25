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

## Scheduling (not yet enabled)

Recommended: run every 30 minutes during the season. On Windows (run once in PowerShell, as the user):

```powershell
schtasks /Create /TN "nflcast-operate" /SC MINUTE /MO 30 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File \"C:\Users\Craig\NFL MODEL PROJECTIONS\scripts\operate.ps1\""
```

The PC must be on and online at those times for releases to be timely. A cloud runner (for example GitHub Actions on a
schedule) avoids that dependency, but it needs a GitHub account and repository.

## Publishing the site

`web/out/` is a static site. Free hosts include GitHub Pages, Cloudflare Pages, Netlify and Vercel. They all need an account in your
name. Once one exists, deployment is a folder upload or a small CI workflow.

## Rules
- Never edit or delete files in `releases/`: they are the published record.
- Re-running the full backtest is fine; do **not** change `configs/production.yaml` without recording why in PROGRESS.md.
- The 2025 locked test has been used once (2026-09-24). The next untouched evaluation is the prospective 2026 record.
