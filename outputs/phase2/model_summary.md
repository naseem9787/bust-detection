# Phase 2 Model Summary

First real predictive model: LightGBM, trained separately for the two candidate targets identified in Phase 2A's bust-definition audit (`outputs/phase2/bust_definition_audit.md`) - NOT the diluted `bust_any` composite (see Phase 1/2A findings for why).

Features used (16): `fcst_precip_mm`, `fcst_temp_c`, `fcst_mslp_hpa`, `latitude`, `longitude`, `region_v2`, `fcst_precip_anomaly_vs_domain_mean`, `fcst_temp_anomaly_vs_domain_mean`, `lead_day`, `month`, `precip_forecast_jump`, `temp_forecast_jump`, `hist_bust_precip_categorical_rate`, `hist_bust_temp_hard_rate`, `hist_mean_abs_error_precip_mm`, `hist_mean_abs_error_temp_c`

Train/val/test split is chronological throughout: fit on [2018, 2019], validate (early stopping only) on 2020, final model refit on all of 2018-2020, scored once on 2021 - the same split Phase 1 used, never touched during model/hyperparameter selection.

Random seed: 42. LightGBM params: {"objective": "binary", "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 200, "subsample": 0.8, "subsample_freq": 1, "colsample_bytree": 0.8, "n_jobs": -1, "verbosity": -1}

## Target: `bust_precip_categorical`

- Train prevalence: 2.83%, Test (2021) prevalence: 2.26%
- Fit years [2018, 2019] -> validate on 2020 (early stopping only, best_iteration=86) -> final model refit on 2018-2020 with that fixed tree count -> scored ONCE on 2021
- n_fit=893,040, n_val=446,520, n_train_final=1,339,560, n_test=446,520

### Results (2021 holdout)

| method                                      |   roc_auc |   pr_auc |   brier_score |   brier_skill_score |   precision |   recall |     f1 |   false_alarm_rate |   miss_rate |
|:--------------------------------------------|----------:|---------:|--------------:|--------------------:|------------:|---------:|-------:|-------------------:|------------:|
| Historical baseline (region x lead x month) |    0.6488 |   0.039  |        0.0222 |             -0.004  |      0.0359 |   0.5859 | 0.0676 |             0.3644 |      0.4141 |
| Lead-time-only baseline                     |    0.6216 |   0.0316 |        0.022  |              0.0036 |      0.0305 |   0.6752 | 0.0584 |             0.4959 |      0.3248 |
| LightGBM                                    |    0.9132 |   0.4587 |        0.0153 |              0.3097 |      0.1019 |   0.8324 | 0.1816 |             0.1696 |      0.1676 |

### Top 5 features (gain importance)

| feature                            |     gain |   split |
|:-----------------------------------|---------:|--------:|
| fcst_precip_mm                     | 692910   |     506 |
| fcst_precip_anomaly_vs_domain_mean | 180625   |     235 |
| hist_bust_precip_categorical_rate  | 127615   |     193 |
| region_v2                          |  41734.3 |     303 |
| precip_forecast_jump               |  32115.3 |     197 |

### Calibration

- Brier (raw): 0.0153, Brier (isotonic-calibrated, fit on 2020 validation predictions): 0.0153
- Calibration did NOT improve the Brier score -> confidence_score.py uses the raw probability for this target

### Lead-time behaviour

|   lead_day |     n |   prevalence |   roc_auc |   pr_auc |   brier |
|-----------:|------:|-------------:|----------:|---------:|--------:|
|          1 | 44652 |       0.0067 |    0.9742 |   0.5138 |  0.0042 |
|          2 | 44652 |       0.0105 |    0.9411 |   0.5035 |  0.0065 |
|          3 | 44652 |       0.015  |    0.923  |   0.4932 |  0.0094 |
|          4 | 44652 |       0.0187 |    0.9189 |   0.4749 |  0.0118 |
|          5 | 44652 |       0.0226 |    0.9105 |   0.4838 |  0.0143 |
|          6 | 44652 |       0.024  |    0.8963 |   0.4597 |  0.0159 |
|          7 | 44652 |       0.0279 |    0.8959 |   0.4475 |  0.0188 |
|          8 | 44652 |       0.0304 |    0.8883 |   0.4386 |  0.0211 |
|          9 | 44652 |       0.0339 |    0.8801 |   0.4093 |  0.0244 |
|         10 | 44652 |       0.0365 |    0.8706 |   0.4062 |  0.0264 |

### Regional behaviour (top 5 by ROC-AUC, min 20 samples)

| region_v2         |     n |   prevalence |   roc_auc |   pr_auc |
|:------------------|------:|-------------:|----------:|---------:|
| Arunachal Pradesh | 24400 |       0.0244 |    0.9769 |   0.825  |
| Jammu and Kashmir | 24400 |       0.0067 |    0.9756 |   0.6157 |
| Mizoram           |  4880 |       0.0127 |    0.9731 |   0.7926 |
| Assam             |  9760 |       0.0388 |    0.9719 |   0.7746 |
| Tripura           |  4880 |       0.023  |    0.9491 |   0.6267 |

## Target: `bust_temp_hard`

- Train prevalence: 9.43%, Test (2021) prevalence: 7.17%
- Fit years [2018, 2019] -> validate on 2020 (early stopping only, best_iteration=408) -> final model refit on 2018-2020 with that fixed tree count -> scored ONCE on 2021
- n_fit=893,040, n_val=446,520, n_train_final=1,339,560, n_test=446,520

### Results (2021 holdout)

| method                                      |   roc_auc |   pr_auc |   brier_score |   brier_skill_score |   precision |   recall |     f1 |   false_alarm_rate |   miss_rate |
|:--------------------------------------------|----------:|---------:|--------------:|--------------------:|------------:|---------:|-------:|-------------------:|------------:|
| Historical baseline (region x lead x month) |    0.7112 |   0.1625 |        0.0646 |              0.0376 |      0.117  |   0.7242 | 0.2014 |             0.4224 |      0.2758 |
| Lead-time-only baseline                     |    0.6079 |   0.0968 |        0.0665 |              0.0091 |      0.0935 |   0.6519 | 0.1636 |             0.4883 |      0.3481 |
| LightGBM                                    |    0.8149 |   0.2349 |        0.0608 |              0.0942 |      0.1606 |   0.8108 | 0.2681 |             0.3274 |      0.1892 |

### Top 5 features (gain importance)

| feature                          |   gain |   split |
|:---------------------------------|-------:|--------:|
| hist_bust_temp_hard_rate         | 561745 |     500 |
| fcst_temp_c                      | 178129 |    1673 |
| region_v2                        | 155399 |    1314 |
| fcst_temp_anomaly_vs_domain_mean | 140215 |    1448 |
| temp_forecast_jump               | 120971 |     530 |

### Calibration

- Brier (raw): 0.0608, Brier (isotonic-calibrated, fit on 2020 validation predictions): 0.0601
- Calibration IMPROVED the Brier score -> confidence_score.py uses the calibrated probability for this target

### Lead-time behaviour

|   lead_day |     n |   prevalence |   roc_auc |   pr_auc |   brier |
|-----------:|------:|-------------:|----------:|---------:|--------:|
|          1 | 44652 |       0.0363 |    0.8391 |   0.1686 |  0.0327 |
|          2 | 44652 |       0.0437 |    0.8282 |   0.1876 |  0.0388 |
|          3 | 44652 |       0.0497 |    0.8221 |   0.1982 |  0.0437 |
|          4 | 44652 |       0.0555 |    0.8121 |   0.1898 |  0.049  |
|          5 | 44652 |       0.0645 |    0.8014 |   0.2101 |  0.0561 |
|          6 | 44652 |       0.0733 |    0.797  |   0.2169 |  0.0632 |
|          7 | 44652 |       0.0819 |    0.789  |   0.2299 |  0.0699 |
|          8 | 44652 |       0.0929 |    0.7877 |   0.2455 |  0.0777 |
|          9 | 44652 |       0.1052 |    0.7917 |   0.2826 |  0.0846 |
|         10 | 44652 |       0.1142 |    0.7797 |   0.2762 |  0.092  |

### Regional behaviour (top 5 by ROC-AUC, min 20 samples)

| region_v2      |     n |   prevalence |   roc_auc |   pr_auc |
|:---------------|------:|-------------:|----------:|---------:|
| Tamil Nadu     | 19520 |       0.0251 |    0.9276 |   0.2575 |
| Gujarat        | 26840 |       0.0334 |    0.9019 |   0.2203 |
| Kerala         |  7320 |       0.0072 |    0.8886 |   0.1249 |
| Tripura        |  4880 |       0.05   |    0.8838 |   0.2147 |
| Andhra Pradesh | 31720 |       0.067  |    0.8386 |   0.2543 |

## Limitations

- Ensemble spread features are unavailable this pass (see `outputs/phase2/feature_availability.md`) - the model relies on a single deterministic forecast, historical climatology, and simple derived features (anomaly vs. domain mean, run-to-run forecast jump).
- Wind, humidity, and geopotential height are available in the source data but not yet downloaded/used - a natural next step.
- The geography fix (Part A3) covers 183 of 702 grid points (the actual India domain); 29 regions, some with very few grid points at 1.5-degree resolution, so per-region metrics for small regions should be read with their sample size in mind.
- `bust_precip_categorical`'s very high test ROC-AUC (~0.91) was specifically checked for leakage (see `outputs/phase2/leakage_audit.csv`) - no leakage mechanism was found, and the effect is physically explainable (the forecast's own precipitation value is the top feature - larger forecast values carry more inherent uncertainty), with a smooth, expected decay across lead days rather than a flat or perfect score. Still flagged here for independent replication before being trusted operationally.
- Two SEPARATE models, not one combined bust predictor - per Phase 2A's finding that combining these two candidate targets measurably dilutes signal (see bust_definition_audit.md Candidate D).