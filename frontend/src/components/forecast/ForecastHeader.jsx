/**
 * ForecastHeader Component
 * Displays model initialization metadata, active cycle details, and
 * directly answers: "Where is the forecast most likely to bust, at what lead time, and why?"
 */

import React from 'react';
import { AlertTriangleIcon, InfoIcon, ShieldCheckIcon } from '../icons/Icons.jsx';
import { RiskBadge } from '../ui/RiskBadge.jsx';

export function ForecastHeader({
  cycle = '2026-09-29 00Z',
  leadDay = 5,
  topRiskRegion = 'West Coast',
  topRiskProbability = 0.487,
  primaryTrigger = 'IMD rainfall category shift (moderate -> heavy miss)',
  className = '',
}) {
  const currentLeadHours = leadDay * 24;
  const isHighBust = topRiskProbability >= 0.40;

  return (
    <div className={`forecast-header-card ${className}`}>
      {/* Top Metadata Row */}
      <div className="forecast-header-meta-row">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)', fontSize: '10px' }}>NWP CYCLE</span>
          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
            {cycle}
          </span>
          <span style={{ color: 'var(--text-muted)' }}>&bull;</span>
          <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
            ECMWF HRES (0.25°/1.5° WeatherBench2)
          </span>
          <span style={{ color: 'var(--text-muted)' }}>&bull;</span>
          <span style={{ fontSize: '12px', color: '#38BDF8', fontWeight: 500 }}>
            Target: Day {leadDay} (+{currentLeadHours}h Lead)
          </span>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
            <ShieldCheckIcon size={11} style={{ marginRight: '4px', color: '#10B981' }} />
            TRUTH: ERA5 Reanalysis
          </span>
        </div>
      </div>

      {/* Primary Intelligence Callout: Answers the Core Question at a Glance */}
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
              Primary Intelligence Query &bull; Where is the forecast most likely to bust?
            </div>
            <div style={{ fontSize: '13px', color: 'var(--text-primary)', fontWeight: 500 }}>
              At <strong>Day {leadDay} (+{currentLeadHours}h)</strong>, highest bust likelihood is in{' '}
              <strong style={{ color: '#38BDF8' }}>{topRiskRegion}</strong> with{' '}
              <span className="tabular-nums" style={{ fontWeight: 700 }}>
                {(topRiskProbability * 100).toFixed(1)}%
              </span>{' '}
              bust probability. Trigger: <em>{primaryTrigger}</em>.
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
