"""
Phase 0 - Step 1: pull an India-subset of forecast (HRES) and truth (ERA5)
from the public WeatherBench2 GCS bucket and cache them locally.

Both stores are the same 1.5-degree grid (240 lon x 121 lat), so no
regridding is needed - only a spatial/temporal crop before downloading.

Usage:
    .venv/Scripts/python.exe -m src.fetch_data --start 2018-06-01 --end 2018-09-30

Output:
    data/raw/forecast_<start>_<end>.nc   (dims: init_time, lead_day, latitude, longitude)
    data/raw/truth_<start>_<end>.nc      (dims: time, latitude, longitude)
"""
from __future__ import annotations

import argparse
import os
import time as _time

import gcsfs
import numpy as np
import pandas as pd
import xarray as xr

from . import config


def _subset_bbox(ds: xr.Dataset) -> xr.Dataset:
    """Crop to the India bounding box (+ buffer). Assumes ascending lat/lon,
    which both WB2 stores use."""
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


def fetch_forecast(start: str, end: str) -> xr.Dataset:
    print(f"[forecast] opening {config.FORECAST_STORE}")
    ds = _open_store(config.FORECAST_STORE)
    ds = ds[config.VARIABLES]
    ds = _subset_bbox(ds)
    ds = ds.sel(time=slice(start, end))

    # prediction_timedelta is stored as plain int64 hours (not timedelta64) -
    # keep only the Day 1..Day 10 lead steps we care about.
    lead_hours = np.asarray(config.LEAD_HOURS)
    ds = ds.sel(prediction_timedelta=lead_hours)

    print(
        f"[forecast] subset: {dict(ds.sizes)} "
        f"({ds.time.values[0]} .. {ds.time.values[-1]})"
    )
    t0 = _time.time()
    ds = ds.load()  # triggers the actual (now small) download
    print(f"[forecast] downloaded in {_time.time() - t0:.1f}s")

    # unit conversions for readability: m -> mm, K -> degC, Pa -> hPa
    ds["total_precipitation_24hr"] = ds["total_precipitation_24hr"] * 1000.0
    ds["total_precipitation_24hr"].attrs["units"] = "mm"
    ds["2m_temperature"] = ds["2m_temperature"] - 273.15
    ds["2m_temperature"].attrs["units"] = "degC"
    ds["mean_sea_level_pressure"] = ds["mean_sea_level_pressure"] / 100.0
    ds["mean_sea_level_pressure"].attrs["units"] = "hPa"

    # valid_time = init time + lead hours; lead_day = lead hours / 24.
    # `lead_td` must carry its own 'prediction_timedelta' dim explicitly -
    # otherwise a same-length `time` axis (a coincidence for short test
    # windows) makes xarray broadcast positionally instead of outer-product,
    # silently producing a 1D result instead of the intended (time, lead) grid.
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
    ds = ds.rename({"time": "init_time"})
    return ds


def fetch_truth(start: str, end: str) -> xr.Dataset:
    # truth must cover every valid_time a forecast in [start, end] can point to,
    # i.e. up to config.LEAD_HOURS[-1] hours past `end`.
    truth_end = (pd.Timestamp(end) + pd.Timedelta(hours=config.LEAD_HOURS[-1])).strftime(
        "%Y-%m-%d"
    )
    print(f"[truth] opening {config.TRUTH_STORE}")
    ds = _open_store(config.TRUTH_STORE)
    ds = ds[config.VARIABLES]
    ds = _subset_bbox(ds)
    ds = ds.sel(time=slice(start, truth_end))

    print(f"[truth] subset: {dict(ds.sizes)} ({ds.time.values[0]} .. {ds.time.values[-1]})")
    t0 = _time.time()
    ds = ds.load()
    print(f"[truth] downloaded in {_time.time() - t0:.1f}s")

    ds["total_precipitation_24hr"] = ds["total_precipitation_24hr"] * 1000.0
    ds["total_precipitation_24hr"].attrs["units"] = "mm"
    ds["2m_temperature"] = ds["2m_temperature"] - 273.15
    ds["2m_temperature"].attrs["units"] = "degC"
    ds["mean_sea_level_pressure"] = ds["mean_sea_level_pressure"] / 100.0
    ds["mean_sea_level_pressure"].attrs["units"] = "hPa"
    return ds


def _sanity_check(name: str, ds: xr.Dataset) -> None:
    p = ds["total_precipitation_24hr"]
    t = ds["2m_temperature"]
    print(
        f"[{name}] sanity: precip mm [{float(p.min()):.1f}, {float(p.max()):.1f}] "
        f"mean {float(p.mean()):.2f} | temp degC [{float(t.min()):.1f}, {float(t.max()):.1f}]"
    )
    if float(p.max()) > 2000 or float(t.max()) > 60 or float(t.min()) < -60:
        print(f"[{name}] WARNING: values look out of physical range - check unit conversion.")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=config.DEFAULT_START)
    ap.add_argument("--end", default=config.DEFAULT_END)
    ap.add_argument("--out-dir", default=config.RAW_DIR)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    tag = f"{args.start}_{args.end}"

    forecast = fetch_forecast(args.start, args.end)
    _sanity_check("forecast", forecast)
    fcst_path = os.path.join(args.out_dir, f"forecast_{tag}.nc")
    forecast.to_netcdf(fcst_path)
    print(f"[forecast] saved -> {fcst_path}")

    truth = fetch_truth(args.start, args.end)
    _sanity_check("truth", truth)
    truth_path = os.path.join(args.out_dir, f"truth_{tag}.nc")
    truth.to_netcdf(truth_path)
    print(f"[truth] saved -> {truth_path}")


if __name__ == "__main__":
    main()
