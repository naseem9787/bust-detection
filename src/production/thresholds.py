"""
Phase 4 - configurable operational risk thresholds.

These are NOT scientifically "optimal" cutoffs - Phase 3 never validated an
optimal decision threshold (its precision/recall/F1 numbers used the
train-period base rate as an operating point purely for reporting, see
src/phase2/evaluate.py's docstring). These are round, documented, externally
configurable operational choices, exposed via /metadata so the frontend
never has to guess or hard-code them.

Override via environment variables (e.g. for a different deployment/
operational policy) - see docs/production_inference.md.
"""
from __future__ import annotations

import os

DEFAULT_THRESHOLDS = {
    "low": 0.0,
    "moderate": float(os.environ.get("BUST_THRESHOLD_MODERATE", 0.25)),
    "high": float(os.environ.get("BUST_THRESHOLD_HIGH", 0.50)),
}

THRESHOLD_BASIS = (
    "Round operational cutoffs (0.25 / 0.50), NOT a value derived from ROC/PR "
    "optimization - Phase 3 did not establish a statistically 'optimal' "
    "decision threshold for this system. Configurable via the "
    "BUST_THRESHOLD_MODERATE / BUST_THRESHOLD_HIGH environment variables."
)


def risk_level(calibrated_probability: float, thresholds: dict = DEFAULT_THRESHOLDS) -> str:
    if calibrated_probability >= thresholds["high"]:
        return "high"
    if calibrated_probability >= thresholds["moderate"]:
        return "moderate"
    return "low"
