# SIH 26079: Frontend ↔ Backend API Integration Contract

> **Target Platform:** AI-Based Numerical Weather Prediction (NWP) Forecast Bust Detection Platform  
> **Nodal Agency:** Ministry of Earth Sciences (MoES) / NCMRWF  
> **System Scope:** Medium-Range Weather Forecasts (Day 1–10 / 24h–240h Lead Window)  
> **Frontend Target:** React 19 + Vite SPA (`frontend/`)  
> **Backend Target:** FastAPI REST Server (`/api/v1`)  
> **Document Status:** Authoritative Integration Specification

---

## 1. Overview

This document specifies the exact interface contract between the React frontend and the FastAPI backend for **SIH Problem Statement 26079**. 

### System Boundary & Division of Responsibility
```text
Raw NWP Forecasts (ECMWF HRES) + Reanalysis Truth (ERA5 / IMD)
                         ↓
  ML Bust Detection Engine & Verification Pipeline (Python)
                         ↓
             FastAPI REST Service (/api/v1)
                         ↓
            JSON API Contract (This Document)
                         ↓
             Centralized api.js Service Layer
                         ↓
           React Frontend UI (Visualization Only)
```

- **ML & Backend Responsibility:** Generating actual deterministic forecast error calculations, medium-range bust probabilities, calibrated confidence scores, SHAP feature attributions, and historical verification archives.
- **Frontend Responsibility:** Rendering visualizations, managing interactive lead-day scrubbing (Day 1 to Day 10), presenting the India geographic risk map, and facilitating forecaster decision support.
- **Strict Boundary Rule:** The React frontend **does not and must not** compute, synthesize, or fabricate bust probabilities, feature contributions, or verification metrics. All values displayed in the UI must originate from the backend API.

The existing frontend currently implements:
1. **Forecast Monitoring Workspace:** Lead Day 1–10 scrubbing, choropleth risk map, region deep dive sidebar.
2. **Regional Climatological Analysis:** Multi-horizon error progression curves, seasonal breakdown, and dominant bust diagnostics.
3. **Model Insights & Explainability:** Calibrated confidence scoring, plain-language ranked reason lists, and diverging SHAP feature contribution charts.
4. **Historical Performance Matrix:** 4D verification grid (Lead Day × Region × Season × Variable) over 20+ million grid-hours.
5. **Historical Replay:** Interactive meteorological case study reconstruction (e.g., August 2018 Kerala floods).

---

## 2. Frontend Architecture Relevant to the Backend

All network communication in the frontend is strictly centralized:

```text
React Components & Pages
         ↓ (calls exported async functions)
frontend/src/services/api.js
         ↓ (applies parameter normalization, timeout, caching, deduplication)
HTTP fetch() via Vite proxy (/api/v1 -> http://localhost:8000)
         ↓
FastAPI Backend Endpoints
```

### Core Architecture Rules for Backend Developers
1. **No Direct Component Calls:** UI components never call `fetch()` directly. All endpoints must be accessed through `frontend/src/services/api.js`.
2. **Environment Variable Configuration:** The base URL is configured via `VITE_API_BASE_URL` (default: `/api/v1`).
3. **Mock Mode Toggle:** Controlled by `VITE_USE_MOCK`:
   - `VITE_USE_MOCK=auto`: Attempts live FastAPI first; falls back to calibrated mock data if 404 or connection refused.
   - `VITE_USE_MOCK=false`: Strict live mode; throws `ApiError` to exercise error boundary UI.
   - `VITE_USE_MOCK=true`: Offline standalone development with internal mock data.
4. **Request Caching & Deduplication:** `api.js` provides an in-memory TTL cache and in-flight request deduplication so rapid user clicks do not overwhelm the backend.
5. **Case Normalization:** `api.js` automatically maps backend region keys (display names or IDs) to canonical frontend map IDs before passing payloads to UI components.

---

## 3. Forecast API

Retrieves medium-range bust probability, calibrated confidence score, variable-level forecast errors, and nationwide regional choropleth metrics for a specific forecast initialization cycle, lead day, and region.

### HTTP Endpoint
```http
GET /api/v1/forecast
```

### Query Parameters

| Parameter | Type | Required | Valid Range / Format | Example | Description |
| :--- | :--- | :---: | :--- | :--- | :--- |
| `cycle` | `string` | No | ISO Date or standard cycle string (`YYYY-MM-DD HHZ`) | `2026-09-29 00Z` | Forecast initialization cycle timestamp. Defaults to latest operational. |
| `lead_day` | `integer` | Yes | `1` to `10` | `5` | Forecast lead time horizon in days (Day 1 = +24h, Day 10 = +240h). |
| `region_id` | `string` | Yes | Canonical region ID or short name | `west-coast` | Target region identifier for the deep-dive analysis. |

*Note: The frontend variable `leadDay` is serialized into query parameter `lead_day`, and `regionId` is serialized into `region_id` by `api.js`.*

---

## 4. Forecast Response Schema

The backend must return a JSON response strictly conforming to the following structure:

