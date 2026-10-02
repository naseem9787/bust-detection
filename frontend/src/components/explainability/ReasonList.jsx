/**
 * ReasonList Component
 * Formatted plain-language ranked list answering:
 * "Why is the system giving this forecast low confidence?"
 *
 * Requirements:
 * - Understandable to non-ML judges and operational forecasters
 * - Clearly distinguishes Model Output vs Historical Context
 * - Explains technical terms with tooltips
 * - Strictly avoids causal claims (uses "contributing factors")
 * - Clean scientific decision-support styling (zero glowing AI effects)
 */

import React, { useMemo } from 'react';
import { Tooltip } from '../ui/Tooltip.jsx';
import { AlertTriangleIcon, InfoIcon, DatabaseIcon, LayersIcon } from '../icons/Icons.jsx';

function ReasonListComponent({
  factors = [],
  title = "What is driving the risk?",
  subtitle = "Primary factors statistically associated with elevated forecast uncertainty for this initialization:",
  className = '',
}) {
  // Filter factors that increase risk / lower confidence (memoized)
  const riskFactors = useMemo(() => {
    return factors
      .filter((f) => f.direction === 'positive_risk' || (f.contribution && f.contribution > 0))
      .slice(0, 5);
  }, [factors]);

  return (
    <div className={`reason-list-block ${className}`}>
      <div style={{ marginBottom: '12px' }}>
        <div style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertTriangleIcon size={16} style={{ color: '#F87171' }} />
          <span>{title}</span>
        </div>
        {subtitle && (
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', marginTop: '2px' }}>
            {subtitle}
          </div>
        )}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
        {riskFactors.map((factor, idx) => {
          const isHistorical = factor.source === 'historical_context';
          const badgeVariant = isHistorical ? 'neutral' : 'subtle';
          const SourceIcon = isHistorical ? DatabaseIcon : LayersIcon;

          return (
            <div
              key={factor.factorId || idx}
              style={{
                backgroundColor: 'var(--bg-surface-raised)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
                padding: '12px 14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '6px',
                transition: 'border-color 120ms ease',
              }}
            >
              {/* Header row: Number, Factor Name, Source Badge, and Technical Tooltip */}
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span
                    style={{
                      width: '20px',
                      height: '20px',
                      borderRadius: '50%',
                      backgroundColor: 'rgba(239, 68, 68, 0.15)',
                      color: '#F87171',
                      fontSize: '11px',
                      fontWeight: 700,
                      display: 'inline-flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      fontFamily: 'var(--font-mono)',
                    }}
                  >
                    {idx + 1}
                  </span>
                  <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
                    {factor.name}
                  </span>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  {/* Distinct Source Badge: Model Output vs Historical Context */}
                  <span
                    className={`badge badge-${badgeVariant}`}
                    style={{
                      fontSize: '10px',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: '4px',
                      padding: '2px 8px',
                    }}
                  >
                    <SourceIcon size={11} />
                    <span>{factor.sourceLabel || (isHistorical ? 'Historical Context' : 'Model Output')}</span>
                  </span>

                  {factor.technicalTerm && factor.tooltip && (
                    <Tooltip content={`${factor.technicalTerm}: ${factor.tooltip}`}>
                      <span style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}>
                        <InfoIcon size={13} style={{ color: 'var(--text-muted)' }} />
                      </span>
                    </Tooltip>
                  )}
                </div>
              </div>

              {/* Plain-Language Explanation (Non-ML judge understandable) */}
              <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', lineHeight: 1.45, paddingLeft: '28px' }}>
                {factor.plainReason || factor.description}
              </div>

              {/* Quantitative Telemetry / Physical Evidence */}
              {factor.evidenceValue && (
                <div style={{ paddingLeft: '28px', display: 'flex', alignItems: 'center', gap: '10px', fontSize: '11px', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                  <span>Evidence:</span>
                  <span style={{ color: 'var(--text-primary)', backgroundColor: 'var(--bg-canvas)', padding: '1px 6px', borderRadius: 'var(--radius-xs)', border: '1px solid var(--border-subtle)' }}>
                    {factor.evidenceValue}
                  </span>
                  {factor.shapValue !== undefined && (
                    <span style={{ color: factor.shapValue > 0 ? '#F87171' : '#10B981' }}>
                      SHAP: {factor.shapValue > 0 ? `+${factor.shapValue.toFixed(2)}` : factor.shapValue.toFixed(2)}
                    </span>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '10px', fontStyle: 'italic', display: 'flex', alignItems: 'center', gap: '6px' }}>
        <InfoIcon size={12} />
        <span>Factors represent statistical associations and historical error correlation; they indicate contributing conditions rather than deterministic causation.</span>
      </div>
    </div>
  );
}
export const ReasonList = React.memo(ReasonListComponent);
