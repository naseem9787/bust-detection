"""
Phase 3 - D: merges the new atmospheric variables onto the base feature
table for Ablation Model 6. Two cost tiers (see atmospheric_features.py):
  - wind_speed_10m: full JJAS 2018-2021 scale
  - humidity_850hpa / geopotential_500hpa: pilot window only (2021-07-15..2021-08-04)

Forecast-time values only - no truth/observation columns are merged in.

Usage:
    .venv/Scripts/python.exe -m src.phase3.atmo_merge
"""
from __future__ import annotations

import os

import pandas as pd
import xarray as xr

from .. import config

WIND_COL = {"10m_wind_speed": "wind_speed_10m"}
LEVEL_COLS = {"specific_humidity": "humidity_850hpa", "geopotential": "geopotential_500hpa"}

PILOT_START = "2021-07-15"
PILOT_END = "2021-08-04"


def load_wind_dataframe(years: list[int]) -> pd.DataFrame:
    frames = []
    for year in years:
        path = os.path.join(config.RAW_DIR, f"atmo_wind_{year}-01-01_{year}-12-31.nc")
        if not os.path.exists(path):
            raise SystemExit(f"{path} not found - run fetch_atmo_multi_year.sh first.")
        ds = xr.open_dataset(path)
        df = ds.to_dataframe().reset_index().rename(columns=WIND_COL)
        frames.append(df[["init_time", "lead_day", "latitude", "longitude"] + list(WIND_COL.values())])
    return pd.concat(frames, ignore_index=True)


def load_levels_dataframe() -> pd.DataFrame:
    path = os.path.join(config.RAW_DIR, f"atmo_levels_{PILOT_START}_{PILOT_END}.nc")
    if not os.path.exists(path):
        raise SystemExit(f"{path} not found - run fetch_atmo_multi_year.sh first.")
    ds = xr.open_dataset(path)
    df = ds.to_dataframe().reset_index().rename(columns=LEVEL_COLS)
    return df[["init_time", "lead_day", "latitude", "longitude"] + list(LEVEL_COLS.values())]


def merge_wind_features(base_df: pd.DataFrame, years: list[int]) -> pd.DataFrame:
    wind = load_wind_dataframe(years)
    merged = base_df.merge(wind, on=["init_time", "lead_day", "latitude", "longitude"], how="left")
    n_missing = merged[list(WIND_COL.values())].isna().any(axis=1).sum()
    if n_missing:
        print(f"[atmo_merge] {n_missing:,}/{len(merged):,} rows have no wind match")
    return merged


def merge_level_features(base_df: pd.DataFrame) -> pd.DataFrame:
    levels = load_levels_dataframe()
    merged = base_df.merge(levels, on=["init_time", "lead_day", "latitude", "longitude"], how="left")
    return merged


WIND_FEATURE_COLS = list(WIND_COL.values())
LEVEL_FEATURE_COLS = list(LEVEL_COLS.values())
