"""
Phase 2 - B2: first real predictive model - LightGBM, trained separately for
each of Phase 2A's two evidence-backed candidate targets (bust_precip_categorical,
bust_temp_hard). A modest model: fixed, reasonable hyperparameters, one
chronological validation split for early stopping (NOT hyperparameter search),
never touching the 2021 test set until final scoring.

Procedure (per target):
  1. Fit on 2018-2019, validate (early stopping only) on 2020 - chronological,
     no random shuffling anywhere.
  2. Take the best_iteration from step 1, then refit ONE final model on all
     of 2018-2020 (train) with that fixed number of trees - standard practice
     so the final model sees all available training data.
  3. Score ONCE on 2021 (test) - never touched before this point.

Usage:
    .venv/Scripts/python.exe -m src.phase2.train_model
"""
from __future__ import annotations

import json
import os

import lightgbm as lgb
import numpy as np
import pandas as pd

from .features import FEATURE_COLS, OUT_DIR, TARGET_COLS

RANDOM_SEED = 42
FIT_YEARS = [2018, 2019]
VAL_YEAR = 2020

NUMERIC_FEATURES = [c for c in FEATURE_COLS if c != "region_v2"]
CATEGORICAL_FEATURES = ["region_v2"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

BASE_PARAMS = dict(
    objective="binary",
    learning_rate=0.05,
    num_leaves=31,
    min_child_samples=200,
    subsample=0.8,
    subsample_freq=1,
    colsample_bytree=0.8,
    random_state=RANDOM_SEED,
    n_jobs=-1,
    verbosity=-1,
)
MAX_ESTIMATORS = 1000
EARLY_STOPPING_ROUNDS = 50


def _xy(df: pd.DataFrame, target: str) -> tuple[pd.DataFrame, pd.Series]:
    X = df[ALL_FEATURES].copy()
    y = df[target].astype(int)
    return X, y


def train_one_target(train: pd.DataFrame, test: pd.DataFrame, target: str) -> dict:
    fit_df = train[train.init_time.dt.year.isin(FIT_YEARS)]
    val_df = train[train.init_time.dt.year == VAL_YEAR]
    assert len(fit_df) > 0 and len(val_df) > 0

    X_fit, y_fit = _xy(fit_df, target)
    X_val, y_val = _xy(val_df, target)

    probe = lgb.LGBMClassifier(n_estimators=MAX_ESTIMATORS, **BASE_PARAMS)
    probe.fit(
        X_fit, y_fit,
        eval_set=[(X_val, y_val)],
        eval_metric="auc",
        callbacks=[lgb.early_stopping(EARLY_STOPPING_ROUNDS, verbose=False), lgb.log_evaluation(0)],
    )
    best_iteration = probe.best_iteration_ or MAX_ESTIMATORS
    # validation-set (2020) predictions from the PROBE model (trained only on
    # 2018-2019, never seeing 2020) - used later to fit calibration on data
    # disjoint from the final model's own training set (2018-2020 refit).
    y_val_prob = probe.predict_proba(X_val)[:, 1]

    X_train, y_train = _xy(train, target)
    final_model = lgb.LGBMClassifier(n_estimators=best_iteration, **BASE_PARAMS)
    final_model.fit(X_train, y_train)

    X_test, y_test = _xy(test, target)
    y_prob = final_model.predict_proba(X_test)[:, 1]

    return {
        "target": target,
        "model": final_model,
        "best_iteration": int(best_iteration),
        "y_test": y_test.to_numpy(),
        "y_prob": y_prob,
        "test_index": test.index.to_numpy(),
        "y_val": y_val.to_numpy(),
        "y_val_prob": y_val_prob,
        "fit_years": FIT_YEARS,
        "val_year": VAL_YEAR,
        "train_years": sorted(train.init_time.dt.year.unique().tolist()),
        "n_fit": len(fit_df),
        "n_val": len(val_df),
        "n_train_final": len(train),
        "n_test": len(test),
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    train = pd.read_parquet(os.path.join(OUT_DIR, "features_train.parquet"))
    test = pd.read_parquet(os.path.join(OUT_DIR, "features_test.parquet"))
    train["region_v2"] = train["region_v2"].astype("category")
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].cat.categories)
    )

    results = {}
    config_log = {
        "random_seed": RANDOM_SEED,
        "base_params": {k: v for k, v in BASE_PARAMS.items() if k != "random_state"},
        "max_estimators": MAX_ESTIMATORS,
        "early_stopping_rounds": EARLY_STOPPING_ROUNDS,
        "fit_years": FIT_YEARS,
        "val_year": VAL_YEAR,
        "test_year": 2021,
        "features": ALL_FEATURES,
        "targets": {},
    }

    for target in TARGET_COLS:
        print(f"\n=== training LightGBM for target={target} ===")
        res = train_one_target(train, test, target)
        results[target] = res
        print(
            f"best_iteration={res['best_iteration']} "
            f"n_fit={res['n_fit']:,} n_val={res['n_val']:,} "
            f"n_train_final={res['n_train_final']:,} n_test={res['n_test']:,}"
        )

        model_path = os.path.join(OUT_DIR, f"lightgbm_{target}.txt")
        res["model"].booster_.save_model(model_path)
        print(f"saved -> {model_path}")

        pred_path = os.path.join(OUT_DIR, f"predictions_{target}.parquet")
        pred_df = pd.DataFrame(
            {
                "index": res["test_index"],
                "y_true": res["y_test"],
                "y_prob": res["y_prob"],
            }
        )
        pred_df.to_parquet(pred_path, index=False)
        print(f"saved -> {pred_path}")

        val_pred_path = os.path.join(OUT_DIR, f"val_predictions_{target}.parquet")
        pd.DataFrame({"y_true": res["y_val"], "y_prob": res["y_val_prob"]}).to_parquet(
            val_pred_path, index=False
        )
        print(f"saved -> {val_pred_path}")

        config_log["targets"][target] = {
            "best_iteration": res["best_iteration"],
            "n_fit": res["n_fit"],
            "n_val": res["n_val"],
            "n_train_final": res["n_train_final"],
            "n_test": res["n_test"],
            "train_prevalence": float(train[target].mean()),
            "test_prevalence": float(test[target].mean()),
        }

    config_path = os.path.join(OUT_DIR, "model_training_config.json")
    with open(config_path, "w") as f:
        json.dump(config_log, f, indent=2, default=str)
    print(f"\nsaved -> {config_path}")


if __name__ == "__main__":
    main()
