"""
Phase 4 - persists the two STATIC lookup tables production inference needs
(region grid mapping, train-only-fit historical climatology), so a fresh
process can load them once at startup instead of recomputing from the
multi-GB error_db.parquet on every launch (see docs/production_inference.md
Performance section).

Usage:
    .venv/Scripts/python.exe -m src.production.build_static_artifacts
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2.features import build_features, fit_historical_features
from ..phase2.geography import build_region_map
from .build_artifacts import ARTIFACT_DIR


def main() -> None:
    os.makedirs(ARTIFACT_DIR, exist_ok=True)

    region_map = build_region_map()
    region_path = os.path.join(ARTIFACT_DIR, "region_grid.parquet")
    region_map.to_parquet(region_path, index=False)
    print(f"saved -> {region_path} ({len(region_map)} grid points)")

    train, _ = build_features()  # train-only, per the leakage rules
    fitted = fit_historical_features(train)

    rows = []
    for name, (lookup, fallback) in fitted.items():
        df = lookup.rename("value").reset_index()
        df["feature_name"] = name
        df["fallback"] = fallback
        rows.append(df)
    hist_table = pd.concat(rows, ignore_index=True)
    hist_path = os.path.join(ARTIFACT_DIR, "historical_features.parquet")
    hist_table.to_parquet(hist_path, index=False)
    print(f"saved -> {hist_path} ({len(hist_table)} rows, {len(fitted)} feature tables)")

    print(f"\ntrain-period domain means (for anomaly-feature fallback):")
    dm_precip = float(train.fcst_precip_mm.mean())
    dm_temp = float(train.fcst_temp_c.mean())
    print(f"  precip: {dm_precip:.3f} mm, temp: {dm_temp:.3f} degC")

    import json

    with open(os.path.join(ARTIFACT_DIR, "domain_means.json"), "w") as f:
        json.dump({"fcst_precip_mm": dm_precip, "fcst_temp_c": dm_temp}, f, indent=2)
    print(f"saved -> {os.path.join(ARTIFACT_DIR, 'domain_means.json')}")


if __name__ == "__main__":
    main()
