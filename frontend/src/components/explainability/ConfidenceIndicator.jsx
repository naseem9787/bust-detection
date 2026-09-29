/**
 * Forecast Reliability Indicator Component
 * Reliability = 100% - chance of a major forecast error (the same number
 * shown everywhere else on the page - map, panel, tooltip). Tiers:
 * High (>= 97%), Moderate (94-97%), Low (< 94%) - see weatherRules.js
 * getConfidenceTier, based on the real distribution of model output.
 */

import React from 'react';
import { TOKENS } from '../../design-system/tokens.js';
import { getConfidenceTier } from '../../utils/weatherRules.js';
import { Tooltip } from '../ui/Tooltip.jsx';
import { InfoIcon } from '../icons/Icons.jsx';

function ConfidenceIndicatorComponent({
  confidence = 0.99,
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
            Forecast Reliability
          </span>
          <Tooltip content="How reliable this specific forecast is estimated to be. Reliability = 100% minus the chance of a major forecast error.">
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
            {confInfo.label} Reliability
          </span>
        </div>
      </div>

      {showMeter && (
        <div
          className="confidence-meter-track"
          style={{ height: '8px', backgroundColor: 'var(--bg-canvas)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-pill)', position: 'relative', overflow: 'hidden' }}
          title={`Reliability: ${percent}% (${confInfo.label})`}
        >
          {/* Reliability Fill Bar */}
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
          {/* Same 94%/97% cutoffs as getConfidenceTier - real data-based, not arbitrary */}
          <div
            style={{
              position: 'absolute',
              left: '94%',
              top: 0,
              bottom: 0,
              width: '1px',
              backgroundColor: 'rgba(255, 255, 255, 0.35)',
              zIndex: 2,
            }}
            title="94% Moderate Reliability cutoff"
          />
          <div
            style={{
              position: 'absolute',
              left: '97%',
              top: 0,
              bottom: 0,
              width: '1px',
              backgroundColor: 'rgba(255, 255, 255, 0.35)',
              zIndex: 2,
            }}
            title="97% High Reliability cutoff"
          />
        </div>
      )}

      {showThresholds && (
        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '9.5px', color: 'var(--text-muted)', marginTop: '4px', fontFamily: 'var(--font-mono)' }}>
          <span>Low</span>
          <span>94%</span>
          <span>97%</span>
          <span>100%</span>
        </div>
      )}

      {leadDay && (
        <div style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px', lineHeight: 1.4 }}>
          {percent < 94 ? (
            <span>
              At {leadDay} day{leadDay === 1 ? '' : 's'} ahead, this forecast has a higher than usual chance of being significantly wrong here. Treat it with extra caution.
            </span>
          ) : (
            <span>
              At {leadDay} day{leadDay === 1 ? '' : 's'} ahead, this forecast is within the normal, reliable range for this location.
            </span>
          )}
        </div>
      )}
    </div>
  );
}

export const ConfidenceIndicator = React.memo(ConfidenceIndicatorComponent);
