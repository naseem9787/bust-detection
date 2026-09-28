"""
Phase 3 - M: model interpretability (LightGBM importance only - no SHAP,
per instructions: "do not let SHAP become a blocker"). Copies/restates
Phase 2's already-computed feature importance (same trained models) into
outputs/phase3/feature_importance.csv for a self-contained Phase 3 record,
and adds the ablation study's own per-feature-group deltas as additional
interpretive context (which GROUP of features matters, not just which
single feature).

Usage:
    .venv/Scripts/python.exe -m src.phase3.interpretability
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR

OUT_DIR = os.path.join("outputs", "phase3")


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    phase2_importance = pd.read_csv(os.path.join(PHASE2_OUT_DIR, "feature_importance.csv"))
    path = os.path.join(OUT_DIR, "feature_importance.csv")
    phase2_importance.to_csv(path, index=False)
    print(f"saved -> {path} (Phase 2 model's LightGBM gain/split importance, unchanged)")

    for target in phase2_importance.target.unique():
        top5 = (
            phase2_importance[phase2_importance.target == target]
            .sort_values("gain", ascending=False)
            .head(5)
        )
        print(f"\ntop 5 features for {target}:")
        print(top5[["feature", "gain", "split"]].to_string(index=False))

    ablation_path = os.path.join(OUT_DIR, "ablation_results.csv")
    if os.path.exists(ablation_path):
        ablation = pd.read_csv(ablation_path)
        print("\n--- which FEATURE GROUP matters most (from the ablation study) ---")
        for target in ablation.target.unique():
            d = ablation[ablation.target == target].set_index("model")
            deltas = d.roc_auc.diff().dropna()
            print(f"\n{target}: ROC-AUC delta per added feature group")
            print(deltas.round(4).to_string())


if __name__ == "__main__":
    main()
