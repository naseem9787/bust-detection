"""
Phase 3 - Q: ensemble/feature alignment tests. Uses small synthetic xarray
Datasets (not the real 22GB+ pilot download) so these run fast and don't
require the pilot fetch to have completed - the alignment LOGIC is what's
being tested, not the live data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from src.phase3.ensemble_features import to_dataframe


def _make_synthetic_ensemble_stats() -> xr.Dataset:
    init_times = pd.to_datetime(["2021-07-15", "2021-07-16"])
    lead_hours = np.array([24, 48])
    lats = np.array([20.0, 21.5])
    lons = np.array([80.0, 81.5])

    shape = (len(init_times), len(lead_hours), len(lons), len(lats))
    rng = np.random.default_rng(0)

    def var(base):
        return (("init_time", "prediction_timedelta", "longitude", "latitude"), base + rng.uniform(0, 1, size=shape))

    ds = xr.Dataset(
        {
            "total_precipitation_24hr__mean": var(np.full(shape, 5.0)),
            "total_precipitation_24hr__std": var(np.full(shape, 1.0)),
            "total_precipitation_24hr__min": var(np.full(shape, 0.0)),
            "total_precipitation_24hr__max": var(np.full(shape, 10.0)),
            "total_precipitation_24hr__p25": var(np.full(shape, 3.0)),
            "total_precipitation_24hr__p75": var(np.full(shape, 7.0)),
            "2m_temperature__mean": var(np.full(shape, 25.0)),
            "2m_temperature__std": var(np.full(shape, 1.5)),
            "2m_temperature__min": var(np.full(shape, 22.0)),
            "2m_temperature__max": var(np.full(shape, 28.0)),
            "2m_temperature__p25": var(np.full(shape, 24.0)),
            "2m_temperature__p75": var(np.full(shape, 26.0)),
        },
        coords={
            "init_time": init_times,
            "prediction_timedelta": lead_hours,
            "longitude": lons,
            "latitude": lats,
        },
    )
    lead_day = (lead_hours // 24).astype(int)
    ds = ds.assign_coords(lead_day=("prediction_timedelta", lead_day))
    valid_time = (
        ds.init_time
        + xr.DataArray(pd.to_timedelta(lead_hours, unit="h"), dims="prediction_timedelta")
    )
    ds = ds.assign_coords(valid_time=(("init_time", "prediction_timedelta"), valid_time.data))
    return ds


def test_to_dataframe_preserves_row_count():
    ds = _make_synthetic_ensemble_stats()
    df = to_dataframe(ds)
    # 2 init_times x 2 leads x 2 lons x 2 lats = 16 rows
    assert len(df) == 16


def test_to_dataframe_has_required_alignment_columns():
    ds = _make_synthetic_ensemble_stats()
    df = to_dataframe(ds)
    for col in ["init_time", "valid_time", "lead_day", "latitude", "longitude"]:
        assert col in df.columns


def test_valid_time_equals_init_time_plus_lead():
    ds = _make_synthetic_ensemble_stats()
    df = to_dataframe(ds)
    expected = df.init_time + pd.to_timedelta(df.lead_day * 24, unit="h")
    assert (df.valid_time == expected).all()


def test_ensemble_stats_ordering_min_le_p25_le_mean_le_p75_le_max():
    """Sanity check on the synthetic fixture itself, and on to_dataframe's
    pass-through - catches an accidental column-swap bug in to_dataframe."""
    ds = _make_synthetic_ensemble_stats()
    df = to_dataframe(ds)
    assert (df.ensemble_min_precip <= df.ensemble_mean_precip).all()
    assert (df.ensemble_mean_precip <= df.ensemble_max_precip).all()
    assert (df.ensemble_iqr_precip >= 0).all()


def test_ensemble_cv_only_computed_for_precip_not_temp():
    ds = _make_synthetic_ensemble_stats()
    df = to_dataframe(ds)
    assert "ensemble_cv_precip" in df.columns
    assert "ensemble_cv_temp" not in df.columns  # deliberately not computed - see features docstring


def test_no_duplicate_keys_in_ensemble_dataframe():
    ds = _make_synthetic_ensemble_stats()
    df = to_dataframe(ds)
    key_cols = ["init_time", "lead_day", "latitude", "longitude"]
    assert not df.duplicated(key_cols).any()


def _pilot_parquet_path() -> str:
    import os

    from src import config
    from src.phase3.ensemble_features import PILOT_TAG

    return os.path.join(config.RAW_DIR, f"ensemble_pilot_{PILOT_TAG}.parquet")


@pytest.mark.skipif(
    not __import__("os").path.exists(_pilot_parquet_path()),
    reason="ensemble pilot data not fetched yet",
)
def test_live_pilot_grid_matches_deterministic_grid():
    """The ensemble store and the deterministic HRES/ERA5 stores are
    documented (ensemble_data_audit.md) to share the exact same 1.5-degree
    grid - this checks that claim against the actual downloaded pilot data,
    not just the store metadata inspected during the audit."""
    import os

    import pandas as pd

    from src import config
    from src.phase1.dataset import ERROR_DB_PATH

    pilot = pd.read_parquet(_pilot_parquet_path())
    # compare against the FULL grid (all 702 bbox points, not just the 183
    # in-India-domain ones) - the pilot's own grid isn't domain-filtered, so
    # comparing against an already-filtered table would produce false
    # mismatches for legitimate ocean/border grid points.
    deterministic = pd.read_parquet(ERROR_DB_PATH, columns=["latitude", "longitude"])
    pilot_lats = set(pilot.latitude.round(4))
    pilot_lons = set(pilot.longitude.round(4))
    det_lats = set(deterministic.latitude.round(4))
    det_lons = set(deterministic.longitude.round(4))
    # the pilot's own grid values must be a subset of the standard grid's
    # values (same 1.5-degree spacing/origin) - a spatial misalignment
    # (different regridding, off-by-half-cell) would show up as pilot lat/
    # lon values that never appear in the deterministic grid at all.
    assert pilot_lats <= det_lats, f"pilot latitudes not on the standard grid: {pilot_lats - det_lats}"
    assert pilot_lons <= det_lons, f"pilot longitudes not on the standard grid: {pilot_lons - det_lons}"
    assert len(pilot_lats) > 0 and len(pilot_lons) > 0


@pytest.mark.skipif(
    not __import__("os").path.exists(_pilot_parquet_path()),
    reason="ensemble pilot data not fetched yet",
)
def test_live_pilot_init_times_within_declared_window():
    import pandas as pd

    from src.phase3.ensemble_features import PILOT_END, PILOT_START

    pilot = pd.read_parquet(_pilot_parquet_path())
    assert pilot.init_time.min() >= pd.Timestamp(PILOT_START)
    assert pilot.init_time.max() <= pd.Timestamp(PILOT_END) + pd.Timedelta(hours=23)


@pytest.mark.skipif(
    not __import__("os").path.exists(_pilot_parquet_path()),
    reason="ensemble pilot data not fetched yet",
)
def test_live_pilot_lead_days_match_config():
    import pandas as pd

    from src import config

    pilot = pd.read_parquet(_pilot_parquet_path())
    assert set(pilot.lead_day.unique()) <= set(config.LEAD_DAYS)
