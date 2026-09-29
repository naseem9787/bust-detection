"""
Phase 6 - thin frontend integration adapter, mounted under `/api/v1`.

This module exists ONLY to reshape existing, already-validated Phase 0-5
outputs into the exact JSON contract the React frontend expects (see
`FRONTEND_API_CONTRACT.md` at the repo root). It does not:
  - retrain, recalibrate, or otherwise touch any model artifact
  - change the root production endpoints (/predict, /explain, /analogs, ...)
    in `src/production/api.py` - those keep their original schemas verbatim
  - fabricate any number that isn't derived from a real, already-committed
    artifact or a real call into `ProductionInferenceEngine`

Region model - READ THIS FIRST
-------------------------------
The frontend's India choropleth expects exactly 8 "presentation zones"
(`western-himalaya`, `northwest-india`, `indo-gangetic-plain`,
`northeast-india`, `central-india`, `west-coast`, `east-coast`,
`south-peninsula` - see FRONTEND_API_CONTRACT.md Section 6). The production
rain_v1/temperature_v1 models do NOT predict on this geography - they use
the validated 29-state `region_v2` geography from Phase 2
(`src/phase2/geography.py`), which is what `/predict`, `/explain`,
`/analogs`, and `/regions` all use.

A dormant, never-wired-into-production 8-zone module already exists at
`src/regions.py` with bounding boxes that happen to match the frontend's
8 zones almost exactly. It is NOT used here for point classification,
because inspecting it during this integration surfaced a real bug: its
South Peninsula box (lat 8-16, lon 74.5-80) is fully nested inside its
West Coast box (lat 8-20, lon 72-77), so naive first-match bounding-box
classification always resolves South Peninsula points to West Coast -
South Peninsula would never receive any data. `src/regions.py` itself is
left untouched (per the integration plan: don't modify shared/legacy
files unless the frontend genuinely requires a compatible change, and
this bug is pre-existing and was never exercised because nothing else
imports that module's `assign_region`).

Instead, this adapter aggregates the real 29-state `region_v2` predictions
into the 8 zones via a direct, documented STATE_TO_ZONE mapping (below).
Every explicit zone name in FRONTEND_API_CONTRACT.md's Section 6
parenthetical (e.g. "West Coast (Konkan/Goa/Kerala)") is honored exactly.
A handful of states are NOT named in any zone description (Gujarat, West
Bengal, Jharkhand) or are split across two zone descriptions in the
contract itself (Maharashtra's Konkan-vs-Vidarbha, Tamil Nadu's coast-vs-
interior) - `region_v2` is state-level only, so a sub-state split isn't
possible from existing data. Those are resolved with a documented,
best-effort judgment call, listed inline below. This is the same kind of
disclosed simplification as the project's existing Telangana/Ladakh
`known_limitation` note in the model registry - never silent.
"""
from __future__ import annotations

import os
from functools import lru_cache

import pandas as pd
from fastapi import APIRouter, HTTPException, Query

from ..label_busts import _rain_category
from .thresholds import DEFAULT_THRESHOLDS

router = APIRouter(prefix="/api/v1", tags=["frontend-adapter"])

REFERENCE_PATH = os.path.join("models", "phase5", "reference.parquet")
EVENT_INDEX_PATH = os.path.join("models", "phase5", "event_index.parquet")

