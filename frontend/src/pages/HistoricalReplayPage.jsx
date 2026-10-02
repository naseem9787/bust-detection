/**
 * Historical Replay Page
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 *
 * Shows one real, verified forecast bust from the project's archive: what the
 * ECMWF HRES forecast said at each lead time (Day 1-10) for a single valid
 * date and grid point, against what ERA5 recorded. Everything displayed comes
 * straight from GET /api/v1/replay/event - nothing is simulated or derived
 * here, and no model probability is shown because the endpoint does not
 * return one for this record.
 */

import React, { useState, useEffect } from 'react';
import { getReplayEvents, getReplayData } from '../services/api.js';
import { Card } from '../components/ui/Card.jsx';
import { LoadingState } from '../components/feedback/LoadingState.jsx';
import { ErrorState } from '../components/feedback/ErrorState.jsx';
import { EmptyState } from '../components/feedback/EmptyState.jsx';
import { ClockIcon, RefreshCwIcon } from '../components/icons/Icons.jsx';

// SVG geometry: viewBox 0 0 900 300; Day 1 at x=70, Day 10 at x=850
const W = 900;
const H = 300;
const PAD = { left: 70, right: 50, top: 24, bottom: 44 };
const xOf = (day) => PAD.left + ((day - 1) / 9) * (W - PAD.left - PAD.right);

function TrajectoryChart({ trajectory }) {
  const observed = trajectory[0]?.actualPrecipMm ?? 0;
  const maxVal = Math.max(10, ...trajectory.map((t) => t.forecastPrecipMm), observed);
  const top = Math.ceil(maxVal / 20) * 20;
  const yOf = (v) => H - PAD.bottom - (v / top) * (H - PAD.top - PAD.bottom);
  const ticks = [0, top / 4, top / 2, (3 * top) / 4, top];
  const path = trajectory
    .map((t, i) => `${i === 0 ? 'M' : 'L'} ${xOf(t.leadDay).toFixed(1)} ${yOf(t.forecastPrecipMm).toFixed(1)}`)
    .join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" style={{ width: '100%', height: 'auto' }}
      aria-label="ECMWF forecast rainfall by lead day compared with the ERA5 observed value">
      {ticks.map((t) => (
        <g key={t}>
          <line x1={PAD.left} x2={W - PAD.right} y1={yOf(t)} y2={yOf(t)} stroke="#1E293B" strokeWidth="1" />
          <text x={PAD.left - 10} y={yOf(t) + 4} textAnchor="end" fontSize="11" fill="#94A3B8">{Math.round(t)}</text>
        </g>
      ))}
      <text x={18} y={H / 2} fontSize="11" fill="#94A3B8" transform={`rotate(-90 18 ${H / 2})`} textAnchor="middle">
        24 h rainfall (mm)
      </text>
      {trajectory.map((t) => (
        <text key={t.leadDay} x={xOf(t.leadDay)} y={H - 18} textAnchor="middle" fontSize="11" fill="#94A3B8">
          Day {t.leadDay}
        </text>
      ))}
      <line x1={PAD.left} x2={W - PAD.right} y1={yOf(observed)} y2={yOf(observed)} stroke="#10B981" strokeWidth="2" strokeDasharray="6 4" />
      <text x={PAD.left + 6} y={yOf(observed) - 8} textAnchor="start" fontSize="11" fill="#10B981">
        ERA5 observed: {observed.toFixed(1)} mm
      </text>
      <path d={path} fill="none" stroke="#F97316" strokeWidth="2.5" />
      {trajectory.map((t) => (
        <g key={t.leadDay}>
          <circle cx={xOf(t.leadDay)} cy={yOf(t.forecastPrecipMm)} r="4.5" fill="#F97316" />
          {t.forecastPrecipMm >= 20 && (
            <text x={xOf(t.leadDay)} y={yOf(t.forecastPrecipMm) - 10} textAnchor="middle" fontSize="12" fontWeight="700" fill="#FDBA74">
              {t.forecastPrecipMm.toFixed(1)} mm
            </text>
          )}
        </g>
      ))}
    </svg>
  );
}

