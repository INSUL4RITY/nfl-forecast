# Backtest report `bt_20260924T233950Z`

Generated 2026-09-24T23:39:50.369369+00:00 (UTC). Code hash `e8ae1e520562`. Folds (walk-forward, expanding window): [2019, 2020, 2021, 2022, 2023, 2024]. Locked test season 2025 not evaluated.

All numbers below were produced by `python -m nflcast backtest` on real nflverse data. Lower is better for MAE/RMSE. Historical market lines are the single nflverse schedule line (timing unknown, treated as approximately closing), so market comparisons apply only to the final-pregame horizon.

Periods: `tune` = seasons used to make modelling choices (feature sets, settings); `dev` = walk-forward development report seasons.

## Overall (pooled over folds)

| period | horizon | model | n | margin MAE | margin RMSE | total MAE | total RMSE | home MAE | away MAE | winner acc |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | early | B_qb | 854 | 9.80 | 12.85 | 10.37 | 13.19 | 7.35 | 7.22 | 0.643 |
| dev | early | B_core | 854 | 9.80 | 12.85 | 10.43 | 13.29 | 7.36 | 7.26 | 0.649 |
| dev | early | B_qb_noadj | 854 | 9.82 | 12.87 | 10.33 | 13.20 | 7.36 | 7.20 | 0.648 |
| dev | early | N_naive_home | 854 | 10.63 | 13.80 | 10.80 | 13.66 | 7.78 | 7.66 | 0.546 |
| dev | final | A_market_raw | 854 | 9.49 | 12.48 | 10.11 | 12.95 | 7.19 | 7.03 | 0.681 |
| dev | final | A_market_cal | 854 | 9.50 | 12.50 | 10.11 | 12.95 | 7.19 | 7.04 | 0.681 |
| dev | final | B_qb_inj | 854 | 9.73 | 12.69 | 10.28 | 13.14 | 7.31 | 7.13 | 0.662 |
| dev | final | B_qb | 854 | 9.75 | 12.72 | 10.27 | 13.13 | 7.31 | 7.14 | 0.662 |
| dev | final | B_qb_noadj | 854 | 9.77 | 12.74 | 10.23 | 13.14 | 7.32 | 7.12 | 0.658 |
| dev | final | B_core | 854 | 9.80 | 12.85 | 10.43 | 13.29 | 7.36 | 7.26 | 0.648 |
| dev | final | N_naive_home | 854 | 10.63 | 13.80 | 10.80 | 13.66 | 7.78 | 7.66 | 0.546 |
| tune | early | B_qb | 821 | 10.50 | 13.46 | 10.93 | 13.67 | 7.64 | 7.67 | 0.639 |
| tune | early | B_qb_noadj | 821 | 10.50 | 13.47 | 10.94 | 13.67 | 7.68 | 7.65 | 0.643 |
| tune | early | B_core | 821 | 10.53 | 13.49 | 10.97 | 13.72 | 7.67 | 7.69 | 0.641 |
| tune | early | N_naive_home | 821 | 11.59 | 14.83 | 11.18 | 13.98 | 8.02 | 8.38 | 0.505 |
| tune | final | A_market_raw | 821 | 10.22 | 13.12 | 10.63 | 13.26 | 7.53 | 7.29 | 0.645 |
| tune | final | A_market_cal | 821 | 10.23 | 13.13 | 10.65 | 13.27 | 7.53 | 7.29 | 0.645 |
| tune | final | B_qb | 821 | 10.41 | 13.34 | 10.79 | 13.50 | 7.55 | 7.53 | 0.648 |
| tune | final | B_qb_inj | 821 | 10.42 | 13.34 | 10.77 | 13.48 | 7.54 | 7.54 | 0.649 |
| tune | final | B_qb_noadj | 821 | 10.42 | 13.37 | 10.80 | 13.50 | 7.58 | 7.53 | 0.648 |
| tune | final | B_core | 821 | 10.53 | 13.49 | 10.97 | 13.72 | 7.67 | 7.69 | 0.638 |
| tune | final | N_naive_home | 821 | 11.59 | 14.83 | 11.18 | 13.98 | 8.02 | 8.38 | 0.505 |

## Paired differences (model a minus model b; negative = a better)

Season-week block bootstrap 95% intervals. Few independent seasons: treat as limited evidence.