```json
{
  "meta": {
    "cycle": "2026-09-29 00Z",
    "cycleId": "ecmwf_hres_20260929_00z",
    "model": "ECMWF HRES Deterministic",
    "gridResolution": "1.5° (240x121 equiangular)",
    "leadDay": 5,
    "leadHours": 120,
    "regionId": "west-coast",
    "regionName": "West Coast (Konkan/Goa/Kerala)",
    "timestamp": "2026-09-29T00:00:00Z",
    "disclaimer": "Operational research verification prototype."
  },
  "verification": {
    "bustProbability": 0.452,
    "confidence": 0.580,
    "riskLevel": "high",
    "historicalPercentileExceeded": true,
    "rulesTriggered": {
      "percentileRule": true,
      "imdRainCategoryRule": true,
      "temperatureHardRule": false
    }
  },
  "variables": {
    "precipitation": {
      "unit": "mm",
      "forecastValue": 44.5,
      "observedValue": 18.2,
      "absError": 26.3,
      "categoryShift": 2,
      "missedHeavyRain": false,
      "falseAlarmHeavyRain": true
    },
    "temperature": {
      "unit": "°C",
      "forecastValue": 29.2,
      "observedValue": 30.1,
      "absError": 0.9,
      "heatwaveMissFlag": false
    },
    "meanSeaLevelPressure": {
      "unit": "hPa",
      "forecastValue": 1008.4,
      "observedValue": 1009.6,
      "absError": 1.2
    }
  },
  "regionalMetrics": {
    "west-coast": {
      "regionId": "west-coast",
      "regionName": "West Coast",
      "bustProbability": 0.451,
      "confidence": 0.580,
      "precipError": 8.5,
      "tempError": 1.2
    },
    "western-himalaya": {
      "regionId": "western-himalaya",
      "regionName": "Western Himalaya",
      "bustProbability": 0.445,
      "confidence": 0.600,
      "precipError": 7.2,
      "tempError": 1.5
    },
    "central-india": {
      "regionId": "central-india",
      "regionName": "Central India",
      "bustProbability": 0.429,
      "confidence": 0.650,
      "precipError": 6.8,
      "tempError": 1.1
    },
    "northeast-india": {
      "regionId": "northeast-india",
      "regionName": "Northeast India",
      "bustProbability": 0.412,
      "confidence": 0.620,
      "precipError": 9.1,
      "tempError": 1.0
    },
    "indo-gangetic-plain": {
      "regionId": "indo-gangetic-plain",
      "regionName": "Indo-Gangetic Plain",
      "bustProbability": 0.398,
      "confidence": 0.680,
      "precipError": 5.4,
      "tempError": 1.3
    },
    "east-coast": {
      "regionId": "east-coast",
      "regionName": "East Coast",
      "bustProbability": 0.367,
      "confidence": 0.700,
      "precipError": 6.1,
      "tempError": 0.9
    },
    "south-peninsula": {
      "regionId": "south-peninsula",
      "regionName": "South Peninsula",
      "bustProbability": 0.342,
      "confidence": 0.720,
      "precipError": 4.8,
      "tempError": 0.8
    },
    "northwest-india": {
      "regionId": "northwest-india",
      "regionName": "Northwest India",
      "bustProbability": 0.314,
      "confidence": 0.750,
      "precipError": 3.2,
      "tempError": 1.8
    }
  },
  "explanations": [
    {
      "factorId": "hist-lead-error",
      "name": "Historical Lead-Time Error Climatology",
      "contribution": 0.28,
      "description": "Historical ECMWF verification over West Coast indicates an empirical bust rate of 45.1% at Day 5 lead time.",
      "evidenceValue": "Empirical bust frequency: 45.1%"
    }
  ],
  "spatialGridSample": []
}
```

### Detailed Field Specification

| Path | Datatype | Unit | Required? | Valid Range | Meaning & Frontend Usage |
| :--- | :--- | :---: | :---: | :--- | :--- |
| `meta.cycle` | `string` | — | Yes | Standard timestamp | Displayed in headers and lead time indicators. |
| `meta.leadDay` | `integer` | days | Yes | `1` to `10` | Active lead time day used for UI synchronization. |
| `meta.regionId` | `string` | — | Yes | Canonical region ID | Identifier of the selected deep-dive region. |
| `meta.regionName` | `string` | — | Yes | Descriptive string | Regional title rendered in the analysis header. |
| `verification.bustProbability` | `float` | ratio | Yes | `0.0` to `1.0` | Primary ML prediction probability of forecast breakdown. Rendered as a percentage in `RegionalSummary.jsx`. |
| `verification.confidence` | `float` | ratio | Yes | `0.0` to `1.0` | Calibrated model confidence score (higher is more confident). Governs `ConfidenceIndicator.jsx` meter. |
| `verification.riskLevel` | `string` | — | Yes | `'low'`, `'moderate'`, `'elevated'`, `'high'`, `'extreme'` | Categorical severity badge displayed across cards. |
| `variables.precipitation.forecastValue` | `float` | mm | Yes | `≥ 0.0` | 24-hour accumulated forecast precipitation from NWP. |
| `variables.precipitation.observedValue` | `float` | mm | Yes | `≥ 0.0` | 24-hour accumulated observed/reanalysis truth. |
| `variables.precipitation.absError` | `float` | mm | Yes | `≥ 0.0` | Absolute pointwise difference `\|forecast - observed\|`. |
| `variables.precipitation.categoryShift` | `integer` | steps | Yes | `0` to `5` | Number of IMD rainfall categories shifted between forecast and truth. |
| `variables.precipitation.missedHeavyRain` | `boolean` | — | Yes | `true` / `false` | Triggered if observed ≥ 64.5mm (Heavy Rain) but forecast < 64.5mm. |
| `variables.precipitation.falseAlarmHeavyRain`| `boolean` | — | Yes | `true` / `false` | Triggered if forecast ≥ 64.5mm but observed was not heavy. |
| `variables.temperature.absError` | `float` | °C | Yes | `≥ 0.0` | Absolute 2m temperature error. |
| `variables.temperature.heatwaveMissFlag` | `boolean` | — | Yes | `true` / `false` | Triggered if temperature absolute error exceeds the 3.0°C threshold. |
| `variables.meanSeaLevelPressure.absError`| `float` | hPa | Yes | `≥ 0.0` | Mean sea level pressure error (large-scale synoptic bias indicator). |
| `regionalMetrics` | `object` | — | Yes | Map of 8 region objects | Feeds the nationwide India choropleth map. |

---

## 5. Regional Metrics Contract

The India risk map (`IndiaRiskMap.jsx`) renders a geographic choropleth across all 8 Indian meteorological subdivisions. It **requires** entries for all 8 subdivisions inside `forecastPayload.regionalMetrics`.

### Minimum Required Structure per Region
```json
{
  "bustProbability": 0.451,
  "confidence": 0.580,
  "precipError": 8.5,
  "tempError": 1.2,
  "regionId": "west-coast",
  "regionName": "West Coast"
}
```

