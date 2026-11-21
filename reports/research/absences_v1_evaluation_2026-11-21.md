# Better absence inputs ("absences v1"): evaluation, 2026-11-21

**Pre-registration.** `absences_v1_preregistration_2026-11-21.md`. Its RFC 3161 timestamp (FreeTSA) is 21 Nov 2026
00:08:53 GMT, verified, in `.md.tsa.jsonl`. It was made before anything was built.

**Run and code.** Run `20261121T001329Z`, files `absences_v1_evaluation_20261121T001329Z.json` and
`_predictions.parquet`. Code: `gap_absences/a2_build.py`, `a2_eval.py`, `a2_leak.py`. Every result below comes from
these files.

**Scope.** Research for 2027. Nothing published, frozen or released has changed.

## Verdict: AV1 FAILS the pre-registered rule

Identical games, 2019-2024 folds (1,675 games, market line available):

| Pass check | AV1 | Needed |
|---|---|---|
| Paired SE difference vs v1.0 | +0.17 [−0.87, +1.27] | CI below 0 |
| Paired SE difference vs inj-cur (current injury inputs) | **+0.55** [−0.45, +1.57] | CI below 0 |
| Seasons better than inj-cur | 1 of 6 | ≥ 4 |
| Dev folds 2022-24 vs inj-cur | 162.34 vs 160.94 (worse) | not worse |

AV1 (rating-weight scaling, play rates by status x practice x band, reserve lists, departures and arrivals) is **no
better than the inputs it would replace**. On the point estimate it is slightly worse.

## Every arm (2019-24, same 1,675 games; margin MSE; difference = arm − comparison, 95% season-week bootstrap CI)

| Arm | MSE | vs v1.0 | vs inj-cur | Seasons better than inj-cur | Margin MAE |
|---|---|---|---|---|---|
| v1.0 (`core_qb`, the Model line) | 169.77 | – | +0.38 [−0.39, +1.18] | – | 10.074 |
| inj-cur (`core_qb_inj`, ≈ the shadow line) | 169.39 | −0.38 [−1.18, +0.39] | – | – | 10.069 |
| **AV1 (primary)** | 169.94 | +0.17 [−0.87, +1.27] | +0.55 [−0.45, +1.57] | 1/6 | 10.101 |
| AV1-inj (rating-weight scaling, injury report only) | 169.51 | −0.26 [−1.01, +0.46] | +0.12 [−0.63, +0.84] | 2/6 | 10.082 |
| **AV1-b8** (current formulation, B8 play rates only) | **169.05** | −0.72 [−1.58, +0.13] | **−0.34 [−0.60, −0.09]** | **4/6** | 10.057 |
| AV1-split (AV1 + EDGE and CB subsets, B9) | 169.90 | +0.13 [−1.04, +1.37] | +0.51 [−0.54, +1.60] | 2/6 | 10.108 |
| v2.2 trial (existing predictions) | 169.78 | +0.01 [−1.21, +1.37] | – | – | 10.093 |
| shrink-to-line (line + k x (v1.0 − line), k 0.07-0.11) | **163.75** | **−6.02 [−8.91, −3.10]** | – | – | 9.848 |

**AV1-b8 is exploratory, not adopted.** It is the one arm that beats the current inputs with a CI below zero, in 4 of
6 seasons, and is not worse on the dev folds (160.57 against 160.94). It would still have failed the full rule: its
difference against v1.0 has a CI that crosses zero. By the pre-registration ("if AV1 fails, no other arm is promoted"),
it is listed as **exploratory**: the strongest lead for 2027.

**What it implies.** Correcting the participation rates by status x practice x snap band:
- is worth about 0.34 squared points per game against the current injury inputs;
- makes the injury inputs worth about 0.7 against no injury inputs at all, not significant.

### Seen seasons (reported separately, not part of the verdict)

| Season | v1.0 | inj-cur | AV1 | AV1-inj | AV1-b8 | AV1-split | v2.2 | shrink |
|---|---|---|---|---|---|---|---|---|
| 2025 (285 games), MSE | 161.67 | 161.22 | **158.77** | 159.87 | 160.62 | 158.86 | 159.10 | 150.34 |
| 2026 weeks 1-11 (151 games), MSE | 149.49 | 150.87 | 152.46 | 152.26 | 150.99 | 152.68 | – | 146.03 |

