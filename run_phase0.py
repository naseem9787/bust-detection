"""
Phase 0 orchestrator: fetch data -> build error database -> label busts.

    .venv/Scripts/python.exe run_phase0.py --start 2018-06-01 --end 2018-09-30

Skips the download step if the cached NetCDFs for that date range already
exist in data/raw/ (delete them, or pass --force, to refetch).
"""
from __future__ import annotations

import argparse
import os

from src import build_error_db, config, fetch_data, label_busts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--start", default=config.DEFAULT_START)
    ap.add_argument("--end", default=config.DEFAULT_END)
    ap.add_argument("--force", action="store_true", help="refetch even if cached files exist")
    args = ap.parse_args()

    tag = f"{args.start}_{args.end}"
    fcst_path = os.path.join(config.RAW_DIR, f"forecast_{tag}.nc")
    truth_path = os.path.join(config.RAW_DIR, f"truth_{tag}.nc")

    if args.force or not (os.path.exists(fcst_path) and os.path.exists(truth_path)):
        os.makedirs(config.RAW_DIR, exist_ok=True)
        print(f"=== Step 1/3: fetching {args.start} .. {args.end} ===")
        forecast = fetch_data.fetch_forecast(args.start, args.end)
        fetch_data._sanity_check("forecast", forecast)
        forecast.to_netcdf(fcst_path)
        print(f"[forecast] saved -> {fcst_path}")

        truth = fetch_data.fetch_truth(args.start, args.end)
        fetch_data._sanity_check("truth", truth)
        truth.to_netcdf(truth_path)
        print(f"[truth] saved -> {truth_path}")
    else:
        print(f"=== Step 1/3: using cached {fcst_path} / {truth_path} ===")

    print("\n=== Step 2/3: building error database ===")
    build_error_db.main()

    print("\n=== Step 3/3: labeling busts ===")
    label_busts.main()

    print("\nDone. See data/processed/error_db.parquet and data/processed/bust_labels.parquet")


if __name__ == "__main__":
    main()
