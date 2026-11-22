# Big model-vs-market gaps: diagnosis (A1), 2026-11-20

Brief: user, 20 Nov 2026. Plan: `PLAN.md`. Research only: nothing published, frozen or released has changed.

**Method.** No model was fitted and no game result was used. The only "outcomes" counted are player participation (did
a listed player take an offensive or defensive snap) and later injury-report statuses, the same quantities research
B8 measured.

**Scripts and outputs.** All are in `reports/research/gap_absences/`. Run them from the worktree root with
`PYTHONPATH=src`.

| Script | Output | What it does |
|---|---|---|
| `common.py` | – | Releases, locks and injury snapshots. Re-implements the shadow line's live injury input per player, by the same rule. |
| `a1_timing.py` | `a1_timing.json`, `.parquet`, `a1_timing_games.parquet` | Injury data at every 2026 lock against the last data before kickoff. |
| `a1_penalty.py` | `a1_penalty.json`, `a1_penalty_rows.parquet` | B8: participation by status, practice and snap band, 2019-25 final reports. |
| `a1_midweek.py` | `a1_midweek.json` | A10: what practice-only rows at the 2026 locks turned into. |
| `a1_costs.py` | `a1_costs.json` | Frozen per-unit costs; why the four cost estimates differ. |
| `a1_gap.py` | `a1_gap.json`, `a1_gap_teams.parquet`, `a1_ind_hou.json` | How much of each big 2026 gap absences could account for; IND @ HOU. |

**Replay check.** The lock-time inputs can be rebuilt exactly.
- The injury snapshot I take as "in use at the lock" has the content hash the release recorded for 236 of 238
  team-locks. The exceptions are both ATL @ GB week 3 rows, a release generated before injury data was archived.
- Recomputing the stored `injury_inputs` (week 7 on, 232 team-versions) agrees to within 0.00005 (rounding).

## Answers in brief

**1. Why do the injury inputs move lines so little?**

**a) The fitted costs are small.**
- Frozen shadow ridge: 0.45 points per starter-equivalent of expected lost snaps on the offensive line, 0.36 on
  WR/TE/RB, 0.61 in the front seven and 0.90 in the secondary.
- A typical team carries about 0.4 expected starter-equivalents in each unit (sd about 0.4), so the two teams' loads
  largely cancel.
- At the final pre-game version, the injury inputs' net effect on a game's margin averaged 0.57 points (lock-24h games).

**b) Not because of ridge shrinkage or a miscalibrated input.**
- The penalty at alpha 100 shrinks by about 2% (orthogonal case).
- Snaps actually lost rise 0.86-0.97 per unit of the expected input.
- The larger figures quoted elsewhere measure different things (section 4).

**c) Two kinds of absence never enter: reserve lists and departures (B10, B11).**
- In IND @ HOU they were worth 0.85 points towards HOU at the frozen costs, about as much as all the listed injuries.

**When do they point the wrong way?**

**At locks made before the final report reached the data.**
- Thursday games: **0 of 10** team-locks had final statuses.
- Weeks 4-6, locked at first publication: no injury rows at all.
- At those locks every practice-only row is charged a flat 13.5% of the player's snap share (the "no status" rate).
- In 2026, regulars who did **not** practise at the lock played only 66% of the time (15% for Thursday games).
- Regulars with a full or limited practice played 99-100%.
- So the flat rate undercharges the players most likely to miss and overcharges healthy ones. It charged 31.9
  starter-equivalents to full-practice regulars who lost 2.0, and 5.8 to non-practising regulars who lost 14.8.
- IND @ HOU is the clearest case: at the lock HOU looked more depleted (0.68 against 0.54), and at the final report
  IND was (3.21 against 1.98).
- In 3 of 58 lock-24h games the net injury effect changed sign between the lock and the final version.

**Even on final reports, non-designated and Questionable rows are overcharged (B8).**
- Regulars with no game status played 97.0% against an assumed 86.5%: 4.7 times the realised lost snaps.
- Questionable regulars played 72.4% against 60.0%.

**2. How much of a big gap is news the model can't see?**

