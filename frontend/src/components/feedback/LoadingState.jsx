/**
 * Global Loading State Component
 * Restrained, meteorological radar sweep indicator with informative status text.
 */

import React from 'react';
import { RadarIcon } from '../icons/Icons.jsx';

export function LoadingState({
  message = 'Loading Medium-Range Forecast & Verification Data...',
  subtext = 'Processing ECMWF HRES deterministic run vs ERA5 climatology',
  className = '',
}) {
  return (
    <div
      className={`loading-container ${className}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '60px 20px',
        textAlign: 'center',
        gap: '12px',
        minHeight: '280px',
      }}
      role="status"
      aria-live="polite"
    >
      <div
        className="loading-radar-ring"
        style={{
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          width: '48px',
          height: '48px',
          borderRadius: '50%',
          backgroundColor: 'rgba(2, 132, 199, 0.1)',
          border: '1px solid rgba(56, 189, 248, 0.25)',
        }}
      >
        <RadarIcon size={24} className="loading-radar-icon" style={{ color: '#38BDF8' }} />
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
          {message}
        </span>
        {subtext && (
          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
            {subtext}
          </span>
        )}
      </div>
    </div>
  );
}
