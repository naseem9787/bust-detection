"""
Phase 3 - re-runs lead/regional robustness (Stages H/I) with the Phase 3
extended model (Model 6 - full-scale wind added) as a third comparison
column alongside the historical baseline and the Phase 2 model. Model 7
(ensemble) is NOT included here - it only has predictions for the small
pilot-window subset, not the full 2021 test set these breakdowns need.

Usage:
    .venv/Scripts/python.exe -m src.phase3.finalize_robustness
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR, TARGET_COLS
from . import lead_region_robustness as lrr
from . import modeling
from .ablation import GROUP5
from .atmo_merge import WIND_FEATURE_COLS, merge_wind_features

MODEL6_FEATURES = GROUP5 + WIND_FEATURE_COLS


def train_model6_predictions() -> dict[str, "pd.Series"]:
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))
    train = merge_wind_features(train, [2018, 2019, 2020])
    test = merge_wind_features(test, [2021])
    train["region_v2"] = train["region_v2"].astype("category")
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].cat.categories)
    )
    assert test[WIND_FEATURE_COLS].isna().sum().sum() == 0, "wind merge should be complete at full scale"

    preds = {}
    for target in TARGET_COLS:
        res = modeling.train_lgbm(train, test, target, MODEL6_FEATURES)
        preds[target] = res["y_prob"]
    return preds


def main() -> None:
    print("=== training Model 6 for lead/region robustness comparison ===")
    phase3_preds = train_model6_predictions()

    print("\n=== lead robustness (baseline vs Phase 2 vs Phase 3/Model6) ===")
    lead_df = lrr.run_lead_robustness(phase3_preds)
    print(lead_df.to_string(index=False))

    print("\n=== regional robustness (baseline vs Phase 2 vs Phase 3/Model6) ===")
    region_df = lrr.run_regional_robustness(phase3_preds)
    print(region_df.to_string(index=False))


if __name__ == "__main__":
    main()
