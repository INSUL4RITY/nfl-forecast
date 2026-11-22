# PLAN: big model-vs-market gaps (2027 research + display now)

User brief of 20 Nov 2026. Branch `research/gaps-2026-11`, worktree `C:\Users\Craig\nflwt-gaps`, created from `main` at
7885669. The scheduled task keeps publishing from the main folder. Nothing in this plan changes:
- the frozen v1.0 model;
- the v2.2 trial;
- the shadow injury artifact;
- the pick rule, grading or the publication schedule;
- any release.

Stop points: after this plan, after A1, after each pre-registration, after the evaluation, and before B6.

## 0. Ground rules for this work

- **Worktree.** Copy `data/raw` (1.0 GB) and `data/processed` (14 MB) into the worktree, and run `npm ci` in its `web/`.
  No links out of the worktree. Releases and evidence come from git, as they are in the worktree already.
- **Part A writes only to `reports/research/` and `.scratch/`.**
  - Research scripts go to `reports/research/gap_absences/`, so they are saved with their results.
  - `.scratch/` is git-ignored and holds intermediate files only.
  - In Part A, `src/` is imported and never edited. The A2 candidate is built in the research scripts as a subclass
    of `features/personnel.Availability`, the same class the shadow line uses, not a parallel system. It is moved into
    `personnel.py` only if it passes and you decide to run it as a trial.
- **Not run during Part A:** `predict`, `operate`, `export-web`, `archive`, `push`, or any Odds API call. No network use
  except FreeTSA for the pre-registration timestamps.
- **Read only:** frozen configs and artifacts (`configs/model_freeze.yaml`, `configs/shadow_injury.yaml`,
  `configs/model_v2.yaml`, `artifacts/**`). `freeze-check` runs at every stop point.
- **EPA scale (A12).** All seasons are fitted on one EPA version:
  - 2016-2025 come from the existing processed tables, which are on the old scale.
  - 2026 is read through `EPS.load_pbp`, which holds it on the old scale.
  - Absence costs are fitted in points: the ridge target is own points, as in `core_qb_inj`.
- **Pre-registrations** follow `v2_preregistration_2026-10-26.md`. Each is written before any result, shown to you, then
  timestamped with RFC 3161 via `predict/archive.timestamp` (FreeTSA), as for qb_v3c (`*.md.tsa.jsonl`). It runs only
  after that. Every variant tried is reported, including failures.

## 1. What exists (the work builds on this)

| Item | Where | Relevant facts |
|---|---|---|
| Non-QB absence inputs | `features/personnel.py` `Availability`, `injury_player_weeks`, `snap_shares`, `UNIT_OF_POSITION` | `lost_<unit>` = P(miss given status) x mean snap share over the team's previous 6 games, with zeros for games missed. Status only, no practice. Units: ol, skill, front, db. |
| Shadow line (`football_only_inj`) | `predict/shadow.py`, `configs/shadow_injury.yaml` | Ridge `core_qb_inj`, alpha 100. Frozen P(play): None 0.865, Questionable 0.600, Doubtful 0.004, Out 0.0004 (2021-25, which overlaps the dev fold). Live inputs come from `inj_now` = the injury snapshot as-of the release, filtered to the game week. |
| Feature sets | `models/core.py` `INJ_TEAM` / `INJ_OPP`, `feature_set("core_qb_inj")` | Own `lost_ol` and `lost_skill` feed own points. The opponent's `lost_front` and `lost_db` feed own points. |
| Walk-forward backtest | `evaluation/backtest.py` (`B_qb`, `B_qb_inj`), `evaluation/feature_groups.py`, `evaluation/metrics.block_bootstrap_diff` | Season-week block bootstrap, sorted blocks. |
| v2.2 walk-forward predictions | `reports/research/v2_2_evaluation_20261027T025629Z_predictions.parquet` | 2019-2025, train 2016..S-1, same games as v1.0. |
| Injury versions (2026) | `features/injury_versions.py`, `data/raw/injuries/2026/` (91 snapshots + `checks.jsonl`) | First-observed and last-confirmed times per player-week version. |
| Release snapshot record | `releases/**/rel_*.json` `input_snapshots.injuries` | Our observation time, the provider's Last-Modified time and the sha256 of the injury file used. Releases from week 7 also store `injury_inputs` per game. |
| Reserve lists (display) | `predict/reserve_list.py` (+ export) | From `rosters_weekly`, with codes mapped to plain English. |
| Departures and arrivals (display) | `predict/roster_moves.py` | Weekly rosters, matched by gsis through the players table. |
| Lock rule | `predict/picks.py` `select_lock24`, `LOCK24_START` | Lock-24h from week 7. "original-pick" for weeks 4-6. |
| Line movement | `predict/linemove.py`, `performance.json.line_movement`, Odds API and nflverse schedule snapshots | Timestamped lines since 24-25 Sept 2026. |
| Earlier evidence | `docs/research_2027.md` (A3, A7, A10, A12, B7-B11, C2, C5, C7), `docs/audit-2026-11.md` section 4 | Audit 2026-11: absent-starter bias −0.37 (own offence) and +0.65 (opponent defence) per absent starter. Adding a forecast-time absence input failed the audit's rule. |
| Team analytics OL backtest | `origin/team-analytics:scripts/team_analytics/backtest_line_absences.py` | A starter counts as missing below 50% of that game's snaps, which includes in-game injuries and benchings. Used in A1 only to explain the difference, never as a target. |

