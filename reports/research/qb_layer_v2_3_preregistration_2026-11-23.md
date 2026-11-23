# Pre-registration: QB layer for the stats-only line ("v2.3 = v2.2 + QB layer"), 2026-11-23

Written before any of the inputs below was built or evaluated. User request 2026-11-23: test a "QB-adjusted offensive
model" in model v2, validated against the existing model over 2019-2025, with no garbage-time filtering. Research for
2027 only: the frozen v1.0 Model line, the frozen v2.2 trial line (`configs/model_v2.yaml`), the pick rule and the site
are not changed, and nothing here is shown on the site. Research list items: B34 (this test), B1, B3, B4, B27, B32
(`docs/research_2027.md`).

## Question
The team-form inputs (EPA per play, per dropback, explosive passes, sacks, interceptions...) are averages over the team's
recent games, whoever played quarterback. The QB inputs (`qb_rating`, `qb_delta` = expected starter's rating minus the
rating of the QBs in the team's weighted history, `qb_change`, `qb_log_db`) are meant to correct for that. Does a richer
QB layer correct it better, and does the current model under-correct (treat a new QB as if he inherited his
predecessor's production)?

## Base and data
* **Base:** the v2.2 specification (`feature_set("v2.2")`, `data/processed/feature_snapshots_v22.parquet`), final horizon,
  refit walk-forward in this harness. The QB at the final horizon is the actual starter (retrospective proxy, labelled).
* QB inputs are rebuilt from nflfastR play-by-play 2011-2026 (`ep_scale.load_pbp`, as the pipeline reads it); ratings are
  as of each game's cutoff using only games whose play-by-play was available by then (kickoff + 12 h), exactly as now.
* Builder check (must hold before any evaluation): the rebuilt "current" rating reproduces the stored `qb_rating`,
  `qb_log_db`, `qb_delta` to within 1e-9.

## The QB layer (four components)
1. **B1, QB-split team form.** Team-form weights as now (half-life 8 games, season carry 0.6, last 48 games). For the
   expected starter: `qbs_share` = weighted share of the team's window started by him (0 to 1), and `qbs_db_gap` = the
   team's offensive EPA per dropback in the window's games he started (weighted, shrunk towards the all-games value with
   150 dropbacks) minus the all-games value (0 when he started none).
2. **B3, rating content.** The QB rating adds **designed QB runs** (`rush == 1`, not a scramble, not a kneel, rusher
   listed at QB; EPA and count credited to the rusher) to dropbacks, and **opponent-adjusts** dropback EPA: each game's
   dropback EPA is reduced by dropbacks x the opponent defence's EPA per dropback allowed above the league mean, measured
   as of that game's kickoff from the opponent's earlier games only (same weights as team form, shrunk to 0 with 300
   dropbacks; league mean = all teams' earlier games over the last ~3 seasons).
3. **B27, draft-pedigree prior.** The shrinkage target ("newcomer prior") becomes bucket-specific: round 1, rounds 2-3,
   rounds 4-7, undrafted (nflverse players table; missing round = undrafted). Bucket prior = all-newcomer prior +
   (bucket newcomer EPA per play - all-newcomer EPA per play) x n / (n + 2000), n = the bucket's newcomer plays in the
   same rolling ~3-season window. Everything else in the prior is unchanged.
4. **B4, accuracy.** `qb_cpoe` = the starter's weighted completion percentage over expected (same recency weights as the
   rating, shrunk to the as-of newcomer mean with 200 attempts, divided by 100) and `qb_cpoe_delta` = `qb_cpoe` minus the
   team baseline (the same weighted mix of the team's recent starters as `qb_delta`).

`qb_rating`, `qb_log_db`, `qb_delta` and `qb_exp` (= rating x log dropbacks, in v2.2) are recomputed from the new
rating; `qb_change` is unchanged. Rating constants stay as now (16-game half-life, 0.8 season carry, 250 pseudo-count).
No garbage-time weighting of any kind (failed twice: v2.0, v3-C).

## Arms (walk-forward, train 2016..S-1, alpha by the existing chronological rule, identical games)
* **v2.2** (reference, refit here) and **v1.0** (`core_qb`, reference).
* **QL (primary, "v2.3")**: v2.2 with all four components (`qbs_share`, `qbs_db_gap`, `qb_cpoe`, `qb_cpoe_delta` added to
  the team row; rating replaced as in 2 and 3).
* One-component arms on v2.2: **QL-B1**, **QL-B3**, **QL-B27**, **QL-B4** (exploratory).
* **QL-tuned (B32, exploratory):** QL with (half-life, carry, pseudo-count) chosen from {8, 16, 32} x {0.6, 0.8, 1.0} x
  {100, 250, 500} by pooled margin MSE on folds 2019-2021 only (ties within 0.01: the current constants, then the
  closer value). Judged on the dev folds 2022-2024 only.
* **v1.0+QL (secondary):** `core_qb` with the same QB layer, against v1.0.

## Pass rule (primary: QL vs v2.2, all games of the 2019-2024 folds with a result)
All of:
1. Paired margin squared-error difference QL - v2.2: 95% season-week block-bootstrap interval (2,000 reps) entirely
   below 0 (stricter rule, research item A14).
2. QL better than v2.2 in at least 4 of the 6 seasons.
3. Dev folds 2022-2024: QL margin MSE not above v2.2.

PASS only if all three hold. If QL fails, no other arm is promoted: the others are reported as exploratory leads.
Total-points MSE is reported, not judged.

## Reported, not judged
* **Seen seasons, separately:** 2025 (all games) and 2026 (games in the data on 20 Nov 2026). Never pooled with the folds.
* **Subsets** (paired differences with intervals; mean result-minus-model for the side concerned): games with a QB
  change; starters with under 200 career dropbacks; backup starters (not the team's previous starter and under 200
  career dropbacks); newcomers drafted in round 4 or later or undrafted.
* **"Inherited production" check:** in each arm's out-of-fold predictions, the slope of team points residual (actual -
  predicted) on `qb_delta`, for team-games with and without a QB change. A positive slope in QB-change games means the
  model under-corrects for the new QB.
* Gap-vs-result slopes against untimed (~closing) lines, spreads under 7 and 7+, as in the absences report.
* **Leakage test:** for 20 seeded target games, rebuild the layer with all play-by-play at or after the target's
  kickoff removed: the target's inputs must be identical.
* **2026 week 12 starters (no results):** rating under the current rule and under the QB layer for the backup or rookie
  starters the user named (McCord, Brissett, Mendoza, Milton), as of the week 12 build. Week 12 and later games are
  untouched and are evaluated only after the season.

## Limitations stated in advance
Final-horizon backtest (actual starter known; optimistic against live use); historical lines untimed; designed-run
detection depends on nflverse roster positions; CPOE needs air-yards tracking (missing on some plays). One run per arm,
no retuning after results.
