"""
Phase 4 - builds models/registry/{rain,temperature}_v1.json from the actual
build/calibration manifests and Phase 3 output files (never hand-typed -
"use the actual Phase 3 output files as the source of truth").

Usage (after build_artifacts.py and build_calibration.py have run):
    .venv/Scripts/python.exe -m src.production.build_registry
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

import lightgbm as lgb
import pandas as pd

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR
from .build_artifacts import ARTIFACT_DIR, RAIN_TARGET, TEMP_TARGET

REGISTRY_DIR = os.path.join("models", "registry")

BUST_DEFINITIONS = {
    RAIN_TARGET: (
        "IMD rainfall-category miss: forecast and observed 24h rainfall fall "
        ">=2 IMD categories apart (no_rain/light/moderate/heavy/very_heavy/"
        "extremely_heavy), OR a heavy-or-above event is missed or falsely "
        "predicted. Fixed physical bins (config.IMD_RAIN_BINS), not a "
        "percentile threshold - see src/label_busts.py and "
        "src/phase2/bust_definition_audit.md."
    ),
    TEMP_TARGET: (
        "Temperature hard-threshold bust: |forecast 2m temperature - "
        "observed 2m temperature| > 3.0 degC. Fixed physical threshold "
        "(config.TEMP_BUST_ABS_ERROR_K), not data-derived - see "
        "src/label_busts.py."
    ),
}


def _git_commit() -> str:
    with open(os.path.join(ARTIFACT_DIR, "build_manifest.json")) as f:
        return json.load(f).get("git_commit", "unknown")


def build_registry_entry(
    model_key: str,
    target: str,
    display_name: str,
    model_filename: str,
    feature_order: list[str],
    lead_col: str,
    extra_notes: str,
) -> dict:
    lead_df = pd.read_csv(os.path.join("outputs", "phase3", "lead_robustness.csv"))
    lead_rows = lead_df[lead_df.target == target].sort_values("lead_day")
    lead_curve = {
        int(r.lead_day): {
            "roc_auc": None if pd.isna(r[f"roc_auc_{lead_col}"]) else round(float(r[f"roc_auc_{lead_col}"]), 4),
            "pr_auc": None if pd.isna(r[f"pr_auc_{lead_col}"]) else round(float(r[f"pr_auc_{lead_col}"]), 4),
            "brier": None if pd.isna(r[f"brier_{lead_col}"]) else round(float(r[f"brier_{lead_col}"]), 4),
            "n": int(r.n),
        }
        for _, r in lead_rows.iterrows()
    }

    year_df = pd.read_csv(os.path.join("outputs", "phase3", "year_robustness.csv"))
    year_rows = year_df[year_df.target == target]
    year_robustness = year_rows[
        ["experiment", "train_years", "test_year", "roc_auc", "pr_auc", "brier_score", "brier_skill_score", "n", "prevalence"]
    ].round(4).to_dict(orient="records")

    calibration = json.load(open(os.path.join(ARTIFACT_DIR, "calibration_manifest.json")))
    calib_entry = next(c for c in calibration if c["target"] == target)

    booster = lgb.Booster(model_file=os.path.join(ARTIFACT_DIR, model_filename))
    actual_feature_order = booster.feature_name()
    assert actual_feature_order == feature_order, (
        f"registry feature_order does not match the persisted model's own order for {model_key} - "
        "this would silently break inference; refusing to build a mismatched registry entry"
    )

    return {
        "model_name": model_key,
        "model_version": "v1",
        "display_name": display_name,
        "status": "production",
        "target_variable": target,
        "target_definition": BUST_DEFINITIONS[target],
        "model_artifact_path": f"models/artifacts/{model_filename}",
        "calibration": {
            "method": calib_entry["method"],
            "artifact_path": calib_entry["artifact_path"],
            "fit_on": calib_entry["fit_on"],
            "evaluated_on": calib_entry["evaluated_on"],
            "brier_raw": calib_entry["brier_raw"],
            "brier_calibrated": calib_entry["brier_calibrated"],
        },
        "feature_order": feature_order,
        "n_features": len(feature_order),
        "training_config": {
            "algorithm": "LightGBM (binary classification)",
            "fit_years": [2018, 2019],
            "validation_year": 2020,
            "final_train_years": [2018, 2019, 2020],
            "test_year": 2021,
            "random_seed": 42,
            "hyperparameters": {
                "learning_rate": 0.05, "num_leaves": 31, "min_child_samples": 200,
                "subsample": 0.8, "colsample_bytree": 0.8,
            },
        },
        "source_dataset": {
            "forecast_source": "ECMWF HRES (deterministic)",
            "truth_source": "ERA5 reanalysis",
            "domain": "India + neighboring buffer, restricted to in-India-domain grid cells "
                      "(183 of 702 points - see outputs/phase2/region_assignment_summary.csv)",
            "date_range": "JJAS 2018-2021 (init_time-based)",
            "grid_resolution_deg": 1.5,
        },
        "region_mapping": {
            "source": "src/phase2/geography.py (public GADM-derived state boundaries)",
            "n_regions": 29,
            "known_limitation": (
                "boundary vintage predates 2014 Telangana split (merged into Andhra "
                "Pradesh) and 2019 Ladakh split (merged into Jammu & Kashmir)"
            ),
        },
        "metrics_2021_test": lead_curve,
        "year_robustness": year_robustness,
        "git_commit": _git_commit(),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "notes": extra_notes,
    }


def main() -> None:
    os.makedirs(REGISTRY_DIR, exist_ok=True)

    rain_features = lgb.Booster(model_file=os.path.join(ARTIFACT_DIR, "rain_v1.txt")).feature_name()
    rain_entry = build_registry_entry(
        model_key="rain_v1",
        target=RAIN_TARGET,
        display_name="Rainfall category-miss bust probability",
        model_filename="rain_v1.txt",
        feature_order=rain_features,
        lead_col="phase2",  # the lead_robustness.csv column matching this exact model
        extra_notes=(
            "Identical model to Phase 2's full feature-set LightGBM (Model 5 in the "
            "Phase 3 ablation). Wind was tested (Phase 3 Model 6) and did NOT "
            "meaningfully help this target, so it is excluded from rain_v1."
        ),
    )
    with open(os.path.join(REGISTRY_DIR, "rain_v1.json"), "w") as f:
        json.dump(rain_entry, f, indent=2, default=str)
    print(f"saved -> {os.path.join(REGISTRY_DIR, 'rain_v1.json')}")

    temp_features = lgb.Booster(model_file=os.path.join(ARTIFACT_DIR, "temperature_v1.txt")).feature_name()
    temp_entry = build_registry_entry(
        model_key="temperature_v1",
        target=TEMP_TARGET,
        display_name="Temperature hard-threshold bust probability",
        model_filename="temperature_v1.txt",
        feature_order=temp_features,
        lead_col="phase3",  # this CSV column is exactly Model 6
        extra_notes=(
            "Phase 3 Model 6: Phase 2's full feature set PLUS 10m_wind_speed "
            "(full JJAS 2018-2021 scale, not the pilot-scope ensemble/humidity/"
            "geopotential features - those remain experimental, see "
            "src/phase3/ensemble_pilot_experiment.py)."
        ),
    )
    with open(os.path.join(REGISTRY_DIR, "temperature_v1.json"), "w") as f:
        json.dump(temp_entry, f, indent=2, default=str)
    print(f"saved -> {os.path.join(REGISTRY_DIR, 'temperature_v1.json')}")


if __name__ == "__main__":
    main()
