"""
Phase 1 leakage/correctness tests, on small synthetic data (no dependency on
the multi-GB error_db.parquet, so these run fast and don't require Phase 0's
data to be downloaded).

Run:
    .venv/Scripts/python.exe -m pytest tests/ -v
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.phase1.baselines import fit_all_baselines, fit_global_reference, predict
from src.phase1.dataset import JJAS_WINDOWS, _apply_threshold, _fit_percentile_threshold, _jjas_mask


def test_jjas_mask_boundaries():
    dates = pd.to_datetime(
        ["2019-05-31", "2019-06-01", "2019-09-30 12:00", "2019-10-01", "2020-07-15"],
        format="mixed",
    )
    mask = _jjas_mask(pd.Series(dates))
    assert list(mask) == [False, True, True, False, True]


def test_jjas_windows_are_june_to_september():
    for year, (start, end) in JJAS_WINDOWS.items():
        assert start == f"{year}-06-01"
        assert end == f"{year}-09-30"


def test_percentile_threshold_is_not_influenced_by_test_only_outliers():
    """The core Phase-1 leakage fix: injecting an extreme error value into
    TEST-only rows must not move a threshold fit on TRAIN rows."""
    rng = np.random.default_rng(0)
    train = pd.DataFrame(
        {
            "region": ["A"] * 100,
            "lead_day": [1] * 100,
            "abs_error_precip_mm": rng.uniform(0, 10, size=100),
        }
    )
    threshold_before = _fit_percentile_threshold(train, "abs_error_precip_mm")

    # A wildly different, huge-error test set - must have zero effect on a
    # threshold that was fit on `train` alone.
    test_with_outliers = pd.DataFrame(
        {
            "region": ["A"] * 5,
            "lead_day": [1] * 5,
            "abs_error_precip_mm": [1000.0] * 5,
        }
    )
    threshold_after = _fit_percentile_threshold(train, "abs_error_precip_mm")
    assert threshold_before.equals(threshold_after)

    # thresholds should be applicable to the test rows without needing to
    # have been fit on them
    flagged = _apply_threshold(test_with_outliers, "abs_error_precip_mm", threshold_before)
    assert flagged.all()  # 1000mm error is obviously above any 90th percentile of U(0,10)


def test_baseline_fit_uses_only_rows_passed_in():
    """fit_all_baselines must not see anything beyond the frame it's given -
    passing only 'train' rows must not require or touch a 'test' frame."""
    train = pd.DataFrame(
        {
            "region": ["A", "A", "B", "B"] * 5,
            "lead_day": [1, 2, 1, 2] * 5,
            "month": [6, 6, 7, 7] * 5,
            "bust_any": [1, 0, 1, 1] * 5,
        }
    )
    fitted = fit_all_baselines(train)
    assert set(fitted) == {"historical_climatology", "lead_time_only"}
    ref = fit_global_reference(train)
    assert ref == train.bust_any.mean()

    # predicting on an unseen (region, lead_day, month) combo must fall back
    # to the train-global rate, not raise or silently produce NaN
    unseen = pd.DataFrame(
        {"region": ["Z"], "lead_day": [9], "month": [12], "bust_any": [0]}
    )
    pred = predict(fitted["historical_climatology"], unseen)
    assert not np.isnan(pred).any()
    assert pred[0] == fitted["historical_climatology"].global_fallback


def test_train_test_years_are_disjoint():
    from src.phase1.dataset import TEST_YEAR, TRAIN_YEARS

    assert TEST_YEAR not in TRAIN_YEARS
    assert TEST_YEAR == max(JJAS_WINDOWS)
    assert set(TRAIN_YEARS) | {TEST_YEAR} == set(JJAS_WINDOWS)
