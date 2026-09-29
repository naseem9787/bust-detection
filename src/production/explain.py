"""
Phase 4 - explainability. Real SHAP attribution from the actual trained
LightGBM models (TreeExplainer - exact and fast for tree models, no
sampling needed even on-demand per request), plus a deterministic
human-readable layer built ONLY from those same attributions - never an
LLM, never an invented meteorological cause not present in the features.

SHAP is computed on-demand for a single requested prediction (cheap - a few
ms per row with TreeExplainer), not batch-computed for every grid cell -
see docs/production_inference.md's Explainability section for why.
"""
from __future__ import annotations

from functools import lru_cache

import pandas as pd
import shap

from . import features as feat
from . import registry

TOP_N_FEATURES = 5

# feature -> (human-readable subject, template for "high" and "low" values)
FEATURE_TEMPLATES = {
    "fcst_precip_mm": "the forecast rainfall amount",
    "fcst_temp_c": "the forecast temperature",
    "fcst_mslp_hpa": "the forecast sea-level pressure pattern",
    "precip_forecast_jump": "how much the rainfall forecast changed from the previous run",
    "temp_forecast_jump": "how much the temperature forecast changed from the previous run",
    "hist_bust_precip_categorical_rate": "this region/lead/month's historical rainfall-bust rate",
    "hist_bust_temp_hard_rate": "this region/lead/month's historical temperature-bust rate",
    "hist_mean_abs_error_precip_mm": "this region/lead/month's typical rainfall forecast error",
    "hist_mean_abs_error_temp_c": "this region/lead/month's typical temperature forecast error",
    "fcst_precip_anomaly_vs_domain_mean": "how unusual the rainfall forecast is versus the broader pattern",
    "fcst_temp_anomaly_vs_domain_mean": "how unusual the temperature forecast is versus the broader pattern",
    "wind_speed_10m": "the forecast surface wind speed",
    "region_v2": "the region's typical behaviour",
    "lead_day": "how far ahead this forecast is",
    "month": "the time of year",
    "latitude": "the location (latitude)",
    "longitude": "the location (longitude)",
}


@lru_cache(maxsize=2)
def _get_explainer(model_key: str) -> shap.TreeExplainer:
    import lightgbm as lgb

    entry = registry.load_entry(model_key)
    booster = lgb.Booster(model_file=entry.model_artifact_path)
    return shap.TreeExplainer(booster)


def explain(model_key: str, feature_row: dict) -> dict:
    entry = registry.load_entry(model_key)
    X = pd.DataFrame([feature_row])[entry.feature_order]
    X["region_v2"] = X["region_v2"].astype(feat.region_categories())

    explainer = _get_explainer(model_key)
    shap_values = explainer.shap_values(X)
    if isinstance(shap_values, list):  # some SHAP/LightGBM version combos return [class0, class1]
        shap_values = shap_values[1]
    contributions = shap_values[0]
    base_value = float(
        explainer.expected_value[1] if isinstance(explainer.expected_value, (list, tuple))
        else explainer.expected_value
    )

    ranked = sorted(
        zip(entry.feature_order, contributions, [feature_row[c] for c in entry.feature_order]),
        key=lambda t: abs(t[1]),
        reverse=True,
    )[:TOP_N_FEATURES]

    top_features = [
        {
            "feature": name,
            "value": float(value) if not isinstance(value, str) else value,
            "contribution": float(contrib),
            "direction": "increases_bust_probability" if contrib > 0 else "decreases_bust_probability",
        }
        for name, contrib, value in ranked
    ]

    reasons = [_human_readable_reason(f) for f in top_features if f["feature"] in FEATURE_TEMPLATES]

    from lightgbm import Booster

    booster = Booster(model_file=entry.model_artifact_path)
    raw_probability = float(booster.predict(X)[0])

    return {
        "base_value": base_value,
        "raw_probability": raw_probability,
        "top_features": top_features,
        "human_readable_reasons": reasons,
    }


def _human_readable_reason(feature: dict) -> str:
    subject = FEATURE_TEMPLATES.get(feature["feature"], feature["feature"])
    verb = "increases" if feature["direction"] == "increases_bust_probability" else "decreases"
    magnitude = "strongly" if abs(feature["contribution"]) > 0.05 else "somewhat"
    return f"{subject.capitalize()} {magnitude} {verb} the predicted bust probability."
