/**
 * RegionalSummary Component
 * Detailed panel for the selected state: chance of a major forecast
 * error, forecast reliability, expected forecast error, and why the
 * model is flagging it (model evidence + historical context).
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
        <span style={{ color: 'var(--text-muted)' }}>Select a state on the map to see its forecast.</span>
      </div>
    );
  }

  const { verification, variables, meta } = forecastData;
  const bustProbability = verification?.bustProbability ?? 0.01;
  const confidence = verification?.confidence ?? 0.99;
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
            {meta?.leadDay ? `Forecast for ${meta.leadDay} day${meta.leadDay === 1 ? '' : 's'} ahead` : region.name}
          </div>
        </div>

        <RiskBadge level={riskLevel} />
      </div>

      {/* 2. Core Metrics: Chance of Error & Reliability */}
      <div className="regional-metrics-hero">
        {/* Chance of Major Forecast Error Hero Block */}
        <div className="bust-prob-hero-card">
          <div className="stat-label">Chance of Major Forecast Error</div>
          <div className="bust-prob-value tabular-nums">
            {formatPercent(bustProbability * 100)}
          </div>
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Estimated chance this forecast turns out substantially wrong here
          </div>
        </div>

        {/* Reliability Indicator Meter */}
        <div className="confidence-hero-card">
          <ConfidenceIndicator confidence={confidence} />
        </div>
      </div>

      {/* 3. Expected Forecast Error Breakdown */}
      <div className="expected-errors-section">
        <div style={{ fontSize: '11px', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-muted)', marginBottom: '6px' }}>
          Verified Forecast Error (archived case vs ERA5)
        </div>

        <div className="errors-grid">
          {/* Rainfall Error */}
          <div className="error-item-box">
            <span className="error-item-label">Rainfall Error</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span className="error-item-value tabular-nums">
                {formatPrecip(precip.absError)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                (Forecast: {formatPrecip(precip.forecastValue)} / Observed: {formatPrecip(precip.observedValue)})
              </span>
            </div>
            {precip.categoryShift >= 2 && (
              <div style={{ fontSize: '10px', color: '#F97316', marginTop: '2px', fontWeight: 500 }}>
                &bull; Rainfall may be significantly different from what was forecast
              </div>
            )}
            {precip.missedHeavyRain && (
              <div style={{ fontSize: '10px', color: '#EF4444', fontWeight: 600 }}>
                &bull; A heavy rain event may have been missed
              </div>
            )}
          </div>

          {/* Temperature Error */}
          <div className="error-item-box">
            <span className="error-item-label">Temperature Error</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span className="error-item-value tabular-nums">
                {formatTemp(temp.absError)}
              </span>
              <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                ({formatTemp(temp.forecastValue)} vs {formatTemp(temp.observedValue)})
              </span>
            </div>
            <div style={{ fontSize: '10px', color: temp.heatwaveMissFlag ? '#EF4444' : 'var(--text-muted)', marginTop: '2px' }}>
              {temp.heatwaveMissFlag ? '• Possible heatwave miss: temperature error over 3°C' : '• Within normal range'}
            </div>
          </div>

          {/* Pressure & Historical Baseline */}
          <div className="error-item-box" style={{ gridColumn: 'span 2' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <span className="error-item-label">How Often This Has Happened Before</span>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {region.baselineRisk != null ? `${(region.baselineRisk * 100).toFixed(1)}%` : '—'} of forecasts here (2018–2021)
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span className="error-item-label">Air Pressure Difference</span>
                <div className="tabular-nums" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                  {formatPressure(mslp.absError)}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 4. Why Might This Forecast Be Wrong? (model evidence + historical context) */}
      <div className="explainability-container">
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '4px' }}>
          <AlertTriangleIcon size={14} style={{ color: '#F59E0B' }} />
          <span style={{ fontSize: '12px', fontWeight: 700, color: '#FBBF24', letterSpacing: '0.02em' }}>
            Why Might This Forecast Be Wrong?
          </span>
        </div>

        {/* Forecaster Bulletin Summary */}
        <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', lineHeight: 1.5, marginBottom: '8px', padding: '6px 8px', backgroundColor: 'rgba(0,0,0,0.2)', borderRadius: 'var(--radius-xs)' }}>
          {bulletinSummary}
        </div>

        {/* Model evidence + historical context - each factor tagged by source */}
        <div className="attribution-factors-list">
          {factors.map((factor) => {
            // contribution is a SHAP value in log-odds - show direction + raw value, never as a "% risk"
            const hasContribution = typeof factor.contribution === 'number';
            const raisesRisk = hasContribution && factor.contribution >= 0;
            const isHistorical = factor.source === 'historical_context';
            return (
              <div key={factor.factorId} className="attribution-factor-row">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '2px' }}>
                  <span style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '11px' }}>
                    {factor.name}
                  </span>
                  {hasContribution ? (
                    <span
                      className="tabular-nums"
                      style={{ fontSize: '10.5px', fontWeight: 600, color: raisesRisk ? '#F97316' : '#34D399' }}
                      title="SHAP contribution (log-odds) to this forecast's bust probability"
                    >
                      {raisesRisk ? '▲ raises risk' : '▼ lowers risk'} · SHAP {raisesRisk ? '+' : '−'}{Math.abs(factor.contribution).toFixed(2)}
                    </span>
                  ) : (
                    <span
                      className="badge badge-neutral"
                      style={{ fontSize: '9px', padding: '1px 5px' }}
                    >
                      Similar past case
                    </span>
                  )}
                </div>
                <div style={{ fontSize: '10px', color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                  {isHistorical ? factor.plainReason : factor.description}
                </div>
                {factor.evidenceValue && (
                  <div style={{ fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '1px', fontFamily: 'var(--font-mono)' }}>
                    {factor.evidenceValue}
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
