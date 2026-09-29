/**
 * Model Insights & Explainability Page
 * SIH 26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts
 *
 * PURPOSE:
 * Operational explainability and decision-support workspace answering:
 * "Why is the system giving this forecast low confidence?"
 *
 * Integrates:
 * - Interactive ExplanationPanel (ConfidenceIndicator, ReasonList, FeatureContributionChart)
 * - Three-Pillar Bust Definition Methodology (Percentile, IMD Rain Category, Temp Hard Threshold)
 * - IMD Daily Rainfall Reference Standards Table
 * - Technical explainability and past-analogue search roadmap
 */

import React, { useState, useEffect, useMemo } from 'react';
import { Card } from '../components/ui/Card.jsx';
import { Select } from '../components/ui/Select.jsx';
import { ExplanationPanel } from '../components/explainability/ExplanationPanel.jsx';
import { LoadingState } from '../components/feedback/LoadingState.jsx';
import { ErrorState } from '../components/feedback/ErrorState.jsx';
import {
  DatabaseIcon,
  ShieldCheckIcon,
  InfoIcon,
  LayersIcon,
  RefreshCwIcon,
} from '../components/icons/Icons.jsx';
import {
  BUST_RULES,
  IMD_RAINFALL_CATEGORIES,
  REGIONS,
  LEAD_DAYS,
} from '../design-system/weather-tokens.js';
import {
  getExplanation,
  getForecast,
  getRegions,
  getForecastCycles,
} from '../services/api.js';

const LEAD_OPTIONS = LEAD_DAYS.map((d) => ({
  id: String(d.day),
  label: `Lead Day ${d.day} (+${d.hours}h)`,
}));

const DEFAULT_CYCLES = [
  { code: '2026-09-29 00Z', label: '2026-09-29 00Z (Latest Operational)' },
  { code: '2026-09-28 12Z', label: '2026-09-28 12Z (-12h Run)' },
  { code: '2026-09-28 00Z', label: '2026-09-28 00Z (-24h Run)' },
  { code: '2018-08-14 00Z', label: '2018-08-14 00Z (Kerala Case Study)' },
];

