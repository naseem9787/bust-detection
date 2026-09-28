"""
Phase 3 - F (Model 6): adds the new full-scale atmospheric variable
(wind_speed_10m - the only one affordable at full JJAS 2018-2021 scale,
see atmospheric_features.py) to the ablation study, evaluated on the FULL
2021 test set exactly like Models 0-5 - a fair, directly comparable
addition (unlike the pilot-scope humidity/geopotential/ensemble features,
which get their own separate small-sample experiment in
ensemble_pilot_experiment.py).

Usage (after fetch_atmo_multi_year.sh has produced atmo_wind_*.nc for
2018-2021):
    .venv/Scripts/python.exe -m src.phase3.model6_atmosphere
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR, TARGET_COLS
from . import modeling
from .ablation import GROUP5
from .atmo_merge import WIND_FEATURE_COLS, merge_wind_features

OUT_DIR = os.path.join("outputs", "phase3")

MODEL6_FEATURES = GROUP5 + WIND_FEATURE_COLS


def run() -> pd.DataFrame:
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))

    train = merge_wind_features(train, [2018, 2019, 2020])
    test = merge_wind_features(test, [2021])
    train["region_v2"] = train["region_v2"].astype("category")
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].cat.categories)
    )
    train = train.dropna(subset=WIND_FEATURE_COLS)
    test = test.dropna(subset=WIND_FEATURE_COLS)
    print(f"after wind merge: train={len(train):,} test={len(test):,}")

    rows = []
    for target in TARGET_COLS:
        reference_prob = float(train[target].mean())
        print(f"\n=== Model6_Atmosphere for {target} ===")
        res = modeling.train_lgbm(train, test, target, MODEL6_FEATURES)
        metrics = modeling.score(res["y_test"], res["y_prob"], reference_prob, reference_prob)
        row = {"model": "Model6_Atmosphere_Wind", "target": target,
               "n_features": len(MODEL6_FEATURES), "best_iteration": res["best_iteration"], **metrics}
        rows.append(row)
        print(f"  ROC-AUC={row['roc_auc']:.4f} PR-AUC={row['pr_auc']:.4f} "
              f"Brier={row['brier_score']:.4f} BSS={row['brier_skill_score']:.4f}")

    result = pd.DataFrame(rows)
    os.makedirs(OUT_DIR, exist_ok=True)
    ablation_path = os.path.join(OUT_DIR, "ablation_results.csv")
    existing = pd.read_csv(ablation_path)
    existing = existing[existing.model != "Model6_Atmosphere_Wind"]  # idempotent re-run
    combined = pd.concat([existing, result], ignore_index=True)
    combined.to_csv(ablation_path, index=False)
    print(f"\nappended Model6 to -> {ablation_path}")
    return result


if __name__ == "__main__":
    run()
