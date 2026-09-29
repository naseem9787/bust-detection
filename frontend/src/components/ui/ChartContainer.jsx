/**
 * Scientific Chart Container Primitive
 * Standardized framing, grid lines, units, and axis conventions for verification curves
 */

import React from 'react';

export function ChartContainer({
  title,
  subtitle,
  unit,
  legend = [], // Array of { label, color, dashed? }
  actions = null,
  height = 180,
  children,
  className = '',
}) {
  return (
    <div className={`chart-shell ${className}`}>
      <div className="chart-header">
        <div>
          <div className="chart-title">{title}</div>
          {subtitle && <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{subtitle}</div>}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          {unit && (
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
              Unit: [{unit}]
            </span>
          )}

          {legend.length > 0 && (
            <div className="chart-legend-row">
              {legend.map((item, idx) => (
                <div key={idx} className="chart-legend-item">
                  <span
                    className="chart-legend-indicator"
                    style={{
                      backgroundColor: item.color,
                      borderTop: item.dashed ? `1px dashed ${item.color}` : 'none',
                    }}
                  />
                  <span>{item.label}</span>
                </div>
              ))}
            </div>
          )}

          {actions}
        </div>
      </div>

      <div className="chart-body-canvas" style={{ height: `${height}px` }}>
        {/* Subtle reference gridlines */}
        <div className="chart-gridline" style={{ top: '25%' }} />
        <div className="chart-gridline" style={{ top: '50%' }} />
        <div className="chart-gridline" style={{ top: '75%' }} />

        {children}
      </div>
    </div>
  );
}
