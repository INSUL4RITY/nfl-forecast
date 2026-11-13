# 2027 research list

Every idea raised during the 2026 season for the 2027 model, in one place. Nothing here changes the 2026 model, which is
frozen (`configs/model_freeze.yaml`). Each item becomes a test only after the season: pre-register the test and its pass
rule first, evaluate chronologically on games the candidate never saw, and pair comparisons on identical games. The 2026
season (with our own timestamped lines) is the new untouched test; the 2025 locked season is no longer untouched.

Status key: **open** = not tested yet · **trial** = running live in 2026, judge after the season · **tested** = already
tested, result noted · **parked** = needs a user decision or data we do not have.

## A. Season-end reviews (run these first)

| # | Item | Status | Notes |
|---|---|---|---|
| A1 | Score the full season (`score`), all publicly verifiable pregame forecasts vs market-only and football-only | open | After the Super Bowl (Feb 2027). |
| A2 | Judge the Model v2 trial (v2.2) vs the Model line (v1.0) on weeks 8-18 + playoffs | trial | Margin error is the main measure (steadier than records). ~150 games: a record gap under ~8 games is noise. v2.1's record is kept under `replaces`. Leading 2027 candidate. |
| A3 | Judge the injury trial line ("model + injuries", `football_only_inj`) | trial | Pre-season evidence 12.717 -> 12.686 RMSE, CI spans zero. No longer shown on the site; still archived. |
| A4 | Stats-only line vs the lines we actually lock against (Big 3+ / Biggest 4+ gaps) | open | Research plan item 1. Long-run backtest: stats-only side ~46-51% on closing lines, so a good 2026 run is not proof on its own. |
| A5 | Hybrid that may weight the stats more than the market, if A4 holds | open | The v1.0 combined ridge chose maximum shrinkage (alpha 1e5, i.e. ~market). |
| A6 | Decide the official pick basis for 2027 (stats-only vs market-adjusted) from A4/A5 | open | Decide with a rule written down in advance, not from the record alone. |
| A7 | Lock timing: Tuesday publication vs lock-24h vs final pregame | open | Use the timestamped lines and the line-movement tracker (`performance.json` `line_movement`). So far the line has tended to move toward the model on 3+ gaps after the lock. |
| A8 | The Odds API consensus lines vs nflverse lines: does the source change accuracy? | open | Identical games only (limitation 1 in PROGRESS.md). |
| A9 | Weather on strictly as-of data (forecast snapshots collected since 2026) | open | Pre-season evaluation was retrospective and did not pass. |
| A10 | Mid-week injury practice readings: calibrate with the injury versions collected in 2026 | open | Limitation 2. |
| A12 | Refit on one consistent EPA version across all seasons | open | nflfastR PR 618 (open on 2026-11-10) revalues scoring plays net of the next kickoff: touchdown ~5.9 not 7, EPA compressed toward 0, kickoff EPA ~-0.07 instead of ~+0.2. Re-download every season under the same version before 2027 fitting. |
| A11 | Re-check the exploratory new-QB carry-over hint (NQ lowered early-season total error) | open | Not pre-specified; exploratory only. |
| A14 | Stricter pass rules for the 2027 model (v2) | open | Audit 2026-11-13. The v2 tests passed on point estimates: v2.2 "passed" at -0.18 SE difference with a 95% interval of -0.77 to +0.37, and v2.1 was picked from drop-one results on the same folds it was then judged on. For 2027, pre-register a rule that needs the interval below zero, or judge the v2 trial only on its clean 2026 games (weeks 8-18, A2). |
| A13 | Put intervals on every spread backtest result | open | Audit 2026-11-13. Backtest records vs the line use untimed (~closing) lines and the actual starter, and are reported with no interval. At ~1,900 games the 95% interval on a win rate is about +/-2.2 points (1.96 x sqrt(0.25/1900)), so 51.4% vs 49.9% is not a difference. Add intervals (and paired differences on identical games) to the reports; a real test of picks vs the line needs timestamped historical lines, i.e. the paid backfill (D5). |

## B. Model inputs to test