# ---------------------------------------------------------------------------
# 8-zone presentation geography. bbox/centroid taken directly from the
# (unused-in-production) src/regions.py boxes, which already match
# FRONTEND_API_CONTRACT.md Section 6 exactly.
ZONE_META = {
    "western-himalaya": {
        "id": "western-himalaya", "name": "Western Himalaya (J&K/HP/Uttarakhand)",
        "shortName": "Western Himalaya", "bbox": [73.0, 28.0, 81.0, 36.0], "centroid": [77.0, 32.0],
    },
    "northwest-india": {
        "id": "northwest-india", "name": "Northwest India (Punjab/Haryana/Rajasthan)",
        "shortName": "Northwest India", "bbox": [69.0, 24.0, 79.0, 32.0], "centroid": [74.0, 28.0],
    },
    "indo-gangetic-plain": {
        "id": "indo-gangetic-plain", "name": "Indo-Gangetic Plain (UP/Bihar)",
        "shortName": "Indo-Gangetic Plain", "bbox": [79.0, 24.0, 88.0, 30.0], "centroid": [83.5, 27.0],
    },
    "northeast-india": {
        "id": "northeast-india", "name": "Northeast India",
        "shortName": "Northeast India", "bbox": [88.0, 22.0, 97.5, 29.5], "centroid": [92.75, 25.75],
    },
    "central-india": {
        "id": "central-india", "name": "Central India (MP/Chhattisgarh/Vidarbha)",
        "shortName": "Central India", "bbox": [74.0, 18.0, 84.0, 26.0], "centroid": [79.0, 22.0],
    },
    "west-coast": {
        "id": "west-coast", "name": "West Coast (Konkan/Goa/Kerala)",
        "shortName": "West Coast", "bbox": [72.0, 8.0, 77.0, 20.0], "centroid": [74.5, 14.0],
    },
    "east-coast": {
        "id": "east-coast", "name": "East Coast (Andhra/Odisha/TN coast)",
        "shortName": "East Coast", "bbox": [78.0, 8.0, 87.0, 20.0], "centroid": [82.5, 14.0],
    },
    "south-peninsula": {
        "id": "south-peninsula", "name": "South Peninsula (Interior Karnataka/TN)",
        "shortName": "South Peninsula", "bbox": [74.5, 8.0, 80.0, 16.0], "centroid": [77.25, 12.0],
    },
}

# Direct state (region_v2) -> zone mapping. Entries marked "judgment call"
# are states not explicitly named in any FRONTEND_API_CONTRACT.md zone
# description, or split across two zone descriptions there; region_v2 is
# state-level only so a sub-state split is not possible from existing data.
STATE_TO_ZONE: dict[str, str] = {
    # -- explicitly named in the frontend contract's own zone descriptions --
    "Jammu and Kashmir": "western-himalaya",
    "Himachal Pradesh": "western-himalaya",
    "Uttarakhand": "western-himalaya",
    "Punjab": "northwest-india",
    "Haryana": "northwest-india",
    "Rajasthan": "northwest-india",
    "Uttar Pradesh": "indo-gangetic-plain",
    "Bihar": "indo-gangetic-plain",
    "Arunachal Pradesh": "northeast-india",
    "Assam": "northeast-india",
    "Manipur": "northeast-india",
    "Meghalaya": "northeast-india",
    "Mizoram": "northeast-india",
    "Tripura": "northeast-india",
    "Sikkim": "northeast-india",
    "Madhya Pradesh": "central-india",
    "Chhattisgarh": "central-india",
    "Kerala": "west-coast",
    "Goa": "west-coast",
    "Andhra Pradesh": "east-coast",
    "Odisha": "east-coast",
    "Karnataka": "south-peninsula",
    # -- judgment calls (state not named, or named in two zones) --
    "Maharashtra": "west-coast",  # coastal Konkan identity chosen over interior Vidarbha
    "Tamil Nadu": "east-coast",  # coastal identity chosen over interior south-peninsula half
    "Gujarat": "northwest-india",  # not named anywhere; closest bbox/climate affinity
    "West Bengal": "indo-gangetic-plain",  # Gangetic delta identity
    "Jharkhand": "indo-gangetic-plain",  # borders Bihar, conventionally grouped with it
    "Andaman and Nicobar": "east-coast",  # island territory, Bay of Bengal
    "Lakshadweep": "west-coast",  # island territory, Arabian Sea
}

SEASON_MONTHS = {
    "monsoon_JJAS": {6, 7, 8, 9},
    "post_monsoon_ON": {10, 11},
    "pre_monsoon_MAM": {3, 4, 5},
    "winter_DJF": {12, 1, 2},
}

RISK_LEVEL_BANDS = [
    (0.45, "extreme"), (0.35, "high"), (0.25, "elevated"), (0.15, "moderate"),
]


def _risk_level(p: float) -> str:
    """Frontend's own 5-tier presentational scheme (FRONTEND_API_CONTRACT.md
    Section 5) - separate from and does not replace the backend's own
    configurable DEFAULT_THRESHOLDS (3-tier) used by the root /predict etc."""
    for cutoff, label in RISK_LEVEL_BANDS:
        if p >= cutoff:
            return label
    return "low"


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
    df = pd.read_parquet(REFERENCE_PATH)
    df["zone"] = df["region_v2"].map(STATE_TO_ZONE)
    return df


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
    df["zone"] = df["region_v2"].map(STATE_TO_ZONE)
    return df.set_index("event_id")


