"""
Phase 0 - Step 2: turn the cached forecast/truth NetCDFs into a tidy
"error database": one row per (init_time, lead_day, grid cell), with the
forecast value, the observed (truth) value, and the error, for every
variable and every region.

Usage:
    .venv/Scripts/python.exe -m src.build_error_db

Input:  data/raw/forecast_*.nc + matching data/raw/truth_*.nc
Output: data/processed/error_db.parquet
"""
from __future__ import annotations

import glob
import os

import numpy as np
import pandas as pd
import xarray as xr

from . import config
from .regions import assign_region

VAR_RENAME_FCST = {
    "total_precipitation_24hr": "fcst_precip_mm",
    "2m_temperature": "fcst_temp_c",
    "mean_sea_level_pressure": "fcst_mslp_hpa",
}
VAR_RENAME_TRUTH = {
    "total_precipitation_24hr": "obs_precip_mm",
    "2m_temperature": "obs_temp_c",
    "mean_sea_level_pressure": "obs_mslp_hpa",
}


def _season(month: int) -> str:
    if month in (6, 7, 8, 9):
        return "monsoon_JJAS"
    if month in (12, 1, 2):
        return "winter_DJF"
    if month in (3, 4, 5):
        return "pre_monsoon_MAM"
    return "post_monsoon_ON"


def _region_lookup_table(lats: np.ndarray, lons: np.ndarray) -> pd.DataFrame:
    """Precompute region for every unique (lat, lon) grid point once, instead
    of calling assign_region per row."""
    pts = pd.MultiIndex.from_product([lats, lons], names=["latitude", "longitude"]).to_frame(
        index=False
    )
    pts["region"] = [assign_region(lat, lon) for lat, lon in zip(pts.latitude, pts.longitude)]
    return pts


def load_pair(fcst_path: str, truth_path: str) -> pd.DataFrame:
    dsf = xr.open_dataset(fcst_path)
    dst = xr.open_dataset(truth_path)

    df_f = dsf.to_dataframe().reset_index().rename(columns=VAR_RENAME_FCST)
    df_t = (
        dst.to_dataframe()
        .reset_index()
        .rename(columns={"time": "valid_time", **VAR_RENAME_TRUTH})
    )

    merged = df_f.merge(
        df_t[["valid_time", "longitude", "latitude", *VAR_RENAME_TRUTH.values()]],
        on=["valid_time", "longitude", "latitude"],
        how="left",
    )

    n_before = len(merged)
    merged = merged.dropna(subset=list(VAR_RENAME_TRUTH.values()) + list(VAR_RENAME_FCST.values()))
    n_after = len(merged)
    if n_after < n_before:
        print(
            f"  dropped {n_before - n_after}/{n_before} rows with missing "
            "forecast or truth (edge of downloaded window)"
        )

    regions = _region_lookup_table(dsf.latitude.values, dsf.longitude.values)
    merged = merged.merge(regions, on=["latitude", "longitude"], how="left")

    merged["error_precip_mm"] = merged.fcst_precip_mm - merged.obs_precip_mm
    merged["error_temp_c"] = merged.fcst_temp_c - merged.obs_temp_c
    merged["error_mslp_hpa"] = merged.fcst_mslp_hpa - merged.obs_mslp_hpa
    for v in ["precip_mm", "temp_c", "mslp_hpa"]:
        merged[f"abs_error_{v}"] = merged[f"error_{v}"].abs()

    merged["month"] = merged.valid_time.dt.month
    merged["season"] = merged.month.map(_season)

    keep = [
        "init_time", "valid_time", "lead_day", "latitude", "longitude", "region",
        "month", "season",
        "fcst_precip_mm", "obs_precip_mm", "error_precip_mm", "abs_error_precip_mm",
        "fcst_temp_c", "obs_temp_c", "error_temp_c", "abs_error_temp_c",
        "fcst_mslp_hpa", "obs_mslp_hpa", "error_mslp_hpa", "abs_error_mslp_hpa",
    ]
    return merged[keep]


def main() -> None:
    fcst_files = sorted(glob.glob(os.path.join(config.RAW_DIR, "forecast_*.nc")))
    if not fcst_files:
        raise SystemExit(
            f"No forecast_*.nc files in {config.RAW_DIR}/ - run fetch_data.py first."
        )

    frames = []
    for fcst_path in fcst_files:
        tag = os.path.basename(fcst_path)[len("forecast_"):]
        truth_path = os.path.join(config.RAW_DIR, f"truth_{tag}")
        if not os.path.exists(truth_path):
            print(f"skip {fcst_path}: no matching {truth_path}")
            continue
        print(f"processing {fcst_path} + {truth_path}")
        frames.append(load_pair(fcst_path, truth_path))

    if not frames:
        raise SystemExit("No matching forecast/truth pairs found.")

    db = pd.concat(frames, ignore_index=True)
    os.makedirs(config.PROCESSED_DIR, exist_ok=True)
    out_path = os.path.join(config.PROCESSED_DIR, "error_db.parquet")
    db.to_parquet(out_path, index=False)

    print(f"\nsaved {len(db):,} rows -> {out_path}")
    print(f"init_time range: {db.init_time.min()} .. {db.init_time.max()}")
    print(f"lead days: {sorted(db.lead_day.unique())}")
    print(f"regions: {sorted(db.region.unique())}")
    print("\nmean |error| by lead_day (precip mm / temp degC):")
    print(
        db.groupby("lead_day")[["abs_error_precip_mm", "abs_error_temp_c"]]
        .mean()
        .round(2)
    )


if __name__ == "__main__":
    main()
