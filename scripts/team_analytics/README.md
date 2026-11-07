# NFL team analytics report

A weekly report on all 32 NFL teams, built in Python from public [nflverse](https://github.com/nflverse) data.
Live page: [insul4rity.github.io/sports-analytics/nfl-team-analytics](https://insul4rity.github.io/sports-analytics/nfl-team-analytics/)

It sits beside the [Insularity NFL Forecast](https://insul4rity.github.io/nfl-forecast/) but is separate from it: it never
reads or changes the forecasting model, and it uses no market data (spread, total and price columns are dropped on load).

## What it does

- **Opponent-adjusted efficiency.** EPA per play, per dropback and per rush for each offence and defence, adjusted for the
  opponents faced with a least-squares fit, plus success rate, explosive plays, third down, red zone, turnovers and more.
- **Matchups for the coming week.** For each game, every offence-against-defence measure has an expected value pulled toward
  the league average by how reliable that measure has been (shrinkage fitted on 2021-25). The headline edges are scored on
  these shrunk effects, so a noisy stat cannot top the list.
- **Player availability.** Regular players are matched across weekly rosters, injury reports, depth charts and snap counts.
  Absences are split into new and long-term, with the next player up and his own 2026 sample. Arrivals and departures from
  trades and signings are shown too.
- **Context.** Recent form, rest and travel (with a 2002-25 study of travel effects), defensive workload, penalties,
  referee crews, play-callers, quarterback splits, weather (forecast plus how similar past games played out) and flags for
  unusual games such as heavy rain.
- **Checks.** Every run writes quality checks (games matched, players matched, duplicates merged, missing data) to the
  report's Method section. Gaps are stated, never estimated.

## Files

| File | Role |
|---|---|
| `compute.py` | Downloads the data, computes every table and writes the report folder |
| `build_html.py`, `template.html` | Build the single-file interactive page |
| `export_games.py` | Writes one Markdown file per game |
| `refresh_status.py` | Re-reads injury reports, rosters and depth charts later in the week |
| `context.py`, `players.py`, `usage.py`, `depth.py`, `nextup.py`, `arrivals.py`, `garbage.py`, `unusual.py`, `referees.py`, `callers.py`, `game_weather.py` | One topic each |
| `publish_public.py` | Copies the newest report to the public page |
| `*_2026.json` | Small hand-kept inputs, each with its source (ESPN win rates, play-callers, referee assignments) |

Outputs for each week are in [`reports/team_analytics/`](../../reports/team_analytics/).

## Run it

From the repository root, with the project's Python environment:

```
python scripts/team_analytics/compute.py --season 2026 --through-week 8
python scripts/team_analytics/refresh_status.py --season 2026 --through-week 8
python -m pytest -q
```

## Data and credits

Play-by-play, rosters, injuries, depth charts, snap counts, schedules and players from nflverse; charting data from FTN and
advanced stats from Pro Football Reference, both via nflverse; Next Gen Stats via nflverse; ESPN team win rates copied by hand
with their date; weather forecasts from the National Weather Service and Open-Meteo. Built with Claude Code.
