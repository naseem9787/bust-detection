/**
 * Mock Data Architecture for SIH 26079 ML API
 * AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts
 *
 * NOTE: This mock data provides realistic, strongly-typed JavaScript structures
 * that mirror the planned FastAPI backend endpoints.
 * DISCLAIMER: This data is synthetic and designed for frontend architecture testing;
 * it must NOT be interpreted as live meteorological advisories.
 */

export const DATA_DISCLAIMER =
  'SYNTHETIC_BENCHMARK_DATA: Designed for SIH 26079 UI/API integration testing. Reflects ECMWF HRES / ERA5 1.5° WeatherBench2 schemas.';

// 1. Forecast Cycles
export const MOCK_CYCLES = [
  {
    id: '2026-09-29T00:00:00Z',
    code: '2026-09-29 00Z',
    label: '2026-09-29 00Z (Latest Operational)',
    model: 'ECMWF HRES Deterministic',
    truthBaseline: 'ERA5 Reanalysis',
    gridResolution: '1.5° equiangular (240x121)',
    status: 'completed',
    generatedAt: '2026-09-29T01:00:00Z',
    isSynthetic: true,
  },
  {
    id: '2026-09-28T12:00:00Z',
    code: '2026-09-28 12Z',
    label: '2026-09-28 12Z (-12h Run)',
    model: 'ECMWF HRES Deterministic',
    truthBaseline: 'ERA5 Reanalysis',
    gridResolution: '1.5° equiangular (240x121)',
    status: 'completed',
    generatedAt: '2026-09-28T13:00:00Z',
    isSynthetic: true,
  },
  {
    id: '2026-09-28T00:00:00Z',
    code: '2026-09-28 00Z',
    label: '2026-09-28 00Z (-24h Run)',
    model: 'ECMWF HRES Deterministic',
    truthBaseline: 'ERA5 Reanalysis',
    gridResolution: '1.5° equiangular (240x121)',
    status: 'completed',
    generatedAt: '2026-09-28T01:00:00Z',
    isSynthetic: true,
  },
  {
    id: '2018-08-14T00:00:00Z',
    code: '2018-08-14 00Z',
    label: '2018-08-14 00Z (Kerala Flood Case Study)',
    model: 'ECMWF HRES Deterministic',
    truthBaseline: 'ERA5 Reanalysis',
    gridResolution: '1.5° equiangular (240x121)',
    status: 'archived',
    generatedAt: '2018-08-14T01:00:00Z',
    isSynthetic: true,
  },
];

// 2. Regions (directly aligned with src/regions.py)
export const MOCK_REGIONS = [
  {
    id: 'western-himalaya',
    name: 'Western Himalaya (J&K/HP/Uttarakhand)',
    shortName: 'Western Himalaya',
    bbox: { latMin: 28.0, latMax: 36.0, lonMin: 73.0, lonMax: 81.0 },
    centroid: { lat: 32.0, lon: 77.0 },
    climatologicalBustModes: ['Western Disturbances', 'Orographic Freezing Level'],
    baselineRisk: 0.445,
    dominantSeason: 'winter_DJF',
  },
  {
    id: 'northwest-india',
    name: 'Northwest India (Punjab/Haryana/Rajasthan)',
    shortName: 'Northwest India',
    bbox: { latMin: 24.0, latMax: 32.0, lonMin: 69.0, lonMax: 79.0 },
    centroid: { lat: 28.0, lon: 74.0 },
    climatologicalBustModes: ['Heat Waves (>3.0°C)', 'Convective Dust Storms'],
    baselineRisk: 0.314,
    dominantSeason: 'pre_monsoon_MAM',
  },
  {
    id: 'indo-gangetic-plain',
    name: 'Indo-Gangetic Plain (UP/Bihar)',
    shortName: 'Indo-Gangetic Plain',
    bbox: { latMin: 24.0, latMax: 30.0, lonMin: 79.0, lonMax: 88.0 },
    centroid: { lat: 27.0, lon: 83.5 },
    climatologicalBustModes: ['Monsoon Trough Displacement', 'Winter Inversion Fog'],
    baselineRisk: 0.398,
    dominantSeason: 'monsoon_JJAS',
  },
  {
    id: 'northeast-india',
    name: 'Northeast India',
    shortName: 'Northeast India',
    bbox: { latMin: 22.0, latMax: 29.5, lonMin: 88.0, lonMax: 97.5 },
    centroid: { lat: 25.75, lon: 92.75 },
    climatologicalBustModes: ['Extreme Rainfall Underestimation (>115.6mm)', 'Terrain Funneling'],
    baselineRisk: 0.412,
    dominantSeason: 'monsoon_JJAS',
  },
  {
    id: 'central-india',
    name: 'Central India (MP/Chhattisgarh/Vidarbha)',
    shortName: 'Central India',
    bbox: { latMin: 18.0, latMax: 26.0, lonMin: 74.0, lonMax: 84.0 },
    centroid: { lat: 22.0, lon: 79.0 },
    climatologicalBustModes: ['Monsoon Low Pressure Systems (LPS)', 'Depression Track Bias'],
    baselineRisk: 0.429,
    dominantSeason: 'monsoon_JJAS',
  },
  {
    id: 'west-coast',
    name: 'West Coast (Konkan/Goa/Kerala)',
    shortName: 'West Coast',
    bbox: { latMin: 8.0, latMax: 20.0, lonMin: 72.0, lonMax: 77.0 },
    centroid: { lat: 14.0, lon: 74.5 },
    climatologicalBustModes: ['Western Ghats Coastal Heavy Rain', 'Offshore Vortex Busts'],
    baselineRisk: 0.451,
    dominantSeason: 'monsoon_JJAS',
  },
  {
    id: 'east-coast',
    name: 'East Coast (Andhra/Odisha/TN coast)',
    shortName: 'East Coast',
    bbox: { latMin: 8.0, latMax: 20.0, lonMin: 78.0, lonMax: 87.0 },
    centroid: { lat: 14.0, lon: 82.5 },
    climatologicalBustModes: ['Post-Monsoon Cyclones & Landfall Timing', 'Coastal Wind Shear'],
    baselineRisk: 0.367,
    dominantSeason: 'post_monsoon_ON',
  },
  {
    id: 'south-peninsula',
    name: 'South Peninsula (Interior Karnataka/TN)',
    shortName: 'South Peninsula',
    bbox: { latMin: 8.0, latMax: 16.0, lonMin: 74.5, lonMax: 80.0 },
    centroid: { lat: 12.0, lon: 77.25 },
    climatologicalBustModes: ['Rain-Shadow Convective Deficits', 'Inter-Seasonal Dry Spells'],
    baselineRisk: 0.342,
    dominantSeason: 'pre_monsoon_MAM',
  },
];

import { HISTORICAL_SUMMARY_DATABASE } from './historicalSummaryData.js';

// 3. Historical Summary Baseline Dataset (from 2018–2021 database in data/processed/summary_by_region_lead_season.csv)
export const MOCK_HISTORICAL_PERFORMANCE = HISTORICAL_SUMMARY_DATABASE;

