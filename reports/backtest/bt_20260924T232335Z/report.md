# Backtest report `bt_20260924T232335Z`

Generated 2026-09-24T23:23:35.612809+00:00 (UTC). Code hash `d5f0d2134ea1`. Folds (walk-forward, expanding window): [2022, 2023, 2024]. Locked test season 2025 not evaluated.

All numbers below were produced by `python -m nflcast backtest` on real nflverse data. Lower is better for MAE/RMSE. Historical market lines are the single nflverse schedule line (timing unknown, treated as approximately closing), so market comparisons apply only to the final-pregame horizon.

## Overall (pooled over folds)

| horizon | model | n | margin MAE | margin RMSE | total MAE | total RMSE | home MAE | away MAE | winner acc |
|---|---|---|---|---|---|---|---|---|---|
| early | B_football_ridge | 854 | 9.81 | 12.86 | 10.48 | 13.32 | 7.37 | 7.27 | 0.644 |
| early | N_naive_home | 854 | 10.63 | 13.80 | 10.80 | 13.66 | 7.78 | 7.66 | 0.546 |
| final | A_market_raw | 854 | 9.49 | 12.48 | 10.11 | 12.95 | 7.19 | 7.03 | 0.681 |
| final | A_market_cal | 854 | 9.50 | 12.50 | 10.11 | 12.95 | 7.19 | 7.04 | 0.681 |
| final | B_football_ridge | 854 | 9.81 | 12.86 | 10.48 | 13.32 | 7.38 | 7.27 | 0.647 |
| final | N_naive_home | 854 | 10.63 | 13.80 | 10.80 | 13.66 | 7.78 | 7.66 | 0.546 |

## Paired differences (model a minus model b; negative = a better)

Season-week block bootstrap 95% intervals. Only three development seasons: treat as limited evidence.

| horizon | a | b | loss | n | mean diff | 95% CI |
|---|---|---|---|---|---|---|
| early | B_football_ridge | N_naive_home | ae_margin | 854 | -0.817 | [-1.074, -0.551] |
| early | B_football_ridge | N_naive_home | ae_total | 854 | -0.323 | [-0.571, -0.067] |
| early | B_football_ridge | N_naive_home | se_margin | 854 | -25.070 | [-34.063, -16.534] |
| early | B_football_ridge | N_naive_home | se_total | 854 | -9.223 | [-16.453, -2.339] |
| final | B_football_ridge | A_market_raw | ae_margin | 854 | +0.319 | [+0.156, +0.493] |
| final | B_football_ridge | A_market_raw | ae_total | 854 | +0.366 | [+0.170, +0.566] |
| final | B_football_ridge | A_market_raw | se_margin | 854 | +9.607 | [+4.435, +14.963] |
| final | B_football_ridge | A_market_raw | se_total | 854 | +9.658 | [+4.744, +14.717] |
| final | B_football_ridge | A_market_cal | ae_margin | 854 | +0.308 | [+0.147, +0.473] |
| final | B_football_ridge | A_market_cal | ae_total | 854 | +0.364 | [+0.155, +0.560] |
| final | B_football_ridge | A_market_cal | se_margin | 854 | +9.209 | [+4.097, +14.777] |
| final | B_football_ridge | A_market_cal | se_total | 854 | +9.811 | [+4.806, +14.870] |
| final | A_market_cal | A_market_raw | ae_margin | 854 | +0.011 | [-0.002, +0.025] |
| final | A_market_cal | A_market_raw | ae_total | 854 | +0.002 | [-0.007, +0.011] |
| final | A_market_cal | A_market_raw | se_margin | 854 | +0.398 | [+0.083, +0.703] |
| final | A_market_cal | A_market_raw | se_total | 854 | -0.154 | [-0.388, +0.070] |
| final | B_football_ridge | N_naive_home | ae_margin | 854 | -0.817 | [-1.084, -0.534] |
| final | B_football_ridge | N_naive_home | ae_total | 854 | -0.324 | [-0.588, -0.061] |
| final | B_football_ridge | N_naive_home | se_margin | 854 | -25.078 | [-33.486, -16.703] |
| final | B_football_ridge | N_naive_home | se_total | 854 | -9.231 | [-16.281, -2.507] |

