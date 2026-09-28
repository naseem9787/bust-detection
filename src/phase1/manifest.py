"""
Phase 1 - experiment manifest: a single JSON record of everything needed to
reproduce this experiment (data sources, spatial/temporal bounds, bust
definition, split boundaries, package versions). Written after dataset
summary + evaluation so it can also record the operating threshold that
evaluate.py picked.

Usage:
    .venv/Scripts/python.exe -m src.phase1.manifest
"""
from __future__ import annotations

import json
import os
import platform
import sys

import numpy as np
import pandas as pd
import sklearn

from .. import config
from .dataset import JJAS_WINDOWS, TEST_YEAR, TRAIN_YEARS

OUT_DIR = os.path.join("outputs", "phase1")


def build_manifest() -> dict:
    eval_config_path = os.path.join(OUT_DIR, "evaluation_config.json")
    eval_config = {}
    if os.path.exists(eval_config_path):
        with open(eval_config_path) as f:
            eval_config = json.load(f)

    return {
        "phase": "Phase 1 - forecast error baselines and analysis",
        "dataset_version": "JJAS 2018-2021 (init_time-based windows)",
        "jjas_windows": JJAS_WINDOWS,
        "forecast_source": {
            "name": "ECMWF HRES (deterministic)",
            "zarr_store": config.FORECAST_STORE,
        },
        "truth_source": {
            "name": "ERA5 reanalysis",
            "zarr_store": config.TRUTH_STORE,
        },
        "spatial_bounds": {
            "lat": config.INDIA_LAT,
            "lon": config.INDIA_LON,
            "bbox_buffer_deg": config.BBOX_BUFFER_DEG,
            "grid_resolution_deg": 1.5,
        },
        "lead_days": config.LEAD_DAYS,
        "lead_hours": config.LEAD_HOURS,
        "variables": config.VARIABLES,
        "bust_definition": {
            "categorical_rule": {
                "description": "IMD rainfall-category gap >=2, or heavy-or-above missed/false-alarmed",
                "imd_rain_bins_mm": config.IMD_RAIN_BINS,
                "imd_rain_labels": config.IMD_RAIN_LABELS,
                "heavy_or_above_index": config.HEAVY_OR_ABOVE_INDEX,
            },
            "percentile_rule": {
                "description": (
                    "|error| > Nth percentile per (region, lead_day), threshold "
                    "fit on TRAIN split only (Phase 1 fix over Phase 0's global-"
                    "sample threshold - see src/phase1/dataset.py docstring)"
                ),
                "percentile": config.BUST_PERCENTILE,
            },
            "temp_hard_threshold_degC": config.TEMP_BUST_ABS_ERROR_K,
        },
        "regions": {
            "method": "coarse lat/lon bounding boxes (src/regions.py), not a real shapefile",
            "note": (
                "Boxes don't tile the full India+buffer domain, so a majority of "
                "grid cells fall in 'Unclassified' - see dataset_summary.md"
            ),
        },
        "temporal_split": {
            "method": "chronological (no random splitting)",
            "train_years": TRAIN_YEARS,
            "test_year_unseen_holdout": TEST_YEAR,
        },
        "evaluation": eval_config,
        "baselines": {
            "A_historical_climatology": "P(bust | region, lead_day, month), fit on train",
            "B_lead_time_only": "P(bust | lead_day), fit on train",
            "C_ensemble_spread": "NOT AVAILABLE - see src/phase1/baselines.py BASELINE_C_STATUS",
        },
        "random_seed": "not applicable - all Phase 1 baselines are deterministic "
        "historical-frequency lookups; no stochastic component is used",
        "software_versions": {
            "python": sys.version.split()[0],
            "platform": platform.platform(),
            "pandas": pd.__version__,
            "numpy": np.__version__,
            "scikit_learn": sklearn.__version__,
        },
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    manifest = build_manifest()
    path = os.path.join(OUT_DIR, "experiment_manifest.json")
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
    print(f"saved -> {path}")


if __name__ == "__main__":
    main()
