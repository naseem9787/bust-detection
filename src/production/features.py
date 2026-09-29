"""
Phase 4 - the shared production feature builder. Uses the SAME formulas as
training (src/phase2/features.py - domain-mean anomaly, forecast-jump,
historical-climatology lookup), but reads from the small PERSISTED static
artifacts (region_grid.parquet, historical_features.parquet,
domain_means.json - see build_static_artifacts.py) instead of rebuilding
from the multi-GB error_db.parquet on every call, which is what
src/phase3/predict.py's prototype did (fine for a one-off demo, too slow
for a real service - see docs/production_inference.md's Performance note).

This is the ONE place production feature engineering happens - both
src/production/inference.py and any future batch/API path call into this
module, so there is no duplicated feature logic to drift out of sync with
training.
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd

from ..phase2.geography import OUTSIDE_DOMAIN_LABEL
from .build_artifacts import ARTIFACT_DIR
from .registry import EXPERIMENTAL_FEATURE_NAMES

HIST_GROUP_COLS = ["region_v2", "lead_day", "month"]


class UnknownRegionError(ValueError):
    pass


class FeatureValidationError(ValueError):
    pass


@lru_cache(maxsize=1)
def _load_region_grid() -> pd.DataFrame:
    return pd.read_parquet(os.path.join(ARTIFACT_DIR, "region_grid.parquet"))


@lru_cache(maxsize=1)
def region_categories() -> pd.CategoricalDtype:
    """The exact category set/order LightGBM saw at training time - training
    only ever used in-India-domain rows, so the categorical dtype must be
    built from that subset, NOT from the full 702-point grid (which also
    contains the 'Outside India domain...' label, never seen in training)."""
    grid = _load_region_grid()
    categories = sorted(grid.loc[grid.in_india_domain, "region_v2"].unique())
    return pd.CategoricalDtype(categories=categories)


@lru_cache(maxsize=1)
def _load_historical_lookups() -> dict[str, tuple[pd.Series, float]]:
    table = pd.read_parquet(os.path.join(ARTIFACT_DIR, "historical_features.parquet"))
    out = {}
    for name, g in table.groupby("feature_name"):
        lookup = g.set_index(HIST_GROUP_COLS)["value"]
        fallback = float(g["fallback"].iloc[0])
        out[name] = (lookup, fallback)
    return out


@lru_cache(maxsize=1)
def _load_domain_means() -> dict:
    import json

    with open(os.path.join(ARTIFACT_DIR, "domain_means.json")) as f:
        return json.load(f)


def lookup_region(latitude: float, longitude: float) -> tuple[str, bool]:
    """Nearest grid point on the model's own 1.5-degree grid. Returns
    (region_name, in_india_domain)."""
    grid = _load_region_grid()
    d2 = (grid.latitude - latitude) ** 2 + (grid.longitude - longitude) ** 2
    nearest = grid.loc[d2.idxmin()]
    return nearest.region_v2, bool(nearest.in_india_domain)


def historical_feature_value(name: str, region: str, lead_day: int, month: int) -> float:
    lookup, fallback = _load_historical_lookups()[name]
    return float(lookup.get((region, lead_day, month), fallback))


def build_feature_row(
    *,
    init_time: pd.Timestamp,
    lead_day: int,
    latitude: float,
    longitude: float,
    forecast_precip_mm: float,
    forecast_temp_c: float,
    forecast_mslp_hpa: float,
    forecast_wind_speed_10m: float | None = None,
    domain_mean_precip_mm: float | None = None,
    domain_mean_temp_c: float | None = None,
    previous_run_forecast_precip_mm: float | None = None,
    previous_run_forecast_temp_c: float | None = None,
    requested_experimental_features: set[str] | None = None,
) -> dict:
    """Builds one feature row using EXACTLY the training-time formulas.
    Raises ExperimentalFeatureRequestedError (via registry.py) if the caller
    asks for any pilot-scope ensemble/atmosphere feature - production never
    silently substitutes or drops those."""
    from .registry import assert_no_experimental_features

    assert_no_experimental_features(requested_experimental_features or set())

    region, in_domain = lookup_region(latitude, longitude)
    if not in_domain:
        raise UnknownRegionError(
            f"({latitude}, {longitude}) is outside the model's India domain "
            "(ocean/distant foreign territory) - see "
            "outputs/phase2/region_assignment_summary.csv. No prediction is made."
        )

    valid_time = init_time + pd.Timedelta(days=int(lead_day))
    month = int(valid_time.month)

    domain_means = _load_domain_means()
    dm_precip = domain_mean_precip_mm if domain_mean_precip_mm is not None else domain_means["fcst_precip_mm"]
    dm_temp = domain_mean_temp_c if domain_mean_temp_c is not None else domain_means["fcst_temp_c"]

    precip_jump = (
        forecast_precip_mm - previous_run_forecast_precip_mm
        if previous_run_forecast_precip_mm is not None
        else 0.0
    )
    temp_jump = (
        forecast_temp_c - previous_run_forecast_temp_c
        if previous_run_forecast_temp_c is not None
        else 0.0
    )

    row = {
        "fcst_precip_mm": forecast_precip_mm,
        "fcst_temp_c": forecast_temp_c,
        "fcst_mslp_hpa": forecast_mslp_hpa,
        "latitude": latitude,
        "longitude": longitude,
        "region_v2": region,
        "fcst_precip_anomaly_vs_domain_mean": forecast_precip_mm - dm_precip,
        "fcst_temp_anomaly_vs_domain_mean": forecast_temp_c - dm_temp,
        "lead_day": lead_day,
        "month": month,
        "precip_forecast_jump": precip_jump,
        "temp_forecast_jump": temp_jump,
    }
    for name in [
        "hist_bust_precip_categorical_rate", "hist_bust_temp_hard_rate",
        "hist_mean_abs_error_precip_mm", "hist_mean_abs_error_temp_c",
    ]:
        row[name] = historical_feature_value(name, region, lead_day, month)

    if forecast_wind_speed_10m is not None:
        row["wind_speed_10m"] = forecast_wind_speed_10m

    return {"region": region, "in_india_domain": in_domain, "valid_time": valid_time, "features": row}


def validate_feature_row(features: dict, expected_order: list[str]) -> None:
    """Every feature the model expects must be present, with a sane dtype,
    and nothing from the experimental feature set may have leaked in."""
    missing = [c for c in expected_order if c not in features]
    if missing:
        raise FeatureValidationError(f"missing required features: {missing}")
    leaked_experimental = set(features) & EXPERIMENTAL_FEATURE_NAMES
    if leaked_experimental:
        raise FeatureValidationError(
            f"experimental features present in a production feature row: {leaked_experimental}"
        )
    for name in expected_order:
        if name == "region_v2":
            continue
        value = features[name]
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise FeatureValidationError(f"feature '{name}' has non-numeric value: {value!r}")
