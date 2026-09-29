"""
Phase 5 - builds and persists the analog index.

Usage:
    .venv/Scripts/python.exe -m src.phase5.build_analog_index
"""
from __future__ import annotations

import os
import time

from .analogs import INDEX_DIR, AnalogIndex
from .dataset import OUT_DIR, build_reference_dataset


def main() -> None:
    t0 = time.time()
    ref_path = os.path.join(OUT_DIR, "analog_reference_dataset.parquet")
    if os.path.exists(ref_path):
        import pandas as pd

        df = pd.read_parquet(ref_path)
    else:
        df = build_reference_dataset()
        df.to_parquet(ref_path, index=False)
        print(f"saved -> {ref_path}")
    print(f"reference dataset: {len(df):,} rows ({time.time() - t0:.1f}s)")

    t0 = time.time()
    index = AnalogIndex.build(df)
    build_time = time.time() - t0
    print(f"index built in {build_time:.2f}s")

    index.save(INDEX_DIR)
    print(f"saved -> {INDEX_DIR}")

    with open(os.path.join(INDEX_DIR, "build_stats.txt"), "w") as f:
        f.write(f"n_rows={len(df)}\nbuild_time_seconds={build_time:.3f}\n")


if __name__ == "__main__":
    main()
