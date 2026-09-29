"""
Phase 5 - analog search engine tests: similarity, leakage, spatial,
temporal, and index build/load/query consistency.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from src.phase5.analogs import INDEX_DIR, AnalogIndex
from src.phase5.feature_vector import ANALOG_FEATURE_COLS

INDEX_AVAILABLE = os.path.exists(os.path.join(INDEX_DIR, "reference.parquet"))
pytestmark = pytest.mark.skipif(not INDEX_AVAILABLE, reason="analog index not built yet")


@pytest.fixture(scope="module")
def index():
    idx = AnalogIndex.load(INDEX_DIR)
    idx.warm_cache()
    return idx


@pytest.fixture(scope="module")
def sample_query(index):
    ref = index.reference_df
    row = ref[(ref.split == "test") & (ref.region_v2 == "Madhya Pradesh")].iloc[100]
    return row.to_dict()


def test_query_is_deterministic(index, sample_query):
    r1 = index.query(sample_query, k=5, spatial_constraint="same_region")
    r2 = index.query(sample_query, k=5, spatial_constraint="same_region")
    assert r1.status == r2.status
    if r1.status == "ok":
        assert [a.distance for a in r1.analogs] == [a.distance for a in r2.analogs]
        assert [a.historical_init_time for a in r1.analogs] == [a.historical_init_time for a in r2.analogs]


def test_analogs_are_correctly_ranked_by_distance(index, sample_query):
    result = index.query(sample_query, k=10, spatial_constraint="same_region")
    if result.status != "ok":
        pytest.skip("no analogs for this sample query")
    distances = [a.distance for a in result.analogs]
    assert distances == sorted(distances)
    ranks = [a.rank for a in result.analogs]
    assert ranks == list(range(1, len(ranks) + 1))


def test_similarity_is_monotonically_decreasing_in_distance(index, sample_query):
    result = index.query(sample_query, k=10, spatial_constraint="same_region")
    if result.status != "ok":
        pytest.skip("no analogs for this sample query")
    for a in result.analogs:
        # distance is computed on a float32 feature matrix (see
        # feature_vector.AnalogScaler.transform), so a float64 recomputation
        # from the stored (already float32-rounded) distance can differ at
        # the ~1e-7 relative precision level - not a bug, just float32 vs
        # float64 arithmetic, hence the looser (still tight) tolerance.
        assert abs(a.similarity - 1.0 / (1.0 + a.distance)) < 1e-6
        assert 0 < a.similarity <= 1.0


def test_features_are_standardized_before_distance():
    """AnalogScaler must be fit (mean/std computed) - a query vector for a
    feature far from the mean should get a non-trivial |z| contribution,
    not be silently ignored."""
    from src.phase5.feature_vector import AnalogScaler

    df = pd.DataFrame(
        {c: np.random.default_rng(0).normal(size=100) for c in ANALOG_FEATURE_COLS}
    )
    scaler = AnalogScaler().fit(df)
    z = scaler.transform(df)
    assert abs(z.mean()) < 0.5  # standardized data should be ~mean 0
    assert 0.5 < z.std() < 2.0  # ~unit variance


def test_current_case_excludes_itself(index):
    ref = index.reference_df
    row = ref[ref.split == "test"].iloc[0]
    q = row.to_dict()
    key = (q["init_time"], q["lead_day"], q["latitude"], q["longitude"])
    result = index.query(q, k=10, spatial_constraint="india_wide", exclude_key=key)
    if result.status == "ok":
        for a in result.analogs:
            found_self = (
                a.historical_init_time == key[0] and a.lead_day == key[1]
                and a.latitude == key[2] and a.longitude == key[3]
            )
            assert not found_self, "query retrieved its own exact record"


def test_no_future_analogs_in_retrospective_mode(index):
    """as_of defaults to the query's own init_time - no returned analog may
    have an init_time >= as_of (i.e. no future-relative-to-query leakage)."""
    ref = index.reference_df
    row = ref[(ref.split == "test") & (ref.lead_day == 5)].iloc[50]
    q = row.to_dict()
    result = index.query(q, k=10, spatial_constraint="india_wide")
    if result.status == "ok":
        for a in result.analogs:
            assert a.historical_init_time < q["init_time"]


def test_explicit_as_of_cutoff_is_respected(index):
    ref = index.reference_df
    row = ref[(ref.split == "test") & (ref.lead_day == 5)].iloc[0]
    q = row.to_dict()
    cutoff = pd.Timestamp("2019-01-01")
    result = index.query(q, k=10, spatial_constraint="india_wide", as_of=cutoff)
    if result.status == "ok":
        for a in result.analogs:
            assert a.historical_init_time < cutoff


def test_same_region_constraint_only_returns_that_region(index, sample_query):
    result = index.query(sample_query, k=10, spatial_constraint="same_region")
    if result.status == "ok":
        for a in result.analogs:
            assert a.region == sample_query["region_v2"]


def test_exact_month_constraint_only_returns_that_month(index, sample_query):
    result = index.query(sample_query, k=10, spatial_constraint="same_region", temporal_constraint="exact_month")
    if result.status == "ok":
        for a in result.analogs:
            assert pd.Timestamp(a.historical_valid_time).month == sample_query["month"] or \
                   pd.Timestamp(a.historical_init_time).month == sample_query["month"]


def test_no_reliable_analogs_for_impossible_constraints(index, sample_query):
    """An absurdly small max_distance must yield the quality-control path,
    not a forced/fabricated result."""
    result = index.query(sample_query, k=10, spatial_constraint="same_region", max_distance=1e-9)
    assert result.status == "no_reliable_analogs"
    assert result.warning is not None


def test_index_build_load_query_consistency(tmp_path):
    ref = pd.DataFrame(
        {
            "init_time": pd.to_datetime(["2018-06-01", "2018-06-02", "2021-06-01"]),
            "valid_time": pd.to_datetime(["2018-06-05", "2018-06-06", "2021-06-05"]),
            "lead_day": [4, 4, 4],
            "latitude": [20.0, 20.0, 20.0],
            "longitude": [78.0, 78.0, 78.0],
            "region_v2": ["A", "A", "A"],
            "month": [6, 6, 6],
            "split": ["train", "train", "test"],
            "fcst_precip_mm": [5.0, 50.0, 6.0],
            "fcst_temp_c": [25.0, 26.0, 25.5],
            "fcst_mslp_hpa": [1005.0, 1004.0, 1005.0],
            "wind_speed_10m": [3.0, 3.5, 3.1],
            "precip_forecast_jump": [0.0, 0.0, 0.0],
            "temp_forecast_jump": [0.0, 0.0, 0.0],
            "obs_precip_mm": [4.5, 45.0, 5.5],
            "obs_temp_c": [24.8, 25.9, 25.3],
            "error_precip_mm": [0.5, 5.0, 0.5],
            "error_temp_c": [0.2, 0.1, 0.2],
            "bust_precip_categorical": [False, True, False],
            "bust_temp_hard": [False, False, False],
        }
    )
    built = AnalogIndex.build(ref)
    save_path = str(tmp_path / "idx")
    built.save(save_path)
    loaded = AnalogIndex.load(save_path)
    assert len(loaded.reference_df) == len(built.reference_df)
    np.testing.assert_array_almost_equal(loaded.feature_matrix, built.feature_matrix)

    q = ref.iloc[2].to_dict()
    r_built = built.query(q, k=1, spatial_constraint="same_region", min_analogs=1)
    r_loaded = loaded.query(q, k=1, spatial_constraint="same_region", min_analogs=1)
    assert r_built.status == r_loaded.status
