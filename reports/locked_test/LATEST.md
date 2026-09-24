# Backtest report `locked_20260924T234835Z`

Generated 2026-09-24T23:48:35.292547+00:00 (UTC). Code hash `39e057cbc51b`. Folds (walk-forward, expanding window): [2019, 2020, 2021, 2022, 2023, 2024, 2025]. Locked test season 2025 INCLUDED.

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
| locked | early | B_qb | 285 | 10.02 | 12.86 | 10.52 | 13.25 | 7.27 | 7.53 | 0.609 |
| locked | early | B_qb_noadj | 285 | 10.04 | 12.88 | 10.66 | 13.35 | 7.31 | 7.56 | 0.613 |
| locked | early | B_core | 285 | 10.18 | 13.00 | 10.50 | 13.31 | 7.28 | 7.63 | 0.588 |
| tune | early | B_qb | 821 | 10.50 | 13.46 | 10.93 | 13.67 | 7.64 | 7.67 | 0.639 |
| tune | early | B_qb_noadj | 821 | 10.50 | 13.47 | 10.94 | 13.67 | 7.68 | 7.65 | 0.643 |
| tune | early | B_core | 821 | 10.53 | 13.49 | 10.97 | 13.72 | 7.67 | 7.69 | 0.641 |
| locked | early | N_naive_home | 285 | 11.00 | 14.11 | 11.00 | 13.83 | 7.82 | 7.98 | 0.521 |
| tune | early | N_naive_home | 821 | 11.59 | 14.83 | 11.18 | 13.98 | 8.02 | 8.38 | 0.505 |
| locked | final | C_resid_hgb | 285 | 9.66 | 12.22 | 10.71 | 13.52 | 7.48 | 7.30 | 0.665 |
| locked | final | A_market_cal | 285 | 9.67 | 12.23 | 10.41 | 13.22 | 7.33 | 7.24 | 0.658 |
| locked | final | A_market_raw | 285 | 9.67 | 12.24 | 10.42 | 13.24 | 7.34 | 7.24 | 0.658 |
| locked | final | C_resid | 285 | 9.68 | 12.27 | 10.51 | 13.32 | 7.39 | 7.27 | 0.658 |
| locked | final | C_resid_nopersonnel | 285 | 9.67 | 12.28 | 10.45 | 13.24 | 7.35 | 7.23 | 0.658 |
| locked | final | C_resid_noinj | 285 | 9.70 | 12.29 | 10.53 | 13.32 | 7.39 | 7.25 | 0.655 |
| locked | final | C_direct | 285 | 9.74 | 12.35 | 10.39 | 13.14 | 7.30 | 7.28 | 0.648 |
| locked | final | B_qb_inj | 285 | 9.98 | 12.70 | 10.49 | 13.24 | 7.24 | 7.53 | 0.606 |
| locked | final | B_qb | 285 | 9.97 | 12.70 | 10.54 | 13.28 | 7.23 | 7.55 | 0.616 |
| locked | final | B_qb_noadj | 285 | 10.01 | 12.73 | 10.67 | 13.36 | 7.28 | 7.61 | 0.609 |
| locked | final | B_core | 285 | 10.17 | 13.00 | 10.50 | 13.31 | 7.28 | 7.63 | 0.588 |
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
| locked | final | N_naive_home | 285 | 11.00 | 14.11 | 11.00 | 13.83 | 7.82 | 7.98 | 0.521 |
| tune | final | N_naive_home | 821 | 11.59 | 14.83 | 11.18 | 13.98 | 8.02 | 8.38 | 0.505 |

## Paired differences (model a minus model b; negative = a better)

Season-week block bootstrap 95% intervals. Few independent seasons: treat as limited evidence.

