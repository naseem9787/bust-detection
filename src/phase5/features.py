"""
Phase 5 - builds a single analog QUERY row from raw forecast-time inputs,
for the API endpoints (/analogs, /analog-summary, /explain). Reuses Phase
4's own region lookup (src.production.features.lookup_region) rather than
re-implementing spatial matching a second time.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd

from ..production.features import UnknownRegionError, lookup_region


@lru_cache(maxsize=1)
def _train_period_mean_wind() -> float:
    """Fallback for callers that don't supply wind_speed_10m: the TRAIN-
    period mean (a genuine 'typical' value, ~3.4 m/s), never a hard-coded
    0.0 - which is an extreme outlier (observed range is ~0.3-19 m/s) that
    would silently distort every analog distance computation for anyone
    who omits this field. Computed once, cached - not refit per call."""
    import os

    from .analogs import INDEX_DIR

    ref = pd.read_parquet(os.path.join(INDEX_DIR, "reference.parquet"), columns=["split", "wind_speed_10m"])
    return float(ref.loc[ref.split == "train", "wind_speed_10m"].mean())


def build_query_row(
    *,
    init_time: str | pd.Timestamp,
    lead_day: int,
    latitude: float,
    longitude: float,
    forecast_precip_mm: float,
    forecast_temp_c: float,
    forecast_mslp_hpa: float,
    forecast_wind_speed_10m: float | None = None,
    precip_forecast_jump: float = 0.0,
    temp_forecast_jump: float = 0.0,
) -> dict:
    init_ts = pd.Timestamp(init_time)
    region, in_domain = lookup_region(latitude, longitude)
    if not in_domain:
        raise UnknownRegionError(
            f"({latitude}, {longitude}) is outside the model's India domain - no analogs available"
        )
    valid_time = init_ts + pd.Timedelta(days=int(lead_day))
    wind = forecast_wind_speed_10m if forecast_wind_speed_10m is not None else _train_period_mean_wind()
    return {
        "init_time": init_ts,
        "lead_day": lead_day,
        "latitude": latitude,
        "longitude": longitude,
        "region_v2": region,
        "month": int(valid_time.month),
        "fcst_precip_mm": forecast_precip_mm,
        "fcst_temp_c": forecast_temp_c,
        "fcst_mslp_hpa": forecast_mslp_hpa,
        "wind_speed_10m": wind,
        "precip_forecast_jump": precip_forecast_jump,
        "temp_forecast_jump": temp_forecast_jump,
    }