## 2. Part A steps

### A1. Diagnosis: `reports/research/gap_diagnosis_2026-11-<dd>.md`

No fitting and no game outcomes.

**Scripts** (all under `reports/research/gap_absences/`):

**1. `a1_timing.py`: timing at every 2026 lock.**
- For each locked pick (weeks 3-11), the lock version comes from `picks.lock_rule` / `select_*`.
- For each team, using the archived injury snapshots and `injury_versions`, it records:
  - whether that week's final game statuses were in the feed at the lock;
  - when they first appeared;
  - the provider Last-Modified time against our observation time (lag);
  - the share of the final pre-kickoff injury inputs already present at the lock. "Final" means the last version
    before kickoff. The share is player-matched expected lost snaps, recomputed with `Availability` and the frozen
    P(play), and checked against the stored `injury_inputs` from week 7.
- Results are reported by kickoff slot: Thursday, early international, Saturday, Sunday early, Sunday late or night,
  Monday.
- Reads: releases, `publication_evidence`, `data/raw/injuries/2026`, `injury_versions`.
- Writes: `reports/research/gap_absences/a1_timing.{json,parquet}`.

**2. `a1_penalty.py`: the no-status penalty (B8) and statuses, descriptive.**
- Shares of expected lost snaps that come from no-status rows, Questionable rows and practice-only rows:
  - 2026 releases at the lock against the final version;
  - historical final reports, 2019-25.
- Re-derives the B8 rates (97.1% and 72.3% played, against assumed 86.5% and 60.0%) from `injury_player_weeks`.
- These are player-participation outcomes, not game outcomes.

**3. `a1_costs.py`: why the four cost estimates differ, by arithmetic only.**
- **Shadow coefficients.** Read from the frozen artifact: points per unit of `lost_*`, and why a unit is
  "starter-equivalents of expected lost snaps" and not "starters out".
- **Errors-in-variables attenuation.** Variance shares of `lost_ol` that come from probabilistic no-status and
  Questionable rows, against near-certain Out rows. This is descriptive and needs no outcomes.
- **Double counting.** The 6-game share with zeros, and the team-form weights (11% on the last game, 37% on the last
  four).
- **Ridge shrinkage.** The standardised coefficient at alpha 100.
- **Team-analytics figure.** −0.047 EPA per dropback x 35-40 dropbacks. The definition differences:
  - in-game exits and benchings are counted;
  - it is passing plays only;
  - it is EPA, not points;
  - it is per missing starter (50% of snaps), not per full-time starter-equivalent.
- **Hand estimate.** 1.25-1.5 points per tackle: a position-specific value against the unit mean.
- **B11's 0.39.** A model-vs-market difference per starter-equivalent, not a cost per absence.

**4. `a1_ind_hou.py`: IND @ HOU breakdown.**
- By team and unit, at the lock (`rel_20261118T195302Z`) and at the final pre-game release (`rel_20261119T234714Z`).
- Shows:
  - each listed player's status, practice status, snap share, P(miss) and expected lost snaps;
  - points per unit through the frozen shadow coefficients;
  - regulars on reserve lists and traded regulars (Downs, Allen, Nelson, Buckner; Al-Shaair), from the
    `reserve_list` and `roster_moves` logic, in starter-equivalents. These are not in any input.
