"""
Phase 4 - one-time (re-runnable) build script that produces the actual
production model artifacts. This is NOT part of the runtime API - it's
run manually when a new production model version is cut, exactly the way
src/phase2/train_model.py and src/phase3/model6_atmosphere.py were run
manually during research. The runtime (src/production/inference.py) only
ever LOADS what this script writes; it never trains.

Production models (validated in Phase 3, NOT the pilot-scope ensemble
model - see src/phase3/ensemble_pilot_experiment.py's docstring for why
that one is excluded):

  rain_v1        = Phase 2's exact Model 5 (GROUP5 feature set, no wind -
                    wind did not help this target, see
                    outputs/phase3/ablation_results.csv). Reuses the
                    ALREADY-TRAINED, already-validated artifact at
                    outputs/phase2/lightgbm_bust_precip_categorical.txt
                    rather than retraining (retraining with a different
                    column order gives near-identical but not bit-exact
                    results - see outputs/phase3/replication_results.csv
                    for how tight that difference is; using the original
                    file avoids the question entirely).

  temperature_v1 = Phase 3's Model 6 (GROUP5 + wind_speed_10m, full JJAS
                    2018-2021 scale) - validated to meaningfully beat the
                    no-wind model for this target
                    (outputs/phase3/ablation_results.csv:
                    Model6_Atmosphere_Wind vs Model5). This was only
                    trained transiently in src/phase3/model6_atmosphere.py
                    and never persisted - this script retrains it ONCE,
                    with the same fit/validate/refit procedure, and saves
                    the model file plus the validation-year predictions
                    needed to fit calibration.

Usage:
    .venv/Scripts/python.exe -m src.production.build_artifacts
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess

import pandas as pd

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR
from ..phase3 import modeling
from ..phase3.ablation import GROUP5
from ..phase3.atmo_merge import WIND_FEATURE_COLS, merge_wind_features

ARTIFACT_DIR = os.path.join("models", "artifacts")

RAIN_TARGET = "bust_precip_categorical"
TEMP_TARGET = "bust_temp_hard"
TEMP_FEATURES = GROUP5 + WIND_FEATURE_COLS


def _git_commit() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=os.path.dirname(__file__), text=True
        ).strip()
    except Exception:
        return "unknown"


def build_rain_artifact() -> dict:
    """Copies the existing, already-validated Phase 2 model file verbatim -
    no retraining, so there is zero risk of a numerically-slightly-
    different production model versus what Phase 2/3 actually validated."""
    src_model = os.path.join(PHASE2_OUT_DIR, f"lightgbm_{RAIN_TARGET}.txt")
    dst_model = os.path.join(ARTIFACT_DIR, "rain_v1.txt")
    shutil.copyfile(src_model, dst_model)

    import lightgbm as lgb

    booster = lgb.Booster(model_file=dst_model)
    feature_order = booster.feature_name()

    val_src = os.path.join(PHASE2_OUT_DIR, f"val_predictions_{RAIN_TARGET}.parquet")
    val_dst = os.path.join(ARTIFACT_DIR, "rain_v1_val_predictions.parquet")
    shutil.copyfile(val_src, val_dst)

    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    print(f"[rain_v1] copied {src_model} -> {dst_model}")
    print(f"[rain_v1] feature order ({len(feature_order)}): {feature_order}")
    return {
        "feature_order": feature_order,
        "train_prevalence": float(train[RAIN_TARGET].mean()),
    }


def build_temperature_artifact() -> dict:
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))
    train = merge_wind_features(train, [2018, 2019, 2020])
    test = merge_wind_features(test, [2021])
    train["region_v2"] = train["region_v2"].astype("category")
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].cat.categories)
    )
    assert test[WIND_FEATURE_COLS].isna().sum().sum() == 0, "wind must fully cover the 2021 test set"
    assert train[WIND_FEATURE_COLS].isna().sum().sum() == 0, "wind must fully cover 2018-2020 train"

    # same fit/validate/refit procedure as Phase 2/3, but this time we KEEP
    # the probe model's validation predictions (needed for calibration) and
    # SAVE the final model (Phase 3's model6_atmosphere.py discarded both).
    fit_df = train[train.init_time.dt.year.isin(modeling.FIT_YEARS)]
    val_df = train[train.init_time.dt.year == modeling.VAL_YEAR]

    import lightgbm as lgb

    X_fit, y_fit = fit_df[TEMP_FEATURES], fit_df[TEMP_TARGET].astype(int)
    X_val, y_val = val_df[TEMP_FEATURES], val_df[TEMP_TARGET].astype(int)
    probe = lgb.LGBMClassifier(n_estimators=modeling.MAX_ESTIMATORS, **modeling.BASE_PARAMS)
    probe.fit(
        X_fit, y_fit,
        eval_set=[(X_val, y_val)],
        eval_metric="auc",
        callbacks=[lgb.early_stopping(modeling.EARLY_STOPPING_ROUNDS, verbose=False), lgb.log_evaluation(0)],
    )
    best_iteration = probe.best_iteration_ or modeling.MAX_ESTIMATORS
    y_val_prob = probe.predict_proba(X_val)[:, 1]

    X_train, y_train = train[TEMP_FEATURES], train[TEMP_TARGET].astype(int)
    final_model = lgb.LGBMClassifier(n_estimators=best_iteration, **modeling.BASE_PARAMS)
    final_model.fit(X_train, y_train)

    X_test, y_test = test[TEMP_FEATURES], test[TEMP_TARGET].astype(int)
    y_prob = final_model.predict_proba(X_test)[:, 1]

    dst_model = os.path.join(ARTIFACT_DIR, "temperature_v1.txt")
    final_model.booster_.save_model(dst_model)
    feature_order = final_model.booster_.feature_name()
    print(f"[temperature_v1] saved -> {dst_model} (best_iteration={best_iteration})")
    print(f"[temperature_v1] feature order ({len(feature_order)}): {feature_order}")

    val_pred_path = os.path.join(ARTIFACT_DIR, "temperature_v1_val_predictions.parquet")
    pd.DataFrame({"y_true": y_val.to_numpy(), "y_prob": y_val_prob}).to_parquet(val_pred_path, index=False)
    print(f"[temperature_v1] saved -> {val_pred_path}")

    from sklearn.metrics import (
        average_precision_score, brier_score_loss, roc_auc_score,
    )

    metrics = {
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "pr_auc": float(average_precision_score(y_test, y_prob)),
        "brier_score": float(brier_score_loss(y_test, y_prob)),
        "best_iteration": int(best_iteration),
    }
    print(f"[temperature_v1] 2021 test metrics: {metrics}")

    return {
        "feature_order": feature_order,
        "best_iteration": int(best_iteration),
        "train_prevalence": float(train[TEMP_TARGET].mean()),
        "test_metrics": metrics,
    }


def main() -> None:
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    print("=== building rain_v1 artifact ===")
    rain_info = build_rain_artifact()
    print("\n=== building temperature_v1 artifact (Model 6 - retrained + persisted) ===")
    temp_info = build_temperature_artifact()

    build_manifest = {
        "git_commit": _git_commit(),
        "rain_v1": rain_info,
        "temperature_v1": temp_info,
    }
    manifest_path = os.path.join(ARTIFACT_DIR, "build_manifest.json")
    with open(manifest_path, "w") as f:
        json.dump(build_manifest, f, indent=2, default=str)
    print(f"\nsaved -> {manifest_path}")


if __name__ == "__main__":
    main()