| period | horizon | a | b | loss | n | mean diff | 95% CI |
|---|---|---|---|---|---|---|---|
| dev | early | B_qb | B_core | ae_margin | 854 | +0.002 | [-0.042, +0.046] |
| dev | early | B_qb | B_core | ae_total | 854 | -0.058 | [-0.152, +0.035] |
| dev | early | B_qb | B_core | se_margin | 854 | -0.009 | [-1.215, +1.092] |
| dev | early | B_qb | B_core | se_total | 854 | -2.735 | [-5.231, -0.263] |
| dev | early | B_qb_noadj | B_core | ae_margin | 854 | +0.019 | [-0.035, +0.069] |
| dev | early | B_qb_noadj | B_core | ae_total | 854 | -0.095 | [-0.202, +0.014] |
| dev | early | B_qb_noadj | B_core | se_margin | 854 | +0.559 | [-0.829, +1.937] |
| dev | early | B_qb_noadj | B_core | se_total | 854 | -2.426 | [-5.191, +0.433] |
| dev | early | N_naive_home | B_core | ae_margin | 854 | +0.827 | [+0.564, +1.085] |
| dev | early | N_naive_home | B_core | ae_total | 854 | +0.373 | [+0.117, +0.620] |
| dev | early | N_naive_home | B_core | se_margin | 854 | +25.326 | [+16.770, +33.478] |
| dev | early | N_naive_home | B_core | se_total | 854 | +10.031 | [+3.434, +16.956] |
| dev | early | B_core | N_naive_home | ae_margin | 854 | -0.827 | [-1.057, -0.553] |
| dev | early | B_core | N_naive_home | ae_total | 854 | -0.373 | [-0.622, -0.122] |
| dev | early | B_core | N_naive_home | se_margin | 854 | -25.326 | [-33.647, -16.780] |
| dev | early | B_core | N_naive_home | se_total | 854 | -10.031 | [-16.965, -2.769] |
| dev | final | A_market_cal | A_market_raw | ae_margin | 854 | +0.011 | [-0.002, +0.025] |
| dev | final | A_market_cal | A_market_raw | ae_total | 854 | +0.002 | [-0.008, +0.011] |
| dev | final | A_market_cal | A_market_raw | se_margin | 854 | +0.398 | [+0.095, +0.699] |
| dev | final | A_market_cal | A_market_raw | se_total | 854 | -0.154 | [-0.381, +0.070] |
| dev | final | B_core | A_market_raw | ae_margin | 854 | +0.309 | [+0.142, +0.474] |
| dev | final | B_core | A_market_raw | ae_total | 854 | +0.317 | [+0.134, +0.499] |
| dev | final | B_core | A_market_raw | se_margin | 854 | +9.341 | [+4.142, +14.588] |
| dev | final | B_core | A_market_raw | se_total | 854 | +8.873 | [+4.471, +13.433] |
| dev | final | B_qb | A_market_raw | ae_margin | 854 | +0.258 | [+0.117, +0.404] |
| dev | final | B_qb | A_market_raw | ae_total | 854 | +0.162 | [+0.012, +0.303] |
| dev | final | B_qb | A_market_raw | se_margin | 854 | +5.927 | [+1.815, +9.864] |
| dev | final | B_qb | A_market_raw | se_total | 854 | +4.535 | [+0.381, +8.837] |
| dev | final | B_qb_inj | A_market_raw | ae_margin | 854 | +0.241 | [+0.116, +0.376] |
| dev | final | B_qb_inj | A_market_raw | ae_total | 854 | +0.173 | [+0.028, +0.320] |
| dev | final | B_qb_inj | A_market_raw | se_margin | 854 | +5.143 | [+1.124, +8.788] |
| dev | final | B_qb_inj | A_market_raw | se_total | 854 | +4.823 | [+0.960, +8.819] |
| dev | final | B_qb_noadj | A_market_raw | ae_margin | 854 | +0.274 | [+0.135, +0.420] |
| dev | final | B_qb_noadj | A_market_raw | ae_total | 854 | +0.120 | [-0.035, +0.265] |
| dev | final | B_qb_noadj | A_market_raw | se_margin | 854 | +6.434 | [+2.292, +10.625] |
| dev | final | B_qb_noadj | A_market_raw | se_total | 854 | +4.838 | [+0.879, +8.714] |
| dev | final | N_naive_home | A_market_raw | ae_margin | 854 | +1.136 | [+0.823, +1.441] |
| dev | final | N_naive_home | A_market_raw | ae_total | 854 | +0.690 | [+0.406, +0.965] |
| dev | final | N_naive_home | A_market_raw | se_margin | 854 | +34.685 | [+24.208, +45.375] |
| dev | final | N_naive_home | A_market_raw | se_total | 854 | +18.889 | [+11.093, +27.374] |
| dev | final | A_market_cal | B_core | ae_margin | 854 | -0.298 | [-0.458, -0.139] |
| dev | final | A_market_cal | B_core | ae_total | 854 | -0.315 | [-0.494, -0.135] |
| dev | final | A_market_cal | B_core | se_margin | 854 | -8.943 | [-14.182, -3.738] |
| dev | final | A_market_cal | B_core | se_total | 854 | -9.026 | [-13.416, -4.523] |
| dev | final | A_market_raw | B_core | ae_margin | 854 | -0.309 | [-0.473, -0.150] |
| dev | final | A_market_raw | B_core | ae_total | 854 | -0.317 | [-0.501, -0.130] |
| dev | final | A_market_raw | B_core | se_margin | 854 | -9.341 | [-14.551, -4.039] |
| dev | final | A_market_raw | B_core | se_total | 854 | -8.873 | [-13.263, -4.386] |
| dev | final | B_qb | B_core | ae_margin | 854 | -0.051 | [-0.173, +0.063] |
| dev | final | B_qb | B_core | ae_total | 854 | -0.156 | [-0.282, -0.037] |
| dev | final | B_qb | B_core | se_margin | 854 | -3.414 | [-6.586, -0.498] |
| dev | final | B_qb | B_core | se_total | 854 | -4.338 | [-7.283, -1.554] |
| dev | final | B_qb_inj | B_core | ae_margin | 854 | -0.069 | [-0.205, +0.055] |
| dev | final | B_qb_inj | B_core | ae_total | 854 | -0.145 | [-0.267, -0.022] |
| dev | final | B_qb_inj | B_core | se_margin | 854 | -4.198 | [-8.153, -1.096] |
| dev | final | B_qb_inj | B_core | se_total | 854 | -4.049 | [-7.154, -1.209] |
| dev | final | B_qb_noadj | B_core | ae_margin | 854 | -0.035 | [-0.156, +0.085] |
| dev | final | B_qb_noadj | B_core | ae_total | 854 | -0.197 | [-0.332, -0.063] |
| dev | final | B_qb_noadj | B_core | se_margin | 854 | -2.907 | [-6.414, +0.127] |
| dev | final | B_qb_noadj | B_core | se_total | 854 | -4.035 | [-7.504, -0.868] |
| dev | final | N_naive_home | B_core | ae_margin | 854 | +0.827 | [+0.571, +1.072] |
| dev | final | N_naive_home | B_core | ae_total | 854 | +0.373 | [+0.111, +0.629] |
| dev | final | N_naive_home | B_core | se_margin | 854 | +25.344 | [+17.401, +33.341] |
| dev | final | N_naive_home | B_core | se_total | 854 | +10.016 | [+3.287, +16.959] |
| dev | final | B_core | N_naive_home | ae_margin | 854 | -0.827 | [-1.066, -0.570] |
| dev | final | B_core | N_naive_home | ae_total | 854 | -0.373 | [-0.627, -0.111] |
| dev | final | B_core | N_naive_home | se_margin | 854 | -25.344 | [-33.735, -17.034] |
| dev | final | B_core | N_naive_home | se_total | 854 | -10.016 | [-16.827, -3.508] |
| tune | early | B_qb | B_core | ae_margin | 821 | -0.030 | [-0.061, +0.002] |
| tune | early | B_qb | B_core | ae_total | 821 | -0.039 | [-0.093, +0.018] |
| tune | early | B_qb | B_core | se_margin | 821 | -0.774 | [-1.714, +0.108] |
| tune | early | B_qb | B_core | se_total | 821 | -1.484 | [-3.160, +0.237] |
| tune | early | B_qb_noadj | B_core | ae_margin | 821 | -0.024 | [-0.073, +0.024] |
| tune | early | B_qb_noadj | B_core | ae_total | 821 | -0.028 | [-0.108, +0.046] |
| tune | early | B_qb_noadj | B_core | se_margin | 821 | -0.485 | [-1.971, +1.031] |
| tune | early | B_qb_noadj | B_core | se_total | 821 | -1.371 | [-3.505, +0.830] |
| tune | early | N_naive_home | B_core | ae_margin | 821 | +1.065 | [+0.762, +1.347] |
| tune | early | N_naive_home | B_core | ae_total | 821 | +0.217 | [-0.028, +0.461] |
| tune | early | N_naive_home | B_core | se_margin | 821 | +37.913 | [+29.831, +46.140] |
| tune | early | N_naive_home | B_core | se_total | 821 | +7.238 | [-0.457, +14.878] |
| tune | early | B_core | N_naive_home | ae_margin | 821 | -1.065 | [-1.354, -0.776] |
| tune | early | B_core | N_naive_home | ae_total | 821 | -0.217 | [-0.455, +0.021] |
| tune | early | B_core | N_naive_home | se_margin | 821 | -37.913 | [-46.249, -29.833] |
| tune | early | B_core | N_naive_home | se_total | 821 | -7.238 | [-14.755, +0.037] |
| tune | final | A_market_cal | A_market_raw | ae_margin | 821 | +0.015 | [-0.009, +0.038] |
| tune | final | A_market_cal | A_market_raw | ae_total | 821 | +0.011 | [-0.004, +0.025] |
| tune | final | A_market_cal | A_market_raw | se_margin | 821 | +0.337 | [-0.246, +0.950] |
| tune | final | A_market_cal | A_market_raw | se_total | 821 | +0.291 | [-0.062, +0.659] |
| tune | final | B_core | A_market_raw | ae_margin | 821 | +0.308 | [+0.101, +0.511] |
| tune | final | B_core | A_market_raw | ae_total | 821 | +0.334 | [+0.156, +0.507] |
| tune | final | B_core | A_market_raw | se_margin | 821 | +9.995 | [+3.446, +16.604] |
| tune | final | B_core | A_market_raw | se_total | 821 | +12.443 | [+7.178, +17.782] |
| tune | final | B_qb | A_market_raw | ae_margin | 821 | +0.189 | [+0.042, +0.344] |
| tune | final | B_qb | A_market_raw | ae_total | 821 | +0.157 | [-0.000, +0.315] |
| tune | final | B_qb | A_market_raw | se_margin | 821 | +5.943 | [+1.154, +10.917] |
| tune | final | B_qb | A_market_raw | se_total | 821 | +6.494 | [+1.592, +11.168] |
| tune | final | B_qb_inj | A_market_raw | ae_margin | 821 | +0.195 | [+0.044, +0.352] |
| tune | final | B_qb_inj | A_market_raw | ae_total | 821 | +0.137 | [-0.026, +0.306] |
| tune | final | B_qb_inj | A_market_raw | se_margin | 821 | +5.981 | [+1.243, +10.874] |
| tune | final | B_qb_inj | A_market_raw | se_total | 821 | +5.896 | [+1.294, +10.771] |
| tune | final | B_qb_noadj | A_market_raw | ae_margin | 821 | +0.205 | [+0.034, +0.366] |
| tune | final | B_qb_noadj | A_market_raw | ae_total | 821 | +0.168 | [+0.001, +0.325] |
| tune | final | B_qb_noadj | A_market_raw | se_margin | 821 | +6.788 | [+2.093, +11.663] |
| tune | final | B_qb_noadj | A_market_raw | se_total | 821 | +6.378 | [+1.434, +11.433] |
| tune | final | N_naive_home | A_market_raw | ae_margin | 821 | +1.372 | [+0.991, +1.737] |
| tune | final | N_naive_home | A_market_raw | ae_total | 821 | +0.549 | [+0.291, +0.807] |
| tune | final | N_naive_home | A_market_raw | se_margin | 821 | +47.884 | [+36.019, +59.515] |
| tune | final | N_naive_home | A_market_raw | se_total | 821 | +19.656 | [+12.741, +26.353] |
| tune | final | A_market_cal | B_core | ae_margin | 821 | -0.293 | [-0.493, -0.108] |
| tune | final | A_market_cal | B_core | ae_total | 821 | -0.323 | [-0.498, -0.146] |
| tune | final | A_market_cal | B_core | se_margin | 821 | -9.658 | [-15.944, -3.582] |
| tune | final | A_market_cal | B_core | se_total | 821 | -12.152 | [-17.517, -6.913] |
| tune | final | A_market_raw | B_core | ae_margin | 821 | -0.308 | [-0.503, -0.103] |
| tune | final | A_market_raw | B_core | ae_total | 821 | -0.334 | [-0.512, -0.158] |
| tune | final | A_market_raw | B_core | se_margin | 821 | -9.995 | [-16.206, -3.465] |
| tune | final | A_market_raw | B_core | se_total | 821 | -12.443 | [-17.604, -7.380] |
| tune | final | B_qb | B_core | ae_margin | 821 | -0.118 | [-0.201, -0.032] |
| tune | final | B_qb | B_core | ae_total | 821 | -0.176 | [-0.282, -0.073] |
| tune | final | B_qb | B_core | se_margin | 821 | -4.052 | [-6.962, -1.317] |
| tune | final | B_qb | B_core | se_total | 821 | -5.949 | [-8.598, -3.275] |
| tune | final | B_qb_inj | B_core | ae_margin | 821 | -0.112 | [-0.200, -0.029] |
| tune | final | B_qb_inj | B_core | ae_total | 821 | -0.196 | [-0.315, -0.083] |
| tune | final | B_qb_inj | B_core | se_margin | 821 | -4.013 | [-7.124, -1.020] |
| tune | final | B_qb_inj | B_core | se_total | 821 | -6.547 | [-9.796, -3.425] |
| tune | final | B_qb_noadj | B_core | ae_margin | 821 | -0.103 | [-0.181, -0.018] |
| tune | final | B_qb_noadj | B_core | ae_total | 821 | -0.166 | [-0.267, -0.057] |
| tune | final | B_qb_noadj | B_core | se_margin | 821 | -3.207 | [-5.995, -0.400] |
| tune | final | B_qb_noadj | B_core | se_total | 821 | -6.065 | [-8.865, -3.265] |
| tune | final | N_naive_home | B_core | ae_margin | 821 | +1.065 | [+0.781, +1.338] |
| tune | final | N_naive_home | B_core | ae_total | 821 | +0.215 | [-0.018, +0.456] |
| tune | final | N_naive_home | B_core | se_margin | 821 | +37.890 | [+30.101, +45.604] |
| tune | final | N_naive_home | B_core | se_total | 821 | +7.213 | [-0.450, +14.815] |
| tune | final | B_core | N_naive_home | ae_margin | 821 | -1.065 | [-1.322, -0.777] |
| tune | final | B_core | N_naive_home | ae_total | 821 | -0.215 | [-0.446, +0.013] |
| tune | final | B_core | N_naive_home | se_margin | 821 | -37.890 | [-45.888, -29.870] |
| tune | final | B_core | N_naive_home | se_total | 821 | -7.213 | [-14.942, +0.588] |

