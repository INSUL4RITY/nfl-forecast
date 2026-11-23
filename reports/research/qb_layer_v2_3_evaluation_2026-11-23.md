# QB layer for the stats-only line ("v2.3 = v2.2 + QB layer"): evaluation, 2026-11-23

**Pre-registration.** `qb_layer_v2_3_preregistration_2026-11-23.md`, written before anything was built. Its RFC 3161
timestamp (FreeTSA) is 23 Nov 2026 19:23:35 GMT, verified, in `.md.tsa.jsonl`.

**Run and code.** Run `20261123T193014Z`, files `qb_layer_v2_3_evaluation_20261123T193014Z.json` and
`_predictions.parquet`. Code: `qb_layer/build.py`, `qb_layer/evaluate.py`, `qb_layer/week12.py`. Every number below comes
from these files.

**Scope.** Research for 2027. The frozen v1.0 Model line, the frozen v2.2 trial line, the pick rule and the site are
unchanged.

## Verdict: the QB layer FAILS the pre-registered rule

All 1,675 games of the 2019-2024 folds, identical across arms:

| Pass check | QL ("v2.3") vs v2.2 | Needed |
|---|---|---|
| Paired margin SE difference | −0.31 [−0.94, +0.29] | CI below 0 |
| Seasons better | 4 of 6 | ≥ 4 |
| Dev folds 2022-24 MSE | 161.18 vs 161.36 | not worse |

The layer points in the right direction, but by too little to separate from noise. Two of three checks pass; the
interval check, the one that matters, does not. Per season (QL minus v2.2): 2019 −0.77, 2020 +0.10, 2021 −0.64,
2022 −0.41, 2023 +0.86, 2024 −0.99. Total-points MSE −0.22 [−0.85, +0.37]. Margin MAE −0.024 [−0.047, −0.004]
(not judged).

## Every arm (2019-24, 1,675 games; margin MSE; difference vs v2.2 with 95% season-week bootstrap CI)

| Arm | MSE | vs v2.2 | Seasons better | Dev 2022-24 |
|---|---|---|---|---|
| v2.2 (rebuilt on current data, the reference) | 169.84 | – | – | 161.36 |
| v1.0 (official Model line) | 169.77 | −0.07 [−1.34, +1.21] | 3/6 | 161.73 |
| **QL (primary)** | 169.53 | −0.31 [−0.94, +0.29] | 4/6 | 161.18 |
| QL-B1 (QB-split team form only) | 169.98 | +0.14 [−0.39, +0.69] | 3/6 | 161.88 |
| **QL-B3 (designed runs + opponent adjustment only)** | 169.57 | **−0.27 [−0.53, −0.02]** | 4/6 | 161.01 |
| QL-B27 (draft-pedigree prior only) | 169.62 | −0.22 [−0.53, +0.10] | 4/6 | **160.89** |
| QL-B4 (CPOE only) | 169.80 | −0.04 [−0.29, +0.21] | 3/6 | 161.35 |
| QL-tuned (B32, constants from 2019-21) | 169.33 | −0.50 [−1.12, +0.14] | 5/6 | 161.34 |
| v1.0 + QL (secondary, vs v1.0) | 169.83 | +0.06 vs v1.0 [−0.82, +0.92] | 3/6 | 161.56 |

**Exploratory leads, not adopted** (as pre-registered, no other arm is promoted when the primary fails):
- **QL-B3:** the QB rating with designed QB runs and opponent-adjusted dropbacks.
  - It is the one arm whose interval is below zero, in 4 of 6 seasons, and better on the dev folds.
  - Seen seasons disagree: 2025 worse (159.81 vs 159.12), 2026 better (148.98 vs 149.72).
- **QL-B27:** the draft-pedigree prior.
  - Best on the dev folds and better in 2025 (158.36). The interval crosses zero.
  - It helps most where intended: newcomers drafted in round 4 or later, or undrafted, at −0.77 in 2019-24 and
    −4.41 in 2025. Both intervals are wide.

**Not supported:**
- **QL-B1 (QB-split team form):** worse overall, and clearly worse in backup-QB games (+3.16 [+0.32, +6.25]).
- **QL-B4 (CPOE):** no effect.
- **B32 (tuning):** it chose a 32-game half-life with no season decay. The gain appears only on the folds it was tuned
  on: dev 161.34 against 161.36.
- **Adding the layer to v1.0:** no help.

## The question asked: does the model treat a new QB as inheriting the old QB's production?

