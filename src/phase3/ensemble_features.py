"""
Phase 3 - B: ensemble uncertainty features, from a deliberately bounded
pilot window (see outputs/phase3/ensemble_data_audit.md for why the window
is small - the ensemble store is ~50x the data volume of the deterministic
stores per unit of time/variable coverage).

Feature set (meteorologically interpretable, not "every possible statistic"):
  ensemble_mean, ensemble_std, ensemble_min, ensemble_max, ensemble_iqr
  (p75-p25), ensemble_cv (std/mean, precip only - MSLP/temp means aren't
  naturally zero-referenced so a coefficient of variation isn't meaningful
  for them), domain_mean_ensemble_std (spatially aggregated spread - same
  domain-mean-anomaly trick Phase 2 used for the deterministic forecast).

All statistics are computed by reducing over the ensemble `number` dimension
ONLY - never over time, lead, or space in a way that would look at a
different (init_time, lead_day, grid cell) than the row it's attached to.
The reduction happens immediately on load; raw per-member values are never
persisted (see the audit doc's data-volume rationale).

Usage:
    .venv/Scripts/python.exe -m src.phase3.ensemble_features
"""
from __future__ import annotations

import os
import time as _time

import gcsfs
import numpy as np
import pandas as pd
import xarray as xr

from .. import config

ENSEMBLE_STORE = (
    "gs://weatherbench2/datasets/ifs_ens/"
    "2018-2022-240x121_equiangular_with_poles_conservative.zarr"
)
ENSEMBLE_VARIABLES = ["total_precipitation_24hr", "2m_temperature"]

# Bounded pilot window - see outputs/phase3/ensemble_data_audit.md
PILOT_START = "2021-07-15"
PILOT_END = "2021-08-04"

RAW_DIR = config.RAW_DIR
PILOT_TAG = f"{PILOT_START}_{PILOT_END}"
PILOT_NC_PATH = os.path.join(RAW_DIR, f"ensemble_pilot_{PILOT_TAG}.nc")


def _subset_bbox(ds: xr.Dataset) -> xr.Dataset:
    lat_min, lat_max = config.INDIA_LAT
    lon_min, lon_max = config.INDIA_LON
    b = config.BBOX_BUFFER_DEG
    return ds.sel(
        latitude=slice(lat_min - b, lat_max + b),
        longitude=slice(lon_min - b, lon_max + b),
    )


