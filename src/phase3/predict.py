"""
Phase 3 - L: preliminary Forecast Reliability Engine - a clean, reusable
Python inference interface (NOT a web API - that's Phase 4's job, see
run_phase3.py's docstring for what's deliberately deferred).

Wraps the currently-best trained models (Phase 2's LightGBM, one per
target) plus the train-only historical lookups and calibration, so a
caller can go from a single forecast instance straight to a bust
probability and confidence score without re-deriving the whole pipeline.

Usage:
    from src.phase3.predict import ForecastReliabilityEngine
    engine = ForecastReliabilityEngine()
    result = engine.predict(
        init_time="2021-07-20", lead_day=5, latitude=22.5, longitude=81.0,
        fcst_precip_mm=45.2, fcst_temp_c=28.1, fcst_mslp_hpa=1003.4,
    )
    # result.rainfall_bust_probability, result.temperature_bust_probability,
    # result.rainfall_confidence, result.temperature_confidence, result.model_version
"""
from __future__ import annotations

import os
from dataclasses import dataclass

import lightgbm as lgb
import pandas as pd
from sklearn.isotonic import IsotonicRegression

from ..phase2.features import (
    FEATURE_COLS,
    OUT_DIR as PHASE2_OUT_DIR,
    TARGET_COLS,
    build_features,
    fit_historical_features,
)
from ..phase2.geography import OUTSIDE_DOMAIN_LABEL, build_region_map

MODEL_VERSION = "phase3-v1 (Phase 2 feature set; ensemble/atmosphere pilot not yet integrated into the served model - see outputs/phase3/model_summary.md)"


@dataclass
class ReliabilityResult:
    rainfall_bust_probability: float
    temperature_bust_probability: float
    rainfall_confidence: float
    temperature_confidence: float
    region: str
    model_version: str = MODEL_VERSION


class ForecastReliabilityEngine:
    def __init__(self) -> None:
        self._models: dict[str, lgb.Booster] = {}
        for target in TARGET_COLS:
            path = os.path.join(PHASE2_OUT_DIR, f"lightgbm_{target}.txt")
            self._models[target] = lgb.Booster(model_file=path)

        # Needs the raw abs_error_* columns to fit hist_mean_abs_error_* -
        # those aren't in the trimmed features_train.parquet, so rebuild
        # in-memory from Phase 2's own function (same train split, same fit).
        train, _ = build_features()
        self._hist_lookups = fit_historical_features(train)
        self._train_domain_mean_precip = float(train.fcst_precip_mm.mean())
        self._train_domain_mean_temp = float(train.fcst_temp_c.mean())
        self._region_categories = train["region_v2"].astype("category").cat.categories

        self._region_map = build_region_map()

        calib = pd.read_csv(os.path.join(PHASE2_OUT_DIR, "calibration_summary.csv")).set_index(
            "target"
        )
        val_preds = {
            t: pd.read_parquet(os.path.join(PHASE2_OUT_DIR, f"val_predictions_{t}.parquet"))
            for t in TARGET_COLS
        }
        self._calibrators: dict[str, IsotonicRegression | None] = {}
        for target in TARGET_COLS:
            if bool(calib.loc[target, "calibration_improved"]):
                iso = IsotonicRegression(out_of_bounds="clip")
                iso.fit(val_preds[target]["y_prob"], val_preds[target]["y_true"])
                self._calibrators[target] = iso
            else:
                self._calibrators[target] = None

    def _lookup_region(self, latitude: float, longitude: float) -> str:
        """Nearest grid point on the model's own 1.5-degree grid - matches
        how the training data itself is gridded."""
        d2 = (self._region_map.latitude - latitude) ** 2 + (
            self._region_map.longitude - longitude
        ) ** 2
        nearest = self._region_map.loc[d2.idxmin()]
        return nearest.region_v2

    def _apply_hist_features(self, row: dict, region: str, lead_day: int, month: int) -> dict:
        key = (region, lead_day, month)
        out = dict(row)
        for name, (lookup, fallback) in self._hist_lookups.items():
            out[name] = lookup.get(key, fallback)
        return out

    def predict(
        self,
        init_time: str,
        lead_day: int,
        latitude: float,
        longitude: float,
        fcst_precip_mm: float,
        fcst_temp_c: float,
        fcst_mslp_hpa: float,
        domain_mean_precip: float | None = None,
        domain_mean_temp: float | None = None,
        prev_run_fcst_precip: float | None = None,
        prev_run_fcst_temp: float | None = None,
    ) -> ReliabilityResult:
        """`domain_mean_*` and `prev_run_fcst_*` are optional - if the caller
        doesn't have the full domain snapshot or the previous day's forecast
        run handy, this falls back to the TRAIN-period average domain mean
        (for the anomaly feature) and to "no jump information" (0.0, for the
        forecast-jump feature) respectively. Both fallbacks are documented
        here, not silently assumed elsewhere."""
        init_ts = pd.Timestamp(init_time)
        month = int((init_ts + pd.Timedelta(days=int(lead_day))).month)
        region = self._lookup_region(latitude, longitude)
        if region == OUTSIDE_DOMAIN_LABEL:
            raise ValueError(
                f"({latitude}, {longitude}) is outside the model's India domain "
                "(ocean/distant foreign territory) - see outputs/phase2/region_assignment_summary.csv"
            )

        dm_precip = domain_mean_precip if domain_mean_precip is not None else self._train_domain_mean_precip
        dm_temp = domain_mean_temp if domain_mean_temp is not None else self._train_domain_mean_temp
        jump_precip = (
            fcst_precip_mm - prev_run_fcst_precip if prev_run_fcst_precip is not None else 0.0
        )
        jump_temp = fcst_temp_c - prev_run_fcst_temp if prev_run_fcst_temp is not None else 0.0

        row = {
            "fcst_precip_mm": fcst_precip_mm,
            "fcst_temp_c": fcst_temp_c,
            "fcst_mslp_hpa": fcst_mslp_hpa,
            "latitude": latitude,
            "longitude": longitude,
            "region_v2": region,
            "fcst_precip_anomaly_vs_domain_mean": fcst_precip_mm - dm_precip,
            "fcst_temp_anomaly_vs_domain_mean": fcst_temp_c - dm_temp,
            "lead_day": lead_day,
            "month": month,
            "precip_forecast_jump": jump_precip,
            "temp_forecast_jump": jump_temp,
        }
        row = self._apply_hist_features(row, region, lead_day, month)

        X = pd.DataFrame([row])
        X["region_v2"] = pd.Categorical([region], categories=self._region_categories)
        X = X[FEATURE_COLS]

        probs = {}
        for target in TARGET_COLS:
            raw = float(self._models[target].predict(X)[0])
            calibrator = self._calibrators[target]
            probs[target] = float(calibrator.predict([raw])[0]) if calibrator is not None else raw

        return ReliabilityResult(
            rainfall_bust_probability=probs["bust_precip_categorical"],
            temperature_bust_probability=probs["bust_temp_hard"],
            rainfall_confidence=1.0 - probs["bust_precip_categorical"],
            temperature_confidence=1.0 - probs["bust_temp_hard"],
            region=region,
        )


def _demo() -> None:
    engine = ForecastReliabilityEngine()
    result = engine.predict(
        init_time="2021-07-20",
        lead_day=5,
        latitude=22.5,
        longitude=81.0,
        fcst_precip_mm=45.2,
        fcst_temp_c=28.1,
        fcst_mslp_hpa=1003.4,
    )
    print(result)


if __name__ == "__main__":
    _demo()