def _resolve_zone_id(region_id: str) -> str:
    """Accepts canonical kebab-case id, display name, or short name - api.js
    normalizes most of this already, but the adapter stays permissive."""
    if region_id in ZONE_META:
        return region_id
    for zid, meta in ZONE_META.items():
        if region_id in (meta["name"], meta["shortName"]):
            return zid
    lowered = region_id.strip().lower().replace(" ", "-")
    if lowered in ZONE_META:
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


# ===========================================================================
# 1. GET /api/v1/forecast
# ===========================================================================
@router.get("/forecast")
def forecast(
    cycle: str = "latest",
    lead_day: int = Query(..., ge=1, le=10),
    region_id: str = Query(...),
):
    zone_id = _resolve_zone_id(region_id)
    df = _reference()
    init_time = _latest_real_init_time(df, lead_day)
    snapshot = df[(df.init_time == init_time) & (df.lead_day == lead_day)]
    scored = _predict_points(snapshot)

    # regionalMetrics: real per-point model predictions aggregated per zone
    regional_metrics = {}
    for zid, zmeta in ZONE_META.items():
        zpts = scored[scored.zone == zid]
        if zpts.empty:
            continue
        regional_metrics[zid] = {
            "regionId": zid,
            "regionName": zmeta["shortName"],
            "bustProbability": round(float(zpts.rain_prob.mean()), 4),
            "confidence": round(float(1.0 - zpts.rain_prob.std(ddof=0)) if len(zpts) > 1 else 0.5, 4),
            "precipError": round(float(zpts.abs_error_precip_mm.mean()), 2),
            "tempError": round(float(zpts.abs_error_temp_c.mean()), 2),
        }

    zpts = scored[scored.zone == zone_id]
    if zpts.empty:
        raise HTTPException(status_code=404, detail=f"no real grid points fall in zone {zone_id!r}")
    # representative point = real grid point nearest the zone centroid, for
    # the single-value `variables`/`verification` fields
    clon, clat = ZONE_META[zone_id]["centroid"]
    rep = zpts.assign(_d=((zpts.latitude - clat) ** 2 + (zpts.longitude - clon) ** 2)).sort_values("_d").iloc[0]

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
            "regionId": zone_id,
            "regionName": ZONE_META[zone_id]["name"],
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
            "confidence": round(float(1.0 - bust_prob), 4) if pd.isna(rep.temp_prob) else round(float(1.0 - abs(rep.rain_prob - rep.temp_prob)), 4),
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
    for zid, zmeta in ZONE_META.items():
        zpts = train[train.zone == zid]
        baseline = float(zpts.bust_precip_categorical.mean()) if not zpts.empty else None
        top_states = (
            zpts.groupby("region_v2")["bust_precip_categorical"].mean().sort_values(ascending=False).head(2)
            if not zpts.empty else pd.Series(dtype=float)
        )
        lon_min, lat_min, lon_max, lat_max = zmeta["bbox"]
        out.append({
            "id": zid,
            "name": zmeta["name"],
            "shortName": zmeta["shortName"],
            # NOTE: FRONTEND_API_CONTRACT.md Section 7 documents `bbox` as an
            # array, but the actual RegionalSummary.jsx reads
            # `region.bbox.{latMin,latMax,lonMin,lonMax}` as an object - the
            # real component code wins over the written doc (per integration
            # instructions). indiaGeoData.js's own separate `bbox` arrays
            # (static SVG map data) are untouched.
            "bbox": {"latMin": lat_min, "latMax": lat_max, "lonMin": lon_min, "lonMax": lon_max},
            "centroid": zmeta["centroid"],
            "baselineRisk": round(baseline, 4) if baseline is not None else None,
            "dominantSeason": "monsoon_JJAS",
            "climatologicalBustModes": [
                f"{state}: {rate:.1%} historical IMD-category bust rate (2018-2020 train split)"
                for state, rate in top_states.items()
            ],
        })
    return out


