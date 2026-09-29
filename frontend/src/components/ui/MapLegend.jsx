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
      <div className={`legend-panel ${className}`} role="region" aria-label="Forecast Reliability Legend">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
          <span className="legend-title">Forecast Reliability</span>
          <span style={{ fontSize: '9.5px', color: 'var(--text-muted)' }} title="Reliability = 100% minus the chance of a major forecast error.">
            100% &minus; chance of error
          </span>
        </div>

        <div className="legend-discrete-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)' }}>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: TOKENS.colors.confidence.high.color }} />
            <span>High (&ge;97%)</span>
          </div>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: TOKENS.colors.confidence.moderate.color }} />
            <span>Moderate (94&ndash;97%)</span>
          </div>
          <div className="legend-discrete-item">
            <span className="legend-color-chip" style={{ backgroundColor: TOKENS.colors.confidence.low.color }} />
            <span>Low (&lt;94%)</span>
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

  // Default: Chance of Major Forecast Error scale (green -> yellow -> orange -> red)
  // Bins come from the real distribution of the production model's output
  // across all states/lead days (see weatherRules.js getBustRiskLevel) -
  // not an assumed or invented scale.
  return (
    <div className={`legend-panel ${className}`} role="region" aria-label="Chance of Major Forecast Error Scale">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
        <span className="legend-title">Chance of Major Forecast Error</span>
        <span style={{ fontSize: '9.5px', color: 'var(--text-muted)' }} title="Estimated chance that the forecast will be substantially wrong for this state.">
          Low &rarr; High
        </span>
      </div>

      {/* Discrete 4-tier ramp bar */}
      <div className="legend-ramp-bar">
        <div className="legend-ramp-segment" style={{ backgroundColor: '#10B981' }} title="Low (below 1%)" />
        <div className="legend-ramp-segment" style={{ backgroundColor: '#EAB308' }} title="Moderate (1-3%)" />
        <div className="legend-ramp-segment" style={{ backgroundColor: '#F97316' }} title="Elevated (3-6%)" />
        <div className="legend-ramp-segment" style={{ backgroundColor: '#EF4444' }} title="High (above 6%)" />
      </div>

      {/* Clear numeric labels below each tier - never rely on color alone */}
      <div className="legend-labels">
        <span style={{ color: '#34D399' }}>Low &lt;1%</span>
        <span style={{ color: '#FDE047' }}>Moderate 1&ndash;3%</span>
        <span style={{ color: '#FB923C' }}>Elevated 3&ndash;6%</span>
        <span style={{ color: '#F87171', fontWeight: 600 }}>High &gt;6%</span>
      </div>
    </div>
  );
}
