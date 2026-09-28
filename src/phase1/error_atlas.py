"""
Phase 1 - Forecast Error Atlas: MAE / RMSE / bias / median-abs-error / bust
rate / heavy-rain miss & false-alarm rate, broken down by lead day, region,
and month - answering "where, when, and at what lead time does the forecast
historically become unreliable?"

Uses the FULL JJAS 2018-2021 sample (train + test) for descriptive analysis -
this is a diagnostic atlas of historical behaviour, not a predictive
evaluation, so there's no train/test leakage concern here (that concern
applies to baselines.py / evaluate.py, which score predictions against a
held-out year).

Usage:
    .venv/Scripts/python.exe -m src.phase1.error_atlas
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from .. import config
from .dataset import build_phase1_dataset

OUT_DIR = os.path.join("outputs", "phase1")

VARIABLES = {
    "precip_mm": ("error_precip_mm", "abs_error_precip_mm"),
    "temp_c": ("error_temp_c", "abs_error_temp_c"),
    "mslp_hpa": ("error_mslp_hpa", "abs_error_mslp_hpa"),
}

MONTH_NAME = {6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep"}


def _metrics_by(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    rows = []
    for keys, g in df.groupby(group_cols, observed=True):
        keys = keys if isinstance(keys, tuple) else (keys,)
        row = dict(zip(group_cols, keys))
        row["n_samples"] = len(g)
        for var, (err_col, abs_err_col) in VARIABLES.items():
            row[f"mae_{var}"] = g[abs_err_col].mean()
            row[f"rmse_{var}"] = np.sqrt((g[err_col] ** 2).mean())
            row[f"bias_{var}"] = g[err_col].mean()  # signed: fcst - obs
            row[f"median_abs_error_{var}"] = g[abs_err_col].median()
        row["bust_rate"] = g.bust_any.mean()
        row["heavy_rain_miss_rate"] = g.missed_heavy_rain_event.mean()
        row["heavy_rain_false_alarm_rate"] = g.false_alarm_heavy_rain.mean()
        rows.append(row)
    out = pd.DataFrame(rows)
    numeric_cols = out.columns.difference(group_cols + ["n_samples"])
    out[numeric_cols] = out[numeric_cols].round(4)
    return out.sort_values(group_cols).reset_index(drop=True)


def build_atlas(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    df = df.copy()
    df["month_name"] = df.month.map(MONTH_NAME)

    by_lead = _metrics_by(df, ["lead_day"])
    by_region = _metrics_by(df.loc[df.region != "Unclassified"], ["region"])
    by_month = _metrics_by(df, ["month_name"])
    by_region_lead = _metrics_by(df.loc[df.region != "Unclassified"], ["region", "lead_day"])

    bust_rate_by_lead = (
        df.groupby("lead_day")
        .agg(
            n_samples=("bust_any", "size"),
            bust_rate=("bust_any", "mean"),
            precip_bust_rate=("bust_precip", "mean"),
            temp_bust_rate=("bust_temp", "mean"),
            heavy_rain_miss_rate=("missed_heavy_rain_event", "mean"),
            heavy_rain_false_alarm_rate=("false_alarm_heavy_rain", "mean"),
        )
        .round(4)
        .reset_index()
    )

    return {
        "error_by_lead": by_lead,
        "error_by_region": by_region,
        "error_by_month": by_month,
        "error_by_region_lead": by_region_lead,
        "bust_rate_by_lead": bust_rate_by_lead,
    }


BUST_COMPONENT_COLS = [
    "bust_precip_categorical",  # fixed IMD bins - NOT normalized per region/lead
    "bust_temp_hard",  # fixed >3degC - NOT normalized per region/lead
    "bust_precip_percentile",  # fit to ~10% exceedance PER (region, lead_day)
    "bust_temp_percentile",  # fit to ~10% exceedance PER (region, lead_day)
    "bust_mslp_percentile",  # fit to ~10% exceedance PER (region, lead_day)
]


def label_composition_by_region(df: pd.DataFrame) -> pd.DataFrame:
    """Rate of each individual bust-flag component, by region.

    Why this matters: bust_any is an OR of 5 flags. Three of them
    (*_percentile) are fit to hit ~(1 - BUST_PERCENTILE) exceedance in EVERY
    (region, lead_day) bucket BY CONSTRUCTION, so they carry almost no
    region/lead signal - they show up at a near-constant rate everywhere.
    Only the two fixed-threshold flags (categorical, temp_hard) carry real,
    un-normalized regional/seasonal signal. Since the percentile flags
    dominate bust_any's occurrence count, this caps how well a simple
    region/lead climatology baseline can ever predict bust_any - see
    outputs/phase1/PHASE1_REPORT.md "important findings".
    """
    out = (
        df.loc[df.region != "Unclassified"]
        .groupby("region")[BUST_COMPONENT_COLS]
        .mean()
        .round(4)
        .reset_index()
    )
    return out


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    ds = build_phase1_dataset()
    atlas = build_atlas(ds.df)
    for name, table in atlas.items():
        path = os.path.join(OUT_DIR, f"{name}.csv")
        table.to_csv(path, index=False)
        print(f"saved {len(table):,} rows -> {path}")

    composition = label_composition_by_region(ds.df)
    comp_path = os.path.join(OUT_DIR, "bust_label_composition_by_region.csv")
    composition.to_csv(comp_path, index=False)
    print(f"saved {len(composition):,} rows -> {comp_path}")

    print("\n--- error_by_lead ---")
    print(atlas["error_by_lead"][["lead_day", "mae_precip_mm", "rmse_precip_mm", "bust_rate"]])
    print("\n--- bust_rate_by_lead ---")
    print(atlas["bust_rate_by_lead"])


if __name__ == "__main__":
    main()