| period | horizon | a | b | loss | n | mean diff | 95% CI |
|---|---|---|---|---|---|---|---|
| dev | early | B_qb | B_core | ae_margin | 854 | +0.002 | [-0.043, +0.048] |
| dev | early | B_qb | B_core | ae_total | 854 | -0.058 | [-0.151, +0.040] |
| dev | early | B_qb | B_core | se_margin | 854 | -0.009 | [-1.110, +1.098] |
| dev | early | B_qb | B_core | se_total | 854 | -2.735 | [-5.247, -0.058] |
| dev | early | B_qb_noadj | B_core | ae_margin | 854 | +0.019 | [-0.035, +0.068] |
| dev | early | B_qb_noadj | B_core | ae_total | 854 | -0.095 | [-0.214, +0.017] |
| dev | early | B_qb_noadj | B_core | se_margin | 854 | +0.559 | [-0.833, +1.944] |
| dev | early | B_qb_noadj | B_core | se_total | 854 | -2.426 | [-5.270, +0.468] |
| dev | early | N_naive_home | B_core | ae_margin | 854 | +0.827 | [+0.563, +1.073] |
| dev | early | N_naive_home | B_core | ae_total | 854 | +0.373 | [+0.112, +0.639] |
| dev | early | N_naive_home | B_core | se_margin | 854 | +25.326 | [+17.275, +33.941] |
| dev | early | N_naive_home | B_core | se_total | 854 | +10.031 | [+3.110, +16.959] |
| dev | early | B_core | N_naive_home | ae_margin | 854 | -0.827 | [-1.082, -0.571] |
| dev | early | B_core | N_naive_home | ae_total | 854 | -0.373 | [-0.625, -0.115] |
| dev | early | B_core | N_naive_home | se_margin | 854 | -25.326 | [-33.097, -17.110] |
| dev | early | B_core | N_naive_home | se_total | 854 | -10.031 | [-16.854, -3.315] |
| dev | final | A_market_cal | A_market_raw | ae_margin | 854 | +0.011 | [-0.003, +0.025] |
| dev | final | A_market_cal | A_market_raw | ae_total | 854 | +0.002 | [-0.007, +0.011] |
| dev | final | A_market_cal | A_market_raw | se_margin | 854 | +0.398 | [+0.089, +0.697] |
| dev | final | A_market_cal | A_market_raw | se_total | 854 | -0.154 | [-0.382, +0.072] |
| dev | final | B_core | A_market_raw | ae_margin | 854 | +0.309 | [+0.153, +0.479] |
| dev | final | B_core | A_market_raw | ae_total | 854 | +0.317 | [+0.126, +0.498] |
| dev | final | B_core | A_market_raw | se_margin | 854 | +9.341 | [+3.963, +14.606] |
| dev | final | B_core | A_market_raw | se_total | 854 | +8.873 | [+4.543, +13.326] |
| dev | final | B_qb | A_market_raw | ae_margin | 854 | +0.258 | [+0.119, +0.394] |
| dev | final | B_qb | A_market_raw | ae_total | 854 | +0.162 | [+0.019, +0.306] |
| dev | final | B_qb | A_market_raw | se_margin | 854 | +5.927 | [+1.237, +9.817] |
| dev | final | B_qb | A_market_raw | se_total | 854 | +4.535 | [+0.503, +8.714] |
| dev | final | B_qb_inj | A_market_raw | ae_margin | 854 | +0.241 | [+0.113, +0.370] |
| dev | final | B_qb_inj | A_market_raw | ae_total | 854 | +0.173 | [+0.022, +0.316] |
| dev | final | B_qb_inj | A_market_raw | se_margin | 854 | +5.143 | [+1.016, +9.015] |
| dev | final | B_qb_inj | A_market_raw | se_total | 854 | +4.823 | [+0.874, +8.818] |
| dev | final | B_qb_noadj | A_market_raw | ae_margin | 854 | +0.274 | [+0.132, +0.420] |
| dev | final | B_qb_noadj | A_market_raw | ae_total | 854 | +0.120 | [-0.028, +0.265] |
| dev | final | B_qb_noadj | A_market_raw | se_margin | 854 | +6.434 | [+1.992, +10.416] |
| dev | final | B_qb_noadj | A_market_raw | se_total | 854 | +4.838 | [+1.011, +8.758] |
| dev | final | C_direct | A_market_raw | ae_margin | 854 | +0.068 | [-0.002, +0.140] |
| dev | final | C_direct | A_market_raw | ae_total | 854 | +0.095 | [-0.019, +0.206] |
| dev | final | C_direct | A_market_raw | se_margin | 854 | +1.265 | [-0.631, +3.181] |
| dev | final | C_direct | A_market_raw | se_total | 854 | +1.227 | [-1.687, +4.129] |
| dev | final | C_resid | A_market_raw | ae_margin | 854 | -0.005 | [-0.025, +0.013] |
| dev | final | C_resid | A_market_raw | ae_total | 854 | +0.004 | [-0.082, +0.091] |
| dev | final | C_resid | A_market_raw | se_margin | 854 | -0.069 | [-0.489, +0.343] |
| dev | final | C_resid | A_market_raw | se_total | 854 | -1.366 | [-3.493, +0.759] |
| dev | final | C_resid_hgb | A_market_raw | ae_margin | 854 | +0.095 | [-0.025, +0.217] |
| dev | final | C_resid_hgb | A_market_raw | ae_total | 854 | -0.047 | [-0.181, +0.084] |
| dev | final | C_resid_hgb | A_market_raw | se_margin | 854 | +3.250 | [+0.281, +6.092] |
| dev | final | C_resid_hgb | A_market_raw | se_total | 854 | -0.975 | [-4.697, +2.776] |
| dev | final | C_resid_noinj | A_market_raw | ae_margin | 854 | -0.008 | [-0.036, +0.018] |
| dev | final | C_resid_noinj | A_market_raw | ae_total | 854 | -0.004 | [-0.091, +0.078] |
| dev | final | C_resid_noinj | A_market_raw | se_margin | 854 | -0.197 | [-0.825, +0.402] |
| dev | final | C_resid_noinj | A_market_raw | se_total | 854 | -1.508 | [-3.874, +0.683] |
| dev | final | C_resid_nopersonnel | A_market_raw | ae_margin | 854 | -0.008 | [-0.045, +0.032] |
| dev | final | C_resid_nopersonnel | A_market_raw | ae_total | 854 | +0.013 | [-0.055, +0.075] |
| dev | final | C_resid_nopersonnel | A_market_raw | se_margin | 854 | -0.217 | [-1.267, +0.816] |
| dev | final | C_resid_nopersonnel | A_market_raw | se_total | 854 | -1.037 | [-2.870, +0.648] |
| dev | final | N_naive_home | A_market_raw | ae_margin | 854 | +1.136 | [+0.816, +1.436] |
| dev | final | N_naive_home | A_market_raw | ae_total | 854 | +0.690 | [+0.405, +0.981] |
| dev | final | N_naive_home | A_market_raw | se_margin | 854 | +34.685 | [+24.747, +45.597] |
| dev | final | N_naive_home | A_market_raw | se_total | 854 | +18.889 | [+11.006, +26.779] |
| dev | final | A_market_cal | B_core | ae_margin | 854 | -0.298 | [-0.458, -0.138] |
| dev | final | A_market_cal | B_core | ae_total | 854 | -0.315 | [-0.496, -0.135] |
| dev | final | A_market_cal | B_core | se_margin | 854 | -8.943 | [-14.578, -3.816] |
| dev | final | A_market_cal | B_core | se_total | 854 | -9.026 | [-13.517, -4.750] |
| dev | final | A_market_raw | B_core | ae_margin | 854 | -0.309 | [-0.468, -0.148] |
| dev | final | A_market_raw | B_core | ae_total | 854 | -0.317 | [-0.495, -0.131] |
| dev | final | A_market_raw | B_core | se_margin | 854 | -9.341 | [-14.815, -4.414] |
| dev | final | A_market_raw | B_core | se_total | 854 | -8.873 | [-13.363, -4.323] |
| dev | final | B_qb | B_core | ae_margin | 854 | -0.051 | [-0.167, +0.062] |
| dev | final | B_qb | B_core | ae_total | 854 | -0.156 | [-0.275, -0.033] |
| dev | final | B_qb | B_core | se_margin | 854 | -3.414 | [-6.714, -0.369] |
| dev | final | B_qb | B_core | se_total | 854 | -4.338 | [-7.236, -1.424] |
| dev | final | B_qb_inj | B_core | ae_margin | 854 | -0.069 | [-0.203, +0.056] |
| dev | final | B_qb_inj | B_core | ae_total | 854 | -0.145 | [-0.270, -0.016] |
| dev | final | B_qb_inj | B_core | se_margin | 854 | -4.198 | [-8.076, -0.991] |
| dev | final | B_qb_inj | B_core | se_total | 854 | -4.049 | [-7.059, -1.106] |
| dev | final | B_qb_noadj | B_core | ae_margin | 854 | -0.035 | [-0.156, +0.084] |
| dev | final | B_qb_noadj | B_core | ae_total | 854 | -0.197 | [-0.335, -0.063] |
| dev | final | B_qb_noadj | B_core | se_margin | 854 | -2.907 | [-6.355, +0.029] |
| dev | final | B_qb_noadj | B_core | se_total | 854 | -4.035 | [-7.284, -0.875] |
| dev | final | C_direct | B_core | ae_margin | 854 | -0.242 | [-0.413, -0.066] |
| dev | final | C_direct | B_core | ae_total | 854 | -0.223 | [-0.386, -0.068] |
| dev | final | C_direct | B_core | se_margin | 854 | -8.076 | [-13.164, -3.200] |
| dev | final | C_direct | B_core | se_total | 854 | -7.646 | [-11.223, -4.025] |
| dev | final | C_resid | B_core | ae_margin | 854 | -0.314 | [-0.478, -0.154] |
| dev | final | C_resid | B_core | ae_total | 854 | -0.313 | [-0.517, -0.106] |
| dev | final | C_resid | B_core | se_margin | 854 | -9.410 | [-14.657, -3.856] |
| dev | final | C_resid | B_core | se_total | 854 | -10.238 | [-15.225, -4.995] |
| dev | final | C_resid_hgb | B_core | ae_margin | 854 | -0.214 | [-0.406, -0.014] |
| dev | final | C_resid_hgb | B_core | ae_total | 854 | -0.364 | [-0.573, -0.150] |
| dev | final | C_resid_hgb | B_core | se_margin | 854 | -6.091 | [-12.168, +0.053] |
| dev | final | C_resid_hgb | B_core | se_total | 854 | -9.848 | [-15.603, -4.291] |
| dev | final | C_resid_noinj | B_core | ae_margin | 854 | -0.317 | [-0.481, -0.155] |
| dev | final | C_resid_noinj | B_core | ae_total | 854 | -0.321 | [-0.527, -0.121] |
| dev | final | C_resid_noinj | B_core | se_margin | 854 | -9.538 | [-15.001, -4.485] |
| dev | final | C_resid_noinj | B_core | se_total | 854 | -10.381 | [-15.869, -5.491] |
| dev | final | C_resid_nopersonnel | B_core | ae_margin | 854 | -0.317 | [-0.481, -0.153] |
| dev | final | C_resid_nopersonnel | B_core | ae_total | 854 | -0.305 | [-0.493, -0.111] |
| dev | final | C_resid_nopersonnel | B_core | se_margin | 854 | -9.558 | [-14.673, -4.610] |
| dev | final | C_resid_nopersonnel | B_core | se_total | 854 | -9.910 | [-14.483, -5.528] |
| dev | final | N_naive_home | B_core | ae_margin | 854 | +0.827 | [+0.563, +1.074] |
| dev | final | N_naive_home | B_core | ae_total | 854 | +0.373 | [+0.122, +0.624] |
| dev | final | N_naive_home | B_core | se_margin | 854 | +25.344 | [+17.246, +33.967] |
| dev | final | N_naive_home | B_core | se_total | 854 | +10.016 | [+3.382, +16.960] |
| dev | final | B_core | N_naive_home | ae_margin | 854 | -0.827 | [-1.078, -0.572] |
| dev | final | B_core | N_naive_home | ae_total | 854 | -0.373 | [-0.614, -0.120] |
| dev | final | B_core | N_naive_home | se_margin | 854 | -25.344 | [-33.732, -16.988] |
| dev | final | B_core | N_naive_home | se_total | 854 | -10.016 | [-16.711, -3.128] |
| tune | early | B_qb | B_core | ae_margin | 821 | -0.030 | [-0.063, +0.002] |
| tune | early | B_qb | B_core | ae_total | 821 | -0.039 | [-0.092, +0.018] |
| tune | early | B_qb | B_core | se_margin | 821 | -0.774 | [-1.671, +0.105] |
| tune | early | B_qb | B_core | se_total | 821 | -1.484 | [-3.081, +0.185] |
| locked | early | B_qb | B_core | ae_margin | 285 | -0.156 | [-0.272, -0.037] |
| locked | early | B_qb | B_core | ae_total | 285 | +0.016 | [-0.165, +0.199] |
| locked | early | B_qb | B_core | se_margin | 285 | -3.586 | [-6.961, -0.248] |
| locked | early | B_qb | B_core | se_total | 285 | -1.729 | [-5.380, +1.819] |
| tune | early | B_qb_noadj | B_core | ae_margin | 821 | -0.024 | [-0.072, +0.024] |
| tune | early | B_qb_noadj | B_core | ae_total | 821 | -0.028 | [-0.105, +0.046] |
| tune | early | B_qb_noadj | B_core | se_margin | 821 | -0.485 | [-2.050, +0.982] |
| tune | early | B_qb_noadj | B_core | se_total | 821 | -1.371 | [-3.508, +0.924] |
| locked | early | B_qb_noadj | B_core | ae_margin | 285 | -0.139 | [-0.265, -0.007] |
| locked | early | B_qb_noadj | B_core | ae_total | 285 | +0.158 | [-0.024, +0.355] |
| locked | early | B_qb_noadj | B_core | se_margin | 285 | -3.112 | [-7.340, +0.757] |
| locked | early | B_qb_noadj | B_core | se_total | 285 | +0.913 | [-3.986, +5.380] |
| tune | early | N_naive_home | B_core | ae_margin | 821 | +1.065 | [+0.783, +1.337] |
| tune | early | N_naive_home | B_core | ae_total | 821 | +0.217 | [-0.020, +0.466] |
| tune | early | N_naive_home | B_core | se_margin | 821 | +37.913 | [+30.394, +46.038] |
| tune | early | N_naive_home | B_core | se_total | 821 | +7.238 | [-0.885, +14.668] |
| locked | early | N_naive_home | B_core | ae_margin | 285 | +0.822 | [+0.320, +1.352] |
| locked | early | N_naive_home | B_core | ae_total | 285 | +0.499 | [+0.071, +0.924] |
| locked | early | N_naive_home | B_core | se_margin | 285 | +30.231 | [+13.656, +46.502] |
| locked | early | N_naive_home | B_core | se_total | 285 | +13.966 | [+5.050, +21.977] |
| tune | early | B_core | N_naive_home | ae_margin | 821 | -1.065 | [-1.342, -0.784] |
| tune | early | B_core | N_naive_home | ae_total | 821 | -0.217 | [-0.465, +0.023] |
| tune | early | B_core | N_naive_home | se_margin | 821 | -37.913 | [-45.971, -30.621] |
| tune | early | B_core | N_naive_home | se_total | 821 | -7.238 | [-14.630, +0.575] |
| locked | early | B_core | N_naive_home | ae_margin | 285 | -0.822 | [-1.350, -0.309] |
| locked | early | B_core | N_naive_home | ae_total | 285 | -0.499 | [-0.914, -0.066] |
| locked | early | B_core | N_naive_home | se_margin | 285 | -30.231 | [-47.667, -14.407] |
| locked | early | B_core | N_naive_home | se_total | 285 | -13.966 | [-22.301, -4.768] |
| tune | final | A_market_cal | A_market_raw | ae_margin | 821 | +0.015 | [-0.008, +0.039] |
| tune | final | A_market_cal | A_market_raw | ae_total | 821 | +0.011 | [-0.002, +0.026] |
| tune | final | A_market_cal | A_market_raw | se_margin | 821 | +0.337 | [-0.269, +0.929] |
| tune | final | A_market_cal | A_market_raw | se_total | 821 | +0.291 | [-0.079, +0.668] |
| locked | final | A_market_cal | A_market_raw | ae_margin | 285 | +0.001 | [-0.014, +0.016] |
| locked | final | A_market_cal | A_market_raw | ae_total | 285 | -0.011 | [-0.047, +0.026] |
| locked | final | A_market_cal | A_market_raw | se_margin | 285 | -0.272 | [-0.574, +0.025] |
| locked | final | A_market_cal | A_market_raw | se_total | 285 | -0.584 | [-1.457, +0.328] |
| tune | final | B_core | A_market_raw | ae_margin | 821 | +0.308 | [+0.096, +0.507] |
| tune | final | B_core | A_market_raw | ae_total | 821 | +0.334 | [+0.159, +0.509] |
| tune | final | B_core | A_market_raw | se_margin | 821 | +9.995 | [+4.042, +16.309] |
| tune | final | B_core | A_market_raw | se_total | 821 | +12.443 | [+7.371, +17.574] |
| locked | final | B_core | A_market_raw | ae_margin | 285 | +0.504 | [+0.156, +0.903] |
| locked | final | B_core | A_market_raw | ae_total | 285 | +0.076 | [-0.211, +0.335] |
| locked | final | B_core | A_market_raw | se_margin | 285 | +19.013 | [+9.802, +28.270] |
| locked | final | B_core | A_market_raw | se_total | 285 | +1.897 | [-4.728, +8.713] |
| tune | final | B_qb | A_market_raw | ae_margin | 821 | +0.189 | [+0.030, +0.335] |
| tune | final | B_qb | A_market_raw | ae_total | 821 | +0.157 | [+0.004, +0.314] |
| tune | final | B_qb | A_market_raw | se_margin | 821 | +5.943 | [+1.001, +10.852] |
| tune | final | B_qb | A_market_raw | se_total | 821 | +6.494 | [+2.145, +11.264] |
| locked | final | B_qb | A_market_raw | ae_margin | 285 | +0.301 | [-0.029, +0.593] |
| locked | final | B_qb | A_market_raw | ae_total | 285 | +0.122 | [-0.178, +0.442] |
| locked | final | B_qb | A_market_raw | se_margin | 285 | +11.332 | [+4.555, +18.252] |
| locked | final | B_qb | A_market_raw | se_total | 285 | +1.159 | [-7.131, +9.098] |
| tune | final | B_qb_inj | A_market_raw | ae_margin | 821 | +0.195 | [+0.031, +0.350] |
| tune | final | B_qb_inj | A_market_raw | ae_total | 821 | +0.137 | [-0.021, +0.301] |
| tune | final | B_qb_inj | A_market_raw | se_margin | 821 | +5.981 | [+1.257, +10.557] |
| tune | final | B_qb_inj | A_market_raw | se_total | 821 | +5.896 | [+1.145, +10.775] |
| locked | final | B_qb_inj | A_market_raw | ae_margin | 285 | +0.307 | [-0.001, +0.609] |
| locked | final | B_qb_inj | A_market_raw | ae_total | 285 | +0.071 | [-0.250, +0.391] |
| locked | final | B_qb_inj | A_market_raw | se_margin | 285 | +11.275 | [+4.465, +18.922] |
| locked | final | B_qb_inj | A_market_raw | se_total | 285 | +0.010 | [-8.617, +8.643] |
| tune | final | B_qb_noadj | A_market_raw | ae_margin | 821 | +0.205 | [+0.040, +0.368] |
| tune | final | B_qb_noadj | A_market_raw | ae_total | 821 | +0.168 | [+0.002, +0.336] |
| tune | final | B_qb_noadj | A_market_raw | se_margin | 821 | +6.788 | [+1.916, +11.777] |
| tune | final | B_qb_noadj | A_market_raw | se_total | 821 | +6.378 | [+1.279, +11.320] |
| locked | final | B_qb_noadj | A_market_raw | ae_margin | 285 | +0.335 | [-0.010, +0.651] |
| locked | final | B_qb_noadj | A_market_raw | ae_total | 285 | +0.251 | [-0.086, +0.580] |
| locked | final | B_qb_noadj | A_market_raw | se_margin | 285 | +12.113 | [+4.391, +19.999] |
| locked | final | B_qb_noadj | A_market_raw | se_total | 285 | +3.387 | [-5.606, +11.934] |
| tune | final | C_direct | A_market_raw | ae_margin | 821 | +0.054 | [-0.053, +0.151] |
| tune | final | C_direct | A_market_raw | ae_total | 821 | +0.100 | [-0.038, +0.242] |
| tune | final | C_direct | A_market_raw | se_margin | 821 | +1.708 | [-1.250, +4.736] |
| tune | final | C_direct | A_market_raw | se_total | 821 | +4.440 | [+0.915, +8.086] |
| locked | final | C_direct | A_market_raw | ae_margin | 285 | +0.066 | [-0.081, +0.200] |
| locked | final | C_direct | A_market_raw | ae_total | 285 | -0.029 | [-0.215, +0.151] |
| locked | final | C_direct | A_market_raw | se_margin | 285 | +2.472 | [-1.314, +6.410] |
| locked | final | C_direct | A_market_raw | se_total | 285 | -2.620 | [-7.290, +1.907] |
| tune | final | C_resid | A_market_raw | ae_margin | 821 | +0.008 | [-0.027, +0.041] |
| tune | final | C_resid | A_market_raw | ae_total | 821 | +0.008 | [-0.008, +0.023] |
| tune | final | C_resid | A_market_raw | se_margin | 821 | +0.347 | [-0.510, +1.212] |
| tune | final | C_resid | A_market_raw | se_total | 821 | +0.179 | [-0.207, +0.571] |
| locked | final | C_resid | A_market_raw | ae_margin | 285 | +0.014 | [-0.073, +0.103] |
| locked | final | C_resid | A_market_raw | ae_total | 285 | +0.087 | [-0.102, +0.271] |
| locked | final | C_resid | A_market_raw | se_margin | 285 | +0.650 | [-1.757, +3.021] |
| locked | final | C_resid | A_market_raw | se_total | 285 | +2.270 | [-3.021, +7.293] |
| tune | final | C_resid_hgb | A_market_raw | ae_margin | 821 | +0.048 | [-0.091, +0.180] |
| tune | final | C_resid_hgb | A_market_raw | ae_total | 821 | +0.226 | [+0.042, +0.388] |
| tune | final | C_resid_hgb | A_market_raw | se_margin | 821 | +2.374 | [-1.334, +5.518] |
| tune | final | C_resid_hgb | A_market_raw | se_total | 821 | +8.204 | [+3.511, +12.698] |
| locked | final | C_resid_hgb | A_market_raw | ae_margin | 285 | -0.014 | [-0.192, +0.149] |
| locked | final | C_resid_hgb | A_market_raw | ae_total | 285 | +0.290 | [+0.007, +0.573] |
| locked | final | C_resid_hgb | A_market_raw | se_margin | 285 | -0.498 | [-5.155, +3.655] |
| locked | final | C_resid_hgb | A_market_raw | se_total | 285 | +7.550 | [-1.386, +16.977] |
| tune | final | C_resid_noinj | A_market_raw | ae_margin | 821 | +0.009 | [-0.016, +0.036] |
| tune | final | C_resid_noinj | A_market_raw | ae_total | 821 | +0.008 | [-0.007, +0.023] |
| tune | final | C_resid_noinj | A_market_raw | se_margin | 821 | +0.320 | [-0.355, +0.978] |
| tune | final | C_resid_noinj | A_market_raw | se_total | 821 | +0.172 | [-0.211, +0.531] |
| locked | final | C_resid_noinj | A_market_raw | ae_margin | 285 | +0.026 | [-0.113, +0.163] |
| locked | final | C_resid_noinj | A_market_raw | ae_total | 285 | +0.106 | [-0.082, +0.292] |
| locked | final | C_resid_noinj | A_market_raw | se_margin | 285 | +1.095 | [-2.696, +4.815] |
| locked | final | C_resid_noinj | A_market_raw | se_total | 285 | +2.232 | [-2.922, +7.167] |
| tune | final | C_resid_nopersonnel | A_market_raw | ae_margin | 821 | +0.006 | [-0.026, +0.039] |
| tune | final | C_resid_nopersonnel | A_market_raw | ae_total | 821 | +0.007 | [-0.008, +0.021] |
| tune | final | C_resid_nopersonnel | A_market_raw | se_margin | 821 | +0.297 | [-0.528, +1.126] |
| tune | final | C_resid_nopersonnel | A_market_raw | se_total | 821 | +0.171 | [-0.200, +0.493] |
| locked | final | C_resid_nopersonnel | A_market_raw | ae_margin | 285 | -0.004 | [-0.123, +0.129] |
| locked | final | C_resid_nopersonnel | A_market_raw | ae_total | 285 | +0.027 | [-0.092, +0.129] |
| locked | final | C_resid_nopersonnel | A_market_raw | se_margin | 285 | +0.771 | [-2.717, +4.372] |
| locked | final | C_resid_nopersonnel | A_market_raw | se_total | 285 | +0.161 | [-2.663, +2.945] |
| tune | final | N_naive_home | A_market_raw | ae_margin | 821 | +1.372 | [+0.981, +1.733] |
| tune | final | N_naive_home | A_market_raw | ae_total | 821 | +0.549 | [+0.295, +0.799] |
| tune | final | N_naive_home | A_market_raw | se_margin | 821 | +47.884 | [+36.433, +59.600] |
| tune | final | N_naive_home | A_market_raw | se_total | 821 | +19.656 | [+12.984, +26.369] |
| locked | final | N_naive_home | A_market_raw | ae_margin | 285 | +1.328 | [+0.881, +1.787] |
| locked | final | N_naive_home | A_market_raw | ae_total | 285 | +0.577 | [+0.236, +0.911] |
| locked | final | N_naive_home | A_market_raw | se_margin | 285 | +49.275 | [+35.007, +64.704] |
| locked | final | N_naive_home | A_market_raw | se_total | 285 | +15.957 | [+9.634, +22.103] |
| tune | final | A_market_cal | B_core | ae_margin | 821 | -0.293 | [-0.491, -0.083] |
| tune | final | A_market_cal | B_core | ae_total | 821 | -0.323 | [-0.504, -0.133] |
| tune | final | A_market_cal | B_core | se_margin | 821 | -9.658 | [-15.877, -3.603] |
| tune | final | A_market_cal | B_core | se_total | 821 | -12.152 | [-17.184, -7.155] |
| locked | final | A_market_cal | B_core | ae_margin | 285 | -0.502 | [-0.886, -0.132] |
| locked | final | A_market_cal | B_core | ae_total | 285 | -0.088 | [-0.332, +0.187] |
| locked | final | A_market_cal | B_core | se_margin | 285 | -19.285 | [-28.183, -10.246] |
| locked | final | A_market_cal | B_core | se_total | 285 | -2.481 | [-9.087, +4.301] |
| tune | final | A_market_raw | B_core | ae_margin | 821 | -0.308 | [-0.513, -0.106] |
| tune | final | A_market_raw | B_core | ae_total | 821 | -0.334 | [-0.507, -0.148] |
| tune | final | A_market_raw | B_core | se_margin | 821 | -9.995 | [-16.480, -3.799] |
| tune | final | A_market_raw | B_core | se_total | 821 | -12.443 | [-17.673, -7.336] |
| locked | final | A_market_raw | B_core | ae_margin | 285 | -0.504 | [-0.896, -0.136] |
| locked | final | A_market_raw | B_core | ae_total | 285 | -0.076 | [-0.326, +0.225] |
| locked | final | A_market_raw | B_core | se_margin | 285 | -19.013 | [-27.655, -9.745] |
| locked | final | A_market_raw | B_core | se_total | 285 | -1.897 | [-8.512, +4.562] |
| tune | final | B_qb | B_core | ae_margin | 821 | -0.118 | [-0.200, -0.034] |
| tune | final | B_qb | B_core | ae_total | 821 | -0.176 | [-0.290, -0.070] |
| tune | final | B_qb | B_core | se_margin | 821 | -4.052 | [-7.040, -1.302] |
| tune | final | B_qb | B_core | se_total | 821 | -5.949 | [-8.780, -3.124] |
| locked | final | B_qb | B_core | ae_margin | 285 | -0.203 | [-0.414, +0.006] |
| locked | final | B_qb | B_core | ae_total | 285 | +0.045 | [-0.250, +0.326] |
| locked | final | B_qb | B_core | se_margin | 285 | -7.681 | [-14.270, -1.302] |
| locked | final | B_qb | B_core | se_total | 285 | -0.738 | [-8.007, +6.645] |
| tune | final | B_qb_inj | B_core | ae_margin | 821 | -0.112 | [-0.201, -0.032] |
| tune | final | B_qb_inj | B_core | ae_total | 821 | -0.196 | [-0.313, -0.080] |
| tune | final | B_qb_inj | B_core | se_margin | 821 | -4.013 | [-7.002, -1.139] |
| tune | final | B_qb_inj | B_core | se_total | 821 | -6.547 | [-9.716, -3.480] |
| locked | final | B_qb_inj | B_core | ae_margin | 285 | -0.197 | [-0.425, +0.035] |
| locked | final | B_qb_inj | B_core | ae_total | 285 | -0.005 | [-0.301, +0.303] |
| locked | final | B_qb_inj | B_core | se_margin | 285 | -7.738 | [-14.756, -0.983] |
| locked | final | B_qb_inj | B_core | se_total | 285 | -1.887 | [-9.276, +5.642] |
| tune | final | B_qb_noadj | B_core | ae_margin | 821 | -0.103 | [-0.182, -0.024] |
| tune | final | B_qb_noadj | B_core | ae_total | 821 | -0.166 | [-0.266, -0.062] |
| tune | final | B_qb_noadj | B_core | se_margin | 821 | -3.207 | [-5.852, -0.455] |
| tune | final | B_qb_noadj | B_core | se_total | 821 | -6.065 | [-8.858, -3.229] |
| locked | final | B_qb_noadj | B_core | ae_margin | 285 | -0.169 | [-0.384, +0.048] |
| locked | final | B_qb_noadj | B_core | ae_total | 285 | +0.174 | [-0.107, +0.479] |
| locked | final | B_qb_noadj | B_core | se_margin | 285 | -6.900 | [-13.540, -0.107] |
| locked | final | B_qb_noadj | B_core | se_total | 285 | +1.489 | [-6.239, +9.421] |
| tune | final | C_direct | B_core | ae_margin | 821 | -0.254 | [-0.384, -0.121] |
| tune | final | C_direct | B_core | ae_total | 821 | -0.234 | [-0.353, -0.123] |
| tune | final | C_direct | B_core | se_margin | 821 | -8.287 | [-12.743, -3.966] |
| tune | final | C_direct | B_core | se_total | 821 | -8.003 | [-11.370, -4.660] |
| locked | final | C_direct | B_core | ae_margin | 285 | -0.438 | [-0.745, -0.132] |
| locked | final | C_direct | B_core | ae_total | 285 | -0.106 | [-0.387, +0.190] |
| locked | final | C_direct | B_core | se_margin | 285 | -16.541 | [-24.269, -9.169] |
| locked | final | C_direct | B_core | se_total | 285 | -4.518 | [-11.140, +2.440] |
| tune | final | C_resid | B_core | ae_margin | 821 | -0.300 | [-0.498, -0.100] |
| tune | final | C_resid | B_core | ae_total | 821 | -0.325 | [-0.502, -0.152] |
| tune | final | C_resid | B_core | se_margin | 821 | -9.647 | [-15.634, -3.873] |
| tune | final | C_resid | B_core | se_total | 821 | -12.264 | [-17.286, -7.165] |
| locked | final | C_resid | B_core | ae_margin | 285 | -0.490 | [-0.853, -0.129] |
| locked | final | C_resid | B_core | ae_total | 285 | +0.010 | [-0.266, +0.312] |
| locked | final | C_resid | B_core | se_margin | 285 | -18.363 | [-26.292, -10.554] |
| locked | final | C_resid | B_core | se_total | 285 | +0.372 | [-7.789, +8.794] |
| tune | final | C_resid_hgb | B_core | ae_margin | 821 | -0.259 | [-0.530, -0.017] |
| tune | final | C_resid_hgb | B_core | ae_total | 821 | -0.108 | [-0.311, +0.087] |
| tune | final | C_resid_hgb | B_core | se_margin | 821 | -7.621 | [-14.700, -0.465] |
| tune | final | C_resid_hgb | B_core | se_total | 821 | -4.239 | [-10.598, +2.320] |
| locked | final | C_resid_hgb | B_core | ae_margin | 285 | -0.518 | [-0.900, -0.132] |
| locked | final | C_resid_hgb | B_core | ae_total | 285 | +0.214 | [-0.086, +0.537] |
| locked | final | C_resid_hgb | B_core | se_margin | 285 | -19.511 | [-29.270, -9.749] |
| locked | final | C_resid_hgb | B_core | se_total | 285 | +5.653 | [-5.492, +16.246] |
| tune | final | C_resid_noinj | B_core | ae_margin | 821 | -0.298 | [-0.482, -0.109] |
| tune | final | C_resid_noinj | B_core | ae_total | 821 | -0.325 | [-0.491, -0.145] |
| tune | final | C_resid_noinj | B_core | se_margin | 821 | -9.675 | [-15.659, -3.700] |
| tune | final | C_resid_noinj | B_core | se_total | 821 | -12.271 | [-17.691, -7.307] |
| locked | final | C_resid_noinj | B_core | ae_margin | 285 | -0.478 | [-0.837, -0.120] |
| locked | final | C_resid_noinj | B_core | ae_total | 285 | +0.029 | [-0.249, +0.353] |
| locked | final | C_resid_noinj | B_core | se_margin | 285 | -17.918 | [-26.323, -9.779] |
| locked | final | C_resid_noinj | B_core | se_total | 285 | +0.335 | [-7.964, +8.135] |
| tune | final | C_resid_nopersonnel | B_core | ae_margin | 821 | -0.302 | [-0.494, -0.100] |
| tune | final | C_resid_nopersonnel | B_core | ae_total | 821 | -0.327 | [-0.505, -0.156] |
| tune | final | C_resid_nopersonnel | B_core | se_margin | 821 | -9.697 | [-15.834, -3.250] |
| tune | final | C_resid_nopersonnel | B_core | se_total | 821 | -12.272 | [-17.153, -6.892] |
| locked | final | C_resid_nopersonnel | B_core | ae_margin | 285 | -0.508 | [-0.868, -0.163] |
| locked | final | C_resid_nopersonnel | B_core | ae_total | 285 | -0.050 | [-0.294, +0.232] |
| locked | final | C_resid_nopersonnel | B_core | se_margin | 285 | -18.243 | [-26.250, -9.562] |
| locked | final | C_resid_nopersonnel | B_core | se_total | 285 | -1.736 | [-8.871, +5.298] |
| tune | final | N_naive_home | B_core | ae_margin | 821 | +1.065 | [+0.782, +1.347] |
| tune | final | N_naive_home | B_core | ae_total | 821 | +0.215 | [-0.031, +0.446] |
| tune | final | N_naive_home | B_core | se_margin | 821 | +37.890 | [+29.775, +45.799] |
| tune | final | N_naive_home | B_core | se_total | 821 | +7.213 | [-0.255, +14.728] |
| locked | final | N_naive_home | B_core | ae_margin | 285 | +0.824 | [+0.290, +1.389] |
| locked | final | N_naive_home | B_core | ae_total | 285 | +0.501 | [+0.098, +0.899] |
| locked | final | N_naive_home | B_core | se_margin | 285 | +30.262 | [+13.173, +47.151] |
| locked | final | N_naive_home | B_core | se_total | 285 | +14.060 | [+5.096, +22.763] |
| tune | final | B_core | N_naive_home | ae_margin | 821 | -1.065 | [-1.342, -0.779] |
| tune | final | B_core | N_naive_home | ae_total | 821 | -0.215 | [-0.451, +0.019] |
| tune | final | B_core | N_naive_home | se_margin | 821 | -37.890 | [-45.912, -29.680] |
| tune | final | B_core | N_naive_home | se_total | 821 | -7.213 | [-14.596, +0.182] |
| locked | final | B_core | N_naive_home | ae_margin | 285 | -0.824 | [-1.409, -0.335] |
| locked | final | B_core | N_naive_home | ae_total | 285 | -0.501 | [-0.905, -0.083] |
| locked | final | B_core | N_naive_home | se_margin | 285 | -30.262 | [-46.961, -14.546] |
| locked | final | B_core | N_naive_home | se_total | 285 | -14.060 | [-22.571, -5.250] |

