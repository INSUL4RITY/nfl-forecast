# Backtest report `bt_20260924T234406Z`

Generated 2026-09-24T23:44:06.276207+00:00 (UTC). Code hash `5adea321aa0a`. Folds (walk-forward, expanding window): [2019, 2020, 2021, 2022, 2023, 2024]. Locked test season 2025 not evaluated.

All numbers below were produced by `python -m nflcast backtest` on real nflverse data. Lower is better for MAE/RMSE. Historical market lines are the single nflverse schedule line (timing unknown, treated as approximately closing), so market comparisons apply only to the final-pregame horizon.

Periods: `tune` = seasons used to make modelling choices (feature sets, settings); `dev` = walk-forward development report seasons.

## Overall (pooled over folds)

| period | horizon | model | n | margin MAE | margin RMSE | total MAE | total RMSE | home MAE | away MAE | winner acc |
|---|---|---|---|---|---|---|---|---|---|---|
| dev | early | B_qb | 854 | 9.80 | 12.85 | 10.37 | 13.19 | 7.35 | 7.22 | 0.643 |
| dev | early | B_core | 854 | 9.80 | 12.85 | 10.43 | 13.29 | 7.36 | 7.26 | 0.649 |
| dev | early | B_qb_noadj | 854 | 9.82 | 12.87 | 10.33 | 13.20 | 7.36 | 7.20 | 0.648 |
| dev | early | N_naive_home | 854 | 10.63 | 13.80 | 10.80 | 13.66 | 7.78 | 7.66 | 0.546 |
| dev | final | C_resid_nopersonnel | 854 | 9.48 | 12.47 | 10.12 | 12.91 | 7.16 | 7.05 | 0.680 |
| dev | final | C_resid_noinj | 854 | 9.48 | 12.47 | 10.11 | 12.90 | 7.16 | 7.05 | 0.681 |
| dev | final | C_resid | 854 | 9.49 | 12.48 | 10.12 | 12.90 | 7.17 | 7.05 | 0.681 |
| dev | final | A_market_raw | 854 | 9.49 | 12.48 | 10.11 | 12.95 | 7.19 | 7.03 | 0.681 |
| dev | final | A_market_cal | 854 | 9.50 | 12.50 | 10.11 | 12.95 | 7.19 | 7.04 | 0.681 |
| dev | final | C_direct | 854 | 9.56 | 12.53 | 10.21 | 13.00 | 7.22 | 7.08 | 0.682 |
| dev | final | C_resid_hgb | 854 | 9.59 | 12.61 | 10.06 | 12.92 | 7.20 | 7.10 | 0.681 |
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
| tune | final | C_resid_nopersonnel | 821 | 10.23 | 13.13 | 10.64 | 13.27 | 7.52 | 7.30 | 0.645 |
| tune | final | C_resid_noinj | 821 | 10.23 | 13.13 | 10.64 | 13.27 | 7.53 | 7.30 | 0.645 |
| tune | final | A_market_cal | 821 | 10.23 | 13.13 | 10.65 | 13.27 | 7.53 | 7.29 | 0.645 |
| tune | final | C_resid | 821 | 10.23 | 13.13 | 10.64 | 13.27 | 7.52 | 7.30 | 0.645 |
| tune | final | C_direct | 821 | 10.27 | 13.18 | 10.73 | 13.43 | 7.52 | 7.44 | 0.652 |
| tune | final | C_resid_hgb | 821 | 10.27 | 13.21 | 10.86 | 13.57 | 7.63 | 7.35 | 0.656 |
| tune | final | B_qb | 821 | 10.41 | 13.34 | 10.79 | 13.50 | 7.55 | 7.53 | 0.648 |
| tune | final | B_qb_inj | 821 | 10.42 | 13.34 | 10.77 | 13.48 | 7.54 | 7.54 | 0.649 |
| tune | final | B_qb_noadj | 821 | 10.42 | 13.37 | 10.80 | 13.50 | 7.58 | 7.53 | 0.648 |
| tune | final | B_core | 821 | 10.53 | 13.49 | 10.97 | 13.72 | 7.67 | 7.69 | 0.638 |
| tune | final | N_naive_home | 821 | 11.59 | 14.83 | 11.18 | 13.98 | 8.02 | 8.38 | 0.505 |

## Paired differences (model a minus model b; negative = a better)

Season-week block bootstrap 95% intervals. Few independent seasons: treat as limited evidence.

