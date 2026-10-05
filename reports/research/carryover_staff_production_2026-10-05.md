# Research: targeted carry-over after staff changes and lost production (2026-10-05)

Outcome: **no variant passed the pre-registered rule; the model is unchanged and final for the 2026 season.**

## Pre-registration (written before any result)

# Pre-registration: targeted carry-over (staff changes, returning production) — written 2026-10-05, before any result

Question (user, 2026-10-05): should last season count less for a side of the ball (offence/defence) when that side's
play-calling staff changed or it lost much of last season's production, while stable teams keep the normal weighting?

Setup: identical to the earlier carry-over experiment (.scratch/weighting/run_experiment.py, frozen code snapshot,
seasons <= 2024 only, final horizon, walk-forward; tune 2019-21, dev 2022-24). V0 = production (half-life 8, carry 0.6).
Side-specific carry at each season boundary into season S (offence metrics use the offence carry, defence metrics the
defence carry; opponent-adjusted ratings weight a row by sqrt(offence factor of the team x defence factor of the opponent);
the team QB baseline uses the offence carry).

Inputs (season S, team T):
- Staff change, offence: head coach changed, or the offensive coordinator changed (if no coordinator is listed, the head
  coach is taken to run that side). Defence likewise with the defensive coordinator. Source: data/manual/coaching_staff.csv
  (Wikipedia season infoboxes / final staff boxes; week-1 staff where the infobox lists it).
- Returning production, offence: share of T's season S-1 regular-season offensive snaps played by players on T's week-1
  active roster in season S (matched by PFR id or normalised name, same team). Defence likewise with defensive snaps.
  r = share / league mean share that season.

Variants (only these three):
- PC:   carry_side = 0.3 if that side's staff changed, else 0.6.
- RP:   carry_side = 0.6 * clip(r_side, 0.5, 1.25).
- PCRP: carry_side = clip(0.6 * clip(r_side, 0.5, 1.25) * (0.5 if staff changed else 1), 0.2, 0.75).

Decision rule (same as the earlier experiment): a variant is "better" only if, for the COMBINED model (C_resid, core_qb),
final horizon, its margin squared error is lower than V0 in BOTH tune (2019-21) and dev (2022-24), with the 95% season-week
block-bootstrap interval of the paired difference (variant - V0) entirely below zero in each period. If several pass, the
one with the lowest dev loss is adopted. Football-only results, weeks 1-4 bands and against-the-spread records are reported
but are not part of the rule. If none passes, the model stays as it is. 2025 (locked test) and 2026 are not used.
After this decision nothing further is changed this season (user instruction).
- Data fix (2026-10-05, before acceptance): 2017 MIA/TB had no week-1 roster (Hurricane Irma postponement); the
  first roster week of each team is used instead of week 1. Applied identically to all variants.


## Results (paired difference vs V0 in margin squared error; negative = better; 95% season-week block bootstrap)

| Variant | Model | Period | Diff | 95% CI |
|---|---|---|---|---|
| PC | combined | tune | +0.009 | [-0.011, +0.028] |
| PC | combined | tune weeks 1-4 | +0.015 | [-0.034, +0.068] |
| PC | combined | dev | +0.041 | [-0.047, +0.138] |
| PC | combined | dev weeks 1-4 | -0.113 | [-0.354, +0.134] |
| PC | football-only | tune | +0.360 | [-0.418, +1.066] |
| PC | football-only | tune weeks 1-4 | +1.383 | [-0.034, +2.763] |
| PC | football-only | dev | -0.313 | [-0.971, +0.335] |
| PC | football-only | dev weeks 1-4 | +0.260 | [-2.120, +2.397] |
| RP | combined | tune | +0.023 | [-0.152, +0.204] |
| RP | combined | tune weeks 1-4 | +0.096 | [-0.207, +0.447] |
| RP | combined | dev | -0.013 | [-0.063, +0.035] |
| RP | combined | dev weeks 1-4 | -0.079 | [-0.244, +0.022] |
| RP | football-only | tune | +0.081 | [-0.310, +0.488] |
| RP | football-only | tune weeks 1-4 | +0.242 | [-0.868, +1.583] |
| RP | football-only | dev | -0.119 | [-0.431, +0.183] |
| RP | football-only | dev weeks 1-4 | +0.063 | [-0.867, +0.934] |
| PCRP | combined | tune | +0.007 | [-0.015, +0.029] |
| PCRP | combined | tune weeks 1-4 | +0.017 | [-0.045, +0.076] |
| PCRP | combined | dev | +0.030 | [-0.080, +0.148] |
| PCRP | combined | dev weeks 1-4 | -0.161 | [-0.477, +0.096] |
| PCRP | football-only | tune | +0.539 | [-0.371, +1.468] |
| PCRP | football-only | tune weeks 1-4 | +1.877 | [+0.205, +4.166] |
| PCRP | football-only | dev | -0.338 | [-1.045, +0.405] |
| PCRP | football-only | dev weeks 1-4 | +0.603 | [-1.764, +2.940] |

## Against the spread (exploratory, historical lines ~closing)

| Variant | Model | Period | W-L | % |
|---|---|---|---|---|
| PC | combined | tune | 394-413 | 48.8 |
| PC | combined | dev | 424-400 | 51.5 |
| PC | football-only | tune | 422-384 | 52.4 |
| PC | football-only | dev | 412-414 | 49.9 |
| RP | combined | tune | 394-413 | 48.8 |
| RP | combined | dev | 421-401 | 51.2 |
| RP | football-only | tune | 420-387 | 52.0 |
| RP | football-only | dev | 415-409 | 50.4 |
| PCRP | combined | tune | 394-413 | 48.8 |
| PCRP | combined | dev | 421-401 | 51.2 |
| PCRP | football-only | tune | 427-378 | 53.0 |
| PCRP | football-only | dev | 411-414 | 49.8 |

Decision: PC: does not pass; RP: does not pass; PCRP: does not pass.

Inputs: data/manual/coaching_staff.csv (Wikipedia, CC BY-SA), snap counts and weekly rosters (nflverse). Code:
`.scratch/weighting/run_exp2.py` (research harness, git-ignored; same frozen-code snapshot as the 2026-09-28 experiment).