## Per season

| horizon | model | season | n | margin MAE | total MAE | winner acc |
|---|---|---|---|---|---|---|
| early | N_naive_home | 2019 | 267 | 11.62 | 11.13 | 0.511 |
| early | N_naive_home | 2020 | 269 | 11.08 | 11.34 | 0.496 |
| early | N_naive_home | 2021 | 285 | 12.04 | 11.09 | 0.507 |
| early | N_naive_home | 2022 | 284 | 9.58 | 11.30 | 0.560 |
| early | N_naive_home | 2023 | 285 | 11.10 | 10.99 | 0.554 |
| early | N_naive_home | 2024 | 285 | 11.19 | 10.12 | 0.523 |
| early | B_core | 2019 | 267 | 10.43 | 10.96 | 0.643 |
| early | B_core | 2020 | 269 | 10.01 | 10.78 | 0.668 |
| early | B_core | 2021 | 285 | 11.11 | 11.15 | 0.613 |
| early | B_core | 2022 | 284 | 8.93 | 10.84 | 0.649 |
| early | B_core | 2023 | 285 | 10.33 | 10.56 | 0.621 |
| early | B_core | 2024 | 285 | 10.14 | 9.90 | 0.677 |
| early | B_qb | 2019 | 267 | 10.42 | 10.98 | 0.639 |
| early | B_qb | 2020 | 269 | 9.98 | 10.68 | 0.660 |
| early | B_qb | 2021 | 285 | 11.06 | 11.11 | 0.620 |
| early | B_qb | 2022 | 284 | 8.96 | 10.64 | 0.649 |
| early | B_qb | 2023 | 285 | 10.30 | 10.52 | 0.618 |
| early | B_qb | 2024 | 285 | 10.15 | 9.95 | 0.663 |
| early | B_qb_noadj | 2019 | 267 | 10.45 | 11.00 | 0.643 |
| early | B_qb_noadj | 2020 | 269 | 10.00 | 10.64 | 0.675 |
| early | B_qb_noadj | 2021 | 285 | 11.03 | 11.16 | 0.613 |
| early | B_qb_noadj | 2022 | 284 | 8.96 | 10.60 | 0.652 |
| early | B_qb_noadj | 2023 | 285 | 10.30 | 10.45 | 0.628 |
| early | B_qb_noadj | 2024 | 285 | 10.19 | 9.96 | 0.663 |
| final | N_naive_home | 2019 | 267 | 11.62 | 11.13 | 0.511 |
| final | N_naive_home | 2020 | 269 | 11.08 | 11.34 | 0.496 |
| final | N_naive_home | 2021 | 285 | 12.04 | 11.09 | 0.507 |
| final | N_naive_home | 2022 | 284 | 9.58 | 11.30 | 0.560 |
| final | N_naive_home | 2023 | 285 | 11.10 | 10.99 | 0.554 |
| final | N_naive_home | 2024 | 285 | 11.19 | 10.12 | 0.523 |
| final | B_core | 2019 | 267 | 10.43 | 10.96 | 0.635 |
| final | B_core | 2020 | 269 | 10.01 | 10.79 | 0.668 |
| final | B_core | 2021 | 285 | 11.11 | 11.15 | 0.613 |
| final | B_core | 2022 | 284 | 8.93 | 10.84 | 0.649 |
| final | B_core | 2023 | 285 | 10.33 | 10.55 | 0.621 |
| final | B_core | 2024 | 285 | 10.14 | 9.89 | 0.674 |
| final | B_qb | 2019 | 267 | 10.35 | 10.94 | 0.639 |
| final | B_qb | 2020 | 269 | 9.94 | 10.54 | 0.675 |
| final | B_qb | 2021 | 285 | 10.92 | 10.90 | 0.630 |
| final | B_qb | 2022 | 284 | 9.01 | 10.57 | 0.660 |
| final | B_qb | 2023 | 285 | 10.25 | 10.43 | 0.635 |
| final | B_qb | 2024 | 285 | 9.99 | 9.82 | 0.691 |
| final | B_qb_noadj | 2019 | 267 | 10.38 | 10.95 | 0.643 |
| final | B_qb_noadj | 2020 | 269 | 9.95 | 10.48 | 0.679 |
| final | B_qb_noadj | 2021 | 285 | 10.92 | 10.97 | 0.623 |
| final | B_qb_noadj | 2022 | 284 | 9.01 | 10.52 | 0.656 |
| final | B_qb_noadj | 2023 | 285 | 10.25 | 10.36 | 0.625 |
| final | B_qb_noadj | 2024 | 285 | 10.03 | 9.81 | 0.695 |
| final | B_qb_inj | 2019 | 267 | 10.34 | 10.92 | 0.635 |
| final | B_qb_inj | 2020 | 269 | 9.94 | 10.48 | 0.672 |
| final | B_qb_inj | 2021 | 285 | 10.94 | 10.91 | 0.641 |
| final | B_qb_inj | 2022 | 284 | 9.00 | 10.57 | 0.645 |
| final | B_qb_inj | 2023 | 285 | 10.23 | 10.46 | 0.660 |
| final | B_qb_inj | 2024 | 285 | 9.96 | 9.81 | 0.681 |
| final | A_market_raw | 2019 | 267 | 10.18 | 10.78 | 0.643 |
| final | A_market_raw | 2020 | 269 | 9.79 | 10.30 | 0.672 |
| final | A_market_raw | 2021 | 285 | 10.67 | 10.81 | 0.623 |
| final | A_market_raw | 2022 | 284 | 8.78 | 10.40 | 0.663 |
| final | A_market_raw | 2023 | 285 | 9.98 | 10.17 | 0.674 |
| final | A_market_raw | 2024 | 285 | 9.70 | 9.77 | 0.705 |
| final | A_market_cal | 2019 | 267 | 10.22 | 10.79 | 0.643 |
| final | A_market_cal | 2020 | 269 | 9.80 | 10.30 | 0.672 |
| final | A_market_cal | 2021 | 285 | 10.66 | 10.84 | 0.623 |
| final | A_market_cal | 2022 | 284 | 8.81 | 10.41 | 0.663 |
| final | A_market_cal | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | A_market_cal | 2024 | 285 | 9.71 | 9.76 | 0.705 |

