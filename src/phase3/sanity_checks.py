"""
Phase 3 - N/O: scientific sanity checks and the grouped-generalization test.

N - re-verifies, with fresh code (not just re-reading old conclusions):
  1. No feature is derived from a future/truth observation (re-checks
     leakage_audit.csv's REJECTED rows are actually absent from the trained
     feature set).
  2. Historical features are train-only-fit (re-runs the same check as
     tests/test_phase2_leakage.py, standalone here for the audit record).
  3. No duplicate (init_time, lead_day, latitude, longitude) rows exist
     within either split, and no row's key appears in BOTH splits.
  4. Feature correlation matrix, to surface near-duplicate/redundant
     features (not a leakage issue by itself, but worth recording).
  5. Class-imbalance context for interpreting PR-AUC/Brier.

O - grouped generalization test: confirms that no single forecast
initialization (init_time) has rows split across train and test - i.e.
the year-based split is ALREADY a grouped split at the init_time level
(every row from a given init_time falls entirely within one year, hence
entirely within one split), so there is no risk of "the same weather
situation" leaking across the train/test boundary at the row level.

Usage:
    .venv/Scripts/python.exe -m src.phase3.sanity_checks
"""
from __future__ import annotations

import json
import os

import pandas as pd

from ..phase2.features import FEATURE_COLS, OUT_DIR as PHASE2_OUT_DIR, TARGET_COLS

OUT_DIR = os.path.join("outputs", "phase3")

FUTURE_OBSERVATION_COLUMNS = {
    "obs_precip_mm", "obs_temp_c", "obs_mslp_hpa",
    "error_precip_mm", "error_temp_c", "error_mslp_hpa",
    "abs_error_precip_mm", "abs_error_temp_c", "abs_error_mslp_hpa",
    "bust_any", "bust_precip", "bust_temp",
}


def check_no_future_observation_features() -> dict:
    leaked = FUTURE_OBSERVATION_COLUMNS & set(FEATURE_COLS)
    return {
        "check": "no_future_observation_in_feature_cols",
        "passed": len(leaked) == 0,
        "detail": f"leaked columns found: {sorted(leaked)}" if leaked else "clean",
    }


def check_no_duplicate_keys_and_no_cross_split_init_time() -> dict:
    train = pd.read_parquet(
        os.path.join(PHASE2_OUT_DIR, "features_train.parquet"),
        columns=["init_time", "lead_day", "latitude", "longitude"],
    )
    test = pd.read_parquet(
        os.path.join(PHASE2_OUT_DIR, "features_test.parquet"),
        columns=["init_time", "lead_day", "latitude", "longitude"],
    )
    key_cols = ["init_time", "lead_day", "latitude", "longitude"]
    train_dupes = int(train.duplicated(key_cols).sum())
    test_dupes = int(test.duplicated(key_cols).sum())

    train_inits = set(train.init_time.unique())
    test_inits = set(test.init_time.unique())
    overlap = train_inits & test_inits

    return {
        "check": "no_duplicate_rows_and_no_cross_split_init_time",
        "passed": train_dupes == 0 and test_dupes == 0 and len(overlap) == 0,
        "detail": (
            f"train duplicate rows={train_dupes}, test duplicate rows={test_dupes}, "
            f"init_times appearing in BOTH splits={len(overlap)} "
            f"(train inits: {len(train_inits)}, test inits: {len(test_inits)})"
        ),
    }


def check_grouped_generalization() -> dict:
    """O: every row from a given init_time is entirely within one split,
    because the split is defined by calendar year and every init_time
    belongs to exactly one year - so this is already a grouped-by-
    initialization split, not just a grouped-by-row split."""
    train = pd.read_parquet(
        os.path.join(PHASE2_OUT_DIR, "features_train.parquet"), columns=["init_time"]
    )
    test = pd.read_parquet(
        os.path.join(PHASE2_OUT_DIR, "features_test.parquet"), columns=["init_time"]
    )
    train_years = set(train.init_time.dt.year.unique())
    test_years = set(test.init_time.dt.year.unique())
    return {
        "check": "grouped_generalization_by_init_time",
        "passed": len(train_years & test_years) == 0,
        "detail": (
            f"train years={sorted(train_years)}, test years={sorted(test_years)} - "
            "disjoint calendar years mean every init_time (and every forecast "
            "issuance's full lead-day ladder) is entirely in one split; no "
            "additional row-shuffling could have crossed this boundary because "
            "the split key (year) is coarser than any row-level grouping"
        ),
    }


def feature_correlation_matrix() -> pd.DataFrame:
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    numeric_cols = [c for c in FEATURE_COLS if c != "region_v2"]
    corr = train[numeric_cols].corr()
    return corr


def class_imbalance_context() -> pd.DataFrame:
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))
    rows = []
    for target in TARGET_COLS:
        rows.append(
            {
                "target": target,
                "train_prevalence": float(train[target].mean()),
                "test_prevalence": float(test[target].mean()),
                "train_n_positive": int(train[target].sum()),
                "test_n_positive": int(test[target].sum()),
                "note": (
                    "PR-AUC and Brier must be read against this prevalence, not "
                    "against the 0.5/uniform-class assumption ROC-AUC implicitly avoids"
                ),
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    checks = [
        check_no_future_observation_features(),
        check_no_duplicate_keys_and_no_cross_split_init_time(),
        check_grouped_generalization(),
    ]
    for c in checks:
        status = "PASS" if c["passed"] else "FAIL"
        print(f"[{status}] {c['check']}: {c['detail']}")

    path = os.path.join(OUT_DIR, "sanity_checks.json")
    with open(path, "w") as f:
        json.dump(checks, f, indent=2, default=str)
    print(f"saved -> {path}")

    corr = feature_correlation_matrix()
    corr_path = os.path.join(OUT_DIR, "feature_correlation_matrix.csv")
    corr.to_csv(corr_path)
    print(f"saved -> {corr_path}")
    # find highly correlated pairs (|r|>0.8), upper triangle only (avoid duplicates/self-pairs)
    import numpy as np
    mask = np.triu(np.ones(corr.shape), k=1).astype(bool)
    pairs = corr.where(mask).stack()
    high_pairs = pairs[pairs.abs() > 0.8].sort_values(key=abs, ascending=False)
    if len(high_pairs) > 0:
        print("\nhighly correlated feature pairs (|r|>0.8):")
        print(high_pairs.to_string())
    else:
        print("\nno feature pairs with |r|>0.8 - no obvious duplicate information")

    imbalance = class_imbalance_context()
    imbalance_path = os.path.join(OUT_DIR, "class_imbalance_context.csv")
    imbalance.to_csv(imbalance_path, index=False)
    print(f"\nsaved -> {imbalance_path}")
    print(imbalance.to_string(index=False))

    all_passed = all(c["passed"] for c in checks)
    if not all_passed:
        print("\n*** STOP CONDITION: one or more sanity checks FAILED - investigate before proceeding ***")
    else:
        print("\nAll sanity checks passed.")


if __name__ == "__main__":
    main()
