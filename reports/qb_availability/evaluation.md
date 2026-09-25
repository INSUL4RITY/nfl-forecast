# QB start-probability audit and evaluation

Generated 2026-09-25T01:37:00.125972+00:00. Target = the depth-chart QB1 **started** (weekly depth charts 2016-2024).
Each test season is predicted from earlier seasons only.

## What the Questionable / Doubtful cases measure

| status | final practice | n | started | played, not started | declared inactive | P(start) Jeffreys | 90% interval |
|---|---|---|---|---|---|---|---|
| Doubtful | DNP | 20 | 0 | 0 | 12 | 0.02 | 0.00-0.09 |
| Doubtful | Limited | 9 | 0 | 0 | 7 | 0.05 | 0.00-0.19 |
| Doubtful | Full | 2 | 0 | 0 | 2 | 0.17 | 0.00-0.57 |
| Questionable | Limited | 131 | 68 | 5 | 39 | 0.52 | 0.45-0.59 |
| Questionable | Full | 41 | 36 | 1 | 3 | 0.87 | 0.78-0.94 |
| Questionable | DNP | 21 | 8 | 0 | 11 | 0.39 | 0.23-0.56 |

## Chronological evaluation (test seasons 2019, 2020, 2021, 2022, 2023, 2024)

| method | subset | n | log loss | Brier | mean predicted | observed |
|---|---|---|---|---|---|---|
| status_beta11 | Questionable+Doubtful | 162 | 0.6246 | 0.2245 | 0.565 | 0.475 |
| status_jeffreys | Questionable+Doubtful | 162 | 0.6216 | 0.2244 | 0.563 | 0.475 |
| status_x_practice | Questionable+Doubtful | 162 | 0.6019 | 0.2143 | 0.535 | 0.475 |
| status_beta11 | all QB1 games | 3331 | 0.2650 | 0.0710 | 0.887 | 0.877 |
| status_jeffreys | all QB1 games | 3331 | 0.2647 | 0.0710 | 0.887 | 0.877 |
| status_x_practice | all QB1 games | 3331 | 0.2588 | 0.0693 | 0.886 | 0.877 |

Paired log-loss difference vs the previous estimator (negative = better; bootstrap over test cases):

| method | subset | n | mean diff | 95% CI |
|---|---|---|---|---|
| status_jeffreys | uncertain | 162 | -0.0029 | [-0.0046, -0.0014] |
| status_jeffreys | overall | 3331 | -0.0003 | [-0.0004, -0.0002] |
| status_x_practice | uncertain | 162 | -0.0227 | [-0.0602, +0.0184] |
| status_x_practice | overall | 3331 | -0.0062 | [-0.0105, -0.0019] |

Shrinkage pseudo-count m chosen per test season (nested, training seasons only): {2019: 20.0, 2020: 5.0, 2021: 5.0, 2022: 20.0, 2023: 20.0, 2024: 20.0}

Note: all estimators over-predict starts for Questionable/Doubtful QBs in these test seasons (mean predicted vs observed above): the start rate for listed QBs has drifted down in recent seasons (e.g. 9/27 Questionable QB1s started in 2024). This is reported, not corrected; a recency-weighted estimator is a candidate for future evaluation.