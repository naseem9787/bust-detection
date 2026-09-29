"""
Phase 5 - Stage 2: the analog feature vector definition.

Candidates considered (per the audited, available forecast-state columns):
fcst_precip_mm, fcst_temp_c, fcst_mslp_hpa, wind_speed_10m,
precip_forecast_jump, temp_forecast_jump, lead_day, latitude, longitude,
month, region_v2.

Excluded, and why:
  - `hist_bust_*_rate` / `hist_mean_abs_error_*` (Phase 2/4 historical
    features): these ARE available at forecast issuance, but they are
    climatological PRIORS for a (region, lead_day, month) bucket, not
    forecast-STATE descriptors - including them would make analogs
    trivially cluster by region/lead/month, double-counting what the
    explicit spatial/temporal constraints (Stages 5-6) already do more
    transparently. The task asks for "forecast state similarity", not
    "similar historical bucket".
  - `fcst_*_anomaly_vs_domain_mean`: correlates at 0.995 (precip) / 0.949
    (temp) with the raw forecast value itself (see
    outputs/phase3/feature_correlation_matrix.csv) - redundant, and the
    raw value is the more directly interpretable "similar forecast"
    quantity for a human-facing analog case.
  - `region_v2`: used as a hard SPATIAL CONSTRAINT (Stage 5 experiment),
    not as a distance-vector dimension - a categorical variable doesn't
    belong in a Euclidean feature space, and folding it in as one-hot
    would silently give it a different implicit weight than the
    continuous features.
  - `month`: tested as a hard TEMPORAL CONSTRAINT (Stage 6 experiment)
    rather than baked into the vector by default - see
    outputs/phase5/temporal_constraint_comparison.csv for why.

Retained set (9 features) - checked pairwise, max |r|=0.73 (fcst_temp_c vs
fcst_mslp_hpa - a real physical relationship, not redundant duplicate
information; see outputs/phase5/analog_feature_correlation.csv):
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

OUT_DIR = os.path.join("outputs", "phase5")

ANALOG_FEATURE_COLS = [
    "fcst_precip_mm", "fcst_temp_c", "fcst_mslp_hpa", "wind_speed_10m",
    "precip_forecast_jump", "temp_forecast_jump",
    "lead_day", "latitude", "longitude",
]


class AnalogScaler:
    """z-score standardization, fit on a reference (TRAIN-period) sample
    only - never on data that includes the query point(s) being evaluated
    at retrospective-evaluation time, matching every other train-only-fit
    artifact in this project (see docs/historical_analogs.md Leakage
    section)."""

    def __init__(self) -> None:
        self.mean_: pd.Series | None = None
        self.std_: pd.Series | None = None

    def fit(self, df: pd.DataFrame) -> "AnalogScaler":
        self.mean_ = df[ANALOG_FEATURE_COLS].mean()
        self.std_ = df[ANALOG_FEATURE_COLS].std().replace(0, 1.0)
        return self

    def transform(self, df: pd.DataFrame) -> np.ndarray:
        if self.mean_ is None:
            raise RuntimeError("AnalogScaler not fit yet")
        z = (df[ANALOG_FEATURE_COLS] - self.mean_) / self.std_
        return z.to_numpy(dtype=np.float32)

    def to_dict(self) -> dict:
        return {"mean": self.mean_.to_dict(), "std": self.std_.to_dict()}

    @classmethod
    def from_dict(cls, d: dict) -> "AnalogScaler":
        scaler = cls()
        scaler.mean_ = pd.Series(d["mean"])
        scaler.std_ = pd.Series(d["std"])
        return scaler


def check_feature_correlations(df: pd.DataFrame) -> pd.DataFrame:
    corr = df[ANALOG_FEATURE_COLS].corr()
    path = os.path.join(OUT_DIR, "analog_feature_correlation.csv")
    os.makedirs(OUT_DIR, exist_ok=True)
    corr.to_csv(path)
    print(f"saved -> {path}")
    max_abs_offdiag = corr.where(~np.eye(len(corr), dtype=bool)).abs().max().max()
    print(f"max |off-diagonal correlation| among analog features: {max_abs_offdiag:.3f}")
    return corr


if __name__ == "__main__":
    df = pd.read_parquet(os.path.join(OUT_DIR, "analog_reference_dataset.parquet"))
    check_feature_correlations(df)
