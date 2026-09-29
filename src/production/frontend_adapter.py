"""
Phase 6 - thin frontend integration adapter, mounted under `/api/v1`.

This module exists ONLY to reshape existing, already-validated Phase 0-5
outputs into the JSON shape the React frontend expects. It does not:
  - retrain, recalibrate, or otherwise touch any model artifact
  - change the root production endpoints (/predict, /explain, /analogs, ...)
    in `src/production/api.py` - those keep their original schemas verbatim
  - fabricate any number that isn't derived from a real, already-committed
    artifact or a real call into `ProductionInferenceEngine`

Region model
------------
The map shows the REAL production geography directly: the 29 states/UTs
of `region_v2` (`src/phase2/geography.py`), the same geography `/predict`,
`/explain`, `/analogs`, and the root `/regions` all use. There is no
separate presentation geography and no aggregation judgment calls - each
state IS a `region_v2` category, one to one.

(An earlier version of this adapter aggregated the 29 states into 8 broad
zones for a first integration pass. That required a documented but
inherently approximate state->zone mapping - see git history if you need
it. It has been replaced by this direct state-level model per explicit
product direction: showing India's real states is both more accurate and
more meaningful to a non-expert viewer than 8 hand-drawn blobs.)

State geometry: `frontend/src/data/indiaStatesGeo.js` (real SVG paths) and
`outputs/phase2/state_geo_meta.json` (bbox/centroid only, used here) are
both generated from the SAME real GADM-derived boundary file
(`data/raw/india_states.geojson`) that `src/phase2/geography.py` uses to
assign every real grid point to a state - see
`src/phase2/export_state_svg.py`. 6 small union territories in that source
file (Chandigarh, Delhi, Puducherry, Dadra & Nagar Haveli, Daman & Diu,
Nagaland) never receive a real production grid point on this 1.5-degree
grid and are intentionally absent rather than shown with fabricated data.

Risk color bands
-----------------
Chosen from the REAL distribution of calibrated state-level bust
probability across all 10 lead days (computed during this integration,
183 real grid points x 10 lead days): 10th pctile 0.08%, 50th 0.14%,
75th 0.5%, 90th 2.5%, 95th 5.1%, 99th 12.9%, max 15.3%. The distribution
is heavily right-skewed - most state/lead-day combinations are very safe,
with a real, occasional high-risk tail. Bands (`RISK_BANDS` below) are
round numbers close to the 75th/90th/97th percentiles, not the old
mock-data-era thresholds (which assumed probabilities commonly reached
20-60%day and would have shown nearly everything as "low" on real data).
"""
from __future__ import annotations

import json
import os
from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..label_busts import _rain_category

router = APIRouter(prefix="/api/v1", tags=["frontend-adapter"])

REFERENCE_PATH = os.path.join("models", "phase5", "reference.parquet")
EVENT_INDEX_PATH = os.path.join("models", "phase5", "event_index.parquet")
STATE_META_PATH = os.path.join("outputs", "phase2", "state_geo_meta.json")

SEASON_MONTHS = {
    "monsoon_JJAS": {6, 7, 8, 9},
    "post_monsoon_ON": {10, 11},
    "pre_monsoon_MAM": {3, 4, 5},
    "winter_DJF": {12, 1, 2},
}

# See module docstring "Risk color bands" for how these were chosen.
RISK_BANDS = [(0.06, "high"), (0.03, "elevated"), (0.01, "moderate")]


def _risk_level(p: float) -> str:
    for cutoff, label in RISK_BANDS:
        if p >= cutoff:
            return label
    return "low"


