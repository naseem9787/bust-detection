/**
 * Calibrated Forecast Confidence Indicator Component
 * Reusable scientific confidence gauge distinguishing calibrated skill tiers:
 * High (>= 80%), Moderate (50-79%), Low (< 50%)
 *
 * Designed for scientific decision support — no glowing neon or generic AI effects.
 */

import React from 'react';
import { TOKENS } from '../../design-system/tokens.js';
import { getConfidenceTier } from '../../utils/weatherRules.js';
import { Tooltip } from '../ui/Tooltip.jsx';
import { InfoIcon } from '../icons/Icons.jsx';

function ConfidenceIndicatorComponent({
  confidence = 0.27,
  showMeter = true,
  showThresholds = true,
  leadDay = null,
  className = '',
}) {
  const score = confidence > 1 ? confidence / 100 : confidence;
  const percent = Math.round(score * 100);
  const tier = getConfidenceTier(score);
  const confInfo = TOKENS.colors.confidence[tier] || TOKENS.colors.confidence.low;

  return (
    <div className={`confidence-indicator-block ${className}`}>
      <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: '6px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: 600 }}>
            Forecast Confidence
          </span>
          <Tooltip content="Calibrated probability score derived from historical reliability and ensemble dispersion. A score of 27% indicates high forecast uncertainty.">
            <span style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}>
              <InfoIcon size={12} style={{ color: 'var(--text-muted)' }} />
            </span>
          </Tooltip>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            className="tabular-nums"
            style={{ fontSize: '24px', fontWeight: 700, color: confInfo.color, lineHeight: 1 }}
          >
            {percent}%
          </span>
          <span
            className={`badge badge-conf-${tier === 'moderate' ? 'mod' : tier}`}
            style={{ fontSize: '10.5px', padding: '2px 8px', fontWeight: 600 }}
          >
            {confInfo.label} Skill
          </span>
        </div>
      </div>

      {showMeter && (
        <div
          className="confidence-meter-track"
          style={{ height: '8px', backgroundColor: 'var(--bg-canvas)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-pill)', position: 'relative', overflow: 'hidden' }}
          title={`Calibrated Skill Score: ${percent}% (${confInfo.label})`}
        >
          {/* Calibrated Fill Bar */}
          <div
            className="confidence-meter-fill"
            style={{
              width: `${percent}%`,
              backgroundColor: confInfo.color,
              height: '100%',
              borderRadius: 'var(--radius-pill)',
              transition: 'width 250ms ease',
            }}
          />
          {/* Calibration benchmark markers */}
          <div
            style={{
              position: 'absolute',
              left: '50%',
              top: 0,
              bottom: 0,
              width: '1px',
              backgroundColor: 'rgba(255, 255, 255, 0.35)',
              zIndex: 2,
            }}
            title="50% Moderate Skill Threshold"
          />
          <div
            style={{
              position: 'absolute',
              left: '80%',
              top: 0,
              bottom: 0,
              width: '1px',
              backgroundColor: 'rgba(255, 255, 255, 0.35)',
              zIndex: 2,
            }}
            title="80% High Skill Threshold"
          />
        </div>
      )}

      {showThresholds && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
          <span>0% (High Uncertainty)</span>
          <span>50% (Moderate)</span>
          <span>80% (High Skill)</span>
          <span>100%</span>
        </div>
      )}

      {leadDay && (
        <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: 1.4 }}>
          {percent < 50 ? (
            <span>
              Confidence at Lead Day {leadDay} is constrained below the 50% operational reliability threshold. Decision makers should cross-verify with ensemble scenarios.
            </span>
          ) : (
            <span>
              Forecast skill at Lead Day {leadDay} conforms with operational standards.
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export const ConfidenceIndicator = React.memo(ConfidenceIndicatorComponent);
