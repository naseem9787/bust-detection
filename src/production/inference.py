"""
Phase 4 - production inference engine.

    forecast input -> feature construction -> feature validation
    -> model inference -> probability calibration -> output schema

Models and calibrators are loaded ONCE at construction (see Performance
notes in docs/production_inference.md) - a fresh Python process calling
`ProductionInferenceEngine()` is the only setup step needed; nothing here
depends on notebook state or a running training script.
"""
from __future__ import annotations

import os
import pickle

import lightgbm as lgb
import pandas as pd

from . import features as feat
from . import registry
from .thresholds import DEFAULT_THRESHOLDS, risk_level

MODEL_VERSION_TAG = "phase4-production-v1"
FEATURE_VERSION_TAG = "phase2-feature-schema-v1"


class ProductionInferenceEngine:
    def __init__(self) -> None:
        self.entries = registry.all_entries()
        self._boosters: dict[str, lgb.Booster] = {}
        self._calibrators: dict[str, object] = {}
        for key, entry in self.entries.items():
            self._boosters[key] = lgb.Booster(model_file=entry.model_artifact_path)
            if entry.calibration_artifact_path:
                with open(entry.calibration_artifact_path, "rb") as f:
                    self._calibrators[key] = pickle.load(f)
            else:
                self._calibrators[key] = None

    def _predict_one(self, model_key: str, feature_row: dict) -> tuple[float, float]:
        entry = self.entries[model_key]
        feat.validate_feature_row(feature_row, entry.feature_order)
        X = pd.DataFrame([feature_row])[entry.feature_order]
        X["region_v2"] = X["region_v2"].astype(feat.region_categories())
        raw = float(self._boosters[model_key].predict(X)[0])
        calibrator = self._calibrators[model_key]
        calibrated = float(calibrator.predict([raw])[0]) if calibrator is not None else raw
        calibrated = min(max(calibrated, 0.0), 1.0)
        return raw, calibrated

    def predict(
        self,
        init_time: str | pd.Timestamp,
        lead_day: int,
        latitude: float,
        longitude: float,
        forecast_precip_mm: float,
        forecast_temp_c: float,
        forecast_mslp_hpa: float,
        forecast_wind_speed_10m: float | None = None,
        domain_mean_precip_mm: float | None = None,
        domain_mean_temp_c: float | None = None,
        previous_run_forecast_precip_mm: float | None = None,
        previous_run_forecast_temp_c: float | None = None,
    ) -> dict:
        init_ts = pd.Timestamp(init_time)
        built = feat.build_feature_row(
            init_time=init_ts,
            lead_day=lead_day,
            latitude=latitude,
            longitude=longitude,
            forecast_precip_mm=forecast_precip_mm,
            forecast_temp_c=forecast_temp_c,
            forecast_mslp_hpa=forecast_mslp_hpa,
            forecast_wind_speed_10m=forecast_wind_speed_10m,
            domain_mean_precip_mm=domain_mean_precip_mm,
            domain_mean_temp_c=domain_mean_temp_c,
            previous_run_forecast_precip_mm=previous_run_forecast_precip_mm,
            previous_run_forecast_temp_c=previous_run_forecast_temp_c,
        )
        row = built["features"]

        rain_raw, rain_cal = self._predict_one("rain_v1", row)
        rain_result = {
            "raw": rain_raw,
            "calibrated": rain_cal,
            "confidence": 1.0 - rain_cal,
            "risk_level": risk_level(rain_cal),
        }

        temp_result = None
        if forecast_wind_speed_10m is not None:
            temp_raw, temp_cal = self._predict_one("temperature_v1", row)
            temp_result = {
                "raw": temp_raw,
                "calibrated": temp_cal,
                "confidence": 1.0 - temp_cal,
                "risk_level": risk_level(temp_cal),
            }

        return {
            "init_time": init_ts,
            "lead_day": lead_day,
            "valid_time": built["valid_time"],
            "latitude": latitude,
            "longitude": longitude,
            "region": built["region"],
            "in_india_domain": built["in_india_domain"],
            "forecast_precip_mm": forecast_precip_mm,
            "forecast_temp_c": forecast_temp_c,
            "rain_bust_probability": rain_result,
            "temperature_bust_probability": temp_result,
            "model_version": MODEL_VERSION_TAG,
            "feature_version": FEATURE_VERSION_TAG,
            "calibration_version": (
                f"rain={self.entries['rain_v1'].calibration_method};"
                f"temp={self.entries['temperature_v1'].calibration_method}"
            ),
        }

    def feature_row_for_explanation(self, **kwargs) -> tuple[dict, str]:
        """Returns (feature_row, region) - used by explain.py so it doesn't
        duplicate the feature-building call."""
        if "init_time" in kwargs:
            kwargs["init_time"] = pd.Timestamp(kwargs["init_time"])
        built = feat.build_feature_row(**kwargs)
        return built["features"], built["region"]
