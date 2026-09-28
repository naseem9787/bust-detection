"""
Phase 3 - D deliverable: feature_registry.csv - one row per feature (Phase 2
features + new Phase 3 atmospheric/ensemble features), with source, units,
transformation, forecast-time availability, leakage status, and intended
physical interpretation.

Usage:
    .venv/Scripts/python.exe -m src.phase3.feature_registry
"""
from __future__ import annotations

import os

import pandas as pd

OUT_DIR = os.path.join("outputs", "phase3")

REGISTRY = [
    # --- Phase 2 features (unchanged) ---
    ("fcst_precip_mm", "HRES forecast", "mm", "m -> mm (x1000)", True, "OK", "how much rain the model expects"),
    ("fcst_temp_c", "HRES forecast", "degC", "K -> degC (-273.15)", True, "OK", "how hot/cold the model expects"),
    ("fcst_mslp_hpa", "HRES forecast", "hPa", "Pa -> hPa (/100)", True, "OK", "large-scale pressure pattern"),
    ("latitude", "grid coordinate", "degrees", "none", True, "OK", "static location"),
    ("longitude", "grid coordinate", "degrees", "none", True, "OK", "static location"),
    ("region_v2", "src/phase2/geography.py (static state boundaries)", "categorical", "point-in-polygon", True, "OK", "administrative/climatological region"),
    ("fcst_precip_anomaly_vs_domain_mean", "derived from fcst_precip_mm", "mm", "value - domain mean at same (init,lead)", True, "OK", "how unusual this cell's rain forecast is vs. the broader pattern that day"),
    ("fcst_temp_anomaly_vs_domain_mean", "derived from fcst_temp_c", "degC", "value - domain mean", True, "OK", "how unusual this cell's temp forecast is vs. the broader pattern"),
    ("lead_day", "forecast metadata", "days", "none", True, "OK", "how far ahead this forecast is"),
    ("month", "forecast metadata (valid_time)", "1-12", "none", True, "OK", "seasonality"),
    ("precip_forecast_jump", "derived: this run's fcst_precip_mm minus the run issued 24h earlier for the same valid_time", "mm", "subtraction", True, "OK", "did the model change its mind about rain since yesterday's run"),
    ("temp_forecast_jump", "derived, same as above for temperature", "degC", "subtraction", True, "OK", "did the model change its mind about temperature"),
    ("hist_bust_precip_categorical_rate", "train-only-fit climatology (region x lead x month)", "probability", "groupby mean, fit on train only", True, "OK - CONDITIONAL (train-only)", "how often this bucket has historically busted on rainfall category"),
    ("hist_bust_temp_hard_rate", "train-only-fit climatology", "probability", "groupby mean, fit on train only", True, "OK - CONDITIONAL (train-only)", "how often this bucket has historically busted on temperature"),
    ("hist_mean_abs_error_precip_mm", "train-only-fit climatology", "mm", "groupby mean, fit on train only", True, "OK - CONDITIONAL (train-only)", "typical rainfall forecast error for this bucket"),
    ("hist_mean_abs_error_temp_c", "train-only-fit climatology", "degC", "groupby mean, fit on train only", True, "OK - CONDITIONAL (train-only)", "typical temperature forecast error for this bucket"),
    # --- Phase 3 new: atmospheric (full JJAS 2018-2021 scale) ---
    ("wind_speed_10m", "HRES forecast (new, Phase 3)", "m/s", "none", True, "OK", "surface wind strength - relevant to cyclones, squalls, convective systems"),
    ("humidity_850hpa", "HRES forecast (new, Phase 3)", "g/kg", "kg/kg -> g/kg (x1000)", True, "OK", "low-level monsoon moisture availability"),
    ("geopotential_500hpa", "HRES forecast (new, Phase 3)", "m (geopotential height)", "m2/s2 / 9.80665", True, "OK", "synoptic-scale trough/ridge pattern"),
    # --- Phase 3 new: ensemble (PILOT WINDOW ONLY - 2021-07-15..2021-08-04) ---
    ("ensemble_mean_precip", "IFS ensemble, 50 members (PILOT WINDOW ONLY)", "mm", "mean over members, m -> mm", True, "OK - PILOT SCOPE ONLY", "ensemble-average rainfall forecast"),
    ("ensemble_std_precip", "IFS ensemble (PILOT WINDOW ONLY)", "mm", "std over members", True, "OK - PILOT SCOPE ONLY", "rainfall forecast uncertainty at this exact cell/lead"),
    ("ensemble_min_precip", "IFS ensemble (PILOT WINDOW ONLY)", "mm", "min over members", True, "OK - PILOT SCOPE ONLY", "most optimistic (driest) member"),
    ("ensemble_max_precip", "IFS ensemble (PILOT WINDOW ONLY)", "mm", "max over members", True, "OK - PILOT SCOPE ONLY", "most pessimistic (wettest) member"),
    ("ensemble_iqr_precip", "IFS ensemble (PILOT WINDOW ONLY)", "mm", "p75 - p25 over members", True, "OK - PILOT SCOPE ONLY", "robust spread, less sensitive to outlier members than std"),
    ("ensemble_cv_precip", "IFS ensemble (PILOT WINDOW ONLY)", "unitless ratio", "std / mean (precip only - has a meaningful zero)", True, "OK - PILOT SCOPE ONLY", "relative (not absolute) uncertainty - useful since rain amounts vary over orders of magnitude"),
    ("ensemble_mean_temp", "IFS ensemble (PILOT WINDOW ONLY)", "degC", "mean over members, K -> degC", True, "OK - PILOT SCOPE ONLY", "ensemble-average temperature forecast"),
    ("ensemble_std_temp", "IFS ensemble (PILOT WINDOW ONLY)", "degC", "std over members", True, "OK - PILOT SCOPE ONLY", "temperature forecast uncertainty"),
    ("ensemble_min_temp", "IFS ensemble (PILOT WINDOW ONLY)", "degC", "min over members", True, "OK - PILOT SCOPE ONLY", "coolest member"),
    ("ensemble_max_temp", "IFS ensemble (PILOT WINDOW ONLY)", "degC", "max over members", True, "OK - PILOT SCOPE ONLY", "warmest member"),
    ("ensemble_iqr_temp", "IFS ensemble (PILOT WINDOW ONLY)", "degC", "p75 - p25 over members", True, "OK - PILOT SCOPE ONLY", "robust temperature spread"),
    ("domain_mean_ensemble_std_precip", "derived from ensemble_std_precip", "mm", "domain-mean at same (init,lead)", True, "OK - PILOT SCOPE ONLY", "spatially-aggregated uncertainty - is the WHOLE region uncertain today, not just this cell"),
    ("domain_mean_ensemble_std_temp", "derived from ensemble_std_temp", "degC", "domain-mean at same (init,lead)", True, "OK - PILOT SCOPE ONLY", "spatially-aggregated temperature uncertainty"),
    # --- explicitly rejected / unavailable, for completeness of the registry ---
    ("obs_precip_mm / obs_temp_c / obs_mslp_hpa", "ERA5 truth", "mm / degC / hPa", "n/a", False, "REJECTED", "the verification target, not an input"),
    ("bust_any / bust_precip_categorical / bust_temp_hard", "computed from forecast AND truth", "boolean", "n/a", False, "REJECTED", "the label itself"),
    ("spread_relative_to_historical_spread", "would need historical (train-period) ensemble data", "ratio", "not computed", False, "NOT COMPUTED - no historical basis", "the pilot window IS the test year, so there is no train-period ensemble sample to compare against - documented gap, not fabricated"),
]

COLUMNS = [
    "feature", "source", "units", "transformation",
    "available_at_forecast_time", "leakage_status", "physical_interpretation",
]


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.DataFrame(REGISTRY, columns=COLUMNS)
    path = os.path.join(OUT_DIR, "feature_registry.csv")
    df.to_csv(path, index=False)
    print(f"saved {len(df)} rows -> {path}")
    print(df.leakage_status.value_counts().to_string())


if __name__ == "__main__":
    main()