### Quarterbacks
| # | Item | Status | Notes |
|---|---|---|---|
| B1 | QB-aware team form: separate a team's games by quarterback | open | ATL@GB 2026 wk 3: weeks 1-2 without Penix dragged ATL's form. |
| B2 | "Returning starter" vs "backup coming in" in the QB-change input | open | Same game: QB change added ~+1.2 pts to GB although the starter was returning. |
| B3 | Rate the starter's quality, not only whether he plays; episode-level QB start-rate estimator | open | Limitation 4 (clustering by injury episode). Backend review 2026-11-10: the QB rating is EPA per dropback only (scrambles in, designed QB runs out) and is not adjusted for the defences faced, so a running QB's absence is under-counted; test adding designed runs and an opponent adjustment. Measured weights in the Model line: 7.3 pts per 1.0 EPA/dropback of rating + 20.9 per 1.0 of rating-vs-team-baseline + -1.15 for any change of starter; starter-to-backup swaps in 2026 releases moved the line 4.3 pts on average, 8.3 at most (Allen, Prescott, Maye). |
| B4 | CPOE (and aDOT) as QB inputs | open | Fits with B3. |
| B5 | QB mismatch (user idea): QB rating x experience vs supporting cast | open | An elite experienced QB with weak weapons vs a rookie with strong weapons should favour the elite QB; test a rating x experience term and QB vs receiving-group interactions. |
| B6 | Interception-worthy throws instead of actual interceptions | open | FTN charting, 2022+ only. Example: Penix 4 INTs in the ATL@TB rain game (wk 8) after 1 INT in about 143 throws; FTN charted all 4 as interception-worthy and 15 of 24 passes as uncatchable (40 of 143 before), so charting alone cannot separate a wet ball from bad decisions. Pair with B17. |
| B27 | Split the newcomer QB default by draft pedigree and role; treat emergency starters separately | open | User idea (2026-11-05, Fagnano, BAL wk 9). The default for QBs under 200 career dropbacks pools first-round rookies with third-stringers, and depth rank and preseason snaps are not used. Exploratory check on 2019-2025 final-horizon predictions (not pre-registered): round 5+/undrafted under 200 dropbacks, actual margin 1.7 worse than the model (n=153, SE 1.1); round 1-2 0.3 better (n=160, SE 1.0). Under 50 dropbacks and round 5+/undrafted: 2.0 worse (n=60, SE 1.7). Same group as 7+ underdogs: model 2.8 kinder than the market, yet 1.0 better than the market line (n=50). Error spread about the same as for established QBs (SD ~13.3 vs ~13.0), so intervals need no widening. Also test emergency-relief snaps being down-weighted. |
| B29 | Start rate for a new QB1 who was not with the team last game (trade or signing) | open | Backend review 2026-11-10. Before the injury report is out, a depth-chart QB1 with no dropbacks in the team's previous game gets the "did not finish the previous game" rate (59%, 52/88), which mixes injured starters with new arrivals. BAL week 10: Brissett (traded from ARI) 59%, Fagnano 32%, Slovis 9% on Tuesday; it corrects itself once the report is published. Test a separate category, or use the roster transaction date. |

### Injuries and roster changes
| # | Item | Status | Notes |
|---|---|---|---|
| B7 | Player-value injuries: weight a missing player by production, not snaps (targets/EPA for receivers, pressure/sacks allowed for OL, coverage for DBs), compared with his replacement | open | Main 2027 injury job. A WR1 currently counts the same per snap as a backup. Measured 2026-11-10 (trial lines): one full-time starter out is worth 0.45 pts (OL), 0.36 (WR/TE/RB), 0.61 (front seven), 0.90 (secondary), the same for every player in the unit; the injury input moved the 2026 line 0.46 pts on average, 1.6 at most. |
| B8 | Drop the ~13% lost-snap penalty for listed players with no game status; estimate P(miss) by snap-share band | open | Long practice lists make a team look more hurt than it is. Measured 2026-11-10 (2021-25): regular starters (recent snap share 0.5+) listed with no game status played 97.1% of the time (the input assumes 86.5%) and Questionable starters 72.3% (assumes 60.0%). The pooled rates are pulled down by fringe players (share under 0.2: 64.6% / 43.2%), partly because special-teams-only snaps count as not played. 22.5% of all expected lost snaps come from no-status rows. |
| B9 | "Several starters out in one unit" cluster feature; non-QB injuries by depth role | open | Research plan item 5. |
| B10 | IR players: they drop off the weekly injury report, so the injury input misses them | open | Week 10 of 2026: the average team had 0.78 starter-equivalents of this season's snaps on reserve lists (WAS 2.05, BAL and LA 1.84). |
| B11 | Roster-change share by unit: snaps lost to departures minus snaps added by arrivals | open | Trades/cuts (e.g. Colts trades, Simmons to CHI) only reach the model through results. `predict/roster_moves.py` already finds the moves (display only). Measured 2026-11-10: mid-season team form puts about 11% of its weight on the last game and 37% on the last four, so a non-QB trade is half absorbed only after about 8 games. Exploratory, weeks 3-10 (118 games, not pre-registered): the Model line sits 0.39 pts further toward a team than the market per extra starter-equivalent it is missing (corr 0.14); picks on the more depleted side went 17-12, so no cost shown yet. Week 10 examples: ARI (Harrison Jr. traded, Paris Johnson on IR; Big gap toward ARI), IND (Nelson, Buckner traded). |
| B12 | Injury recovery times from historical injury reports (games missed by injury type) | open | |