## Subgroups, dev period (prespecified; small groups are exploratory)

| horizon | model | group | n | margin MAE | total MAE | exploratory |
|---|---|---|---|---|---|---|
| early | N_naive_home | weeks_1_4 | 192 | 10.70 | 10.74 |  |
| early | N_naive_home | weeks_5_plus_reg | 623 | 10.56 | 10.84 |  |
| early | N_naive_home | playoffs | 39 | 11.38 | 10.44 | yes |
| early | N_naive_home | neutral_site | 20 | 9.20 | 9.66 | yes |
| early | N_naive_home | expected_qb_changed | 158 | 10.64 | 10.74 |  |
| early | B_core | weeks_1_4 | 192 | 10.09 | 10.11 |  |
| early | B_core | weeks_5_plus_reg | 623 | 9.64 | 10.53 |  |
| early | B_core | playoffs | 39 | 10.89 | 10.35 | yes |
| early | B_core | neutral_site | 20 | 9.09 | 8.54 | yes |
| early | B_core | expected_qb_changed | 158 | 9.56 | 10.39 |  |
| early | B_qb | weeks_1_4 | 192 | 10.08 | 10.13 |  |
| early | B_qb | weeks_5_plus_reg | 623 | 9.65 | 10.47 |  |
| early | B_qb | playoffs | 39 | 10.89 | 9.90 | yes |
| early | B_qb | neutral_site | 20 | 9.04 | 8.44 | yes |
| early | B_qb | expected_qb_changed | 158 | 9.45 | 10.37 |  |
| early | B_qb_noadj | weeks_1_4 | 192 | 10.06 | 10.11 |  |
| early | B_qb_noadj | weeks_5_plus_reg | 623 | 9.68 | 10.43 |  |
| early | B_qb_noadj | playoffs | 39 | 10.92 | 9.91 | yes |
| early | B_qb_noadj | neutral_site | 20 | 9.02 | 8.40 | yes |
| early | B_qb_noadj | expected_qb_changed | 158 | 9.49 | 10.35 |  |
| final | N_naive_home | weeks_1_4 | 192 | 10.70 | 10.74 |  |
| final | N_naive_home | weeks_5_plus_reg | 623 | 10.56 | 10.84 |  |
| final | N_naive_home | playoffs | 39 | 11.38 | 10.44 | yes |
| final | N_naive_home | neutral_site | 20 | 9.20 | 9.66 | yes |
| final | N_naive_home | expected_qb_changed | 200 | 10.86 | 10.86 |  |
| final | B_core | weeks_1_4 | 192 | 10.09 | 10.11 |  |
| final | B_core | weeks_5_plus_reg | 623 | 9.64 | 10.53 |  |
| final | B_core | playoffs | 39 | 10.88 | 10.35 | yes |
| final | B_core | neutral_site | 20 | 9.09 | 8.53 | yes |
| final | B_core | expected_qb_changed | 200 | 10.11 | 10.56 |  |
| final | B_qb | weeks_1_4 | 192 | 10.13 | 10.08 |  |
| final | B_qb | weeks_5_plus_reg | 623 | 9.55 | 10.34 |  |
| final | B_qb | playoffs | 39 | 11.01 | 10.10 | yes |
| final | B_qb | neutral_site | 20 | 9.03 | 8.43 | yes |
| final | B_qb | expected_qb_changed | 200 | 9.77 | 9.98 |  |
| final | B_qb_noadj | weeks_1_4 | 192 | 10.13 | 10.05 |  |
| final | B_qb_noadj | weeks_5_plus_reg | 623 | 9.57 | 10.30 |  |
| final | B_qb_noadj | playoffs | 39 | 11.05 | 10.07 | yes |
| final | B_qb_noadj | neutral_site | 20 | 9.04 | 8.40 | yes |
| final | B_qb_noadj | expected_qb_changed | 200 | 9.82 | 9.96 |  |
| final | B_qb_inj | weeks_1_4 | 192 | 10.16 | 10.07 |  |
| final | B_qb_inj | weeks_5_plus_reg | 623 | 9.52 | 10.37 |  |
| final | B_qb_inj | playoffs | 39 | 10.94 | 10.05 | yes |
| final | B_qb_inj | neutral_site | 20 | 8.91 | 8.36 | yes |
| final | B_qb_inj | expected_qb_changed | 200 | 9.72 | 10.06 |  |
| final | A_market_raw | weeks_1_4 | 192 | 10.06 | 10.03 |  |
| final | A_market_raw | weeks_5_plus_reg | 623 | 9.22 | 10.15 |  |
| final | A_market_raw | playoffs | 39 | 11.01 | 9.91 | yes |
| final | A_market_raw | neutral_site | 20 | 8.47 | 8.80 | yes |
| final | A_market_raw | expected_qb_changed | 200 | 9.68 | 9.93 |  |
| final | A_market_cal | weeks_1_4 | 192 | 10.07 | 10.05 |  |
| final | A_market_cal | weeks_5_plus_reg | 623 | 9.23 | 10.15 |  |
| final | A_market_cal | playoffs | 39 | 11.02 | 9.92 | yes |
| final | A_market_cal | neutral_site | 20 | 8.46 | 8.80 | yes |
| final | A_market_cal | expected_qb_changed | 200 | 9.71 | 9.93 |  |

