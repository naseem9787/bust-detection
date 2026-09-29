"""
Phase 4 - production FastAPI service. Backend/inference only - no frontend
code lives here or anywhere in this repository; a separate team owns that.
See docs/api_contract.md for the full frontend-facing contract with
worked JSON examples.

Run:
    .venv/Scripts/python.exe -m uvicorn src.production.api:app --reload
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from . import registry
from .aggregation import aggregate_region
from .features import UnknownRegionError
from .inference import ProductionInferenceEngine
from .registry import ExperimentalFeatureRequestedError, UnknownModelError
from .schemas import (
    BustProbability,
    ErrorResponse,
    ExplanationResponse,
    FeatureContribution,
    GridPrediction,
    HealthResponse,
    ModelMetadata,
    PredictionRequest,
    PredictionResponse,
    RegionInfo,
    ServiceMetadata,
    Variable,
)
from .thresholds import DEFAULT_THRESHOLDS, THRESHOLD_BASIS

API_VERSION = "0.1.0"
_state: dict = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # loaded ONCE at process startup - never per-request (see
    # docs/production_inference.md Performance section)
    _state["engine"] = ProductionInferenceEngine()
    _state["started_at"] = datetime.now(timezone.utc)
    yield
    _state.clear()


app = FastAPI(
    title="Forecast Bust Detection API (SIH 2026 PS 26079)",
    version=API_VERSION,
    lifespan=lifespan,
    description=(
        "Estimates the probability that an NWP forecast will experience a "
        "predefined forecast bust, using historical forecast behaviour and "
        "forecast-state features. Not a weather forecast itself; not a "
        "guarantee of accuracy."
    ),
)


def _engine() -> ProductionInferenceEngine:
    return _state["engine"]


@app.exception_handler(UnknownRegionError)
async def _handle_outside_domain(request, exc: UnknownRegionError):
    return JSONResponse(status_code=422, content=ErrorResponse(error="outside_domain", detail=str(exc)).model_dump())


@app.exception_handler(UnknownModelError)
async def _handle_unknown_model(request, exc: UnknownModelError):
    return JSONResponse(status_code=404, content=ErrorResponse(error="unknown_model", detail=str(exc)).model_dump())


@app.exception_handler(ExperimentalFeatureRequestedError)
async def _handle_experimental(request, exc: ExperimentalFeatureRequestedError):
    return JSONResponse(status_code=400, content=ErrorResponse(error="experimental_feature_requested", detail=str(exc)).model_dump())


# --------------------------------------------------------------------------
@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok" if "engine" in _state else "starting",
        api_version=API_VERSION,
        models_loaded=list(registry.PRODUCTION_MODELS),
        timestamp=datetime.now(timezone.utc),
    )


# --------------------------------------------------------------------------
@app.get("/metadata", response_model=ServiceMetadata)
def metadata() -> ServiceMetadata:
    models = []
    for key in registry.PRODUCTION_MODELS:
        entry = registry.load_entry(key)
        models.append(
            ModelMetadata(
                model_name=entry.raw["model_name"],
                model_version=entry.raw["model_version"],
                status=entry.status,
                target_variable=entry.target_variable,
                target_definition=entry.raw["target_definition"],
                n_features=entry.raw["n_features"],
                calibration_method=entry.calibration_method,
                training_config=entry.raw["training_config"],
                metrics_2021_test_by_lead=entry.lead_curve,
                region_mapping_known_limitation=entry.raw["region_mapping"]["known_limitation"],
            )
        )
    return ServiceMetadata(
        api_version=API_VERSION,
        models=models,
        supported_lead_days=list(range(1, 11)),
        supported_variables=[Variable.rain, Variable.temperature],
        geographic_domain=registry.load_entry("rain_v1").raw["source_dataset"],
        risk_thresholds={**DEFAULT_THRESHOLDS, "basis": THRESHOLD_BASIS},
    )


# --------------------------------------------------------------------------
@app.post("/predict", response_model=PredictionResponse)
def predict(req: PredictionRequest) -> PredictionResponse:
    result = _engine().predict(
        init_time=req.init_time,
        lead_day=req.lead_day,
        latitude=req.latitude,
        longitude=req.longitude,
        forecast_precip_mm=req.forecast_precip_mm,
        forecast_temp_c=req.forecast_temp_c,
        forecast_mslp_hpa=req.forecast_mslp_hpa,
        forecast_wind_speed_10m=req.forecast_wind_speed_10m,
        domain_mean_precip_mm=req.domain_mean_precip_mm,
        domain_mean_temp_c=req.domain_mean_temp_c,
        previous_run_forecast_precip_mm=req.previous_run_forecast_precip_mm,
        previous_run_forecast_temp_c=req.previous_run_forecast_temp_c,
    )

    def _prob(d: dict | None) -> BustProbability | None:
        return None if d is None else BustProbability(**d)

    grid = GridPrediction(
        init_time=result["init_time"],
        lead_day=result["lead_day"],
        valid_time=result["valid_time"],
        latitude=result["latitude"],
        longitude=result["longitude"],
        region=result["region"],
        in_india_domain=result["in_india_domain"],
        forecast_precip_mm=result["forecast_precip_mm"],
        forecast_temp_c=result["forecast_temp_c"],
        rain_bust_probability=_prob(result["rain_bust_probability"]),
        temperature_bust_probability=_prob(result["temperature_bust_probability"]),
        model_version=result["model_version"],
        feature_version=result["feature_version"],
        calibration_version=result["calibration_version"],
    )
    return PredictionResponse(prediction=grid)


# --------------------------------------------------------------------------
PREDICTIONS_DIR = os.path.join("outputs", "production", "batch")


@app.get("/predictions")
def get_predictions(
    init_time: str | None = None,
    lead_day: int | None = Query(None, ge=1, le=10),
    region: str | None = None,
    variable: Variable | None = None,
):
    import glob

    files = sorted(
        glob.glob(os.path.join(PREDICTIONS_DIR, "**", "grid_predictions.parquet"), recursive=True),
        key=os.path.getmtime,
    )
    if not files:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="no_persisted_predictions",
                detail=(
                    "No batch predictions have been generated yet. Run "
                    "`python -m src.production.batch_predict --init-time-start ... "
                    "--init-time-end ... --output outputs/production/batch/<run>` "
                    "first - this endpoint never fabricates data."
                ),
            ).model_dump(),
        )
    df = pd.read_parquet(files[-1])
    if init_time is not None:
        df = df[df.init_time == pd.Timestamp(init_time)]
    if lead_day is not None:
        df = df[df.lead_day == lead_day]
    if region is not None:
        df = df[df.region == region]
    if variable is not None:
        cols = [c for c in df.columns if c.startswith(variable.value)]
        df = df[["init_time", "lead_day", "valid_time", "latitude", "longitude", "region"] + cols]
    return JSONResponse(content=df.astype(str).to_dict(orient="records"))


# --------------------------------------------------------------------------
@app.get("/regions", response_model=list[RegionInfo])
def regions() -> list[RegionInfo]:
    path = os.path.join("outputs", "phase2", "region_assignment_summary.csv")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"{path} not found")
    df = pd.read_csv(path)
    known_limitation = registry.load_entry("rain_v1").raw["region_mapping"]["known_limitation"]
    return [
        RegionInfo(
            region=row.region,
            n_grid_points=int(row.n_grid_points),
            known_limitation=known_limitation if row.get("note") else None,
        )
        for _, row in df.iterrows()
    ]


# --------------------------------------------------------------------------
@app.get("/timeseries")
def timeseries(
    valid_time: str,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=0, le=360),
):
    """OFFLINE/HISTORICAL mode only (see docs/production_inference.md Data
    Availability section) - pulls the ACTUAL historical forecasts issued at
    every lead day 1-10 for the given valid_time/location from the research
    error database, and returns the model's probability at each lead day.
    This is real historical data, not live operational ingestion (which
    this repository does not implement)."""
    error_db_path = os.path.join("data", "processed", "error_db.parquet")
    if not os.path.exists(error_db_path):
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="historical_data_unavailable",
                detail=f"{error_db_path} not found locally - cannot serve historical timeseries.",
            ).model_dump(),
        )
    df = pd.read_parquet(error_db_path)
    vt = pd.Timestamp(valid_time)
    d2 = (df.latitude - latitude) ** 2 + (df.longitude - longitude) ** 2
    nearest_latlon = df.loc[d2.idxmin(), ["latitude", "longitude"]]
    rows = df[
        (df.valid_time == vt)
        & (df.latitude == nearest_latlon.latitude)
        & (df.longitude == nearest_latlon.longitude)
    ].sort_values("lead_day")
    if rows.empty:
        return JSONResponse(
            status_code=404,
            content=ErrorResponse(
                error="no_historical_forecasts_for_valid_time",
                detail=f"no forecasts targeting {valid_time} at this location were found in the historical dataset",
            ).model_dump(),
        )

    engine = _engine()
    out = []
    for _, row in rows.iterrows():
        result = engine.predict(
            init_time=row.init_time,
            lead_day=int(row.lead_day),
            latitude=float(row.latitude),
            longitude=float(row.longitude),
            forecast_precip_mm=float(row.fcst_precip_mm),
            forecast_temp_c=float(row.fcst_temp_c),
            forecast_mslp_hpa=float(row.fcst_mslp_hpa),
        )
        out.append(
            {
                "lead_day": result["lead_day"],
                "init_time": str(result["init_time"]),
                "rain_bust_probability": result["rain_bust_probability"]["calibrated"],
                "rain_confidence": result["rain_bust_probability"]["confidence"],
            }
        )
    return {"valid_time": valid_time, "latitude": float(nearest_latlon.latitude),
            "longitude": float(nearest_latlon.longitude), "trajectory": out}


# --------------------------------------------------------------------------
@app.get("/explain", response_model=ExplanationResponse)
def explain_prediction(
    variable: Variable,
    init_time: str,
    lead_day: int = Query(..., ge=1, le=10),
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=0, le=360),
    forecast_precip_mm: float = 0.0,
    forecast_temp_c: float = 25.0,
    forecast_mslp_hpa: float = 1010.0,
    forecast_wind_speed_10m: float | None = None,
) -> ExplanationResponse:
    from . import explain as explain_module

    model_key = "rain_v1" if variable == Variable.rain else "temperature_v1"
    if model_key == "temperature_v1" and forecast_wind_speed_10m is None:
        raise HTTPException(
            status_code=422,
            detail="forecast_wind_speed_10m is required to explain the temperature model",
        )
    row, region = _engine().feature_row_for_explanation(
        init_time=init_time, lead_day=lead_day, latitude=latitude, longitude=longitude,
        forecast_precip_mm=forecast_precip_mm, forecast_temp_c=forecast_temp_c,
        forecast_mslp_hpa=forecast_mslp_hpa, forecast_wind_speed_10m=forecast_wind_speed_10m,
    )
    result = explain_module.explain(model_key, row)
    return ExplanationResponse(
        variable=variable,
        model_version=registry.load_entry(model_key).raw["model_version"],
        base_value=result["base_value"],
        raw_probability=result["raw_probability"],
        top_features=[FeatureContribution(**f) for f in result["top_features"]],
        human_readable_reasons=result["human_readable_reasons"],
    )
