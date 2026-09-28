"""
Phase 3 - J: calibration analysis. Extends Phase 2's isotonic-only check
with Platt/sigmoid calibration (slope + intercept in logit space) and
Expected Calibration Error (ECE), all fit on the 2020 validation-year
predictions only (never 2021), evaluated on the 2021 holdout.

Usage:
    .venv/Scripts/python.exe -m src.phase3.calibration
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import brier_score_loss

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR
from ..phase2.features import TARGET_COLS

OUT_DIR = os.path.join("outputs", "phase3")
PLOT_DIR = os.path.join(OUT_DIR, "plots")
EPS = 1e-6


def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, EPS, 1 - EPS)
    return np.log(p / (1 - p))


def expected_calibration_error(y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10) -> float:
    bins = np.linspace(0, 1, n_bins + 1)
    bin_ids = np.digitize(y_prob, bins[1:-1])
    ece = 0.0
    n = len(y_true)
    for b in range(n_bins):
        mask = bin_ids == b
        if mask.sum() == 0:
            continue
        conf = y_prob[mask].mean()
        acc = y_true[mask].mean()
        ece += (mask.sum() / n) * abs(acc - conf)
    return float(ece)


def calibrate_target(target: str) -> dict:
    preds = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, f"predictions_{target}.parquet"))
    val_preds = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, f"val_predictions_{target}.parquet"))

    y_val, p_val = val_preds["y_true"].to_numpy(), val_preds["y_prob"].to_numpy()
    y_test, p_test_raw = preds["y_true"].to_numpy(), preds["y_prob"].to_numpy()

    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(p_val, y_val)
    p_test_iso = iso.predict(p_test_raw)

    platt = LogisticRegression()
    platt.fit(_logit(p_val).reshape(-1, 1), y_val)
    p_test_platt = platt.predict_proba(_logit(p_test_raw).reshape(-1, 1))[:, 1]
    slope = float(platt.coef_[0][0])
    intercept = float(platt.intercept_[0])

    results = {
        "target": target,
        "brier_raw": brier_score_loss(y_test, p_test_raw),
        "brier_isotonic": brier_score_loss(y_test, p_test_iso),
        "brier_platt": brier_score_loss(y_test, p_test_platt),
        "ece_raw": expected_calibration_error(y_test, p_test_raw),
        "ece_isotonic": expected_calibration_error(y_test, p_test_iso),
        "ece_platt": expected_calibration_error(y_test, p_test_platt),
        "platt_slope": slope,
        "platt_intercept": intercept,
        "platt_slope_interpretation": (
            "slope=1, intercept=0 would mean the raw probability is already "
            "perfectly calibrated in logit space; slope<1 means raw "
            "probabilities are overconfident (too spread out), slope>1 means "
            "underconfident"
        ),
        "calibration_fit_on": "2020 validation predictions (probe model, never trained on 2020)",
    }

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.plot([0, 1], [0, 1], "k--", label="perfectly calibrated")
    for label, p in [("raw", p_test_raw), ("isotonic", p_test_iso), ("platt", p_test_platt)]:
        frac_pos, mean_pred = calibration_curve(y_test, p, n_bins=10, strategy="quantile")
        ax.plot(mean_pred, frac_pos, marker="o", label=label)
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed rate")
    ax.set_title(f"Calibration - {target} (2021 holdout)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, f"calibration_{target}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    results["plot"] = path
    return results


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    rows = [calibrate_target(t) for t in TARGET_COLS]
    df = pd.DataFrame(rows)
    path = os.path.join(OUT_DIR, "calibration_results.csv")
    df.to_csv(path, index=False)
    print(f"saved -> {path}")
    print(df[["target", "brier_raw", "brier_isotonic", "brier_platt",
              "ece_raw", "ece_isotonic", "ece_platt", "platt_slope", "platt_intercept"]].to_string(index=False))


if __name__ == "__main__":
    main()
