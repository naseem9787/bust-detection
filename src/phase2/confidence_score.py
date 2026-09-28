"""
Phase 2 - Part C: first version of a forecast-confidence score.

    bust probability -> (calibrated, if calibration actually improved Brier
                          score on the 2021 holdout; else raw) -> confidence = 1 - P(bust)

Deliberately simple - no invented composite score. The raw probability is
always kept alongside the confidence value.

Usage:
    .venv/Scripts/python.exe -m src.phase2.confidence_score
"""
from __future__ import annotations

import os

import pandas as pd
from sklearn.isotonic import IsotonicRegression

from .features import OUT_DIR, TARGET_COLS


def main() -> None:
    calibration = pd.read_csv(os.path.join(OUT_DIR, "calibration_summary.csv")).set_index("target")

    for target in TARGET_COLS:
        preds = pd.read_parquet(os.path.join(OUT_DIR, f"predictions_{target}.parquet"))
        val_preds = pd.read_parquet(os.path.join(OUT_DIR, f"val_predictions_{target}.parquet"))

        use_calibrated = bool(calibration.loc[target, "calibration_improved"])
        if use_calibrated:
            iso = IsotonicRegression(out_of_bounds="clip")
            iso.fit(val_preds["y_prob"], val_preds["y_true"])
            y_prob_used = iso.predict(preds["y_prob"])
            source = "isotonic-calibrated (fit on 2020 validation predictions)"
        else:
            y_prob_used = preds["y_prob"].to_numpy()
            source = "raw (calibration did not improve Brier score on 2020 - see calibration_summary.csv)"

        out = pd.DataFrame(
            {
                "y_true": preds["y_true"],
                "y_prob_raw": preds["y_prob"],
                "y_prob_used": y_prob_used,
                "confidence": 1.0 - y_prob_used,
                "calibration_source": source,
            }
        )
        path = os.path.join(OUT_DIR, f"confidence_scores_{target}.parquet")
        out.to_parquet(path, index=False)
        print(f"saved -> {path} (source: {source})")
        print(
            f"  confidence stats: mean={out.confidence.mean():.3f} "
            f"min={out.confidence.min():.3f} max={out.confidence.max():.3f}"
        )


if __name__ == "__main__":
    main()