**Not wholesale.** The team-form inputs are averaged over every recent game, whoever played QB. But `qb_delta` (the new
starter's rating minus the rating of the QBs behind that history) corrects for the change. In the v2.2 fit for 2024 it is
worth about 5.4 points of team score per 1.0 EPA per dropback of rating, plus 12.3 per 1.0 of delta. Example: a backup
rated 0.25 below the team's usual starter takes roughly 4.4 points off the team's expected score.

**It may under-correct slightly. The evidence is not conclusive.** The slope of the team-points residual (actual minus
predicted) on `qb_delta`, in team-games with a QB change, 2019-24 out-of-fold:

| Model | QB-change team-games | Slope (pts per 1.0 delta) | Change + newcomer starter | No change |
|---|---|---|---|---|
| v1.0 | 427 | +8.6 (SE 5.2) | +18.0 (SE 13.6), n 120 | +4.3 (SE 5.4) |
| v2.2 | 427 | +9.3 (SE 5.1) | +18.0 (SE 13.4) | +7.3 (SE 5.4) |
| QL | 427 | +9.5 (SE 5.1) | +18.1 (SE 13.4) | +5.0 (SE 5.4) |

- A positive slope means a team whose QB got worse scored a little less than predicted. Taken at face value, the
  0.25 downgrade above is under-counted by about 2 points.
- That slope is under 2 standard errors. A similar slope appears in games with no QB change, so it is probably general
  ridge shrinkage of the QB inputs rather than a "new QB" problem.
- With 2025 included, the QB-change slope falls to +5-6 (SE 4.8).
- Teams with a new QB finished on average 0.7-0.9 points below the model (SE 0.6): not significant.
- None of the QB-layer components changes this pattern.

## Subsets (paired QL − v2.2 margin SE; 2019-24 unless stated)

| Subset | Games | QL − v2.2 | Mean result − model, side concerned (v2.2) |
|---|---|---|---|
| QB change (either team) | 382 | +0.08 [−1.60, +1.89] | −0.89 (SE 0.62) |
| Starter under 200 career dropbacks | 302 | +0.35 [−1.46, +2.13] | −0.39 (SE 0.71) |
| Backup starter (new and under 200 dropbacks) | 120 | +2.59 [−0.86, +6.51] | −0.23 (SE 1.14) |
| Newcomer drafted round 4+ or undrafted | 153 | +0.82 [−1.60, +3.16] | −0.73 (SE 1.06) |

**Seen seasons, small samples:**
- 2025: the late-round newcomer sides finished 5.5 points below the model (n 20, SE 2.9).
- 2026: those sides finished 2.2 below (n 10).

That matches the B5/B27 pattern noted on 17 Nov: suggestive, too few games to act on.

## Seen seasons (reported separately, never pooled)

| Season | v1.0 | v2.2 | QL | QL-B3 | QL-B27 | QL-tuned |
|---|---|---|---|---|---|---|
| 2025 (285 games) | 161.67 | 159.12 | **158.02** | 159.81 | 158.36 | 159.38 |
| 2026 to 20 Nov (151 games) | 149.49 | 149.72 | 149.49 | **148.98** | 149.93 | 148.88 |

- QL vs v2.2: 2025 −1.10 [−2.41, +0.21]; 2026 −0.23 [−2.39, +2.25].
- 2026 uses the actual starter (retrospective), not the QB known at the lock.

## Big gaps (gap-vs-result slope, untimed ~closing lines, 2019-25, 1,960 games)

| Arm | All | Spread < 7 | Spread ≥ 7 |
|---|---|---|---|
| v1.0 | 0.01 (SE 0.11) | 0.20 (0.14) | −0.22 (0.17) |
| v2.2 | 0.10 | 0.30 | −0.11 |
| QL | 0.12 | 0.32 | −0.09 |

The QB layer does not make big-spread gaps informative either: the slope at spreads of 7+ stays at or below zero. This
is the C7/C11 finding, unchanged.

## Week 12 2026 starters you named (ratings only; these games are untouched, evaluated after the season)

Rating = shrunk EPA per play, as of the data on 20 Nov. "Prior" = the starting estimate a QB is shrunk towards.

| QB | Draft | Career dropbacks | Prior: current → layer | Rating: current → layer |
|---|---|---|---|---|
| Fernando Mendoza | round 1, pick 1 | 48 | −0.142 → −0.111 | −0.158 → −0.109 |
| Kyle McCord | round 6, pick 181 | 37 | −0.142 → −0.194 | −0.174 → −0.220 |
| Joe Milton III | round 6, pick 193 | 104 | −0.142 → −0.194 | −0.138 → −0.173 |
| Jacoby Brissett | round 3, pick 91 | 2,962 | −0.142 → −0.140 | −0.066 → −0.058 |

- The pedigree prior moves the rookies the way you would expect: a first overall pick is trusted more, sixth-rounders
  less.
- Through the model's weights, each change is worth well under a point. It would not by itself have changed these
  games' lines much.
- Brissett is rated on his own long record, so the layer barely moves him.
- A missing Brock Bowers is a non-QB absence: the QB layer does not cover it.

## Checks
- **Builder:** the rebuilt current rule reproduces the stored v1.0 `qb_rating`, `qb_log_db` and `qb_delta` exactly
  (maximum difference 0.0, 3,033 games).
- **Leakage:** 20 seeded target team-games, rebuilt with all play-by-play at or after kickoff removed: identical
  (maximum difference 0.0).
- **Deviation from the pre-registration (disclosed).**
  - The stored v2.2 feature file dates from 27 Oct 2026, before the current starter rule (the trick-play passer fix).
  - Its QB columns differ from today's; its other columns are identical through 2025.
  - So the v2.2 reference, and every QL arm, uses the v2.2 specification rebuilt on the same 20 Nov data
    (`features/v2.build_snapshots`).
  - The stored file, refit, scores 169.78 against the rebuilt 169.84 (−0.05 [−0.16, +0.01]), so the choice does not
    matter.

## Limitations
- Final-horizon backtest: the actual starter is known, which is optimistic against live use.
- Historical lines are untimed.
- Designed-run detection depends on nflverse positions.
- One run per arm; no retuning after results.
- 2026 games after 20 Nov are untouched.

## What it means for 2027
- Keep the QB inputs as they are for v2.2's end-of-season review.
- Carry two leads into the 2027 pre-registration, judged on clean 2026 weeks 12-18 plus the full season:
  - designed runs + opponent adjustment (QL-B3);
  - the draft-pedigree prior (QL-B27).
- Drop QB-split team form (B1) and CPOE (B4) as model inputs.
- Do not repeat constant tuning (B32) without a new idea.
- The "inherits production" question is worth one more look with the 2026 season added: the slope is positive in every
  arm, but not yet significant.
