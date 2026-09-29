"""
Phase 5 - reference dataset assembly for the analog database. Reuses
Phase 2/3's own functions (no re-implementation): `data_assembly` for the
in-India-domain, JJAS 2018-2021 base table with bust labels, and
`atmo_merge` for the full-scale wind feature - the exact same dataset
Phase 4's `temperature_v1` was trained on, so analogs and the production
model are describing the same forecast reality.

Usage:
    .venv/Scripts/python.exe -m src.phase5.dataset
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2.features import TARGET_COLS
from ..phase3.atmo_merge import WIND_FEATURE_COLS, merge_wind_features
from ..phase3.data_assembly import build_experiment_features, build_full_domain_base

OUT_DIR = os.path.join("outputs", "phase5")

TRAIN_YEARS = [2018, 2019, 2020]
TEST_YEAR = 2021

KEEP_COLS = [
    "init_time", "valid_time", "lead_day", "latitude", "longitude", "region_v2", "month", "year",
    "fcst_precip_mm", "fcst_temp_c", "fcst_mslp_hpa", "wind_speed_10m",
    "precip_forecast_jump", "temp_forecast_jump",
    # not part of the analog SIMILARITY vector (see feature_vector.py's
    # documented exclusions) but kept in the reference table so
    # analog_enhanced_model.py can train a Model-6-equivalent (GROUP5+wind)
    # baseline for a fair comparison against the analog-enhanced variant
    "fcst_precip_anomaly_vs_domain_mean", "fcst_temp_anomaly_vs_domain_mean",
    "hist_bust_precip_categorical_rate", "hist_bust_temp_hard_rate",
    "hist_mean_abs_error_precip_mm", "hist_mean_abs_error_temp_c",
    "obs_precip_mm", "obs_temp_c", "obs_mslp_hpa",
    "error_precip_mm", "error_temp_c", "abs_error_precip_mm", "abs_error_temp_c",
    "bust_precip_categorical", "bust_temp_hard", "bust_precip", "bust_temp",
    "missed_heavy_rain_event", "false_alarm_heavy_rain",
]


def build_reference_dataset() -> pd.DataFrame:
    """Full analog reference table: 2018-2021 JJAS, in-India-domain, with
    wind merged in and leak-free bust labels (train-only-fit thresholds,
    fit on the SAME 2018-2020/2021 split Phase 2-4 use)."""
    base = build_full_domain_base()
    train, test = build_experiment_features(base, TRAIN_YEARS, TEST_YEAR)
    train = train.copy()
    test = test.copy()
    train["split"] = "train"
    test["split"] = "test"
    full = pd.concat([train, test], ignore_index=True)

    full = merge_wind_features(full, TRAIN_YEARS + [TEST_YEAR])
    n_missing_wind = full["wind_speed_10m"].isna().sum()
    if n_missing_wind:
        print(f"warning: {n_missing_wind} rows missing wind_speed_10m - dropping")
        full = full.dropna(subset=["wind_speed_10m"])

    full["year"] = full.init_time.dt.year

    # precip/temp_forecast_jump is NaN at lead_day=10 (no lead_day+1 to
    # compare against) and at a few JJAS-window start/end boundary rows -
    # same documented gap as src/phase2/features.py. Filled with 0.0
    # ("no jump information available"), matching the exact fallback
    # convention already used by src/production/features.py at inference
    # time - never silently dropped from the reference database, since
    # that would remove lead_day=10 analogs entirely.
    n_missing_jump = full[["precip_forecast_jump", "temp_forecast_jump"]].isna().any(axis=1).sum()
    print(f"filling {n_missing_jump:,} rows' missing forecast-jump with 0.0 (documented fallback)")
    full["precip_forecast_jump"] = full["precip_forecast_jump"].fillna(0.0)
    full["temp_forecast_jump"] = full["temp_forecast_jump"].fillna(0.0)

    keep = [c for c in KEEP_COLS if c in full.columns] + ["split"]
    return full[keep].reset_index(drop=True)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    df = build_reference_dataset()
    path = os.path.join(OUT_DIR, "analog_reference_dataset.parquet")
    df.to_parquet(path, index=False)
    print(f"saved {len(df):,} rows -> {path}")
    print(f"train: {(df.split == 'train').sum():,}  test: {(df.split == 'test').sum():,}")
    print(f"years: {sorted(df.year.unique())}")
    print(f"months: {sorted(df.month.unique())}")
    print(f"regions: {df.region_v2.nunique()}")


if __name__ == "__main__":
    main()