@router.get("/regions/{region_id}")
def region_detail(
    region_id: str,
    season: str = "monsoon_JJAS",
    lead_day: int = Query(5, ge=1, le=10),
    cycle: str = "latest",
):
    zone_id = _resolve_zone_id(region_id)
    df = _reference()
    zdf = df[df.zone == zone_id]
    if zdf.empty:
        raise HTTPException(status_code=404, detail=f"no real data for zone {zone_id!r}")
    months = SEASON_MONTHS.get(season)
    if months is not None:
        zdf = zdf[zdf.month.isin(months)]

    by_lead = (
        zdf.groupby("lead_day")
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

    top_states = zdf.groupby("region_v2")["bust_precip_categorical"].mean().sort_values(ascending=False).head(3)
    return {
        "id": zone_id,
        "name": ZONE_META[zone_id]["name"],
        "season": season,
        "requestedLeadDay": lead_day,
        "cycle": cycle,
        "errorProgression": error_progression,
        "dominantBustModes": [
            f"{state}: {rate:.1%} historical IMD-category bust rate" for state, rate in top_states.items()
        ],
        "nSamplesTotal": int(len(zdf)),
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
    from . import registry
    from .api import _analog_index, _engine
    from . import explain as explain_module
    from ..phase5.features import _train_period_mean_wind

    zone_id = _resolve_zone_id(region_id)
    df = _reference()
    init_time = _latest_real_init_time(df, lead_day)
    snapshot = df[(df.init_time == init_time) & (df.lead_day == lead_day) & (df.zone == zone_id)]
    if snapshot.empty:
        raise HTTPException(status_code=404, detail=f"no real grid points fall in zone {zone_id!r}")
    clon, clat = ZONE_META[zone_id]["centroid"]
    rep = snapshot.assign(_d=((snapshot.latitude - clat) ** 2 + (snapshot.longitude - clon) ** 2)).sort_values("_d").iloc[0]

    engine = _engine()
    row, region_v2 = engine.feature_row_for_explanation(
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

    factors = []
    for f in result["top_features"]:
        factors.append({
            "factorId": f"model-{f['feature']}",
            "name": f["feature"].replace("_", " ").title(),
            "plainReason": f["feature"].replace("_", " "),
            "description": f"Model feature contribution for {f['feature']} (real SHAP value, rain_v1).",
            "source": "model_output",
            "contribution": round(float(f["contribution"]), 4),
            "shapValue": round(float(f["contribution"]), 4),
            "direction": "positive_risk" if f["direction"] == "increases_bust_probability" else "negative_risk",
            "severity": "high" if abs(f["contribution"]) > 0.2 else ("elevated" if abs(f["contribution"]) > 0.1 else "low"),
            "evidenceValue": f"value={f['value']}",
            "tooltip": "Real LightGBM/SHAP feature contribution - see docs/production_inference.md.",
        })
    for a in analog_result.analogs:
        factors.append({
            "factorId": f"analog-{a.rank}",
            "name": f"Historical Analog #{a.rank} ({a.region}, {pd.Timestamp(a.historical_valid_time).date()})",
            "plainReason": f"Similar past forecast in {a.region} realized {a.actual_precip_mm:.1f}mm vs {a.forecast_precip_mm:.1f}mm forecast",
            "description": (
                f"Retrieved historical analog (similarity={a.similarity:.3f}, real ERA5-verified "
                f"outcome) - evidence, not proof; similarity does not guarantee a similar outcome."
            ),
            "source": "historical_context",
            "contribution": None,
            "shapValue": None,
            "direction": "positive_risk" if a.actual_precip_mm > a.forecast_precip_mm else "negative_risk",
            "severity": "elevated",
            "evidenceValue": f"forecast={a.forecast_precip_mm:.1f}mm, actual={a.actual_precip_mm:.1f}mm",
            "tooltip": "Real Phase 5 analog retrieval - never a fabricated case.",
        })

    return {
        "cycle": cycle,
        "leadDay": lead_day,
        "region": ZONE_META[zone_id]["shortName"],
        "bulletinSummary": (
            result["human_readable_reasons"][0] if result["human_readable_reasons"]
            else f"Model evidence and {len(analog_result.analogs)} historical analog(s) retrieved for {ZONE_META[zone_id]['shortName']} at Day {lead_day}."
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
        df = df[df.zone == _resolve_zone_id(region_id)]

    group_cols = ["zone", "lead_day"]
    out = []
    for (zid, ld), g in df.groupby(group_cols, observed=True):
        if zid not in ZONE_META:
            continue
        record = {
            "region": ZONE_META[zid]["shortName"],
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
        if variable == "all" or variable == "precipitation":
            out.append(record)
        elif variable == "temperature":
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
    # the same (init_time is NOT fixed here - valid_time is; different
    # lead_days for the same valid_time come from different init_times) -
    # so we instead show the real trajectory across lead_day using the
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
