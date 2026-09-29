"""
Phase 4 - operational batch inference CLI. Runs the complete pipeline in
one command: load forecast input -> build features -> validate -> rain
model -> calibrate -> temperature model -> calibrate -> grid output ->
region aggregates -> metadata -> Parquet/NetCDF/GeoJSON.

This is OFFLINE/HISTORICAL batch inference over an already-fetched forecast
window (data/raw/forecast_*.nc, from src/fetch_data.py) - there is no live
NWP ingestion in this repository (see docs/production_inference.md's Data
Availability section). Point --init-time-start/--init-time-end at a window
already covered by the cached forecast NetCDFs.

Usage:
    .venv/Scripts/python.exe -m src.production.batch_predict \
        --init-time-start 2021-07-15 --init-time-end 2021-07-16 \
        --output outputs/production/batch/run_2021-07-15
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

import pandas as pd

from ..phase1.dataset import ERROR_DB_PATH
from . import registry
from .aggregation import aggregate_region
from .inference import ProductionInferenceEngine
from .writers import write_geojson, write_netcdf, write_parquet


def load_forecast_window(init_time_start: str, init_time_end: str) -> pd.DataFrame:
    """Historical mode: reads already-fetched forecast rows from
    data/processed/error_db.parquet (built by src/build_error_db.py) rather
    than hitting a live NWP feed - see module docstring."""
    if not os.path.exists(ERROR_DB_PATH):
        raise SystemExit(
            f"{ERROR_DB_PATH} not found - this batch CLI runs in OFFLINE/"
            "HISTORICAL mode over already-fetched forecast data (see "
            "fetch_multi_year.sh). No live NWP ingestion is implemented."
        )
    df = pd.read_parquet(ERROR_DB_PATH)
    mask = (df.init_time >= pd.Timestamp(init_time_start)) & (
        df.init_time <= pd.Timestamp(init_time_end) + pd.Timedelta(hours=23)
    )
    window = df.loc[mask]
    if window.empty:
        raise SystemExit(
            f"No cached forecast rows in [{init_time_start}, {init_time_end}] - "
            "widen the window or fetch that range first."
        )
    return window


def run_batch(init_time_start: str, init_time_end: str, output_dir: str) -> None:
    os.makedirs(output_dir, exist_ok=True)
    window = load_forecast_window(init_time_start, init_time_end)
    print(f"loaded {len(window):,} cached forecast rows")

    engine = ProductionInferenceEngine()
    rows = []
    n_skipped_outside_domain = 0
    for _, r in window.iterrows():
        try:
            result = engine.predict(
                init_time=r.init_time,
                lead_day=int(r.lead_day),
                latitude=float(r.latitude),
                longitude=float(r.longitude),
                forecast_precip_mm=float(r.fcst_precip_mm),
                forecast_temp_c=float(r.fcst_temp_c),
                forecast_mslp_hpa=float(r.fcst_mslp_hpa),
            )
        except Exception:
            n_skipped_outside_domain += 1
            continue
        rows.append(
            {
                "init_time": result["init_time"], "lead_day": result["lead_day"],
                "valid_time": result["valid_time"], "latitude": result["latitude"],
                "longitude": result["longitude"], "region": result["region"],
                "forecast_precip_mm": result["forecast_precip_mm"],
                "forecast_temp_c": result["forecast_temp_c"],
                "rain_bust_probability_raw": result["rain_bust_probability"]["raw"],
                "rain_bust_probability_calibrated": result["rain_bust_probability"]["calibrated"],
                "rain_confidence": result["rain_bust_probability"]["confidence"],
                "model_version": result["model_version"],
                "feature_version": result["feature_version"],
                "calibration_version": result["calibration_version"],
            }
        )
    print(f"predicted {len(rows):,} grid cells ({n_skipped_outside_domain:,} outside India domain, skipped)")

    grid_df = pd.DataFrame(rows)
    if grid_df.empty:
        raise SystemExit("no in-domain rows to write - nothing generated")

    parquet_path = write_parquet(grid_df, os.path.join(output_dir, "grid_predictions.parquet"))
    print(f"wrote -> {parquet_path}")

    # one NetCDF per forecast issuance (init_time), lead_day as an internal
    # dimension - the natural grouping for a meteorological grid file, and
    # the one that guarantees a unique (lead_day, lat, lon) index per file
    for init_time, g in grid_df.groupby("init_time"):
        tag = pd.Timestamp(init_time).strftime("%Y%m%dT%H%M")
        nc_path = write_netcdf(g, os.path.join(output_dir, f"grid_predictions_{tag}.nc"))
        print(f"wrote -> {nc_path}")

    geojson_path = write_geojson(grid_df, os.path.join(output_dir, "grid_predictions.geojson"))
    print(f"wrote -> {geojson_path}")

    region_agg = aggregate_region(
        grid_df, "rain_bust_probability_calibrated", "rain_confidence", "forecast_precip_mm"
    )
    region_path = os.path.join(output_dir, "region_predictions.parquet")
    region_agg.to_parquet(region_path, index=False)
    print(f"wrote -> {region_path}")

    run_metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "init_time_window": [init_time_start, init_time_end],
        "n_grid_predictions": len(grid_df),
        "n_skipped_outside_domain": n_skipped_outside_domain,
        "models_used": {k: registry.load_entry(k).raw["model_version"] for k in registry.PRODUCTION_MODELS},
        "mode": "OFFLINE/HISTORICAL - no live NWP ingestion",
    }
    meta_path = os.path.join(output_dir, "run_metadata.json")
    with open(meta_path, "w") as f:
        json.dump(run_metadata, f, indent=2, default=str)
    print(f"wrote -> {meta_path}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--init-time-start", required=True)
    ap.add_argument("--init-time-end", required=True)
    ap.add_argument("--output", required=True)
    args = ap.parse_args()
    run_batch(args.init_time_start, args.init_time_end, args.output)


if __name__ == "__main__":
    main()
