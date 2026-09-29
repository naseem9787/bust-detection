/**
 * ReplayOutcomeComparison Component
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 *
 * Compares Model Forecast vs Ground Truth Historical Outcome:
 * - Deterministic NWP forecast (Precipitation, Temperature)
 * - Model predictions (Bust probability, calibrated confidence)
 * - Ground truth observed outcome (IMD AWS network / ERA5 reanalysis)
 * - Error magnitude, IMD category shift, and verification verdict
 */

import React from 'react';
import { RiskBadge } from '../ui/RiskBadge.jsx';
import {
  AlertTriangleIcon,
  ShieldCheckIcon,
  CloudRainIcon,
  ThermometerIcon,
  CheckCircleIcon,
} from '../icons/Icons.jsx';
import { formatPrecip, formatTemp } from '../../utils/formatters.js';

function ReplayOutcomeComparisonComponent({
  predictionSummary = {},
  historicalOutcome = {},
  leadDay = 5,
  regionName = 'West Coast',
  className = '',
}) {
  const {
    forecastPrecipMm = 58.4,
    forecastTempC = 27.2,
    bustProbability = 0.84,
    confidence = 0.22,
    riskLevel = 'extreme',
    imdForecastCategory = 'Moderate Rain (15.6–64.4mm)',
  } = predictionSummary;

  const {
    observedPrecipMm = 218.6,
    observedTempC = 25.4,
    observedMslpHpa = 1006.2,
    imdObservedCategory = 'Extremely Heavy Rain (≥204.5mm)',
    precipitationDelta = 160.2,
    temperatureDelta = -1.8,
    categoryShift = 3,
    percentileExceeded = true,
    verdict = 'VERIFIED BUST',
    verdictSeverity = 'danger',
    verdictSummary = '',
  } = historicalOutcome;

  const isBust = verdict.includes('BUST');
  const verdictColor =
    verdictSeverity === 'danger'
      ? '#EF4444'
      : verdictSeverity === 'warning'
      ? '#F59E0B'
      : '#10B981';

  return (
    <div className={`replay-comparison-container ${className}`} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
      {/* 1. Ground Truth Verification Verdict Banner */}
      <div
        style={{
          backgroundColor: isBust ? 'rgba(239, 68, 68, 0.08)' : 'rgba(16, 185, 129, 0.08)',
          border: `1px solid ${isBust ? 'rgba(239, 68, 68, 0.3)' : 'rgba(16, 185, 129, 0.3)'}`,
          borderRadius: 'var(--radius-md)',
          padding: '12px 16px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '10px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          {isBust ? (
            <AlertTriangleIcon size={18} style={{ color: '#EF4444' }} />
          ) : (
            <CheckCircleIcon size={18} style={{ color: '#10B981' }} />
          )}
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '13px', fontWeight: 700, color: verdictColor, letterSpacing: '0.02em' }}>
                VERIFICATION VERDICT: {verdict}
              </span>
              <span
                className="badge"
                style={{
                  backgroundColor: 'rgba(255, 255, 255, 0.06)',
                  color: 'var(--text-secondary)',
                  fontSize: '10px',
                  fontFamily: 'var(--font-mono)',
                }}
              >
                Lead Day {leadDay} (+{leadDay * 24}h)
              </span>
            </div>
            <div style={{ fontSize: '11.5px', color: 'var(--text-secondary)', marginTop: '2px', lineHeight: 1.4 }}>
              {verdictSummary || `Ground truth evaluation confirms forecast deviation exceeded operational threshold tolerance.`}
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {percentileExceeded && (
            <span
              className="badge badge-risk-high"
              style={{ fontSize: '10px', padding: '3px 8px' }}
              title="Error exceeded the 90th climatological percentile threshold (35mm)"
            >
              90th %ile Bust Threshold Exceeded
            </span>
          )}
          {categoryShift >= 2 && (
            <span
              className="badge badge-risk-elevated"
              style={{ fontSize: '10px', padding: '3px 8px' }}
              title="Forecast drifted across multiple IMD rainfall categories"
            >
              &Delta; {categoryShift} IMD Categories Apart
            </span>
          )}
        </div>
      </div>

      {/* 2. Side-by-Side Analytical Comparison: Forecast vs Ground Truth */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
          gap: '14px',
        }}
      >
        {/* Model Forecast Card */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <ShieldCheckIcon size={14} style={{ color: '#38BDF8' }} />
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Numerical Model Forecast (ECMWF)
              </span>
            </div>
            <RiskBadge level={riskLevel} showLabel={false} />
          </div>

          {/* Model Predictions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Precipitation Forecast */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CloudRainIcon size={13} style={{ color: '#38BDF8' }} />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Forecast Precipitation:</span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span className="tabular-nums" style={{ fontSize: '14px', fontWeight: 700, color: '#38BDF8' }}>
                  {formatPrecip(forecastPrecipMm)}
                </span>
                <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                  {imdForecastCategory}
                </div>
              </div>
            </div>

            {/* Temperature Forecast */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ThermometerIcon size={13} style={{ color: '#F59E0B' }} />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Forecast 2m Temp:</span>
              </div>
              <span className="tabular-nums" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                {formatTemp(forecastTempC)}
              </span>
            </div>

            {/* AI Bust Probability Assessment */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>AI Bust Probability:</span>
              <span className="tabular-nums" style={{ fontSize: '15px', fontWeight: 700, color: isBust ? '#F87171' : '#FBBF24' }}>
                {Math.round(bustProbability * 100)}% P(Bust)
              </span>
            </div>

            {/* AI Calibrated Confidence */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Calibrated Confidence:</span>
              <span className="tabular-nums" style={{ fontSize: '13px', fontWeight: 700, color: confidence < 0.4 ? '#F87171' : '#38BDF8' }}>
                {Math.round(confidence * 100)}% ({confidence < 0.4 ? 'Low Skill' : confidence < 0.7 ? 'Moderate Skill' : 'High Skill'})
              </span>
            </div>
          </div>
        </div>

        {/* Observed Ground Truth Card */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            padding: '16px',
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <CheckCircleIcon size={14} style={{ color: '#10B981' }} />
              <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
                Ground Truth Outcome &bull; {regionName}
              </span>
            </div>
            <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Verified Observation
            </span>
          </div>

          {/* Actual Observed Metrics */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {/* Observed Precipitation */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <CloudRainIcon size={13} style={{ color: '#10B981' }} />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Observed Precipitation:</span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span className="tabular-nums" style={{ fontSize: '14px', fontWeight: 700, color: '#10B981' }}>
                  {formatPrecip(observedPrecipMm)}
                </span>
                <div style={{ fontSize: '10px', color: '#F87171', fontWeight: 600 }}>
                  {imdObservedCategory}
                </div>
              </div>
            </div>

            {/* Observed Temperature */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <ThermometerIcon size={13} style={{ color: '#F59E0B' }} />
                <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Observed 2m Temp:</span>
              </div>
              <div style={{ textAlign: 'right' }}>
                <span className="tabular-nums" style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {formatTemp(observedTempC)}
                </span>
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                  (&Delta; {temperatureDelta > 0 ? `+${temperatureDelta}` : temperatureDelta}°C)
                </span>
              </div>
            </div>

            {/* Observed MSLP */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Observed MSLP:</span>
              <span className="tabular-nums" style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                {observedMslpHpa} hPa
              </span>
            </div>

            {/* Ground Truth Error Delta */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline' }}>
              <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Precipitation Delta (&Delta;):</span>
              <span
                className="tabular-nums"
                style={{
                  fontSize: '14px',
                  fontWeight: 700,
                  color: precipitationDelta > 0 ? '#F87171' : '#38BDF8',
                }}
              >
                {precipitationDelta > 0 ? `+${precipitationDelta}` : precipitationDelta} mm/24h
                <span style={{ fontSize: '10.5px', color: 'var(--text-muted)', marginLeft: '4px' }}>
                  ({precipitationDelta > 0 ? 'Underpredicted' : 'Overpredicted'})
                </span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
export const ReplayOutcomeComparison = React.memo(ReplayOutcomeComparisonComponent);
