"""
Phase 2 - B1: reproducible feature-building pipeline.

Builds one row per (init_time, lead_day, grid cell) - the same granularity
error_db.parquet already uses - restricted to the "in India domain" grid
cells from src/phase2/geography.py (183 of 702 points; the rest are ocean/
distant foreign territory, not meaningful for regional bust modeling - see
outputs/phase2/region_assignment_summary.csv).

All historical/climatological features are fit on the TRAIN split (2018-
2020) only and applied unchanged to both splits - see
outputs/phase2/leakage_audit.csv for the full accounting of every feature.

Usage:
    .venv/Scripts/python.exe -m src.phase2.features
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase1.dataset import build_phase1_dataset
from .geography import build_region_map

OUT_DIR = os.path.join("outputs", "phase2")

HIST_GROUP_COLS = ["region_v2", "lead_day", "month"]

TARGET_COLS = ["bust_precip_categorical", "bust_temp_hard"]

FEATURE_COLS = [
    # forecast state
    "fcst_precip_mm", "fcst_temp_c", "fcst_mslp_hpa",
    # spatial
    "latitude", "longitude", "region_v2",
    "fcst_precip_anomaly_vs_domain_mean", "fcst_temp_anomaly_vs_domain_mean",
    # temporal
    "lead_day", "month",
    "precip_forecast_jump", "temp_forecast_jump",
    # historical (train-only fit) - see fit_historical_features()
    "hist_bust_precip_categorical_rate", "hist_bust_temp_hard_rate",
    "hist_mean_abs_error_precip_mm", "hist_mean_abs_error_temp_c",
]


def add_domain_mean_anomaly(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    grp = df.groupby(["init_time", "lead_day"])
    df["fcst_precip_anomaly_vs_domain_mean"] = df.fcst_precip_mm - grp.fcst_precip_mm.transform(
        "mean"
    )
    df["fcst_temp_anomaly_vs_domain_mean"] = df.fcst_temp_c - grp.fcst_temp_c.transform("mean")
    return df


def add_forecast_jump(df: pd.DataFrame) -> pd.DataFrame:
    """precip/temp_forecast_jump = this forecast's value minus the value from
    the run issued exactly 24h earlier, for the SAME valid_time/grid cell
    (i.e. that earlier run's lead_day is this row's lead_day + 1). Both
    values being compared were issued at or before the current forecast's
    issuance time - see outputs/phase2/leakage_audit.csv."""
    key_cols = ["valid_time", "lead_day", "latitude", "longitude"]
    lookup = df[key_cols + ["fcst_precip_mm", "fcst_temp_c"]].copy()
    lookup["lead_day"] = lookup["lead_day"] - 1  # realign the earlier run's key to match on
    lookup = lookup.rename(
        columns={"fcst_precip_mm": "_prev_run_precip", "fcst_temp_c": "_prev_run_temp"}
    )
    df = df.merge(lookup, on=key_cols, how="left")
    df["precip_forecast_jump"] = df.fcst_precip_mm - df._prev_run_precip
    df["temp_forecast_jump"] = df.fcst_temp_c - df._prev_run_temp
    return df.drop(columns=["_prev_run_precip", "_prev_run_temp"])


def fit_historical_features(train: pd.DataFrame) -> dict:
    """Fit every train-only historical lookup once; returns a dict of
    (lookup Series, fallback float) pairs to be applied to both splits."""
    fitted = {}
    for target in TARGET_COLS:
        lookup = train.groupby(HIST_GROUP_COLS, observed=True)[target].mean()
        fitted[f"hist_{target}_rate"] = (lookup, float(train[target].mean()))
    for col in ["abs_error_precip_mm", "abs_error_temp_c"]:
        lookup = train.groupby(HIST_GROUP_COLS, observed=True)[col].mean()
        name = "hist_mean_abs_error_precip_mm" if "precip" in col else "hist_mean_abs_error_temp_c"
        fitted[name] = (lookup, float(train[col].mean()))
    return fitted


def apply_historical_features(df: pd.DataFrame, fitted: dict) -> pd.DataFrame:
    df = df.copy()
    keys = pd.MultiIndex.from_frame(df[HIST_GROUP_COLS])
    for name, (lookup, fallback) in fitted.items():
        pred = keys.map(lookup)
        df[name] = pd.Series(pred, index=df.index, dtype=float).fillna(fallback)
    return df


def build_features() -> tuple[pd.DataFrame, pd.DataFrame]:
    ds = build_phase1_dataset()
    df = ds.df

    region_map = build_region_map()[["latitude", "longitude", "region_v2", "in_india_domain"]]
    df = df.merge(region_map, on=["latitude", "longitude"], how="left")

    # domain-mean anomaly and forecast-jump use the FULL grid (all 702
    # points, both splits) as context, computed BEFORE restricting to the
    # in-India-domain subset - "the broader pattern that day" should mean
    # the whole downloaded grid, not just the already-restricted subset.
    df = add_domain_mean_anomaly(df)
    df = add_forecast_jump(df)

    train_full = df[df.split == "train"]
    fitted = fit_historical_features(train_full)
    df = apply_historical_features(df, fitted)

    in_domain = df[df.in_india_domain].copy()
    in_domain["region_v2"] = in_domain["region_v2"].astype("category")

    train = in_domain[in_domain.split == "train"].reset_index(drop=True)
    test = in_domain[in_domain.split == "test"].reset_index(drop=True)
    return train, test


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    train, test = build_features()

    keep = FEATURE_COLS + TARGET_COLS + ["init_time", "valid_time", "region_v2"]
    keep = list(dict.fromkeys(keep))  # dedupe, preserve order

    train_path = os.path.join(OUT_DIR, "features_train.parquet")
    test_path = os.path.join(OUT_DIR, "features_test.parquet")
    train[keep].to_parquet(train_path, index=False)
    test[keep].to_parquet(test_path, index=False)

    print(f"saved {len(train):,} rows -> {train_path}")
    print(f"saved {len(test):,} rows -> {test_path}")
    print(f"\nfeature columns: {FEATURE_COLS}")
    print(f"targets: {TARGET_COLS}")
    print(f"\ntrain target rates: {train[TARGET_COLS].mean().to_dict()}")
    print(f"test target rates: {test[TARGET_COLS].mean().to_dict()}")
    print(f"\nmissing values in train:\n{train[keep].isna().sum()[train[keep].isna().sum() > 0]}")
    print(f"missing values in test:\n{test[keep].isna().sum()[test[keep].isna().sum() > 0]}")


if __name__ == "__main__":
    main()
