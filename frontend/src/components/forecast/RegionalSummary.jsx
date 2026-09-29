/**
 * RegionalSummary Component
 * Detailed intelligence analysis panel for the selected region.
 * Displays: Region, Bust Probability, Confidence, Expected Error, Historical Bust Rate, Primary Explanation.
 */

import React from 'react';
import { RiskBadge } from '../ui/RiskBadge.jsx';
import { ConfidenceIndicator } from './ConfidenceIndicator.jsx';
import { AlertTriangleIcon, RadarIcon } from '../icons/Icons.jsx';
import { getBustRiskLevel } from '../../utils/weatherRules.js';
import { formatPercent, formatPrecip, formatTemp, formatPressure } from '../../utils/formatters.js';

function RegionalSummaryComponent({
  region,
  forecastData,
  explanationData,
  className = '',
}) {
  if (!region || !forecastData) {
    return (
      <div className={`regional-summary-panel empty-state ${className}`}>
        <span style={{ color: 'var(--text-muted)' }}>Select a region on the map to inspect verification details.</span>
      </div>
    );
  }

  const { verification, variables, meta } = forecastData;
  const bustProbability = verification?.bustProbability ?? 0.35;
  const confidence = verification?.confidence ?? 0.60;
  const riskLevel = verification?.riskLevel || getBustRiskLevel(bustProbability);

  const precip = variables?.precipitation || {};
  const temp = variables?.temperature || {};
  const mslp = variables?.meanSeaLevelPressure || {};
  const factors = explanationData?.factors || [];
  const bulletinSummary = explanationData?.bulletinSummary || 'Evaluating ensemble spread and synoptic jumpiness.';

  return (
    <div className={`regional-summary-panel ${className}`}>
      {/* 1. Region Header */}
      <div className="regional-summary-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <RadarIcon size={15} style={{ color: '#38BDF8' }} />
            <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
              {region.shortName}
            </h2>
          </div>
          <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {region.bbox ? `${region.bbox.latMin}°–${region.bbox.latMax}°N &bull; ${region.bbox.lonMin}°–${region.bbox.lonMax}°E` : region.name}
          </div>
        </div>

        <RiskBadge level={riskLevel} />
      </div>

      {/* 2. Core Metrics: Visual Emphasis on Bust Probability & Confidence */}
      <div className="regional-metrics-hero">
        {/* Bust Probability Hero Block */}
        <div className="bust-prob-hero-card">
          <div className="stat-label">Bust Probability</div>
          <div className="bust-prob-value tabular-nums">
            {formatPercent(bustProbability * 100)}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Exceeds 90th percentile threshold for Day {meta?.leadDay ?? 5}
          </div>
        </div>

        {/* Confidence Indicator Meter */}
        <div className="confidence-hero-card">
          <ConfidenceIndicator confidence={confidence} />
        </div>
      </div>

      {/* 3. Expected Forecast Errors Breakdown */}
      <div className="expected-errors-section">
        <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '6px' }}>
          Expected Pointwise Errors (ECMWF vs ERA5)
        </div>

        <div className="errors-grid">
          {/* Precipitation Error */}
          <div className="error-item-box">
            <span className="error-item-label">Precipitation |Error|</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span className="error-item-value tabular-nums">
                {formatPrecip(precip.absError)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                (Fcst: {formatPrecip(precip.forecastValue)} / Obs: {formatPrecip(precip.observedValue)})
              </span>
            </div>
            {precip.categoryShift >= 2 && (
              <div style={{ fontSize: '10px', color: '#F97316', marginTop: '2px', fontWeight: 500 }}>
                &bull; IMD Shift: {precip.categoryShift} categories apart
              </div>
            )}
            {precip.missedHeavyRain && (
              <div style={{ fontSize: '10px', color: '#EF4444', fontWeight: 600 }}>
                &bull; Missed Heavy Rain Event (&ge;64.5mm)
              </div>
            )}
          </div>

          {/* Temperature Error */}
          <div className="error-item-box">
            <span className="error-item-label">2m Air Temp |Error|</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span className="error-item-value tabular-nums">
                {formatTemp(temp.absError)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                ({formatTemp(temp.forecastValue)} vs {formatTemp(temp.observedValue)})
              </span>
            </div>
            <div style={{ fontSize: '10px', color: temp.heatwaveMissFlag ? '#EF4444' : 'var(--text-muted)', marginTop: '2px' }}>
              {temp.heatwaveMissFlag ? '&bull; Heatwave miss: >3.0°C threshold exceeded' : '&bull; Within normal thermal range'}
            </div>
          </div>

          {/* Pressure & Historical Baseline */}
          <div className="error-item-box" style={{ gridColumn: 'span 2' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="error-item-label">Historical Baseline Bust Rate</span>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {region.baselineRisk ? `${(region.baselineRisk * 100).toFixed(1)}%` : '42.9%'} (2018–2021 JJAS aggregate)
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span className="error-item-label">MSLP Bias</span>
                <div className="tabular-nums" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {formatPressure(mslp.absError)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Primary Explanation & Why Confidence is Low */}
      <div className="explainability-container">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
          <AlertTriangleIcon size={14} style={{ color: '#F59E0B' }} />
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#FBBF24', letterSpacing: '0.02em' }}>
            Primary Explanation &bull; Why is Confidence Low?
          </span>
        </div>

        {/* Forecaster Bulletin Summary */}
        <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '8px', padding: '6px 8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-xs)' }}>
          {bulletinSummary}
        </div>

        {/* Feature Attribution Factors */}
        <div className="attribution-factors-list">
          {factors.map((factor) => {
            const contributionPercent = Math.round(factor.contribution * 100);
            return (
              <div key={factor.factorId} className="attribution-factor-row">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '2px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '11px' }}>
                    {factor.name}
                  </span>
                  <span className="tabular-nums" style={{ fontSize: '10.5px', fontWeight: 600, color: '#F97316' }}>
                    +{contributionPercent}% Risk
                  </span>
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                  {factor.description}
                </div>
                {factor.evidenceValue && (
                  <div style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '1px', fontFamily: 'var(--font-mono)' }}>
                    Evidence: {factor.evidenceValue}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
export const RegionalSummary = React.memo(RegionalSummaryComponent);