@lru_cache(maxsize=1)
def _state_meta() -> dict:
    if not os.path.exists(STATE_META_PATH):
        raise HTTPException(
            status_code=503,
            detail=(
                f"{STATE_META_PATH} not found - run `.venv/Scripts/python.exe "
                "-m src.phase2.export_state_svg` first to regenerate it."
            ),
        )
    with open(STATE_META_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    return {e["id"]: e for e in entries}


def _name_to_id() -> dict:
    return {e["name"]: sid for sid, e in _state_meta().items()}


@lru_cache(maxsize=1)
def _reference() -> pd.DataFrame:
    if not os.path.exists(REFERENCE_PATH):
        raise HTTPException(
            status_code=503,
            detail=(
                f"{REFERENCE_PATH} not found - run `python -m "
                "src.phase5.build_analog_index` first to regenerate it "
                "(gitignored, regenerable artifact)."
            ),
        )
    return pd.read_parquet(REFERENCE_PATH)


@lru_cache(maxsize=1)
def _event_index() -> pd.DataFrame:
    if not os.path.exists(EVENT_INDEX_PATH):
        raise HTTPException(
            status_code=503,
            detail=(
                f"{EVENT_INDEX_PATH} not found - run `python -m "
                "src.phase5.build_event_index` first to regenerate it."
            ),
        )
    df = pd.read_parquet(EVENT_INDEX_PATH)
    return df.set_index("event_id")


def _resolve_state_id(region_id: str) -> str:
    """Accepts the canonical slug id, the exact region_v2 state name, or a
    case-insensitive/space-separated variant of either."""
    meta = _state_meta()
    if region_id in meta:
        return region_id
    name_to_id = _name_to_id()
    if region_id in name_to_id:
        return name_to_id[region_id]
    lowered = region_id.strip().lower().replace(" ", "-")
    if lowered in meta:
        return lowered
    raise HTTPException(status_code=422, detail=f"unknown region_id: {region_id!r}")


def _latest_real_init_time(df: pd.DataFrame, lead_day: int) -> pd.Timestamp:
    sub = df[df.lead_day == lead_day]
    if sub.empty:
        raise HTTPException(status_code=404, detail=f"no real archive data for lead_day={lead_day}")
    return sub.init_time.max()


def _predict_points(points: pd.DataFrame) -> pd.DataFrame:
    """Runs the REAL production engine on each real historical grid point's
    real forecast inputs - genuine model output, never a lookup of a
    precomputed label. Returns points with rain_prob/temp_prob columns added."""
    from .api import _engine  # lazy import - avoids circular import with api.py

    engine = _engine()
    rain_probs, temp_probs = [], []
    for row in points.itertuples():
        result = engine.predict(
            init_time=row.init_time, lead_day=int(row.lead_day),
            latitude=float(row.latitude), longitude=float(row.longitude),
            forecast_precip_mm=float(row.fcst_precip_mm), forecast_temp_c=float(row.fcst_temp_c),
            forecast_mslp_hpa=float(row.fcst_mslp_hpa),
            forecast_wind_speed_10m=float(row.wind_speed_10m) if pd.notna(row.wind_speed_10m) else None,
        )
        rain_probs.append(result["rain_bust_probability"]["calibrated"])
        temp_probs.append(result["temperature_bust_probability"]["calibrated"] if result["temperature_bust_probability"] else None)
    out = points.copy()
    out["rain_prob"] = rain_probs
    out["temp_prob"] = temp_probs
    return out


def _representative_point(pts: pd.DataFrame, sid: str) -> pd.Series:
    """The one real grid point nearest a state's real geometric centroid.
    Used for EVERY per-state number on this page (map tile, tooltip,
    sidebar panel, and /explanations) - using a different statistic (e.g. a
    state-wide mean) in one place and this representative point in another
    produces two different real numbers for the same state/lead-day, which
    is confusing even though each is individually honest. One definition,
    shared by every endpoint below, avoids that."""
    clon, clat = _state_meta()[sid]["centroid"]
    return pts.assign(_d=((pts.latitude - clat) ** 2 + (pts.longitude - clon) ** 2)).sort_values("_d").iloc[0]


# ===========================================================================
# 1. GET /api/v1/forecast
# ===========================================================================
@router.get("/forecast")
def forecast(
    cycle: str = "latest",
    lead_day: int = Query(..., ge=1, le=10),
    region_id: str = Query(...),
):
    state_id = _resolve_state_id(region_id)
    state_name = _state_meta()[state_id]["name"]
    df = _reference()
    init_time = _latest_real_init_time(df, lead_day)
    snapshot = df[(df.init_time == init_time) & (df.lead_day == lead_day)]
    scored = _predict_points(snapshot)

    # regionalMetrics: the SAME representative-point statistic as `verification`
    # below - never a separately-computed state-wide average for the same field.
    regional_metrics = {}
    for sid, smeta in _state_meta().items():
        spts = scored[scored.region_v2 == smeta["name"]]
        if spts.empty:
            continue
        rp = _representative_point(spts, sid)
        bust_prob = float(rp.rain_prob)
        regional_metrics[sid] = {
            "regionId": sid,
            "regionName": smeta["name"],
            "bustProbability": round(bust_prob, 4),
            # Same 1 - calibrated_probability definition ProductionInferenceEngine
            # returns - identical formula everywhere on this page (map, panel).
            "confidence": round(float(1.0 - bust_prob), 4),
            "precipError": round(float(rp.abs_error_precip_mm), 2),
            "tempError": round(float(rp.abs_error_temp_c), 2),
        }

    spts = scored[scored.region_v2 == state_name]
    if spts.empty:
        raise HTTPException(status_code=404, detail=f"no real grid points fall in {state_name!r}")
    # Same representative point as regionalMetrics[state_id] above - the map
    # tile/tooltip and this panel must always agree for the same state.
    rep = _representative_point(spts, state_id)

    fcst_cat = _rain_category(pd.Series([rep.fcst_precip_mm])).cat.codes.iloc[0]
    obs_cat = _rain_category(pd.Series([rep.obs_precip_mm])).cat.codes.iloc[0]

    bust_prob = float(rep.rain_prob)
    return {
        "meta": {
            "cycle": cycle,
            "cycleId": f"ecmwf_hres_{pd.Timestamp(init_time).strftime('%Y%m%d_%H')}z",
            "model": "ECMWF HRES Deterministic",
            "gridResolution": "1.5 deg (real domain grid points, Phase 0-5 archive)",
            "leadDay": lead_day,
            "leadHours": lead_day * 24,
            "regionId": state_id,
            "regionName": state_name,
            "timestamp": pd.Timestamp(init_time).isoformat(),
            "disclaimer": (
                "Operational research verification prototype. Backed by the most "
                "recent REAL verified ECMWF HRES / ERA5 archive date available "
                f"({pd.Timestamp(init_time).isoformat()}), not a live 2026 NWP run - "
                "this system does not ingest live operational forecasts."
            ),
        },
        "verification": {
            "bustProbability": round(bust_prob, 4),
            "confidence": round(float(1.0 - bust_prob), 4),
            "riskLevel": _risk_level(bust_prob),
            "historicalPercentileExceeded": bool(rep.bust_precip_categorical),
            "rulesTriggered": {
                "percentileRule": bool(rep.bust_precip),
                "imdRainCategoryRule": bool(rep.bust_precip_categorical),
                "temperatureHardRule": bool(rep.bust_temp_hard),
            },
        },
        "variables": {
            "precipitation": {
                "unit": "mm",
                "forecastValue": round(float(rep.fcst_precip_mm), 2),
                "observedValue": round(float(rep.obs_precip_mm), 2),
                "absError": round(float(rep.abs_error_precip_mm), 2),
                "categoryShift": int(abs(fcst_cat - obs_cat)),
                "missedHeavyRain": bool(rep.missed_heavy_rain_event),
                "falseAlarmHeavyRain": bool(rep.false_alarm_heavy_rain),
            },
            "temperature": {
                "unit": "degC",
                "forecastValue": round(float(rep.fcst_temp_c), 2),
                "observedValue": round(float(rep.obs_temp_c), 2),
                "absError": round(float(rep.abs_error_temp_c), 2),
                "heatwaveMissFlag": bool(rep.bust_temp_hard),
            },
            "meanSeaLevelPressure": {
                "unit": "hPa",
                "forecastValue": round(float(rep.fcst_mslp_hpa), 2),
                "observedValue": round(float(rep.obs_mslp_hpa), 2),
                "absError": round(float(abs(rep.fcst_mslp_hpa - rep.obs_mslp_hpa)), 2),
            },
        },
        "regionalMetrics": regional_metrics,
        "explanations": [],  # populated via GET /api/v1/explanations, not duplicated here
        "spatialGridSample": [],
    }


# ===========================================================================
# 2 & 3. GET /api/v1/regions, GET /api/v1/regions/{id}
# ===========================================================================
@router.get("/regions")
def regions_list():
    df = _reference()
    train = df[df.split == "train"]
    out = []
    for sid, smeta in _state_meta().items():
        spts = train[train.region_v2 == smeta["name"]]
        baseline = float(spts.bust_precip_categorical.mean()) if not spts.empty else None
        lon_min, lat_min, lon_max, lat_max = smeta["bbox"]
        out.append({
            "id": sid,
            "name": smeta["name"],
            "shortName": smeta["name"],
            "bbox": {"latMin": lat_min, "latMax": lat_max, "lonMin": lon_min, "lonMax": lon_max},
            "centroid": smeta["centroid"],
            "baselineRisk": round(baseline, 4) if baseline is not None else None,
            "dominantSeason": "monsoon_JJAS",
            "nRealGridPoints": int(spts[["latitude", "longitude"]].drop_duplicates().shape[0]),
        })
    return out


@router.get("/regions/{region_id}")
def region_detail(
    region_id: str,
    season: str = "monsoon_JJAS",
    lead_day: int = Query(5, ge=1, le=10),
    cycle: str = "latest",
):
    state_id = _resolve_state_id(region_id)
    state_name = _state_meta()[state_id]["name"]
    df = _reference()
    sdf = df[df.region_v2 == state_name]
    if sdf.empty:
        raise HTTPException(status_code=404, detail=f"no real data for {state_name!r}")
    months = SEASON_MONTHS.get(season)
    if months is not None:
        sdf = sdf[sdf.month.isin(months)]

    by_lead = (
        sdf.groupby("lead_day")
        .agg(
            meanAbsErrorPrecipMm=("abs_error_precip_mm", "mean"),
            meanAbsErrorTempC=("abs_error_temp_c", "mean"),
            bustRate=("bust_precip_categorical", "mean"),
            nSamples=("bust_precip_categorical", "size"),
        )
        .reset_index()
    )
    error_progression = [
        {
            "leadDay": int(r.lead_day),
            "meanAbsErrorPrecipMm": round(float(r.meanAbsErrorPrecipMm), 2),
            "meanAbsErrorTempC": round(float(r.meanAbsErrorTempC), 2),
            "bustRate": round(float(r.bustRate) * 100, 1),
            "nSamples": int(r.nSamples),
        }
        for r in by_lead.itertuples()
    ]

    return {
        "id": state_id,
        "name": state_name,
        "season": season,
        "requestedLeadDay": lead_day,
        "cycle": cycle,
        "errorProgression": error_progression,
        "nSamplesTotal": int(len(sdf)),
        "disclaimer": (
            "All statistics computed from the real 2018-2021 ECMWF HRES / ERA5 "
            "verification archive (JJAS only - see docs/historical_analogs.md "
            "Limitations); not live operational statistics."
        ),
    }


# ===========================================================================
# 4. GET /api/v1/explanations
# ===========================================================================
@router.get("/explanations")
def explanations(
    cycle: str = "latest",
    lead_day: int = Query(..., ge=1, le=10),
    region_id: str = Query(...),
):
    from .api import _analog_index, _engine
    from . import explain as explain_module
    from ..phase5.features import _train_period_mean_wind

    state_id = _resolve_state_id(region_id)
    state_name = _state_meta()[state_id]["name"]
    df = _reference()
    init_time = _latest_real_init_time(df, lead_day)
    snapshot = df[(df.init_time == init_time) & (df.lead_day == lead_day) & (df.region_v2 == state_name)]
    if snapshot.empty:
        raise HTTPException(status_code=404, detail=f"no real grid points fall in {state_name!r}")
    rep = _representative_point(snapshot, state_id)

    engine = _engine()
    row, _region_v2 = engine.feature_row_for_explanation(
        init_time=rep.init_time, lead_day=int(rep.lead_day),
        latitude=float(rep.latitude), longitude=float(rep.longitude),
        forecast_precip_mm=float(rep.fcst_precip_mm), forecast_temp_c=float(rep.fcst_temp_c),
        forecast_mslp_hpa=float(rep.fcst_mslp_hpa),
        forecast_wind_speed_10m=float(rep.wind_speed_10m) if pd.notna(rep.wind_speed_10m) else None,
    )
    result = explain_module.explain("rain_v1", row)

    query_row = dict(row)
    query_row["init_time"] = pd.Timestamp(rep.init_time)
    query_row["month"] = int(rep.month)
    if "wind_speed_10m" not in query_row or query_row["wind_speed_10m"] is None:
        query_row["wind_speed_10m"] = _train_period_mean_wind()
    analog_result = _analog_index().query(query_row, k=5, spatial_constraint="same_region", temporal_constraint="exact_month")

    # Plain-English feature names - a non-expert should never see a raw
    # Python column name like "hist_bust_precip_categorical_rate".
    PLAIN_FEATURE_NAMES = {
        "hist_bust_precip_categorical_rate": "How often forecasts have been wrong here before",
        "hist_bust_temp_hard_rate": "How often temperature forecasts have been wrong here before",
        "hist_mean_abs_error_precip_mm": "Typical rainfall forecast error in this area",
        "hist_mean_abs_error_temp_c": "Typical temperature forecast error in this area",
        "fcst_precip_mm": "How much rain is forecast",
        "fcst_temp_c": "Forecast temperature",
        "fcst_mslp_hpa": "Forecast air pressure pattern",
        "fcst_precip_anomaly_vs_domain_mean": "Rain forecast is unusually high/low for this time of year",
        "fcst_temp_anomaly_vs_domain_mean": "Temperature forecast is unusually high/low for this time of year",
        "precip_forecast_jump": "Rain forecast changed a lot from the previous model run",
        "temp_forecast_jump": "Temperature forecast changed a lot from the previous model run",
        "wind_speed_10m": "Forecast wind speed",
        "lead_day": "How many days ahead this forecast is for",
        "month": "Time of year",
        "region_v2": "Location",
    }

    factors = []
    for f in result["top_features"]:
        plain_name = PLAIN_FEATURE_NAMES.get(f["feature"], f["feature"].replace("_", " ").title())
        factors.append({
            "factorId": f"model-{f['feature']}",
            "name": plain_name,
            "plainReason": plain_name,
            "description": f"Model input: {plain_name.lower()} (value={f['value']}).",
            "source": "model_output",
            "contribution": round(float(f["contribution"]), 4),
            "shapValue": round(float(f["contribution"]), 4),
            "direction": "positive_risk" if f["direction"] == "increases_bust_probability" else "negative_risk",
            "severity": "high" if abs(f["contribution"]) > 0.2 else ("elevated" if abs(f["contribution"]) > 0.1 else "low"),
            "evidenceValue": f"value={f['value']}",
            "tooltip": "From the model's own real calculation for this forecast (SHAP feature contribution).",
        })
    for a in analog_result.analogs:
        factors.append({
            "factorId": f"analog-{a.rank}",
            "name": f"Similar past case: {a.region}, {pd.Timestamp(a.historical_valid_time).date()}",
            "plainReason": f"A similar past forecast in {a.region} predicted {a.forecast_precip_mm:.1f}mm of rain, but {a.actual_precip_mm:.1f}mm actually fell",
            "description": (
                "A real, verified past forecast that closely resembles this one, and what actually "
                "happened then. This is evidence, not proof - it does not guarantee the same outcome this time."
            ),
            "source": "historical_context",
            "contribution": None,
            "shapValue": None,
            "direction": "positive_risk" if a.actual_precip_mm > a.forecast_precip_mm else "negative_risk",
            "severity": "elevated",
            "evidenceValue": f"forecast={a.forecast_precip_mm:.1f}mm, actual={a.actual_precip_mm:.1f}mm",
            "tooltip": "Real historical case retrieved by similarity search - never a fabricated example.",
        })

    return {
        "cycle": cycle,
        "leadDay": lead_day,
        "region": state_name,
        "bulletinSummary": (
            result["human_readable_reasons"][0] if result["human_readable_reasons"]
            else f"{len(factors)} reasons found for {state_name} at {lead_day} days ahead."
        ),
        "factors": factors,
    }


# ===========================================================================
# 5. GET /api/v1/historical-performance
# ===========================================================================
@router.get("/historical-performance")
def historical_performance(
    lead_day: int | None = Query(None, ge=1, le=10),
    region_id: str | None = None,
    season: str = "monsoon_JJAS",
    variable: str = "all",
):
    df = _reference()
    months = SEASON_MONTHS.get(season)
    if months is None:
        # no real data outside our JJAS-only archive - never fabricate a
        # winter/pre-monsoon/post-monsoon record that doesn't exist
        return []
    df = df[df.month.isin(months)]
    if lead_day is not None:
        df = df[df.lead_day == lead_day]
    if region_id is not None:
        state_name = _state_meta()[_resolve_state_id(region_id)]["name"]
        df = df[df.region_v2 == state_name]

    out = []
    for (state_name, ld), g in df.groupby(["region_v2", "lead_day"], observed=True):
        record = {
            "region": state_name,
            "season": season,
            "leadDay": int(ld),
            "bustRate": round(float(g.bust_precip_categorical.mean()) * 100, 1),
            "precipBustRate": round(float(g.bust_precip_categorical.mean()) * 100, 1),
            "meanAbsErrorPrecipMm": round(float(g.abs_error_precip_mm.mean()), 2),
            "tempBustRate": round(float(g.bust_temp_hard.mean()) * 100, 1),
            "meanAbsErrorTempC": round(float(g.abs_error_temp_c.mean()), 2),
            "nSamples": int(len(g)),
            "missedHeavyRainEvents": int(g.missed_heavy_rain_event.sum()),
            "falseAlarmHeavyRain": int(g.false_alarm_heavy_rain.sum()),
        }
        if variable in ("all", "precipitation", "temperature"):
            out.append(record)
    return out


# ===========================================================================
# 6. GET /api/v1/cycles
# ===========================================================================
@router.get("/cycles")
def cycles():
    df = _reference()
    real_init_times = sorted(df[df.lead_day == 1].init_time.unique())[-5:]
    out = []
    for i, ts in enumerate(reversed(real_init_times)):
        ts = pd.Timestamp(ts)
        label_suffix = " (most recent real archive date)" if i == 0 else ""
        code = f"{ts.strftime('%Y-%m-%d')} {ts.strftime('%H')}Z"
        out.append({
            "code": code,
            "label": f"{code}{label_suffix}",
            "model": "ECMWF HRES Deterministic",
            "gridResolution": "1.5 deg (real domain grid points, Phase 0-5 archive)",
            "id": code,
        })
    return out


# ===========================================================================
# 7 & 8. GET /api/v1/replay/events, GET /api/v1/replay/event
# ===========================================================================
# The one real, verified showcase case wired for this demo. NOTE: an earlier
# Phase 5 report cited "Jharkhand, forecast 92.8mm vs actual 3.4mm" as a real
# case - that number pair was actually a synthetic /explain test-query
# parameter, not a verified ERA5 outcome, and does not appear in the real
# event index. It has been corrected here: this is a genuinely verified
# Phase 5 event-index record.
SHOWCASE_EVENT_ID = "f9956e4b8883ec69"  # Jharkhand, init 2018-07-16, lead_day 8


@router.get("/replay/events")
def replay_events():
    events = _event_index()
    if SHOWCASE_EVENT_ID not in events.index:
        return []
    row = events.loc[SHOWCASE_EVENT_ID]
    return [{
        "eventId": SHOWCASE_EVENT_ID,
        "label": f"{row.region_v2}, {pd.Timestamp(row.valid_time).date()} - heavy rain bust",
        "region": row.region_v2,
        "validTime": pd.Timestamp(row.valid_time).isoformat(),
        "summary": (
            f"Real ECMWF HRES Day-{int(row.lead_day)} forecast called "
            f"{row.fcst_precip_mm:.1f}mm; ERA5-verified truth was "
            f"{row.obs_precip_mm:.1f}mm - a real, verified categorical rain bust."
        ),
    }]


@router.get("/replay/event")
def replay_event(
    event_id: str,
    lead_day: int | None = Query(None, ge=1, le=10),
    cycle: str | None = None,
    region_id: str | None = None,
):
    events = _event_index()
    if event_id not in events.index:
        raise HTTPException(status_code=404, detail=f"unknown event_id: {event_id!r}")
    anchor = events.loc[event_id]

    # Real forecast-evolution-across-lead-days for this one physical event:
    # valid_time is fixed, different lead_days come from different real
    # init_times - so we show the real trajectory across lead_day using the
    # reference table filtered to this exact grid point + valid_time.
    df = _reference()
    same_point = df[
        (df.latitude == anchor.latitude)
        & (df.longitude == anchor.longitude)
        & (df.valid_time == anchor.valid_time)
    ].sort_values("lead_day")

    trajectory = [
        {
            "leadDay": int(r.lead_day),
            "initTime": pd.Timestamp(r.init_time).isoformat(),
            "forecastPrecipMm": round(float(r.fcst_precip_mm), 2),
            "actualPrecipMm": round(float(r.obs_precip_mm), 2),
            "absErrorMm": round(float(r.abs_error_precip_mm), 2),
        }
        for r in same_point.itertuples()
    ]

    return {
        "eventId": event_id,
        "region": anchor.region_v2,
        "validTime": pd.Timestamp(anchor.valid_time).isoformat(),
        "requestedLeadDay": lead_day,
        "requestedCycle": cycle,
        "leadDayTrajectory": trajectory,
        "disclaimer": (
            "Real ECMWF HRES forecast values issued at different lead times "
            "for this one verified historical event, plotted against the "
            "single real ERA5-verified outcome - not a live replay simulation."
        ),
    }
