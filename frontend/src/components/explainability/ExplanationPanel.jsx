/**
 * ExplanationPanel Component
 * Comprehensive reusable decision-support workspace answering:
 * "Why is the system giving this forecast low confidence?"
 *
 * Integrates:
 * 1. ConfidenceIndicator (Calibrated score)
 * 2. ReasonList (Rank-ordered plain-language reasons for non-ML judges)
 * 3. FeatureContributionChart (Diverging SHAP feature contribution bar chart)
 * 4. Model Output vs Historical Context separation
 * 5. Operational Forecaster Bulletin summary (scientific non-causal language)
 */

import React, { useState, useMemo } from 'react';
import { ConfidenceIndicator } from './ConfidenceIndicator.jsx';
import { ReasonList } from './ReasonList.jsx';
import { FeatureContributionChart } from './FeatureContributionChart.jsx';
import { Badge } from '../ui/Badge.jsx';
import {
  ShieldCheckIcon,
  DatabaseIcon,
  LayersIcon,
  InfoIcon,
  ClockIcon,
} from '../icons/Icons.jsx';

function ExplanationPanelComponent({
  confidence = 0.27,
  factors = [],
  regionName = 'West Coast',
  leadDay = 5,
  cycle = '2026-09-29 00Z',
  bulletinSummary = null,
  className = '',
}) {
  const [activeTab, setActiveTab] = useState('all'); // 'all' | 'model' | 'historical'

  const { modelOutputFactors, historicalFactors } = useMemo(() => {
    return {
      modelOutputFactors: factors.filter((f) => f.source === 'model_output'),
      historicalFactors: factors.filter((f) => f.source === 'historical_context'),
    };
  }, [factors]);

  const displayedFactors = useMemo(() => {
    if (activeTab === 'model') return modelOutputFactors;
    if (activeTab === 'historical') return historicalFactors;
    return factors;
  }, [activeTab, modelOutputFactors, historicalFactors, factors]);

  return (
    <div className={`explanation-panel-container ${className}`} style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* 1. Header & Verification Context Strip */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '12px 18px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <ShieldCheckIcon size={16} style={{ color: '#38BDF8' }} />
          <div>
            <div style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--text-primary)' }}>
              Forecast Confidence &amp; Explainability Diagnostic &bull; {regionName}
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Operational Cycle: {cycle} &bull; Lead Time: Day {leadDay} (+{leadDay * 24}h)
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Badge variant="neutral">
            <ClockIcon size={12} style={{ marginRight: '4px' }} />
            T+{leadDay * 24}h Horizon
          </Badge>
          <Badge variant="subtle">
            Methodology: SHAP + Climatological Covariance
          </Badge>
        </div>
      </div>

      {/* 2. Upper Grid: Confidence Indicator + Primary Diagnostic Callout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '320px 1fr',
          gap: '16px',
        }}
        className="explanation-top-grid"
      >
        {/* Calibrated Confidence Indicator */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            padding: '18px',
            display: 'flex',
            flexDirection: 'column',
            justifyContent: 'center',
          }}
        >
          <ConfidenceIndicator confidence={confidence} leadDay={leadDay} />
        </div>

        {/* Executive Decision Support Synthesis */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            padding: '18px',
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            justifyContent: 'center',
          }}
        >
          <div style={{ fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.04em', color: '#38BDF8', fontWeight: 700, display: 'flex', alignItems: 'center', gap: '6px' }}>
            <InfoIcon size={13} />
            <span>Operational Decision Support Briefing</span>
          </div>

          <div style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: 1.5 }}>
            {bulletinSummary || (
              <span>
                Forecast skill over <strong>{regionName}</strong> at Day {leadDay} is significantly constrained by <em>precipitation categorical boundary shifts</em> and <em>historical lead-time error growth</em>. Forecasters are advised not to rely solely on deterministic precipitation amounts exceeding 64.5mm without cross-checking ensemble quantile spread.
              </span>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '14px', fontSize: '11px', color: 'var(--text-muted)', paddingTop: '6px', borderTop: '1px solid var(--border-subtle)', flexWrap: 'wrap' }}>
            <span>Identified Contributing Factors: <strong style={{ color: 'var(--text-primary)' }}>{factors.length}</strong></span>
            <span>&bull;</span>
            <span>Risk-Inflating Factors: <strong style={{ color: '#F87171' }}>{factors.filter(f => (f.shapValue ?? f.contribution) > 0).length}</strong></span>
            <span>&bull;</span>
            <span>Stabilizing Constraints: <strong style={{ color: '#10B981' }}>{factors.filter(f => (f.shapValue ?? f.contribution) < 0).length}</strong></span>
          </div>
        </div>
      </div>

      {/* 3. ReasonList: "Why is confidence low?" (Plain Language for Judges) */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          padding: '18px 20px',
        }}
      >
        <ReasonList
          factors={factors}
          title="Why is confidence low for this forecast?"
          subtitle="Key empirical and dynamical conditions contributing to elevated forecast uncertainty for this regional window:"
        />
      </div>

      {/* 4. Visual Feature Contribution (SHAP) Chart */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          padding: '18px 20px',
        }}
      >
        {/* Source Filter Tabs */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px', flexWrap: 'wrap', gap: '8px' }}>
          <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-secondary)' }}>
            Filter Contributing Factors by Provenance:
          </span>

          <div style={{ display: 'flex', gap: '4px' }}>
            <button
              type="button"
              className={`btn btn-xs ${activeTab === 'all' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('all')}
            >
              All Factors ({factors.length})
            </button>
            <button
              type="button"
              className={`btn btn-xs ${activeTab === 'model' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('model')}
            >
              <LayersIcon size={11} style={{ marginRight: '4px' }} />
              Model Output ({modelOutputFactors.length})
            </button>
            <button
              type="button"
              className={`btn btn-xs ${activeTab === 'historical' ? 'btn-primary' : 'btn-secondary'}`}
              onClick={() => setActiveTab('historical')}
            >
              <DatabaseIcon size={11} style={{ marginRight: '4px' }} />
              Historical Context ({historicalFactors.length})
            </button>
          </div>
        </div>

        <FeatureContributionChart
          factors={displayedFactors}
          title="Additive Feature Contribution to Bust Risk (SHAP)"
          subtitle="Showing relative magnitude and direction of each meteorological condition against the baseline expectation."
        />
      </div>

      {/* 5. Provenance Separation: Model Output vs Historical Context */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '16px',
        }}
        className="explanation-provenance-grid"
      >
        {/* Model Output Panel */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            padding: '16px 18px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <LayersIcon size={15} style={{ color: '#38BDF8' }} />
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
              NWP Model Output Signals (Active Run)
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11.5px' }}>
            {modelOutputFactors.map((f) => (
              <div
                key={f.factorId}
                style={{
                  padding: '8px 10px',
                  backgroundColor: 'var(--bg-surface-raised)',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' }}>
                  <span>{f.name}</span>
                  <span className="tabular-nums" style={{ color: (f.shapValue ?? 0) > 0 ? '#F87171' : '#10B981' }}>
                    {(f.shapValue ?? 0) > 0 ? `+${f.shapValue.toFixed(2)}` : f.shapValue?.toFixed(2)}
                  </span>
                </div>
                <div style={{ color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                  {f.description}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Historical Context Panel */}
        <div
          style={{
            backgroundColor: 'var(--bg-surface)',
            border: '1px solid var(--border-default)',
            borderRadius: 'var(--radius-md)',
            padding: '16px 18px',
            display: 'flex',
            flexDirection: 'column',
            gap: '10px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
            <DatabaseIcon size={15} style={{ color: '#F59E0B' }} />
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
              Historical Climatological Context (2018–2021)
            </span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '11.5px' }}>
            {historicalFactors.map((f) => (
              <div
                key={f.factorId}
                style={{
                  padding: '8px 10px',
                  backgroundColor: 'var(--bg-surface-raised)',
                  borderRadius: 'var(--radius-xs)',
                  border: '1px solid var(--border-subtle)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 600, color: 'var(--text-primary)', marginBottom: '2px' }}>
                  <span>{f.name}</span>
                  <span className="tabular-nums" style={{ color: (f.shapValue ?? 0) > 0 ? '#F87171' : '#10B981' }}>
                    {(f.shapValue ?? 0) > 0 ? `+${f.shapValue.toFixed(2)}` : f.shapValue?.toFixed(2)}
                  </span>
                </div>
                <div style={{ color: 'var(--text-secondary)', lineHeight: 1.35 }}>
                  {f.description}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
export const ExplanationPanel = React.memo(ExplanationPanelComponent);