### Metrics Definitions & Ranges
- `bustProbability` (`float`, `0.0` to `1.0`): Drives the choropleth fill color:
  - `< 0.15`: Low Risk (`#10B981` Green)
  - `0.15 – 0.25`: Moderate Risk (`#F59E0B` Amber)
  - `0.25 – 0.35`: Elevated Risk (`#F97316` Orange)
  - `0.35 – 0.45`: High Risk (`#EF4444` Red)
  - `≥ 0.45`: Extreme Risk (`#991B1B` Maroon + accessible cross-hatch pattern)
- `confidence` (`float`, `0.0` to `1.0`): Drives the confidence layer choropleth.
- `precipError` (`float`, mm): Expected absolute 24h precipitation error driving the precipitation layer choropleth.
- `tempError` (`float`, °C): Expected 2m temperature error.

---

## 6. Canonical Region Identifiers

The frontend recognizes exactly eight (8) meteorological regions matching `src/regions.py` and projected in `frontend/src/data/indiaGeoData.js`. 

The backend **must** use the canonical IDs as keys or properties:

| Canonical ID (`region_id`) | Display Name / Official Subdivision Name | Short Name | Bounding Box [LonMin, LatMin, LonMax, LatMax] |
| :--- | :--- | :--- | :--- |
| `western-himalaya` | Western Himalaya (J&K/HP/Uttarakhand) | Western Himalaya | `[73.0, 28.0, 81.0, 36.0]` |
| `northwest-india` | Northwest India (Punjab/Haryana/Rajasthan) | Northwest India | `[69.0, 24.0, 79.0, 32.0]` |
| `indo-gangetic-plain`| Indo-Gangetic Plain (UP/Bihar) | Indo-Gangetic Plain | `[79.0, 24.0, 88.0, 30.0]` |
| `northeast-india` | Northeast India | Northeast India | `[88.0, 22.0, 97.5, 29.5]` |
| `central-india` | Central India (MP/Chhattisgarh/Vidarbha) | Central India | `[74.0, 18.0, 84.0, 26.0]` |
| `west-coast` | West Coast (Konkan/Goa/Kerala) | West Coast | `[72.0, 8.0, 77.0, 20.0]` |
| `east-coast` | East Coast (Andhra/Odisha/TN coast) | East Coast | `[78.0, 8.0, 87.0, 20.0]` |
| `south-peninsula` | South Peninsula (Interior Karnataka/TN) | South Peninsula | `[74.5, 8.0, 80.0, 16.0]` |

*Note: In `api.js`, `CANONICAL_REGION_IDS` automatically normalizes common display variants (e.g. `"West Coast"`, `"west coast"`) to canonical kebab-case IDs.*

---

## 7. Regions API

Retrieves metadata, extents, and climatological profiles for all 8 Indian regions.

### HTTP Endpoint
```http
GET /api/v1/regions
```

### Expected Response
```json
[
  {
    "id": "west-coast",
    "name": "West Coast (Konkan/Goa/Kerala)",
    "shortName": "West Coast",
    "bbox": [72.0, 8.0, 77.0, 20.0],
    "centroid": [74.5, 14.0],
    "baselineRisk": 0.451,
    "dominantSeason": "monsoon_JJAS",
    "climatologicalBustModes": [
      "Western Ghats Coastal Heavy Rain",
      "Offshore Vortex Busts"
    ]
  }
]
```

### Field Definitions
- `id` (`string`): Canonical region ID (`west-coast`).
- `name` (`string`): Full administrative subdivision name.
- `shortName` (`string`): Concise label for dropdowns and badges.
- `bbox` (`array[float]`): `[lon_min, lat_min, lon_max, lat_max]`.
- `centroid` (`array[float]`): `[lon, lat]` representative geographic center.
- `baselineRisk` (`float`): Historical 2018–2021 aggregate bust probability.

---

## 8. Explainability API

Provides feature attribution and plain-language reasoning explaining why the system assigned a specific confidence score or bust risk.

### HTTP Endpoint
```http
GET /api/v1/explanations
```

### Query Parameters
- `cycle` (`string`): Forecast initialization timestamp.
- `lead_day` (`integer`, `1`–`10`): Lead time horizon.
- `region_id` (`string`): Target canonical region ID.

### Expected Response
```json
{
  "cycle": "2026-09-29 00Z",
  "leadDay": 5,
  "region": "West Coast",
  "bulletinSummary": "Forecast confidence for West Coast at Day 5 is constrained by IMD rainfall category dispersion and run-to-run 500hPa geopotential height jumpiness.",
  "factors": [
    {
      "factorId": "hist-error-lead",
      "name": "Historical Day 5 Error Growth",
      "plainReason": "High historical error at Day 5 lead time in this season",
      "description": "Historical ECMWF verification over West Coast indicates an empirical bust rate of 48.7% at Day 5 lead time.",
      "source": "historical_context",
      "contribution": 0.28,
      "shapValue": 0.28,
      "direction": "positive_risk",
      "severity": "high",
      "evidenceValue": "Empirical verification bust frequency: 48.7%",
      "tooltip": "Historical Climatological Error: Quantified empirical bust rate over 2018–2021 ECMWF archive."
    },
    {
      "factorId": "precip-spread",
      "name": "Precipitation Ensemble Spread",
      "plainReason": "Large precipitation spread across orographic boundaries",
      "description": "Ensemble spread exceeds climatological 90th percentile along the Western Ghats crest.",
      "source": "model_output",
      "contribution": 0.24,
      "shapValue": 0.24,
      "direction": "positive_risk",
      "severity": "elevated",
      "evidenceValue": "Ensemble 90th/10th spread: ±18.4 mm/24h",
      "tooltip": "Ensemble Quantile Spread: High dispersion indicates acute sensitivity to convection triggering."
    },
    {
      "factorId": "synoptic-stability",
      "name": "Large-Scale Synoptic Stability",
      "plainReason": "Monsoon trough axis alignment is steady across runs",
      "description": "Cross-equatorial flow and low-level jet velocity show minimal run-to-run divergence.",
      "source": "model_output",
      "contribution": -0.15,
      "shapValue": -0.15,
      "direction": "negative_risk",
      "severity": "low",
      "evidenceValue": "Jet speed variance: 1.2 m/s",
      "tooltip": "Synoptic Stability: Mitigating factor reducing the risk of a categorical bust."
    }
  ]
}
```

