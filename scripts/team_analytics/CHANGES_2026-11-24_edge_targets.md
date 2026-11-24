# Changes for the week 12 build (24 Nov 2026), after CIN at WAS

Recommendations reviewed (from another chat, passed on by the user). Each one was tested where it makes a claim; what failed is
not shown on the page.

| # | Recommendation | Done | Result |
|---|---|---|---|
| 6 | Group edges by what they predict | Yes: `backtest_edge_targets.py`, `edge_targets.json`; each game's sheet is grouped | The overall efficiency gap goes with the margin (about 4.3 points per 1.0, correlation 0.38, 959 games). Beyond it: passing and pass-rush edges predicted only that unit's result; big passing plays a little of that offence's score (95% +0.1 to +2.0 points per 1.0); the run game a little of the margin (+0.1 to +2.6, but no better on held-out seasons); no edge predicted the total. The pasted table assumed "both pass offences against both pass defences" predict the total: not supported. |
| 7 | Stability tier and sample size on every edge | Yes | The edge score already includes shrinkage calibrated per measure (`matchup_calibration.json`, not refitted). Each headline edge now shows its stability (the same scale as the matchup tables: share of each team's record kept) and n for offence and defence; every expected value in the tables shows n. |
| 8a | One-dimensional favourite flag (5+ point favourite, bottom-5 run game) | Tested, not shown | Those 25 favourites beat the expected margin by +3.0 points against +0.7 for the other 333 (difference 95% -2.6 to +6.9). Stated in Method. |
| 8b | Line moves 2.5+ off the lookahead after a primetime result | Not added | This page uses no market data by design (spread and total columns are dropped on load), and no lookahead lines exist in the data. |
| 8c | Weather from two sources | Yes | NWS and Open-Meteo both read for US venues; the label uses the wetter and windier one, the line shows both and says when they disagree on rain. Note: the week 11 Monday forecast was read on Sunday 22 Nov; the scheduled refresh (Thu/Fri) does not re-read Monday games. |
| 9 | Four-man pressure, interior vs edge | Yes, as context | New matchup row: hit-or-sack rate with 4 or fewer rushers (FTN). The line caution now says where the missing linemen play (guard/centre or tackle) and what share of the defence's PFR pressures come from interior linemen and edge rushers. Not tested, labelled so. ESPN win rates stay as they were. |

Also: rest days. A player who missed or was limited in practice with "Not injury related - resting player" is shown as a
rest day (not injured) and never counted as a practice concern (week 11: Stefon Diggs, Dexter Lawrence, Jonathan Allen and
others). "Personal matter" is not a rest day: it stays a practice concern. `data_check.py` checks the week's data, the injury
report and the reserve list before a build.
