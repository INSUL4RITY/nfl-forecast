# Better absence inputs ("absences v1", research A2/A3): pre-registration, 2026-11-21

Written before any candidate input was built or any result computed. Brief: user, 20 Nov 2026. Plan: `PLAN.md`.
Diagnosis: `gap_diagnosis_2026-11-20.md`. User go-ahead: 21 Nov 2026 ("you can write A2, A3 pre-registration next.
Just do everything").

This is offline research for the 2027 model. It changes nothing published:
- the frozen v1.0 model;
- the v2.2 trial;
- the shadow injury artifact (`configs/shadow_injury.yaml`);
- the pick rule, grading, the schedule and every release.

If a candidate passes, whether it becomes a frozen, tracking-only trial line this season is the user's decision. Every
variant below is reported, including failures.

## 1. What is tested

The stats-only ridge (`FootballRidge`) keeps the `core_qb_inj` structure:
- own `lost_ol` and `lost_skill` feed own points;
- the opponent's `lost_front` and `lost_db` feed own points.

Only **how the four unit inputs are computed** changes. QBs are excluded from every unit and keep the existing QB
logic. Everything else in the feature set is the frozen v1.0 specification.

### Definitions shared by all candidates (team T, target game t)

**Window.** T's last 48 games before t, the same rows and weights as team form (`features/asof.py`):
- w_g = 0.5^(k/8) x 0.6^(seasons back), with k = games ago (0 = most recent);
- W_T = the sum of w_g.

**Snap share.** s_ig = offensive snap % for OL and skill players, defensive snap % for front and DB players, from
nflverse snap counts (2012+). "Played" = s_ig > 0.

**Unit.** The player's snap-count position mapped by `personnel.UNIT_OF_POSITION`. QB, K, P and LS are excluded.

**Rating share and its parts.** For each player with any played game for T in the window:
- r_i = sum(w_g s_ig) / W_T, his share of the team's current rating;
- W_i = sum(w_g [played]) / W_T;
- b_i = sum(w_g s_ig) / sum(w_g [played]), his usual share when he plays.

**Band** of b_i: under 0.2, 0.2-0.5, 0.5-0.8, 0.8 and over.

**Played last game.** Whether the player had s > 0 in T's previous game.

**Injury report.** The nflverse final weekly report for t's week. Game status: None, Questionable, Doubtful or Out.
Practice status: DNP, Limited, Full or none. Historical files hold only the final report, so this is **retrospective and
optimistic**: live inputs before the final report would be worse (A1, section 2).

**Roster file.** nflverse weekly rosters (2016+): T's file for the previous game week (week 1: the week-1 file). A
player is:
- **reserve** if his status there is RES;
- **departed** if he is not on T's file that week as ACT or INA (traded, released, practice squad, retired);
- **active** otherwise.

The files' publication times are not recorded, so this is labelled as a possible lag.

**Expected participation P_i:**
1. **On t's injury report** (this takes precedence over the roster, to de-duplicate players designated to return):
   P_list(status x practice x band). Each cell is shrunk to its status x band rate with weight m = 50 (fixed now, not
   tuned).
2. **Else reserve or departed:** 0.
3. **Else active and unlisted:** P_unl(band x played-last-game).

**Rates are as-of.** Each game's rates use only the 5 seasons before its own season (2012+ for P_list; 2016+ for P_unl).
- For 2016, the first roster season, P_unl uses 2016 itself. 2016 is only ever a training season, never a test season.
- "Played" in the rate tables = took an offensive or defensive snap in that game (participation, not results).

**Arrivals.** Players active on T's roster file who have no played game for T in the window, but at least one for
another team in their own last 48 games:
- b_i = his weighted usual share there (same weights, his games);
- r_i = 0;
- P_i as in rules 1-3.

### Candidates

| Arm | Unit input lost_u = sum over the unit's players of | Notes |
|---|---|---|
| **AV1 (primary)** | (r_i − b_i x P_i): every window player plus arrivals | B8 rates + reserve lists (B10) + departures and arrivals (B11) + rating-weight scaling (B11). Returns and arrivals come out negative. |
| AV1-inj | (r_i − b_i x P_i) over players on t's injury report only | Rating-weight scaling + B8 rates; no roster information. |
| AV1-b8 | 6-game share x (1 − P_list), over players on t's report | The current shadow formulation with the B8 cells (band from the 6-game share). Isolates the B8 rates. |
| AV1-split (B9, secondary) | AV1, plus two subset inputs: lost_edge (DE, OLB, EDGE) and lost_cb (CB) | Totals keep the unit means; the subsets carry the difference, shrunk by the ridge penalty, which is chosen chronologically inside each training window. Depth-role splits are not tested this round. |

**Not tested:** costs per player production (B7's "player value" idea) and depth-role splits. Both are left for 2027.

### Comparison arms (same harness, same games)

| Arm | What it is |
|---|---|
| **v1.0** | `B_qb`, feature set `core_qb`. Refit walk-forward; it must reproduce the frozen specification. |
| **inj-cur** | `B_qb_inj`, the current injury inputs (as-of P(play) by status, from `feature_snapshots.parquet`). The walk-forward equivalent of the shadow line (`football_only_inj`). |
| v2.2 | Existing walk-forward predictions (`v2_2_evaluation_20261027T025629Z_predictions.parquet`, 2019-2025, same folds). |
| shrink-to-line | q = line + k(v1.0 − line). k minimises squared margin error on v1.0's out-of-fold predictions of the seasons before S (starting 2017), clipped to [0, 1] (C2/C7). |

## 2. Folds, data, metric and pass rule (fixed now)

**Folds.**
- Final horizon (actual starter as the QB proxy, labelled retrospective).
- Walk-forward, expanding: train 2016..S−1, predict S.
- Ridge alpha by `select_alpha_chronologically` inside each training window.
- Tune folds 2019-21, dev folds 2022-24.
- **2025** and **2026 weeks 1-11** are seen data, reported separately: train ≤2024 for 2025, ≤2025 for 2026.
- 2026 uses final-report inputs (retrospective), not the lock-time inputs.

**Untouched.** 2026 games that kick off after this file's RFC 3161 timestamp (week 12 on). Evaluated after the season,
not now.

**EPA scale.** Every fit uses the existing processed tables (old EPA scale; 2026 held on it by `data/ep_scale.py`).
Absence costs are in points (the ridge target is own points).

**Primary metric.** Paired margin squared error on identical games (all arms present, market line available).
`evaluation/metrics.block_bootstrap_diff` resampling season-weeks, 2,000 reps, seed 20261121.

**Pass rule.** AV1 passes only if ALL of these hold over the 2019-2024 folds:
1. the mean paired SE difference vs **v1.0** has a 95% CI entirely below zero;
2. the mean paired SE difference vs **inj-cur** has a 95% CI entirely below zero;
3. AV1's mean SE is lower than inj-cur's in at least **4 of the 6** seasons;
4. AV1 is not worse than inj-cur on the dev folds 2022-24 alone (point estimate).

**Not gating** (reported only):
- v2.2;
- shrink-to-line;
- margin MAE and RMSE;
- totals;
- 2025;
- 2026;
- the three other AV1 arms (each also shown against v1.0 and inj-cur with the same statistics).

If AV1 fails, no other arm is promoted from this test. Any arm that would have met the rule is listed as exploratory.

## 3. Secondary analyses (descriptive, fixed now)

**C5 slope.** Regress (result margin − line margin) on (model margin − line margin), per arm, with OLS slope, SE and
n, split by |spread| < 7 and >= 7.
- Lines: 2019-2025 untimed nflverse (~closing), labelled.
- 2026: the archived **lock** line of each locked pick (`locked_pick.line_home_spread`).
- The two are never pooled.

**Gap bins.** Share of games finishing on the model's side of the line by |gap| bin (0-1, 1-2, 2-3, 3-4, 4+), with 95%
Wilson intervals. Pushes and zero gaps are excluded. Descriptive only.

**Question 2 check.** In big-gap games (|v1.0 − line| >= 3), report the mean of (AV1 − v1.0) signed towards the gap:
how much of the gap the new absence inputs take back.

## 4. Leakage test (must pass before any result is reported)

Pick 40 target games, chosen by a fixed seed from 2019-2026. Rebuild AV1's inputs after corrupting:
- every snap-count row of the target game and of every later game (shares set to random values, rows added and dropped);
- every injury-report row of later weeks;
- every roster-file row of the target week and later weeks;
- every 2026 row dated after the target's kickoff.

The four unit inputs for the target games must be identical to the uncorrupted build, to 1e-12.

The target game's own **final injury report** is allowed: it is published before kickoff, and is the input being tested.

## 5. Outputs

All under `reports/research/`:
- `absences_v1_preregistration_2026-11-21.md`, plus its `.tsa.jsonl` RFC 3161 token, made before the run;
- `gap_absences/a2_*.py` scripts;
- `absences_v1_evaluation_<UTC>.json` and `_predictions.parquet`;
- `absences_v1_evaluation_<date>.md`.

If AV1 passes, the user decides whether it becomes a frozen, tracking-only trial line. Labels such as "Gap holds after
absences", "Absences explain the gap" and "Absences reverse the gap" would then be **proposed, not built**, with the
record of the games each label would set aside.