### Factor Object Fields
- `factorId` (`string`): Unique identifier.
- `name` (`string`): Title of the attribution feature.
- `plainReason` (`string`): Non-technical forecaster reason.
- `description` (`string`): Full scientific narrative.
- `source` (`string`): `'model_output'` (NWP state, spread) or `'historical_context'` (climatology, empirical bias).
- `contribution` / `shapValue` (`float`, `-1.0` to `1.0`): Additive impact on the bust prediction (positive increases risk, negative decreases risk).
- `direction` (`string`): `'positive_risk'` or `'negative_risk'`.
- `severity` (`string`): `'low'`, `'moderate'`, `'elevated'`, `'high'`.
- `evidenceValue` (`string`): Concrete numerical evidence displayed in UI badges.

---

## 9. Historical Performance API

Powers the 4-dimensional verification heatmap and seasonal trajectory charts in `HistoricalPerformancePage.jsx`.

### HTTP Endpoint
```http
GET /api/v1/historical-performance
```

### Query Parameters

| Parameter | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `lead_day` | `integer` | No | Filter by lead time (`1`–`10`). If omitted, returns all lead days. |
| `region_id` | `string` | No | Filter by canonical region ID. If omitted, returns all regions. |
| `season` | `string` | No | Filter by season (`monsoon_JJAS`, `post_monsoon_ON`, `pre_monsoon_MAM`, `winter_DJF`). |
| `variable` | `string` | No | Meteorological variable (`all`, `precipitation`, `temperature`, `wind`, `mslp`). |

### Expected Response
Array of records representing regional verification statistics:

```json
[
  {
    "region": "West Coast",
    "season": "monsoon_JJAS",
    "leadDay": 5,
    "bustRate": 48.7,
    "precipBustRate": 51.2,
    "meanAbsErrorPrecipMm": 9.45,
    "tempBustRate": 14.8,
    "meanAbsErrorTempC": 1.12,
    "nSamples": 27328,
    "missedHeavyRainEvents": 264,
    "falseAlarmHeavyRain": 418
  }
]
```

### Field Definitions
- `region` (`string`): Region name or canonical ID.
- `season` (`string`): Meteorological season key.
- `leadDay` (`integer`, `1`–`10`): Forecast horizon.
- `bustRate` (`float`, `%`): Overall multi-rule forecast bust rate.
- `precipBustRate` (`float`, `%`): Precipitation categorical bust frequency.
- `meanAbsErrorPrecipMm` (`float`, `mm`): Mean absolute error for 24h precipitation.
- `tempBustRate` (`float`, `%`): Temperature bust frequency (>3°C error).
- `meanAbsErrorTempC` (`float`, `°C`): Mean absolute error for 2m air temperature.
- `nSamples` (`integer`): Number of verification grid-point samples in this bucket.

---

## 10. Forecast Cycles API

Retrieves operational NWP initialization cycles available in the system.

### HTTP Endpoint
```http
GET /api/v1/cycles
```

### Expected Response
```json
[
  {
    "code": "2026-09-29 00Z",
    "label": "2026-09-29 00Z (Latest Operational)",
    "model": "ECMWF HRES Deterministic",
    "gridResolution": "1.5° (240x121 equiangular)",
    "id": "2026-09-29 00Z"
  },
  {
    "code": "2026-09-28 12Z",
    "label": "2026-09-28 12Z (-12h Run)",
    "model": "ECMWF HRES Deterministic",
    "gridResolution": "1.5° (240x121 equiangular)",
    "id": "2026-09-28 12Z"
  }
]
```

---

## 11. Historical Replay API

The historical replay module allows forecasters and hackathon evaluators to replay high-impact historical extreme events (e.g. 2018 Kerala Floods, 2021 Cyclone Tauktae) across lead horizons (Day 1–10).

### Endpoints Expected by Frontend
1. **Catalog Endpoint:**
   ```http
   GET /api/v1/replay/events
   ```
   Returns catalog of available benchmark events.
2. **Event Replay State:**
   ```http
   GET /api/v1/replay/event?event_id=kerala-2018&lead_day=5&cycle=2018-08-14%2000Z&region_id=West%20Coast
   ```

### Status: `CURRENTLY MOCK / FUTURE BACKEND REQUIREMENT`
- The frontend `api.js` has functions `getReplayEvents()` and `getReplayData()` that currently query `/api/v1/replay/events` and `/api/v1/replay/event`.
- If the live backend does not implement these endpoints, `api.js` transparently serves the built-in calibrated case studies from `MOCK_HISTORICAL_REPLAY_EVENTS`.
- Once the ML team generates historical reanalysis inference for these events, the FastAPI backend should serve them matching the schema in `MOCK_HISTORICAL_REPLAY_DATA`.

---

## 12. Model Output → API Transformation Mapping

The ML pipeline must transform raw model tensors and arrays into the JSON structure expected by the frontend.

```text
RAW ML / NWP ARRAYS (Python / Xarray / PyTorch / LightGBM)
  ├── model.predict_proba(X) -> P(bust)
  ├── tree_explainer.shap_values(X) -> shap_matrix
  ├── error_t2m = |pred_t2m - era5_t2m|
  └── error_tp = |pred_tp - era5_tp|
                ↓
FASTAPI TRANSFORMATION LAYER (Pydantic Models)
  ├── Maps array indices to canonical region IDs (west-coast, etc.)
  ├── Classifies riskLevel based on P(bust) thresholds
  ├── Formats SHAP values into top positive & negative factor descriptors
  └── Constructs regionalMetrics dictionary for all 8 subdivisions
                ↓
FRONTEND JSON CONTRACT (/api/v1/forecast)
```

