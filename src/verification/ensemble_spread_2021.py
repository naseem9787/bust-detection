"""
Full-season IFS ensemble rain spread for the 2021 hold-out (JJAS, 00Z + 12Z).

Purpose: score raw ensemble spread - the standard "how uncertain is this
forecast" baseline - against our model on exactly the same 2021 test rows.
Spread is rank-based evidence, so it needs no fitting and uses no training
data.

The Phase 3 pilot (src/phase3/ensemble_features.py) covered only 3 weeks
because every chunk carries all 50 members (~46.5 MB). Rain only, one week
at a time, cached to data/raw/ens2021/ so an interrupted run resumes.
Only the reduced statistics (mean, std, max) are saved.

Usage:
    .venv/Scripts/python.exe -m src.verification.ensemble_spread_2021
"""
from __future__ import annotations

import os
import time as _time

import gcsfs
import numpy as np
import pandas as pd
import xarray as xr

from .. import config
from ..phase3.ensemble_features import ENSEMBLE_STORE, _subset_bbox

VAR = "total_precipitation_24hr"
OUT_DIR = os.path.join(config.RAW_DIR, "ens2021")
SEASON_START, SEASON_END = "2021-06-01", "2021-09-30T12:00"


def fetch_week(ds: xr.Dataset, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    sub = ds.sel(time=slice(start, end))
    if sub.sizes["time"] == 0:
        return pd.DataFrame()
    da = sub[VAR]
    stats = xr.Dataset({
        "ens_mean_precip": da.mean("number") * 1000.0,
        "ens_std_precip": da.std("number") * 1000.0,
        "ens_max_precip": da.max("number") * 1000.0,
    }).load()
    df = stats.to_dataframe().reset_index().rename(columns={"time": "init_time"})
    td = df.pop("prediction_timedelta")
    hours = td / pd.Timedelta(hours=1) if pd.api.types.is_timedelta64_dtype(td) else td
    df["lead_day"] = (hours // 24).astype(int)
    return df


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    fs = gcsfs.GCSFileSystem(token="anon")
    ds = xr.open_zarr(fs.get_mapper(ENSEMBLE_STORE), consolidated=True)[[VAR]]
    ds = _subset_bbox(ds).sel(prediction_timedelta=np.asarray(config.LEAD_HOURS))

    weeks = pd.date_range(SEASON_START, SEASON_END, freq="7D")
    t_all = _time.time()
    for i, ws in enumerate(weeks):
        we = min(ws + pd.Timedelta(days=7) - pd.Timedelta(hours=1), pd.Timestamp(SEASON_END))
        path = os.path.join(OUT_DIR, f"week_{ws:%Y%m%d}.parquet")
        if os.path.exists(path):
            print(f"[{i + 1}/{len(weeks)}] {ws:%Y-%m-%d} cached", flush=True)
            continue
        t0 = _time.time()
        for attempt in range(3):
            try:
                df = fetch_week(ds, ws, we)
                break
            except Exception as e:  # network blips on a public bucket
                print(f"   retry {attempt + 1}: {e!r}", flush=True)
                _time.sleep(30)
        else:
            raise SystemExit(f"week {ws:%Y-%m-%d} failed 3 times")
        df.to_parquet(path, index=False)
        print(f"[{i + 1}/{len(weeks)}] {ws:%Y-%m-%d} rows={len(df):,} in {_time.time() - t0:.0f}s "
              f"(total {(_time.time() - t_all) / 60:.1f} min)", flush=True)

    full = pd.concat([pd.read_parquet(os.path.join(OUT_DIR, f)) for f in sorted(os.listdir(OUT_DIR))
                      if f.startswith("week_")], ignore_index=True)
    full.to_parquet(os.path.join(OUT_DIR, "ens_spread_2021_jjas.parquet"), index=False)
    print(f"DONE rows={len(full):,} inits={full.init_time.nunique()}", flush=True)


if __name__ == "__main__":
    main()