## Per season

| horizon | model | season | n | margin MAE | total MAE | winner acc |
|---|---|---|---|---|---|---|
| early | N_naive_home | 2022 | 284 | 9.58 | 11.30 | 0.560 |
| early | N_naive_home | 2023 | 285 | 11.10 | 10.99 | 0.554 |
| early | N_naive_home | 2024 | 285 | 11.19 | 10.12 | 0.523 |
| early | B_football_ridge | 2022 | 284 | 8.96 | 10.80 | 0.652 |
| early | B_football_ridge | 2023 | 285 | 10.37 | 10.71 | 0.614 |
| early | B_football_ridge | 2024 | 285 | 10.10 | 9.92 | 0.667 |
| final | N_naive_home | 2022 | 284 | 9.58 | 11.30 | 0.560 |
| final | N_naive_home | 2023 | 285 | 11.10 | 10.99 | 0.554 |
| final | N_naive_home | 2024 | 285 | 11.19 | 10.12 | 0.523 |
| final | B_football_ridge | 2022 | 284 | 8.95 | 10.80 | 0.652 |
| final | B_football_ridge | 2023 | 285 | 10.37 | 10.71 | 0.621 |
| final | B_football_ridge | 2024 | 285 | 10.10 | 9.92 | 0.667 |
| final | A_market_raw | 2022 | 284 | 8.78 | 10.40 | 0.663 |
| final | A_market_raw | 2023 | 285 | 9.98 | 10.17 | 0.674 |
| final | A_market_raw | 2024 | 285 | 9.70 | 9.77 | 0.705 |
| final | A_market_cal | 2022 | 284 | 8.81 | 10.41 | 0.663 |
| final | A_market_cal | 2023 | 285 | 9.99 | 10.17 | 0.674 |
| final | A_market_cal | 2024 | 285 | 9.71 | 9.76 | 0.705 |

## Subgroups (prespecified; small groups are exploratory)

| horizon | model | group | n | margin MAE | total MAE | exploratory |
|---|---|---|---|---|---|---|
| early | N_naive_home | weeks_1_4 | 192 | 10.70 | 10.74 |  |
| early | N_naive_home | weeks_5_plus_reg | 623 | 10.56 | 10.84 |  |
| early | N_naive_home | playoffs | 39 | 11.38 | 10.44 | yes |
| early | N_naive_home | neutral_site | 20 | 9.20 | 9.66 | yes |
| early | B_football_ridge | weeks_1_4 | 192 | 10.09 | 10.11 |  |
| early | B_football_ridge | weeks_5_plus_reg | 623 | 9.66 | 10.60 |  |
| early | B_football_ridge | playoffs | 39 | 10.90 | 10.39 | yes |
| early | B_football_ridge | neutral_site | 20 | 9.11 | 8.85 | yes |
| final | N_naive_home | weeks_1_4 | 192 | 10.70 | 10.74 |  |
| final | N_naive_home | weeks_5_plus_reg | 623 | 10.56 | 10.84 |  |
| final | N_naive_home | playoffs | 39 | 11.38 | 10.44 | yes |
| final | N_naive_home | neutral_site | 20 | 9.20 | 9.66 | yes |
| final | B_football_ridge | weeks_1_4 | 192 | 10.08 | 10.11 |  |
| final | B_football_ridge | weeks_5_plus_reg | 623 | 9.66 | 10.60 |  |
| final | B_football_ridge | playoffs | 39 | 10.90 | 10.39 | yes |
| final | B_football_ridge | neutral_site | 20 | 9.12 | 8.82 | yes |
| final | A_market_raw | weeks_1_4 | 192 | 10.06 | 10.03 |  |
| final | A_market_raw | weeks_5_plus_reg | 623 | 9.22 | 10.15 |  |
| final | A_market_raw | playoffs | 39 | 11.01 | 9.91 | yes |
| final | A_market_raw | neutral_site | 20 | 8.47 | 8.80 | yes |
| final | A_market_cal | weeks_1_4 | 192 | 10.07 | 10.05 |  |
| final | A_market_cal | weeks_5_plus_reg | 623 | 9.23 | 10.15 |  |
| final | A_market_cal | playoffs | 39 | 11.02 | 9.92 | yes |
| final | A_market_cal | neutral_site | 20 | 8.46 | 8.80 | yes |