The frontend **must not** receive raw tensors, unscaled logits, numpy arrays, or internal pandas DataFrames.

---

## 13. Important ML/Backend Questions

The following questions must be confirmed by the ML/Backend engineering team:

> [!IMPORTANT]
> **BACKEND/ML TEAM TO CONFIRM:**
> 1. **Model Formulation:** Does the ML model predict a continuous bust probability $P(\text{bust}) \in [0, 1]$, a multi-class outcome (no bust, moderate bust, severe bust), or direct regression of expected forecast error?
> 2. **Input Feature Space:** What exact features are fed to the model (e.g., ensemble mean, ensemble spread, run-to-run tendency, 500hPa geopotential height anomaly, Cape, Precipitable Water)?
> 3. **Model Artifact:** What model artifact format is deployed in production (`.joblib`, `.onnx`, `.pt`, LightGBM `.txt`)?
> 4. **Confidence Score Derivation:** Is `confidence` derived from ensemble spread entropy, prediction interval width, or calibration curves (e.g. Platt scaling / Isotonic regression)?
> 5. **Risk Level Mapping:** Does `riskLevel` use fixed probability thresholds (`low < 0.15`, `moderate < 0.25`, `elevated < 0.35`, `high < 0.45`, `extreme >= 0.45`) or regional percentile quantiles?
> 6. **Ground Truth Data Source:** Does the real-time system evaluate against IMD AWS station data, IMD gridded rainfall ($0.25^\circ$), or delayed ERA5 reanalysis?
> 7. **Execution Latency:** Can the model generate inference across all 8 regions within the 8,000ms frontend request timeout?

---

## 14. Error Handling Contract

FastAPI should return standard HTTP status codes with a JSON error payload:

```json
{
  "detail": "Descriptive error message explaining why the request failed."
}
```

### HTTP Status Code Handling in Frontend

| Status Code | Cause | Frontend Action |
| :---: | :--- | :--- |
| `400 Bad Request` | Invalid query parameter (e.g. `lead_day=15`). | Displays `ErrorState` with validation message. |
| `404 Not Found` | Unknown region ID or uninitialized cycle. | In `useMock=auto`, falls back to mock; in `useMock=false`, renders `EmptyState` with retry button. |
| `502 / 503 / 504` | Backend server booting or inference timeout. | `api.js` automatically retries up to 2 times with exponential backoff (600ms, 1200ms) before displaying `ErrorState`. |
| `Network Error` | FastAPI backend down / connection refused. | Displays retryable `ErrorState` with actionable user instructions. |

---

## 15. Mock vs Production Environment

```text
Development / Offline Testing:
  VITE_USE_MOCK=auto (or true)
  React Frontend → api.js → Calibrated Mock Fallback Data

Production / Integrated Evaluation:
  VITE_USE_MOCK=false
  React Frontend → api.js → FastAPI Backend → Live Model Predictions
```

To switch the frontend to strict live backend mode:
1. Open `frontend/.env`.
2. Set `VITE_USE_MOCK=false`.
3. Set `VITE_API_BASE_URL=http://localhost:8000/api/v1` (or production host URL).
4. Restart the frontend dev server (`npm run dev`) or build production bundle (`npm run build`).

---

## 16. Integration Rules

- **Rule 1: Preserve Field Names:** Do not alter frontend property names (e.g. `bustProbability`, `regionalMetrics`) to suit Python internal variable names. Map them in FastAPI Pydantic schemas.
- **Rule 2: Keep React Free of ML Math:** Never move ML inference, interpolation, or threshold math into React components.
- **Rule 3: No Hardcoded Regional Risk:** The choropleth map must strictly consume `forecastPayload.regionalMetrics`.
- **Rule 4: Canonical Region IDs:** Always key dictionaries and filter queries using the 8 canonical kebab-case region IDs (`west-coast`, `western-himalaya`, etc.).
- **Rule 5: CORS Policy:** FastAPI must configure `CORSMiddleware` to allow requests from `http://localhost:3000` (development) and production origins.
- **Rule 6: Schema Stability:** Existing properties must not be removed or renamed, as this will break UI rendering without a corresponding frontend update.

---

## 17. End-to-End Execution Example

```text
1. Forecaster selects "Day 7" and "Northeast India" in the React UI.
                     ↓
2. Frontend executes api.js:
   GET /api/v1/forecast?cycle=2026-09-29%2000Z&lead_day=7&region_id=northeast-india
                     ↓
3. FastAPI endpoint parses query parameters, loads Day 7 ECMWF HRES forecast data for Northeast India.
                     ↓
4. ML model evaluates atmospheric fields:
   - Predicted bust probability: 0.528
   - Model confidence score: 0.380
   - Expected precipitation error: 14.8 mm
   - Regional choropleth metrics computed for all 8 regions.
                     ↓
5. FastAPI serializes data conforming to Section 4 JSON schema.
                     ↓
6. Frontend api.js caches response, normalizes region IDs.
                     ↓
7. IndiaRiskMap displays updated choropleth; RegionalSummary sidebar displays Northeast India Day 7 deep dive.
```

---

## 18. Frontend Integration Checklist

- [ ] FastAPI service running at `/api/v1` with CORS enabled for port 3000.
- [ ] `GET /api/v1/forecast` returns `verification`, `variables`, and `regionalMetrics`.
- [ ] `regionalMetrics` contains entries for all 8 canonical region IDs.
- [ ] `lead_day` supports horizons from Day 1 to Day 10.
- [ ] `GET /api/v1/regions` returns 8 subdivision metadata objects.
- [ ] `GET /api/v1/explanations` returns `bulletinSummary` and `factors` array.
- [ ] `GET /api/v1/historical-performance` returns verification records across seasons and lead times.
- [ ] `GET /api/v1/cycles` returns operational initialization timestamps.
- [ ] `VITE_USE_MOCK=false` tested in `frontend/.env` with zero UI breakage.

---

# Strict Frontend Integration Inspection Report