// Specific explanation generator answering the 5 key factors required by forecasters
export function getRegionalExplanationFactors({
  regionId = 'west-coast',
  leadDay = 5,
  cycle = '2026-09-29 00Z',
  regionName = 'West Coast',
} = {}) {
  // Climatological reference bust rate at this lead
  const rec = HISTORICAL_SUMMARY_DATABASE.find(
    (r) => r.region.toLowerCase().includes(regionName.toLowerCase()) && r.leadDay === Number(leadDay) && r.season === 'monsoon_JJAS'
  );
  const leadBustRate = rec ? rec.bustRate : Number((32.0 + leadDay * 2.1).toFixed(1));

  // Regional synoptic regime map
  const REGION_REGIMES = {
    'west-coast': {
      regime: 'Western Ghats Orographic & Offshore Vortex Forcing',
      evidence: 'Low-level moisture convergence: 14.8 m/s westerly jet',
      spread: 'IMD category spread: 2 tiers (Moderate vs Very Heavy)',
    },
    'western-himalaya': {
      regime: 'Western Disturbance Mid-Latitude Trough & Terrain Funneling',
      evidence: 'Freezing level descent: 420m below seasonal mean',
      spread: 'Orographic precipitation boundary shift: +35mm',
    },
    'central-india': {
      regime: 'Monsoon Low Pressure System (LPS) Track Displacement',
      evidence: 'Trough tilt: 2.1° south of normal axis',
      spread: 'Depression core rainfall corridor spread: 120km',
    },
    'northwest-india': {
      regime: 'Boundary Layer Dry Inversion & Convective Dust Trigger',
      evidence: 'Surface heating anomaly: +3.2°C above climatology',
      spread: '2m temperature forecast spread: ±2.8°C',
    },
    'indo-gangetic-plain': {
      regime: 'Monsoon Trough Oscillation & Boundary Boundary Shear',
      evidence: 'Trough axis oscillation: 1.8° northward displacement',
      spread: 'Rainfall category jumpiness: Moderate to Heavy',
    },
    'northeast-india': {
      regime: 'Bay of Bengal Moisture Inflow & Orographic Funneling',
      evidence: 'Precipitable water anomaly: +18mm above normal',
      spread: 'Extreme rainfall underprediction risk (>115.6mm)',
    },
    'east-coast': {
      regime: 'Coastal Boundary Layer Convergence & Depression Landfall',
      evidence: 'Coastal wind shear anomaly: 18 knots',
      spread: 'Landfall precipitation distribution spread: 45mm',
    },
    'south-peninsula': {
      regime: 'Rain-Shadow Convective Trigger & Western Ghats Lee Wave',
      evidence: 'Convective Available Potential Energy (CAPE): 2,400 J/kg',
      spread: 'Convective cell initiation timing variance: ±3 hours',
    },
  };

  const regInfo = REGION_REGIMES[regionId] || REGION_REGIMES['west-coast'];

  return [
    {
      factorId: 'historical_lead_error',
      name: 'High Historical Error at Lead Time',
      plainReason: 'Forecast error compounding at Day 5: historical models miss observed values 36.7% of the time at this lead.',
      source: 'historical_context',
      sourceLabel: 'Historical Context',
      category: 'climatological_baseline',
      direction: 'positive_risk',
      shapValue: Number((0.26 + (leadDay > 5 ? 0.06 : 0)).toFixed(2)),
      contribution: Number((0.26 + (leadDay > 5 ? 0.06 : 0)).toFixed(2)),
      severity: leadDay >= 6 ? 'high' : leadDay >= 3 ? 'elevated' : 'moderate',
      description: `Historical verification shows Day ${leadDay} has an empirical bust rate of ${leadBustRate}% in the 2018–2021 database. Error compounding with lead time establishes this as a primary statistical constraint.`,
      evidenceValue: `Empirical bust rate: ${leadBustRate}%`,
      technicalTerm: 'Climatological Error Growth',
      tooltip: 'Atmospheric predictability diminishes with lead time. Empirical verification over 2018–2021 establishes the historical baseline error rate for this specific horizon.',
    },
    {
      factorId: 'precipitation_uncertainty',
      name: 'Large Precipitation Category Uncertainty',
      plainReason: 'Ensemble members disagree on rainfall amount, crossing the boundary from moderate rain into severe downpour.',
      source: 'model_output',
      sourceLabel: 'Model Output',
      category: 'precipitation_dispersion',
      direction: 'positive_risk',
      shapValue: 0.24,
      contribution: 0.24,
      severity: 'high',
      description: `Model ensemble exhibits elevated dispersion across IMD categorical boundaries. Small shifts in sub-grid parameterization push the forecast across the heavy-rain threshold (>64.5mm).`,
      evidenceValue: regInfo.spread,
      technicalTerm: 'IMD Rain Category Shift',
      tooltip: 'India Meteorological Department (IMD) classifies rainfall into 6 standardized tiers. Shifts across 2 or more tiers represent major operational forecast discrepancies.',
    },
    {
      factorId: 'past_analogue_matches',
      name: 'Past-Analogue Pattern Mispredictions',
      plainReason: 'Weather maps from past years that looked similar to this setup frequently resulted in major forecast busts.',
      source: 'historical_context',
      sourceLabel: 'Historical Context',
      category: 'historical_analogue',
      direction: 'positive_risk',
      shapValue: 0.18,
      contribution: 0.18,
      severity: 'elevated',
      description: `Top FAISS vector analogues matching this synoptic pattern (e.g. August 2018 active monsoon surge) experienced a 44.2% historical bust rate under similar moisture inflow.`,
      evidenceValue: 'FAISS L2 distance: 0.38',
      technicalTerm: 'FAISS Vector Analogue Match',
      tooltip: 'Facebook AI Similarity Search (FAISS) compresses high-dimensional weather fields into spatial vectors to instantly locate the closest historical meteorological twins.',
    },
    {
      factorId: 'model_disagreement',
      name: 'Multi-Model & Ensemble Spread',
      plainReason: 'Individual ensemble members predict different storm tracks and rain center locations across the region.',
      source: 'model_output',
      sourceLabel: 'Model Output',
      category: 'ensemble_spread',
      direction: 'positive_risk',
      shapValue: 0.15,
      contribution: 0.15,
      severity: 'elevated',
      description: `Variance among ensemble members regarding convective trigger timing and spatial moisture accumulation over surrounding 1.5° grid cells.`,
      evidenceValue: `Ensemble standard deviation: ±16.2 mm`,
      technicalTerm: 'Ensemble Spread',
      tooltip: 'Standard deviation across 50 perturbed ensemble forecasts. High spread signifies elevated atmospheric sensitivity and rapid error growth.',
    },
    {
      factorId: 'run_to_run_changes',
      name: 'Run-to-Run Consistency (500hPa Jumpiness)',
      plainReason: 'The new model forecast shifted noticeably compared to the previous run 12 hours ago, indicating volatility.',
      source: 'model_output',
      sourceLabel: 'Model Output',
      category: 'synoptic_jumpiness',
      direction: 'positive_risk',
      shapValue: 0.12,
      contribution: 0.12,
      severity: 'moderate',
      description: `500hPa geopotential height contours show a 38 gpm shift compared to the previous operational run (${cycle.replace('00Z', '12Z')}), signaling circulation volatility.`,
      evidenceValue: '500hPa shift: 38 gpm',
      technicalTerm: '500hPa Geopotential Jumpiness',
      tooltip: 'Measures steering flow consistency at ~5,500m altitude between successive 12-hour NWP initialization cycles. High jumpiness indicates circulation instability.',
    },
    {
      factorId: 'atmospheric_regime',
      name: 'Atmospheric Regime Indicator',
      plainReason: `Active regional weather regime (${regInfo.regime}) creates non-linear convective triggers.`,
      source: 'model_output',
      sourceLabel: 'Model Output',
      category: 'synoptic_forcing',
      direction: 'positive_risk',
      shapValue: 0.10,
      contribution: 0.10,
      severity: 'moderate',
      description: `Active ${regInfo.regime} dominant over the sub-basin. Synoptic-scale forcing couples non-linearly with localized microphysics.`,
      evidenceValue: regInfo.evidence,
      technicalTerm: 'Synoptic Circulation Regime',
      tooltip: 'Large-scale meteorological pattern (e.g. Monsoon Trough, Western Disturbance) dictating moisture transport and regional convective vulnerability.',
    },
    {
      factorId: 'boundary_layer_stability',
      name: 'Stable Surface Boundary Pressure Field',
      plainReason: 'Barometric pressure across surrounding sea-level stations is well-aligned with observations, stabilizing the forecast.',
      source: 'model_output',
      sourceLabel: 'Model Output',
      category: 'stabilizing_dynamics',
      direction: 'negative_risk',
      shapValue: -0.11,
      contribution: -0.11,
      severity: 'favorable',
      description: `Mean sea-level pressure gradient is well-captured by ECMWF deterministic core (bias < 0.8 hPa), mitigating synoptic-scale position drift.`,
      evidenceValue: 'MSLP error: 0.8 hPa (Favorable)',
      technicalTerm: 'MSLP Gradient Stability',
      tooltip: 'A well-modeled surface pressure field reduces large-scale circulation error propagation and provides an anchoring constraint for the forecast.',
    },
    {
      factorId: 'seasonal_climatology_anchor',
      name: 'Climatological Moisture Baseline Consistency',
      plainReason: 'Total atmospheric moisture content matches seasonal norms for this time of year, ruling out extreme moisture spikes.',
      source: 'historical_context',
      sourceLabel: 'Historical Context',
      category: 'climatological_anchor',
      direction: 'negative_risk',
      shapValue: -0.07,
      contribution: -0.07,
      severity: 'favorable',
      description: `Precipitable water anomaly remains within 1.0 standard deviation of the 30-year climatological mean, preventing runaway moisture bias.`,
      evidenceValue: 'Anomaly: +3.2 mm (Within normal bounds)',
      technicalTerm: 'Precipitable Water Anomaly',
      tooltip: 'Depth of water in a column of the atmosphere if all water vapor were condensed. Normal values correlate with predictable background moisture transport.',
    },
  ];
}

