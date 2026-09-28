"""
Phase 1 - chronological evaluation: train on 2018-2020 JJAS, test on the
completely unseen 2021 JJAS season. No random splitting anywhere.

Computes, per baseline, on the held-out 2021 test set:
  ROC-AUC, PR-AUC (average precision), Brier score, Brier Skill Score
  (relative to a constant train-period-base-rate reference forecast),
  precision, recall, F1, false-alarm rate (FPR), miss rate (FNR), at an
  operating threshold documented below - plus a reliability diagram.

Threshold choice
-----------------
Historical-frequency baselines rarely cross 0.5 (the train bust rate is
~27%), so thresholding at 0.5 would call almost nothing a bust. Instead the
operating threshold is set to the TRAIN-period overall bust rate itself, so
each baseline's predicted-positive rate is calibrated to roughly match the
observed rate rather than using an arbitrary cutoff. This threshold is
recorded in outputs/phase1/experiment_manifest.json for reproducibility.

Usage:
    .venv/Scripts/python.exe -m src.phase1.evaluate
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from . import baselines as bl
from .dataset import TEST_YEAR, TRAIN_YEARS, build_phase1_dataset

OUT_DIR = os.path.join("outputs", "phase1")
PLOT_DIR = os.path.join(OUT_DIR, "plots")


def _brier_skill_score(y_true: np.ndarray, y_prob: np.ndarray, reference_prob: float) -> float:
    bs_model = brier_score_loss(y_true, y_prob)
    bs_ref = brier_score_loss(y_true, np.full_like(y_prob, reference_prob, dtype=float))
    if bs_ref == 0:
        return float("nan")
    return 1.0 - bs_model / bs_ref


def score_baseline(
    name: str, y_true: np.ndarray, y_prob: np.ndarray, threshold: float, reference_prob: float
) -> dict:
    y_pred = (y_prob >= threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred, labels=[0, 1]).ravel()
    far = fp / (fp + tn) if (fp + tn) > 0 else float("nan")  # false alarm rate = FPR
    miss_rate = fn / (fn + tp) if (fn + tp) > 0 else float("nan")  # = 1 - recall
    return {
        "method": name,
        "n_test": int(len(y_true)),
        "test_bust_rate": float(np.mean(y_true)),
        "roc_auc": roc_auc_score(y_true, y_prob),
        "pr_auc": average_precision_score(y_true, y_prob),
        "brier_score": brier_score_loss(y_true, y_prob),
        "brier_skill_score": _brier_skill_score(y_true, y_prob, reference_prob),
        "precision": precision_score(y_true, y_pred, zero_division=0),
        "recall": recall_score(y_true, y_pred, zero_division=0),
        "f1": f1_score(y_true, y_pred, zero_division=0),
        "false_alarm_rate": far,
        "miss_rate": miss_rate,
        "operating_threshold": threshold,
    }


def plot_reliability(results: dict[str, tuple[np.ndarray, np.ndarray]]) -> str:
    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([0, 1], [0, 1], "k--", label="perfectly calibrated")
    for name, (y_true, y_prob) in results.items():
        frac_pos, mean_pred = calibration_curve(y_true, y_prob, n_bins=10, strategy="quantile")
        ax.plot(mean_pred, frac_pos, marker="o", label=name)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed bust frequency")
    ax.set_title("Reliability diagram - 2021 JJAS holdout")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "reliability_diagram.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    ds = build_phase1_dataset()
    df = ds.df
    train = df[df.split == "train"]
    test = df[df.split == "test"]

    print(f"train years {TRAIN_YEARS}: {len(train):,} rows")
    print(f"test year {TEST_YEAR}: {len(test):,} rows")

    fitted = bl.fit_all_baselines(train)
    reference_prob = bl.fit_global_reference(train)
    threshold = reference_prob  # see module docstring

    y_true = test.bust_any.to_numpy().astype(int)
    rows = []
    reliability_inputs = {}
    for key, baseline in fitted.items():
        y_prob = bl.predict(baseline, test)
        rows.append(score_baseline(baseline.name, y_true, y_prob, threshold, reference_prob))
        reliability_inputs[baseline.name] = (y_true, y_prob)

    # Baseline C - documented as unavailable, not fabricated.
    rows.append(
        {
            "method": "Ensemble spread baseline",
            "n_test": None,
            "test_bust_rate": None,
            "roc_auc": None,
            "pr_auc": None,
            "brier_score": None,
            "brier_skill_score": None,
            "precision": None,
            "recall": None,
            "f1": None,
            "false_alarm_rate": None,
            "miss_rate": None,
            "operating_threshold": None,
            "status": bl.BASELINE_C_STATUS,
        }
    )

    comparison = pd.DataFrame(rows)
    numeric_cols = [
        "roc_auc", "pr_auc", "brier_score", "brier_skill_score",
        "precision", "recall", "f1", "false_alarm_rate", "miss_rate",
    ]
    comparison[numeric_cols] = comparison[numeric_cols].astype(float).round(4)
    out_path = os.path.join(OUT_DIR, "baseline_comparison.csv")
    comparison.to_csv(out_path, index=False)
    print(f"\nsaved -> {out_path}")
    print(comparison[["method"] + numeric_cols].to_string(index=False))

    reliability_path = plot_reliability(reliability_inputs)
    print(f"saved -> {reliability_path}")

    with open(os.path.join(OUT_DIR, "evaluation_config.json"), "w") as f:
        json.dump(
            {
                "train_years": TRAIN_YEARS,
                "test_year": TEST_YEAR,
                "operating_threshold": threshold,
                "operating_threshold_definition": (
                    "train-period overall bust_any rate (calibrated cutoff, "
                    "not an arbitrary 0.5 - see evaluate.py module docstring)"
                ),
                "brier_skill_score_reference": (
                    "constant forecast = train-period overall bust_any rate"
                ),
                "false_alarm_rate_definition": "FP / (FP + TN)  [false positive rate]",
                "miss_rate_definition": "FN / (FN + TP)  [= 1 - recall]",
            },
            f,
            indent=2,
        )


if __name__ == "__main__":
    main()
