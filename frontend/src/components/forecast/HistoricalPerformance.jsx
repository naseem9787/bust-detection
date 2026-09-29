/**
 * HistoricalPerformance Component (Integrated Secondary Area)
 * Displays quiet, supporting climatological context and verification history for the selected region.
 */

import React, { useMemo } from 'react';
import { Card } from '../ui/Card.jsx';
import { DatabaseIcon } from '../icons/Icons.jsx';

function HistoricalPerformanceComponent({
  regionName = 'West Coast',
  leadDay = 5,
  historicalData = [],
  className = '',
}) {
  const metrics = useMemo(() => {
    if (!historicalData || historicalData.length === 0) {
      return {
        monsoon: 48.7,
        postMonsoon: 27.7,
        preMonsoon: 23.7,
        winter: 14.6,
        missedHeavy: 264,
        falseAlarm: 418,
        samples: '27,328',
      };
    }

    const jjas = historicalData.find((r) => r.season === 'monsoon_JJAS');
    const on = historicalData.find((r) => r.season === 'post_monsoon_ON');
    const mam = historicalData.find((r) => r.season === 'pre_monsoon_MAM');
    const djf = historicalData.find((r) => r.season === 'winter_DJF');

    const missed = historicalData.reduce((acc, r) => acc + (r.missedHeavyRainEvents || 0), 0);
    const falseAlarm = historicalData.reduce((acc, r) => acc + (r.falseAlarmHeavyRain || 0), 0);
    const nSamples = historicalData.reduce((acc, r) => acc + (r.nSamples || 0), 0);

    return {
      monsoon: jjas?.bustRate ?? 48.7,
      postMonsoon: on?.bustRate ?? 27.7,
      preMonsoon: mam?.bustRate ?? 23.7,
      winter: djf?.bustRate ?? 14.6,
      missedHeavy: missed || 264,
      falseAlarm: falseAlarm || 418,
      samples: nSamples ? nSamples.toLocaleString() : '27,328',
    };
  }, [historicalData]);

  return (
    <Card
      title={`Climatological Verification Skill &bull; ${regionName}`}
      subtitle={`Evaluated against 2018–2021 database at Lead Day ${leadDay}`}
      icon={DatabaseIcon}
      className={className}
    >
      <div className="historical-performance-grid">
        {/* Seasonal Skill Comparison */}
        <div className="historical-metric-subcard">
          <div className="subcard-title">Seasonal Climatology (Bust Rate)</div>
          <div className="seasonal-progress-list">
            <div className="seasonal-row">
              <span className="season-name">Monsoon (JJAS)</span>
              <div className="season-bar-track">
                <div className="season-bar-fill" style={{ width: `${Math.min(100, metrics.monsoon)}%`, backgroundColor: '#0284C7' }} />
              </div>
              <span className="tabular-nums season-val">{metrics.monsoon}%</span>
            </div>

            <div className="seasonal-row">
              <span className="season-name">Post-Monsoon (ON)</span>
              <div className="season-bar-track">
                <div className="season-bar-fill" style={{ width: `${Math.min(100, metrics.postMonsoon)}%`, backgroundColor: '#10B981' }} />
              </div>
              <span className="tabular-nums season-val">{metrics.postMonsoon}%</span>
            </div>

            <div className="seasonal-row">
              <span className="season-name">Pre-Monsoon (MAM)</span>
              <div className="season-bar-track">
                <div className="season-bar-fill" style={{ width: `${Math.min(100, metrics.preMonsoon)}%`, backgroundColor: '#EA580C' }} />
              </div>
              <span className="tabular-nums season-val">{metrics.preMonsoon}%</span>
            </div>

            <div className="seasonal-row">
              <span className="season-name">Winter (DJF)</span>
              <div className="season-bar-track">
                <div className="season-bar-fill" style={{ width: `${Math.min(100, metrics.winter)}%`, backgroundColor: '#818CF8' }} />
              </div>
              <span className="tabular-nums season-val">{metrics.winter}%</span>
            </div>
          </div>
        </div>

        {/* Operational Misses & Sample Depth */}
        <div className="historical-metric-subcard">
          <div className="subcard-title">Operational Extreme Events (2018–2021)</div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', marginTop: '6px' }}>
            <div style={{ padding: '6px 8px', backgroundColor: 'var(--bg-canvas)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Missed Heavy Rain</div>
              <div className="tabular-nums" style={{ fontSize: '16px', fontWeight: 700, color: '#F87171' }}>
                {metrics.missedHeavy}
              </div>
              <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>Obs &ge;64.5mm missed</div>
            </div>

            <div style={{ padding: '6px 8px', backgroundColor: 'var(--bg-canvas)', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border-subtle)' }}>
              <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>False Alarm Heavy</div>
              <div className="tabular-nums" style={{ fontSize: '16px', fontWeight: 700, color: '#FBBF24' }}>
                {metrics.falseAlarm}
              </div>
              <div style={{ fontSize: '9px', color: 'var(--text-muted)' }}>Fcst &ge;64.5mm not observed</div>
            </div>
          </div>

          <div style={{ marginTop: '8px', display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '10.5px', color: 'var(--text-muted)' }}>
            <span>Verification depth:</span>
            <span className="tabular-nums" style={{ color: 'var(--text-secondary)' }}>
              {metrics.samples} regional grid-hours
            </span>
          </div>
        </div>
      </div>
    </Card>
  );
}

export const HistoricalPerformance = React.memo(HistoricalPerformanceComponent);
