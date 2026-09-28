"""
Phase 1 - dataset summary: records exactly what went into the JJAS 2018-2021
experiment (sample counts, coverage, missing values, bust/miss/false-alarm
counts) as both machine-readable JSON and a human-readable Markdown table.

Usage:
    .venv/Scripts/python.exe -m src.phase1.dataset_summary
"""
from __future__ import annotations

import json
import os
import platform
import sys

import numpy as np
import pandas as pd

from .. import config
from .dataset import JJAS_WINDOWS, TEST_YEAR, TRAIN_YEARS, build_phase1_dataset

OUT_DIR = os.path.join("outputs", "phase1")

NUMERIC_COLS = [
    "fcst_precip_mm", "obs_precip_mm", "error_precip_mm", "abs_error_precip_mm",
    "fcst_temp_c", "obs_temp_c", "error_temp_c", "abs_error_temp_c",
    "fcst_mslp_hpa", "obs_mslp_hpa", "error_mslp_hpa", "abs_error_mslp_hpa",
]


def _split_stats(d: pd.DataFrame) -> dict:
    return {
        "n_rows": int(len(d)),
        "n_forecast_issuances": int(d.init_time.nunique()),
        "date_range_init_time": [str(d.init_time.min()), str(d.init_time.max())],
        "bust_rate": float(d.bust_any.mean()),
        "precip_bust_rate": float(d.bust_precip.mean()),
        "temp_bust_rate": float(d.bust_temp.mean()),
        "missed_heavy_rain_events": int(d.missed_heavy_rain_event.sum()),
        "false_alarm_heavy_rain": int(d.false_alarm_heavy_rain.sum()),
    }


def build_summary() -> dict:
    ds = build_phase1_dataset()
    df = ds.df
    train = df[df.split == "train"]
    test = df[df.split == "test"]

    missing = {c: int(df[c].isna().sum()) for c in NUMERIC_COLS}
    total_missing = sum(missing.values())

    summary = {
        "experiment_window": "JJAS 2018-2021 (init_time-based, inclusive)",
        "jjas_windows": JJAS_WINDOWS,
        "train_years": TRAIN_YEARS,
        "test_year": TEST_YEAR,
        "n_rows_total": int(len(df)),
        "n_forecast_issuances_total": int(df.init_time.nunique()),
        "n_grid_points": int(df.groupby(["latitude", "longitude"]).ngroups),
        "n_regions_named": int(df.loc[df.region != "Unclassified", "region"].nunique()),
        "regions": sorted(df.region.unique().tolist()),
        "unclassified_row_fraction": float((df.region == "Unclassified").mean()),
        "variables": list(config.VARIABLES),
        "lead_days": sorted(df.lead_day.unique().tolist()),
        "date_range_init_time": [str(df.init_time.min()), str(df.init_time.max())],
        "date_range_valid_time": [str(df.valid_time.min()), str(df.valid_time.max())],
        "missing_values_by_column": missing,
        "missing_values_total": total_missing,
        "bust_definition": {
            "categorical_rule": (
                "IMD rainfall-category miss (>=2 category steps apart) or a "
                "heavy-or-above event missed/falsely predicted - fixed bins, "
                "no fitting, config.IMD_RAIN_BINS/HEAVY_OR_ABOVE_INDEX"
            ),
            "percentile_rule": (
                f"|error| > {config.BUST_PERCENTILE:.0%} percentile for that "
                "(region, lead_day), fit on the TRAIN split (2018-2020) ONLY "
                "to avoid leaking 2021 statistics into the test-year labels "
                "- see src/phase1/dataset.py module docstring"
            ),
            "temp_hard_threshold_degC": config.TEMP_BUST_ABS_ERROR_K,
        },
        "train": _split_stats(train),
        "test": _split_stats(test),
        "overall": _split_stats(df),
        "software_versions": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
        },
    }
    return summary


def to_markdown(summary: dict) -> str:
    lines = [
        "# Phase 1 Dataset Summary - JJAS 2018-2021",
        "",
        f"Experiment window: **{summary['experiment_window']}**",
        "",
        "| Year | JJAS window (init_time) |",
        "|---|---|",
    ]
    for year, (start, end) in summary["jjas_windows"].items():
        lines.append(f"| {year} | {start} .. {end} |")
    lines += [
        "",
        f"- Train years: {summary['train_years']}",
        f"- Test year (unseen holdout): {summary['test_year']}",
        f"- Total rows (grid-cell x lead-day x forecast-issuance): "
        f"{summary['n_rows_total']:,}",
        f"- Distinct forecast issuances (init_time): "
        f"{summary['n_forecast_issuances_total']:,}",
        f"- Distinct grid points: {summary['n_grid_points']}",
        f"- Named regions: {summary['n_regions_named']} "
        f"({summary['unclassified_row_fraction']:.1%} of rows fall outside all "
        "named region boxes - 'Unclassified', a known Phase-0 regions.py "
        "coverage gap, see README)",
        f"- Variables: {', '.join(summary['variables'])}",
        f"- Lead days: {summary['lead_days']}",
        f"- init_time coverage: {summary['date_range_init_time'][0]} .. "
        f"{summary['date_range_init_time'][1]}",
        f"- valid_time coverage: {summary['date_range_valid_time'][0]} .. "
        f"{summary['date_range_valid_time'][1]}",
        f"- Missing values across all forecast/obs/error columns: "
        f"{summary['missing_values_total']} (0 expected - Phase 0's "
        "build_error_db.py already drops any row missing forecast or truth)",
        "",
        "## Bust counts",
        "",
        "| Split | Rows | Forecast issuances | Bust rate | Precip bust | Temp bust | "
        "Missed heavy-rain | False-alarm heavy-rain |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split_name in ("train", "test", "overall"):
        s = summary[split_name]
        lines.append(
            f"| {split_name} | {s['n_rows']:,} | {s['n_forecast_issuances']:,} | "
            f"{s['bust_rate']:.1%} | {s['precip_bust_rate']:.1%} | "
            f"{s['temp_bust_rate']:.1%} | {s['missed_heavy_rain_events']:,} | "
            f"{s['false_alarm_heavy_rain']:,} |"
        )
    lines += [
        "",
        "## Bust definition",
        "",
        f"- Categorical rule: {summary['bust_definition']['categorical_rule']}",
        f"- Percentile rule: {summary['bust_definition']['percentile_rule']}",
        f"- Temp hard threshold: {summary['bust_definition']['temp_hard_threshold_degC']} degC",
        "",
        "## Software",
        "",
        f"- Python {summary['software_versions']['python']} on "
        f"{summary['software_versions']['platform']}",
        f"- pandas {summary['software_versions']['pandas']}, "
        f"numpy {summary['software_versions']['numpy']}",
    ]
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    summary = build_summary()

    json_path = os.path.join(OUT_DIR, "dataset_summary.json")
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2, default=str)
    print(f"saved -> {json_path}")

    md_path = os.path.join(OUT_DIR, "dataset_summary.md")
    with open(md_path, "w") as f:
        f.write(to_markdown(summary))
    print(f"saved -> {md_path}")

    print(f"\ntotal rows: {summary['n_rows_total']:,}")
    print(f"train bust rate: {summary['train']['bust_rate']:.1%}")
    print(f"test bust rate: {summary['test']['bust_rate']:.1%}")
    print(f"missing values total: {summary['missing_values_total']}")


if __name__ == "__main__":
    main()