## Fold details

```json
{
 "folds": [
  {
   "horizon": "early",
   "fold": 2022,
   "n_train": 1622,
   "n_test": 284,
   "B_alpha": 1000.0,
   "B_alpha_scores": {
    "1": 9.841023617584304,
    "3": 9.837745025601555,
    "10": 9.83370050371617,
    "30": 9.829234092014072,
    "100": 9.819883717157936,
    "300": 9.808993248329656,
    "1000": 9.807701420288561,
    "3000": 9.829626880799106,
    "10000": 9.88613132328976,
    "30000": 9.999527412629938
   }
  },
  {
   "horizon": "early",
   "fold": 2023,
   "n_train": 1906,
   "n_test": 285,
   "B_alpha": 1.0,
   "B_alpha_scores": {
    "1": 8.96128795244969,
    "3": 8.96437887060724,
    "10": 8.971870059843805,
    "30": 8.979988647284879,
    "100": 8.983697514530892,
    "300": 8.97957451307353,
    "1000": 8.971215854859118,
    "3000": 8.973648773968932,
    "10000": 9.00990891282922,
    "30000": 9.09955910912699
   }
  },
  {
   "horizon": "early",
   "fold": 2024,
   "n_train": 2191,
   "n_test": 285,
   "B_alpha": 100.0,
   "B_alpha_scores": {
    "1": 9.601652137940533,
    "3": 9.589434971939164,
    "10": 9.57173216192918,
    "30": 9.55864071903468,
    "100": 9.552111981452471,
    "300": 9.553445106236559,
    "1000": 9.561075320959803,
    "3000": 9.577873601433337,
    "10000": 9.620459195389822,
    "30000": 9.7153295600723
   }
  },
  {
   "horizon": "final",
   "fold": 2022,
   "n_train": 1622,
   "n_test": 284,
   "B_alpha": 1000.0,
   "B_alpha_scores": {
    "1": 9.839543382850557,
    "3": 9.837157856416045,
    "10": 9.83421236551568,
    "30": 9.8305728993666,
    "100": 9.821778554090145,
    "300": 9.810771849461371,
    "1000": 9.808837385234108,
    "3000": 9.830110805981054,
    "10000": 9.886228586378147,
    "30000": 9.999575347512529
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
   "B_alpha": 1.0,
   "B_alpha_scores": {
    "1": 8.957643511049575,
    "3": 8.960666107061746,
    "10": 8.968046380164312,
    "30": 8.976485272695468,
    "100": 8.981422910971006,
    "300": 8.978364576796244,
    "1000": 8.970562378068838,
    "3000": 8.973261170527223,
    "10000": 9.00977855707812,
    "30000": 9.09959410804033
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
   "B_alpha": 100.0,
   "B_alpha_scores": {
    "1": 9.602189250936679,
    "3": 9.590205913403087,
    "10": 9.57267704819063,
    "30": 9.559561147171266,
    "100": 9.55297255005408,
    "300": 9.554158895284148,
    "1000": 9.561427187948452,
    "3000": 9.577859309900953,
    "10000": 9.620207959735462,
    "30000": 9.715115031256788
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