## Fold details

```json
{
 "folds": [
  {
   "horizon": "early",
   "fold": 2019,
   "n_train": 801,
   "n_test": 267,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0
   }
  },
  {
   "horizon": "early",
   "fold": 2020,
   "n_train": 1068,
   "n_test": 269,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0
   }
  },
  {
   "horizon": "early",
   "fold": 2021,
   "n_train": 1337,
   "n_test": 285,
   "alphas": {
    "B_core": 3000.0,
    "B_qb": 3000.0,
    "B_qb_noadj": 1000.0
   }
  },
  {
   "horizon": "early",
   "fold": 2022,
   "n_train": 1622,
   "n_test": 284,
   "alphas": {
    "B_core": 3000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0
   }
  },
  {
   "horizon": "early",
   "fold": 2023,
   "n_train": 1906,
   "n_test": 285,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0
   }
  },
  {
   "horizon": "early",
   "fold": 2024,
   "n_train": 2191,
   "n_test": 285,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0
   }
  },
  {
   "horizon": "final",
   "fold": 2019,
   "n_train": 801,
   "n_test": 267,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0,
    "B_qb_inj": 1000.0
   },
   "market_rows_test": 267,
   "A_cal_params": {
    "margin_intercept": 0.2714332281373468,
    "margin_slope": 1.009921527715767,
    "total_intercept": -1.107805616630536,
    "total_slope": 1.0202486943816753
   }
  },
  {
   "horizon": "final",
   "fold": 2020,
   "n_train": 1068,
   "n_test": 269,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0,
    "B_qb_inj": 1000.0
   },
   "market_rows_test": 269,
   "A_cal_params": {
    "margin_intercept": -0.3131370526446391,
    "margin_slope": 1.0304095915217468,
    "total_intercept": -0.15667839919503024,
    "total_slope": 1.0030162948909653
   }
  },
  {
   "horizon": "final",
   "fold": 2021,
   "n_train": 1337,
   "n_test": 285,
   "alphas": {
    "B_core": 3000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0,
    "B_qb_inj": 1000.0
   },
   "market_rows_test": 285,
   "A_cal_params": {
    "margin_intercept": -0.4238922732118018,
    "margin_slope": 1.0173469735624494,
    "total_intercept": -1.7024676035908186,
    "total_slope": 1.0424531162064488
   }
  },
  {
   "horizon": "final",
   "fold": 2022,
   "n_train": 1622,
   "n_test": 284,
   "alphas": {
    "B_core": 3000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0,
    "B_qb_inj": 1000.0
   },
   "market_rows_test": 284,
   "A_cal_params": {
    "margin_intercept": -0.3372140492370519,
    "margin_slope": 1.0186881736489692,
    "total_intercept": -0.3791273355051885,
    "total_slope": 1.0108706410863275
   }
  },
  {
   "horizon": "final",
   "fold": 2023,
   "n_train": 1906,
   "n_test": 285,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0,
    "B_qb_inj": 1000.0
   },
   "market_rows_test": 285,
   "A_cal_params": {
    "margin_intercept": -0.19669998553214119,
    "margin_slope": 0.9913842008521099,
    "total_intercept": -0.12022426750792903,
    "total_slope": 1.0042802601952003
   }
  },
  {
   "horizon": "final",
   "fold": 2024,
   "n_train": 2191,
   "n_test": 285,
   "alphas": {
    "B_core": 1000.0,
    "B_qb": 1000.0,
    "B_qb_noadj": 1000.0,
    "B_qb_inj": 1000.0
   },
   "market_rows_test": 285,
   "A_cal_params": {
    "margin_intercept": -0.027850388525439973,
    "margin_slope": 0.9944984920419533,
    "total_intercept": 0.7895283444290158,
    "total_slope": 0.9860085794495842
   }
  }
 ]
}
```