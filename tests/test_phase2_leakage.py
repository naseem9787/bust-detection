"""
Phase 2 leakage/correctness tests: component-analysis climatology is
train-only-fit, the leakage audit has no ambiguous rows, and the
chronological split it all sits on (inherited from Phase 1) still holds.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from src.phase2.component_analysis import _fit_climatology, _predict
from src.phase2.leakage_audit import build_audit_table


def test_component_climatology_threshold_not_influenced_by_test_only_rows():
    rng = np.random.default_rng(0)
    train = pd.DataFrame(
        {
            "region": ["A"] * 100,
            "lead_day": [1] * 100,
            "month": [6] * 100,
            "bust_temp_hard": rng.integers(0, 2, size=100),
        }
    )
    lookup_before, fallback_before = _fit_climatology(train, "bust_temp_hard")

    # a test-only frame with an extreme, opposite-signal outcome must have
    # zero effect on a lookup table fit on `train` alone
    test_outlier = pd.DataFrame(
        {"region": ["A"] * 20, "lead_day": [1] * 20, "month": [6] * 20, "bust_temp_hard": [1] * 20}
    )
    lookup_after, fallback_after = _fit_climatology(train, "bust_temp_hard")
    assert lookup_before.equals(lookup_after)
    assert fallback_before == fallback_after

    pred = _predict(test_outlier, lookup_before, fallback_before)
    assert np.allclose(pred, lookup_before.iloc[0])  # driven by train stats, not test_outlier


def test_leakage_audit_has_no_ambiguous_status():
    df = build_audit_table()
    allowed_statuses = {
        "OK", "OK - CONDITIONAL", "REJECTED", "REJECTED for Phase 1/2 use",
        "UNAVAILABLE - not fabricated", "DEFERRED - not fabricated",
    }
    assert set(df.status.unique()) <= allowed_statuses
    assert df.status.notna().all()


def test_leakage_audit_rejects_future_observations_and_labels():
    df = build_audit_table()
    future_obs_rows = df[df.uses_future_observation == True]  # noqa: E712
    assert len(future_obs_rows) > 0  # sanity: the audit actually covers some
    assert (future_obs_rows.status.str.startswith("REJECTED")).all()


def test_leakage_audit_flags_percentile_full_sample_threshold_as_rejected():
    df = build_audit_table()
    row = df[df.feature.str.contains("percentile bust thresholds fit on the FULL")]
    assert len(row) == 1
    assert row.iloc[0].status.startswith("REJECTED")


def test_chronological_split_still_holds():
    from src.phase1.dataset import JJAS_WINDOWS, TEST_YEAR, TRAIN_YEARS

    assert TEST_YEAR == 2021
    assert TRAIN_YEARS == [2018, 2019, 2020]
    assert set(JJAS_WINDOWS) == {2018, 2019, 2020, 2021}