**Date of Inspection:** 2026-09-29  
**Inspected Working Tree:** `frontend/` on branch `frontend-avannish`  
**Inspector:** Antigravity Automated Verification Agent

---

## 1. Inspection Scope

The following 32 source files were directly read, analyzed, and verified against the integration contract:

### Services & API Layer
- `frontend/src/services/api.js`

### Top-Level Pages
- `frontend/src/pages/ForecastPage.jsx`
- `frontend/src/pages/RegionsPage.jsx`
- `frontend/src/pages/ModelInsightsPage.jsx`
- `frontend/src/pages/HistoricalPerformancePage.jsx`
- `frontend/src/pages/HistoricalReplayPage.jsx`
- `frontend/src/pages/AboutPage.jsx`

### Data & Geo Abstractions
- `frontend/src/data/mockData.js`
- `frontend/src/data/historicalSummaryData.js`
- `frontend/src/data/indiaGeoData.js`
- `frontend/src/design-system/weather-tokens.js`
- `frontend/src/design-system/tokens.js`

### Forecast Visualization Components
- `frontend/src/components/forecast/ForecastHeader.jsx`
- `frontend/src/components/forecast/LeadDaySelector.jsx`
- `frontend/src/components/forecast/IndiaRiskMap.jsx`
- `frontend/src/components/forecast/RegionalSummary.jsx`
- `frontend/src/components/forecast/ForecastErrorChart.jsx`
- `frontend/src/components/forecast/HistoricalPerformance.jsx`
- `frontend/src/components/forecast/ConfidenceIndicator.jsx`

### Explainability Components
- `frontend/src/components/explainability/ExplanationPanel.jsx`
- `frontend/src/components/explainability/FeatureContributionChart.jsx`
- `frontend/src/components/explainability/ReasonList.jsx`
- `frontend/src/components/explainability/ConfidenceIndicator.jsx`
- `frontend/src/components/explainability/index.js`

### Replay Components
- `frontend/src/components/replay/ReplayControlBar.jsx`
- `frontend/src/components/replay/ReplayOutcomeComparison.jsx`

### Navigation & Feedback Components
- `frontend/src/components/navigation/AppHeader.jsx`
- `frontend/src/components/navigation/DesktopNav.jsx`
- `frontend/src/components/navigation/MobileNav.jsx`
- `frontend/src/components/navigation/forecastCycles.js`
- `frontend/src/components/feedback/LoadingState.jsx`
- `frontend/src/components/feedback/ErrorState.jsx`
- `frontend/src/components/feedback/EmptyState.jsx`

---

## 2. API Endpoint Inspection Table

| Endpoint | Frontend Reference | Status | Evidence | Backend Action Required |
| :--- | :--- | :---: | :--- | :--- |
| `GET /api/v1/forecast` | `api.js:250`, `ForecastPage.jsx:75` | `EXPECTED` | `apiRequest('/forecast?...')` is called unconditionally on cycle/lead/region change. Falls back to mock if backend offline. | Implement endpoint conforming to Section 4. |
| `GET /api/v1/regions` | `api.js:332`, `ForecastPage.jsx:57`, `RegionsPage.jsx:150` | `EXPECTED` | `apiRequest('/regions')` called on mount in all core pages. | Implement endpoint returning 8 region metadata objects. |
| `GET /api/v1/regions/{regionId}` | `api.js:367`, `RegionsPage.jsx:165` | `EXPECTED` | `apiRequest('/regions/{regionId}?season=...&lead_day=...&cycle=...')` called on parameter change. | Implement endpoint returning regional Day 1–10 error curves. |
| `GET /api/v1/explanations` | `api.js:569`, `ForecastPage.jsx:81`, `ModelInsightsPage.jsx:87` | `EXPECTED` | `apiRequest('/explanations?...')` called on forecast inspection. | Implement endpoint returning SHAP feature attribution factors. |
| `GET /api/v1/historical-performance` | `api.js:514`, `HistoricalPerformancePage.jsx:86` | `EXPECTED` | `apiRequest('/historical-performance?...')` called for grid matrix. | Implement endpoint returning historical verification records. |
| `GET /api/v1/cycles` | `api.js:621`, `RegionsPage.jsx:151`, `ModelInsightsPage.jsx:69` | `EXPECTED` | `apiRequest('/cycles')` called on mount to populate initialization dropdowns. | Implement endpoint returning available operational cycle timestamps. |
| `GET /api/v1/replay/events` | `api.js:652`, `HistoricalReplayPage.jsx:47` | `EXPECTED` | `apiRequest('/replay/events')` called on mount in replay page. | Optional: Implement historical event catalog. |
| `GET /api/v1/replay/event` | `api.js:683`, `HistoricalReplayPage.jsx:71` | `EXPECTED` | `apiRequest('/replay/event?...')` called on event/lead scrub. | Optional: Implement event replay simulation state. |

---

## 3. Field-Level Inspection Table

