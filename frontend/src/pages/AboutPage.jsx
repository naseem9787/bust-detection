/**
 * About Page
 * Project overview, SIH Problem Statement 26079 context, and institutional architecture
 */

import React from 'react';
import { Card } from '../components/ui/Card.jsx';
import { RadarIcon, DatabaseIcon, ShieldCheckIcon, HelpCircleIcon } from '../components/icons/Icons.jsx';

export function AboutPage() {
  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      {/* Title & Institutional Header Panel */}
      <div className="analysis-header-panel">
        <div className="analysis-header-eyebrow">
          <HelpCircleIcon size={14} style={{ color: '#38BDF8' }} />
          <span>Research prototype &bull; SIH 2026 Problem Statement 26079</span>
        </div>

        <div className="analysis-header-top">
          <div className="analysis-title-group">
            <h1>About the Meteorological Bust Detection Platform</h1>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '6px', maxWidth: '920px', lineHeight: 1.55 }}>
              This research prototype, built by team TWP for SIH 2026 problem statement 26079 (<strong>Ministry of Earth Sciences</strong>), estimates where a medium-range NWP forecast is likely to bust, and explains why, across <strong>Day 1 through Day 10</strong> lead times. It is validated on archived ECMWF HRES forecasts with ERA5 reanalysis as verified truth; it does not ingest live forecasts.
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>Team TWP</span>
            <span className="badge badge-subtle">SIH 26079</span>
          </div>
        </div>
      </div>

      {/* Grid of Institutional Details */}
      <div className="grid-3col">
        <Card title="Institutional Stakeholders" icon={RadarIcon}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Problem Statement From:</strong>
              <div>Ministry of Earth Sciences (MoES), Government of India</div>
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Intended Users:</strong>
              <div>NWP forecasters &amp; verification teams (not yet deployed with any agency)</div>
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Rain-Bust Rule Uses:</strong>
              <div>India Meteorological Department (IMD) rainfall intensity categories</div>
            </div>
          </div>
        </Card>

        <Card title="Data Infrastructure" icon={DatabaseIcon}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Forecast Store:</strong>
              <div>ECMWF HRES (2016–2022) via WeatherBench2 GCS Bucket</div>
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Ground Truth Store:</strong>
              <div>ERA5 Reanalysis (1959–2023) at matching 1.5° grid</div>
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Future Inputs:</strong>
              <div>Designed to accept other NWP sources (e.g. NCUM/NEPS) and IMD 0.25° rainfall; not yet tested</div>
            </div>
          </div>
        </Card>

        <Card title="Technical Compliance" icon={ShieldCheckIcon}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '12px', color: 'var(--text-secondary)' }}>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Frontend Architecture:</strong>
              <div>React.js (JavaScript pure, 0 TypeScript, zero external bloat)</div>
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Backend Integration:</strong>
              <div>FastAPI Python ML services &amp; Parquet error databases</div>
            </div>
            <div>
              <strong style={{ color: 'var(--text-primary)' }}>Design Standard:</strong>
              <div>Government/Scientific dark slate, tabular numbers, restrained UI</div>
            </div>
          </div>
        </Card>
      </div>

      {/* Kaggle Dataset Technical Note */}
      <Card title="Note on Verification Data Integrity" subtitle="Avoiding common Kaggle mislabeling traps">
        <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.55 }}>
          <p>
            Unlike preliminary Kaggle repositories that mistakenly treat India-WRIS <code>daily-rainfall-at-state-level.csv</code> <code>rfs</code> column (&ldquo;Rainfall Storage&rdquo;, a reservoir volume metric) as rainfall forecast, this project uses genuine, pointwise deterministic NWP model runs (ECMWF HRES) aligned with ERA5 reanalysis ground truth on an identical 240 &times; 121 equiangular grid over the Indian subcontinent.
          </p>
        </div>
      </Card>
    </div>
  );
}
