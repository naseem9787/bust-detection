"""
Phase 4 - reusable output writers for grid-level predictions: Parquet
(efficient tabular), NetCDF (meteorological/geospatial grid), and a
GeoJSON-compatible FeatureCollection (for map layers/region integration).
No frontend code here - these just write files the frontend's own mapping
library (Leaflet/Mapbox/deck.gl/whatever) can consume directly.
"""
from __future__ import annotations

import json

import pandas as pd
import xarray as xr

REQUIRED_COLUMNS = [
    "init_time", "lead_day", "valid_time", "latitude", "longitude", "region",
    "forecast_precip_mm", "forecast_temp_c",
    "rain_bust_probability_raw", "rain_bust_probability_calibrated", "rain_confidence",
    "model_version", "feature_version", "calibration_version",
]


def _check_columns(df: pd.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"grid prediction frame is missing required columns: {missing}")


def write_parquet(df: pd.DataFrame, path: str) -> str:
    _check_columns(df)
    df.to_parquet(path, index=False)
    return path


def write_netcdf(df: pd.DataFrame, path: str) -> str:
    """One (init_time, lead_day) slice per call is the natural granularity -
    a full multi-lead-day grid is written as a single Dataset indexed by
    (lead_day, latitude, longitude), which is what a meteorological NetCDF
    consumer expects."""
    _check_columns(df)
    value_cols = [
        "forecast_precip_mm", "forecast_temp_c",
        "rain_bust_probability_raw", "rain_bust_probability_calibrated", "rain_confidence",
    ]
    if "temperature_bust_probability_calibrated" in df.columns:
        value_cols += [
            "temperature_bust_probability_raw", "temperature_bust_probability_calibrated",
            "temperature_confidence",
        ]
    index_cols = ["lead_day", "latitude", "longitude"]
    dupes = df.duplicated(index_cols).sum()
    if dupes:
        raise ValueError(
            f"{dupes} duplicate (lead_day, lat, lon) rows - write_netcdf expects a "
            "single forecast issuance (one init_time) per call; group by init_time first"
        )
    indexed = df.set_index(index_cols)[value_cols]
    ds = indexed.to_xarray()
    ds.attrs["model_version"] = str(df.model_version.iloc[0])
    ds.attrs["feature_version"] = str(df.feature_version.iloc[0])
    ds.attrs["calibration_version"] = str(df.calibration_version.iloc[0])
    ds.attrs["init_time"] = str(df.init_time.iloc[0])
    ds.attrs["scientific_framing"] = (
        "Probability that the underlying NWP forecast will experience a "
        "predefined forecast bust - not a weather forecast itself, not a "
        "guarantee."
    )
    ds.to_netcdf(path)
    return path


def write_geojson(df: pd.DataFrame, path: str) -> str:
    _check_columns(df)
    features = []
    for _, row in df.iterrows():
        properties = row.drop(["latitude", "longitude"]).to_dict()
        for k, v in properties.items():
            if isinstance(v, pd.Timestamp):
                properties[k] = v.isoformat()
        features.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [row.longitude, row.latitude]},
                "properties": properties,
            }
        )
    collection = {"type": "FeatureCollection", "features": features}
    with open(path, "w") as f:
        json.dump(collection, f, default=str)
    return path
