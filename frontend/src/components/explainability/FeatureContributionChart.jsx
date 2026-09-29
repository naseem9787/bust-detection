/**
 * FeatureContributionChart Component
 * Visualizes machine learning feature contributions (SHAP values)
 * via a scientific horizontal diverging bar chart.
 *
 * Requirements:
 * - Shows positive contribution (increases bust risk / lowers confidence)
 *   and negative contribution (mitigates bust risk / supports confidence)
 * - Clear zero baseline reference
 * - Tooltips explaining technical terms
 * - Distinguishes Model Output vs Historical Context
 * - Restrained, decision-support styling without glowing AI effects
 */

import React, { useMemo } from 'react';
import { Tooltip } from '../ui/Tooltip.jsx';
import { InfoIcon, DatabaseIcon, LayersIcon } from '../icons/Icons.jsx';

function FeatureContributionChartComponent({
  factors = [],
  title = "Feature Contribution (SHAP Value Decomposition)",
  subtitle = "Quantifying each factor's additive contribution to the bust risk prediction relative to the baseline expectation.",
  className = '',
}) {
  // Sort factors by absolute magnitude of contribution and derive max scale once
  const { sortedFactors, maxVal } = useMemo(() => {
    const sorted = [...factors].sort((a, b) => {
      const valA = Math.abs(a.shapValue ?? a.contribution ?? 0);
      const valB = Math.abs(b.shapValue ?? b.contribution ?? 0);
      return valB - valA;
    });

    const max = Math.max(
      0.35,
      ...sorted.map((f) => Math.abs(f.shapValue ?? f.contribution ?? 0))
    );

    return { sortedFactors: sorted, maxVal: max };
  }, [factors]);

  return (
    <div className={`feature-contribution-chart-card ${className}`}>
      <div style={{ marginBottom: '14px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '8px' }}>
        <div>
          <div style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span>{title}</span>
            <Tooltip content="SHAP (Shapley Additive exPlanations): Game-theoretic method measuring how much each meteorological variable shifts the predicted bust probability away from the climatological baseline.">
              <span style={{ cursor: 'pointer', display: 'inline-flex', alignItems: 'center' }}>
                <InfoIcon size={13} style={{ color: 'var(--text-muted)' }} />
              </span>
            </Tooltip>
          </div>
          {subtitle && (
            <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '2px' }}>
              {subtitle}
            </div>
          )}
        </div>

        {/* Legend */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '11px', color: 'var(--text-muted)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#10B981' }} />
            <span>Stabilizing (Lowers Risk)</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '10px', height: '10px', borderRadius: '2px', backgroundColor: '#EF4444' }} />
            <span>Uncertainty Driver (Increases Risk)</span>
          </div>
        </div>
      </div>

      {/* Diverging Bar Chart Canvas */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
          padding: '12px 14px',
          backgroundColor: 'var(--bg-canvas)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        {/* Scale Axis Header */}
        <div className="feature-shap-header">
          <span className="feature-shap-label">Feature Variable</span>
          <span className="feature-shap-neg-label">-{(maxVal).toFixed(2)} (Mitigating)</span>
          <span className="feature-shap-pos-label">+{(maxVal).toFixed(2)} (Risk-Inflating)</span>
          <span className="feature-shap-weight">Weight</span>
        </div>

        {/* Rows */}
        {sortedFactors.map((factor) => {
          const val = factor.shapValue ?? factor.contribution ?? 0;
          const isNegative = val < 0;
          const absVal = Math.abs(val);
          const barWidthPct = Math.min(100, (absVal / maxVal) * 100);
          const barColor = isNegative ? '#10B981' : '#EF4444';
          const isHistorical = factor.source === 'historical_context';
          const SourceIcon = isHistorical ? DatabaseIcon : LayersIcon;

          return (
            <div key={factor.factorId} className="feature-shap-row">
              {/* Feature Label + Tooltip */}
              <div className="feature-shap-label">
                <span title={isHistorical ? 'Historical Context' : 'Model Output'} style={{ display: 'inline-flex', color: isHistorical ? 'var(--text-muted)' : '#38BDF8' }}>
                  <SourceIcon size={12} />
                </span>
                <span className="feature-shap-name">
                  {factor.name}
                </span>
                {factor.tooltip && (
                  <Tooltip content={`${factor.technicalTerm || factor.name}: ${factor.tooltip}`}>
                    <span style={{ cursor: 'pointer', display: 'inline-flex' }}>
                      <InfoIcon size={11} style={{ color: 'var(--text-muted)' }} />
                    </span>
                  </Tooltip>
                )}
              </div>

              {/* Left Bar (Negative / Stabilizing Contribution) */}
              <div className="feature-shap-neg-bar">
                {isNegative && (
                  <div
                    style={{
                      width: `${barWidthPct}%`,
                      height: '12px',
                      backgroundColor: barColor,
                      borderRadius: '2px 0 0 2px',
                      transition: 'width 200ms ease',
                    }}
                    title={`Mitigates bust risk: ${val.toFixed(2)}`}
                  />
                )}
              </div>

              {/* Right Bar (Positive / Risk-Inflating Contribution) */}
              <div className="feature-shap-pos-bar">
                {!isNegative && (
                  <div
                    style={{
                      width: `${barWidthPct}%`,
                      height: '12px',
                      backgroundColor: barColor,
                      borderRadius: '0 2px 2px 0',
                      transition: 'width 200ms ease',
                    }}
                    title={`Increases bust risk: +${val.toFixed(2)}`}
                  />
                )}
              </div>

              {/* Numeric Value Label */}
              <div
                className="tabular-nums feature-shap-weight"
                style={{
                  color: isNegative ? '#10B981' : '#F87171',
                }}
              >
                {val > 0 ? `+${val.toFixed(2)}` : val.toFixed(2)}
              </div>
            </div>
          );
        })}
      </div>

      {/* Axis Footer Note */}
      <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10.5px', color: 'var(--text-muted)', marginTop: '8px' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <DatabaseIcon size={12} />
          <span>Historical context factor</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <LayersIcon size={12} style={{ color: '#38BDF8' }} />
          <span>Current model output factor</span>
        </span>
      </div>
    </div>
  );
}
export const FeatureContributionChart = React.memo(FeatureContributionChartComponent);
