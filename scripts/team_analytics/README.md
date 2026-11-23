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
  error on all 17 measures, and predicting each season only from earlier ones (forward-only) on 16 of 17. Notable headline edges pointed the right way 67% of the time (pass rush vs protection 72%, big passing plays 60%); explosive runs (58%) are not a headline edge.
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
| `ngs_trends.py`, `ngs_trends_2026.json`, `backtest_coverage.py`, `coverage_backtest.json` | Next Gen Stats coverage, personnel, pass-rush and scheme usage (read weekly from NFL.com's Next Gen Trends pages), and the 2018-25 test that decided they are shown as description only |
| `reliability.py` | The Low/Medium/High reliability badges, from the fitted shrinkage weights (team measures and player efficiency) |
| `backtest_special_teams.py`, `st_shrinkage.json` | How much special-teams EPA per game lasts; the combined rating keeps that share (about 27% after 9 games) |
| `backtest_streaks.py`, `streak_backtest.json` | Hot and cold teams (2021-25): how much of a last-four-games form change lasted (none measurable), and whether luck and one-score records carry on (they do not); the hot/cold verdicts quote it |
| `backtest_qb_change.py`, `qb_change.json` | What a team loses when someone other than its opening quarterback starts (2021-25, pre-game definition): EPA per dropback -0.104 with a rookie (95% -0.153 to -0.060, 154 games), -0.085 with a veteran backup (-0.117 to -0.057, 392); traded-in starters too few to call. Quoted in the matchup cautions and summaries |
| `backtest_td_expectation.py`, `td_expectation.json` | Touchdown rate of a target or designed carry by yards from the end zone (2021-25) and the test behind the touchdown-opportunity table: expected touchdowns predicted second-half touchdowns with less error than actual touchdowns (0.214 vs 0.230 per game); only 29% of touchdowns above or below expected carried on |
| `backtest_line_absences_pregame.py`, `line_absence_pregame.json` | What an offensive-line starter known to be out before kickoff costs (2021-25, 2,238 team-games: -0.036 EPA per dropback each, 95% -0.051 to -0.020; no extra cost against strong pass rushes); the line caution quotes it from week 11 |
| `backtest_line_absences.py`, `line_absence_backtest.json` | Kept for history: the first version counted a starter as missing when he played under half the snaps, so it included in-game injuries (-0.047) |
| `game_variance_test.json` | Test of game-level variance in the matchup shrinkage (2021-25): no gain, so it stays off |
| `layout_audit_state.py`, `layout_audit_state.json` | Whether a browser layout audit is needed: fingerprints of the page-shaping files at the last build that passed the local and live audits (lets the unattended refresh skip it for data-only changes) |
| `ep_scale.py`, `ep_harmonise.py`, `ep_scale_2026.yaml` | Puts 2026 play-by-play back on the original EP valuation exactly as the forecast does (archived values for plays in the last original-scale snapshot, the forecast's frozen line for later plays; `ep_scale_2026.yaml` is a verbatim copy of main's `configs/ep_scale.yaml`), checks the residual each build, and warns if any season is still on a revised scale |
| `caller_check.py` | Compares the hand-kept play-caller file with Sam Hoppen's public dataset and lists differences to verify |
| `publish_public.py` | Copies the newest report to the public page, with its preview image and glossary |
| `og_card.py` | Open Graph and Twitter card tags and the 1200 x 630 preview image (top of that week's ratings), screenshotted by headless Edge or Chrome at build time |
| `glossary.py` | The shared glossary of metric definitions (raw, opponent-adjusted, weighted and shrunk; luck; ratings) for this page and the forecast, written as `glossary.html` |
| `*_2026.json` | Small hand-kept inputs, each with its source (ESPN win rates, play-callers, referee assignments, this season's referee flag rates from Hashtag Football, and quarterback news the rosters cannot show yet: trades, signings, named starters) |

Outputs for each week are in [`reports/team_analytics/`](../../reports/team_analytics/).

## Page checks

The page is a standard HTML document (`lang="en-GB"`). `scripts/layout_audit.js` checks it at 1280, 768, 414, 375 and 320 px for sideways
scrolling and overflowing panels, and runs axe-core 4 in the same pass: any serious or critical accessibility violation fails the audit.

## Weekly build checklist

1. Check the data is in: every game of the last week in play-by-play, FTN charting and PFR advanced stats (nflverse).
2. Update the hand-kept files: `qb_news_<season>.json` (named starters the rosters cannot show yet), `referees_<season>.json`
   (Football Zebras), `referee_rates_<season>.json` (Hashtag Football), `ngs_trends_<season>.json` (NFL.com Next Gen Trends,
   `ngs_trends.py`).
3. `compute.py --season 2026 --through-week <W> --refresh`, then `refresh_status.py --season 2026 --through-week <W>` (statuses,
   page and per-game Markdown).
4. `python -m pytest -q`, then `layout_audit_state.py check`; if it says AUDIT NEEDED, run the browser audit (layout and axe-core,
   five widths) on the local page and record it.
5. Publish the private report (with `glossary.html`), run `publish_public.py`, push both repositories, audit the live page and record it.

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
public dataset (github.com/samhoppen/NFL_public), which is read at build time and not copied here; this season's flags per referee copied by hand, with their date, from Hashtag Football's penalty tracker; coverage, personnel and scheme usage from NFL Next Gen Stats (NFL.com Next Gen Trends), read weekly with the date. Built with Claude Code.
