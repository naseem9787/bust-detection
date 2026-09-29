# Production Inference — SIH 2026 PS 26079

Backend/ML/inference documentation for `src/production/`. This is the
backend team's reference; the frontend contract is in
[`api_contract.md`](api_contract.md).

**Scientific framing (repeat this everywhere):** this system estimates the
probability that an NWP forecast will experience a predefined forecast
bust, based on historical forecast behaviour and forecast-state features.
It is not a weather forecast, not a guarantee, and does not claim perfect
accuracy.

## 1. Production model

Two independent LightGBM classifiers, chosen from the Phase 3 ablation
study (`outputs/phase3/ablation_results.csv`) — **not** the pilot-scope
ensemble model (see §11).

| | `rain_v1` | `temperature_v1` |
|---|---|---|
| Ablation model | Model 5 (full Phase 2 feature set) | Model 6 (Model 5 + `wind_speed_10m`, full JJAS scale) |
| Why wind is/isn't included | Tested (Phase 3 Model 6) — did **not** meaningfully help | Tested — genuinely helped (+0.010 AUC, +0.010 BSS) |
| 2021 test ROC-AUC | 0.913 | 0.825 |
| 2021 test PR-AUC | 0.459 | 0.250 |
| 2021 test Brier | 0.0153 | 0.0601 → 0.0593 (calibrated) |
| 2021 test BSS | 0.310 | ~0.10 |
| D1 → D10 ROC-AUC | 0.974 → 0.871 | 0.858 → 0.789 |

Every number above is sourced programmatically from
`outputs/phase3/lead_robustness.csv` / `ablation_results.csv` by
`src/production/build_registry.py` — never hand-typed. The full curve for
every lead day is in `models/registry/{rain,temperature}_v1.json`
(`metrics_2021_test`).

## 2. Target definitions

- **Rain bust** (`bust_precip_categorical`): forecast and observed 24h
  rainfall fall ≥2 IMD categories apart, or a heavy-or-above event is
  missed/falsely predicted. Fixed physical bins, not a percentile
  threshold.
- **Temperature bust** (`bust_temp_hard`): `|forecast 2m temp − observed 2m
  temp| > 3.0°C`. Fixed physical threshold.

Both defined in `src/label_busts.py` / `src/config.py`, unchanged since
Phase 0.

## 3. Feature definitions

One shared builder (`src/production/features.py`) is used by **both**
inference and everywhere in Phase 2/3 research (it imports Phase 2's own
`add_domain_mean_anomaly`, `add_forecast_jump`, `fit_historical_features` —
nothing is reimplemented in parallel). Full registry with source/units/
leakage-status: `outputs/phase3/feature_registry.csv`, reproduced per-model
in `models/registry/*.json`'s `feature_order`.

| Category | Features | Available at forecast issuance? |
|---|---|---|
| Forecast state | `fcst_precip_mm`, `fcst_temp_c`, `fcst_mslp_hpa`, `wind_speed_10m` (temp model only) | Yes — the forecast itself |
| Spatial | `latitude`, `longitude`, `region_v2`, domain-mean anomaly | Yes — static or derived from the same forecast |
| Temporal | `lead_day`, `month`, run-to-run jump | Yes — forecast metadata / an earlier run |
| Historical | `hist_bust_*_rate`, `hist_mean_abs_error_*` | Yes — **train-only-fit** artifacts, see §4 |
| Experimental (NOT in any production model) | ensemble mean/std/min/max/iqr/cv, `humidity_850hpa`, `geopotential_500hpa` | N/A — pilot-scope only, see §11 |

## 4. Leakage safety

Production inference **never** requires: future observations, realized
forecast error, future bust labels, test-period statistics, or full-sample
(train+test) statistics.

Historical/climatological features are **persisted artifacts**
(`models/artifacts/historical_features.parquet`, built once by
`src/production/build_static_artifacts.py` from `fit_historical_features()`
on the 2018–2020 TRAIN split only) — inference loads this table, it never
recomputes climatology from live data. `domain_mean_*` and
`previous_run_forecast_*` are optional request fields with documented
fallbacks (train-period average / zero jump) if the caller doesn't have
them — never silently invented from future data.

Automated leakage regression tests:
`tests/test_production_features_and_leakage.py` (feature-row content
checks) and `tests/test_production_registry.py` (experimental-feature
blocking). Both run as part of the standard suite.

## 5. Calibration

Fit with Phase 3's exact methodology: isotonic regression on the
**2020 validation-year predictions from the probe model** (which never
saw 2020, let alone 2021), evaluated on the 2021 test set — see
`src/production/build_calibration.py`.

