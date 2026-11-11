# NFL team analytics report

A weekly report on all 32 NFL teams, built in Python from public [nflverse](https://github.com/nflverse) data.
Live page: [insul4rity.github.io/sports-analytics/nfl-team-analytics](https://insul4rity.github.io/sports-analytics/nfl-team-analytics/)

It sits beside the [Insularity NFL Forecast](https://insul4rity.github.io/nfl-forecast/) but is separate from it: it never
reads or changes the forecasting model, and it uses no market data (spread, total and price columns are dropped on load).

## What it does

- **Opponent-adjusted efficiency.** EPA per play, per dropback and per rush for each offence and defence, adjusted for the
  opponents faced with a least-squares fit, plus success rate, explosive plays, third down, red zone, turnovers and more.
- **Matchups for the coming week.** For each game, every offence-against-defence measure has an expected value pulled toward
  the league average by how little data supports it (empirical-Bayes shrinkage on this season's plays). The headline edges
  are scored on these shrunk effects, so a noisy stat cannot top the list.
- **Backtested and calibrated.** `backtest_matchups.py` replays 2021-25: fit on weeks 1 to W, predict every pairing of week
  W+1 (about 1,900 team-games per measure). The shrunk expectations beat a league-average guess on 14 of 17 measures but
  were too extreme early in a season (the real gap was 37% of the expected one at weeks 4-5), so each weight is multiplied
  by a week-and-measure factor (`matchup_calibration.json`). Each season predicted from the other four, that lowered the
  error on all 17 measures. Calibrated edges of 1.0 or more pointed the right way 66% of the time, small ones 53%.
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
| `backtest_matchups.py`, `matchup_calibration.json` | The 2021-25 backtest of the matchup expectations and the calibration fitted from it (refitted once a year) |
| `backtest_qb_sample.py`, `qb_shrinkage.json` | How much of a quarterback's early EPA per dropback lasts (2021-25), and the quarterback shrinkage fitted from it |
| `backtest_player_sample.py`, `player_shrinkage.json` | The same test for running backs (EPA per carry) and receivers (EPA per target): efficiency settles slowly, usage quickly |
| `ep_scale.py` | Warns if nflverse switches play-by-play to a revised EP valuation |
| `caller_check.py` | Compares the hand-kept play-caller file with Sam Hoppen's public dataset and lists differences to verify |
| `publish_public.py` | Copies the newest report to the public page |
| `*_2026.json` | Small hand-kept inputs, each with its source (ESPN win rates, play-callers, referee assignments, this season's referee flag rates from Hashtag Football, and quarterback news the rosters cannot show yet: trades, signings, named starters) |

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
with their date; weather forecasts from the National Weather Service and Open-Meteo; play-callers cross-checked against Sam Hoppen's
public dataset (github.com/samhoppen/NFL_public), which is read at build time and not copied here; this season's flags per referee copied by hand, with their date, from Hashtag Football's penalty tracker. Built with Claude Code.
