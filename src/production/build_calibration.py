"""
Phase 4 - one-time build script: fits and persists the production
calibration artifact for each target, using Phase 3's validated
methodology (isotonic regression fit on validation-year predictions from
the PROBE model, which never saw that year during training - never the
2021 test year).

For rain_v1 (identical model to Phase 3's original), Phase 3 already
established calibration does NOT improve Brier - that decision is reused
directly. For temperature_v1 (Model 6 - a genuinely different, newly-
persisted model with wind added), the decision is NOT assumed from Phase
3's original (no-wind) result - it's independently refit and evaluated on
Model 6's own validation predictions, per instructions ("preserve the
validated decision... rather than inventing a new strategy" refers to not
inventing a new STRATEGY, not to skipping validation for a model that
was never tested before).

Usage:
    .venv/Scripts/python.exe -m src.production.build_calibration
"""
from __future__ import annotations

import json
import os

import lightgbm as lgb
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR
from ..phase3.atmo_merge import merge_wind_features
from .build_artifacts import ARTIFACT_DIR, RAIN_TARGET, TEMP_FEATURES, TEMP_TARGET


def fit_and_evaluate(target: str, val_path: str, model_path: str, feature_cols: list[str]) -> dict:
    val = pd.read_parquet(val_path)
    booster = lgb.Booster(model_file=model_path)

    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))
    if "wind_speed_10m" in feature_cols:
        test = merge_wind_features(test, [2021])
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].astype("category").cat.categories)
    )
    y_test = test[target].to_numpy().astype(int)
    y_test_prob_raw = booster.predict(test[feature_cols])

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(val["y_prob"], val["y_true"])
    y_test_prob_iso = iso.predict(y_test_prob_raw)

    brier_raw = brier_score_loss(y_test, y_test_prob_raw)
    brier_iso = brier_score_loss(y_test, y_test_prob_iso)
    use_isotonic = bool(brier_iso < brier_raw)

    artifact_path = os.path.join(ARTIFACT_DIR, f"{target}_calibrator.pkl")
    if use_isotonic:
        import pickle

        with open(artifact_path, "wb") as f:
            pickle.dump(iso, f)
        print(f"[{target}] isotonic calibration IMPROVES Brier "
              f"({brier_raw:.4f} -> {brier_iso:.4f}) - artifact saved -> {artifact_path}")
    else:
        print(f"[{target}] isotonic calibration does NOT improve Brier "
              f"({brier_raw:.4f} -> {brier_iso:.4f}) - production uses RAW probability, "
              "per Phase 3's validated decision-making rule (don't calibrate when it doesn't help)")
        if os.path.exists(artifact_path):
            os.remove(artifact_path)

    return {
        "target": target,
        "method": "isotonic" if use_isotonic else "none (raw preserved)",
        "brier_raw": float(brier_raw),
        "brier_calibrated": float(brier_iso),
        "improves": use_isotonic,
        "fit_on": "2020 validation-year predictions (probe model, never trained on 2020 or 2021)",
        "evaluated_on": "2021 test set",
        "artifact_path": artifact_path if use_isotonic else None,
    }


def main() -> None:
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    results = []

    rain_val = os.path.join(ARTIFACT_DIR, "rain_v1_val_predictions.parquet")
    rain_model = os.path.join(ARTIFACT_DIR, "rain_v1.txt")
    rain_features = lgb.Booster(model_file=rain_model).feature_name()
    results.append(fit_and_evaluate(RAIN_TARGET, rain_val, rain_model, rain_features))

    temp_val = os.path.join(ARTIFACT_DIR, "temperature_v1_val_predictions.parquet")
    temp_model = os.path.join(ARTIFACT_DIR, "temperature_v1.txt")
    results.append(fit_and_evaluate(TEMP_TARGET, temp_val, temp_model, TEMP_FEATURES))

    path = os.path.join(ARTIFACT_DIR, "calibration_manifest.json")
    with open(path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    print(f"\nsaved -> {path}")


if __name__ == "__main__":
    main()