// 4. Model Explanation & Attribution Factors
export const MOCK_EXPLANATION_FACTORS = {
  default: [
    {
      factorId: 'imd_categorical_spread',
      name: 'IMD Rain Category Shift',
      category: 'precipitation_scale',
      contribution: 0.28,
      direction: 'positive_bust_risk',
      severity: 'high',
      description: 'Model forecasts moderate rainfall (28mm), but ensemble dispersion points to heavy rain (>65mm).',
      evidenceValue: 'Spread gap: 2 categories',
    },
    {
      factorId: 'synoptic_flow_jumpiness',
      name: '500hPa Geopotential Jumpiness',
      category: 'synoptic_pattern',
      contribution: 0.21,
      direction: 'positive_bust_risk',
      severity: 'elevated',
      description: 'Run-to-run inconsistency of geopotential height contour across surrounding grid cells.',
      evidenceValue: 'Divergence: 42 gpm',
    },
    {
      factorId: 'monsoon_trough_position',
      name: 'Monsoon Trough Alignment',
      category: 'climatological_regime',
      contribution: 0.16,
      direction: 'positive_bust_risk',
      severity: 'moderate',
      description: 'Trough axis oscillates south of normal position, historically inflating Day 4–7 error variance.',
      evidenceValue: 'Axis tilt: 2.4° southward',
    },
    {
      factorId: 'past_analogue_match',
      name: 'Past-Analogue Error Signature',
      category: 'historical_analogue',
      contribution: 0.14,
      direction: 'positive_bust_risk',
      severity: 'moderate',
      description: 'Top-3 FAISS vector analogues (e.g. Aug-2018 event) experienced 46% underprediction rate.',
      evidenceValue: 'FAISS L2 distance: 0.38',
    },
  ],
};

// 5. Representative Spatial 1.5° Grid Points (India domain: 8°N–36°N, 68°E–96°E)
export const MOCK_SPATIAL_GRID = [
  { lat: 9.5, lon: 76.5, region: 'West Coast', bustProb: 0.52, confidence: 0.38, risk: 'extreme', precipMm: 84.5, tempC: 28.2 },
  { lat: 12.5, lon: 75.0, region: 'West Coast', bustProb: 0.48, confidence: 0.42, risk: 'extreme', precipMm: 92.0, tempC: 27.8 },
  { lat: 15.5, lon: 73.8, region: 'West Coast', bustProb: 0.44, confidence: 0.48, risk: 'high', precipMm: 68.2, tempC: 28.5 },
  { lat: 18.5, lon: 73.0, region: 'West Coast', bustProb: 0.41, confidence: 0.52, risk: 'high', precipMm: 54.0, tempC: 29.1 },
  { lat: 13.0, lon: 80.2, region: 'East Coast', bustProb: 0.31, confidence: 0.65, risk: 'elevated', precipMm: 12.4, tempC: 31.4 },
  { lat: 17.7, lon: 83.3, region: 'East Coast', bustProb: 0.34, confidence: 0.61, risk: 'elevated', precipMm: 18.0, tempC: 30.8 },
  { lat: 20.3, lon: 85.8, region: 'East Coast', bustProb: 0.38, confidence: 0.57, risk: 'high', precipMm: 36.5, tempC: 30.2 },
  { lat: 21.1, lon: 79.1, region: 'Central India', bustProb: 0.42, confidence: 0.53, risk: 'high', precipMm: 42.0, tempC: 31.5 },
  { lat: 23.2, lon: 77.4, region: 'Central India', bustProb: 0.39, confidence: 0.58, risk: 'high', precipMm: 28.5, tempC: 32.0 },
  { lat: 26.8, lon: 80.9, region: 'Indo-Gangetic Plain', bustProb: 0.38, confidence: 0.60, risk: 'high', precipMm: 22.0, tempC: 32.8 },
  { lat: 25.6, lon: 85.1, region: 'Indo-Gangetic Plain', bustProb: 0.40, confidence: 0.56, risk: 'high', precipMm: 31.2, tempC: 31.9 },
  { lat: 26.1, lon: 91.7, region: 'Northeast India', bustProb: 0.43, confidence: 0.52, risk: 'high', precipMm: 74.0, tempC: 28.4 },
  { lat: 27.0, lon: 75.8, region: 'Northwest India', bustProb: 0.29, confidence: 0.68, risk: 'elevated', precipMm: 4.5, tempC: 38.6 },
  { lat: 30.7, lon: 76.8, region: 'Northwest India', bustProb: 0.32, confidence: 0.64, risk: 'elevated', precipMm: 8.2, tempC: 36.2 },
  { lat: 32.2, lon: 76.3, region: 'Western Himalaya', bustProb: 0.45, confidence: 0.49, risk: 'extreme', precipMm: 34.0, tempC: 18.5 },
  { lat: 34.1, lon: 74.8, region: 'Western Himalaya', bustProb: 0.47, confidence: 0.45, risk: 'extreme', precipMm: 26.0, tempC: 14.2 },
  { lat: 12.9, lon: 77.6, region: 'South Peninsula', bustProb: 0.28, confidence: 0.72, risk: 'elevated', precipMm: 6.8, tempC: 27.4 },
];