export function ModelInsightsPage() {
  const [selectedRegionId, setSelectedRegionId] = useState('west-coast');
  const [selectedLeadDay, setSelectedLeadDay] = useState(5);
  const [selectedCycle, setSelectedCycle] = useState('2026-09-29 00Z');

  const [availableRegions, setAvailableRegions] = useState(REGIONS);
  const [availableCycles, setAvailableCycles] = useState([]);
  const [explanationData, setExplanationData] = useState(null);
  const [forecastData, setForecastData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load initial options
  useEffect(() => {
    let isMounted = true;
    Promise.all([getRegions(), getForecastCycles()])
      .then(([regs, cycles]) => {
        if (isMounted) {
          if (regs?.length) setAvailableRegions(regs);
          if (cycles?.length) setAvailableCycles(cycles);
        }
      })
      .catch((err) => console.warn('Could not load metadata:', err));

    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch explanation and forecast data when selectors change
  useEffect(() => {
    let isMounted = true;
    Promise.all([
      getExplanation({
        cycle: selectedCycle,
        leadDay: selectedLeadDay,
        regionId: selectedRegionId,
      }),
      getForecast({
        cycle: selectedCycle,
        leadDay: selectedLeadDay,
        regionId: selectedRegionId,
      }),
    ])
      .then(([exp, fcst]) => {
        if (isMounted) {
          setExplanationData(exp);
          setForecastData(fcst);
          setLoading(false);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('Failed to load explainability data:', err);
          setError('Failed to load model attribution and explanation factors.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedRegionId, selectedLeadDay, selectedCycle]);

  const handleRefresh = () => {
    setLoading(true);
    Promise.all([
      getExplanation({
        cycle: selectedCycle,
        leadDay: selectedLeadDay,
        regionId: selectedRegionId,
        forceReload: true,
      }),
      getForecast({
        cycle: selectedCycle,
        leadDay: selectedLeadDay,
        regionId: selectedRegionId,
        forceReload: true,
      }),
    ])
      .then(([exp, fcst]) => {
        setExplanationData(exp);
        setForecastData(fcst);
        setLoading(false);
        setError(null);
      })
      .catch((err) => {
        console.error('Failed to refresh explainability data:', err);
        setError('Failed to load model attribution and explanation factors.');
        setLoading(false);
      });
  };

  const activeRegionObj = availableRegions.find(
    (r) => r.id === selectedRegionId || r.shortName === selectedRegionId
  ) || availableRegions[5];

  const regionOptions = useMemo(
    () =>
      availableRegions.map((r) => ({
        id: r.id || r.shortName,
        label: r.name || r.shortName,
      })),
    [availableRegions]
  );

  const cycleOptions = useMemo(
    () =>
      (availableCycles.length > 0 ? availableCycles : DEFAULT_CYCLES).map((c) => ({
        id: c.code || c.id,
        label: c.label || c.code,
      })),
    [availableCycles]
  );

  const leadOptions = LEAD_OPTIONS;

  const confidenceScore = forecastData?.verification?.confidence ?? 0.27;
  const factors = explanationData?.factors || [];

  return (
    <div className="page-container">
      <div style={{ display: 'flex', flexDirection: 'column', gap: '22px' }}>
        {/* Top Header & Interactive Scope Toolbar */}
        <div className="analysis-header-panel">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
            <div>
              <div className="analysis-header-eyebrow">
                <ShieldCheckIcon size={14} style={{ color: '#38BDF8' }} />
                <span>Explainable AI &bull; Scientific Decision Support Architecture</span>
              </div>
              <h1 style={{ fontSize: '20px', fontWeight: 700, letterSpacing: '-0.01em', color: 'var(--text-primary)', margin: 0, lineHeight: 1.25 }}>
                Model Insights &amp; Explainability Diagnostic
              </h1>
              <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px', maxWidth: '880px', lineHeight: 1.5 }}>
                Decomposing machine learning predictions into human-interpretable meteorological factors. Answers why the system assigns low confidence to specific regional forecasts.
              </div>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={handleRefresh}
                title="Refresh attribution analysis"
                style={{ height: '34px', padding: '0 10px' }}
              >
                <RefreshCwIcon size={14} className={loading ? 'spin' : ''} />
              </button>
            </div>
          </div>

          {/* Interactive Inspection Controls */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              paddingTop: '12px',
              borderTop: '1px solid var(--border-subtle)',
              flexWrap: 'wrap',
              gap: '12px',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '11px', color: 'var(--text-muted)', fontWeight: 600, textTransform: 'uppercase' }}>
              <LayersIcon size={13} style={{ color: '#38BDF8' }} />
              <span>Diagnostic Target:</span>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
              <Select
                id="exp-region-select"
                value={selectedRegionId}
                onChange={setSelectedRegionId}
                options={regionOptions}
                style={{ minWidth: '220px' }}
              />

              <Select
                id="exp-lead-select"
                value={String(selectedLeadDay)}
                onChange={(val) => setSelectedLeadDay(Number(val))}
                options={leadOptions}
                style={{ minWidth: '180px' }}
              />

              <Select
                id="exp-cycle-select"
                value={selectedCycle}
                onChange={setSelectedCycle}
                options={cycleOptions}
                style={{ minWidth: '190px' }}
              />
            </div>
          </div>
        </div>

        {/* ==========================================================================
            SECTION 1: THE CORE EXPLANATION PANEL
            Answers: "Why is the system giving this forecast low confidence?"
            ========================================================================== */}
        {loading && !explanationData ? (
          <LoadingState message="Computing SHAP feature contributions and climatological error covariance..." />
        ) : error && !explanationData ? (
          <ErrorState title="Explainability Unavailable" message={error} onRetry={handleRefresh} />
        ) : (
          <ExplanationPanel
            confidence={confidenceScore}
            factors={factors}
            regionName={activeRegionObj.name || activeRegionObj.shortName}
            leadDay={selectedLeadDay}
            cycle={selectedCycle}
            bulletinSummary={explanationData?.bulletinSummary}
          />
        )}

        {/* ==========================================================================
            SECTION 2: BUST DEFINITION METHODOLOGY (Phase 0 Rules Engine)
            ========================================================================== */}
        <div className="section-block" style={{ marginTop: '10px' }}>
          <div className="section-header-row" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <span className="section-heading" style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <ShieldCheckIcon size={16} style={{ color: '#38BDF8' }} />
              <span>Three-Pillar Bust Definition Methodology (src/label_busts.py)</span>
            </span>
            <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              Deterministic Evaluation Protocol
            </span>
          </div>

          <div className="grid-3col">
            {/* Rule 1: Percentile Rule */}
            <Card title="1. Percentile Distribution Rule" subtitle="Lead-Time & Region Aware">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                <p>
                  An error is flagged as a bust if |error| exceeds the <strong>90th percentile</strong> ({BUST_RULES.percentile * 100}th quantile) of historical error for that specific <code className="tabular-nums">(region, lead_day)</code> bucket.
                </p>
                <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-surface-raised)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '11px' }}>
                  <strong>Operational Rationale:</strong> A Day-10 error that is standard for Day-10 does not get flagged just because it looks large in absolute terms.
                </div>
              </div>
            </Card>

            {/* Rule 2: IMD Categorical Rain Rule */}
            <Card title="2. IMD Rainfall Category Shift" subtitle="Operationally Sensitive">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                <p>
                  Flags a bust when forecast and observed rainfall categories are <strong>&ge; 2 steps apart</strong>, or if a <strong>heavy-or-above event (&ge;64.5mm)</strong> is missed or falsely predicted.
                </p>
                <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-surface-raised)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '11px' }}>
                  <strong>Operational Focus:</strong> Missed heavy-rain events carry severe life-safety implications for flood response, regardless of lead time.
                </div>
              </div>
            </Card>

            {/* Rule 3: Temperature Hard Threshold */}
            <Card title="3. Temperature Hard Threshold" subtitle="Heatwave Alert Relevant">
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
                <p>
                  Absolute temperature error <strong>&gt; 3.0°C</strong> ({BUST_RULES.tempHardThresholdK}°K) is unconditionally flagged as a bust across all lead times.
                </p>
                <div style={{ padding: '8px 10px', backgroundColor: 'var(--bg-surface-raised)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)', fontSize: '11px' }}>
                  <strong>Heatwave Safety:</strong> Catches extreme heatwave forecast misses in Northwest India even when local variance is naturally elevated.
                </div>
              </div>
            </Card>
          </div>
        </div>

        {/* ==========================================================================
            SECTION 3: IMD RAINFALL CLASSIFICATION STANDARDS TABLE
            ========================================================================== */}
        <Card
          title="IMD Daily Rainfall Classification Standards"
          subtitle="Reference threshold standards utilized for categorical difference computation (src/config.py)"
          icon={DatabaseIcon}
          noPadding
        >
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Category ID</th>
                  <th>Classification</th>
                  <th>24h Rainfall Range</th>
                  <th>Severity Tier</th>
                  <th>Operational Consequence</th>
                </tr>
              </thead>
              <tbody>
                {IMD_RAINFALL_CATEGORIES.map((cat, idx) => (
                  <tr key={cat.id}>
                    <td><code>{cat.id}</code></td>
                    <td style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{cat.label}</td>
                    <td className="tabular-nums" style={{ color: cat.color, fontWeight: 600 }}>{cat.range}</td>
                    <td>
                      <span className="badge" style={{ backgroundColor: `${cat.color}22`, color: cat.color, borderColor: `${cat.color}44` }}>
                        Index {idx}
                      </span>
                    </td>
                    <td style={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
                      {idx >= 3 ? 'Triggers Heavy Rain Alert Protocol' : 'Routine Baseline Monitoring'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        {/* ==========================================================================
            SECTION 4: TECHNICAL EXPLAINABILITY ROADMAP
            ========================================================================== */}
        <div className="section-block">
          <div className="section-header-row" style={{ marginBottom: '12px' }}>
            <span className="section-heading" style={{ fontSize: '14.5px', fontWeight: 700, color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <InfoIcon size={16} style={{ color: '#38BDF8' }} />
              <span>Phase 1+ AI / Explainability Architecture Roadmap</span>
            </span>
          </div>

          <div className="grid-2col">
            <Card title="Past-Analog Search (FAISS)" subtitle="ROADMAP Phase 1">
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                Vector similarity search across compressed spatial representations of past forecast maps. Answers the key operational question:
                <em> &ldquo;Which past forecasts looked like this one, and how did they fail?&rdquo;</em> Uses L2 distance across compressed ERA5 reanalysis fields to identify historical analogues.
              </p>
            </Card>

            <Card title="Explainable Feature Attribution (SHAP)" subtitle="ROADMAP Phase 1">
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
                Translates machine learning feature importance into human-readable forecaster bulletin text, highlighting whether low confidence stems from MJO phase, run-to-run 500hPa jumpiness, or orographic convective triggers.
              </p>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
