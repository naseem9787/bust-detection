"""
Phase 3 - C: additional atmospheric variables (wind, humidity, geopotential).

IMPORTANT COST DISCOVERY (documented, not hidden - see
outputs/phase3/ensemble_data_audit.md's sibling note below): in the HRES/
ERA5 coarse (240x121) stores, `geopotential` and `specific_humidity` are
chunked as (1, 8, 13, 240, 121) - ALL 13 pressure levels bundled into every
chunk. Selecting a single level with `.sel(level=...)` happens AFTER the
lazy chunk is loaded, so it does NOT reduce network bytes fetched - a
level-variable costs ~13x what a surface variable costs per unit of date/
lead coverage. `10m_wind_speed` has no level dimension and is exactly as
cheap as Phase 0's original 3 variables.

This was discovered mid-run (the first fetch attempt was killed after ~30
minutes once projected runtime came out to 10+ hours for a naive full-scale
4-year fetch of all 3 variables - a clear violation of the "don't spend
hours on one download" rule). Scope was corrected instead of just letting
it run:

  - `10m_wind_speed`: fetched at FULL JJAS-2018-2021 scale (cheap, same
    cost class as Phase 0's original variables).
  - `specific_humidity` (850hPa) and `geopotential` (500hPa): fetched ONLY
    for the SAME bounded pilot window already used for the ensemble data
    (2021-07-15..2021-08-04, 42 forecast issuances) - genuinely real data,
    just deliberately small in date-range scope, exactly like the ensemble
    pilot and for the identical reason (chunk-bundling cost).

Usage:
    .venv/Scripts/python.exe -m src.phase3.atmospheric_features wind --start 2018-01-01 --end 2018-12-31
    .venv/Scripts/python.exe -m src.phase3.atmospheric_features levels --start 2021-07-15 --end 2021-08-04
"""
from __future__ import annotations

import argparse
import os
import time as _time

import gcsfs
import numpy as np
import pandas as pd
import xarray as xr

from .. import config

CHEAP_VARIABLES = ["10m_wind_speed"]  # no pressure-level dim - full JJAS 2018-2021 scale
LEVEL_VARIABLES = ["specific_humidity", "geopotential"]  # 13x cost - pilot scale only
PRESSURE_LEVEL_HPA = {"specific_humidity": 850, "geopotential": 500}

RAW_DIR = config.RAW_DIR


def _subset_bbox(ds: xr.Dataset) -> xr.Dataset:
    lat_min, lat_max = config.INDIA_LAT
    lon_min, lon_max = config.INDIA_LON
    b = config.BBOX_BUFFER_DEG
    return ds.sel(
        latitude=slice(lat_min - b, lat_max + b),
        longitude=slice(lon_min - b, lon_max + b),
    )


def _open_store(url: str) -> xr.Dataset:
    fs = gcsfs.GCSFileSystem(token="anon")
    store = fs.get_mapper(url)
    return xr.open_zarr(store, consolidated=True)


def _add_time_coords(ds: xr.Dataset) -> xr.Dataset:
    lead_td = xr.DataArray(
        pd.to_timedelta(ds["prediction_timedelta"].values, unit="h"),
        dims="prediction_timedelta",
        coords={"prediction_timedelta": ds["prediction_timedelta"].values},
    )
    valid_time = ds["time"] + lead_td
    ds = ds.assign_coords(valid_time=(("time", "prediction_timedelta"), valid_time.data))
    ds = ds.assign_coords(
        lead_day=("prediction_timedelta", (ds.prediction_timedelta.values // 24).astype(int))
    )
    return ds.rename({"time": "init_time"})


def fetch_cheap_forecast(start: str, end: str) -> xr.Dataset:
    print(f"[wind-forecast] opening {config.FORECAST_STORE}")
    ds = _open_store(config.FORECAST_STORE)
    ds = ds[CHEAP_VARIABLES]
    ds = _subset_bbox(ds)
    ds = ds.sel(time=slice(start, end))
    lead_hours = np.asarray(config.LEAD_HOURS)
    ds = ds.sel(prediction_timedelta=lead_hours)
    print(f"[wind-forecast] subset: {dict(ds.sizes)}")
    t0 = _time.time()
    ds = ds.load()
    print(f"[wind-forecast] downloaded in {_time.time() - t0:.1f}s")
    ds["10m_wind_speed"].attrs["units"] = "m/s"
    return _add_time_coords(ds)


def fetch_level_forecast(start: str, end: str) -> xr.Dataset:
    print(f"[levels-forecast] opening {config.FORECAST_STORE} (PILOT SCOPE - see module docstring)")
    ds = _open_store(config.FORECAST_STORE)
    ds = ds[LEVEL_VARIABLES]
    for var, level in PRESSURE_LEVEL_HPA.items():
        ds[var] = ds[var].sel(level=level)
    ds = ds.drop_vars("level", errors="ignore")
    ds = _subset_bbox(ds)
    ds = ds.sel(time=slice(start, end))
    lead_hours = np.asarray(config.LEAD_HOURS)
    ds = ds.sel(prediction_timedelta=lead_hours)
    print(f"[levels-forecast] subset: {dict(ds.sizes)}")
    t0 = _time.time()
    ds = ds.load()
    print(f"[levels-forecast] downloaded in {_time.time() - t0:.1f}s")
    ds["specific_humidity"] = ds["specific_humidity"] * 1000.0
    ds["specific_humidity"].attrs["units"] = "g/kg"
    ds["geopotential"] = ds["geopotential"] / 9.80665
    ds["geopotential"].attrs["units"] = "m (geopotential height)"
    return _add_time_coords(ds)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["wind", "levels"])
    ap.add_argument("--start", required=True)
    ap.add_argument("--end", required=True)
    args = ap.parse_args()

    os.makedirs(RAW_DIR, exist_ok=True)
    tag = f"{args.start}_{args.end}"

    if args.mode == "wind":
        path = os.path.join(RAW_DIR, f"atmo_wind_{tag}.nc")
        if os.path.exists(path):
            print(f"cached: {path}")
            return
        ds = fetch_cheap_forecast(args.start, args.end)
        ds.to_netcdf(path)
        print(f"[wind-forecast] saved -> {path}")
    else:
        path = os.path.join(RAW_DIR, f"atmo_levels_{tag}.nc")
        if os.path.exists(path):
            print(f"cached: {path}")
            return
        ds = fetch_level_forecast(args.start, args.end)
        ds.to_netcdf(path)
        print(f"[levels-forecast] saved -> {path}")


if __name__ == "__main__":
    main()
