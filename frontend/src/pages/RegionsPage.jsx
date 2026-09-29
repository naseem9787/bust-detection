/**
 * Region Analysis Page
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 *
 * PURPOSE:
 * Meteorological research and forecast verification tool allowing forecasters
 * and researchers to investigate WHY a geographic region historically experiences
 * medium-range forecast busts.
 *
 * STRUCTURE:
 * 1. HEADER: Region name, current forecast cycle, status & controls
 * 2. CURRENT FORECAST: Bust probability, calibrated confidence, expected errors
 * 3. PRIMARY ANALYSIS: Historical bust rate by Day 1–10 (trajectory & matrix)
 * 4. SECONDARY ANALYSIS: Mean absolute forecast error (MAE) by Day 1–10 (Precip mm vs Temp °C)
 * 5. EXPLANATION: 5 factors affecting confidence (historical error at lead, precip uncertainty,
 *    model disagreement, run-to-run changes, atmospheric regime indicators)
 * 6. HISTORICAL PATTERNS: Seasonal climatology breakdown & operational extreme misses archive
 */

import React, { useState, useEffect, useMemo } from 'react';
import { REGIONS, LEAD_DAYS, SEASONS } from '../design-system/weather-tokens.js';
import {
  getRegionAnalysis,
  getRegions,
  getForecastCycles,
} from '../services/api.js';

const SEASON_OPTIONS = SEASONS.map((s) => ({
  id: s.id,
  label: s.label,
}));

const DEFAULT_CYCLES = [
  { code: '2026-09-29 00Z', label: '2026-09-29 00Z (Latest Operational)' },
  { code: '2026-09-28 12Z', label: '2026-09-28 12Z (-12h Run)' },
  { code: '2026-09-28 00Z', label: '2026-09-28 00Z (-24h Run)' },
  { code: '2018-08-14 00Z', label: '2018-08-14 00Z (Kerala Case Study)' },
];
import { Select } from '../components/ui/Select.jsx';
import { RiskBadge } from '../components/ui/RiskBadge.jsx';
import { Badge } from '../components/ui/Badge.jsx';
import { ChartContainer } from '../components/ui/ChartContainer.jsx';
import { ConfidenceIndicator } from '../components/forecast/ConfidenceIndicator.jsx';
import { ExplanationPanel } from '../components/explainability/ExplanationPanel.jsx';
import { LoadingState } from '../components/feedback/LoadingState.jsx';
import { ErrorState } from '../components/feedback/ErrorState.jsx';
import { EmptyState } from '../components/feedback/EmptyState.jsx';
import {
  MapPinIcon,
  LayersIcon,
  DatabaseIcon,
  TrendingUpIcon,
  AlertTriangleIcon,
  ClockIcon,
  RefreshCwIcon,
  CloudRainIcon,
  ThermometerIcon,
} from '../components/icons/Icons.jsx';

// Regional synoptic profiles aligned with src/regions.py
const REGIONAL_PROFILES = {
  'Western Himalaya': {
    primaryBustMode: 'Orographic Precip & Freezing Level Descent',
    vulnerableSeason: 'Winter (DJF) / Monsoon (JJAS)',
    dominantError: 'Underprediction of Western Disturbance precipitation volume',
    samplePoints: '1,248 grid points',
    lat: [28.0, 36.0],
    lon: [73.0, 81.0],
  },
  'Northwest India': {
    primaryBustMode: 'Extreme Temperature Inversions & Heatwaves',
    vulnerableSeason: 'Pre-Monsoon (MAM)',
    dominantError: '2m temperature error > 3.0°C during persistent dry heat spells',
    samplePoints: '1,680 grid points',
    lat: [24.0, 32.0],
    lon: [69.0, 79.0],
  },
  'Indo-Gangetic Plain': {
    primaryBustMode: 'Monsoon Trough Oscillation & Low-Level Fog',
    vulnerableSeason: 'Monsoon (JJAS) & Winter (DJF)',
    dominantError: 'Categorical precipitation misclassification across trough axis',
    samplePoints: '1,512 grid points',
    lat: [24.0, 30.0],
    lon: [79.0, 88.0],
  },
  'Northeast India': {
    primaryBustMode: 'High-Volume Rainfall & Terrain Funneling',
    vulnerableSeason: 'Monsoon (JJAS)',
    dominantError: 'Underestimating extreme heavy rainfall (>115.6mm)',
    samplePoints: '1,120 grid points',
    lat: [22.0, 29.5],
    lon: [88.0, 97.5],
  },
  'Central India': {
    primaryBustMode: 'Monsoon Low Pressure Systems (LPS) Track Bias',
    vulnerableSeason: 'Monsoon (JJAS)',
    dominantError: 'Displacement of heavy rainfall corridor relative to depression track',
    samplePoints: '2,240 grid points',
    lat: [18.0, 26.0],
    lon: [74.0, 84.0],
  },
  'West Coast': {
    primaryBustMode: 'Western Ghats Orographic Coastal Heavy Rain',
    vulnerableSeason: 'Monsoon (JJAS)',
    dominantError: 'Offshore vortex false alarms and missed coastal heavy rain surges',
    samplePoints: '1,440 grid points',
    lat: [8.0, 20.0],
    lon: [72.0, 77.0],
  },
  'East Coast': {
    primaryBustMode: 'Post-Monsoon Cyclones & Landfall Timing',
    vulnerableSeason: 'Post-Monsoon (ON)',
    dominantError: 'Coastal landfall wind field and precipitation distribution',
    samplePoints: '1,600 grid points',
    lat: [8.0, 20.0],
    lon: [78.0, 87.0],
  },
  'South Peninsula': {
    primaryBustMode: 'Convective Cell Timing & Rain-Shadow Deficit',
    vulnerableSeason: 'Pre-Monsoon (MAM) & Post-Monsoon (ON)',
    dominantError: 'Localized convective precipitation timing in the lee of Western Ghats',
    samplePoints: '1,320 grid points',
    lat: [8.0, 16.0],
    lon: [74.5, 80.0],
  },
};

