/**
 * Meteorological Risk Level Badge
 * Displays bust risk tiers: Low, Moderate, Elevated, High, Extreme
 */

import React from 'react';
import { TOKENS } from '../../design-system/tokens.js';
import { getBustRiskLevel } from '../../utils/weatherRules.js';

export function RiskBadge({
  level,
  probability = null,
  showLabel = true,
  className = '',
}) {
  const resolvedLevel = level || (probability !== null ? getBustRiskLevel(probability) : 'low');
  const riskInfo = TOKENS.colors.risk[resolvedLevel] || TOKENS.colors.risk.low;

  return (
    <span
      className={`badge badge-risk-${resolvedLevel} ${className}`}
      title={`Bust Risk: ${riskInfo.label}${probability !== null ? ` (${(probability * 100).toFixed(0)}%)` : ''}`}
    >
      <span className="badge-dot" />
      {showLabel && riskInfo.label}
      {probability !== null && (
        <span className="tabular-nums" style={{ opacity: 0.9, marginLeft: '2px' }}>
          {(probability > 1 ? probability : probability * 100).toFixed(0)}%
        </span>
      )}
    </span>
  );
}
