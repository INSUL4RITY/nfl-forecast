# Data sources, availability matrix and licences

Milestone 1 deliverable. Everything marked **measured** comes from `python -m nflcast audit`
(results: `reports/audit/audit_latest.json`, first run 2026-09-24 UTC). Items marked **documented**
come from provider documentation and have not been independently verified.

"Available" means the data exists **today**. It does not mean the data existed at the time a
historical forecast would have been made. The *as-of* column records what we can actually prove.

## Availability matrix

| Source (nflverse unless noted) | Seasons (measured) | Refresh / lag | Historical as-of timestamps? | Use in strict backtest | Licence / attribution |
|---|---|---|---|---|---|
| Schedules, scores, venue, rest, roof | 1999–2026 | Updated during the season (file Last-Modified 2026-09-24) | No. One row per game, with no version history | Yes. Fixture info is known in advance; scores go only into the outcomes partition | CC-BY-4.0 (nflverse-data) |
| Schedule `spread_line` / `total_line` | 1999–2025 complete; 2026 posted for the current week only | Overwritten over time | **No timestamp.** One line per game, timing unknown | Final-pregame horizon only, labelled `approx_closing`. **Not** valid for the 72 h horizon | CC-BY-4.0. Price columns (moneyline, spread/total odds) are dropped at ingestion (measured: 6 columns dropped) |
| Play-by-play (EPA, success, CPOE, drives) | 1999–2026 | Nightly-ish after games (documented). We assume a 12 h lag | Game-level: a game counts once kickoff + 12 h ≤ cutoff | Yes (core). CPOE null on ~15–22% of dropbacks (sacks/throwaways etc.) | CC-BY-4.0. nflfastR EPA/CPOE models are periodically re-fit, so this is an **approximate** historical reconstruction |
| Player weekly stats | 1999–2026 | Nightly | Game-level | Yes | CC-BY-4.0 |
| Weekly rosters | 2002–2026 | Weekly | Week label only | Approximate (week-level) | CC-BY-4.0 |
| Depth charts | 2001–2026 | Daily from 2025 | **2016–2024: weekly, no timestamp. 2025+: daily snapshots with `dt`** (measured: 219 distinct days in 2025) | Week-level approximation before 2025; true as-of from 2025 | CC-BY-4.0 |
| Injury reports | 2009–2026 | Updated during the week (file refreshed daily) | **Measured: one record per player per week, i.e. only the final report.** `date_modified` exists through 2024 and is **absent from 2025**. Wednesday/Thursday practice versions are not retained | Final-pregame horizon only (final report ≈ Friday). **Cannot reconstruct 72 h injury state historically.** 2026+ we archive our own snapshots | CC-BY-4.0 |
| Snap counts (PFR) | 2012–2026 | Within days | Game-level | Yes (usage/workload after each game) | Sourced from Pro-Football-Reference via nflverse. Check Sports Reference terms before redistributing |
| Participation (pressure, coverage, routes) | 2016–2025. **2026 file absent** | **Released after the season** (2025 file last modified 2026-02-10) | n/a | **Not usable as a live weekly feature.** `was_pressure`/`route` ~60% null before 2023 | CC-BY-4.0. NGS-derived fields |
| FTN charting (motion, PA, RPO, INT-worthy, drops, blitzers) | 2022–2026 | Documented "within 48 hours"; 2026 measured `date_pulled` lag 2–9 days | `date_pulled` is the **latest** re-pull, not first publication. Earlier seasons show re-pulls months later | Advanced model only, 2022+, with a ≥ 1 week lag assumption for safety | **CC-BY-SA 4.0, attribute "FTN Data via nflverse"** |
| PFR advanced passing (pressures, hurries, bad throws, drops) | 2018–2026 | Weekly during the season | Game-level | Candidate line-play/pressure features, 2018+ | Pro-Football-Reference via nflverse; check terms |
| Next Gen Stats passing | 2016–2026 | Weekly | Week label | Candidate QB features, 2016+ | NFL Next Gen Stats via nflverse; check terms |
| Officials | 2015–2026 | Pre-season / weekly | Week-level | Not planned | CC-BY-4.0 |
| Staff (HC/OC/DC/play-caller) | Only the head coach name is in schedules | n/a | No effective or announcement dates | **Gap:** needs a maintained manual table (`data/manual/staff_history.csv`, to be created) | n/a |
| Weather: Open-Meteo Historical Forecast API | Works for 2018+ (probe OK) | n/a | **Stitched short-lead series, not the forecast known 72 h out** | Retrospective experiment only, labelled as such | Open-Meteo CC-BY-4.0 (documented) |
| Weather: Open-Meteo Single Runs API | **Earliest archived GFS run found: 2026-04-07** (measured, stepping back week by week) | Live | Yes (actual operational runs) | **Prospective only (2026+).** No strict historical weather backtest is possible from free data | Open-Meteo |
| Schedule `temp`/`wind` | ~65–95% of outdoor games | Post-game | Observed game-time values | **Never a pregame feature** | CC-BY-4.0 |
| Timestamped market snapshots (opening/72 h lines) | None free | n/a | n/a | **Gap.** Paid option: The Odds API historical plan (not subscribed). Fallback: CSV import + our own archiving from 2026-09-24 | Provider-specific |