- **At the frozen costs, little.**
  - Across the 19 big-gap locks of 2026 (stats-only line 3+ points from the line), three things were combined: the
    listed injuries with B8-corrected participation rates, plus reserve-list and departed regulars counted by their
    weight in the team's current rating.
  - Together they moved the line back towards the market by 0.35 points on average, at the final pre-game version.
    The mean gap was 3.76 points, so about 9%.
  - They never reversed a gap and halved one (DAL @ IND, week 9).
- **The answer depends on the costs, which only A2 can estimate.**

  | Cost multiple | Gaps reversed (of 19) | Gaps halved (of 19) | Notes |
  |---|---|---|---|
  | x1 (frozen) | 0 | 1 | |
  | x2 | 1 | 5 | |
  | x3 | 4 | 6 | Scale of the 19 Nov hand estimate. Includes IND @ HOU. |

  On the evidence so far, most of a typical big gap is the stats-only rating disagreeing with the market about the
  teams. It is not absence news the model missed.

**3. What should the site show before a pick locks?** This belongs to Part B and A4. A1's contribution:
- the lock should not be treated as informed by final statuses for Thursday games;
- elsewhere the final statuses were in the data at 92% of lock-24h team-locks;
- B1's note "Measured before final injury reports reached the data" would have applied to 24 of 116 lock-24h
  team-locks, including all 10 Thursday ones.

## 1. Feed timing at every 2026 lock

Source: `a1_timing.json`.
- "Final" is the last archived injury snapshot before kickoff.
- A team-lock "has final designations" when its set of game designations (player, Out/Doubtful/Questionable) at the
  lock equals the final set.

| Lock rule (weeks) | Games | Team-locks | Final designations at lock | Hours lock before kickoff (median) | Designations first in our data, hours before kickoff (median) | Share of final injury input present at lock |
|---|---|---|---|---|---|---|
| final-pregame (3) | 16 | 32 | 32 | 0.2 | 30.4 | 100% |
| original-pick (4-6) | 45 | 90 | 3* | 120.0 | 34.7 | 0% |
| lock-24h (7-11) | 58 | 116 | 92 | 27.8 | 30.2 | 92% |

\* Three teams had no designations in either version. Weeks 4-6 locked at the first publication, Tuesday to Thursday,
before that week's first practice report was in the data.

**Lock-24h by kickoff slot (US Eastern time):**

| Slot | Games | Team-locks | Final designations at lock | Designations first seen, h before kickoff | Input present at lock | Mean change of a team's injury effect, lock to final (max) |
|---|---|---|---|---|---|---|
| Thursday | 5 | 10 | **0** | 8.4 | 33% | 0.80 pts (1.65) |
| Sunday early international | 3 | 6 | 3 | 24.5 | 93% | 0.04 (0.22) |
| Sunday early | 29 | 58 | 50 | 27.8 | 99% | 0.02 (0.54) |
| Sunday late / night | 17 | 34 | 31 | 33.5 | 98% | 0.02 (0.65) |
| Monday | 4 | 8 | 8 | 38.1 | 100% | 0.00 |

**What the timing shows:**

**Feed cadence.**
- The nflverse injury file's Last-Modified times fall mostly at 06:00-07:00 UTC (27 of 46 snapshots that record one),
  with occasional updates 11:00-16:00 UTC.
- Our own observation lag after the provider's update: median 2.0 h, 90th percentile 6.4 h, maximum 10.5 h. The
  longer lags are times the PC was off.
- So a report issued in the US afternoon usually reaches our data the next morning (UTC).

**Thursday games.** All five final reports reached our data on the Thursday:
- 06:01 GMT (NE @ CHI);
- 14:07 (CAR @ GB);
- 15:22 (JAX @ BAL);
- 07:01 (WAS @ NYG);
- 16:30 (IND @ HOU).

Each was 7-18 h before kickoff and long after the Wednesday-evening lock. No 2026 Thursday lock has seen final statuses.

**Sunday and international games.** The 8 Sunday-early and 3 Sunday-late misses are mostly not missing reports.
- In 10 of these 11 the lock already had that team's designations.
- The final file (Sunday 06:00 GMT) added Saturday changes: downgrades, players ruled out and IR moves.
- The injury effect changed by at most 0.65 points.
- Two international games (PIT @ NO week 7, CIN @ ATL week 9) locked before Saturday's 11:57 / Sunday's 07:01 update.

