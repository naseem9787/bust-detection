"""
Phase 0 configuration: data sources, domain, variables, bust-definition constants.

Data sources (verified against the public WeatherBench2 GCS bucket on 2026-09-27):
  - Forecast: ECMWF HRES deterministic, 2016-01-01 to 2022-12-31, init every 12h
    (00Z/12Z), lead times 0-240h every 6h (41 steps -> Day 0 .. Day 10).
  - Truth:    ERA5 reanalysis, 1959-01-01 to 2023-01-10, every 6h.

Both stores are the SAME 1.5-degree regridded product (240 lon x 121 lat,
identical grid points), which lets us compare forecast vs. truth pointwise
with no regridding step. This keeps Phase 0 downloads small (~GB, not TB) so
it runs on a laptop. Phase 1+ should move to the full 0.25-degree stores
(ideally from a machine in the same GCP region as the bucket, to avoid slow/
costly egress) or to NCMRWF's own NCUM/NEPS output once available.
"""
from __future__ import annotations

FORECAST_STORE = (
    "gs://weatherbench2/datasets/hres/"
    "2016-2022-0012-240x121_equiangular_with_poles_conservative.zarr"
)
TRUTH_STORE = (
    "gs://weatherbench2/datasets/era5/"
    "1959-2023_01_10-6h-240x121_equiangular_with_poles_conservative.zarr"
)

# Variables pulled for Phase 0. Names must match both stores exactly.
#   total_precipitation_24hr : 24h-accumulated rainfall ending at the valid time (mm, as m in
#                               the raw ERA5/HRES convention -> converted to mm on load)
#   2m_temperature            : instantaneous 2m air temperature (K)
#   mean_sea_level_pressure   : instantaneous MSLP (Pa) - cheap large-scale pattern signal
VARIABLES = ["total_precipitation_24hr", "2m_temperature", "mean_sea_level_pressure"]

# India + margin bounding box, in the store's 0-360 longitude convention.
# A small buffer is added beyond the strict 5-40N / 65-100E box so slicing on
# a 1.5-degree grid doesn't clip edge states.
INDIA_LAT = (5.0, 40.0)
INDIA_LON = (65.0, 100.0)
BBOX_BUFFER_DEG = 2.0

# Lead days the problem statement asks for: Day 1 .. Day 10.
LEAD_DAYS = list(range(1, 11))
LEAD_HOURS = [24 * d for d in LEAD_DAYS]  # -> [24, 48, ..., 240], all on the 6h grid

# Default Phase-0 window: JJAS 2018 (captures the Aug-2018 Kerala floods bust).
# Widen this once the pipeline is verified - see README "Scaling up".
DEFAULT_START = "2018-06-01"
DEFAULT_END = "2018-09-30"

# --- Bust-definition constants -------------------------------------------------
# 1) Percentile rule: an error is a "bust" if it exceeds this quantile of the
#    historical |error| distribution for that (region, lead_day) bucket.
BUST_PERCENTILE = 0.90

# 2) Rainfall-category rule (IMD daily rainfall categories, mm/day).
#    A bust is flagged if forecast and observed categories differ by >=2 steps,
#    or if a heavy-or-above event is missed / falsely predicted.
IMD_RAIN_BINS = [-0.01, 2.5, 15.6, 64.5, 115.6, 204.5, float("inf")]
IMD_RAIN_LABELS = [
    "no_rain", "light", "moderate", "heavy", "very_heavy", "extremely_heavy",
]
HEAVY_OR_ABOVE_INDEX = IMD_RAIN_LABELS.index("heavy")  # index 3

# 3) Temperature bust: absolute error above this is always flagged, regardless
#    of the percentile threshold (catches heat-wave-relevant misses).
TEMP_BUST_ABS_ERROR_K = 3.0

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"