/**
 * Generates a realistic mock forecast payload for any (cycle, leadDay, regionId)
 */
export function generateMockForecastResponse({ cycle = '2026-09-29 00Z', leadDay = 5, regionId = 'west-coast' } = {}) {
  const region = MOCK_REGIONS.find((r) => r.id === regionId || r.shortName === regionId) || MOCK_REGIONS[5];
  const cycleObj = MOCK_CYCLES.find((c) => c.code === cycle || c.id === cycle) || MOCK_CYCLES[0];

  // Realistic error growth curve: errors increase with lead time
  const baseRate = region.baselineRisk * 100;
  const leadDayFactor = (leadDay - 1) * 3.4;
  const bustProbability = Math.min(0.68, (baseRate + leadDayFactor) / 100);
  const confidence = Math.max(0.20, 0.95 - (leadDay * 0.068) - (region.id === 'west-coast' ? 0.05 : 0));

  let riskLevel = 'low';
  if (bustProbability >= 0.45) riskLevel = 'extreme';
  else if (bustProbability >= 0.35) riskLevel = 'high';
  else if (bustProbability >= 0.25) riskLevel = 'elevated';
  else if (bustProbability >= 0.15) riskLevel = 'moderate';

  const precipFcstMm = Number((18.5 + leadDay * 5.2 + (region.id === 'west-coast' ? 24.0 : 0)).toFixed(1));
  const precipObsMm = Number((precipFcstMm * (0.8 + Math.sin(leadDay) * 0.4)).toFixed(1));
  const precipAbsError = Number(Math.abs(precipFcstMm - precipObsMm).toFixed(2));

  const tempFcstC = Number((28.5 + (region.id === 'northwest-india' ? 6.5 : 0)).toFixed(1));
  const tempObsC = Number((tempFcstC + (leadDay * 0.25)).toFixed(1));
  const tempAbsError = Number(Math.abs(tempFcstC - tempObsC).toFixed(2));

  return {
    meta: {
      cycle: cycleObj.code,
      cycleId: cycleObj.id,
      model: cycleObj.model,
      gridResolution: cycleObj.gridResolution,
      leadDay: Number(leadDay),
      leadHours: Number(leadDay) * 24,
      regionId: region.id,
      regionName: region.name,
      disclaimer: DATA_DISCLAIMER,
      timestamp: new Date().toISOString(),
    },
    verification: {
      bustProbability: Number(bustProbability.toFixed(3)),
      confidence: Number(confidence.toFixed(3)),
      riskLevel,
      historicalPercentileExceeded: bustProbability >= 0.38,
      rulesTriggered: {
        percentileRule: bustProbability >= 0.35,
        imdRainCategoryRule: precipAbsError >= 15.0,
        temperatureHardRule: tempAbsError > 3.0,
      },
    },
    variables: {
      precipitation: {
        unit: 'mm',
        forecastValue: precipFcstMm,
        observedValue: precipObsMm,
        absError: precipAbsError,
        categoryShift: precipAbsError > 20.0 ? 2 : 1,
        missedHeavyRain: precipObsMm >= 64.5 && precipFcstMm < 64.5,
        falseAlarmHeavyRain: precipFcstMm >= 64.5 && precipObsMm < 64.5,
      },
      temperature: {
        unit: '°C',
        forecastValue: tempFcstC,
        observedValue: tempObsC,
        absError: tempAbsError,
        heatwaveMissFlag: tempAbsError > 3.0,
      },
      meanSeaLevelPressure: {
        unit: 'hPa',
        forecastValue: 1008.4,
        observedValue: 1009.6,
        absError: 1.2,
      },
    },
    regionalMetrics: Object.fromEntries(
      MOCK_REGIONS.map((r) => {
        const rBase = r.baselineRisk;
        const rLeadGrowth = (leadDay - 1) * 0.024;
        const rProb = Math.min(0.64, Number((rBase + rLeadGrowth).toFixed(3)));
        const rConf = Math.max(0.22, Number((0.94 - leadDay * 0.068 - (r.id === 'west-coast' ? 0.05 : 0)).toFixed(3)));
        const rPrecipErr = Number((3.0 + leadDay * 1.2 + (r.id === 'west-coast' ? 3.5 : 0)).toFixed(1));
        const rTempErr = Number((1.1 + leadDay * 0.15).toFixed(1));

        return [
          r.id,
          {
            regionId: r.id,
            regionName: r.shortName,
            bustProbability: rProb,
            confidence: rConf,
            precipError: rPrecipErr,
            tempError: rTempErr,
          },
        ];
      })
    ),
    explanations: MOCK_EXPLANATION_FACTORS.default,
    spatialGridSample: MOCK_SPATIAL_GRID.filter((pt) => pt.region === region.shortName || Math.random() > 0.5),
  };
}

// ============================================================================
// 10. HISTORICAL REPLAY BENCHMARK EVENTS (SIH 26079)
// Purpose: Allows judges to select known historical weather events and replay
// how the system evaluates forecast bust risk and confidence across lead times.
// NOTE: Clearly marked as benchmark / reanalysis calibration data.
// ============================================================================

