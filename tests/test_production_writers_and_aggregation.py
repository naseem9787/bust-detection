"""
Phase 4 - output writer and region-aggregation tests.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from src.production.aggregation import aggregate_region
from src.production.writers import write_geojson, write_netcdf, write_parquet


def _sample_grid_df(n_lead_days=2, n_cells=3):
    rows = []
    for lead in range(1, n_lead_days + 1):
        for i in range(n_cells):
            rows.append(
                {
                    "init_time": pd.Timestamp("2021-07-15"),
                    "lead_day": lead,
                    "valid_time": pd.Timestamp("2021-07-15") + pd.Timedelta(days=lead),
                    "latitude": 20.0 + i * 1.5,
                    "longitude": 78.0 + i * 1.5,
                    "region": "Madhya Pradesh" if i == 0 else "Maharashtra",
                    "forecast_precip_mm": 5.0 + i,
                    "forecast_temp_c": 25.0 + i,
                    "rain_bust_probability_raw": 0.1 * (i + 1),
                    "rain_bust_probability_calibrated": 0.1 * (i + 1),
                    "rain_confidence": 1 - 0.1 * (i + 1),
                    "model_version": "test-v1",
                    "feature_version": "test-v1",
                    "calibration_version": "test",
                }
            )
    return pd.DataFrame(rows)


def test_write_parquet_roundtrip(tmp_path):
    df = _sample_grid_df()
    path = write_parquet(df, str(tmp_path / "grid.parquet"))
    loaded = pd.read_parquet(path)
    assert len(loaded) == len(df)


def test_write_parquet_rejects_missing_columns(tmp_path):
    df = _sample_grid_df().drop(columns=["rain_confidence"])
    with pytest.raises(ValueError):
        write_parquet(df, str(tmp_path / "grid.parquet"))


def test_write_netcdf_single_init_time(tmp_path):
    df = _sample_grid_df()
    path = write_netcdf(df, str(tmp_path / "grid.nc"))
    assert os.path.exists(path)
    import xarray as xr

    ds = xr.open_dataset(path)
    assert "rain_bust_probability_calibrated" in ds
    assert ds.attrs["model_version"] == "test-v1"


def test_write_netcdf_rejects_duplicate_lead_lat_lon(tmp_path):
    df = _sample_grid_df()
    dup = pd.concat([df, df.iloc[[0]]], ignore_index=True)  # introduce a duplicate key
    with pytest.raises(ValueError):
        write_netcdf(dup, str(tmp_path / "grid.nc"))


def test_write_geojson_structure(tmp_path):
    df = _sample_grid_df()
    path = write_geojson(df, str(tmp_path / "grid.geojson"))
    import json

    with open(path) as f:
        gj = json.load(f)
    assert gj["type"] == "FeatureCollection"
    assert len(gj["features"]) == len(df)
    assert gj["features"][0]["geometry"]["type"] == "Point"


def test_aggregate_region_produces_expected_columns():
    df = _sample_grid_df()
    agg = aggregate_region(df, "rain_bust_probability_calibrated", "rain_confidence", "forecast_precip_mm")
    for col in [
        "region", "lead_day", "valid_time", "n_grid_cells", "region_max_probability",
        "region_mean_probability", "region_high_risk_fraction", "high_risk_threshold_used",
        "representative_forecast_value", "representative_confidence",
    ]:
        assert col in agg.columns


def test_aggregate_region_max_and_mean_are_sane():
    df = _sample_grid_df()
    agg = aggregate_region(df, "rain_bust_probability_calibrated", "rain_confidence", "forecast_precip_mm")
    assert (agg.region_max_probability >= agg.region_mean_probability).all()
    assert (agg.region_high_risk_fraction >= 0).all() and (agg.region_high_risk_fraction <= 1).all()