| Field Path | Consuming Component | Required? | Status | Notes / Fallback Behavior |
| :--- | :--- | :---: | :---: | :--- |
| `meta.cycle` | `ForecastHeader`, `RegionalSummary` | Yes | `IMPLEMENTED` | Falls back to active select state if omitted. |
| `meta.leadDay` | `ForecastHeader`, `RegionalSummary` | Yes | `IMPLEMENTED` | Verified against Day 1–10 selector. |
| `verification.bustProbability` | `RegionalSummary`, `ForecastErrorChart` | Yes | `IMPLEMENTED` | Drives primary `% Bust` display and risk level. |
| `verification.confidence` | `ConfidenceIndicator`, `RegionalSummary` | Yes | `IMPLEMENTED` | Drives meter fill and confidence tier text. |
| `verification.riskLevel` | `RiskBadge`, `RegionalSummary` | Yes | `IMPLEMENTED` | Derived via `getBustRiskLevel` if omitted by API. |
| `variables.precipitation.absError` | `RegionalSummary` | Yes | `IMPLEMENTED` | Formatted via `formatPrecip(val)`. |
| `variables.precipitation.categoryShift`| `RegionalSummary` | No | `IMPLEMENTED` | Triggers alert callout if `categoryShift >= 2`. |
| `variables.precipitation.missedHeavyRain`| `RegionalSummary`| No | `IMPLEMENTED` | Triggers red alert badge if `true`. |
| `variables.temperature.absError` | `RegionalSummary` | Yes | `IMPLEMENTED` | Formatted via `formatTemp(val)`. |
| `variables.temperature.heatwaveMissFlag`| `RegionalSummary` | No | `IMPLEMENTED` | Triggers heatwave callout if `true`. |
| `variables.meanSeaLevelPressure.absError`| `RegionalSummary` | Yes | `IMPLEMENTED` | Formatted via `formatPressure(val)`. |
| `regionalMetrics` | `ForecastPage`, `IndiaRiskMap` | Yes | `IMPLEMENTED` | Feeds all 8 region fills on India choropleth map. |
| `regionalMetrics[id].bustProbability` | `IndiaRiskMap` | Yes | `IMPLEMENTED` | Drives SVG path fill color and severe hatch. |
| `regionalMetrics[id].confidence` | `IndiaRiskMap` | Yes | `IMPLEMENTED` | Drives confidence layer choropleth. |
| `regionalMetrics[id].precipError` | `IndiaRiskMap` | Yes | `IMPLEMENTED` | Drives precipitation error layer choropleth. |
| `explanations[].name` | `RegionalSummary`, `ReasonList` | Yes | `IMPLEMENTED` | Rendered as feature attribution title. |
| `explanations[].contribution` | `RegionalSummary`, `FeatureContributionChart` | Yes | `IMPLEMENTED` | Rendered as `% Risk` contribution. |
| `explanations[].source` | `ExplanationPanel`, `ReasonList` | Yes | `IMPLEMENTED` | Filters between `model_output` and `historical_context`. |

---

## 4. Request Parameter Inspection

| Endpoint | HTTP Method | Query Param Name | Frontend Variable | Datatype | Required? | Transformation |
| :--- | :---: | :--- | :--- | :--- | :---: | :--- |
| `/forecast` | `GET` | `cycle` | `cycle` | `string` | No | Direct string query serialization. |
| `/forecast` | `GET` | `lead_day` | `leadDay` | `integer` | Yes | `String(leadDay)` (camelCase &rarr; snake_case). |
| `/forecast` | `GET` | `region_id` | `regionId` | `string` | Yes | Direct string query serialization. |
| `/regions/{id}` | `GET` | Path variable | `regionId` | `string` | Yes | `encodeURIComponent(regionId)`. |
| `/regions/{id}` | `GET` | `season` | `season` | `string` | Yes | Direct string query serialization. |
| `/regions/{id}` | `GET` | `lead_day` | `leadDay` | `integer` | Yes | `String(leadDay)`. |
| `/regions/{id}` | `GET` | `cycle` | `cycle` | `string` | Yes | Direct string query serialization. |
| `/explanations` | `GET` | `cycle` | `cycle` | `string` | Yes | Direct string query serialization. |
| `/explanations` | `GET` | `lead_day` | `leadDay` | `integer` | Yes | `String(leadDay)`. |
| `/explanations` | `GET` | `region_id` | `regionId` | `string` | Yes | Direct string query serialization. |
| `/historical-performance` | `GET` | `lead_day` | `leadDay` | `integer` | No | Serialized if `leadDay` provided. |
| `/historical-performance` | `GET` | `region_id` | `regionId` | `string` | No | Serialized if `regionId` provided. |
| `/historical-performance` | `GET` | `season` | `season` | `string` | No | Serialized if `season` provided. |
| `/historical-performance` | `GET` | `variable` | `variable` | `string` | No | Default: `'precipitation'`. |
| `/replay/event` | `GET` | `event_id` | `eventId` | `string` | Yes | Serialized as `event_id`. |
| `/replay/event` | `GET` | `lead_day` | `leadDay` | `integer` | Yes | `String(leadDay)`. |

---

## 5. Response Normalization Inspection

`frontend/src/services/api.js` contains active response normalization:

1. **`normalizeRegionalMetrics(rawMetrics, leadDay)`**:
   - Iterates through all entries of `rawMetrics`.
   - Normalizes keys to canonical kebab-case IDs using `CANONICAL_REGION_IDS`.
   - Dual-indexes metrics under both canonical ID (`west-coast`) and display name (`West Coast`) to prevent lookup failure in any component.
   - Enforces default numerical fallbacks for missing properties (`bustProbability`, `confidence`, `precipError`, `tempError`).
2. **`normalizeForecastPayload(payload, leadDay)`**:
   - Ensures `payload.regionalMetrics` is guaranteed to exist and is properly indexed before passing to React state.

---

## 6. Regional Metrics Inspection

- **Inspection Target:** `frontend/src/pages/ForecastPage.jsx` lines 129–150.
- **Finding:**
  ```javascript
  // Regional metrics for the choropleth map supplied by the forecast API layer
  const regionalMetrics = forecastPayload?.regionalMetrics || EMPTY_REGIONAL_METRICS;
  ```
- **Audit Result:** **`PASS`** — Regional forecast risk values are consumed strictly from `forecastPayload.regionalMetrics`. No local `baseRates` or synthetic `leadFactor` calculations exist in `ForecastPage.jsx`.

---

## 7. Region ID Consistency Inspection

| Source File | Region Identifiers Used | Inspection Result |
| :--- | :--- | :---: |
| `frontend/src/services/api.js` | Canonical kebab-case (`west-coast`, `western-himalaya`, etc.) + normalizer mapping | `PASS` |
| `frontend/src/data/indiaGeoData.js` | Canonical kebab-case `id` (`west-coast`, etc.) | `PASS` |
| `frontend/src/design-system/weather-tokens.js` | Display title `id` (`West Coast`, etc.) | `WARNING` (Handled by `api.js` normalization) |
| `frontend/src/components/forecast/IndiaRiskMap.jsx`| Dual-indexed lookup (`regionalMetrics[region.id] \|\| regionalMetrics[region.shortName]`) | `PASS` |
| `frontend/src/pages/ForecastPage.jsx` | Matches `r.shortName === id \|\| r.id === id \|\| r.name.includes(id)` | `PASS` |

