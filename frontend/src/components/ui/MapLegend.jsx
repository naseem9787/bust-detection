/**
 * MapLegend Component
 * Clearly explains the scientific scale and color semantics for spatial meteorological risk.
 * Semantics:
 * - Low risk -> cool/neutral (teal/green)
 * - Moderate risk -> warning range (amber/orange)
 * - High risk -> danger range (red/crimson)
 */

import React from 'react';
import { TOKENS } from '../../design-system/tokens.js';

export function MapLegend({
  mode = 'risk', // 'risk' | 'confidence' | 'precip'
  className = '',
}) {
  if (mode === 'confidence') {
    return (
      <div className={`legend-panel ${className}`} role="region" aria-label="Forecast Confidence Legend">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <span className="legend-title">Forecast Confidence Scale (Calibrated)</span>
          <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            ECMWF Ensemble Spread
          </span>
        </div>

        <div className="legend-discrete-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: TOKENS.colors.confidence.high.color }} />
            <span>High (&ge;80%)</span>
          </div>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: TOKENS.colors.confidence.moderate.color }} />
            <span>Moderate (50–79%)</span>
          </div>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: TOKENS.colors.confidence.low.color }} />
            <span>Low / Uncertain (&lt;50%)</span>
          </div>
        </div>
      </div>
    );
  }

  if (mode === 'precip') {
    return (
      <div className={`legend-panel ${className}`} role="region" aria-label="Precipitation Error Scale">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <span className="legend-title">Mean Absolute Precipitation Error</span>
          <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
            ERA5 Truth (mm/day)
          </span>
        </div>

        <div className="legend-discrete-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: '#38BDF8' }} />
            <span>Nominal (&le;5 mm)</span>
          </div>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: '#0EA5E9' }} />
            <span>Elevated (5–12 mm)</span>
          </div>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: '#0284C7' }} />
            <span>Severe Miss (&gt;12 mm)</span>
          </div>
        </div>
      </div>
    );
  }

  // Default: Bust Risk Scale (Cool/Neutral -> Warning -> Danger)
  return (
    <div className={`legend-panel ${className}`} role="region" aria-label="Bust Probability Scale">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="legend-title">Forecast Bust Probability Scale</span>
          <span style={{ fontSize: '9.5px', color: 'var(--text-muted)' }}>
            (Cool = Nominal &bull; Amber = Warning &bull; Red = Danger)
          </span>
        </div>
        <span style={{ fontSize: '9.5px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
          90th %ile Threshold: 35%
        </span>
      </div>

      {/* Discrete 5-tier ramp bar */}
      <div className="legend-ramp-bar">
        <div className="legend-ramp-segment" style={{ backgroundColor: '#10B981' }} title="Low Risk (<15%)" />
        <div className="legend-ramp-segment" style={{ backgroundColor: '#F59E0B' }} title="Moderate Risk (15-25%)" />
        <div className="legend-ramp-segment" style={{ backgroundColor: '#F97316' }} title="Elevated Risk (25-35%)" />
        <div className="legend-ramp-segment" style={{ backgroundColor: '#EF4444' }} title="High Risk (35-45%)" />
        <div className="legend-ramp-segment" style={{ backgroundColor: '#991B1B' }} title="Severe Bust (≥45%)" />
      </div>

      {/* Clear numeric labels below each tier */}
      <div className="legend-labels">
        <span style={{ color: '#34D399' }}>Low &lt;15%</span>
        <span style={{ color: '#FBBF24' }}>15–25%</span>
        <span style={{ color: '#FB923C' }}>25–35%</span>
        <span style={{ color: '#F87171' }}>35–45%</span>
        <span style={{ color: '#FCA5A5', fontWeight: 600 }}>Severe &ge;45%</span>
      </div>
    </div>
  );
}
