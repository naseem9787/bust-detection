"""
Phase 0 - Step 3: label each row of the error database as a "forecast bust"
or not, using two complementary rules:

  1. Percentile rule: |error| exceeds the 90th percentile (config.BUST_PERCENTILE)
     of the historical |error| distribution for that (region, lead_day) bucket.
     This is region- and lead-time-aware: a Day-10 error that's normal for
     Day 10 doesn't get flagged just because it looks big in absolute terms.

  2. Rainfall-category rule (IMD bins): flags a bust when the forecast and
     observed rainfall categories are 2+ steps apart, or a heavy-or-above
     event is missed / falsely predicted - independent of how "normal" that
     error is, because a missed heavy-rain warning matters operationally
     even if the model often gets that lead time wrong.

  3. Temperature hard threshold: |error| > 3 degC always counts as a bust
     (catches heat-wave-relevant misses even where the local error
     distribution is unusually spread out).

Usage:
    .venv/Scripts/python.exe -m src.label_busts

Input:  data/processed/error_db.parquet
Output: data/processed/bust_labels.parquet
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from . import config


def _rain_category(mm: pd.Series) -> pd.Series:
    """Returns a categorical Series (not a bare Categorical) - pd.cut on a
    Series input already gives back a Series with categorical dtype, whose
    codes live under `.cat.codes`, not `.codes`."""
    return pd.cut(
        mm, bins=config.IMD_RAIN_BINS, labels=config.IMD_RAIN_LABELS, right=True
    )


def add_percentile_thresholds(df: pd.DataFrame, col: str, group_cols: list[str]) -> pd.Series:
    q = config.BUST_PERCENTILE
    thresh = df.groupby(group_cols)[col].transform(lambda s: s.quantile(q))
    return df[col] > thresh


def main() -> None:
    in_path = os.path.join(config.PROCESSED_DIR, "error_db.parquet")
    if not os.path.exists(in_path):
        raise SystemExit(f"{in_path} not found - run build_error_db.py first.")
    df = pd.read_parquet(in_path)

    # --- rainfall category miss ------------------------------------------------
    fcst_cat = _rain_category(df.fcst_precip_mm)
    obs_cat = _rain_category(df.obs_precip_mm)
    fcst_code = fcst_cat.cat.codes.astype(int)
    obs_code = obs_cat.cat.codes.astype(int)
    df["fcst_rain_category"] = fcst_cat
    df["obs_rain_category"] = obs_cat
    category_gap = np.abs(fcst_code - obs_code)

    heavy_idx = config.HEAVY_OR_ABOVE_INDEX
    missed_heavy = (obs_code >= heavy_idx) & (fcst_code < heavy_idx)
    false_alarm_heavy = (fcst_code >= heavy_idx) & (obs_code < heavy_idx)
    df["bust_precip_categorical"] = (category_gap >= 2) | missed_heavy | false_alarm_heavy
    df["missed_heavy_rain_event"] = missed_heavy
    df["false_alarm_heavy_rain"] = false_alarm_heavy

    # --- percentile rule, per (region, lead_day) --------------------------------
    group_cols = ["region", "lead_day"]
    df["bust_precip_percentile"] = add_percentile_thresholds(df, "abs_error_precip_mm", group_cols)
    df["bust_temp_percentile"] = add_percentile_thresholds(df, "abs_error_temp_c", group_cols)
    df["bust_mslp_percentile"] = add_percentile_thresholds(df, "abs_error_mslp_hpa", group_cols)

    # --- temperature hard threshold ---------------------------------------------
    df["bust_temp_hard"] = df.abs_error_temp_c > config.TEMP_BUST_ABS_ERROR_K

    # --- combined flags ----------------------------------------------------------
    df["bust_precip"] = df.bust_precip_categorical | df.bust_precip_percentile
    df["bust_temp"] = df.bust_temp_percentile | df.bust_temp_hard
    df["bust_any"] = df.bust_precip | df.bust_temp | df.bust_mslp_percentile

    # a simple 0-1 "confidence" score for the dashboard: 1 - fraction of bust
    # rules triggered (crude for Phase 0; Phase 2 replaces this with a
    # calibrated model probability).
    bust_flags = df[["bust_precip", "bust_temp", "bust_mslp_percentile"]].astype(int)
    df["forecast_confidence"] = 1.0 - bust_flags.mean(axis=1)

    out_path = os.path.join(config.PROCESSED_DIR, "bust_labels.parquet")
    df.to_parquet(out_path, index=False)
    print(f"saved {len(df):,} labeled rows -> {out_path}")

    print(f"\noverall bust rate: {df.bust_any.mean():.1%}")
    print(f"  precip bust rate: {df.bust_precip.mean():.1%}")
    print(f"  temp bust rate:   {df.bust_temp.mean():.1%}")
    print(f"  missed heavy-rain events: {df.missed_heavy_rain_event.sum():,}")
    print(f"  false-alarm heavy-rain:   {df.false_alarm_heavy_rain.sum():,}")

    print("\nbust rate by lead day:")
    print((df.groupby("lead_day").bust_any.mean() * 100).round(1).astype(str) + "%")

    print("\ntop 10 (region, lead_day) combos by bust rate (min 20 samples):")
    grp = df.groupby(["region", "lead_day"]).agg(
        n=("bust_any", "size"), bust_rate=("bust_any", "mean")
    )
    grp = grp[grp.n >= 20].sort_values("bust_rate", ascending=False).head(10)
    grp["bust_rate"] = (grp.bust_rate * 100).round(1).astype(str) + "%"
    print(grp)


if __name__ == "__main__":
    main()