## Per season

| horizon | model | season | n | margin MAE | total MAE | winner acc |
|---|---|---|---|---|---|---|
| early | N_naive_home | 2019 | 267 | 11.62 | 11.13 | 0.511 |
| early | N_naive_home | 2020 | 269 | 11.08 | 11.34 | 0.496 |
| early | N_naive_home | 2021 | 285 | 12.04 | 11.09 | 0.507 |
| early | N_naive_home | 2022 | 284 | 9.58 | 11.30 | 0.560 |
| early | N_naive_home | 2023 | 285 | 11.10 | 10.99 | 0.554 |
| early | N_naive_home | 2024 | 285 | 11.19 | 10.12 | 0.523 |
| early | N_naive_home | 2025 | 285 | 11.00 | 11.00 | 0.521 |
| early | B_core | 2019 | 267 | 10.43 | 10.96 | 0.643 |
| early | B_core | 2020 | 269 | 10.01 | 10.78 | 0.668 |
| early | B_core | 2021 | 285 | 11.11 | 11.15 | 0.613 |
| early | B_core | 2022 | 284 | 8.93 | 10.84 | 0.649 |
| early | B_core | 2023 | 285 | 10.33 | 10.56 | 0.621 |
| early | B_core | 2024 | 285 | 10.14 | 9.90 | 0.677 |
| early | B_core | 2025 | 285 | 10.18 | 10.50 | 0.588 |
| early | B_qb | 2019 | 267 | 10.42 | 10.98 | 0.639 |
| early | B_qb | 2020 | 269 | 9.98 | 10.68 | 0.660 |
| early | B_qb | 2021 | 285 | 11.06 | 11.11 | 0.620 |
| early | B_qb | 2022 | 284 | 8.96 | 10.64 | 0.649 |
| early | B_qb | 2023 | 285 | 10.30 | 10.52 | 0.618 |
| early | B_qb | 2024 | 285 | 10.15 | 9.95 | 0.663 |
| early | B_qb | 2025 | 285 | 10.02 | 10.52 | 0.609 |
| early | B_qb_noadj | 2019 | 267 | 10.45 | 11.00 | 0.643 |
| early | B_qb_noadj | 2020 | 269 | 10.00 | 10.64 | 0.675 |
| early | B_qb_noadj | 2021 | 285 | 11.03 | 11.16 | 0.613 |
| early | B_qb_noadj | 2022 | 284 | 8.96 | 10.60 | 0.652 |
| early | B_qb_noadj | 2023 | 285 | 10.30 | 10.45 | 0.628 |
| early | B_qb_noadj | 2024 | 285 | 10.19 | 9.96 | 0.663 |
| early | B_qb_noadj | 2025 | 285 | 10.04 | 10.66 | 0.613 |
| final | N_naive_home | 2019 | 267 | 11.62 | 11.13 | 0.511 |
| final | N_naive_home | 2020 | 269 | 11.08 | 11.34 | 0.496 |
| final | N_naive_home | 2021 | 285 | 12.04 | 11.09 | 0.507 |
| final | N_naive_home | 2022 | 284 | 9.58 | 11.30 | 0.560 |
| final | N_naive_home | 2023 | 285 | 11.10 | 10.99 | 0.554 |
| final | N_naive_home | 2024 | 285 | 11.19 | 10.12 | 0.523 |
| final | N_naive_home | 2025 | 285 | 11.00 | 11.00 | 0.521 |
| final | B_core | 2019 | 267 | 10.43 | 10.96 | 0.635 |
| final | B_core | 2020 | 269 | 10.01 | 10.79 | 0.668 |
| final | B_core | 2021 | 285 | 11.11 | 11.15 | 0.613 |
| final | B_core | 2022 | 284 | 8.93 | 10.84 | 0.649 |
| final | B_core | 2023 | 285 | 10.33 | 10.55 | 0.621 |
| final | B_core | 2024 | 285 | 10.14 | 9.89 | 0.674 |
| final | B_core | 2025 | 285 | 10.17 | 10.50 | 0.588 |
| final | B_qb | 2019 | 267 | 10.35 | 10.94 | 0.639 |
| final | B_qb | 2020 | 269 | 9.94 | 10.54 | 0.675 |
| final | B_qb | 2021 | 285 | 10.92 | 10.90 | 0.630 |
| final | B_qb | 2022 | 284 | 9.01 | 10.57 | 0.660 |
| final | B_qb | 2023 | 285 | 10.25 | 10.43 | 0.635 |
| final | B_qb | 2024 | 285 | 9.99 | 9.82 | 0.691 |
| final | B_qb | 2025 | 285 | 9.97 | 10.54 | 0.616 |
| final | B_qb_noadj | 2019 | 267 | 10.38 | 10.95 | 0.643 |
| final | B_qb_noadj | 2020 | 269 | 9.95 | 10.48 | 0.679 |
| final | B_qb_noadj | 2021 | 285 | 10.92 | 10.97 | 0.623 |
| final | B_qb_noadj | 2022 | 284 | 9.01 | 10.52 | 0.656 |
| final | B_qb_noadj | 2023 | 285 | 10.25 | 10.36 | 0.625 |
| final | B_qb_noadj | 2024 | 285 | 10.03 | 9.81 | 0.695 |
| final | B_qb_noadj | 2025 | 285 | 10.01 | 10.67 | 0.609 |
| final | B_qb_inj | 2019 | 267 | 10.34 | 10.92 | 0.635 |
| final | B_qb_inj | 2020 | 269 | 9.94 | 10.48 | 0.672 |
| final | B_qb_inj | 2021 | 285 | 10.94 | 10.91 | 0.641 |
| final | B_qb_inj | 2022 | 284 | 9.00 | 10.57 | 0.645 |
| final | B_qb_inj | 2023 | 285 | 10.23 | 10.46 | 0.660 |
| final | B_qb_inj | 2024 | 285 | 9.96 | 9.81 | 0.681 |
| final | B_qb_inj | 2025 | 285 | 9.98 | 10.49 | 0.606 |
| final | A_market_raw | 2019 | 267 | 10.18 | 10.78 | 0.643 |
| final | A_market_raw | 2020 | 269 | 9.79 | 10.30 | 0.672 |
| final | A_market_raw | 2021 | 285 | 10.67 | 10.81 | 0.623 |
| final | A_market_raw | 2022 | 284 | 8.78 | 10.40 | 0.663 |
| final | A_market_raw | 2023 | 285 | 9.98 | 10.17 | 0.674 |
| final | A_market_raw | 2024 | 285 | 9.70 | 9.77 | 0.705 |
| final | A_market_raw | 2025 | 285 | 9.67 | 10.42 | 0.658 |
| final | A_market_cal | 2019 | 267 | 10.22 | 10.79 | 0.643 |
| final | A_market_cal | 2020 | 269 | 9.80 | 10.30 | 0.672 |
| final | A_market_cal | 2021 | 285 | 10.66 | 10.84 | 0.623 |
| final | A_market_cal | 2022 | 284 | 8.81 | 10.41 | 0.663 |
| final | A_market_cal | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | A_market_cal | 2024 | 285 | 9.71 | 9.76 | 0.705 |
| final | A_market_cal | 2025 | 285 | 9.67 | 10.41 | 0.658 |
| final | C_resid | 2019 | 267 | 10.22 | 10.79 | 0.643 |
| final | C_resid | 2020 | 269 | 9.80 | 10.30 | 0.672 |
| final | C_resid | 2021 | 285 | 10.64 | 10.83 | 0.623 |
| final | C_resid | 2022 | 284 | 8.79 | 10.38 | 0.663 |
| final | C_resid | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | C_resid | 2024 | 285 | 9.67 | 9.80 | 0.705 |
| final | C_resid | 2025 | 285 | 9.68 | 10.51 | 0.658 |
| final | C_resid_hgb | 2019 | 267 | 10.37 | 11.22 | 0.635 |
| final | C_resid_hgb | 2020 | 269 | 9.88 | 10.52 | 0.694 |
| final | C_resid_hgb | 2021 | 285 | 10.54 | 10.85 | 0.641 |
| final | C_resid_hgb | 2022 | 284 | 8.88 | 10.33 | 0.681 |
| final | C_resid_hgb | 2023 | 285 | 10.16 | 10.13 | 0.653 |
| final | C_resid_hgb | 2024 | 285 | 9.72 | 9.73 | 0.709 |
| final | C_resid_hgb | 2025 | 285 | 9.66 | 10.71 | 0.665 |
| final | C_direct | 2019 | 267 | 10.24 | 10.89 | 0.643 |
| final | C_direct | 2020 | 269 | 9.80 | 10.48 | 0.679 |
| final | C_direct | 2021 | 285 | 10.75 | 10.83 | 0.634 |
| final | C_direct | 2022 | 284 | 8.93 | 10.49 | 0.649 |
| final | C_direct | 2023 | 285 | 10.07 | 10.33 | 0.681 |
| final | C_direct | 2024 | 285 | 9.68 | 9.80 | 0.716 |
| final | C_direct | 2025 | 285 | 9.74 | 10.39 | 0.648 |
| final | C_resid_noinj | 2019 | 267 | 10.22 | 10.79 | 0.643 |
| final | C_resid_noinj | 2020 | 269 | 9.79 | 10.30 | 0.672 |
| final | C_resid_noinj | 2021 | 285 | 10.65 | 10.83 | 0.623 |
| final | C_resid_noinj | 2022 | 284 | 8.79 | 10.36 | 0.663 |
| final | C_resid_noinj | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | C_resid_noinj | 2024 | 285 | 9.66 | 9.80 | 0.705 |
| final | C_resid_noinj | 2025 | 285 | 9.70 | 10.53 | 0.655 |
| final | C_resid_nopersonnel | 2019 | 267 | 10.21 | 10.78 | 0.643 |
| final | C_resid_nopersonnel | 2020 | 269 | 9.80 | 10.31 | 0.672 |
| final | C_resid_nopersonnel | 2021 | 285 | 10.64 | 10.83 | 0.623 |
| final | C_resid_nopersonnel | 2022 | 284 | 8.79 | 10.39 | 0.663 |
| final | C_resid_nopersonnel | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | C_resid_nopersonnel | 2024 | 285 | 9.67 | 9.81 | 0.702 |
| final | C_resid_nopersonnel | 2025 | 285 | 9.67 | 10.45 | 0.658 |