### Special teams, luck, situations
| # | Item | Status | Notes |
|---|---|---|---|
| B13 | Kicker rating: FG accuracy vs expected by distance, follows the kicker between teams | open | e.g. Rams kicker change (Mevis -> McManus). |
| B14 | Split special teams into skill (kicking, punting distance) and randomness (blocks, return TDs, muffs) | open | v2's special-teams group helped (+0.39) but is noisy early in the season. |
| B15 | Luck-adjusted EPA: replace actual turnovers with expected ones (league INT rate for the dropbacks, half of fumbles lost) | open | Audit 2026-11-13: in the v1.0 Model line the fumbles-lost rate has the wrong sign (+106 pts per unit of own fumbles lost per play, i.e. more fumbles lost = more points), and the defence's interception rate (-61 per unit for the opponent's), starting field position and points per drive all carry turnover luck. Replace them with expected turnovers (and B16's regression terms) rather than adding more turnover inputs. |
| B16 | Regression features: turnover margin, fumble recovery, one-score record, red zone, 3rd/4th down, without double counting | open | Research plan item 3. v2's luck group helped slightly (+0.18). |
| B17 | Discount extreme-weather games when building team ratings | open | ATL@TB wk 8: TB dropped back 5 times all game; compare both teams in the same game. |

### Context
| # | Item | Status | Notes |
|---|---|---|---|
| B18 | Team-specific home advantage | open | All teams get the same home field now; e.g. LAC's weak home crowd. Hard to estimate reliably. |
| B19 | Carry-over by offseason change: new head coach, new QB, returning production, play-caller changes | tested / open | Coach and QB carry-over failed the pre-season test (no variant passed). Returning production and play-callers untested. Play-caller source found 2026-11-11: Sam Hoppen's all_playcallers.csv (github.com/samhoppen/NFL_public, with Arif Hasan; offensive/defensive play caller and head coach per team-game, 1999-2026, matches all our 2016+ finished games; no licence stated, so kept in data/raw/playcallers/ and the private backup only). It has no announcement dates and already fills future weeks, so a test must use only callers seen in finished games. Same repo: nfl_executives_yearly.csv (GMs/owners by year; low priority). Game pages show play callers from 2026-11-11 (display only). |
| B20 | Divisional underdogs | tested | 2019-2025: 53.4% (687) vs 51.2% (1,273), within chance. Low priority. |
| B21 | Head-to-head and QB-vs-defence history | open | Low priority. |
| B30 | Simplify the rest inputs (rest difference, off-bye flag, short-week flag) | open | Backend review 2026-11-10. In the Model line they largely cancel: 7 extra rest days are worth +0.98 pts through rest difference, and the two off-bye flags take back 0.93, so a bye is worth about 0.05 pts; the short-week flags have the opposite sign to what football sense suggests (+0.78 own points). Likely noise from three overlapping inputs; test one rest term. |
| B28 | "Deserved margin" ratings: rate teams on what their plays usually produce (success rate + yards per play, takeaways folded in) instead of the scoreboard; the gap is luck | open | User link (2026-11-10): github.com/dgrifka/nfl_simulator (MIT, Python, nflverse data, weights fit 2016-2023). Overlaps B15/B16; test as a replacement for actual margins in team form. It leaves out special teams, field position and penalties. |
| B26 | 4th-down decision quality instead of go rate | open | Low priority. Reference model: nfl4th (nflverse, R; go/punt/FG model behind The Athletic's calculator; user link 2026-11-10). v2's go-rate proxy did almost nothing (-0.03 in the drop-one test). The team analytics already computes fd_agree_rate and fd_ep_lost_per. Idea from a 2017-era Cal Poly student paper (2002-12 data); its "coaches are too conservative" finding predates the rise in go rates. |
| B22 | Pressure / coverage / OL vs pass-rush matchups | parked | FTN charting only from 2022; PFF is paid; participation data arrives only after the postseason. |

### Already tested in the v2 work (do not repeat without a new design)
| # | Item | Result |
|---|---|---|
| B23 | Travel / body clock | Hurt in v2.0 (-0.57); dropped from v2.1. |
| B24 | Garbage-time filter (rbsdm-style) | Hurt in v2.0 (-0.80); dropped. |
| B25 | Fatigue: last game's plays, overtime, short-week load, time of possession | In v2.2. Short-week load +0.19 pts per extra play; last-game plays and opponent OT look like noise. Team analytics: ten extra defensive plays changed EPA allowed by +0.0005/play. Do not expand. |

## C. How picks and chances are presented

| # | Item | Status | Notes |
|---|---|---|---|
| C1 | "No edge" threshold, learned from the 2019-2025 backtests | open | At week 8, 39 of 74 picks came from a model line within 1.5 pts of the market line (near 50% by construction). |
| C2 | Cap or extra shrink when the model is 4+ pts from the line, especially after a QB change | open | Biggest gaps were 0-3 at the time. |
| C3 | Calibrated chances: shrink toward 50% (q = 0.5 + k(p - 0.5)) | open | Walk-forward fit k ~0.15 (v1) / ~0.2 (v2); raw chances overstated by ~7 pts on average, 15-25 pts at the biggest gaps (`.scratch/calib.py`, not committed). |
| C4 | Key-number-aware probabilities | open | Key-number weights are in `configs/key_numbers.yaml` (display only so far). |
| C5 | Gap-vs-result check: regress (result - line) on (model - line) | open | Shows whether bigger gaps really mean more. |
| C6 | Stats-only totals | open | Not usable as is (well under 50% in 2026). Fix or drop. |
| C7 | Weight the model by spread size; anchor chances on the market | open | User question (2026-11-05). Exploratory, 2019-2025 final horizon, untimed ~closing lines. Spreads 7+ (572 games) RMSE: market 12.79, v1 13.35, v2.2 13.42, 50/50 blend 12.98; squared-error gap vs market v1 14.7 (SE 3.5), v2.2 16.5 (SE 3.9). Best weight on the model in q = market + k(model - market): about 0 at 7+ (full-sample k -0.09 v1, -0.12 v2.2; never positive walk-forward after 2021), about 0.01-0.07 overall, so a 50/50 blend is far too generous. Possible edge only on small spreads with big gaps: v2.2 under 7 with gap 3+ went 163-125 (56.6%, selected after the fact). Re-test on our timestamped 2026 lines (A7). At 7+ the slope of (result - line) on (model - line) is about zero: v1 -0.21 (SE 0.23), v2.2 -0.05 (SE 0.21). Favourites of 7+ against an underdog QB under 200 dropbacks, round 3+/undrafted: won 87.1%, beat the line 38-43-4, average margin 11.4 vs line 11.3 (85 games). |

## D. Not model work

| # | Item | Status | Notes |
|---|---|---|---|
| D1 | Move operation to a cloud runner (remove the PC dependency) | parked | Needs a user decision and setup. |
| D2 | Player props: do the team analytics' position-level matchup flags beat the prop line? | parked | User idea (2026-11-03). First test the flags against actual results (free). Props need prices, which the market-data policy forbids, so this needs a user decision and a private folder outside `nflcast`. The Odds API history starts 2023-05-03 at 10 credits per region, market and event: ~33,000 credits for 3 seasons x 4 markets x 1 snapshot. |
| D5 | One-month The Odds API backfill of timed spreads and totals, 2020-2025 | parked | ~40,000 credits for 3 points per game, US region (~80,000 with EU for Pinnacle). Needed for A4, A7 and C1 on timed lines. The 100K plan ($59, price seen 2026-11-03) covers this plus D2 on US books. User decision; buy in February. |
| D3 | Team analytics report fixes (arrivals, Friday refresh, edge screen on shrunk values, small samples) | open | Analytics branch only; see the week 9 review hand-off. |
| D4 | CV update with the full-season result and the v2 trial outcome | open | After the Super Bowl. |

Sources: PROGRESS.md (sections 6-8 and session notes), the pre-registrations in `reports/research/`, and the 2026
discussions with the user (week 3 to week 9). Add new ideas here, not only in chat.
