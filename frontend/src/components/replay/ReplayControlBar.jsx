/**
 * ReplayControlBar Component
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 *
 * Provides event selection, initialization cycle selection,
 * and scientific benchmark context for historical replay analysis.
 */

import React, { useMemo } from 'react';
import { Badge } from '../ui/Badge.jsx';
import { CalendarIcon, MapPinIcon } from '../icons/Icons.jsx';

function ReplayControlBarComponent({
  events = [],
  selectedEventId = 'kerala-2018',
  onSelectEvent,
  selectedCycle = '2018-08-14 00Z',
  onSelectCycle,
  currentEventMeta = {},
  className = '',
}) {
  const eventOptions = useMemo(
    () =>
      events.map((e) => ({
        id: e.id,
        label: e.name,
      })),
    [events]
  );

  const cycleOptions = useMemo(
    () =>
      (currentEventMeta.initializations || []).map((c) => ({
        id: c.id,
        label: c.label,
      })),
    [currentEventMeta.initializations]
  );

  return (
    <div className={`replay-control-bar ${className}`} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      {/* 1. Primary Replay Selectors Row */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 18px',
          flexWrap: 'wrap',
          gap: '14px',
        }}
      >
        {/* Left: Replay Mode Badge & Event Selector */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: '#38BDF8',
                display: 'inline-block',
                boxShadow: '0 0 6px rgba(56, 189, 248, 0.4)',
              }}
            />
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Historical Replay
            </span>
          </div>

          <div style={{ width: '1px', height: '22px', backgroundColor: 'var(--border-subtle)' }} />

          {/* Event Selector */}
          <div className="replay-filter-item">
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              Historical Event:
            </span>
            <select
              className="select-control replay-select-control"
              style={{ height: '32px', fontSize: '12px', fontWeight: 600 }}
              value={selectedEventId}
              onChange={(e) => onSelectEvent && onSelectEvent(e.target.value)}
              aria-label="Select Historical Weather Event"
            >
              {eventOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Right: Forecast Initialization Cycle */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }} className="replay-controls-right">
          <div className="replay-filter-item">
            <span style={{ fontSize: '11px', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
              Forecast Cycle:
            </span>
            <select
              className="select-control replay-select-control"
              style={{ height: '32px', fontSize: '12px' }}
              value={selectedCycle}
              onChange={(e) => onSelectCycle && onSelectCycle(e.target.value)}
              aria-label="Select Replay Forecast Cycle"
            >
              {cycleOptions.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <Badge variant="neutral">
            <CalendarIcon size={12} style={{ marginRight: '4px' }} />
            {currentEventMeta.dateRange || 'Historical Record'}
          </Badge>
        </div>
      </div>

      {/* 2. Event Synopsis & Benchmark Quality Banner */}
      <div
        style={{
          backgroundColor: 'var(--bg-surface-raised)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-md)',
          padding: '12px 18px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '12px',
        }}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '3px', maxWidth: '850px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {currentEventMeta.name}
            </span>
            <span className="badge badge-subtle" style={{ fontSize: '10px' }}>
              <MapPinIcon size={10} style={{ marginRight: '3px' }} />
              Primary Focus: {currentEventMeta.primaryRegionName || 'West Coast'}
            </span>
            <span className="badge badge-neutral" style={{ fontSize: '10px' }}>
              {currentEventMeta.category}
            </span>
          </div>

          <div style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.4 }}>
            {currentEventMeta.description}
          </div>
        </div>

        {/* Data Quality / Disclaimer Badge */}
        <div
          style={{
            fontSize: '10.5px',
            color: 'var(--text-muted)',
            fontFamily: 'var(--font-mono)',
            padding: '4px 10px',
            backgroundColor: 'rgba(255, 255, 255, 0.03)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-xs)',
          }}
          title={currentEventMeta.dataQualityBadge}
        >
          {currentEventMeta.dataQualityBadge || 'BENCHMARK REANALYSIS CALIBRATION DATA'}
        </div>
      </div>
    </div>
  );
}
export const ReplayControlBar = React.memo(ReplayControlBarComponent);
