"""
Phase 3 - tests for the atmo/ensemble integration pieces (Model 6, Model 7,
association check). Skips gracefully if the underlying fetched files are
absent (e.g. a fresh checkout that hasn't run fetch_atmo_multi_year.sh /
ensemble_features.py yet), matching the pattern used elsewhere.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest

from src import config
from src.phase3.atmo_merge import LEVEL_FEATURE_COLS, WIND_FEATURE_COLS

WIND_2018_PATH = os.path.join(config.RAW_DIR, "atmo_wind_2018-01-01_2018-12-31.nc")
LEVELS_PATH = os.path.join(config.RAW_DIR, "atmo_levels_2021-07-15_2021-08-04.nc")


@pytest.mark.skipif(not os.path.exists(WIND_2018_PATH), reason="atmo wind data not fetched")
def test_wind_merge_has_full_coverage_no_missing():
    from src.phase2.features import OUT_DIR as PHASE2_OUT_DIR
    from src.phase3.atmo_merge import merge_wind_features

    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))
    merged = merge_wind_features(test, [2021])
    assert merged[WIND_FEATURE_COLS].isna().sum().sum() == 0, (
        "wind is fetched at full JJAS scale - the 2021 test set must merge with zero misses"
    )
    assert len(merged) == len(test)  # no row duplication from the merge


@pytest.mark.skipif(not os.path.exists(WIND_2018_PATH), reason="atmo wind data not fetched")
def test_wind_values_are_physically_plausible():
    from src.phase3.atmo_merge import load_wind_dataframe

    df = load_wind_dataframe([2018])
    assert (df.wind_speed_10m >= 0).all(), "wind speed (a magnitude) cannot be negative"
    assert df.wind_speed_10m.max() < 100, "no sane 10m wind speed forecast should exceed 100 m/s"


@pytest.mark.skipif(not os.path.exists(LEVELS_PATH), reason="atmo levels pilot data not fetched")
def test_levels_pilot_values_are_physically_plausible():
    from src.phase3.atmo_merge import load_levels_dataframe

    df = load_levels_dataframe()
    assert (df.humidity_850hpa >= 0).all(), "specific humidity cannot be negative"
    assert df.humidity_850hpa.max() < 30, "850hPa specific humidity should be well under 30 g/kg"
    assert df.geopotential_500hpa.between(4500, 6500).mean() > 0.95, (
        "500hPa geopotential height should mostly sit in the ~4500-6500m band for this domain/season"
    )


@pytest.mark.skipif(
    not (os.path.exists(WIND_2018_PATH) and os.path.exists(LEVELS_PATH)),
    reason="atmo data not fully fetched",
)
def test_model6_features_do_not_include_rejected_columns():
    from src.phase3.model6_atmosphere import MODEL6_FEATURES
    from src.phase3.sanity_checks import FUTURE_OBSERVATION_COLUMNS

    assert not (FUTURE_OBSERVATION_COLUMNS & set(MODEL6_FEATURES))


def test_ensemble_feature_cols_do_not_include_rejected_columns():
    from src.phase3.ensemble_pilot_experiment import ENSEMBLE_FEATURE_COLS
    from src.phase3.sanity_checks import FUTURE_OBSERVATION_COLUMNS

    assert not (FUTURE_OBSERVATION_COLUMNS & set(ENSEMBLE_FEATURE_COLS))


def test_ablation_results_model6_and_model7_are_documented_as_different_scope():
    """Model 6 (full 2021 test, n~446520) and Model7 (pilot subset,
    n~25620) must never be silently compared as if they had the same test
    set size - this checks the actual recorded n values stay far apart,
    catching a future refactor that accidentally unifies them."""
    path = os.path.join("outputs", "phase3", "ablation_results.csv")
    if not os.path.exists(path):
        pytest.skip("ablation_results.csv not generated yet")
    df = pd.read_csv(path)
    if "Model6_Atmosphere_Wind" not in df.model.values or "Model7_Ensemble_pilot_subset" not in df.model.values:
        pytest.skip("Model6/Model7 rows not present yet")
    n6 = df[df.model == "Model6_Atmosphere_Wind"].n.iloc[0]
    n7 = df[df.model == "Model7_Ensemble_pilot_subset"].n.iloc[0]
    assert n6 > 10 * n7, "Model6 (full-scale) and Model7 (pilot-scale) sample sizes should differ by an order of magnitude"