## Subgroups, reported period (dev, or locked when included; prespecified; small groups are exploratory)

| horizon | model | group | n | margin MAE | total MAE | exploratory |
|---|---|---|---|---|---|---|
| early | N_naive_home | weeks_1_4 | 64 | 10.30 | 11.33 | yes |
| early | N_naive_home | weeks_5_plus_reg | 208 | 11.29 | 10.86 |  |
| early | N_naive_home | playoffs | 13 | 9.77 | 11.59 | yes |
| early | N_naive_home | neutral_site | 8 | 8.50 | 8.34 | yes |
| early | N_naive_home | expected_qb_changed | 63 | 10.28 | 10.55 | yes |
| early | B_core | weeks_1_4 | 64 | 9.25 | 11.11 | yes |
| early | B_core | weeks_5_plus_reg | 208 | 10.59 | 10.31 |  |
| early | B_core | playoffs | 13 | 8.06 | 10.60 | yes |
| early | B_core | neutral_site | 8 | 8.02 | 7.60 | yes |
| early | B_core | expected_qb_changed | 63 | 9.95 | 10.41 | yes |
| early | B_qb | weeks_1_4 | 64 | 9.14 | 11.26 | yes |
| early | B_qb | weeks_5_plus_reg | 208 | 10.42 | 10.29 |  |
| early | B_qb | playoffs | 13 | 7.93 | 10.45 | yes |
| early | B_qb | neutral_site | 8 | 7.27 | 7.29 | yes |
| early | B_qb | expected_qb_changed | 63 | 9.65 | 10.39 | yes |
| early | B_qb_noadj | weeks_1_4 | 64 | 9.20 | 11.33 | yes |
| early | B_qb_noadj | weeks_5_plus_reg | 208 | 10.43 | 10.45 |  |
| early | B_qb_noadj | playoffs | 13 | 7.94 | 10.71 | yes |
| early | B_qb_noadj | neutral_site | 8 | 7.33 | 7.48 | yes |
| early | B_qb_noadj | expected_qb_changed | 63 | 9.59 | 10.48 | yes |
| final | N_naive_home | weeks_1_4 | 64 | 10.30 | 11.33 | yes |
| final | N_naive_home | weeks_5_plus_reg | 208 | 11.29 | 10.86 |  |
| final | N_naive_home | playoffs | 13 | 9.77 | 11.59 | yes |
| final | N_naive_home | neutral_site | 8 | 8.50 | 8.34 | yes |
| final | N_naive_home | expected_qb_changed | 70 | 12.40 | 10.77 | yes |
| final | B_core | weeks_1_4 | 64 | 9.25 | 11.08 | yes |
| final | B_core | weeks_5_plus_reg | 208 | 10.59 | 10.31 |  |
| final | B_core | playoffs | 13 | 8.07 | 10.61 | yes |
| final | B_core | neutral_site | 8 | 8.02 | 7.57 | yes |
| final | B_core | expected_qb_changed | 70 | 12.04 | 10.09 | yes |
| final | B_qb | weeks_1_4 | 64 | 9.37 | 11.31 | yes |
| final | B_qb | weeks_5_plus_reg | 208 | 10.27 | 10.32 |  |
| final | B_qb | playoffs | 13 | 8.11 | 10.42 | yes |
| final | B_qb | neutral_site | 8 | 7.86 | 6.82 | yes |
| final | B_qb | expected_qb_changed | 70 | 11.65 | 10.24 | yes |
| final | B_qb_noadj | weeks_1_4 | 64 | 9.42 | 11.41 | yes |
| final | B_qb_noadj | weeks_5_plus_reg | 208 | 10.31 | 10.45 |  |
| final | B_qb_noadj | playoffs | 13 | 8.06 | 10.67 | yes |
| final | B_qb_noadj | neutral_site | 8 | 7.89 | 7.34 | yes |
| final | B_qb_noadj | expected_qb_changed | 70 | 11.63 | 10.33 | yes |
| final | B_qb_inj | weeks_1_4 | 64 | 9.28 | 11.23 | yes |
| final | B_qb_inj | weeks_5_plus_reg | 208 | 10.30 | 10.28 |  |
| final | B_qb_inj | playoffs | 13 | 8.19 | 10.30 | yes |
| final | B_qb_inj | neutral_site | 8 | 7.80 | 6.65 | yes |
| final | B_qb_inj | expected_qb_changed | 70 | 11.55 | 10.01 | yes |
| final | A_market_raw | weeks_1_4 | 64 | 8.84 | 11.41 | yes |
| final | A_market_raw | weeks_5_plus_reg | 208 | 9.99 | 10.08 |  |
| final | A_market_raw | playoffs | 13 | 8.58 | 11.04 | yes |
| final | A_market_raw | neutral_site | 8 | 7.25 | 7.25 | yes |
| final | A_market_raw | expected_qb_changed | 70 | 11.08 | 10.27 | yes |
| final | A_market_cal | weeks_1_4 | 64 | 8.84 | 11.40 | yes |
| final | A_market_cal | weeks_5_plus_reg | 208 | 10.00 | 10.07 |  |
| final | A_market_cal | playoffs | 13 | 8.58 | 11.05 | yes |
| final | A_market_cal | neutral_site | 8 | 7.27 | 7.23 | yes |
| final | A_market_cal | expected_qb_changed | 70 | 11.10 | 10.27 | yes |
| final | C_resid | weeks_1_4 | 64 | 8.75 | 11.27 | yes |
| final | C_resid | weeks_5_plus_reg | 208 | 10.05 | 10.25 |  |
| final | C_resid | playoffs | 13 | 8.39 | 10.97 | yes |
| final | C_resid | neutral_site | 8 | 7.56 | 6.72 | yes |
| final | C_resid | expected_qb_changed | 70 | 11.11 | 10.63 | yes |
| final | C_resid_hgb | weeks_1_4 | 64 | 8.71 | 11.37 | yes |
| final | C_resid_hgb | weeks_5_plus_reg | 208 | 10.06 | 10.49 |  |
| final | C_resid_hgb | playoffs | 13 | 7.84 | 11.14 | yes |
| final | C_resid_hgb | neutral_site | 8 | 7.59 | 7.52 | yes |
| final | C_resid_hgb | expected_qb_changed | 70 | 11.00 | 11.13 | yes |
| final | C_direct | weeks_1_4 | 64 | 8.88 | 11.29 | yes |
| final | C_direct | weeks_5_plus_reg | 208 | 10.08 | 10.09 |  |
| final | C_direct | playoffs | 13 | 8.50 | 10.88 | yes |
| final | C_direct | neutral_site | 8 | 6.93 | 7.04 | yes |
| final | C_direct | expected_qb_changed | 70 | 11.16 | 10.18 | yes |
| final | C_resid_noinj | weeks_1_4 | 64 | 8.70 | 11.31 | yes |
| final | C_resid_noinj | weeks_5_plus_reg | 208 | 10.09 | 10.26 |  |
| final | C_resid_noinj | playoffs | 13 | 8.25 | 11.01 | yes |
| final | C_resid_noinj | neutral_site | 8 | 7.50 | 6.79 | yes |
| final | C_resid_noinj | expected_qb_changed | 70 | 11.23 | 10.69 | yes |
| final | C_resid_nopersonnel | weeks_1_4 | 64 | 8.67 | 11.32 | yes |
| final | C_resid_nopersonnel | weeks_5_plus_reg | 208 | 10.06 | 10.13 |  |
| final | C_resid_nopersonnel | playoffs | 13 | 8.28 | 11.20 | yes |
| final | C_resid_nopersonnel | neutral_site | 8 | 7.58 | 6.97 | yes |
| final | C_resid_nopersonnel | expected_qb_changed | 70 | 11.15 | 10.40 | yes |

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
   "horizon": "early",
   "fold": 2025,
   "n_train": 2476,
   "n_test": 285,
   "alphas": {
    "B_core": 100.0,
    "B_qb": 300.0,
    "B_qb_noadj": 300.0
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
  },
  {
   "horizon": "final",
   "fold": 2025,
   "n_train": 2476,
   "n_test": 285,
   "alphas": {
    "B_core": 100.0,
    "B_qb": 300.0,
    "B_qb_noadj": 100.0,
    "B_qb_inj": 300.0,
    "C_resid": [
     10000.0,
     3000.0
    ],
    "C_direct": 100.0,
    "C_resid_noinj": [
     3000.0,
     3000.0
    ],
    "C_resid_nopersonnel": [
     3000.0,
     10000.0
    ]
   },
   "market_rows_test": 285,
   "A_cal_params": {
    "margin_intercept": 0.0059280790104490055,
    "margin_slope": 1.0204688777917168,
    "total_intercept": 1.0304961202216845,
    "total_slope": 0.9841623274172253
   },
   "C_resid_top_coefs": {
    "margin": [
     [
      "home_def_expl_rush",
      -0.10620769109276756
     ],
     [
      "away_lost_front",
      0.103590225237021
     ],
     [
      "home_off_start_fp",
      -0.10082974930223142
     ],
     [
      "home_off_rz_td",
      -0.09372606837651558
     ],
     [
      "away_off_succ_play",
      -0.08392230313933154
     ],
     [
      "away_def_epa_db",
      -0.07729217763371496
     ],
     [
      "away_lost_skill",
      0.07591557392143206
     ],
     [
      "away_qb_change",
      0.07391700145290617
     ]
    ],
    "total": [
     [
      "home_qb_change",
      -0.33262942986115585
     ],
     [
      "home_def_neutral_pass",
      -0.29256752597142677
     ],
     [
      "dome",
      0.28905629796934074
     ],
     [
      "away_off_neutral_pass",
      0.25466705868011175
     ],
     [
      "away_off_sack_rate",
      0.2465151891456793
     ],
     [
      "home_lost_skill",
      0.23849571950530876
     ],
     [
      "home_off_start_fp",
      -0.2274770262661058
     ],
     [
      "away_def_neutral_pass",
      -0.19468630302806683
     ]
    ]
   }
  }
 ]
}
```

## Outcome probabilities (walk-forward; calibrated on earlier seasons' out-of-fold predictions)

Tie probability = smoothed regular-season tie rate since 2017 (as of the training seasons); 0 in playoffs.

| period | horizon | model | n | ties | log loss | Brier (3-class) | Brier (home win) |
|---|---|---|---|---|---|---|---|
| dev | early | B_qb | 854 | 2 | 0.6531 | 0.4491 | 0.2230 |
| dev | final | C_resid_noinj | 854 | 2 | 0.6225 | 0.4219 | 0.2094 |
| dev | final | A_market_raw | 854 | 2 | 0.6234 | 0.4228 | 0.2099 |
| dev | final | B_qb | 854 | 2 | 0.6466 | 0.4434 | 0.2202 |
| locked | early | B_qb | 285 | 1 | 0.6473 | 0.4413 | 0.2183 |
| tune | early | B_qb | 554 | 2 | 0.6501 | 0.4402 | 0.2189 |
| locked | final | A_market_raw | 285 | 1 | 0.6286 | 0.4269 | 0.2108 |
| tune | final | A_market_raw | 554 | 2 | 0.6286 | 0.4232 | 0.2105 |
| tune | final | C_resid_noinj | 554 | 2 | 0.6291 | 0.4232 | 0.2105 |
| locked | final | C_resid_noinj | 285 | 1 | 0.6327 | 0.4307 | 0.2128 |
| tune | final | B_qb | 554 | 2 | 0.6424 | 0.4327 | 0.2150 |
| locked | final | B_qb | 285 | 1 | 0.6444 | 0.4387 | 0.2171 |

Paired log-loss differences (a − b; negative = a better), season-week block bootstrap:

| period | a | b | n | mean diff | 95% CI |
|---|---|---|---|---|---|
| tune | C_resid_noinj | A_market_raw | 554 | +0.0005 | [-0.0022, +0.0030] |
| tune | B_qb | A_market_raw | 554 | +0.0138 | [+0.0026, +0.0254] |
| tune | C_resid_noinj | B_qb | 554 | -0.0133 | [-0.0248, -0.0018] |
| dev | C_resid_noinj | A_market_raw | 854 | -0.0009 | [-0.0025, +0.0008] |
| dev | B_qb | A_market_raw | 854 | +0.0232 | [+0.0143, +0.0329] |
| dev | C_resid_noinj | B_qb | 854 | -0.0241 | [-0.0333, -0.0142] |
| locked | C_resid_noinj | A_market_raw | 285 | +0.0042 | [-0.0051, +0.0146] |
| locked | B_qb | A_market_raw | 285 | +0.0159 | [-0.0052, +0.0362] |
| locked | C_resid_noinj | B_qb | 285 | -0.0117 | [-0.0329, +0.0110] |

### Calibration (latest reported period, P(home win) bins, with counts)

**final / C_resid_noinj**

| bin | n | mean predicted | observed home-win rate |
|---|---|---|---|
| 0.1–0.2 | 12 | 0.164 | 0.250 |
| 0.2–0.3 | 29 | 0.254 | 0.207 |
| 0.3–0.4 | 47 | 0.357 | 0.404 |
| 0.4–0.5 | 34 | 0.439 | 0.441 |
| 0.5–0.6 | 43 | 0.563 | 0.581 |
| 0.6–0.7 | 49 | 0.652 | 0.531 |
| 0.7–0.8 | 38 | 0.739 | 0.737 |
| 0.8–0.9 | 29 | 0.854 | 0.897 |
| 0.9–1.0 | 4 | 0.914 | 1.000 |

**final / A_market_raw**

| bin | n | mean predicted | observed home-win rate |
|---|---|---|---|
| 0.1–0.2 | 9 | 0.154 | 0.111 |
| 0.2–0.3 | 37 | 0.254 | 0.270 |
| 0.3–0.4 | 59 | 0.366 | 0.390 |
| 0.4–0.5 | 15 | 0.424 | 0.533 |
| 0.5–0.6 | 53 | 0.562 | 0.566 |
| 0.6–0.7 | 50 | 0.642 | 0.580 |
| 0.7–0.8 | 35 | 0.736 | 0.714 |
| 0.8–0.9 | 27 | 0.860 | 0.963 |

**final / B_qb**

| bin | n | mean predicted | observed home-win rate |
|---|---|---|---|
| 0.1–0.2 | 7 | 0.161 | 0.143 |
| 0.2–0.3 | 28 | 0.250 | 0.321 |
| 0.3–0.4 | 35 | 0.356 | 0.400 |
| 0.4–0.5 | 55 | 0.448 | 0.491 |
| 0.5–0.6 | 50 | 0.550 | 0.360 |
| 0.6–0.7 | 44 | 0.649 | 0.659 |
| 0.7–0.8 | 36 | 0.754 | 0.778 |
| 0.8–0.9 | 26 | 0.836 | 0.846 |
| 0.9–1.0 | 4 | 0.905 | 1.000 |

**early / B_qb**

| bin | n | mean predicted | observed home-win rate |
|---|---|---|---|
| 0.1–0.2 | 7 | 0.174 | 0.286 |
| 0.2–0.3 | 19 | 0.265 | 0.263 |
| 0.3–0.4 | 40 | 0.355 | 0.350 |
| 0.4–0.5 | 61 | 0.456 | 0.508 |
| 0.5–0.6 | 43 | 0.548 | 0.326 |
| 0.6–0.7 | 55 | 0.649 | 0.673 |
| 0.7–0.8 | 36 | 0.751 | 0.833 |
| 0.8–0.9 | 22 | 0.839 | 0.773 |
| 0.9–1.0 | 2 | 0.915 | 1.000 |

## Prediction intervals (coverage should be close to the nominal level)

| period | horizon | model | target | method | level | coverage | mean width |
|---|---|---|---|---|---|---|---|
| dev | early | B_qb | margin | quantile | 0.80 | 0.811 | 33.6 |
| dev | early | B_qb | margin | quantile | 0.95 | 0.958 | 53.8 |
| dev | early | B_qb | margin | residual | 0.80 | 0.803 | 33.9 |
| dev | early | B_qb | margin | residual | 0.95 | 0.956 | 53.4 |
| dev | early | B_qb | total | quantile | 0.80 | 0.813 | 34.5 |
| dev | early | B_qb | total | quantile | 0.95 | 0.943 | 51.6 |
| dev | early | B_qb | total | residual | 0.80 | 0.816 | 34.7 |
| dev | early | B_qb | total | residual | 0.95 | 0.952 | 52.6 |
| dev | final | A_market_raw | margin | quantile | 0.80 | 0.799 | 31.7 |
| dev | final | A_market_raw | margin | quantile | 0.95 | 0.956 | 52.4 |
| dev | final | A_market_raw | margin | residual | 0.80 | 0.802 | 31.8 |
| dev | final | A_market_raw | margin | residual | 0.95 | 0.951 | 52.1 |
| dev | final | A_market_raw | total | quantile | 0.80 | 0.827 | 33.8 |
| dev | final | A_market_raw | total | quantile | 0.95 | 0.944 | 51.0 |
| dev | final | A_market_raw | total | residual | 0.80 | 0.828 | 33.8 |
| dev | final | A_market_raw | total | residual | 0.95 | 0.947 | 51.3 |
| dev | final | B_qb | margin | quantile | 0.80 | 0.811 | 33.2 |
| dev | final | B_qb | margin | quantile | 0.95 | 0.953 | 53.2 |
| dev | final | B_qb | margin | residual | 0.80 | 0.807 | 33.4 |
| dev | final | B_qb | margin | residual | 0.95 | 0.954 | 53.1 |
| dev | final | B_qb | total | quantile | 0.80 | 0.811 | 34.0 |
| dev | final | B_qb | total | quantile | 0.95 | 0.941 | 51.0 |
| dev | final | B_qb | total | residual | 0.80 | 0.817 | 34.4 |
| dev | final | B_qb | total | residual | 0.95 | 0.947 | 52.1 |
| dev | final | C_resid_noinj | margin | quantile | 0.80 | 0.797 | 31.9 |
| dev | final | C_resid_noinj | margin | quantile | 0.95 | 0.954 | 52.3 |
| dev | final | C_resid_noinj | margin | residual | 0.80 | 0.797 | 31.8 |
| dev | final | C_resid_noinj | margin | residual | 0.95 | 0.953 | 52.1 |
| dev | final | C_resid_noinj | total | quantile | 0.80 | 0.822 | 33.8 |
| dev | final | C_resid_noinj | total | quantile | 0.95 | 0.944 | 50.7 |
| dev | final | C_resid_noinj | total | residual | 0.80 | 0.820 | 33.5 |
| dev | final | C_resid_noinj | total | residual | 0.95 | 0.947 | 51.1 |
| tune | early | B_qb | margin | quantile | 0.80 | 0.800 | 33.2 |
| locked | early | B_qb | margin | quantile | 0.80 | 0.804 | 33.7 |
| tune | early | B_qb | margin | quantile | 0.95 | 0.940 | 53.6 |
| locked | early | B_qb | margin | quantile | 0.95 | 0.958 | 53.0 |
| tune | early | B_qb | margin | residual | 0.80 | 0.792 | 33.5 |
| locked | early | B_qb | margin | residual | 0.80 | 0.796 | 33.9 |
| tune | early | B_qb | margin | residual | 0.95 | 0.933 | 51.9 |
| locked | early | B_qb | margin | residual | 0.95 | 0.958 | 53.1 |
| tune | early | B_qb | total | quantile | 0.80 | 0.792 | 34.6 |
| locked | early | B_qb | total | quantile | 0.80 | 0.800 | 33.9 |
| tune | early | B_qb | total | quantile | 0.95 | 0.935 | 50.4 |
| locked | early | B_qb | total | quantile | 0.95 | 0.947 | 52.2 |
| tune | early | B_qb | total | residual | 0.80 | 0.801 | 35.3 |
| locked | early | B_qb | total | residual | 0.80 | 0.796 | 34.1 |
| tune | early | B_qb | total | residual | 0.95 | 0.942 | 51.6 |
| locked | early | B_qb | total | residual | 0.95 | 0.951 | 52.7 |
| tune | final | A_market_raw | margin | quantile | 0.80 | 0.796 | 32.1 |
| locked | final | A_market_raw | margin | quantile | 0.80 | 0.814 | 32.1 |
| tune | final | A_market_raw | margin | quantile | 0.95 | 0.933 | 51.6 |
| locked | final | A_market_raw | margin | quantile | 0.95 | 0.972 | 51.9 |
| tune | final | A_market_raw | margin | residual | 0.80 | 0.800 | 31.8 |
| locked | final | A_market_raw | margin | residual | 0.80 | 0.818 | 32.5 |
| tune | final | A_market_raw | margin | residual | 0.95 | 0.930 | 51.1 |
| locked | final | A_market_raw | margin | residual | 0.95 | 0.975 | 52.0 |
| tune | final | A_market_raw | total | quantile | 0.80 | 0.814 | 33.8 |
| locked | final | A_market_raw | total | quantile | 0.80 | 0.800 | 33.0 |
| tune | final | A_market_raw | total | quantile | 0.95 | 0.955 | 52.2 |
| locked | final | A_market_raw | total | quantile | 0.95 | 0.947 | 51.3 |
| tune | final | A_market_raw | total | residual | 0.80 | 0.827 | 34.2 |
| locked | final | A_market_raw | total | residual | 0.80 | 0.804 | 33.0 |
| tune | final | A_market_raw | total | residual | 0.95 | 0.944 | 50.3 |
| locked | final | A_market_raw | total | residual | 0.95 | 0.947 | 51.6 |
| tune | final | B_qb | margin | quantile | 0.80 | 0.803 | 33.1 |
| locked | final | B_qb | margin | quantile | 0.80 | 0.800 | 32.8 |
| tune | final | B_qb | margin | quantile | 0.95 | 0.940 | 52.3 |
| locked | final | B_qb | margin | quantile | 0.95 | 0.961 | 52.5 |
| tune | final | B_qb | margin | residual | 0.80 | 0.800 | 33.2 |
| locked | final | B_qb | margin | residual | 0.80 | 0.804 | 33.4 |
| tune | final | B_qb | margin | residual | 0.95 | 0.935 | 51.3 |
| locked | final | B_qb | margin | residual | 0.95 | 0.958 | 52.4 |
| tune | final | B_qb | total | quantile | 0.80 | 0.816 | 35.0 |
| locked | final | B_qb | total | quantile | 0.80 | 0.796 | 33.5 |
| tune | final | B_qb | total | quantile | 0.95 | 0.942 | 51.2 |
| locked | final | B_qb | total | quantile | 0.95 | 0.951 | 51.6 |
| tune | final | B_qb | total | residual | 0.80 | 0.814 | 35.2 |
| locked | final | B_qb | total | residual | 0.80 | 0.800 | 33.5 |
| tune | final | B_qb | total | residual | 0.95 | 0.944 | 51.4 |
| locked | final | B_qb | total | residual | 0.95 | 0.951 | 52.5 |
| tune | final | C_resid_noinj | margin | quantile | 0.80 | 0.794 | 32.2 |
| locked | final | C_resid_noinj | margin | quantile | 0.80 | 0.807 | 32.2 |
| tune | final | C_resid_noinj | margin | quantile | 0.95 | 0.928 | 51.5 |
| locked | final | C_resid_noinj | margin | quantile | 0.95 | 0.972 | 52.1 |
| tune | final | C_resid_noinj | margin | residual | 0.80 | 0.791 | 32.0 |
| locked | final | C_resid_noinj | margin | residual | 0.80 | 0.800 | 32.5 |
| tune | final | C_resid_noinj | margin | residual | 0.95 | 0.926 | 51.0 |
| locked | final | C_resid_noinj | margin | residual | 0.95 | 0.972 | 52.0 |
| tune | final | C_resid_noinj | total | quantile | 0.80 | 0.809 | 34.0 |
| locked | final | C_resid_noinj | total | quantile | 0.80 | 0.782 | 32.7 |
| tune | final | C_resid_noinj | total | quantile | 0.95 | 0.951 | 52.2 |
| locked | final | C_resid_noinj | total | quantile | 0.95 | 0.937 | 51.2 |
| tune | final | C_resid_noinj | total | residual | 0.80 | 0.807 | 34.2 |
| locked | final | C_resid_noinj | total | residual | 0.80 | 0.782 | 32.7 |
| tune | final | C_resid_noinj | total | residual | 0.95 | 0.942 | 50.4 |
| locked | final | C_resid_noinj | total | residual | 0.95 | 0.940 | 51.4 |