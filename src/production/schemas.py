"""
Phase 4 - Pydantic request/response schemas for the production API. See
docs/api_contract.md for the frontend-facing documentation of these same
shapes with worked examples.
"""
from __future__ import annotations

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

LEAD_DAY_MIN, LEAD_DAY_MAX = 1, 10
LAT_MIN, LAT_MAX = -90.0, 90.0
LON_MIN, LON_MAX = -180.0, 360.0  # store convention is 0-360; both accepted, see features.py


class Variable(str, Enum):
    rain = "rain"
    temperature = "temperature"


class RiskLevel(str, Enum):
    low = "low"
    moderate = "moderate"
    high = "high"


# --------------------------------------------------------------------------
# /predict
# --------------------------------------------------------------------------
class PredictionRequest(BaseModel):
    init_time: datetime = Field(..., description="Forecast issuance time (ISO 8601)")
    lead_day: int = Field(..., ge=LEAD_DAY_MIN, le=LEAD_DAY_MAX)
    latitude: float = Field(..., ge=LAT_MIN, le=LAT_MAX)
    longitude: float = Field(..., ge=LON_MIN, le=LON_MAX)
    forecast_precip_mm: float = Field(..., ge=0, description="HRES forecast 24h precipitation, mm")
    forecast_temp_c: float = Field(..., description="HRES forecast 2m temperature, degC")
    forecast_mslp_hpa: float = Field(..., description="HRES forecast mean sea level pressure, hPa")
    forecast_wind_speed_10m: float | None = Field(
        None, ge=0, description="HRES forecast 10m wind speed, m/s - required for the "
        "temperature model; if omitted, the temperature prediction is skipped "
        "and rain_bust_probability alone is returned (see api_contract.md)"
    )
    domain_mean_precip_mm: float | None = Field(
        None, description="Optional: mean forecast precip across the full domain at this "
        "init_time/lead_day. Falls back to the training-period average if omitted."
    )
    domain_mean_temp_c: float | None = Field(None, description="Optional, same fallback as above")
    previous_run_forecast_precip_mm: float | None = Field(
        None, description="Optional: the forecast issued 24h earlier for the same valid_time/"
        "location, for the run-to-run jump feature. Falls back to 0 (no jump signal) if omitted."
    )
    previous_run_forecast_temp_c: float | None = Field(None, description="Optional, same as above")

    @field_validator("longitude")
    @classmethod
    def _normalize_longitude(cls, v: float) -> float:
        return v + 360.0 if v < 0 else v


class BustProbability(BaseModel):
    raw: float = Field(..., ge=0, le=1)
    calibrated: float = Field(..., ge=0, le=1)
    confidence: float = Field(
        ..., ge=0, le=1,
        description="Operational reliability score = 1 - calibrated probability. "
        "NOT a formal statistical confidence interval - see docs/production_inference.md.",
    )
    risk_level: RiskLevel


class GridPrediction(BaseModel):
    init_time: datetime
    lead_day: int
    valid_time: datetime
    latitude: float
    longitude: float
    region: str
    in_india_domain: bool

    forecast_precip_mm: float
    forecast_temp_c: float

    rain_bust_probability: BustProbability
    temperature_bust_probability: BustProbability | None = Field(
        None, description="null if forecast_wind_speed_10m was not supplied"
    )

    model_version: str
    feature_version: str
    calibration_version: str


class PredictionResponse(BaseModel):
    prediction: GridPrediction


# --------------------------------------------------------------------------
# /regions, region aggregation
# --------------------------------------------------------------------------
class RegionInfo(BaseModel):
    region: str
    n_grid_points: int
    known_limitation: str | None = None


class RegionPrediction(BaseModel):
    region: str
    lead_day: int
    valid_time: datetime
    variable: Variable
    n_grid_cells: int
    region_max_probability: float
    region_mean_probability: float
    region_high_risk_fraction: float = Field(
        ..., description="fraction of this region's grid cells with calibrated "
        "probability >= the configured high-risk threshold"
    )
    high_risk_threshold_used: float
    representative_forecast_value: float
    representative_confidence: float


# --------------------------------------------------------------------------
# /metadata
# --------------------------------------------------------------------------
class ModelMetadata(BaseModel):
    model_name: str
    model_version: str
    status: str
    target_variable: str
    target_definition: str
    n_features: int
    calibration_method: str
    training_config: dict
    metrics_2021_test_by_lead: dict
    region_mapping_known_limitation: str


class ServiceMetadata(BaseModel):
    project: str = "AI-Based Forecast Bust Detection (SIH 2026 PS 26079)"
    api_version: str
    models: list[ModelMetadata]
    supported_lead_days: list[int]
    supported_variables: list[Variable]
    geographic_domain: dict
    risk_thresholds: dict
    scientific_framing: str = (
        "This system estimates the probability that an NWP forecast will "
        "experience a predefined forecast bust, based on historical forecast "
        "behaviour and forecast-state features. It is not a guarantee, does "
        "not claim perfect accuracy, and is not itself a weather forecast."
    )


# --------------------------------------------------------------------------
# /explain
# --------------------------------------------------------------------------
class FeatureContribution(BaseModel):
    feature: str
    value: float | str = Field(..., description="numeric for most features; the region name (str) for region_v2")
    contribution: float
    direction: str = Field(..., pattern="^(increases_bust_probability|decreases_bust_probability)$")


class ExplanationResponse(BaseModel):
    variable: Variable
    model_version: str
    base_value: float
    raw_probability: float
    top_features: list[FeatureContribution]
    human_readable_reasons: list[str]


# --------------------------------------------------------------------------
# /health
# --------------------------------------------------------------------------
class HealthResponse(BaseModel):
    status: str
    api_version: str
    models_loaded: list[str]
    timestamp: datetime


# --------------------------------------------------------------------------
# generic structured error (never silently fake missing data)
# --------------------------------------------------------------------------
class ErrorResponse(BaseModel):
    error: str
    detail: str