## 2. The no-status penalty (B8) and what the inputs are made of

Source: `a1_penalty.json`, final weekly reports. Inputs are rebuilt exactly by the training rule: as-of P(play) from
the five earlier seasons, and the player's mean snap share over the team's previous six games.

**Participation by final status and recent snap share, 2021-25** (the frozen shadow's rate window):

| Final status | Share < 0.2 | 0.2-0.5 | 0.5-0.8 | 0.8+ | Rate the input assumes |
|---|---|---|---|---|---|
| None (no game status) | 62.9% (n 3,219) | 91.8% (3,692) | 96.4% (4,327) | 97.8% (3,347) | 86.3% |
| Questionable | 42.1% (2,237) | 67.1% (1,802) | 72.9% (1,879) | 71.5% (1,179) | 60.7% |
| Doubtful | 0.0% (267) | 0.0% (141) | 0.5% (202) | 1.5% (130) | 1.0% |
| Out | 0.1% (1,919) | 0.0% (1,432) | 0.1% (1,263) | 0.0% (586) | 0.0% |

**B8 reproduced.** Regulars (share 0.5+) with no status played 97.0% (n 7,674); Questionable regulars 72.4% (n 3,058).

Fringe players lower the pooled rates. Special-teams-only snaps count as "did not play", which is why the under-0.2 band
looks injured.

**Composition, 2019-25** (3,920 team-games):

| Unit | Mean (sd) per team-game | Share of expected lost snaps from no-status / Questionable / Doubtful / Out rows | Share of variance across team-games from the same rows | Realised mean | Slope of realised on expected |
|---|---|---|---|---|---|
| ol | 0.39 (0.42) | 25 / 27 / 7 / 41% | 4 / 19 / 13 / 64% | 0.31 | 0.94 |
| skill | 0.39 (0.37) | 22 / 27 / 8 / 43% | 3 / 18 / 13 / 65% | 0.29 | 0.90 |
| front | 0.41 (0.38) | 27 / 27 / 6 / 40% | 6 / 21 / 12 / 62% | 0.28 | 0.86 |
| db | 0.38 (0.42) | 18 / 27 / 8 / 47% | 3 / 16 / 12 / 69% | 0.33 | 0.97 |

**What the composition means:**
- No-status rows carry 23% of all expected lost snaps but realise only 32% of what they are charged (1,406 against 443
  starter-equivalents).
- For no-status regulars the realised share is 21% (1,114 against 235).
- On **final** reports this is mostly a near-constant offset: no-status rows explain only 3-6% of the variance between
  team-games. Two-thirds of the variance comes from Out rows, which are almost exactly calibrated.
- That is why the frozen coefficients are not badly attenuated (slopes 0.86-0.97). The penalty inflates every team's
  load about equally, so on final reports it mostly cancels between the two teams.

**At mid-week locks the penalty points the wrong way** (`a1_midweek.json`). These are 2026 lock snapshots: 58 games,
777 practice-only rows, all in games whose snap counts are in the data.

| Practice status at lock | Regular (share 0.5+): n / played / later Out or Doubtful | Others: n / played |
|---|---|---|
| Did not practise | 59 / 66.1% / 25.4% | 39 / 46.2% |
| Limited | 52 / 100% / 0% | 44 / 81.8% |
| Full | 307 / 99.0% / 0% | 276 / 75.0% |

Every row is charged 13.5% of the player's share whatever his practice status:
- for full-practice regulars: 31.9 starter-equivalents charged, 2.0 realised;
- for non-practising regulars: 5.8 charged, 14.8 realised.

At Thursday locks, non-practising regulars played 15% (n 20); at Sunday-early locks 100% (n 18). A Wednesday DNP before a
Thursday game is a different signal from a Wednesday DNP before a Sunday game.

A2 note: the historical files hold only final reports, so these mid-week rates (A10) can only come from the 2026
injury versions, a small sample.

## 3. Reserve lists and departures (B10, B11)

These players are in no input:
- players on reserve lists drop off the weekly injury report;
- traded or released players leave it.

Their absence reaches the model only through results, at the team-form weights (11% on the last game, 37% on the last
four). `a1_gap.py` counts each by his **rating share**: the form-weighted snap share over the team's last 48 games,
which is the part of the current rating that still contains him.

In IND @ HOU at the lock:

| Team | Players | Total rating share | At frozen costs |
|---|---|---|---|
| IND | Downs, Nelson, Buckner, Allen (traded); Davis-Gaither, Alie-Cox, Pierce, Carlies, Taylor-Britt, Clemons (reserve lists) | 3.6 starter-equivalents | 1.69 points |
| HOU | Al-Shaair (IR), Noel, Higgins, Speed, Edwards, Horton (reserve lists); Wayne (departed) | 1.6 | 0.84 points |

Net: 0.85 points towards HOU. Across the 19 big-gap locks, these players moved the line back towards the market in 12
and away from it in 7. The mean was 0.11 points towards the market at the final version, and the mean size 0.39
points.

Caveat for A2: Al-Shaair was both on the injury report (no status, did not practise) and on injured reserve in the
lock's roster file. The two sources must be de-duplicated.

## 4. Why the cost estimates differ by about four times

Source: `a1_costs.json`.

| Estimate | Value | What it actually measures |
|---|---|---|
| Shadow ridge (B7) | 0.45 pts per OL starter-equivalent (0.43 for a 95%-snap starter listed Out) | Effect on own points of pre-game expected lost snaps from the final report, after team form and QB inputs, fitted on 2,793 games. Ridge shrink about 2%; input slope 0.94. |
| Team-analytics OL figure | −0.047 EPA per dropback (CI −0.061 to −0.032) x 35-40 dropbacks = 1.6-1.9 EPA | Effect on that game's passing EPA of a top-5 lineman playing **under half of that game's snaps**. Controls for line and pass-rush hit-or-sack rates only, not the offence's overall efficiency. |
| Hand estimate, 19 Nov | 1.25-1.5 pts per starting tackle | An assumed position value: about 3 times the OL unit mean. Not estimated. |
| B11 exploratory | 0.39 pts per starter-equivalent | How far the Model line sat from the **market line** per extra starter-equivalent missing (118 games, corr 0.14). A model-vs-market difference, not a cost. |

The team-analytics "missing starter" is mostly not a pre-game absence. Of its 2,236 missing starters (2021-25, its own
definition):

| Share | n | What it was |
|---|---|---|
| 24% | 547 | Listed Out or Doubtful before kickoff: the only kind the injury input prices with certainty |
| 10% | 221 | Questionable, did not play |
| 22% | 489 | Played some snaps: in-game injuries, benchings, rotation |
| 26% | 585 | On a reserve list: long-term absences, partly already in team form |
| 11% | 244 | Active but took no line snaps: lost the job |
| 7% | about 150 | Other: listed with no status, inactive or gone |

**Why the analytics figure is higher.** Three of these categories select on how the game or season was going:
- in-game exits and benchings happen in games that are going badly;
- long injury lists build up on declining teams;
- losing the job follows poor play.

The regression does not hold the offence's efficiency constant. So the analytics figure combines:
- the cost of an absence;
- in-game breakdowns;
- poor play.

It also counts passing plays only, and in EPA rather than points. It is a fair description of "games where the line was
short-handed". It is not the cost of a lineman known to be out before kickoff, and is not a fitting target (brief, A1).

**Cross-check.** The audit's walk-forward residual of the Model line without injury inputs found −0.37 points for own
offence and +0.65 for the opposing defence per absent full-time starter (`docs/audit-2026-11.md`, section 4). That is the
same range as the shadow costs, from a different method.

**What remains genuinely uncertain:**
1. **Position differences inside a unit.** Flat costs treat a left tackle like a guard and a cornerback like a safety.
   The hand estimate assumes they differ by about 3 times. Only a pre-registered split (B9) can test that.
2. **Whether the coefficients are pulled down by the final reports' own mixing of designations.** A Questionable regular
   is charged 40% and realises 28%.

Neither is likely to close a gap of four times. On the evidence so far, the 0.45 is the right order for a pre-game
OL absence.

## 5. IND @ HOU, week 11

Source: `a1_ind_hou.json`. Research only, never a forecast.

**Lock** (`rel_20261118T195302Z`): injury file observed 18 Nov 18:10 UTC, provider Last-Modified 16:38 GMT.
- Both teams' rows were practice rows with **no game status**, each charged 13.5% of the player's recent share.
- HOU (0.68): DNP Lassiter, Marks, Al-Shaair, Hunter, plus full-practice Rutledge, Blankenship, Dell, Nwaiwu and
  Fisher, who supplied 0.24 of the 0.68.
- IND (0.54): DNP Ward, Raimann, Travis, Gardner, Tillery, Mallory, Carlies.

| Team | OL | Skill | Front | DB | Margin effect |
|---|---|---|---|---|---|
| HOU | 0.16 | 0.16 | 0.17 | 0.19 | −0.40 pts |
| IND | 0.23 | 0.04 | 0.06 | 0.21 | −0.34 pts |

The net effect was 0.06 points towards IND. The shadow line's 0.18 includes small differences in its other
coefficients against v1.0.

**Final pre-game** (`rel_20261119T234714Z`): file observed 19 Nov 18:27, Last-Modified 16:30 GMT.

| Team | Out | Questionable | OL | Skill | Front | DB | Margin effect |
|---|---|---|---|---|---|---|---|
| IND | Ward (0.89 lost), Raimann (0.83), Travis (0.72), Tillery (0.24), Mallory (0.17) | Gardner (0.27 lost of a 0.66 share), Gould | 1.58 | 0.21 | 0.26 | 1.16 | −1.99 pts (OL −0.71, DB −1.04) |
| HOU | Marks (0.68), Hunter (0.61), Harrison Jr. (0.14), Jordan (0.07) | Teller, J. Smith, Hummel (near-zero shares) | 0.16 | 0.94 | 0.69 | 0.19 | −1.00 pts |

Net: 0.99 points towards HOU. In the frozen shadow line this appeared as 8.57 against 7.71.

**Taken together at the final version, all at frozen costs:**

| Source | Points towards HOU |
|---|---|
| Listed injuries | 0.99 (B8-corrected rates: 1.10) |
| Reserve lists and departures | 0.85 |
| Total | 1.95 |

That is 41% of the 4.79-point gap. At three times the frozen costs it would exceed the gap.

The pick locked about 24 h before final statuses reached the data. Of IND's four non-practising starters at the lock,
three (Ward, Raimann, Travis) were later ruled Out and the fourth (Gardner) Questionable.

## 6. All 19 big-gap locks

Source: `a1_gap.json`. Gap = stats-only line minus market line, home view, at the lock. Effects are signed towards the
gap: negative means back towards the market. All at frozen costs.

| Game | Slot | Gap | Injuries lock → final | Injuries, B8 rates, lock → final | Reserve lists and departures, lock → final |
|---|---|---|---|---|---|
| 2026_03_KC_MIA | Sun early | +4.66 | +0.43 → +0.43 | +0.37 → +0.37 | −0.20 → −0.20 |
| 2026_03_LAC_BUF | Sun early | +3.22 | +0.43 → +0.43 | +0.23 → +0.23 | +0.37 → +0.37 |
| 2026_04_GB_TB | Sun early | +3.89 | 0.00 → −0.49 | 0.00 → −0.39 | +0.27 → +0.68 |
| 2026_04_JAX_CIN | Sun early | −3.58 | 0.00 → +0.20 | 0.00 → +0.12 | +0.05 → +0.44 |
| 2026_04_MIA_MIN | Sun late | −3.38 | 0.00 → +0.06 | 0.00 → +0.05 | 0.00 → −0.10 |
| 2026_04_NYJ_CHI | Sun early | +3.52 | 0.00 → −0.14 | 0.00 → +0.01 | +0.04 → −0.09 |
| 2026_05_CHI_GB | Sun early | +3.57 | 0.00 → −0.29 | 0.00 → −0.38 | −0.41 → −1.08 |
| 2026_05_TB_DAL | Thursday | −3.08 | 0.00 → −1.29 | 0.00 → −1.27 | +0.56 → +0.56 |
| 2026_06_ARI_LA | Sun late | −3.30 | 0.00 → −0.46 | 0.00 → −0.67 | −0.90 → −0.47 |
| 2026_06_CHI_ATL | Sun early | +4.56 | 0.00 → +0.24 | 0.00 → +0.29 | −0.72 → −0.07 |
| 2026_06_NO_NYG | Sun early | +3.94 | 0.00 → −0.91 | 0.00 → −0.75 | −0.30 → −0.30 |
| 2026_06_PIT_TB | Sun early | +4.52 | 0.00 → −0.35 | 0.00 → −0.52 | +0.37 → +0.48 |
| 2026_07_MIA_NYJ | Sun early | −3.06 | +0.06 → +0.06 | +0.05 → +0.05 | +0.01 → +0.06 |
| 2026_08_BAL_BUF | Sun early | +3.78 | +0.73 → +0.73 | +0.57 → +0.57 | −0.04 → −0.04 |
| 2026_09_CIN_ATL | Sun intl | −4.28 | −0.17 → −0.17 | +0.08 → +0.08 | −0.28 → −0.28 |
| 2026_09_CLE_NO | Sun early | +3.56 | +0.32 → +0.32 | +0.12 → +0.12 | −0.30 → −0.30 |
| 2026_09_DAL_IND | Sun early | +3.69 | −0.88 → −1.35 | −0.83 → −1.38 | −0.92 → −0.92 |
| 2026_09_NYJ_KC | Sun early | −3.12 | +0.10 → +0.02 | +0.11 → +0.01 | +0.07 → +0.07 |
| 2026_11_IND_HOU | Thursday | −4.79 | +0.06 → −0.99 | +0.05 → −1.10 | −0.85 → −0.85 |

**Notes on the table:**
- **Weeks 4-6 show 0.00 at the lock** because those locks had no injury rows.
- **Thursday games show the largest lock-to-final moves** (TB @ DAL −1.29, IND @ HOU −1.05).
- **Week 3 locks were the final versions.**
- **Size.** The B8-corrected rates change little on final reports (mean absolute 0.44 against 0.47 points).
- **Direction at the lock is not like for like.** For Thursday locks, applying final-report rates to practice-only
  rows is not like for like (section 2). A practice-aware rate is needed.

## 7. What this means for A2 (to be written into the pre-registration)

**1. Lock-time inputs need their own participation rates.**
- Final-report rates by status x practice x band (B8) fix the final version.
- Mid-week rows need rates by practice status and days to kickoff (A10). These can only be estimated on the 2026
  injury versions, which is small and seen data, so any such rates are exploratory this season.
- The historical backtest can only test the final-report version (labelled retrospective and optimistic).

**2. Add reserve-list and departed regulars by rating share, de-duplicated against the injury report.**
- About 0.39 points of absolute effect per big-gap game at frozen costs, comparable with the listed injuries.

**3. Rating-weight scaling (B11) is what makes item 2 coherent.**
- The rating share already discounts games a player missed. The same quantity should replace the 6-game mean share
  for injured players, so long absences are not counted twice.

**4. Costs: no reason to expect four times the frozen values.**
- The size of a real improvement is likely limited, because most of a big gap is not absences.
- A2 should report that honestly. The pass rule should not be loosened to find one.

## 8. Limitations

**About the 2026 sample:**
- Small: 58 lock-24h games, 5 of them on Thursday, 19 big-gap locks.
- The timing table covers games that kicked off before 20 Nov 18:13 UTC.
- 2026 games are seen data.

**About the data:**
- Historical injury data are final weekly reports only, so mid-week behaviour exists for 2026 alone.
- "Played" counts offensive or defensive snaps, so special-teams-only players count as not playing.
- The weekly roster files' publication times are not recorded. Reserve lists and departures use the latest file
  observed by the lock, which may lag transactions.

**About the method:**
- Absence effects in sections 5-6 are priced at the frozen shadow costs. They illustrate scale and are not estimates
  of what those absences were worth.
- No official NFL report times were collected (NFL.com terms; `docs/data_sources.md`). "Reached our data" combines the
  nflverse lag and our own polling lag.
