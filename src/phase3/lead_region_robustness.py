"""
Phase 3 - H/I: robustness by lead time and by region, comparing the
historical baseline, the Phase 2 model, and (once available) the Phase 3
extended model, all on the SAME 2021 test set/targets.

Reuses Phase 2's already-computed test predictions (outputs/phase2/
predictions_{target}.parquet) rather than retraining - the Phase 2 model
is unchanged, no need to reproduce it a third time.

Usage:
    .venv/Scripts/python.exe -m src.phase3.lead_region_robustness
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR
from ..phase2.features import TARGET_COLS

OUT_DIR = os.path.join("outputs", "phase3")
MIN_SAMPLE_WARNING = 500  # per-region sample count below which results are flagged low-confidence


def _load_test_with_predictions(target: str) -> pd.DataFrame:
    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    preds = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, f"predictions_{target}.parquet"))
    assert len(preds) == len(test)
    test = test.reset_index(drop=True)
    test["y_prob_phase2"] = preds["y_prob"].to_numpy()

    hist_lookup = train.groupby(["region_v2", "lead_day", "month"], observed=True)[target].mean()
    hist_fallback = float(train[target].mean())
    keys = pd.MultiIndex.from_frame(test[["region_v2", "lead_day", "month"]])
    test["y_prob_baseline"] = pd.Series(keys.map(hist_lookup), index=test.index).fillna(
        hist_fallback
    ).to_numpy()
    return test


def _safe_auc(y_true, y_prob) -> float:
    if y_true.min() == y_true.max():
        return float("nan")
    return roc_auc_score(y_true, y_prob)


def _safe_pr_auc(y_true, y_prob) -> float:
    if y_true.max() == 0:
        return float("nan")
    return average_precision_score(y_true, y_prob)


def _metrics_by_group(
    test: pd.DataFrame, target: str, group_col: str, prob_cols: dict[str, str]
) -> pd.DataFrame:
    rows = []
    for key, g in test.groupby(group_col, observed=True):
        y_true = g[target].to_numpy().astype(int)
        row = {group_col: key, "target": target, "n": len(g), "prevalence": float(y_true.mean())}
        for label, col in prob_cols.items():
            y_prob = g[col].to_numpy()
            row[f"roc_auc_{label}"] = _safe_auc(y_true, y_prob)
            row[f"pr_auc_{label}"] = _safe_pr_auc(y_true, y_prob)
            row[f"brier_{label}"] = brier_score_loss(y_true, y_prob)
        rows.append(row)
    df = pd.DataFrame(rows)
    df["low_sample_warning"] = df.n < MIN_SAMPLE_WARNING
    return df


def run_lead_robustness(phase3_preds: dict[str, np.ndarray] | None = None) -> pd.DataFrame:
    all_rows = []
    for target in TARGET_COLS:
        test = _load_test_with_predictions(target)
        prob_cols = {"baseline": "y_prob_baseline", "phase2": "y_prob_phase2"}
        if phase3_preds is not None and target in phase3_preds:
            test["y_prob_phase3"] = phase3_preds[target]
            prob_cols["phase3"] = "y_prob_phase3"
        df = _metrics_by_group(test, target, "lead_day", prob_cols)
        all_rows.append(df)
    result = pd.concat(all_rows, ignore_index=True).sort_values(["target", "lead_day"])
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "lead_robustness.csv")
    result.to_csv(path, index=False)
    print(f"saved -> {path}")
    return result


def run_regional_robustness(phase3_preds: dict[str, np.ndarray] | None = None) -> pd.DataFrame:
    all_rows = []
    for target in TARGET_COLS:
        test = _load_test_with_predictions(target)
        prob_cols = {"baseline": "y_prob_baseline", "phase2": "y_prob_phase2"}
        if phase3_preds is not None and target in phase3_preds:
            test["y_prob_phase3"] = phase3_preds[target]
            prob_cols["phase3"] = "y_prob_phase3"
        df = _metrics_by_group(test, target, "region_v2", prob_cols)
        all_rows.append(df)
    result = pd.concat(all_rows, ignore_index=True).sort_values(
        ["target", "roc_auc_phase2"], ascending=[True, False]
    )
    path = os.path.join(OUT_DIR, "regional_robustness.csv")
    result.to_csv(path, index=False)
    print(f"saved -> {path}")
    return result


def main() -> None:
    print("=== lead robustness ===")
    lead_df = run_lead_robustness()
    print(lead_df.to_string(index=False))

    print("\n=== regional robustness ===")
    region_df = run_regional_robustness()
    print(region_df.head(10).to_string(index=False))
    print(f"\nregions with n < {MIN_SAMPLE_WARNING}: {int(region_df.low_sample_warning.sum())}")


if __name__ == "__main__":
    main()