- Research only; never published as a forecast.

**5. Gap decomposition (question 2), outcome-free.**
- For 2026 locks: how much of each 3+ point gap the injury inputs account for (`football_only_inj` − `football_only`),
  at the lock and at the final version.
- How the gap would change with the B8-corrected rates, plus reserve-list and departure starter-equivalents, priced
  at the frozen unit costs (labelled as an illustration, not a fitted model).

**The report** also states what remains unexplained: market information we cannot see (news, depth-chart changes,
weather, the market's own player values).

**STOP.**

### A2. Better absence inputs: `reports/research/absences_v1_preregistration_2026-11-<dd>.md`

Pre-registered first; **STOP** for your yes; RFC 3161 timestamp; then run.

**Candidate (one primary, plus pre-declared variants).** It extends `Availability` and keeps the four units:
1. **P(miss) (B8).** By final status x final practice status (DNP / Limited / Full / none) x snap-share band (under
   0.2, 0.2-0.5, 0.5-0.8, 0.8 and over). Refitted walk-forward on seasons before the test season only. Cells are
   shrunk to the status margin, with the strength chosen on the tune seasons.
2. **Reserve-list regulars (B10).** From the team's latest weekly roster file before the game week (previous week's
   file; publication time is not recorded, so this is labelled).
3. **Departures and arrivals (B11).** Matched by gsis through the players table, as `roster_moves` does. An arrival's
   share comes from his previous team, scaled by the expected-play rate.
4. **Rating-weight scaling (B11).** Each player's contribution is
   share_i x (W_i − E[play_i]):
   - W_i is the team-form weight (half-life 8, carry 0.6, from `settings`) on the rated games in which he played;
   - E[play_i] is his expected participation this game.

   So an absence already in the results counts only for its unabsorbed part, and a return from injury or IR comes out
   negative (a gain).
5. **QBs excluded.** They keep the existing logic.
6. **Finer splits (B9).** EDGE against interior, CB against S, depth role. Pre-registered as a secondary variant only,
   shrunk towards the unit mean with the penalty chosen on the tune seasons.

**Costs** are fitted only on information available before kickoff: final status x practice x snap band, or "took no
snaps". Never on that game's snap share, and never on a status set on game day. Historical data are final weekly
reports only, so the backtest is labelled retrospective and optimistic.

### A3. Validation, written into the pre-registration

- **Folds.** Walk-forward; train 2016..S−1. Tune 2019-21, dev 2022-24. Snap counts go back to 2012 for the shares and
  rates.
- **Seen data.** 2025 and 2026 weeks 1-11 count as seen and are reported separately. Games after the pre-registration
  timestamp are untouched and evaluated later.
- **Primary metric.** Paired margin squared error on identical games, with `block_bootstrap_diff` by season-week.
  Compared against:
  - v1.0 (`B_qb`);
  - `football_only_inj` (walk-forward `B_qb_inj`, as-of rates);
  - v2.2 (existing walk-forward predictions);
  - a shrink-to-line baseline q = line + k(model − line), with k fitted walk-forward on earlier seasons (C2/C7).
- **Pass rule (proposed, for you to confirm in the pre-registration).** Lower margin squared error than v1.0 AND
  `football_only_inj`, with the 95% CI below zero over 2019-24, and better in at least 4 of 6 seasons. v2.2 and the
  shrink baseline are reported, not gating.
- **Secondary.** Gap-vs-result slope (C5), split under 7 and 7+. Gap bins are descriptive only, with Wilson intervals.
  2019-25 are graded on untimed (~closing) lines and 2026 on archived lock lines, never pooled.
- **Leakage test.** For a sample of games, corrupt every injury, roster and snap row dated after the cutoff, and every
  row for the target game. Re-run the feature build; the outputs must be identical.

**STOP after the evaluation.** If something passes, I propose (but do not build) the three labels and the record of the
games each would set aside, stored in the lock version and graded on its line.

