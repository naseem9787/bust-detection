/**
 * ForecastHeader Component
 * Displays model initialization metadata, active cycle details, and
 * directly answers: "Where is the forecast most likely to bust, at what lead time, and why?"
 */

import React from 'react';
import { AlertTriangleIcon, InfoIcon, ShieldCheckIcon } from '../icons/Icons.jsx';
import { RiskBadge } from '../ui/RiskBadge.jsx';

export function ForecastHeader({
  cycle = '2021-09-30 12Z',
  leadDay = 5,
  topRiskRegion = 'West Coast',
  topRiskProbability = 0.01,
  primaryTrigger = 'Rainfall category may be significantly different from the forecast',
  className = '',
}) {
  // Matches the real "high" risk band used everywhere else on this page
  // (map, legend, panel) - see weatherRules.js getBustRiskLevel.
  const isHighBust = topRiskProbability >= 0.06;

  return (
    <div className={`forecast-header-card ${className}`}>
      {/* Top Metadata Row */}
      <div className="forecast-header-meta-row">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>FORECAST RUN</span>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {cycle}
          </span>
          <span style={{ color: 'var(--text-muted)' }}>&bull;</span>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            ECMWF HRES (1.5°, WeatherBench2)
          </span>
          <span style={{ color: 'var(--text-muted)' }}>&bull;</span>
          <span style={{ fontSize: '12px', color: '#38BDF8', fontWeight: 500 }}>
            {leadDay} day{leadDay === 1 ? '' : 's'} ahead
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
            <ShieldCheckIcon size={11} style={{ marginRight: '4px', color: '#10B981' }} />
            Checked against real recorded weather (ERA5)
          </span>
        </div>
      </div>

      {/* Primary Callout: Highest Forecast Risk */}
      <div className={`forecast-primary-callout ${isHighBust ? 'critical-risk' : 'nominal-risk'}`}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flex: 1, flexWrap: 'wrap' }}>
          <div className="callout-icon-box">
            {isHighBust ? (
              <AlertTriangleIcon size={18} style={{ color: '#EF4444' }} />
            ) : (
              <InfoIcon size={18} style={{ color: '#0284C7' }} />
            )}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', fontWeight: 700, color: isHighBust ? '#F87171' : '#38BDF8' }}>
              Highest Forecast Risk
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: 500 }}>
              <strong style={{ color: '#38BDF8' }}>{topRiskRegion}</strong> has the highest chance of a major forecast error:{' '}
              <span className="tabular-nums" style={{ fontWeight: 700 }}>
                {(topRiskProbability * 100).toFixed(1)}%
              </span>{' '}
              ({leadDay} day{leadDay === 1 ? '' : 's'} ahead). Why this forecast may be wrong: <em>{primaryTrigger}</em>.
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
          <RiskBadge probability={topRiskProbability} />
        </div>
      </div>
    </div>
  );
}