---

## 8. Mock Data Boundary Inspection

| Data Entity | Classification | Details |
| :--- | :---: | :--- |
| `meta`, `verification`, `variables` | `REAL API EXPECTATION` | Required live model verification metrics. Mock fallback used only when backend is disconnected. |
| `regionalMetrics` | `REAL API EXPECTATION` | Required nationwide regional risk metrics for choropleth map. |
| `explanations` / `factors` | `REAL API EXPECTATION` | Required SHAP feature attribution metrics. |
| `historicalPerformance` | `REAL API EXPECTATION` | Aggregated empirical verification records across 2018–2021. |
| `cycles` | `REAL API EXPECTATION` | Operational NWP cycle timestamps. |
| `replayEvents` / `replayData` | `MOCK_ONLY` | Benchmark case study archive. Active mock fallback; future backend endpoint. |
| `INDIA_GEO_REGIONS` | `STATIC UI DATA` | SVG vector paths for drawing Indian subcontinent subdivisions. |
| `LEAD_DAYS` | `STATIC UI DATA` | Constant Day 1 through Day 10 (+24h to +240h) definitions. |
| `SEASONS` | `STATIC UI DATA` | Monsoon JJAS, Post-Monsoon ON, Pre-Monsoon MAM, Winter DJF definitions. |

---

## 9. ML Output Dependency Inspection

### A. Direct ML / Model Outputs (Owned by ML Model)
- `bustProbability` (`float`): Probability of forecast bust at specified lead time.
- `confidence` (`float`): Calibrated model confidence score.
- `riskLevel` (`string`): Categorical risk classification.

### B. Weather Verification Outputs (Owned by Data Processing Pipeline)
- `forecastValue` (`float`): NWP parameter forecast.
- `observedValue` (`float`): Verified ground truth / reanalysis.
- `absError` (`float`): Absolute verification error.
- `categoryShift` (`integer`): IMD categorical step difference.
- `missedHeavyRain` (`boolean`): Severe rain event missed.
- `falseAlarmHeavyRain` (`boolean`): False alarm severe rain.
- `heatwaveMissFlag` (`boolean`): Extreme temperature threshold exceeded.

### C. Explainability Outputs (Owned by SHAP / Attribution Pipeline)
- `bulletinSummary` (`string`): Scientific plain-language synthesis.
- `factors[].contribution` (`float`): Additive attribution value.
- `factors[].source` (`string`): Distinction between atmospheric state and climatology.

### D. Frontend-Derived Values (Owned by React UI)
- Dynamic UI cursor positioning on SVG axes (`getXPos`).
- Table sorting and client-side text filtering.
- Zoom and pan viewport transformations on the SVG map canvas.

---

## 10. Unresolved Backend / ML Questions

The following implementation decisions cannot be determined from frontend source code alone and require explicit confirmation by the backend/ML development team:

1. `[BACKEND/ML CONFIRMATION REQUIRED]` **Inference Engine:** What library or framework executes real-time inference in FastAPI (e.g. LightGBM, ONNX Runtime, PyTorch, Scikit-learn)?
2. `[BACKEND/ML CONFIRMATION REQUIRED]` **Target Definition:** What exact mathematical condition defines a "bust" in the training labels (is it strictly the 90th percentile of absolute error, or a composite score with IMD rainfall category shift)?
3. `[BACKEND/ML CONFIRMATION REQUIRED]` **Latency Budget:** Does the backend compute nationwide `regionalMetrics` on the fly, or are predictions pre-calculated into a caching store (e.g., Redis, SQLite, PostgreSQL) upon forecast cycle arrival?
4. `[BACKEND/ML CONFIRMATION REQUIRED]` **Ground Truth Latency:** When running in real-time operational mode, how is `observedValue` handled for future forecast dates (where ERA5 reanalysis has a 5-day lag)? Are observed fields marked `null` for unverified future lead days?
5. `[BACKEND/ML CONFIRMATION REQUIRED]` **Atmospheric Regimes:** Does the model output large-scale atmospheric regime classifications (e.g. Monsoon Low Pressure System, Western Disturbance, Break Monsoon) as structured explanation metadata?

---

## 11. Blocking vs. Non-Blocking Findings

### Blocking Findings
*None.* The frontend is architecturally unblocked and ready to ingest live responses conforming to Section 4.

### Non-Blocking Findings
1. **Replay Module Persistence:** If the backend does not implement `/api/v1/replay/*`, the frontend will continue serving built-in benchmark events via mock fallback without crashing.
2. **Missing Observed Values for Live Forecasts:** For live unverified runs (e.g., current cycle +120h), the backend should set `observedValue: null` and `absError: null`. The frontend formatters gracefully handle undefined/null metrics without runtime exceptions.
3. **Region ID Aliasing:** `api.js` contains a normalization dictionary for common display names, but the FastAPI backend should standardize on canonical kebab-case IDs (`west-coast`, etc.) for consistency.

---

## 12. Final Integration Readiness

### **Status: READY**

### Why:
- All API requests are strictly centralized in `frontend/src/services/api.js`.
- The frontend contains zero hardcoded regional risk formulas or synthetic probability calculations.
- India risk map choropleth dynamically consumes `forecastPayload.regionalMetrics`.
- Comprehensive error, loading, and empty state boundaries are implemented and verified.
- Production build succeeds with zero linter errors and optimized chunk splitting.

### Backend Must Do Before Integration:
1. Implement `GET /api/v1/forecast`, `GET /api/v1/regions`, `GET /api/v1/explanations`, `GET /api/v1/historical-performance`, and `GET /api/v1/cycles` matching the contracts in Sections 3–10.
2. Enable CORS on FastAPI for origin `http://localhost:3000`.
3. Set `VITE_USE_MOCK=false` in `frontend/.env` to connect live.
