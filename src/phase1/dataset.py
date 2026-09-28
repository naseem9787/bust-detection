"""
Phase 1 - dataset loader: the JJAS 2018-2021 experiment window, with
leak-free bust labels for chronological train/test evaluation.

Reuses Phase 0's already-downloaded/processed data (data/processed/error_db.parquet,
built from the full-calendar-year 2018-01-01..2021-12-31 raw NetCDFs) - no
re-fetching from GCS is needed. This module does NOT modify anything under
src/config.py, src/regions.py, src/fetch_data.py, src/build_error_db.py, or
src/label_busts.py; Phase 0 stays exactly as it was.

Why this module recomputes bust labels instead of reusing
data/processed/bust_labels.parquet directly
--------------------------------------------------------------------------
Phase 0's label_busts.py fits its percentile-based bust threshold
(config.BUST_PERCENTILE, per region x lead_day) on the ENTIRE available
sample - which, now that the sample spans 2018-2021, includes the 2021 data
Phase 1 is supposed to hold out as an unseen test year. Using that threshold
to label the 2021 test rows would leak 2021 statistics into the definition
of "bust" being evaluated on 2021 - a real, if subtle, form of data leakage.

Phase 1 instead:
  1. Filters error_db.parquet (raw forecast/obs/error values, no bust flags)
     down to the explicit JJAS windows below.
  2. Refits the percentile threshold using ONLY the training period
     (2018-2020) rows.
  3. Applies that fixed, train-only threshold to label BOTH train and test
     rows.
The IMD rainfall-category rule and the temperature hard-threshold rule are
fixed physical constants (config.IMD_RAIN_BINS, config.TEMP_BUST_ABS_ERROR_K)
that don't depend on the sample, so they carry over unchanged from Phase 0 -
no leakage risk there, and no need to refit them.

This is the ONLY difference from Phase 0's bust definition; the resulting
bust rates are very close numerically to data/processed/bust_labels.parquet
(see outputs/phase1/dataset_summary.md for both figures side by side).
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np
import pandas as pd

from .. import config
from ..label_busts import _rain_category

# --- explicit JJAS experiment window ---------------------------------------
# init_time (forecast issuance date), inclusive on both ends - matches the
# convention already used by config.DEFAULT_START/DEFAULT_END and
# fetch_data.py's `ds.sel(time=slice(start, end))`. Filtering here happens
# on data already downloaded for the full calendar year, so this is exact.
JJAS_WINDOWS: dict[int, tuple[str, str]] = {
    2018: ("2018-06-01", "2018-09-30"),
    2019: ("2019-06-01", "2019-09-30"),
    2020: ("2020-06-01", "2020-09-30"),
    2021: ("2021-06-01", "2021-09-30"),
}
TRAIN_YEARS = [2018, 2019, 2020]
TEST_YEAR = 2021

ERROR_DB_PATH = os.path.join(config.PROCESSED_DIR, "error_db.parquet")

ERROR_COLS = {
    "precip_mm": ("fcst_precip_mm", "obs_precip_mm"),
    "temp_c": ("fcst_temp_c", "obs_temp_c"),
    "mslp_hpa": ("fcst_mslp_hpa", "obs_mslp_hpa"),
}


@dataclass
class Phase1Dataset:
    df: pd.DataFrame
    train_threshold_precip: pd.DataFrame  # (region, lead_day) -> threshold
    train_threshold_temp: pd.DataFrame
    train_threshold_mslp: pd.DataFrame


def _jjas_mask(init_time: pd.Series) -> pd.Series:
    mask = pd.Series(False, index=init_time.index)
    for start, end in JJAS_WINDOWS.values():
        mask |= (init_time >= pd.Timestamp(start)) & (
            init_time <= pd.Timestamp(end) + pd.Timedelta(hours=23, minutes=59, seconds=59)
        )
    return mask


def load_error_db_jjas(path: str = ERROR_DB_PATH) -> pd.DataFrame:
    """Load error_db.parquet and filter to the JJAS 2018-2021 init_time windows."""
    if not os.path.exists(path):
        raise SystemExit(
            f"{path} not found. Run Phase 0 first "
            "(fetch_multi_year.sh 2018 2021, or run_phase0.py) - see README."
        )
    df = pd.read_parquet(path)
    df = df.loc[_jjas_mask(df.init_time)].copy()
    if df.empty:
        raise SystemExit(
            "JJAS filter produced 0 rows - check that error_db.parquet actually "
            "covers 2018-01-01..2021-12-31 (it should, from the full-year fetch)."
        )
    df["year"] = df.init_time.dt.year
    missing_years = sorted(set(JJAS_WINDOWS) - set(df.year.unique()))
    if missing_years:
        raise SystemExit(
            f"error_db.parquet is missing JJAS data for year(s) {missing_years} - "
            "re-run fetch_multi_year.sh for those years first."
        )
    return df


def _fit_percentile_threshold(train: pd.DataFrame, abs_err_col: str) -> pd.Series:
    """90th-percentile |error| threshold per (region, lead_day), fit on TRAIN
    rows only. Returned as a Series indexed by (region, lead_day)."""
    return train.groupby(["region", "lead_day"])[abs_err_col].quantile(config.BUST_PERCENTILE)


def _apply_threshold(df: pd.DataFrame, abs_err_col: str, thresholds: pd.Series) -> pd.Series:
    thresh_per_row = df.set_index(["region", "lead_day"]).index.map(thresholds)
    thresh_per_row = pd.Series(thresh_per_row, index=df.index, dtype=float)
    return df[abs_err_col] > thresh_per_row


def build_phase1_dataset(path: str = ERROR_DB_PATH) -> Phase1Dataset:
    """Load JJAS 2018-2021, split chronologically (train=2018-2020, test=2021),
    and label busts with thresholds fit on the training split only."""
    df = load_error_db_jjas(path)
    train_mask = df.year.isin(TRAIN_YEARS)
    train = df.loc[train_mask]

    # --- rainfall category-miss rule (fixed physical bins - no fitting) --------
    fcst_cat = _rain_category(df.fcst_precip_mm)
    obs_cat = _rain_category(df.obs_precip_mm)
    fcst_code = fcst_cat.cat.codes.astype(int)
    obs_code = obs_cat.cat.codes.astype(int)
    category_gap = np.abs(fcst_code - obs_code)
    heavy_idx = config.HEAVY_OR_ABOVE_INDEX
    missed_heavy = (obs_code >= heavy_idx) & (fcst_code < heavy_idx)
    false_alarm_heavy = (fcst_code >= heavy_idx) & (obs_code < heavy_idx)
    df["fcst_rain_category"] = fcst_cat
    df["obs_rain_category"] = obs_cat
    df["missed_heavy_rain_event"] = missed_heavy
    df["false_alarm_heavy_rain"] = false_alarm_heavy
    df["bust_precip_categorical"] = (category_gap >= 2) | missed_heavy | false_alarm_heavy

    # --- percentile rule, thresholds fit on TRAIN only --------------------------
    thresh_precip = _fit_percentile_threshold(train, "abs_error_precip_mm")
    thresh_temp = _fit_percentile_threshold(train, "abs_error_temp_c")
    thresh_mslp = _fit_percentile_threshold(train, "abs_error_mslp_hpa")
    df["bust_precip_percentile"] = _apply_threshold(df, "abs_error_precip_mm", thresh_precip)
    df["bust_temp_percentile"] = _apply_threshold(df, "abs_error_temp_c", thresh_temp)
    df["bust_mslp_percentile"] = _apply_threshold(df, "abs_error_mslp_hpa", thresh_mslp)

    # --- temperature hard threshold (fixed constant - no fitting) --------------
    df["bust_temp_hard"] = df.abs_error_temp_c > config.TEMP_BUST_ABS_ERROR_K

    # --- combined flags, same combination logic as Phase 0's label_busts.py ----
    df["bust_precip"] = df.bust_precip_categorical | df.bust_precip_percentile
    df["bust_temp"] = df.bust_temp_percentile | df.bust_temp_hard
    df["bust_any"] = df.bust_precip | df.bust_temp | df.bust_mslp_percentile

    df["split"] = np.where(df.year.isin(TRAIN_YEARS), "train", "test")

    return Phase1Dataset(
        df=df,
        train_threshold_precip=thresh_precip.rename("threshold_abs_error_precip_mm"),
        train_threshold_temp=thresh_temp.rename("threshold_abs_error_temp_c"),
        train_threshold_mslp=thresh_mslp.rename("threshold_abs_error_mslp_hpa"),
    )