**The Odds API (checked 2026-09-25):** an `ODDS_API_KEY` exists only in the Claude app's session environment (not in the Windows
user/system environment, not in a project `.env`, so the scheduled task cannot see it). The key is valid (free tier, 500
requests/month, 0 used; checked with the free `/v4/sports` endpoint). It was **never integrated**: no project code reads it.
Every forecast's market spread/total comes from nflverse schedule data (`spread_line`/`total_line`), snapshot-archived by
this project with retrieval timestamps; releases record this as `market.source = nflverse_schedules_archived`. Integrating
the API would be a new data feature and is out of scope while the model is frozen.

## Added 2026-09-25
| Source | Use | Notes |
|---|---|---|
| nflverse weekly rosters (current season) | QB replacement-chain validation (RES/CUT/RET/EXE/DEV/INA) | `INA` is filled in on game day; historically it measures "declared inactive" |
| Open-Meteo Forecast API | Prospective weather snapshots for upcoming games (display only) | Observation time recorded; free, no key |
| Open-Meteo Geocoding API | City-level venue coordinates (`data/manual/venues.csv` → `venue_coordinates.json`) | Matched place names stored for review |
| Open-Meteo Historical Forecast API | Retrospective weather evaluation only | Values from 2019; stitched short-lead forecasts, not strictly as-of |
| FreeTSA (RFC 3161) | Trusted timestamps of release-file hashes | Only the sha256 is sent; certs in `releases/archive/tsa_certs/` |
| Internet Archive (Wayback Machine) | Independent public copy of each pushed release file | Commit-pinned raw GitHub URL; bytes verified against sha256 |

Data-quality notes: nflverse lists some open-air international venues (e.g. Melbourne Cricket Ground, Stade de France,
Munich) with roof "dome"; roof values are used as provided, and retractable roofs with unknown status count as half exposed.

## What cannot currently be obtained from free data

1. **Historical market lines at a fixed pre-kickoff time** (72 h or opening). Only one untimed
   line per game exists. Consequences: (a) market-based models (A and C) are evaluated
   historically only at the final-pregame horizon, using `approx_closing`; (b) early-horizon market
   comparisons will accumulate prospectively from our own snapshots, which began on 2026-09-24.
2. **Historical mid-week injury/practice report versions.** Only the final weekly record survives.
   Early-horizon injury features can only be validated prospectively.
3. **Historical operational weather forecasts** before ~April 2026.
4. **Live pressure/coverage participation data.** It is released after the season, so it is excluded from
   live features. PFR pressure stats and FTN charting are the in-season alternatives.
5. **Coordinator/play-caller history with announcement dates.** This needs a hand-maintained table.
6. **Pinned historical versions of EPA/CPOE.** nflverse republishes with model updates, so the
   backtest is an approximate reconstruction, not a strict prospective replay.

## Practical fallbacks in place

- `data/manual/market_snapshots/*.csv` import route: columns `game_id, source, snapshot_at (UTC ISO-8601),
  home_spread (negative = home favoured), total`. Any price column makes the import fail.
- Every `python -m nflcast ingest` appends a new timestamped raw snapshot of schedules (lines), injuries,
  depth charts and weekly rosters for the current season. This builds a genuine as-of archive from 2026-09-24.
- Missing market line at release time → football-only forecast with a visible `fallback` status.

## Sign convention check (measured)

The correlation of nflverse `spread_line` with the realised home margin is **+0.426** (all completed
games). So `spread_line` = expected home margin, and the project's home spread is `s = -spread_line`.
This is pinned by `tests/test_signs_and_identities.py`.
