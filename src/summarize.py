"""
Phase 0 - Step 4 (optional): collapse bust_labels.parquet (which can get large
once the date range is widened) into a small, git-friendly summary table -
bust rate and mean |error| by region x lead_day x season - safe to commit
even when the full row-level parquet is too big for a plain git push.

Usage:
    .venv/Scripts/python.exe -m src.summarize
"""
from __future__ import annotations

import os

import pandas as pd

from . import config


def main() -> None:
    in_path = os.path.join(config.PROCESSED_DIR, "bust_labels.parquet")
    if not os.path.exists(in_path):
        raise SystemExit(f"{in_path} not found - run label_busts.py first.")
    df = pd.read_parquet(
        in_path,
        columns=[
            "region", "lead_day", "season",
            "abs_error_precip_mm", "abs_error_temp_c",
            "bust_precip", "bust_temp", "bust_any",
            "missed_heavy_rain_event", "false_alarm_heavy_rain",
        ],
    )

    summary = (
        df.groupby(["region", "lead_day", "season"])
        .agg(
            n_samples=("bust_any", "size"),
            bust_rate=("bust_any", "mean"),
            precip_bust_rate=("bust_precip", "mean"),
            temp_bust_rate=("bust_temp", "mean"),
            mean_abs_error_precip_mm=("abs_error_precip_mm", "mean"),
            mean_abs_error_temp_c=("abs_error_temp_c", "mean"),
            missed_heavy_rain_events=("missed_heavy_rain_event", "sum"),
            false_alarm_heavy_rain=("false_alarm_heavy_rain", "sum"),
        )
        .reset_index()
        .sort_values(["region", "lead_day", "season"])
    )
    for col in ["bust_rate", "precip_bust_rate", "temp_bust_rate"]:
        summary[col] = (summary[col] * 100).round(1)
    summary["mean_abs_error_precip_mm"] = summary.mean_abs_error_precip_mm.round(2)
    summary["mean_abs_error_temp_c"] = summary.mean_abs_error_temp_c.round(2)

    out_path = os.path.join(config.PROCESSED_DIR, "summary_by_region_lead_season.csv")
    summary.to_csv(out_path, index=False)
    print(f"saved {len(summary):,} summary rows -> {out_path}")
    print(f"(full row-level data stays in {in_path}, gitignored - see README)")


if __name__ == "__main__":
    main()