- AV1 against inj-cur: 2025 −2.45 [−4.29, −0.62]; 2026 +1.58 [−0.80, +3.89].
- The two seen seasons point in opposite directions. Neither changes the verdict.
- 2026 uses final-report inputs (retrospective), not the inputs available at the locks.

## Fitted costs (points per starter-equivalent, last training fold, 2024 test)

| Arm | Own OL | Own skill | Opponent front | Opponent DB |
|---|---|---|---|---|
| inj-cur | −0.31 | −0.46 | +0.25 | +0.64 |
| AV1 | −0.28 | −0.41 | +0.68 | +0.29 |
| AV1-b8 | −0.36 | −0.64 | +0.33 | +0.70 |
| AV1-split | −0.29 | −0.42 | +0.67 | DB +0.07, CB subset +0.50, EDGE subset −0.02 |

Better inputs do **not** raise the costs towards the 1.25-1.9 point figures discussed on 19 Nov. With rates corrected
and long absences included, a full-time starter out is still worth roughly 0.3-0.7 points. This is consistent with A1
(section 4).

## Secondary analyses (descriptive)

**Gap-vs-result slope (C5).** Slope of (result − line) on (model − line), untimed ~closing lines, 2019-2025, 1,960
games:

| Arm | All | Spread < 7 | Spread ≥ 7 |
|---|---|---|---|
| v1.0 | 0.01 (SE 0.11) | 0.20 (0.14) | **−0.22 (0.17)** |
| inj-cur | 0.04 | 0.20 | −0.16 |
| AV1 | 0.04 | 0.22 | −0.21 |
| AV1-b8 | 0.06 | 0.22 | −0.14 |
| v2.2 | 0.10 | 0.31 | −0.11 |

None of the absence inputs makes big-spread gaps informative. At spreads of 7+ the slope stays at or below zero for
every arm, so a bigger model-vs-line gap in a lopsided game says nothing about the result. This is the C7 finding,
unchanged.

**2026 lock lines** (119 locked games, weeks 3-11). v1.0 slope 0.98 (SE 0.52), AV1 0.59 (0.52), AV1-b8 0.86 (0.51).
That is too few games to separate them, and they are not pooled with history.

**Gap bins** (share finishing on the model's side of the line, Wilson 95%; full tables in the JSON):

| Arm | Gap 3-4 | Gap 4+ |
|---|---|---|
| v1.0 | 57.5% [51.1, 63.7], n 233 | 50.7% [44.2, 57.1], n 225 |
| AV1 | 49.2% (n 258) | 53.4% (n 223) |
| AV1-b8 | 56.3% (n 231) | 52.5% (n 219) |

Every 4+ interval includes 50%.

**Question 2.** In the 401 games of 2019-24 with a v1.0 gap of 3+ points (mean 4.42):
- AV1 moved the line back towards the market by 0.16 points on average;
- the current injury inputs moved it back by 0.10;
- AV1 reversed the side in 0.5% of them.

Absences, measured this way, explain very little of a big gap. This matches A1's 9% at frozen costs.

## Leakage test (`gap_absences/a2_leak.json`)

40 seeded target team-games, 2019-2026, rebuilt after corrupting everything dated at or after kickoff: later snap
counts (randomised, dropped, fake rows), later injury reports, roster files of the target week and later, later games.

- **39 non-week-1 targets:** identical, maximum difference 1.8e-15 (float summation order). Passed.
- **The one week-1 target** (2022_01_PHI_DET) changed by 2.9. By the pre-registered definition, week 1 reads the
  week-1 roster file, and the test corrupts it. That file may reflect the roster on game week, so for week-1 games
  (about 6% of games) the reserve and departure flags are possibly look-ahead.

This is disclosed rather than hidden. It does not rescue AV1, which fails with or without week 1.

## Limitations

- **Retrospective inputs.** Historical injury data are final weekly reports only, and the QB is the actual starter
  (final horizon). The backtest is optimistic against live use.
- **Roster files.** Their publication times are unknown: the previous-week file is used, and week 1 uses the week-1
  file (above).
- **Untouched games.** 2026 games after 21 Nov 00:08 GMT have not been evaluated. They will be after the season.
- **One run per arm.** The pre-registered settings were not tuned afterwards, and none will be this season.
