# AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts

SIH Problem Statement **26079** (Ministry of Earth Sciences / NCMRWF).

Goal: flag regions and lead times (Day 1-10) where a medium-range NWP forecast
is likely to have a large error ("bust"), using historical forecast-vs-observed
error behaviour - with a confidence map, bust probability, error-prone-area
detection, and an explainable reason for low confidence.

## A note on the Kaggle dataset

If you found this project via the `daily-rainfall-at-state-level.csv` Kaggle
file: that file does **not** contain a forecast. Its `rfs` column is
mislabeled on Kaggle as "rainfall forecast" - the original source
([India Data Portal / India-WRIS](https://ckandev.indiadataportal.com/dataset/climate-data/resource/5bddf229-7ce5-4c5b-895b-411f801f26e9))
labels it **"Rainfall Storage"**, a water-resources volume metric, not a
forecast. (`rfs / actual` is a near-constant ratio that tracks state area,
e.g. Rajasthan ~11.7x, Delhi ~0.05x - a real forecast wouldn't behave like
that.) It's still fine as state-level actual/normal/deviation context, but
verification needs a real forecast.

## What we actually use instead

| Role | Source | Notes |
|---|---|---|
| Forecast | **ECMWF HRES** via [WeatherBench2](https://weatherbench2.readthedocs.io/) (public GCS bucket) | Deterministic, 2016-2022, init 00Z/12Z, lead 0-240h every 6h |
| Truth | **ERA5 reanalysis**, same WeatherBench2 bucket | Same 1.5-degree grid as HRES - no regridding needed |
| Later | **NCMRWF's own NCUM/NEPS** output | Ask via the SIH SPOC/Q&A - swap straight into this same pipeline |
| Later | **IMD gridded rainfall** (0.25-deg) | Better rainfall truth than ERA5 once available |

Both stores were verified directly against the public bucket (paths, variable
names, units, chunking) before writing any code - see `src/config.py` for the
exact zarr paths.

## Project layout

```
src/
  config.py          data sources, India bbox, variable list, bust-definition constants
  regions.py         coarse India regions as lat/lon boxes (swap for a real shapefile later)
  fetch_data.py       pulls forecast + truth from WeatherBench2, crops to India, caches locally
  build_error_db.py   aligns forecast vs truth, computes error per grid cell/lead day/region
  label_busts.py       flags busts: percentile rule + IMD rainfall-category rule + temp threshold
  summarize.py          collapses bust_labels.parquet into a small, git-friendly CSV summary
run_phase0.py          one-command pipeline: fetch -> error db -> bust labels -> summary
data/
  raw/                 cached NetCDFs from fetch_data.py (gitignored - regenerate, don't commit)
  processed/
    error_db.parquet, bust_labels.parquet   full row-level detail (gitignored once the date
                                              range is wide enough to exceed GitHub's 100MB/file
                                              limit - regenerate locally via run_phase0.py)
    summary_by_region_lead_season.csv        small aggregate, safe to commit - what's actually
                                              tracked in this repo
```

## Running it

```bash
python -m venv .venv
# Windows:
.venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python run_phase0.py --start 2018-06-01 --end 2018-09-30
```

Default window is JJAS 2018 (captures the Aug-2018 Kerala floods bust). First
run downloads and caches the India subset from GCS (a few GB depending on the
date range); re-runs reuse the cache unless you pass `--force`.

Output: `data/processed/bust_labels.parquet` - one row per
(init_time, lead_day, grid cell), with forecast value, observed value, error,
region, and bust flags (`bust_precip`, `bust_temp`, `bust_any`), plus a crude
`forecast_confidence` score. This file is gitignored once it gets large (see
below) - `data/processed/summary_by_region_lead_season.csv` (bust rate and
mean |error| per region/lead_day/season) is the small, committed view of it.

### Scaling up

- For more than ~1 season, fetch year-by-year instead of one continuous
  range - a transient network blip then only costs the year in progress:
  ```bash
  ./fetch_multi_year.sh 2018 2021
  ```
  (this is how the 2018-2021 data in this repo's summary was built - 4 years,
  20.5M rows, ~830MB of full row-level detail kept local-only, see below)
- Widen `--start`/`--end` on a single `run_phase0.py` call for a smaller custom range.
- Add more variables in `src/config.py` (`VARIABLES`) - e.g. geopotential
  height at 500hPa for large-scale pattern skill, wind fields for cyclones.
- Move to the full 0.25-degree WB2 stores for higher spatial detail (ideally
  from a machine in the same GCP region as the bucket, to avoid slow/costly
  egress on the full-res chunks).
- Swap in ensemble forecasts (`ifs_ens` store) to get spread-based confidence,
  not just single-forecast error.

## Phase 1 - forecast error atlas + baselines

`src/phase1/` turns the Phase-0 error database into a rigorous baseline and
analysis system, over an explicit **JJAS 2018-2021** window (no re-fetching -
it reuses `data/processed/error_db.parquet`, already built from the full
2018-2021 calendar years):

```
src/phase1/
  dataset.py          JJAS 2018-2021 filter + chronological train(2018-2020)/test(2021)
                        split + bust labels with percentile thresholds fit on TRAIN ONLY
                        (a leakage fix over Phase 0's label_busts.py - see its docstring)
  dataset_summary.py    outputs/phase1/dataset_summary.{json,md}
  error_atlas.py         error_by_lead/region/month/region_lead.csv, bust_rate_by_lead.csv,
                        bust_label_composition_by_region.csv
  plots.py                5 PNGs under outputs/phase1/plots/
  baselines.py             Baseline A (region x lead x month climatology), B (lead-only);
                        C (ensemble spread) is documented as unavailable, not fabricated -
                        HRES is a single deterministic run, no ensemble members to derive spread from
  evaluate.py                ROC-AUC, PR-AUC, Brier, Brier Skill Score, precision/recall/F1,
                        false-alarm rate, miss rate, reliability diagram - on the 2021 holdout
  manifest.py                outputs/phase1/experiment_manifest.json (full reproducibility record)
run_phase1.py            one-command pipeline: summary -> atlas -> plots -> baselines -> manifest
tests/                    first automated test suite (12 tests) - region assignment, IMD bins,
                        JJAS window boundaries, and a dedicated leakage check that a
                        train-only threshold is unaffected by test-only outliers
```

```bash
.venv\Scripts\python -m pytest tests/ -v
.venv\Scripts\python run_phase1.py
```

**Key finding so far:** simple region/lead/month climatology barely beats a
flat base-rate reference (ROC-AUC ~0.51-0.52, Brier Skill Score ~0). Traced
to the bust label itself: 3 of its 5 component rules are percentile
thresholds *fit per (region, lead_day)*, so they occur at a near-constant
~9% rate everywhere by construction - which caps how much region/lead
climatology can ever predict. The two fixed-threshold rules (IMD category
miss, temp hard threshold) *do* carry real regional signal but are a
minority of overall bust occurrences (see
`outputs/phase1/bust_label_composition_by_region.csv`). This is expected at
this stage - Phase 1's job is to establish that honestly, not to be
predictive yet.

## Roadmap (Phase 2+)

1. **Baselines + LightGBM**: predict bust probability from spread, run-to-run
   jumpiness, model disagreement, regime indices (MJO/ENSO), lead day, region.
2. **Past-analog search**: FAISS over a compressed representation of each
   forecast map, to answer "which past forecasts looked like this one, and
   how did they fail?" - directly matches the problem statement's ask.
3. **Explainability**: SHAP -> forecaster-style bulletin text.
4. **Calibration**: isotonic regression / conformal prediction so
   "confidence" numbers are honestly calibrated, not just a raw model score.
5. **Dashboard/API**: FastAPI + a map UI, Day 1-10 slider, region click-through
   for reasons, replay mode for known bust events (Biparjoy 2023, Wayanad 2024).

See the full roadmap discussion in the project chat history for team roles,
tech stack, and pitfalls to avoid (data leakage, testing on random days
instead of held-out later years, etc.).
