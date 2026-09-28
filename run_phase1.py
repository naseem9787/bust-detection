"""
Phase 1 orchestrator: dataset summary -> error atlas -> plots -> baselines ->
chronological evaluation -> experiment manifest.

Reuses Phase 0's already-downloaded data/processed/error_db.parquet (built
from the full-calendar-year 2018-2021 raw NetCDFs) - no re-fetching from GCS.
If that file is missing, run Phase 0 first:

    ./fetch_multi_year.sh 2018 2021

Usage:
    .venv/Scripts/python.exe run_phase1.py
"""
from __future__ import annotations

from src.phase1 import dataset_summary, error_atlas, evaluate, manifest, plots


def main() -> None:
    print("=== Step 1/5: dataset summary (JJAS 2018-2021) ===")
    dataset_summary.main()

    print("\n=== Step 2/5: forecast error atlas ===")
    error_atlas.main()

    print("\n=== Step 3/5: plots ===")
    plots.main()

    print("\n=== Step 4/5: baselines + chronological evaluation (train 2018-2020, test 2021) ===")
    evaluate.main()

    print("\n=== Step 5/5: experiment manifest ===")
    manifest.main()

    print("\nDone. See outputs/phase1/ for all deliverables.")


if __name__ == "__main__":
    main()
