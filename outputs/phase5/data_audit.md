# Phase 5 Data Audit

## Verdict: no new data download needed

Everything the historical-analog feature needs is already fetched and
persisted from Phase 0-4:

| Requirement | Source | Status |
|---|---|---|
| Forecast state (precip/temp/mslp) | `data/processed/error_db.parquet` (Phase 0) | Available, JJAS 2018-2021 |
| Wind speed (full scale) | `data/raw/atmo_wind_*.nc` (Phase 3/4) | Available, all 4 years |
| Observed/actual outcomes | same `error_db.parquet` (`obs_*` columns) | Available |
| Realized error | same file (`error_*`, `abs_error_*` columns) | Available |
| Bust labels (leak-free) | `src/phase2/features.py` `build_features()` | Available, train-only-fit thresholds |
| Region mapping | `src/phase2/geography.py` (29 regions) | Available |
| Run-to-run forecast jump | `src/phase2/features.py` `add_forecast_jump()` | Available |

## Coverage

- **Years:** 2018, 2019, 2020, 2021 (train=2018-2020, test=2021, same
  chronological split as Phase 2-4 - reused, not redefined).
- **Months:** JJAS scope (June-September, plus a small October tail from
  late-September long-lead forecasts) - same scope as all prior phases.
  Wider (full-year, e.g. winter western disturbances) data DOES exist in
  the raw forecast/truth NetCDFs and `error_db.parquet` is NOT itself
  JJAS-restricted, but the leak-free BUST LABELS (train-only-fit
  thresholds) are only computed for the JJAS window by the existing
  pipeline. Recomputing labels for a wider window is a reasonable Phase 6
  extension, not done here to avoid re-deriving a new, untested label
  definition mid-phase (see Limitations in docs/historical_analogs.md).
- **Forecast initialization times:** 00Z/12Z, 976 issuances total (732
  train, 244 test).
- **Lead days:** 1-10 (24h-240h).
- **Grid:** 1.5-degree, 183 in-India-domain points (of 702 in the full
  buffered bounding box - see `outputs/phase2/region_assignment_summary.csv`).
- **Variables available as forecast-time features:** `fcst_precip_mm`,
  `fcst_temp_c`, `fcst_mslp_hpa`, `wind_speed_10m` (full scale),
  `precip_forecast_jump`, `temp_forecast_jump`.
- **Observation/truth variables:** `obs_precip_mm`, `obs_temp_c`,
  `obs_mslp_hpa`, plus the derived `error_*`/`abs_error_*` columns - used
  ONLY for reporting an analog's realized outcome, NEVER for computing
  similarity (see docs/historical_analogs.md Leakage section).
- **Region mapping:** `region_v2`, 29 real Indian states/UTs (Phase 2's
  GADM-derived boundaries) - known limitation: predates the 2014 Telangana
  and 2019 Ladakh splits (unchanged from Phase 2-4, not re-litigated here).
- **Bust definitions:** `bust_precip_categorical` (IMD rainfall-category
  miss) and `bust_temp_hard` (|error|>3degC) - identical definitions to
  Phase 2-4, train-only-fit percentile components refit per experiment
  split (same leakage-safe procedure as `src/phase2/dataset.py`).

## Total candidate reference-database size

183 in-domain grid points x 976 issuances x 10 lead days = 1,786,080 rows
(before any spatial/temporal query-time filtering) - small enough for a
brute-force/tree-based nearest-neighbor search with no need for FAISS (see
docs/historical_analogs.md Performance section for the actual benchmark).
