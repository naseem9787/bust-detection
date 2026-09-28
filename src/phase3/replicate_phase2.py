"""
Phase 3 - E: independently replicate the Phase 2 LightGBM result BEFORE
adding any new complexity. Re-derives the feature table and retrains both
models from scratch, using Phase 2's own code (src.phase2.features,
src.phase2.train_model) unmodified, and compares against the numbers
already recorded in outputs/phase2/model_comparison.csv.

Does NOT overwrite any outputs/phase2/ file - writes only to
outputs/phase3/replication_results.csv.

A LightGBM model trained with n_jobs>1 can have tiny (sub-0.001) floating-
point non-determinism from multithreaded split-finding sum order, so this
does not require BIT-IDENTICAL results - a "changed dramatically" threshold
is applied instead (see DIFFERENCE_ALERT_THRESHOLD).

Usage:
    .venv/Scripts/python.exe -m src.phase3.replicate_phase2
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2 import features as p2features
from ..phase2 import train_model as p2train
from ..phase2.evaluate_model import build_comparison_table

OUT_DIR = os.path.join("outputs", "phase3")
PHASE2_COMPARISON_PATH = os.path.join("outputs", "phase2", "model_comparison.csv")

DIFFERENCE_ALERT_THRESHOLD = 0.02  # absolute ROC-AUC difference that triggers investigation


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    original = pd.read_csv(PHASE2_COMPARISON_PATH)
    original_lgbm = original[original.method == "LightGBM"].set_index("target")

    print("=== re-deriving feature table from scratch (Phase 2's own code) ===")
    train, test = p2features.build_features()
    train["region_v2"] = train["region_v2"].astype("category")
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].cat.categories)
    )

    rows = []
    for target in p2features.TARGET_COLS:
        print(f"\n=== replicating LightGBM for {target} ===")
        res = p2train.train_one_target(train, test, target)
        test_with_pred = test.copy()
        test_with_pred["y_prob_lgbm"] = res["y_prob"]
        comparison = build_comparison_table(train, test_with_pred, target)
        replicated = comparison[comparison.method == "LightGBM"].iloc[0]

        orig = original_lgbm.loc[target]
        for metric in ["roc_auc", "pr_auc", "brier_score", "brier_skill_score"]:
            prev = float(orig[metric])
            new = float(replicated[metric])
            diff = new - prev
            rows.append(
                {
                    "target": target,
                    "metric": metric,
                    "phase2_recorded": prev,
                    "phase3_replicated": new,
                    "difference": diff,
                    "flagged": abs(diff) > DIFFERENCE_ALERT_THRESHOLD if metric == "roc_auc" else None,
                }
            )
        print(
            f"  ROC-AUC: recorded={orig['roc_auc']:.4f} replicated={replicated['roc_auc']:.4f} "
            f"diff={replicated['roc_auc'] - orig['roc_auc']:+.4f}"
        )

    out = pd.DataFrame(rows)
    out_path = os.path.join(OUT_DIR, "replication_results.csv")
    out.to_csv(out_path, index=False)
    print(f"\nsaved -> {out_path}")
    print(out.to_string(index=False))

    flagged = out[out.flagged == True]  # noqa: E712
    if len(flagged) > 0:
        print(
            f"\n*** STOP CONDITION CHECK: {len(flagged)} target(s) show a ROC-AUC "
            f"difference > {DIFFERENCE_ALERT_THRESHOLD} - investigate before proceeding ***"
        )
    else:
        print(
            f"\nReplication OK - no ROC-AUC difference exceeds {DIFFERENCE_ALERT_THRESHOLD}. "
            "Proceeding to Stage F."
        )


if __name__ == "__main__":
    main()