export function HistoricalReplayPage() {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState(null);
  const [replay, setReplay] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let isMounted = true;
    getReplayEvents()
      .then((list) => {
        if (!isMounted) return;
        setEvents(list || []);
        if (list?.length) setSelectedEventId(list[0].eventId);
        else setLoading(false);
      })
      .catch(() => {
        if (isMounted) {
          setError('Unable to load the replay event catalogue.');
          setLoading(false);
        }
      });
    return () => { isMounted = false; };
  }, []);

  const load = (forceReload = false) => {
    if (!selectedEventId) return;
    setLoading(true);
    getReplayData({ eventId: selectedEventId, leadDay: 5, forceReload })
      .then((data) => { setReplay(data); setError(null); setLoading(false); })
      .catch(() => { setError('Failed to load the verification record for this event.'); setLoading(false); });
  };

  useEffect(() => { load(); }, [selectedEventId]); // eslint-disable-line react-hooks/exhaustive-deps

  if (loading && !replay) {
    return <div className="page-container"><LoadingState message="Loading the verified case study..." /></div>;
  }
  if (error && !replay) {
    return <div className="page-container"><ErrorState title="Historical Replay Unavailable" message={error} onRetry={() => load(true)} /></div>;
  }
  if (!replay?.leadDayTrajectory?.length) {
    return (
      <div className="page-container">
        <EmptyState title="No replay record" message="The archive has no replay event yet." onAction={() => load(true)} actionLabel="Reload" />
      </div>
    );
  }

  const traj = replay.leadDayTrajectory;
  const event = events.find((e) => e.eventId === selectedEventId);
  const worst = traj.reduce((a, b) => (b.absErrorMm > a.absErrorMm ? b : a), traj[0]);
  const observed = traj[0].actualPrecipMm;

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
      <div className="analysis-header-panel">
        <div className="analysis-header-eyebrow">
          <ClockIcon size={14} style={{ color: '#38BDF8' }} />
          <span>Verified case study &bull; archived ECMWF HRES forecast vs ERA5</span>
        </div>
        <div className="analysis-header-top">
          <div className="analysis-title-group">
            <h1>Historical Replay: {event?.label || `${replay.region} heavy-rain bust`}</h1>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px', maxWidth: '900px', lineHeight: 1.5 }}>
              One real forecast bust from the 2018&ndash;2021 archive. The same valid date ({replay.validTime.slice(0, 10)}) was
              forecast by ten different model runs, from 1 to 10 days ahead, and we compare each with the single ERA5 outcome.
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>REAL ARCHIVE RECORD</span>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => load(true)} style={{ height: '32px' }}>
              <RefreshCwIcon size={13} className={loading ? 'spin' : ''} style={{ marginRight: '6px' }} />
              Reload
            </button>
          </div>
        </div>
      </div>

      <Card title="What the forecast said, day by day"
        subtitle={`${replay.region} grid point, valid ${replay.validTime.slice(0, 10)}`}>
        <TrajectoryChart trajectory={traj} />
        <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '10px', lineHeight: 1.55 }}>
          ERA5 recorded <strong style={{ color: 'var(--text-primary)' }}>{observed.toFixed(1)} mm</strong>. The Day {worst.leadDay} forecast
          (issued {worst.initTime.slice(0, 10)}) called <strong style={{ color: '#FDBA74' }}>{worst.forecastPrecipMm.toFixed(1)} mm</strong>, an
          error of {worst.absErrorMm.toFixed(1)} mm: a heavy-rain false alarm. Most other lead days were close, which is exactly why a single
          forecast can look trustworthy and still bust.
        </div>
      </Card>

      <Card title="Lead-day record" subtitle="Real ECMWF HRES values at one grid point vs ERA5">
        <div style={{ overflowX: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12.5px' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: 'var(--text-muted)' }}>
                {['Lead', 'Forecast issued', 'Forecast (mm)', 'Observed (mm)', 'Error (mm)'].map((h) => (
                  <th key={h} style={{ padding: '6px 8px', borderBottom: '1px solid var(--border-subtle, #1E293B)' }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {traj.map((t) => (
                <tr key={t.leadDay} style={{ background: t.leadDay === worst.leadDay ? 'rgba(249,115,22,0.12)' : 'transparent' }}>
                  <td style={{ padding: '6px 8px' }}>Day {t.leadDay}</td>
                  <td style={{ padding: '6px 8px' }}>{t.initTime.slice(0, 10)}</td>
                  <td style={{ padding: '6px 8px' }}>{t.forecastPrecipMm.toFixed(1)}</td>
                  <td style={{ padding: '6px 8px' }}>{t.actualPrecipMm.toFixed(1)}</td>
                  <td style={{ padding: '6px 8px', fontWeight: t.leadDay === worst.leadDay ? 700 : 400 }}>{t.absErrorMm.toFixed(1)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div style={{ fontSize: '11.5px', color: 'var(--text-muted)', lineHeight: 1.5 }}>{replay.disclaimer}</div>
    </div>
  );
}