| period | horizon | a | b | loss | n | mean diff | 95% CI |
|---|---|---|---|---|---|---|---|
| dev | early | B_qb | B_core | ae_margin | 854 | +0.002 | [-0.044, +0.044] |
| dev | early | B_qb | B_core | ae_total | 854 | -0.058 | [-0.153, +0.036] |
| dev | early | B_qb | B_core | se_margin | 854 | -0.009 | [-1.100, +1.146] |
| dev | early | B_qb | B_core | se_total | 854 | -2.735 | [-5.212, -0.207] |
| dev | early | B_qb_noadj | B_core | ae_margin | 854 | +0.019 | [-0.032, +0.071] |
| dev | early | B_qb_noadj | B_core | ae_total | 854 | -0.095 | [-0.208, +0.016] |
| dev | early | B_qb_noadj | B_core | se_margin | 854 | +0.559 | [-0.834, +1.970] |
| dev | early | B_qb_noadj | B_core | se_total | 854 | -2.426 | [-5.169, +0.467] |
| dev | early | N_naive_home | B_core | ae_margin | 854 | +0.827 | [+0.578, +1.077] |
| dev | early | N_naive_home | B_core | ae_total | 854 | +0.373 | [+0.107, +0.630] |
| dev | early | N_naive_home | B_core | se_margin | 854 | +25.326 | [+17.051, +34.317] |
| dev | early | N_naive_home | B_core | se_total | 854 | +10.031 | [+3.123, +16.796] |
| dev | early | B_core | N_naive_home | ae_margin | 854 | -0.827 | [-1.071, -0.584] |
| dev | early | B_core | N_naive_home | ae_total | 854 | -0.373 | [-0.627, -0.116] |
| dev | early | B_core | N_naive_home | se_margin | 854 | -25.326 | [-33.824, -17.129] |
| dev | early | B_core | N_naive_home | se_total | 854 | -10.031 | [-16.882, -3.152] |
| dev | final | A_market_cal | A_market_raw | ae_margin | 854 | +0.011 | [-0.002, +0.025] |
| dev | final | A_market_cal | A_market_raw | ae_total | 854 | +0.002 | [-0.008, +0.012] |
| dev | final | A_market_cal | A_market_raw | se_margin | 854 | +0.398 | [+0.068, +0.702] |
| dev | final | A_market_cal | A_market_raw | se_total | 854 | -0.154 | [-0.392, +0.068] |
| dev | final | B_core | A_market_raw | ae_margin | 854 | +0.309 | [+0.144, +0.479] |
| dev | final | B_core | A_market_raw | ae_total | 854 | +0.317 | [+0.127, +0.501] |
| dev | final | B_core | A_market_raw | se_margin | 854 | +9.341 | [+4.068, +14.617] |
| dev | final | B_core | A_market_raw | se_total | 854 | +8.873 | [+4.350, +13.391] |
| dev | final | B_qb | A_market_raw | ae_margin | 854 | +0.258 | [+0.115, +0.389] |
| dev | final | B_qb | A_market_raw | ae_total | 854 | +0.162 | [+0.020, +0.303] |
| dev | final | B_qb | A_market_raw | se_margin | 854 | +5.927 | [+1.670, +9.905] |
| dev | final | B_qb | A_market_raw | se_total | 854 | +4.535 | [+0.291, +8.560] |
| dev | final | B_qb_inj | A_market_raw | ae_margin | 854 | +0.241 | [+0.114, +0.369] |
| dev | final | B_qb_inj | A_market_raw | ae_total | 854 | +0.173 | [+0.035, +0.321] |
| dev | final | B_qb_inj | A_market_raw | se_margin | 854 | +5.143 | [+1.140, +8.934] |
| dev | final | B_qb_inj | A_market_raw | se_total | 854 | +4.823 | [+0.974, +8.851] |
| dev | final | B_qb_noadj | A_market_raw | ae_margin | 854 | +0.274 | [+0.137, +0.410] |
| dev | final | B_qb_noadj | A_market_raw | ae_total | 854 | +0.120 | [-0.024, +0.269] |
| dev | final | B_qb_noadj | A_market_raw | se_margin | 854 | +6.434 | [+2.127, +10.624] |
| dev | final | B_qb_noadj | A_market_raw | se_total | 854 | +4.838 | [+0.915, +8.711] |
| dev | final | C_direct | A_market_raw | ae_margin | 854 | +0.068 | [-0.003, +0.140] |
| dev | final | C_direct | A_market_raw | ae_total | 854 | +0.095 | [-0.020, +0.204] |
| dev | final | C_direct | A_market_raw | se_margin | 854 | +1.265 | [-0.751, +3.113] |
| dev | final | C_direct | A_market_raw | se_total | 854 | +1.227 | [-1.624, +4.045] |
| dev | final | C_resid | A_market_raw | ae_margin | 854 | -0.005 | [-0.023, +0.014] |
| dev | final | C_resid | A_market_raw | ae_total | 854 | +0.004 | [-0.080, +0.090] |
| dev | final | C_resid | A_market_raw | se_margin | 854 | -0.069 | [-0.497, +0.355] |
| dev | final | C_resid | A_market_raw | se_total | 854 | -1.366 | [-3.383, +0.796] |
| dev | final | C_resid_hgb | A_market_raw | ae_margin | 854 | +0.095 | [-0.024, +0.217] |
| dev | final | C_resid_hgb | A_market_raw | ae_total | 854 | -0.047 | [-0.179, +0.086] |
| dev | final | C_resid_hgb | A_market_raw | se_margin | 854 | +3.250 | [+0.382, +6.334] |
| dev | final | C_resid_hgb | A_market_raw | se_total | 854 | -0.975 | [-4.612, +2.764] |
| dev | final | C_resid_noinj | A_market_raw | ae_margin | 854 | -0.008 | [-0.034, +0.018] |
| dev | final | C_resid_noinj | A_market_raw | ae_total | 854 | -0.004 | [-0.096, +0.082] |
| dev | final | C_resid_noinj | A_market_raw | se_margin | 854 | -0.197 | [-0.839, +0.376] |
| dev | final | C_resid_noinj | A_market_raw | se_total | 854 | -1.508 | [-3.774, +0.746] |
| dev | final | C_resid_nopersonnel | A_market_raw | ae_margin | 854 | -0.008 | [-0.044, +0.031] |
| dev | final | C_resid_nopersonnel | A_market_raw | ae_total | 854 | +0.013 | [-0.050, +0.075] |
| dev | final | C_resid_nopersonnel | A_market_raw | se_margin | 854 | -0.217 | [-1.349, +0.774] |
| dev | final | C_resid_nopersonnel | A_market_raw | se_total | 854 | -1.037 | [-2.710, +0.818] |
| dev | final | N_naive_home | A_market_raw | ae_margin | 854 | +1.136 | [+0.825, +1.449] |
| dev | final | N_naive_home | A_market_raw | ae_total | 854 | +0.690 | [+0.403, +0.968] |
| dev | final | N_naive_home | A_market_raw | se_margin | 854 | +34.685 | [+24.444, +45.062] |
| dev | final | N_naive_home | A_market_raw | se_total | 854 | +18.889 | [+10.895, +26.843] |
| dev | final | A_market_cal | B_core | ae_margin | 854 | -0.298 | [-0.451, -0.138] |
| dev | final | A_market_cal | B_core | ae_total | 854 | -0.315 | [-0.500, -0.127] |
| dev | final | A_market_cal | B_core | se_margin | 854 | -8.943 | [-14.123, -3.721] |
| dev | final | A_market_cal | B_core | se_total | 854 | -9.026 | [-13.581, -4.396] |
| dev | final | A_market_raw | B_core | ae_margin | 854 | -0.309 | [-0.475, -0.145] |
| dev | final | A_market_raw | B_core | ae_total | 854 | -0.317 | [-0.508, -0.139] |
| dev | final | A_market_raw | B_core | se_margin | 854 | -9.341 | [-14.855, -4.428] |
| dev | final | A_market_raw | B_core | se_total | 854 | -8.873 | [-13.349, -4.508] |
| dev | final | B_qb | B_core | ae_margin | 854 | -0.051 | [-0.173, +0.060] |
| dev | final | B_qb | B_core | ae_total | 854 | -0.156 | [-0.279, -0.032] |
| dev | final | B_qb | B_core | se_margin | 854 | -3.414 | [-6.919, -0.574] |
| dev | final | B_qb | B_core | se_total | 854 | -4.338 | [-7.254, -1.359] |
| dev | final | B_qb_inj | B_core | ae_margin | 854 | -0.069 | [-0.216, +0.055] |
| dev | final | B_qb_inj | B_core | ae_total | 854 | -0.145 | [-0.266, -0.020] |
| dev | final | B_qb_inj | B_core | se_margin | 854 | -4.198 | [-8.046, -1.037] |
| dev | final | B_qb_inj | B_core | se_total | 854 | -4.049 | [-7.026, -1.162] |
| dev | final | B_qb_noadj | B_core | ae_margin | 854 | -0.035 | [-0.154, +0.082] |
| dev | final | B_qb_noadj | B_core | ae_total | 854 | -0.197 | [-0.339, -0.057] |
| dev | final | B_qb_noadj | B_core | se_margin | 854 | -2.907 | [-6.311, +0.214] |
| dev | final | B_qb_noadj | B_core | se_total | 854 | -4.035 | [-7.278, -0.642] |
| dev | final | C_direct | B_core | ae_margin | 854 | -0.242 | [-0.427, -0.076] |
| dev | final | C_direct | B_core | ae_total | 854 | -0.223 | [-0.377, -0.056] |
| dev | final | C_direct | B_core | se_margin | 854 | -8.076 | [-13.474, -3.333] |
| dev | final | C_direct | B_core | se_total | 854 | -7.646 | [-11.411, -3.945] |
| dev | final | C_resid | B_core | ae_margin | 854 | -0.314 | [-0.473, -0.164] |
| dev | final | C_resid | B_core | ae_total | 854 | -0.313 | [-0.521, -0.103] |
| dev | final | C_resid | B_core | se_margin | 854 | -9.410 | [-14.762, -4.133] |
| dev | final | C_resid | B_core | se_total | 854 | -10.238 | [-15.030, -5.542] |
| dev | final | C_resid_hgb | B_core | ae_margin | 854 | -0.214 | [-0.412, -0.012] |
| dev | final | C_resid_hgb | B_core | ae_total | 854 | -0.364 | [-0.603, -0.148] |
| dev | final | C_resid_hgb | B_core | se_margin | 854 | -6.091 | [-12.074, -0.436] |
| dev | final | C_resid_hgb | B_core | se_total | 854 | -9.848 | [-15.608, -3.937] |
| dev | final | C_resid_noinj | B_core | ae_margin | 854 | -0.317 | [-0.485, -0.149] |
| dev | final | C_resid_noinj | B_core | ae_total | 854 | -0.321 | [-0.533, -0.112] |
| dev | final | C_resid_noinj | B_core | se_margin | 854 | -9.538 | [-14.796, -4.350] |
| dev | final | C_resid_noinj | B_core | se_total | 854 | -10.381 | [-15.547, -5.466] |
| dev | final | C_resid_nopersonnel | B_core | ae_margin | 854 | -0.317 | [-0.487, -0.151] |
| dev | final | C_resid_nopersonnel | B_core | ae_total | 854 | -0.305 | [-0.499, -0.111] |
| dev | final | C_resid_nopersonnel | B_core | se_margin | 854 | -9.558 | [-14.590, -4.627] |
| dev | final | C_resid_nopersonnel | B_core | se_total | 854 | -9.910 | [-14.406, -5.270] |
| dev | final | N_naive_home | B_core | ae_margin | 854 | +0.827 | [+0.566, +1.080] |
| dev | final | N_naive_home | B_core | ae_total | 854 | +0.373 | [+0.112, +0.624] |
| dev | final | N_naive_home | B_core | se_margin | 854 | +25.344 | [+17.035, +33.650] |
| dev | final | N_naive_home | B_core | se_total | 854 | +10.016 | [+3.572, +16.967] |
| dev | final | B_core | N_naive_home | ae_margin | 854 | -0.827 | [-1.083, -0.580] |
| dev | final | B_core | N_naive_home | ae_total | 854 | -0.373 | [-0.639, -0.125] |
| dev | final | B_core | N_naive_home | se_margin | 854 | -25.344 | [-34.091, -17.342] |
| dev | final | B_core | N_naive_home | se_total | 854 | -10.016 | [-16.970, -3.078] |
| tune | early | B_qb | B_core | ae_margin | 821 | -0.030 | [-0.061, +0.002] |
| tune | early | B_qb | B_core | ae_total | 821 | -0.039 | [-0.093, +0.017] |
| tune | early | B_qb | B_core | se_margin | 821 | -0.774 | [-1.671, +0.144] |
| tune | early | B_qb | B_core | se_total | 821 | -1.484 | [-3.014, +0.174] |
| tune | early | B_qb_noadj | B_core | ae_margin | 821 | -0.024 | [-0.075, +0.023] |
| tune | early | B_qb_noadj | B_core | ae_total | 821 | -0.028 | [-0.107, +0.047] |
| tune | early | B_qb_noadj | B_core | se_margin | 821 | -0.485 | [-1.986, +1.045] |
| tune | early | B_qb_noadj | B_core | se_total | 821 | -1.371 | [-3.541, +0.887] |
| tune | early | N_naive_home | B_core | ae_margin | 821 | +1.065 | [+0.787, +1.343] |
| tune | early | N_naive_home | B_core | ae_total | 821 | +0.217 | [-0.018, +0.454] |
| tune | early | N_naive_home | B_core | se_margin | 821 | +37.913 | [+30.054, +45.743] |
| tune | early | N_naive_home | B_core | se_total | 821 | +7.238 | [-0.181, +14.619] |
| tune | early | B_core | N_naive_home | ae_margin | 821 | -1.065 | [-1.354, -0.779] |
| tune | early | B_core | N_naive_home | ae_total | 821 | -0.217 | [-0.460, +0.021] |
| tune | early | B_core | N_naive_home | se_margin | 821 | -37.913 | [-46.270, -29.708] |
| tune | early | B_core | N_naive_home | se_total | 821 | -7.238 | [-14.614, +0.705] |
| tune | final | A_market_cal | A_market_raw | ae_margin | 821 | +0.015 | [-0.008, +0.039] |
| tune | final | A_market_cal | A_market_raw | ae_total | 821 | +0.011 | [-0.003, +0.026] |
| tune | final | A_market_cal | A_market_raw | se_margin | 821 | +0.337 | [-0.269, +0.922] |
| tune | final | A_market_cal | A_market_raw | se_total | 821 | +0.291 | [-0.070, +0.680] |
| tune | final | B_core | A_market_raw | ae_margin | 821 | +0.308 | [+0.112, +0.504] |
| tune | final | B_core | A_market_raw | ae_total | 821 | +0.334 | [+0.162, +0.510] |
| tune | final | B_core | A_market_raw | se_margin | 821 | +9.995 | [+3.774, +16.278] |
| tune | final | B_core | A_market_raw | se_total | 821 | +12.443 | [+7.163, +17.675] |
| tune | final | B_qb | A_market_raw | ae_margin | 821 | +0.189 | [+0.025, +0.349] |
| tune | final | B_qb | A_market_raw | ae_total | 821 | +0.157 | [+0.009, +0.318] |
| tune | final | B_qb | A_market_raw | se_margin | 821 | +5.943 | [+1.343, +10.923] |
| tune | final | B_qb | A_market_raw | se_total | 821 | +6.494 | [+1.799, +11.182] |
| tune | final | B_qb_inj | A_market_raw | ae_margin | 821 | +0.195 | [+0.029, +0.354] |
| tune | final | B_qb_inj | A_market_raw | ae_total | 821 | +0.137 | [-0.036, +0.300] |
| tune | final | B_qb_inj | A_market_raw | se_margin | 821 | +5.981 | [+1.152, +10.740] |
| tune | final | B_qb_inj | A_market_raw | se_total | 821 | +5.896 | [+1.161, +10.859] |
| tune | final | B_qb_noadj | A_market_raw | ae_margin | 821 | +0.205 | [+0.039, +0.364] |
| tune | final | B_qb_noadj | A_market_raw | ae_total | 821 | +0.168 | [+0.008, +0.330] |
| tune | final | B_qb_noadj | A_market_raw | se_margin | 821 | +6.788 | [+2.016, +11.621] |
| tune | final | B_qb_noadj | A_market_raw | se_total | 821 | +6.378 | [+1.366, +11.375] |
| tune | final | C_direct | A_market_raw | ae_margin | 821 | +0.054 | [-0.048, +0.155] |
| tune | final | C_direct | A_market_raw | ae_total | 821 | +0.100 | [-0.030, +0.233] |
| tune | final | C_direct | A_market_raw | se_margin | 821 | +1.708 | [-1.291, +4.488] |
| tune | final | C_direct | A_market_raw | se_total | 821 | +4.440 | [+0.691, +8.442] |
| tune | final | C_resid | A_market_raw | ae_margin | 821 | +0.008 | [-0.025, +0.041] |
| tune | final | C_resid | A_market_raw | ae_total | 821 | +0.008 | [-0.008, +0.024] |
| tune | final | C_resid | A_market_raw | se_margin | 821 | +0.347 | [-0.531, +1.202] |
| tune | final | C_resid | A_market_raw | se_total | 821 | +0.179 | [-0.217, +0.560] |
| tune | final | C_resid_hgb | A_market_raw | ae_margin | 821 | +0.048 | [-0.088, +0.176] |
| tune | final | C_resid_hgb | A_market_raw | ae_total | 821 | +0.226 | [+0.050, +0.385] |
| tune | final | C_resid_hgb | A_market_raw | se_margin | 821 | +2.374 | [-0.937, +5.570] |
| tune | final | C_resid_hgb | A_market_raw | se_total | 821 | +8.204 | [+3.856, +12.884] |
| tune | final | C_resid_noinj | A_market_raw | ae_margin | 821 | +0.009 | [-0.015, +0.035] |
| tune | final | C_resid_noinj | A_market_raw | ae_total | 821 | +0.008 | [-0.007, +0.024] |
| tune | final | C_resid_noinj | A_market_raw | se_margin | 821 | +0.320 | [-0.313, +0.994] |
| tune | final | C_resid_noinj | A_market_raw | se_total | 821 | +0.172 | [-0.215, +0.539] |
| tune | final | C_resid_nopersonnel | A_market_raw | ae_margin | 821 | +0.006 | [-0.027, +0.037] |
| tune | final | C_resid_nopersonnel | A_market_raw | ae_total | 821 | +0.007 | [-0.009, +0.021] |
| tune | final | C_resid_nopersonnel | A_market_raw | se_margin | 821 | +0.297 | [-0.569, +1.104] |
| tune | final | C_resid_nopersonnel | A_market_raw | se_total | 821 | +0.171 | [-0.195, +0.516] |
| tune | final | N_naive_home | A_market_raw | ae_margin | 821 | +1.372 | [+0.981, +1.749] |
| tune | final | N_naive_home | A_market_raw | ae_total | 821 | +0.549 | [+0.286, +0.803] |
| tune | final | N_naive_home | A_market_raw | se_margin | 821 | +47.884 | [+36.298, +59.668] |
| tune | final | N_naive_home | A_market_raw | se_total | 821 | +19.656 | [+12.578, +25.972] |
| tune | final | A_market_cal | B_core | ae_margin | 821 | -0.293 | [-0.484, -0.086] |
| tune | final | A_market_cal | B_core | ae_total | 821 | -0.323 | [-0.506, -0.144] |
| tune | final | A_market_cal | B_core | se_margin | 821 | -9.658 | [-15.863, -3.450] |
| tune | final | A_market_cal | B_core | se_total | 821 | -12.152 | [-17.415, -7.090] |
| tune | final | A_market_raw | B_core | ae_margin | 821 | -0.308 | [-0.506, -0.106] |
| tune | final | A_market_raw | B_core | ae_total | 821 | -0.334 | [-0.508, -0.169] |
| tune | final | A_market_raw | B_core | se_margin | 821 | -9.995 | [-16.498, -3.687] |
| tune | final | A_market_raw | B_core | se_total | 821 | -12.443 | [-17.493, -7.392] |
| tune | final | B_qb | B_core | ae_margin | 821 | -0.118 | [-0.200, -0.034] |
| tune | final | B_qb | B_core | ae_total | 821 | -0.176 | [-0.278, -0.064] |
| tune | final | B_qb | B_core | se_margin | 821 | -4.052 | [-7.038, -1.131] |
| tune | final | B_qb | B_core | se_total | 821 | -5.949 | [-8.828, -3.351] |
| tune | final | B_qb_inj | B_core | ae_margin | 821 | -0.112 | [-0.197, -0.027] |
| tune | final | B_qb_inj | B_core | ae_total | 821 | -0.196 | [-0.312, -0.081] |
| tune | final | B_qb_inj | B_core | se_margin | 821 | -4.013 | [-6.968, -1.100] |
| tune | final | B_qb_inj | B_core | se_total | 821 | -6.547 | [-9.729, -3.448] |
| tune | final | B_qb_noadj | B_core | ae_margin | 821 | -0.103 | [-0.184, -0.023] |
| tune | final | B_qb_noadj | B_core | ae_total | 821 | -0.166 | [-0.273, -0.062] |
| tune | final | B_qb_noadj | B_core | se_margin | 821 | -3.207 | [-5.961, -0.520] |
| tune | final | B_qb_noadj | B_core | se_total | 821 | -6.065 | [-8.962, -3.289] |
| tune | final | C_direct | B_core | ae_margin | 821 | -0.254 | [-0.380, -0.120] |
| tune | final | C_direct | B_core | ae_total | 821 | -0.234 | [-0.351, -0.118] |
| tune | final | C_direct | B_core | se_margin | 821 | -8.287 | [-12.629, -3.885] |
| tune | final | C_direct | B_core | se_total | 821 | -8.003 | [-11.250, -4.635] |
| tune | final | C_resid | B_core | ae_margin | 821 | -0.300 | [-0.514, -0.097] |
| tune | final | C_resid | B_core | ae_total | 821 | -0.325 | [-0.502, -0.149] |
| tune | final | C_resid | B_core | se_margin | 821 | -9.647 | [-15.936, -3.552] |
| tune | final | C_resid | B_core | se_total | 821 | -12.264 | [-17.413, -7.368] |
| tune | final | C_resid_hgb | B_core | ae_margin | 821 | -0.259 | [-0.516, -0.015] |
| tune | final | C_resid_hgb | B_core | ae_total | 821 | -0.108 | [-0.312, +0.088] |
| tune | final | C_resid_hgb | B_core | se_margin | 821 | -7.621 | [-15.131, -0.235] |
| tune | final | C_resid_hgb | B_core | se_total | 821 | -4.239 | [-10.452, +2.270] |
| tune | final | C_resid_noinj | B_core | ae_margin | 821 | -0.298 | [-0.488, -0.115] |
| tune | final | C_resid_noinj | B_core | ae_total | 821 | -0.325 | [-0.496, -0.155] |
| tune | final | C_resid_noinj | B_core | se_margin | 821 | -9.675 | [-15.874, -3.412] |
| tune | final | C_resid_noinj | B_core | se_total | 821 | -12.271 | [-17.396, -7.076] |
| tune | final | C_resid_nopersonnel | B_core | ae_margin | 821 | -0.302 | [-0.497, -0.110] |
| tune | final | C_resid_nopersonnel | B_core | ae_total | 821 | -0.327 | [-0.498, -0.145] |
| tune | final | C_resid_nopersonnel | B_core | se_margin | 821 | -9.697 | [-15.592, -3.549] |
| tune | final | C_resid_nopersonnel | B_core | se_total | 821 | -12.272 | [-17.316, -7.074] |
| tune | final | N_naive_home | B_core | ae_margin | 821 | +1.065 | [+0.782, +1.339] |
| tune | final | N_naive_home | B_core | ae_total | 821 | +0.215 | [-0.020, +0.451] |
| tune | final | N_naive_home | B_core | se_margin | 821 | +37.890 | [+29.206, +45.760] |
| tune | final | N_naive_home | B_core | se_total | 821 | +7.213 | [-0.895, +14.878] |
| tune | final | B_core | N_naive_home | ae_margin | 821 | -1.065 | [-1.345, -0.777] |
| tune | final | B_core | N_naive_home | ae_total | 821 | -0.215 | [-0.452, +0.016] |
| tune | final | B_core | N_naive_home | se_margin | 821 | -37.890 | [-45.927, -30.054] |
| tune | final | B_core | N_naive_home | se_total | 821 | -7.213 | [-15.085, +0.586] |

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
| final | C_resid | 2019 | 267 | 10.22 | 10.79 | 0.643 |
| final | C_resid | 2020 | 269 | 9.80 | 10.30 | 0.672 |
| final | C_resid | 2021 | 285 | 10.64 | 10.83 | 0.623 |
| final | C_resid | 2022 | 284 | 8.79 | 10.38 | 0.663 |
| final | C_resid | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | C_resid | 2024 | 285 | 9.67 | 9.80 | 0.705 |
| final | C_resid_hgb | 2019 | 267 | 10.37 | 11.22 | 0.635 |
| final | C_resid_hgb | 2020 | 269 | 9.88 | 10.52 | 0.694 |
| final | C_resid_hgb | 2021 | 285 | 10.54 | 10.85 | 0.641 |
| final | C_resid_hgb | 2022 | 284 | 8.88 | 10.33 | 0.681 |
| final | C_resid_hgb | 2023 | 285 | 10.16 | 10.13 | 0.653 |
| final | C_resid_hgb | 2024 | 285 | 9.72 | 9.73 | 0.709 |
| final | C_direct | 2019 | 267 | 10.24 | 10.89 | 0.643 |
| final | C_direct | 2020 | 269 | 9.80 | 10.48 | 0.679 |
| final | C_direct | 2021 | 285 | 10.75 | 10.83 | 0.634 |
| final | C_direct | 2022 | 284 | 8.93 | 10.49 | 0.649 |
| final | C_direct | 2023 | 285 | 10.07 | 10.33 | 0.681 |
| final | C_direct | 2024 | 285 | 9.68 | 9.80 | 0.716 |
| final | C_resid_noinj | 2019 | 267 | 10.22 | 10.79 | 0.643 |
| final | C_resid_noinj | 2020 | 269 | 9.79 | 10.30 | 0.672 |
| final | C_resid_noinj | 2021 | 285 | 10.65 | 10.83 | 0.623 |
| final | C_resid_noinj | 2022 | 284 | 8.79 | 10.36 | 0.663 |
| final | C_resid_noinj | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | C_resid_noinj | 2024 | 285 | 9.66 | 9.80 | 0.705 |
| final | C_resid_nopersonnel | 2019 | 267 | 10.21 | 10.78 | 0.643 |
| final | C_resid_nopersonnel | 2020 | 269 | 9.80 | 10.31 | 0.672 |
| final | C_resid_nopersonnel | 2021 | 285 | 10.64 | 10.83 | 0.623 |
| final | C_resid_nopersonnel | 2022 | 284 | 8.79 | 10.39 | 0.663 |
| final | C_resid_nopersonnel | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | C_resid_nopersonnel | 2024 | 285 | 9.67 | 9.81 | 0.702 |

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
| final | C_resid | weeks_1_4 | 192 | 10.05 | 10.20 |  |
| final | C_resid | weeks_5_plus_reg | 623 | 9.22 | 10.11 |  |
| final | C_resid | playoffs | 39 | 11.00 | 9.78 | yes |
| final | C_resid | neutral_site | 20 | 8.49 | 8.88 | yes |
| final | C_resid | expected_qb_changed | 200 | 9.68 | 9.79 |  |
| final | C_resid_hgb | weeks_1_4 | 192 | 10.06 | 10.11 |  |
| final | C_resid_hgb | weeks_5_plus_reg | 623 | 9.36 | 10.07 |  |
| final | C_resid_hgb | playoffs | 39 | 10.86 | 9.76 | yes |
| final | C_resid_hgb | neutral_site | 20 | 8.67 | 9.18 | yes |
| final | C_resid_hgb | expected_qb_changed | 200 | 9.73 | 9.65 |  |
| final | C_direct | weeks_1_4 | 192 | 10.10 | 10.21 |  |
| final | C_direct | weeks_5_plus_reg | 623 | 9.31 | 10.23 |  |
| final | C_direct | playoffs | 39 | 10.83 | 9.78 | yes |
| final | C_direct | neutral_site | 20 | 8.87 | 8.70 | yes |
| final | C_direct | expected_qb_changed | 200 | 9.65 | 9.83 |  |
| final | C_resid_noinj | weeks_1_4 | 192 | 10.04 | 10.19 |  |
| final | C_resid_noinj | weeks_5_plus_reg | 623 | 9.22 | 10.11 |  |
| final | C_resid_noinj | playoffs | 39 | 10.98 | 9.73 | yes |
| final | C_resid_noinj | neutral_site | 20 | 8.45 | 8.93 | yes |
| final | C_resid_noinj | expected_qb_changed | 200 | 9.68 | 9.76 |  |
| final | C_resid_nopersonnel | weeks_1_4 | 192 | 10.03 | 10.17 |  |
| final | C_resid_nopersonnel | weeks_5_plus_reg | 623 | 9.22 | 10.12 |  |
| final | C_resid_nopersonnel | playoffs | 39 | 10.95 | 9.97 | yes |
| final | C_resid_nopersonnel | neutral_site | 20 | 8.43 | 8.97 | yes |
| final | C_resid_nopersonnel | expected_qb_changed | 200 | 9.70 | 9.86 |  |

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
    "B_qb_inj": 1000.0,
    "C_resid": [
     100000.0,
     100000.0
    ],
    "C_direct": 1000.0,
    "C_resid_noinj": [
     100000.0,
     100000.0
    ],
    "C_resid_nopersonnel": [
     100000.0,
     100000.0
    ]
   },
   "market_rows_test": 267,
   "A_cal_params": {
    "margin_intercept": 0.2714332281373468,
    "margin_slope": 1.009921527715767,
    "total_intercept": -1.107805616630536,
    "total_slope": 1.0202486943816753
   },
   "C_resid_top_coefs": {
    "margin": [
     [
      "away_off_bye",
      -0.009074542032415282
     ],
     [
      "away_def_succ_play",
      -0.008917925114793963
     ],
     [
      "away_def_epa_rush",
      -0.0075236250173366746
     ],
     [
      "away_def_pts_drive",
      -0.007291857829891277
     ],
     [
      "home_off_bye",
      -0.007115033665587314
     ],
     [
      "away_adj_def_epa",
      0.006155103089988275
     ],
     [
      "home_off_sack_rate",
      -0.006149599506537145
     ],
     [
      "away_def_expl_rush",
      -0.0056682744282788525
     ]
    ],
    "total": [
     [
      "away_qb_log_db",
      -0.01283960713937504
     ],
     [
      "home_qb_change",
      -0.01011300341660079
     ],
     [
      "away_off_epa_rush",
      -0.009481988163889739
     ],
     [
      "market_margin",
      0.009137831339250597
     ],
     [
      "home_off_fum_rate",
      -0.00867175926345951
     ],
     [
      "away_off_sack_rate",
      0.00863796865061254
     ],
     [
      "home_lost_skill",
      0.008635974045702592
     ],
     [
      "away_qb_rating",
      -0.008556305547895902
     ]
    ]
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
    "B_qb_inj": 1000.0,
    "C_resid": [
     30000.0,
     100000.0
    ],
    "C_direct": 1000.0,
    "C_resid_noinj": [
     100000.0,
     100000.0
    ],
    "C_resid_nopersonnel": [
     30000.0,
     100000.0
    ]
   },
   "market_rows_test": 269,
   "A_cal_params": {
    "margin_intercept": -0.3131370526446391,
    "margin_slope": 1.0304095915217468,
    "total_intercept": -0.15667839919503024,
    "total_slope": 1.0030162948909653
   },
   "C_resid_top_coefs": {
    "margin": [
     [
      "away_def_succ_play",
      -0.029419735594963983
     ],
     [
      "away_def_pts_drive",
      -0.02724190313652972
     ],
     [
      "home_def_expl_rush",
      -0.02695316209347477
     ],
     [
      "home_off_sack_rate",
      -0.026773003637524693
     ],
     [
      "away_lost_ol",
      0.02314640003966891
     ],
     [
      "home_off_bye",
      -0.022304019749974795
     ],
     [
      "away_off_succ_play",
      -0.022135573429358617
     ],
     [
      "away_def_expl_rush",
      -0.020657160160915594
     ]
    ],
    "total": [
     [
      "away_qb_log_db",
      -0.011464766549311101
     ],
     [
      "away_off_sack_rate",
      0.010676033025439284
     ],
     [
      "away_qb_rating",
      -0.010353339106561221
     ],
     [
      "home_off_fum_rate",
      -0.010103364865016527
     ],
     [
      "away_qb_change",
      0.009667053073599366
     ],
     [
      "away_off_fum_rate",
      0.009533719028415261
     ],
     [
      "away_off_epa_rush",
      -0.008599921564376565
     ],
     [
      "away_off_epa_play",
      -0.007970923218485495
     ]
    ]
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
    "B_qb_inj": 1000.0,
    "C_resid": [
     30000.0,
     100000.0
    ],
    "C_direct": 1000.0,
    "C_resid_noinj": [
     100000.0,
     100000.0
    ],
    "C_resid_nopersonnel": [
     30000.0,
     100000.0
    ]
   },
   "market_rows_test": 285,
   "A_cal_params": {
    "margin_intercept": -0.4238922732118018,
    "margin_slope": 1.0173469735624494,
    "total_intercept": -1.7024676035908186,
    "total_slope": 1.0424531162064488
   },
   "C_resid_top_coefs": {
    "margin": [
     [
      "away_lost_ol",
      0.031851840953906946
     ],
     [
      "away_lost_front",
      0.03061736528717698
     ],
     [
      "away_def_pts_drive",
      -0.028591590774163244
     ],
     [
      "away_def_succ_play",
      -0.027932877298705448
     ],
     [
      "away_off_succ_play",
      -0.02599448957871687
     ],
     [
      "away_off_epa_rush",
      -0.025777529899816777
     ],
     [
      "home_off_sack_rate",
      -0.02388220096538668
     ],
     [
      "home_off_expl_db",
      -0.023591060654416966
     ]
    ],
    "total": [
     [
      "away_qb_log_db",
      -0.012308423130865645
     ],
     [
      "home_qb_change",
      -0.011897550344782131
     ],
     [
      "home_qb_delta",
      0.011280614274700352
     ],
     [
      "away_off_fum_rate",
      0.010800460525178392
     ],
     [
      "away_off_sack_rate",
      0.010435529029837807
     ],
     [
      "home_def_neutral_pass",
      -0.010366168961100914
     ],
     [
      "home_qb_log_db",
      0.01028574510454589
     ],
     [
      "away_off_epa_rush",
      -0.009705431097719692
     ]
    ]
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
    "B_qb_inj": 1000.0,
    "C_resid": [
     100000.0,
     30000.0
    ],
    "C_direct": 1000.0,
    "C_resid_noinj": [
     100000.0,
     10000.0
    ],
    "C_resid_nopersonnel": [
     100000.0,
     30000.0
    ]
   },
   "market_rows_test": 284,
   "A_cal_params": {
    "margin_intercept": -0.3372140492370519,
    "margin_slope": 1.0186881736489692,
    "total_intercept": -0.3791273355051885,
    "total_slope": 1.0108706410863275
   },
   "C_resid_top_coefs": {
    "margin": [
     [
      "away_lost_front",
      0.01167161306866733
     ],
     [
      "home_def_expl_rush",
      -0.010650992348835524
     ],
     [
      "home_off_expl_db",
      -0.00911549820920556
     ],
     [
      "home_off_rz_td",
      -0.008726463006333594
     ],
     [
      "away_off_succ_play",
      -0.008574643213737973
     ],
     [
      "away_off_epa_rush",
      -0.008562581532245775
     ],
     [
      "away_off_pts_drive",
      -0.007970037151857439
     ],
     [
      "away_def_succ_play",
      -0.007903979786272395
     ]
    ],
    "total": [
     [
      "home_def_neutral_pass",
      -0.048426859175067144
     ],
     [
      "home_qb_change",
      -0.04146770945821293
     ],
     [
      "home_qb_delta",
      0.03820379415116717
     ],
     [
      "home_qb_log_db",
      0.03652166627059973
     ],
     [
      "home_off_plays_pg",
      -0.033079950526879336
     ],
     [
      "dome",
      0.031015752892507988
     ],
     [
      "home_field",
      0.029156203335997815
     ],
     [
      "away_off_fum_rate",
      0.028079303632259345
     ]
    ]
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
    "B_qb_inj": 1000.0,
    "C_resid": [
     100000.0,
     3000.0
    ],
    "C_direct": 300.0,
    "C_resid_noinj": [
     100000.0,
     3000.0
    ],
    "C_resid_nopersonnel": [
     100000.0,
     3000.0
    ]
   },
   "market_rows_test": 285,
   "A_cal_params": {
    "margin_intercept": -0.19669998553214119,
    "margin_slope": 0.9913842008521099,
    "total_intercept": -0.12022426750792903,
    "total_slope": 1.0042802601952003
   },
   "C_resid_top_coefs": {
    "margin": [
     [
      "home_def_expl_rush",
      -0.012838693473453476
     ],
     [
      "away_lost_front",
      0.010795181149342276
     ],
     [
      "home_lost_front",
      0.010422900203795752
     ],
     [
      "away_def_pts_drive",
      -0.010051628168021362
     ],
     [
      "away_off_succ_play",
      -0.009403898820353916
     ],
     [
      "away_lost_db",
      0.009128019603953057
     ],
     [
      "home_off_expl_db",
      -0.009051786883630484
     ],
     [
      "away_off_epa_rush",
      -0.008881406160954763
     ]
    ],
    "total": [
     [
      "home_def_neutral_pass",
      -0.2955295752066182
     ],
     [
      "home_qb_change",
      -0.2602846869064333
     ],
     [
      "dome",
      0.25591117693962845
     ],
     [
      "away_off_neutral_pass",
      0.25333585661524
     ],
     [
      "home_qb_log_db",
      0.21803464255927837
     ],
     [
      "home_def_fum_rate",
      0.2127055666560408
     ],
     [
      "home_def_int_rate",
      -0.21018784989455433
     ],
     [
      "away_off_fum_rate",
      0.19652601648009463
     ]
    ]
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
    "B_qb_inj": 1000.0,
    "C_resid": [
     30000.0,
     3000.0
    ],
    "C_direct": 100.0,
    "C_resid_noinj": [
     10000.0,
     3000.0
    ],
    "C_resid_nopersonnel": [
     3000.0,
     3000.0
    ]
   },
   "market_rows_test": 285,
   "A_cal_params": {
    "margin_intercept": -0.027850388525439973,
    "margin_slope": 0.9944984920419533,
    "total_intercept": 0.7895283444290158,
    "total_slope": 0.9860085794495842
   },
   "C_resid_top_coefs": {
    "margin": [
     [
      "home_def_expl_rush",
      -0.04165826451014613
     ],
     [
      "home_off_rz_td",
      -0.04036534174494265
     ],
     [
      "away_off_succ_play",
      -0.03296408634292416
     ],
     [
      "away_def_pts_drive",
      -0.031034954315100834
     ],
     [
      "away_def_epa_db",
      -0.029472785463353187
     ],
     [
      "home_off_expl_db",
      -0.028018100552734324
     ],
     [
      "away_lost_front",
      0.027488183657788167
     ],
     [
      "away_def_succ_play",
      -0.027001488489803077
     ]
    ],
    "total": [
     [
      "home_qb_change",
      -0.30281025215569657
     ],
     [
      "home_def_neutral_pass",
      -0.288571180639287
     ],
     [
      "dome",
      0.2759631098981094
     ],
     [
      "away_off_neutral_pass",
      0.2567865814218382
     ],
     [
      "home_off_neutral_pass",
      -0.21886954178946127
     ],
     [
      "away_off_sack_rate",
      0.2124807875110251
     ],
     [
      "home_off_expl_db",
      0.20742564851098755
     ],
     [
      "home_lost_skill",
      0.20252243852490726
     ]
    ]
   }
  }
 ]
}
```