| Model | Decision | Brier raw → calibrated |
|---|---|---|
| `rain_v1` | **raw preserved** (isotonic didn't help) | 0.01528 → 0.01529 |
| `temperature_v1` | **isotonic** | 0.06008 → 0.05933 |

`temperature_v1` is a genuinely new artifact (Model 6, never calibration-
tested in Phase 3) — its calibration decision was independently refit and
verified here, not assumed from Phase 3's original (no-wind) result.

The API always returns both `raw` and `calibrated` probability — never
silently overwrites one with the other (see
`tests/test_production_inference.py::test_raw_probability_is_never_silently_overwritten`).

## 6. Inference pipeline

```
forecast input → feature construction (features.py)
              → feature validation (validate_feature_row)
              → model inference (LightGBM Booster.predict)
              → probability calibration (isotonic, if validated)
              → risk-level classification (thresholds.py)
              → output schema (schemas.py)
```

`src/production/inference.py`'s `ProductionInferenceEngine` loads all
models/calibrators/static artifacts **once** at construction — see §9.

## 7. Model artifacts

```
models/
  registry/
    rain_v1.json            <- full metadata contract (see build_registry.py)
    temperature_v1.json
  artifacts/
    rain_v1.txt                          LightGBM model (copy of the validated Phase 2 artifact)
    temperature_v1.txt                   LightGBM model (retrained + persisted Model 6)
    rain_v1_val_predictions.parquet      for calibration fitting
    temperature_v1_val_predictions.parquet
    bust_temp_hard_calibrator.pkl        isotonic calibrator (temperature only - rain uses raw)
    region_grid.parquet                  702-point grid -> region + in-domain flag
    historical_features.parquet          train-only-fit climatology lookup tables
    domain_means.json                    train-period domain-mean fallbacks
    build_manifest.json, calibration_manifest.json
```

A fresh Python process calling `ProductionInferenceEngine()` needs nothing
else — no notebook state, no training script re-run. Rebuild everything
with (in order): `build_artifacts.py` → `build_static_artifacts.py` →
`build_calibration.py` → `build_registry.py`.

## 8. API endpoints

See [`api_contract.md`](api_contract.md) for the full frontend contract
with worked examples. Summary: `GET /health`, `GET /metadata`,
`POST /predict`, `GET /predictions`, `GET /regions`, `GET /timeseries`,
`GET /explain`.

## 9. Performance

- Models, calibrators, region grid, and historical-climatology lookups are
  loaded **once** at FastAPI startup (`lifespan` context manager in
  `api.py`), not per-request.
- `region_categories()` and the static-artifact loaders use `lru_cache` —
  read from disk once per process.
- SHAP (`TreeExplainer`) is computed **on-demand per requested prediction**,
  not batch-precomputed for every grid cell — a few ms per call, but not
  something you want running for 183 grid cells × 10 lead days on every
  `/predict` call.

## 10. Output files (batch mode)

`python -m src.production.batch_predict --init-time-start ... --init-time-end ... --output <dir>`
writes: `grid_predictions.parquet` (tabular), one `grid_predictions_<init_time>.nc`
per forecast issuance (NetCDF, lead_day × lat × lon), `grid_predictions.geojson`
(map-layer-ready FeatureCollection), `region_predictions.parquet` (aggregates),
`run_metadata.json`.

## 11. Experimental vs. production

**Experimental (isolated in `src/phase3/`, never importable from
`src/production/`):** the IFS ensemble pilot (mean/std/min/max/iqr/cv over
50 members) and `humidity_850hpa`/`geopotential_500hpa` — all fetched for a
**21-day pilot window only** (2021-07-15..08-04), with **zero training-
period coverage**. `src/production/registry.py`'s
`EXPERIMENTAL_FEATURE_NAMES` set + `assert_no_experimental_features()`
make production inference **fail loudly** (`ExperimentalFeatureRequestedError`,
HTTP 400) rather than silently drop or substitute these if ever requested.
See `src/phase3/ensemble_pilot_experiment.py`'s docstring for the full
scientific rationale (why its ~0.947 rain AUC is NOT a production number).

## 12. Limitations

- Region mapping (`src/phase2/geography.py`) uses a public GADM-derived
  boundary vintage that **merges Telangana into Andhra Pradesh and Ladakh
  into Jammu & Kashmir** — surfaced in `/metadata` and `/regions`, not
  hidden.
- No live NWP ingestion — `batch_predict.py` runs in OFFLINE/HISTORICAL
  mode over already-fetched forecast data (see §13). `/timeseries` is
  similarly historical-only.
- Risk thresholds (0.25 / 0.50) are round operational defaults, not a
  statistically "optimal" cutoff Phase 3 validated — configurable via
  environment variables, documented as such in `/metadata`.
- `rain_v1`'s ~0.91 AUC remains high; flagged for continued scrutiny (see
  Phase 3's final report) even though no leakage was found on repeated
  audit.

## 13. Offline/historical vs. future operational ingestion

This repository implements **OFFLINE/HISTORICAL inference only**:
`batch_predict.py` reads already-cached forecast NetCDFs
(`data/raw/forecast_*.nc`, fetched via `fetch_multi_year.sh`) or the
processed `data/processed/error_db.parquet`. There is no connector to a
live NWP feed. A future live-ingestion module would plug in by producing
the same row shape `ProductionInferenceEngine.predict()` expects
(`init_time, lead_day, latitude, longitude, forecast_precip_mm, ...`) — the
inference/calibration/output layers do not need to change.