export const MOCK_HISTORICAL_REPLAY_EVENTS = [
  {
    id: 'kerala-2018',
    name: '2018 Kerala Monsoon Extreme Flooding',
    shortName: 'Kerala Floods (Aug 2018)',
    dateRange: 'August 14–18, 2018',
    primaryRegionId: 'west-coast',
    primaryRegionName: 'West Coast',
    category: 'Extreme Precipitation & Orographic Runoff',
    synopticType: 'Offshore Trough & Active Monsoon LLJ',
    headline: 'Severe precipitation underestimation along Western Ghats in medium range (Day 4–7).',
    description:
      'During mid-August 2018, an exceptionally strong monsoon low-level jet (LLJ) coupled with an offshore trough produced extreme rainfall over Kerala exceeding 200 mm/day. Global numerical weather prediction (ECMWF) under-forecast the extreme precipitation at 5–7 day lead times, triggering an operational forecast bust.',
    dataQualityBadge: 'DEMO BENCHMARK DATA: Calibrated against IMD AWS observations & ERA5 re-analysis',
    initializations: [
      { id: '2018-08-14 00Z', label: '2018-08-14 00Z (Peak Flooding Run)' },
      { id: '2018-08-12 00Z', label: '2018-08-12 00Z (-48h Warning Window)' },
      { id: '2018-08-10 00Z', label: '2018-08-10 00Z (-96h Medium-Range Window)' },
    ],
    impactSummary: {
      fatalities: '483 reported',
      economicLoss: 'Est. ₹40,000 Crore',
      peakObservedRainfall: '414.0 mm/24h (Peermade station)',
      bustSignificance: 'Forecast underpredicted extreme rainfall threshold by 3 IMD categories at Day 5.',
    },
    observedGroundTruth: {
      precipitationMm: 218.6,
      temperatureC: 25.4,
      mslpHpa: 1006.2,
      imdCategory: 'Extremely Heavy Rain (≥204.5mm)',
    },
    forecastProgression: {
      1: { precipFcst: 182.4, tempFcst: 25.6, bustProb: 0.31, conf: 0.69, risk: 'moderate' },
      2: { precipFcst: 154.0, tempFcst: 26.0, bustProb: 0.44, conf: 0.56, risk: 'elevated' },
      3: { precipFcst: 118.2, tempFcst: 26.3, bustProb: 0.58, conf: 0.42, risk: 'high' },
      4: { precipFcst: 86.5, tempFcst: 26.8, bustProb: 0.72, conf: 0.30, risk: 'high' },
      5: { precipFcst: 58.4, tempFcst: 27.2, bustProb: 0.84, conf: 0.22, risk: 'extreme' },
      6: { precipFcst: 42.0, tempFcst: 27.5, bustProb: 0.88, conf: 0.18, risk: 'extreme' },
      7: { precipFcst: 34.5, tempFcst: 27.9, bustProb: 0.91, conf: 0.15, risk: 'extreme' },
      8: { precipFcst: 28.0, tempFcst: 28.1, bustProb: 0.93, conf: 0.12, risk: 'extreme' },
      9: { precipFcst: 24.2, tempFcst: 28.4, bustProb: 0.94, conf: 0.11, risk: 'extreme' },
      10: { precipFcst: 21.0, tempFcst: 28.6, bustProb: 0.95, conf: 0.10, risk: 'extreme' },
    },
    regionalMultipliers: {
      'West Coast': 1.0,
      'South Peninsula': 0.65,
      'Central India': 0.45,
      'East Coast': 0.35,
      'Northwest India': 0.20,
      'Western Himalayas': 0.15,
      'Northeast India': 0.25,
      'Northern Plains': 0.18,
    },
  },
  {
    id: 'fani-2019',
    name: '2019 Cyclone Fani (Extremely Severe Cyclonic Storm)',
    shortName: 'Cyclone Fani (May 2019)',
    dateRange: 'April 30 – May 4, 2019',
    primaryRegionId: 'east-coast',
    primaryRegionName: 'East Coast',
    category: 'Tropical Cyclogenesis & Coastal Landfall Surge',
    synopticType: 'Bay of Bengal Rapid Intensification',
    headline: 'Pre-monsoon Category 4 equivalent cyclone making landfall near Puri, Odisha.',
    description:
      'Cyclone Fani underwent rapid intensification over warm sea-surface temperatures in the Bay of Bengal. Medium-range numerical guidance at Day 6–8 experienced significant track and intensity dispersion, creating large precipitation and gale-force wind forecast busts in coastal Odisha.',
    dataQualityBadge: 'DEMO BENCHMARK DATA: IMD Best Track Archive & ERA5 Reanalysis',
    initializations: [
      { id: '2019-05-01 00Z', label: '2019-05-01 00Z (Pre-Landfall 48h Run)' },
      { id: '2019-04-29 00Z', label: '2019-04-29 00Z (-96h Track Recurvature Run)' },
      { id: '2019-04-27 00Z', label: '2019-04-27 00Z (-144h Genesis Window)' },
    ],
    impactSummary: {
      fatalities: '89 reported across India & Bangladesh',
      economicLoss: 'Est. ₹24,000 Crore',
      peakObservedRainfall: '198.5 mm/24h (Bhubaneswar station)',
      bustSignificance: 'Day 5 forecast missed landfall coastal precipitation centroid by 180km.',
    },
    observedGroundTruth: {
      precipitationMm: 172.4,
      temperatureC: 27.8,
      mslpHpa: 968.0,
      imdCategory: 'Very Heavy Rain (115.6–204.4mm)',
    },
    forecastProgression: {
      1: { precipFcst: 156.0, tempFcst: 28.0, bustProb: 0.28, conf: 0.72, risk: 'moderate' },
      2: { precipFcst: 138.5, tempFcst: 28.2, bustProb: 0.38, conf: 0.62, risk: 'moderate' },
      3: { precipFcst: 104.2, tempFcst: 28.6, bustProb: 0.52, conf: 0.48, risk: 'elevated' },
      4: { precipFcst: 72.0, tempFcst: 29.0, bustProb: 0.66, conf: 0.36, risk: 'high' },
      5: { precipFcst: 46.5, tempFcst: 29.4, bustProb: 0.79, conf: 0.24, risk: 'extreme' },
      6: { precipFcst: 32.0, tempFcst: 29.8, bustProb: 0.85, conf: 0.20, risk: 'extreme' },
      7: { precipFcst: 22.0, tempFcst: 30.1, bustProb: 0.89, conf: 0.16, risk: 'extreme' },
      8: { precipFcst: 18.0, tempFcst: 30.3, bustProb: 0.91, conf: 0.14, risk: 'extreme' },
      9: { precipFcst: 15.0, tempFcst: 30.5, bustProb: 0.92, conf: 0.12, risk: 'extreme' },
      10: { precipFcst: 12.0, tempFcst: 30.8, bustProb: 0.94, conf: 0.10, risk: 'extreme' },
    },
    regionalMultipliers: {
      'East Coast': 1.0,
      'South Peninsula': 0.55,
      'Northeast India': 0.48,
      'Central India': 0.30,
      'Northern Plains': 0.20,
      'West Coast': 0.18,
      'Northwest India': 0.10,
      'Western Himalayas': 0.08,
    },
  },
  {
    id: 'chamoli-2021',
    name: '2021 Chamoli / Uttarakhand High-Altitude Winter Surge',
    shortName: 'Chamoli Surge (Feb 2021)',
    dateRange: 'February 6–8, 2021',
    primaryRegionId: 'western-himalayas',
    primaryRegionName: 'Western Himalayas',
    category: 'High-Altitude Orographic Avalanche & Thermal Anomaly',
    synopticType: 'Western Disturbance Interaction with Complex Terrain',
    headline: 'Sudden flash surge and steep thermal anomaly in the Rishiganga valley.',
    description:
      'A massive rock and ice detachment triggered a catastrophic surge in Chamoli district. Medium-range numerical models struggled to forecast localized mid-tropospheric warming (+4.8°C anomaly) and convective precip bands in complex Himalayan topography.',
    dataQualityBadge: 'DEMO BENCHMARK DATA: Wadia Institute & NCMRWF Post-Event Analysis',
    initializations: [
      { id: '2021-02-06 00Z', label: '2021-02-06 00Z (Eve of Event Run)' },
      { id: '2021-02-04 00Z', label: '2021-02-04 00Z (-48h Warning Run)' },
      { id: '2021-02-02 00Z', label: '2021-02-02 00Z (-96h Medium-Range Run)' },
    ],
    impactSummary: {
      fatalities: 'Over 200 casualties/missing reported',
      economicLoss: 'Severe infrastructure damage to Tapovan Vishnugad HEP',
      peakObservedRainfall: 'Localized mixed-phase precipitation & 4.8°C thermal jump',
      bustSignificance: 'NWP missed sub-grid temperature anomaly and freezing level displacement.',
    },
    observedGroundTruth: {
      precipitationMm: 48.2,
      temperatureC: 6.8,
      mslpHpa: 1018.4,
      imdCategory: 'Moderate Rain/Snow (15.6–64.4mm)',
    },
    forecastProgression: {
      1: { precipFcst: 41.0, tempFcst: 5.8, bustProb: 0.25, conf: 0.74, risk: 'low' },
      2: { precipFcst: 34.5, tempFcst: 4.8, bustProb: 0.36, conf: 0.64, risk: 'moderate' },
      3: { precipFcst: 26.0, tempFcst: 3.5, bustProb: 0.48, conf: 0.52, risk: 'moderate' },
      4: { precipFcst: 18.2, tempFcst: 2.4, bustProb: 0.62, conf: 0.39, risk: 'high' },
      5: { precipFcst: 12.0, tempFcst: 1.5, bustProb: 0.76, conf: 0.27, risk: 'extreme' },
      6: { precipFcst: 8.5, tempFcst: 0.8, bustProb: 0.82, conf: 0.22, risk: 'extreme' },
      7: { precipFcst: 6.0, tempFcst: 0.2, bustProb: 0.86, conf: 0.18, risk: 'extreme' },
      8: { precipFcst: 4.5, tempFcst: -0.5, bustProb: 0.88, conf: 0.15, risk: 'extreme' },
      9: { precipFcst: 3.2, tempFcst: -1.0, bustProb: 0.90, conf: 0.13, risk: 'extreme' },
      10: { precipFcst: 2.5, tempFcst: -1.4, bustProb: 0.92, conf: 0.11, risk: 'extreme' },
    },
    regionalMultipliers: {
      'Western Himalayas': 1.0,
      'Northern Plains': 0.42,
      'Northwest India': 0.38,
      'Northeast India': 0.22,
      'Central India': 0.15,
      'East Coast': 0.10,
      'South Peninsula': 0.05,
      'West Coast': 0.05,
    },
  },
  {
    id: 'nisarga-2020',
    name: '2020 Cyclone Nisarga (Severe Cyclonic Storm)',
    shortName: 'Cyclone Nisarga (Jun 2020)',
    dateRange: 'June 2–4, 2020',
    primaryRegionId: 'west-coast',
    primaryRegionName: 'West Coast',
    category: 'Arabian Sea Pre-Monsoon Cyclogenesis',
    synopticType: 'Rapid Northward Translation & Landfall Swath',
    headline: 'Rare tropical cyclone making landfall on Maharashtra coastline near Alibag.',
    description:
      'Nisarga formed rapidly in the southeast Arabian Sea. Numerical models exhibited track jumpiness across consecutive cycles, shifting the projected landfall point between South Gujarat and North Maharashtra, causing coastal wind and rain distribution busts.',
    dataQualityBadge: 'DEMO BENCHMARK DATA: IMD Tropical Cyclone Division Verified Archive',
    initializations: [
      { id: '2020-06-02 00Z', label: '2020-06-02 00Z (24h Pre-Landfall Run)' },
      { id: '2020-05-31 00Z', label: '2020-05-31 00Z (-72h Cyclone Genesis Run)' },
      { id: '2020-05-29 00Z', label: '2020-05-29 00Z (-120h Medium-Range Run)' },
    ],
    impactSummary: {
      fatalities: '6 reported; successful evacuation of >100,000 residents',
      economicLoss: 'Est. ₹6,000 Crore',
      peakObservedRainfall: '142.5 mm/24h (Ratnagiri/Alibag swath)',
      bustSignificance: 'Consecutive NWP runs shifted landfall track by 140km (500hPa jumpiness).',
    },
    observedGroundTruth: {
      precipitationMm: 128.0,
      temperatureC: 27.2,
      mslpHpa: 984.0,
      imdCategory: 'Very Heavy Rain (115.6–204.4mm)',
    },
    forecastProgression: {
      1: { precipFcst: 118.0, tempFcst: 27.5, bustProb: 0.29, conf: 0.71, risk: 'moderate' },
      2: { precipFcst: 98.0, tempFcst: 27.8, bustProb: 0.38, conf: 0.62, risk: 'moderate' },
      3: { precipFcst: 72.5, tempFcst: 28.2, bustProb: 0.52, conf: 0.49, risk: 'elevated' },
      4: { precipFcst: 48.0, tempFcst: 28.6, bustProb: 0.67, conf: 0.34, risk: 'high' },
      5: { precipFcst: 32.4, tempFcst: 29.0, bustProb: 0.78, conf: 0.25, risk: 'extreme' },
      6: { precipFcst: 24.0, tempFcst: 29.3, bustProb: 0.83, conf: 0.21, risk: 'extreme' },
      7: { precipFcst: 18.0, tempFcst: 29.5, bustProb: 0.87, conf: 0.17, risk: 'extreme' },
      8: { precipFcst: 14.0, tempFcst: 29.8, bustProb: 0.89, conf: 0.15, risk: 'extreme' },
      9: { precipFcst: 11.0, tempFcst: 30.0, bustProb: 0.91, conf: 0.13, risk: 'extreme' },
      10: { precipFcst: 9.0, tempFcst: 30.2, bustProb: 0.93, conf: 0.11, risk: 'extreme' },
    },
    regionalMultipliers: {
      'West Coast': 1.0,
      'South Peninsula': 0.62,
      'Central India': 0.40,
      'Northwest India': 0.25,
      'East Coast': 0.18,
      'Northern Plains': 0.12,
      'Western Himalayas': 0.08,
      'Northeast India': 0.06,
    },
  },
  {
    id: 'nw-coldwave-2019',
    name: '2019 Northwest India Extreme Cold Wave & Dense Fog Deck',
    shortName: 'NW Cold Wave (Dec 2019)',
    dateRange: 'December 27–31, 2019',
    primaryRegionId: 'northwest-india',
    primaryRegionName: 'Northwest India',
    category: 'Persistent Boundary-Layer Inversion & Severe Cold Day',
    synopticType: 'Sub-Tropical Jet Advection & Thick Radiation Fog',
    headline: 'Record minimum temperatures and severe daytime cold busts across Indo-Gangetic Plains.',
    description:
      'In late December 2019, Northwest India experienced its second coldest December since 1901. NWP deterministic models consistently overpredicted maximum temperatures by 5°–8°C due to inadequate representation of persistent boundary-layer fog radiative shielding.',
    dataQualityBadge: 'DEMO BENCHMARK DATA: IMD National Weather Forecasting Centre Bulletins',
    initializations: [
      { id: '2019-12-28 00Z', label: '2019-12-28 00Z (Peak Cold Day Run)' },
      { id: '2019-12-26 00Z', label: '2019-12-26 00Z (-48h Warning Run)' },
      { id: '2019-12-24 00Z', label: '2019-12-24 00Z (-96h Medium-Range Run)' },
    ],
    impactSummary: {
      fatalities: 'Extensive transport cancellations; 18 severe cold casualties',
      economicLoss: 'Severe agricultural frost damage to rabi crops',
      peakObservedRainfall: 'Dry event (0.0mm); Daytime max temp 9.4°C in Delhi (11.4°C below normal)',
      bustSignificance: 'Maximum temperature overprediction bust exceeding 6.2°C at Day 5 lead time.',
    },
    observedGroundTruth: {
      precipitationMm: 0.0,
      temperatureC: 9.4,
      mslpHpa: 1019.2,
      imdCategory: 'No Rain (Severe Cold Day Anomaly)',
    },
    forecastProgression: {
      1: { precipFcst: 0.0, tempFcst: 12.2, bustProb: 0.32, conf: 0.68, risk: 'moderate' },
      2: { precipFcst: 0.0, tempFcst: 13.8, bustProb: 0.45, conf: 0.55, risk: 'elevated' },
      3: { precipFcst: 0.0, tempFcst: 15.2, bustProb: 0.58, conf: 0.43, risk: 'high' },
      4: { precipFcst: 0.0, tempFcst: 16.5, bustProb: 0.72, conf: 0.30, risk: 'high' },
      5: { precipFcst: 0.0, tempFcst: 17.6, bustProb: 0.83, conf: 0.21, risk: 'extreme' },
      6: { precipFcst: 0.0, tempFcst: 18.2, bustProb: 0.86, conf: 0.18, risk: 'extreme' },
      7: { precipFcst: 0.0, tempFcst: 18.8, bustProb: 0.89, conf: 0.15, risk: 'extreme' },
      8: { precipFcst: 0.0, tempFcst: 19.2, bustProb: 0.91, conf: 0.13, risk: 'extreme' },
      9: { precipFcst: 0.0, tempFcst: 19.5, bustProb: 0.93, conf: 0.11, risk: 'extreme' },
      10: { precipFcst: 0.0, tempFcst: 19.8, bustProb: 0.94, conf: 0.10, risk: 'extreme' },
    },
    regionalMultipliers: {
      'Northwest India': 1.0,
      'Northern Plains': 0.85,
      'Western Himalayas': 0.48,
      'Central India': 0.35,
      'East Coast': 0.15,
      'Northeast India': 0.12,
      'West Coast': 0.08,
      'South Peninsula': 0.04,
    },
  },
];