### A4. Lock timing proposal: `docs/research_2027.md` A7, plus a short section in the A1 report

- From A1's timing table, a 2027 rule: lock at the later of (lock-24h, both teams' final statuses in the feed plus a
  buffer), but no later than a fixed time before kickoff.
- The cost is estimated from our own timestamped lines: how much the line moves between lock-24h and the proposed lock
  time, by slot.

### A5. Records

- `docs/research_2027.md`: update A3, A7, A10, A12, B7-B11, C2, C5 and C7. Add a new item: the "market view" on the
  Team ratings page, fitted on the season's archived lock lines with older weeks down-weighted. It needs a like-for-like
  injury treatment, because market lines already include current injuries.
- `PROGRESS.md`: dated entry.

## 3. Part B: display only, built in the same worktree after A1

- Built at export time only, like `reserve_list`.
- Never in the release JSON or in "notable" (the `injury_report` fingerprint must not change).
- No point values.

**B1. "Who is missing" on Big and Biggest gap cards and their game pages.** A new `predict/absence_display.py` reuses:
- `injury_report_for` / `injury_rows` (status or practice status);
- `UNIT_OF_POSITION` (unit, in plain words);
- `reserve_list`;
- `roster_moves` (traded or released since the team's rating window began, i.e. the first game with weight in the
  current form).

A shared helper in `features/injury_versions.py` reports whether each team's final statuses were in the data at the
lock. A1 uses it too. When they were not, the note reads: "Measured before final injury reports reached the data".
Components: new `MissingPlayers.tsx`, used in `GameCard.tsx` (gap cards only) and on the game page.

**B2. Gap records in context.** The 3-4 and 4+ point bands shown separately, each with:
- a Wilson interval;
- the historical rate for the same band, split under 7 and 7+ and labelled retrospective.

The historical rates are computed once from the locked run's out-of-fold `B_qb` predictions (2019-2025, untimed lines)
into `reports/research/gap_band_history_2026-11-<dd>.json`. Export reads that file. Shown on the home record strip and
on Performance.

**B3. "Edge" becomes "difference".**
- `Pick.tsx` (`EDGE`, `edgeText`, card info text);
- `methodology/page.tsx` (lines ~254-257);
- the Details section and any glossary.

The matchup-row "edge" labels (research C8) are a different thing. I propose "advantage" there for consistency, if you
agree.

**B4. Card fixes.**
- `PICK_EXPLAIN` is shown once per page, with an info toggle on each card.
- "Uses market spread & total" (`GameCard.tsx:85`) moves to the market-adjusted line's row.

**B5. Small fixes.**
- UK spelling sweep (`app/game/[id]/page.tsx`, `app/ratings/page.tsx`, `RatingsTable.tsx`).
- Open Graph and Twitter tags with a static preview image, using `metadataBase` = the Pages URL.
- axe-core run in the browser on the local build, home and a game page; target no serious or critical violations.

**Checks.**
- pytest;
- `verify-claims` (new check: absence lists contain no codes or IDs);
- layout audit at 1280, 768, 414, 375 and 320, locally;
- Method page entry;
- CLAUDE.md and PROGRESS.md record the exception.

The IND @ HOU game page shows B1 as the worked example. Nothing is merged or pushed until you say so.

**B6.** Two or three original designs for the About credit, the footer, the README credit and the week header, shown
as a proposal. **STOP** for your choice. The credit stays until the derived layout is gone.

## 4. Order and what you'll see

1. Plan, now. **STOP.**
2. A1 diagnosis report. **STOP.**
3. A2/A3 pre-registration. **STOP**, then timestamp and run.
4. Evaluation. **STOP.**
5. Part B (B1-B5) can be built while you review the A2 pre-registration or results. B1 depends on the A1 timing helper.
6. B6 proposal. **STOP.**
7. A4/A5 written alongside, and final checks.

## 5. Questions I've answered myself (say if you disagree)

- **Pass rule.** It must beat both v1.0 and `football_only_inj` with the CI below zero (audit standard, research A14),
  not a point estimate.
- **Research code** lives in `reports/research/gap_absences/` so it is versioned. `.scratch/` holds intermediates only.
- **Historical band rates for B2** come from the frozen v1.0 out-of-fold predictions (locked run), because that is the
  line the site tracks.
