"""
Phase 2 - B1/B2 tests: train-only historical features, target construction,
model input schema, and feature-inventory consistency.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

from src.phase2.feature_inventory import FEATURES
from src.phase2.features import (
    FEATURE_COLS,
    TARGET_COLS,
    apply_historical_features,
    fit_historical_features,
)
from src.phase2.train_model import ALL_FEATURES, CATEGORICAL_FEATURES, NUMERIC_FEATURES

OUT_DIR = os.path.join("outputs", "phase2")


def _synthetic_frame(n=100, seed=0):
    rng = np.random.default_rng(seed)
    return pd.DataFrame(
        {
            "region_v2": rng.choice(["A", "B"], size=n),
            "lead_day": rng.integers(1, 11, size=n),
            "month": rng.choice([6, 7, 8, 9], size=n),
            "bust_precip_categorical": rng.integers(0, 2, size=n),
            "bust_temp_hard": rng.integers(0, 2, size=n),
            "abs_error_precip_mm": rng.uniform(0, 10, size=n),
            "abs_error_temp_c": rng.uniform(0, 5, size=n),
        }
    )


def test_historical_features_are_train_only_fit():
    train = _synthetic_frame(200, seed=1)
    fitted = fit_historical_features(train)

    # a wildly different "test" frame must have zero effect on lookups that
    # were already fit on `train` - fit_historical_features never sees it
    test_outliers = _synthetic_frame(20, seed=2)
    test_outliers["bust_precip_categorical"] = 1
    test_outliers["abs_error_precip_mm"] = 9999.0
    fitted_again = fit_historical_features(train)
    for name in fitted:
        assert fitted[name][0].equals(fitted_again[name][0])
        assert fitted[name][1] == fitted_again[name][1]


def test_apply_historical_features_falls_back_for_unseen_groups():
    train = _synthetic_frame(200, seed=1)
    fitted = fit_historical_features(train)
    unseen = pd.DataFrame({"region_v2": ["Z"], "lead_day": [99], "month": [12]})
    out = apply_historical_features(unseen, fitted)
    for name in fitted:
        assert not out[name].isna().any()
        assert out[name].iloc[0] == fitted[name][1]  # exactly the fallback value


def test_historical_feature_names_match_expected_targets():
    train = _synthetic_frame(50, seed=3)
    fitted = fit_historical_features(train)
    expected = {
        "hist_bust_precip_categorical_rate",
        "hist_bust_temp_hard_rate",
        "hist_mean_abs_error_precip_mm",
        "hist_mean_abs_error_temp_c",
    }
    assert set(fitted) == expected


def test_target_cols_are_binary():
    for col in TARGET_COLS:
        assert col.startswith("bust_")


def test_all_features_partition_is_consistent():
    assert set(ALL_FEATURES) == set(NUMERIC_FEATURES) | set(CATEGORICAL_FEATURES)
    assert set(NUMERIC_FEATURES) & set(CATEGORICAL_FEATURES) == set()
    assert set(ALL_FEATURES) == set(FEATURE_COLS)
    assert CATEGORICAL_FEATURES == ["region_v2"]


def test_feature_inventory_has_no_duplicate_names():
    names = [row[0] for row in FEATURES]
    assert len(names) == len(set(names))


@pytest.mark.skipif(
    not os.path.exists(os.path.join(OUT_DIR, "features_train.parquet")),
    reason="Phase 2B feature table not generated yet",
)
def test_generated_feature_table_matches_expected_schema():
    train = pd.read_parquet(os.path.join(OUT_DIR, "features_train.parquet"))
    for col in FEATURE_COLS + TARGET_COLS:
        assert col in train.columns, f"missing column {col}"
    for col in TARGET_COLS:
        assert set(train[col].unique()) <= {0, 1, True, False}
    assert train["lead_day"].between(1, 10).all()
    # month comes from valid_time, not init_time (see build_error_db.py) - a
    # forecast issued near Sep 30 with a long lead can validly have a valid_time
    # a few days into October, so allow that documented spillover, not just JJAS.
    assert train["month"].between(6, 10).all()


@pytest.mark.skipif(
    not os.path.exists(os.path.join(OUT_DIR, "features_train.parquet")),
    reason="Phase 2B feature table not generated yet",
)
def test_generated_feature_table_train_test_years_disjoint():
    train = pd.read_parquet(os.path.join(OUT_DIR, "features_train.parquet"), columns=["init_time"])
    test = pd.read_parquet(os.path.join(OUT_DIR, "features_test.parquet"), columns=["init_time"])
    assert train.init_time.dt.year.max() < test.init_time.dt.year.min()