/**
 * Retrieves the full catalog of Historical Replay benchmark events.
 * @returns {Array} List of historical event metadata
 */
export function getHistoricalReplayEvents() {
  return MOCK_HISTORICAL_REPLAY_EVENTS.map((evt) => ({
    id: evt.id,
    name: evt.name,
    shortName: evt.shortName,
    dateRange: evt.dateRange,
    primaryRegionId: evt.primaryRegionId,
    primaryRegionName: evt.primaryRegionName,
    category: evt.category,
    synopticType: evt.synopticType,
    headline: evt.headline,
    description: evt.description,
    dataQualityBadge: evt.dataQualityBadge,
    initializations: evt.initializations,
    impactSummary: evt.impactSummary,
  }));
}

/**
 * Generates an analytical replay record for a specific benchmark event,
 * initialization cycle, lead day, and selected geographic region.
 *
 * @param {Object} params
 * @param {string} params.eventId - e.g. 'kerala-2018'
 * @param {string} [params.cycle] - Selected initialization cycle
 * @param {number} [params.leadDay=5] - Forecast lead day (1–10)
 * @param {string} [params.regionId] - Selected region identifier
 * @returns {Object} Analytical replay payload
 */
export function getHistoricalReplayData({
  eventId = 'kerala-2018',
  cycle = null,
  leadDay = 5,
  regionId = null,
} = {}) {
  const event =
    MOCK_HISTORICAL_REPLAY_EVENTS.find((e) => e.id === eventId) ||
    MOCK_HISTORICAL_REPLAY_EVENTS[0];

  const effectiveCycle = cycle || event.initializations[0].id;
  const leadNum = Math.max(1, Math.min(10, Number(leadDay) || 5));
  const leadProfile = event.forecastProgression[leadNum] || event.forecastProgression[5];
  const groundTruth = event.observedGroundTruth;

  // Selected region
  const targetRegion =
    MOCK_REGIONS.find((r) => r.id === regionId || r.shortName === regionId) ||
    MOCK_REGIONS.find((r) => r.id === event.primaryRegionId) ||
    MOCK_REGIONS[5];

  const isPrimaryRegion = targetRegion.id === event.primaryRegionId || targetRegion.shortName === event.primaryRegionName;
  const regionMultiplier = event.regionalMultipliers[targetRegion.shortName] ?? (isPrimaryRegion ? 1.0 : 0.3);

  // Region-specific scaled metrics
  const bustProbability = Math.min(0.97, Math.max(0.12, leadProfile.bustProb * regionMultiplier));
  const confidence = Math.max(0.08, Math.min(0.85, 1 - (bustProbability * 0.95)));

  let riskLevel = 'low';
  if (bustProbability >= 0.75) riskLevel = 'extreme';
  else if (bustProbability >= 0.60) riskLevel = 'high';
  else if (bustProbability >= 0.40) riskLevel = 'elevated';
  else if (bustProbability >= 0.25) riskLevel = 'moderate';

  const precipFcst = Number((leadProfile.precipFcst * (isPrimaryRegion ? 1.0 : regionMultiplier * 0.4)).toFixed(1));
  const precipObs = Number((groundTruth.precipitationMm * (isPrimaryRegion ? 1.0 : regionMultiplier * 0.35)).toFixed(1));
  const precipDelta = Number((precipObs - precipFcst).toFixed(1));
  const precipAbsError = Number(Math.abs(precipDelta).toFixed(1));

  const tempFcst = leadProfile.tempFcst;
  const tempObs = groundTruth.temperatureC;
  const tempDelta = Number((tempObs - tempFcst).toFixed(1));
  const tempAbsError = Number(Math.abs(tempDelta).toFixed(1));

  // Determine IMD category for precipitation
  let imdFcstCat = 'Light Rain (<7.5mm)';
  if (precipFcst >= 204.5) imdFcstCat = 'Extremely Heavy Rain (≥204.5mm)';
  else if (precipFcst >= 115.6) imdFcstCat = 'Very Heavy Rain (115.6–204.4mm)';
  else if (precipFcst >= 64.5) imdFcstCat = 'Heavy Rain (64.5–115.5mm)';
  else if (precipFcst >= 15.6) imdFcstCat = 'Moderate Rain (15.6–64.4mm)';
  else if (precipFcst >= 7.6) imdFcstCat = 'Rather Heavy / Light-Mod Rain';

  // Ground truth evaluation
  const categoryShift = precipAbsError >= 60 ? 3 : precipAbsError >= 30 ? 2 : precipAbsError >= 15 ? 1 : 0;
  const percentileExceeded = bustProbability >= 0.35;
  const tempRuleExceeded = tempAbsError >= 3.0;

  let verdict = 'VERIFIED BUST';
  let verdictSeverity = 'danger';
  let verdictSummary = `Forecast severely underpredicted outcome by ${precipAbsError} mm/24h at Day ${leadNum}. Early warning system correctly flagged low confidence (${Math.round(confidence * 100)}%).`;

  if (leadNum <= 2 && bustProbability < 0.40) {
    verdict = 'CONVERGING SKILL';
    verdictSeverity = 'warning';
    verdictSummary = `By Day ${leadNum}, numerical forecast converged closer to ground truth within acceptable operational limits.`;
  } else if (!isPrimaryRegion && bustProbability < 0.30) {
    verdict = 'NO REGIONAL BUST';
    verdictSeverity = 'neutral';
    verdictSummary = `Peripheral region experienced normal meteorological conditions within climatological error tolerances.`;
  }

  // Regional metrics map across all 8 Indian regions for IndiaRiskMap
  const regionalMetrics = {};
  MOCK_REGIONS.forEach((r) => {
    const mult = event.regionalMultipliers[r.shortName] ?? 0.25;
    const rBust = Math.min(0.96, Math.max(0.10, leadProfile.bustProb * mult));
    const rConf = Math.max(0.10, Math.min(0.85, 1 - (rBust * 0.92)));
    regionalMetrics[r.shortName] = {
      bustProbability: Number(rBust.toFixed(3)),
      confidence: Number(rConf.toFixed(3)),
      precipError: Number((precipAbsError * mult).toFixed(1)),
      tempError: Number((tempAbsError * mult).toFixed(1)),
    };
  });

  // Replay explanation factors
  const explanationFactors = [
    {
      factorId: 'hist-error-lead',
      name: `Historical Day ${leadNum} Error Growth`,
      plainReason: `High historical error at Day ${leadNum} lead time in this season`,
      description: `Historical ECMWF verification over ${targetRegion.shortName} indicates an empirical bust rate of ${(bustProbability * 100).toFixed(1)}% at T+${leadNum * 24}h.`,
      source: 'historical_context',
      contribution: 0.28,
      shapValue: 0.28,
      direction: 'positive_risk',
      severity: leadNum >= 4 ? 'high' : 'elevated',
      evidenceValue: `Empirical verification bust frequency: ${(bustProbability * 100).toFixed(1)}%`,
      tooltip: 'Historical Climatological Error: Quantified empirical bust rate over 2018–2021 ECMWF archive.',
    },
    {
      factorId: 'precip-uncertainty',
      name: 'Precipitation Ensemble Spread & Convective Ambiguity',
      plainReason: 'Large precipitation ensemble spread across orographic boundaries',
      description: `Ensemble members diverged by ±${(precipFcst * 0.75).toFixed(1)}mm across steep topographic gradients.`,
      source: 'model_output',
      contribution: 0.25,
      shapValue: 0.25,
      direction: 'positive_risk',
      severity: 'high',
      evidenceValue: `Ensemble 90th/10th spread: ±${(precipFcst * 0.75).toFixed(1)} mm/24h`,
      tooltip: 'Ensemble Quantile Spread: High dispersion indicates acute sensitivity to convection triggering.',
    },
    {
      factorId: 'analogue-similarity',
      name: 'Past-Analogue Pattern Mispredictions',
      plainReason: 'Similar historical synoptic patterns produced severe forecast underpredictions',
      description: `Top 5 historical analogue cases with matching 500hPa geopotential height fields resulted in severe mean negative precipitation bias.`,
      source: 'historical_context',
      contribution: 0.18,
      shapValue: 0.18,
      direction: 'positive_risk',
      severity: 'elevated',
      evidenceValue: 'FAISS Top-5 Analogue MAE: 64.2mm (Cosine Distance: 0.89)',
      tooltip: 'Analogue Error Retrieval: Fast vector search matching current synoptic flow against past busts.',
    },
    {
      factorId: 'jumpiness-500hpa',
      name: 'Run-to-Run Consistency (500 hPa Jumpiness)',
      plainReason: 'Consecutive initialization runs shifted the rainfall centroid',
      description: `Geopotential height contours exhibited a ${leadNum >= 4 ? '4.8 dam' : '2.1 dam'} position displacement from previous operational cycle.`,
      source: 'model_output',
      contribution: 0.14,
      shapValue: 0.14,
      direction: 'positive_risk',
      severity: leadNum >= 4 ? 'elevated' : 'moderate',
      evidenceValue: `Centroid shift: ${leadNum >= 4 ? '135 km' : '45 km'} westward`,
      tooltip: '500 hPa Jumpiness: Spatial distance displacement of middle troposphere geopotential contours.',
    },
    {
      factorId: 'stabilizing-mslp',
      name: 'Synoptic Mean Sea Level Pressure Stability',
      plainReason: 'Broad synoptic pressure gradient remained physically anchored',
      description: `Equator-to-pole pressure gradient maintained coherent monsoonal orientation despite localized intensity misses.`,
      source: 'model_output',
      contribution: -0.10,
      shapValue: -0.10,
      direction: 'negative_risk',
      severity: 'low',
      evidenceValue: 'MSLP gradient bias: -0.8 hPa (within tolerance)',
      tooltip: 'Synoptic MSLP Anchor: Consistent background pressure fields restrain unbounded error growth.',
    },
  ];

  return {
    meta: {
      eventId: event.id,
      eventName: event.name,
      eventShortName: event.shortName,
      cycle: effectiveCycle,
      leadDay: leadNum,
      leadHours: leadNum * 24,
      regionId: targetRegion.id,
      regionName: targetRegion.shortName,
      isPrimaryRegion,
      dateRange: event.dateRange,
      category: event.category,
      synopticType: event.synopticType,
      headline: event.headline,
      description: event.description,
      impactSummary: event.impactSummary,
      dataQualityBadge: event.dataQualityBadge,
      timestamp: new Date().toISOString(),
    },
    predictionSummary: {
      forecastPrecipMm: precipFcst,
      forecastTempC: tempFcst,
      bustProbability: Number(bustProbability.toFixed(3)),
      confidence: Number(confidence.toFixed(3)),
      riskLevel,
      imdForecastCategory: imdFcstCat,
    },
    historicalOutcome: {
      observedPrecipMm: precipObs,
      observedTempC: tempObs,
      observedMslpHpa: groundTruth.mslpHpa,
      imdObservedCategory: groundTruth.imdCategory,
      precipitationDelta: precipDelta,
      precipitationAbsError: precipAbsError,
      temperatureDelta: tempDelta,
      temperatureAbsError: tempAbsError,
      categoryShift,
      percentileExceeded,
      tempRuleExceeded,
      verdict,
      verdictSeverity,
      verdictSummary,
    },
    regionalMetrics,
    explanationFactors,
    bulletinSummary: `At Lead Day ${leadNum} (+${leadNum * 24}h) for ${event.shortName}, the AI verification system flagged ${Math.round(bustProbability * 100)}% bust risk with low calibrated confidence (${Math.round(confidence * 100)}%). Ground truth verification confirms ${verdict}: actual precipitation reached ${precipObs} mm/24h vs forecast ${precipFcst} mm/24h (${precipDelta > 0 ? '+' : ''}${precipDelta} mm/24h discrepancy).`,
  };
}

