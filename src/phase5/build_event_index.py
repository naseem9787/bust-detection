"""
Phase 5 - builds and persists the full event record index (adds event_id +
severity_score to every row of the analog reference dataset) - backs
GET /events/{event_id}.

Usage:
    .venv/Scripts/python.exe -m src.phase5.build_event_index
"""
from __future__ import annotations

import os

import pandas as pd

from .analogs import INDEX_DIR
from .events import compute_severity

EVENT_INDEX_PATH = os.path.join(INDEX_DIR, "event_index.parquet")


def main() -> None:
    # read from the analog index's own persisted reference table (single
    # source of truth - the index is always built, this never re-derives
    # its own separate copy of the reference dataset)
    ref_path = os.path.join(INDEX_DIR, "reference.parquet")
    if not os.path.exists(ref_path):
        raise SystemExit(f"{ref_path} not found - run build_analog_index.py first.")
    df = pd.read_parquet(ref_path)
    df = compute_severity(df)

    dupes = df.event_id.duplicated().sum()
    if dupes:
        raise SystemExit(f"{dupes} duplicate event_id values - hashing collision or duplicate rows, investigate")

    os.makedirs(INDEX_DIR, exist_ok=True)
    df.to_parquet(EVENT_INDEX_PATH, index=False)
    print(f"saved {len(df):,} event records -> {EVENT_INDEX_PATH}")

    top = df.sort_values("severity_score", ascending=False).head(5)
    print("\ntop 5 most severe events:")
    print(
        top[["event_id", "init_time", "region_v2", "lead_day", "fcst_precip_mm",
             "obs_precip_mm", "severity_score"]].to_string(index=False)
    )


if __name__ == "__main__":
    main()