def fetch_ensemble_pilot(start: str = PILOT_START, end: str = PILOT_END) -> xr.Dataset:
    print(f"[ensemble] opening {ENSEMBLE_STORE}")
    fs = gcsfs.GCSFileSystem(token="anon")
    store = fs.get_mapper(ENSEMBLE_STORE)
    ds = xr.open_zarr(store, consolidated=True)
    ds = ds[ENSEMBLE_VARIABLES]
    ds = _subset_bbox(ds)
    ds = ds.sel(time=slice(start, end))
    lead_hours = np.asarray(config.LEAD_HOURS)
    ds = ds.sel(prediction_timedelta=lead_hours)

    print(
        f"[ensemble] subset: {dict(ds.sizes)} "
        f"({ds.time.values[0]} .. {ds.time.values[-1]})"
    )

    # reduce over the ensemble ('number') dimension immediately - this is
    # what actually triggers the network fetch of all 50 members per chunk,
    # but only the REDUCED statistics are ever materialized/saved.
    stats = xr.Dataset()
    for var in ENSEMBLE_VARIABLES:
        da = ds[var]
        stats[f"{var}__mean"] = da.mean("number")
        stats[f"{var}__std"] = da.std("number")
        stats[f"{var}__min"] = da.min("number")
        stats[f"{var}__max"] = da.max("number")
        stats[f"{var}__p25"] = da.quantile(0.25, dim="number").drop_vars("quantile", errors="ignore")
        stats[f"{var}__p75"] = da.quantile(0.75, dim="number").drop_vars("quantile", errors="ignore")

    t0 = _time.time()
    stats = stats.load()
    print(f"[ensemble] downloaded + reduced in {_time.time() - t0:.1f}s")

    # unit conversions, matching Phase 0's fetch_data.py convention exactly
    for suffix in ["mean", "std", "min", "max", "p25", "p75"]:
        col = f"total_precipitation_24hr__{suffix}"
        if suffix == "std":
            stats[col] = stats[col] * 1000.0  # std scales linearly, no offset
        else:
            stats[col] = stats[col] * 1000.0
        stats[col].attrs["units"] = "mm"
        tcol = f"2m_temperature__{suffix}"
        if suffix == "std":
            stats[tcol] = stats[tcol]  # std of a Kelvin->Celsius shift is unchanged
        else:
            stats[tcol] = stats[tcol] - 273.15
        stats[tcol].attrs["units"] = "degC"

    valid_time = ds["time"] + xr.DataArray(
        pd.to_timedelta(ds["prediction_timedelta"].values, unit="h"),
        dims="prediction_timedelta",
        coords={"prediction_timedelta": ds["prediction_timedelta"].values},
    )
    stats = stats.assign_coords(valid_time=(("time", "prediction_timedelta"), valid_time.data))
    stats = stats.assign_coords(
        lead_day=("prediction_timedelta", (ds.prediction_timedelta.values // 24).astype(int))
    )
    stats = stats.rename({"time": "init_time"})
    return stats


def to_dataframe(stats: xr.Dataset) -> pd.DataFrame:
    df = stats.to_dataframe().reset_index()

    for var, short in [("total_precipitation_24hr", "precip"), ("2m_temperature", "temp")]:
        mean = df[f"{var}__mean"]
        std = df[f"{var}__std"]
        df[f"ensemble_mean_{short}"] = mean
        df[f"ensemble_std_{short}"] = std
        df[f"ensemble_min_{short}"] = df[f"{var}__min"]
        df[f"ensemble_max_{short}"] = df[f"{var}__max"]
        df[f"ensemble_iqr_{short}"] = df[f"{var}__p75"] - df[f"{var}__p25"]
        if short == "precip":
            # coefficient of variation only makes sense for a ratio-scale
            # quantity with a meaningful zero (precip) - not temperature in
            # degC, which has an arbitrary zero point.
            df["ensemble_cv_precip"] = std / mean.replace(0, np.nan)
            df["ensemble_cv_precip"] = df["ensemble_cv_precip"].fillna(0.0)

    keep_cols = [
        "init_time", "valid_time", "lead_day", "latitude", "longitude",
        "ensemble_mean_precip", "ensemble_std_precip", "ensemble_min_precip",
        "ensemble_max_precip", "ensemble_iqr_precip", "ensemble_cv_precip",
        "ensemble_mean_temp", "ensemble_std_temp", "ensemble_min_temp",
        "ensemble_max_temp", "ensemble_iqr_temp",
    ]
    out = df[keep_cols].copy()

    # spatially aggregated spread - domain-mean ensemble std at this
    # (init_time, lead_day), same trick as Phase 2's domain-mean anomaly
    grp = out.groupby(["init_time", "lead_day"])
    out["domain_mean_ensemble_std_precip"] = grp.ensemble_std_precip.transform("mean")
    out["domain_mean_ensemble_std_temp"] = grp.ensemble_std_temp.transform("mean")
    return out


def build_or_load_pilot() -> pd.DataFrame:
    csv_path = os.path.join(RAW_DIR, f"ensemble_pilot_{PILOT_TAG}.parquet")
    if os.path.exists(csv_path):
        print(f"[ensemble] using cached {csv_path}")
        return pd.read_parquet(csv_path)
    stats = fetch_ensemble_pilot()
    df = to_dataframe(stats)
    df.to_parquet(csv_path, index=False)
    print(f"[ensemble] saved -> {csv_path}")
    return df


def main() -> None:
    os.makedirs(RAW_DIR, exist_ok=True)
    df = build_or_load_pilot()
    print(f"\npilot rows: {len(df):,}")
    print(f"init_time range: {df.init_time.min()} .. {df.init_time.max()}")
    print(f"lead days: {sorted(df.lead_day.unique())}")
    print(df[[c for c in df.columns if c.startswith("ensemble_")]].describe().T)


if __name__ == "__main__":
    main()
