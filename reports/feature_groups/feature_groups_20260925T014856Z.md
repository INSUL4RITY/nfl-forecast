# Feature-group evaluations

Generated 2026-09-25T01:48:56.652932+00:00.

## Pre-specified promotion rule

(fixed before results were seen, 2026-09-25):
  A feature group is promoted into the production (combined) model only if, for the combined model at the final
  horizon, adding the group
    (1) reduces the group's target loss in the DEV seasons with a 95% season-week block-bootstrap interval entirely
        below zero, AND
    (2) also reduces it (mean difference < 0) in the TUNE seasons.
  Target loss: squared error of the total for weather; squared error of margin plus squared error of total for
  non-QB injuries. The football-only model is evaluated the same way and reported, but it is the fallback, not the
  headline model. The locked 2025 season is NOT used for these evaluations.
  Weather has an extra requirement: its historical inputs are retrospective (stitched short-lead forecasts, not what
  was knowable at the forecast cutoff), so even a pass only makes it a "candidate" until strictly as-of prospective
  snapshots confirm it.

## non-QB injuries (final weekly report; expected lost snap share by unit)

Inputs: final weekly injury report (strictly available before the final horizon). Horizon: final. Tune seasons [2019, 2020, 2021], dev seasons [2022, 2023, 2024].

**Decision: not promoted (rule not met)**

Early horizon: not evaluable: mid-week report versions are not retained historically (now being collected).

| model | period | n | loss diff (cand − base) | 95% CI | margin RMSE base → cand | total RMSE base → cand |
|---|---|---|---|---|---|---|
| combined | tune | 821 | +0.035 | [-0.221, +0.307] | 13.129 → 13.130 | 13.269 → 13.269 |
| combined | dev | 854 | +0.271 | [-0.473, +0.936] | 12.474 → 12.479 | 12.896 → 12.902 |
| football_only | tune | 821 | -0.560 | [-1.885, +0.774] | 13.341 → 13.343 | 13.505 → 13.483 |
| football_only | dev | 854 | -0.495 | [-1.833, +0.916] | 12.717 → 12.686 | 13.128 → 13.139 |

## weather (exposure-weighted wind, gusts, cold, precipitation)

Inputs: RETROSPECTIVE: Open-Meteo Historical Forecast API (stitched short-lead forecasts), 2019+. Horizon: final. Tune seasons [2021], dev seasons [2022, 2023, 2024].

**Decision: not promoted (rule not met)**

| model | period | n | loss diff (cand − base) | 95% CI | margin RMSE base → cand | total RMSE base → cand |
|---|---|---|---|---|---|---|
| combined | tune | 285 | -2.843 | [-5.970, +0.252] | 13.634 → 13.633 | 13.358 → 13.251 |
| combined | dev | 854 | -0.465 | [-1.467, +0.557] | 12.517 → 12.508 | 12.940 → 12.922 |
| football_only | tune | 285 | -3.167 | [-6.726, +0.094] | 13.973 → 13.978 | 13.540 → 13.423 |
| football_only | dev | 854 | -2.017 | [-4.571, +0.287] | 12.792 → 12.788 | 13.106 → 13.029 |