// SVG Chart Geometry Constants
// ViewBox: 0 0 900 170. Day 1 at x=60, Day 10 at x=840 (dx = 780 / 9 = 86.66)
const getXPos = (day) => 60 + (day - 1) * (780 / 9);
const EMPTY_SERIES = [];

export function RegionsPage() {
  const [selectedRegionId, setSelectedRegionId] = useState('West Coast');
  const [selectedLeadDay, setSelectedLeadDay] = useState(5);
  const [selectedSeason, setSelectedSeason] = useState('monsoon_JJAS');
  const [selectedCycle, setSelectedCycle] = useState('2026-09-29 00Z');

  const [availableRegions, setAvailableRegions] = useState(REGIONS);
  const [availableCycles, setAvailableCycles] = useState([]);
  const [analysisData, setAnalysisData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load initial select options
  useEffect(() => {
    async function loadMeta() {
      try {
        const [regs, cycles] = await Promise.all([
          getRegions(),
          getForecastCycles(),
        ]);
        if (regs?.length) setAvailableRegions(regs);
        if (cycles?.length) setAvailableCycles(cycles);
      } catch (err) {
        console.warn('Failed to load metadata options:', err);
      }
    }
    loadMeta();
  }, []);

  // Fetch regional analysis data when region, season, leadDay, or cycle changes
  useEffect(() => {
    let isMounted = true;
    getRegionAnalysis({
      regionId: selectedRegionId,
      season: selectedSeason,
      leadDay: selectedLeadDay,
      cycle: selectedCycle,
    })
      .then((data) => {
        if (isMounted) {
          setAnalysisData(data);
          setLoading(false);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('Failed to load region analysis:', err);
          setError('Unable to load verification data for the selected region. Please try again.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedRegionId, selectedSeason, selectedLeadDay, selectedCycle]);

  const handleRefresh = () => {
    setLoading(true);
    getRegionAnalysis({
      regionId: selectedRegionId,
      season: selectedSeason,
      leadDay: selectedLeadDay,
      cycle: selectedCycle,
      forceReload: true,
    })
      .then((data) => {
        setAnalysisData(data);
        setLoading(false);
        setError(null);
      })
      .catch((err) => {
        console.error('Failed to load region analysis:', err);
        setError('Unable to load verification data for the selected region. Please try again.');
        setLoading(false);
      });
  };

  const activeProfile = REGIONAL_PROFILES[selectedRegionId] || REGIONAL_PROFILES['West Coast'];
  const activeRegionObj = availableRegions.find(
    (r) => r.shortName === selectedRegionId || r.id === selectedRegionId || r.name === selectedRegionId
  ) || REGIONS[5];

  // Options for dropdown selectors (memoized to prevent re-instantiating arrays)
  const regionOptions = useMemo(
    () =>
      availableRegions.map((r) => ({
        id: r.shortName || r.name,
        label: r.name || r.shortName,
      })),
    [availableRegions]
  );

  const cycleOptions = useMemo(
    () =>
      (availableCycles.length > 0 ? availableCycles : DEFAULT_CYCLES).map((c) => ({
        id: c.code || c.id,
        label: c.label || c.code,
      })),
    [availableCycles]
  );

  const seasonOptions = SEASON_OPTIONS;

  const leadDaySeries = analysisData?.leadDaySeries || EMPTY_SERIES;

  // Pre-calculated Day 1–10 progression curves memoized to prevent string concatenation on every render
  const { bustRatePoints, precipBustPoints, tempBustPoints, precipMaePoints, tempMaePoints } = useMemo(() => {
    return {
      bustRatePoints: leadDaySeries
        .map((d) => `${getXPos(d.leadDay).toFixed(1)},${(145 - (d.bustRate / 65) * 125).toFixed(1)}`)
        .join(' '),
      precipBustPoints: leadDaySeries
        .map((d) => `${getXPos(d.leadDay).toFixed(1)},${(145 - (d.precipBustRate / 65) * 125).toFixed(1)}`)
        .join(' '),
      tempBustPoints: leadDaySeries
        .map((d) => `${getXPos(d.leadDay).toFixed(1)},${(145 - (d.tempBustRate / 65) * 125).toFixed(1)}`)
        .join(' '),
      precipMaePoints: leadDaySeries
        .map((d) => `${getXPos(d.leadDay).toFixed(1)},${(145 - (d.meanAbsErrorPrecipMm / 14) * 125).toFixed(1)}`)
        .join(' '),
      tempMaePoints: leadDaySeries
        .map((d) => `${getXPos(d.leadDay).toFixed(1)},${(145 - (d.meanAbsErrorTempC / 3.2) * 125).toFixed(1)}`)
        .join(' '),
    };
  }, [leadDaySeries]);

  if (loading && !analysisData) {
    return (
      <div className="page-container">
        <LoadingState message="Loading meteorological verification archive and regional bust curves..." />
      </div>
    );
  }

  if (error && !analysisData) {
    return (
      <div className="page-container">
        <ErrorState
          title="Regional Verification Unavailable"
          message={error}
          onRetry={handleRefresh}
        />
      </div>
    );
  }

  if (!loading && !error && !analysisData) {
    return (
      <div className="page-container">
        <EmptyState
          title="No Regional Analysis Found"
          message={`No verification records available for ${selectedRegionId}.`}
          onAction={handleRefresh}
          actionLabel="Retry Regional Query"
        />
      </div>
    );
  }

  const {
    currentLeadRecord = {},
    seasonalBreakdown = [],
    forecast = {},
    explanations = [],
    operationalMisses = {},
  } = analysisData || {};

  const verification = forecast.verification || {};
  const variables = forecast.variables || {};
  const precip = variables.precipitation || {};
  const temp = variables.temperature || {};
  const mslp = variables.meanSeaLevelPressure || {};

  const bustProb = (verification.bustProbability !== undefined)
    ? Math.round(verification.bustProbability * 100)
    : Math.round((currentLeadRecord.bustRate || 36.7));

  const confidenceScore = verification.confidence !== undefined ? verification.confidence : 0.45;
  const riskLevel = verification.riskLevel || 'high';

  const activeX = getXPos(selectedLeadDay);

  // 90th percentile threshold baseline (e.g. 35% bust rate)
  const thresholdY = (145 - (35 / 65) * 125).toFixed(1);

  const activePrecipMae = currentLeadRecord.meanAbsErrorPrecipMm || precip.absError || 5.75;
  const activeTempMae = currentLeadRecord.meanAbsErrorTempC || temp.absError || 0.92;

  return (
    <div className="page-container">
      <div className="region-analysis-view">
        {/* ==========================================================================
            1. HEADER: Region Name, Forecast Cycle, Status & Diagnostic Controls
            ========================================================================== */}
        <div className="analysis-header-panel">
          <div className="analysis-header-eyebrow">
            <LayersIcon size={14} />
            <span>Operational Meteorological Verification &bull; Regional Climatology & Bust Diagnostics</span>
          </div>

          <div className="analysis-header-top">
            <div className="analysis-title-group">
              <h1>{activeRegionObj.name || activeRegionObj.shortName}</h1>
              <div className="analysis-region-meta">
                <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
                  <MapPinIcon size={13} style={{ color: '#38BDF8' }} />
                  Bounding Box: [{activeProfile.lat.join('°–')}°N, {activeProfile.lon.join('°–')}°E]
                </span>
                <span>&bull;</span>
                <span>{activeProfile.samplePoints}</span>
                <span>&bull;</span>
                <span style={{ color: '#38BDF8' }}>
                  Primary Mode: {activeProfile.primaryBustMode}
                </span>
              </div>
            </div>

            {/* Interactive Selectors Bar */}
            <div className="analysis-header-controls">
              <Select
                id="region-selector"
                value={selectedRegionId}
                onChange={(val) => setSelectedRegionId(val)}
                options={regionOptions}
                style={{ minWidth: '220px' }}
              />

              <Select
                id="cycle-selector"
                value={selectedCycle}
                onChange={(val) => setSelectedCycle(val)}
                options={cycleOptions}
                style={{ minWidth: '200px' }}
              />

              <Select
                id="season-selector"
                value={selectedSeason}
                onChange={(val) => setSelectedSeason(val)}
                options={seasonOptions}
                style={{ minWidth: '190px' }}
              />

              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleRefresh}
                title="Refresh verification metrics"
                style={{ height: '36px', padding: '0 10px' }}
              >
                <RefreshCwIcon size={14} className={loading ? 'spin' : ''} />
              </button>
            </div>
          </div>

          {/* Operational Status Strip */}
          <div className="analysis-status-strip">
            <div className="analysis-status-pills">
              <RiskBadge level={riskLevel} />
              <Badge variant="neutral">
                <ClockIcon size={12} style={{ marginRight: '4px' }} />
                Lead Time: Day {selectedLeadDay} (+{selectedLeadDay * 24}h)
              </Badge>
              <Badge variant="outline">
                Season: {SEASONS.find((s) => s.id === selectedSeason)?.label.split(' (')[0] || selectedSeason}
              </Badge>
              {verification.historicalPercentileExceeded && (
                <span className="badge badge-risk-high" style={{ fontSize: '11px' }}>
                  <AlertTriangleIcon size={12} style={{ marginRight: '4px' }} />
                  90th %ile Bust Threshold Exceeded
                </span>
              )}
            </div>

            <div className="analysis-status-synopsis">
              Empirical Day {selectedLeadDay} bust rate: <strong className="tabular-nums" style={{ color: 'var(--text-primary)' }}>{currentLeadRecord.bustRate || bustProb}%</strong>. {activeProfile.dominantError}.
            </div>
          </div>
        </div>

        {/* ==========================================================================
            2. CURRENT FORECAST: Bust Probability, Calibrated Confidence, Expected Error
            ========================================================================== */}
        <div className="verification-horizon-banner">
          {/* Bust Probability */}
          <div className="horizon-metric-card">
            <div className="horizon-metric-label">
              <span>Bust Probability</span>
              <RiskBadge level={riskLevel} showLabel={false} />
            </div>
            <div className="horizon-metric-val-row">
              <span className="horizon-metric-value tabular-nums" style={{ color: riskLevel === 'extreme' || riskLevel === 'high' ? '#F87171' : '#FBBF24' }}>
                {bustProb}%
              </span>
              <span className="horizon-metric-unit">P(Bust)</span>
            </div>
            <div className="horizon-metric-subtext">
              Lead Day {selectedLeadDay} &bull; 90th %ile threshold: 35.0%
            </div>
          </div>

          {/* Forecast Confidence */}
          <div className="horizon-metric-card" style={{ paddingLeft: '8px' }}>
            <ConfidenceIndicator confidence={confidenceScore} />
          </div>

          {/* Expected Precipitation Error */}
          <div className="horizon-metric-card" style={{ paddingLeft: '8px' }}>
            <div className="horizon-metric-label">
              <span>Expected Precip Error</span>
              <CloudRainIcon size={14} style={{ color: '#0284C7' }} />
            </div>
            <div className="horizon-metric-val-row">
              <span className="horizon-metric-value tabular-nums" style={{ color: '#38BDF8' }}>
                &plusmn;{precip.absError || (activePrecipMae * 1.6).toFixed(1)}
              </span>
              <span className="horizon-metric-unit">mm/24h</span>
            </div>
            <div className="horizon-metric-subtext">
              Fcst: {precip.forecastValue || 48.5}mm &bull; {precip.absError > 15 ? 'IMD Category Shift: Moderate &rarr; Heavy' : 'Within category boundary'}
            </div>
          </div>

          {/* Expected Temperature & Pressure Error */}
          <div className="horizon-metric-card" style={{ paddingLeft: '8px' }}>
            <div className="horizon-metric-label">
              <span>Expected Thermal &amp; MSLP</span>
              <ThermometerIcon size={14} style={{ color: '#F59E0B' }} />
            </div>
            <div className="horizon-metric-val-row">
              <span className="horizon-metric-value tabular-nums" style={{ color: '#FBBF24' }}>
                &plusmn;{temp.absError || activeTempMae}
              </span>
              <span className="horizon-metric-unit">&deg;C</span>
              <span style={{ fontSize: '13px', color: 'var(--text-muted)', marginLeft: '6px' }}>
                &bull; MSLP &plusmn;{mslp.absError || 1.2}hPa
              </span>
            </div>
            <div className="horizon-metric-subtext">
              2m Temp: {temp.forecastValue || 28.5}&deg;C &bull; {temp.absError > 3.0 ? 'Hard temperature bust threshold exceeded' : 'Normal error tolerance (<3.0°C)'}
            </div>
          </div>
        </div>

        {/* ==========================================================================
            3 & 4. PRIMARY & SECONDARY VERIFICATION:
            - Primary: Historical bust rate by Day 1–10
            - Secondary: Mean absolute forecast error (MAE) by Day 1–10
            ========================================================================== */}
        <div className="analysis-section-block">
          <div className="analysis-section-header">
            <div>
              <div className="analysis-section-title">
                <TrendingUpIcon size={16} style={{ color: '#38BDF8' }} />
                <span>Lead-Time Verification Skill: Day 1 through Day 10</span>
              </div>
              <div className="analysis-section-subtitle">
                Historical verification evaluated across 27,328 regional grid-hours in the 2018–2021 database. Click any lead day to inspect that horizon.
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Quick Select Lead:</span>
              <div style={{ display: 'flex', gap: '4px' }}>
                {[1, 3, 5, 7, 10].map((d) => (
                  <button
                    key={d}
                    type="button"
                    className={`btn btn-xs ${selectedLeadDay === d ? 'btn-primary' : 'btn-secondary'}`}
                    onClick={() => setSelectedLeadDay(d)}
                    style={{ minWidth: '50px' }}
                  >
                    Day {d}
                  </button>
                ))}
              </div>
            </div>
          </div>

          <div className="verification-charts-grid">
            {/* PRIMARY ANALYSIS CHART: Historical Bust Rate by Day 1–10 */}
            <ChartContainer
              title="Primary Verification: Historical Bust Rate by Day 1–10"
              subtitle={`Frequency of model forecast busts exceeding the 90th percentile error threshold &bull; ${activeRegionObj.shortName}`}
              unit="%"
              height={190}
              legend={[
                { label: 'Total Bust Rate (%)', color: '#EF4444' },
                { label: 'Precip Bust Rate', color: '#0284C7', dashed: true },
                { label: 'Temp Bust Rate', color: '#F59E0B', dashed: true },
                { label: '90th %ile Threshold', color: 'rgba(255, 255, 255, 0.35)', dashed: true },
              ]}
            >
              <svg className="curve-svg" viewBox="0 0 900 170" preserveAspectRatio="none" role="img" aria-label="Historical Bust Rate by Day 1 to 10">
                {/* Reference Grid lines */}
                <line x1="60" y1="20" x2="840" y2="20" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                <line x1="60" y1="62" x2="840" y2="62" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                <line x1="60" y1="104" x2="840" y2="104" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                <line x1="60" y1="145" x2="840" y2="145" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="1" />

                {/* Y-axis labels */}
                <text x="50" y="24" textAnchor="end" fill="rgba(255, 255, 255, 0.4)" fontSize="10" fontFamily="var(--font-mono)">60%</text>
                <text x="50" y="66" textAnchor="end" fill="rgba(255, 255, 255, 0.4)" fontSize="10" fontFamily="var(--font-mono)">40%</text>
                <text x="50" y="108" textAnchor="end" fill="rgba(255, 255, 255, 0.4)" fontSize="10" fontFamily="var(--font-mono)">20%</text>
                <text x="50" y="149" textAnchor="end" fill="rgba(255, 255, 255, 0.4)" fontSize="10" fontFamily="var(--font-mono)">0%</text>

                {/* 90th percentile threshold benchmark */}
                <line
                  x1="60"
                  y1={thresholdY}
                  x2="840"
                  y2={thresholdY}
                  stroke="rgba(255, 255, 255, 0.35)"
                  strokeWidth="1.2"
                  strokeDasharray="4 4"
                />
                <text x="845" y={Number(thresholdY) + 3} fill="rgba(255, 255, 255, 0.45)" fontSize="9" fontFamily="var(--font-mono)">
                  35% Threshold
                </text>

                {/* Temperature Bust Rate (Amber dashed) */}
                {tempBustPoints && (
                  <polyline
                    fill="none"
                    stroke="#F59E0B"
                    strokeWidth="1.6"
                    strokeDasharray="3 3"
                    points={tempBustPoints}
                  />
                )}

                {/* Precipitation Bust Rate (Blue dashed) */}
                {precipBustPoints && (
                  <polyline
                    fill="none"
                    stroke="#0284C7"
                    strokeWidth="1.8"
                    strokeDasharray="4 3"
                    points={precipBustPoints}
                  />
                )}

                {/* Total Bust Rate (Bold Red) */}
                {bustRatePoints && (
                  <polyline
                    fill="none"
                    stroke="#EF4444"
                    strokeWidth="2.5"
                    points={bustRatePoints}
                  />
                )}

                {/* Clickable data points at each lead day */}
                {leadDaySeries.map((d) => {
                  const cx = getXPos(d.leadDay);
                  const cy = 145 - (d.bustRate / 65) * 125;
                  const isSelected = d.leadDay === selectedLeadDay;

                  return (
                    <g key={d.leadDay} onClick={() => setSelectedLeadDay(d.leadDay)} style={{ cursor: 'pointer' }}>
                      <circle
                        cx={cx}
                        cy={cy}
                        r={isSelected ? 6 : 4}
                        fill={isSelected ? '#EF4444' : '#1E293B'}
                        stroke="#EF4444"
                        strokeWidth={isSelected ? 2.5 : 1.5}
                        className="curve-lead-point-btn"
                      />
                      {isSelected && (
                        <text
                          x={cx}
                          y={cy - 10}
                          textAnchor="middle"
                          fill="#F87171"
                          fontSize="11"
                          fontWeight="700"
                          fontFamily="var(--font-mono)"
                        >
                          {d.bustRate}%
                        </text>
                      )}
                    </g>
                  );
                })}

                {/* Active Lead Day Vertical Marker */}
                <line
                  x1={activeX}
                  y1="10"
                  x2={activeX}
                  y2="155"
                  stroke="#38BDF8"
                  strokeWidth="1.75"
                  strokeDasharray="3 3"
                />

                {/* X-axis ticks (Day 1..10) */}
                {LEAD_DAYS.map((ld) => {
                  const x = getXPos(ld.day);
                  const isSelected = ld.day === selectedLeadDay;
                  return (
                    <g key={ld.day} onClick={() => setSelectedLeadDay(ld.day)} style={{ cursor: 'pointer' }}>
                      <text
                        x={x}
                        y="164"
                        textAnchor="middle"
                        fill={isSelected ? '#38BDF8' : 'rgba(255, 255, 255, 0.45)'}
                        fontSize={isSelected ? '11' : '10'}
                        fontWeight={isSelected ? '700' : '400'}
                        fontFamily="var(--font-mono)"
                      >
                        D{ld.day}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </ChartContainer>

            {/* SECONDARY ANALYSIS CHART: Mean Absolute Forecast Error (MAE) by Day 1–10 */}
            <ChartContainer
              title="Secondary Verification: Mean Absolute Forecast Error (MAE)"
              subtitle={`Precipitation MAE [mm] vs 2m Temperature MAE [°C] scaling across lead times`}
              unit="mm &bull; °C"
              height={190}
              legend={[
                { label: 'Precipitation MAE [mm]', color: '#38BDF8' },
                { label: '2m Temperature MAE [°C]', color: '#10B981' },
              ]}
            >
              <svg className="curve-svg" viewBox="0 0 900 170" preserveAspectRatio="none" role="img" aria-label="Mean Absolute Forecast Error by Day 1 to 10">
                {/* Horizontal reference lines */}
                <line x1="60" y1="20" x2="840" y2="20" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                <line x1="60" y1="62" x2="840" y2="62" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                <line x1="60" y1="104" x2="840" y2="104" stroke="rgba(255, 255, 255, 0.08)" strokeWidth="1" />
                <line x1="60" y1="145" x2="840" y2="145" stroke="rgba(255, 255, 255, 0.15)" strokeWidth="1" />

                {/* Left Y-axis labels (Precip mm) */}
                <text x="50" y="24" textAnchor="end" fill="#38BDF8" fontSize="10" fontFamily="var(--font-mono)">14mm</text>
                <text x="50" y="66" textAnchor="end" fill="#38BDF8" fontSize="10" fontFamily="var(--font-mono)">9mm</text>
                <text x="50" y="108" textAnchor="end" fill="#38BDF8" fontSize="10" fontFamily="var(--font-mono)">4mm</text>
                <text x="50" y="149" textAnchor="end" fill="#38BDF8" fontSize="10" fontFamily="var(--font-mono)">0mm</text>

                {/* Right Y-axis labels (Temp °C) */}
                <text x="850" y="24" textAnchor="start" fill="#10B981" fontSize="10" fontFamily="var(--font-mono)">3.0°C</text>
                <text x="850" y="66" textAnchor="start" fill="#10B981" fontSize="10" fontFamily="var(--font-mono)">2.0°C</text>
                <text x="850" y="108" textAnchor="start" fill="#10B981" fontSize="10" fontFamily="var(--font-mono)">1.0°C</text>
                <text x="850" y="149" textAnchor="start" fill="#10B981" fontSize="10" fontFamily="var(--font-mono)">0°C</text>

                {/* Temperature MAE Curve (Emerald) */}
                {tempMaePoints && (
                  <polyline
                    fill="none"
                    stroke="#10B981"
                    strokeWidth="2.2"
                    points={tempMaePoints}
                  />
                )}

                {/* Precipitation MAE Curve (Cyan) */}
                {precipMaePoints && (
                  <polyline
                    fill="none"
                    stroke="#38BDF8"
                    strokeWidth="2.4"
                    points={precipMaePoints}
                  />
                )}

                {/* Clickable points */}
                {leadDaySeries.map((d) => {
                  const cx = getXPos(d.leadDay);
                  const cyP = 145 - (d.meanAbsErrorPrecipMm / 14) * 125;
                  const cyT = 145 - (d.meanAbsErrorTempC / 3.2) * 125;
                  const isSelected = d.leadDay === selectedLeadDay;

                  return (
                    <g key={d.leadDay} onClick={() => setSelectedLeadDay(d.leadDay)} style={{ cursor: 'pointer' }}>
                      <circle cx={cx} cy={cyP} r={isSelected ? 5.5 : 3.5} fill="#38BDF8" stroke="var(--bg-canvas)" strokeWidth="1.5" />
                      <circle cx={cx} cy={cyT} r={isSelected ? 5.5 : 3.5} fill="#10B981" stroke="var(--bg-canvas)" strokeWidth="1.5" />
                      {isSelected && (
                        <>
                          <text x={cx} y={cyP - 8} textAnchor="middle" fill="#38BDF8" fontSize="10" fontWeight="700" fontFamily="var(--font-mono)">
                            {d.meanAbsErrorPrecipMm}mm
                          </text>
                          <text x={cx} y={cyT + 14} textAnchor="middle" fill="#10B981" fontSize="10" fontWeight="700" fontFamily="var(--font-mono)">
                            {d.meanAbsErrorTempC}°C
                          </text>
                        </>
                      )}
                    </g>
                  );
                })}

                {/* Active Lead Day Vertical Marker */}
                <line
                  x1={activeX}
                  y1="10"
                  x2={activeX}
                  y2="155"
                  stroke="#38BDF8"
                  strokeWidth="1.75"
                  strokeDasharray="3 3"
                />

                {/* X-axis ticks (Day 1..10) */}
                {LEAD_DAYS.map((ld) => {
                  const x = getXPos(ld.day);
                  const isSelected = ld.day === selectedLeadDay;
                  return (
                    <g key={ld.day} onClick={() => setSelectedLeadDay(ld.day)} style={{ cursor: 'pointer' }}>
                      <text
                        x={x}
                        y="164"
                        textAnchor="middle"
                        fill={isSelected ? '#38BDF8' : 'rgba(255, 255, 255, 0.45)'}
                        fontSize={isSelected ? '11' : '10'}
                        fontWeight={isSelected ? '700' : '400'}
                        fontFamily="var(--font-mono)"
                      >
                        D{ld.day}
                      </text>
                    </g>
                  );
                })}
              </svg>
            </ChartContainer>
          </div>

          {/* Lead Day 1–10 Interactive Verification Matrix Table */}
          <div className="lead-matrix-card">
            <div style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-subtle)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                Empirical Verification Matrix across Lead Horizons (Day 1–10)
              </span>
              <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                Click any row to synchronize regional forecast verification
              </span>
            </div>

            <div style={{ overflowX: 'auto' }}>
              <table className="lead-matrix-table">
                <thead>
                  <tr>
                    <th>Lead Horizon</th>
                    <th>Total Bust Rate</th>
                    <th>Precip Bust Rate</th>
                    <th>Temp Bust Rate</th>
                    <th>Precip MAE</th>
                    <th>Temp MAE</th>
                    <th>Missed Heavy Rain (&ge;64.5mm)</th>
                    <th>False Alarms</th>
                    <th>Verification Skill</th>
                  </tr>
                </thead>
                <tbody>
                  {leadDaySeries.map((row) => {
                    const isSelected = row.leadDay === selectedLeadDay;
                    const tier = row.bustRate >= 45 ? 'extreme' : row.bustRate >= 35 ? 'high' : row.bustRate >= 25 ? 'elevated' : 'moderate';

                    return (
                      <tr
                        key={row.leadDay}
                        className={`lead-matrix-row ${isSelected ? 'active' : ''}`}
                        onClick={() => setSelectedLeadDay(row.leadDay)}
                      >
                        <td style={{ fontWeight: 600, color: isSelected ? '#38BDF8' : 'var(--text-primary)' }}>
                          Day {row.leadDay} (+{row.leadDay * 24}h)
                          {isSelected && <span style={{ marginLeft: '6px', fontSize: '10px', color: '#38BDF8' }}>&bull; Active</span>}
                        </td>
                        <td className="tabular-nums" style={{ fontWeight: 700, color: row.bustRate >= 35 ? '#F87171' : '#FBBF24' }}>
                          {row.bustRate}%
                        </td>
                        <td className="tabular-nums" style={{ color: '#38BDF8' }}>
                          {row.precipBustRate}%
                        </td>
                        <td className="tabular-nums" style={{ color: '#F59E0B' }}>
                          {row.tempBustRate}%
                        </td>
                        <td className="tabular-nums">
                          {row.meanAbsErrorPrecipMm} mm
                        </td>
                        <td className="tabular-nums">
                          {row.meanAbsErrorTempC} &deg;C
                        </td>
                        <td className="tabular-nums" style={{ color: row.missedHeavyRainEvents > 100 ? '#F87171' : 'var(--text-secondary)' }}>
                          {row.missedHeavyRainEvents} events
                        </td>
                        <td className="tabular-nums">
                          {row.falseAlarmHeavyRain} events
                        </td>
                        <td>
                          <RiskBadge level={tier} />
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* ==========================================================================
            5. EXPLANATION: Factors Affecting Forecast Confidence
            Answers: "What variables contribute to uncertainty?"
            - Historical error at this lead
            - Precipitation uncertainty
            - Model disagreement
            - Run-to-run changes
            - Atmospheric regime indicators
            ========================================================================== */}
        {/* ==========================================================================
            5. EXPLANATION: Factors Affecting Forecast Confidence
            Answers: "Why is the system giving this forecast low confidence?"
            Integrates reusable ExplanationPanel (ConfidenceIndicator, ReasonList, FeatureContributionChart)
            ========================================================================== */}
        <div className="analysis-section-block">
          <ExplanationPanel
            confidence={confidenceScore}
            factors={explanations}
            regionName={activeRegionObj.name || activeRegionObj.shortName}
            leadDay={selectedLeadDay}
            cycle={selectedCycle}
            bulletinSummary={`At Lead Day ${selectedLeadDay} (${selectedLeadDay * 24}h), model skill over ${activeRegionObj.shortName} is predominantly constrained by precipitation categorical boundary dispersion and historical lead-time error compounding (${currentLeadRecord.bustRate || 36.7}%). Forecasters should treat deterministic precipitation peaks exceeding 64.5mm with caution and cross-verify with ensemble probability cones before issuing flood advisories.`}
          />
        </div>

        {/* ==========================================================================
            6. HISTORICAL PATTERNS: Seasonal Climatology & Operational Extreme Misses
            Answers: "What are the important historical patterns?"
            ========================================================================== */}
        <div className="analysis-section-block">
          <div className="analysis-section-header">
            <div>
              <div className="analysis-section-title">
                <DatabaseIcon size={16} style={{ color: '#38BDF8' }} />
                <span>Historical Climatological Regimes &amp; Extreme Miss Patterns (2018–2021)</span>
              </div>
              <div className="analysis-section-subtitle">
                Systematic bias patterns across seasons and high-impact precipitation verification metrics.
              </div>
            </div>

            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Archive Depth: {operationalMisses.nSamples?.toLocaleString() || '27,328'} grid-hours
            </span>
          </div>

          <div className="patterns-grid">
            {/* Seasonal Climatology Comparison */}
            <div className="pattern-card">
              <div className="pattern-card-title">
                <LayersIcon size={15} style={{ color: '#38BDF8' }} />
                <span>Seasonal Climatology (Bust Frequency at Day {selectedLeadDay})</span>
              </div>

              <div className="seasonal-comparison-list">
                {seasonalBreakdown.map((s) => (
                  <div key={s.seasonKey} className="seasonal-comparison-item">
                    <div className="seasonal-item-header">
                      <span className="seasonal-item-name">{s.seasonName}</span>
                      <span className="seasonal-item-stat">
                        Bust: <strong style={{ color: 'var(--text-primary)' }}>{s.bustRate}%</strong> &bull; MAE: {s.meanAbsErrorPrecipMm}mm
                      </span>
                    </div>
                    <div className="season-bar-track" style={{ height: '7px' }}>
                      <div
                        className="season-bar-fill"
                        style={{
                          width: `${Math.min(100, s.bustRate * 1.8)}%`,
                          backgroundColor: s.color,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>

              <div style={{ fontSize: '11px', color: 'var(--text-secondary)', lineHeight: 1.45, marginTop: '4px' }}>
                Vulnerable Season: <strong style={{ color: '#38BDF8' }}>{activeProfile.vulnerableSeason}</strong>. Peak error variance occurs during high-volume convective setups where sub-grid parameterization drifts rapidly.
              </div>
            </div>

            {/* Operational Extreme Misses Archive */}
            <div className="pattern-card">
              <div className="pattern-card-title">
                <AlertTriangleIcon size={15} style={{ color: '#F87171' }} />
                <span>Operational Extreme Rainfall Events (2018–2021 Database)</span>
              </div>

              <div className="extreme-misses-grid">
                <div className="extreme-miss-box">
                  <span className="extreme-miss-title">Missed Heavy Rain</span>
                  <span className="extreme-miss-count tabular-nums" style={{ color: '#F87171' }}>
                    {operationalMisses.missedHeavyRain || 198}
                  </span>
                  <span className="extreme-miss-sub">
                    Obs &ge; 64.5mm missed by deterministic NWP run
                  </span>
                </div>

                <div className="extreme-miss-box">
                  <span className="extreme-miss-title">False Alarm Heavy</span>
                  <span className="extreme-miss-count tabular-nums" style={{ color: '#FBBF24' }}>
                    {operationalMisses.falseAlarmHeavyRain || 149}
                  </span>
                  <span className="extreme-miss-sub">
                    Fcst &ge; 64.5mm not observed at grid points
                  </span>
                </div>
              </div>

              <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', lineHeight: 1.45, marginTop: '4px' }}>
                <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>Operational Diagnostic: </span>
                {activeProfile.dominantError}. Early lead-time alerts provide critical early warning for state disaster management authorities to position emergency response assets.
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
