# Phase 1 Dataset Summary - JJAS 2018-2021

Experiment window: **JJAS 2018-2021 (init_time-based, inclusive)**

| Year | JJAS window (init_time) |
|---|---|
| 2018 | 2018-06-01 .. 2018-09-30 |
| 2019 | 2019-06-01 .. 2019-09-30 |
| 2020 | 2020-06-01 .. 2020-09-30 |
| 2021 | 2021-06-01 .. 2021-09-30 |

- Train years: [2018, 2019, 2020]
- Test year (unseen holdout): 2021
- Total rows (grid-cell x lead-day x forecast-issuance): 6,851,520
- Distinct forecast issuances (init_time): 976
- Distinct grid points: 702
- Named regions: 7 (67.4% of rows fall outside all named region boxes - 'Unclassified', a known Phase-0 regions.py coverage gap, see README)
- Variables: total_precipitation_24hr, 2m_temperature, mean_sea_level_pressure
- Lead days: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
- init_time coverage: 2018-06-01 00:00:00 .. 2021-09-30 12:00:00
- valid_time coverage: 2018-06-02 00:00:00 .. 2021-10-10 12:00:00
- Missing values across all forecast/obs/error columns: 0 (0 expected - Phase 0's build_error_db.py already drops any row missing forecast or truth)

## Bust counts

| Split | Rows | Forecast issuances | Bust rate | Precip bust | Temp bust | Missed heavy-rain | False-alarm heavy-rain |
|---|---:|---:|---:|---:|---:|---:|---:|
| train | 5,138,640 | 732 | 26.7% | 10.1% | 11.1% | 11,751 | 17,930 |
| test | 1,712,880 | 244 | 24.5% | 9.1% | 9.9% | 3,159 | 4,538 |
| overall | 6,851,520 | 976 | 26.1% | 9.9% | 10.8% | 14,910 | 22,468 |

## Bust definition

- Categorical rule: IMD rainfall-category miss (>=2 category steps apart) or a heavy-or-above event missed/falsely predicted - fixed bins, no fitting, config.IMD_RAIN_BINS/HEAVY_OR_ABOVE_INDEX
- Percentile rule: |error| > 90% percentile for that (region, lead_day), fit on the TRAIN split (2018-2020) ONLY to avoid leaking 2021 statistics into the test-year labels - see src/phase1/dataset.py module docstring
- Temp hard threshold: 3.0 degC

## Software

- Python 3.14.6 on Windows-11-10.0.26200-SP0
- pandas 3.0.6, numpy 2.5.3