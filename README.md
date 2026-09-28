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

- Widen `--start`/`--end` for a bigger sample (more seasons/years).
- Add more variables in `src/config.py` (`VARIABLES`) - e.g. geopotential
  height at 500hPa for large-scale pattern skill, wind fields for cyclones.
- Move to the full 0.25-degree WB2 stores for higher spatial detail (ideally
  from a machine in the same GCP region as the bucket, to avoid slow/costly
  egress on the full-res chunks).
- Swap in ensemble forecasts (`ifs_ens` store) to get spread-based confidence,
  not just single-forecast error.

## Roadmap (Phase 1+)

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
