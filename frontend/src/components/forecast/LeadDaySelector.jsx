/**
 * LeadDaySelector Component
 * Easy to scan and interact Day 1 through Day 10 horizontal lead-time selector
 */

import React, { useState, useEffect } from 'react';
import { LEAD_DAYS } from '../../design-system/weather-tokens.js';
import { Button } from '../ui/Button.jsx';
import { PlayIcon, PauseIcon, StepBackIcon, StepForwardIcon, ClockIcon } from '../icons/Icons.jsx';

export function LeadDaySelector({
  leadDay = 5,
  onChange,
  cycleTimestamp = '2021-09-30 12Z',
  className = '',
}) {
  const [isPlaying, setIsPlaying] = useState(false);

  // Playback timer (1.2s per step)
  useEffect(() => {
    if (!isPlaying) return;
    const interval = setInterval(() => {
      onChange((prev) => (prev >= 10 ? 1 : prev + 1));
    }, 1200);
    return () => clearInterval(interval);
  }, [isPlaying, onChange]);

  const handleStepBack = () => {
    setIsPlaying(false);
    onChange(Math.max(1, leadDay - 1));
  };

  const handleStepForward = () => {
    setIsPlaying(false);
    onChange(Math.min(10, leadDay + 1));
  };

  const togglePlay = () => {
    setIsPlaying((prev) => !prev);
  };

  // Compute simulated valid date based on cycle
  const currentLeadHours = leadDay * 24;
  const isMediumRangeRisk = leadDay >= 5;

  return (
    <div className={`lead-day-selector-panel ${className}`}>
      {/* Top Header Row: Status, Lead hours callout, and Play Controls */}
      <div className="lead-selector-top-row">
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <ClockIcon size={14} style={{ color: '#38BDF8' }} />
            <span style={{ fontSize: '11px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.04em', color: 'var(--text-secondary)' }}>
              How Far Ahead
            </span>
          </div>

          <div
            className="badge badge-neutral tabular-nums"
            style={{ borderColor: '#38BDF8', color: '#38BDF8', fontWeight: 600 }}
            title={`Forecast run: ${cycleTimestamp}`}
          >
            {leadDay} day{leadDay === 1 ? '' : 's'} ahead
          </div>

          {isMediumRangeRisk && (
            <span className="badge badge-risk-elevated">
              <span className="badge-dot" />
              Forecasts get less reliable this far ahead
            </span>
          )}
        </div>

        {/* Playback Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Button
            size="sm"
            variant="outline"
            onClick={handleStepBack}
            disabled={leadDay <= 1}
            title="Step back 24h"
          >
            <StepBackIcon size={12} />
          </Button>

          <Button
            size="sm"
            variant={isPlaying ? 'primary' : 'secondary'}
            onClick={togglePlay}
            title={isPlaying ? 'Pause animation' : 'Auto-play Day 1 to 10'}
          >
            {isPlaying ? <PauseIcon size={12} /> : <PlayIcon size={12} />}
            <span>{isPlaying ? 'Pause' : 'Play Timeline'}</span>
          </Button>

          <Button
            size="sm"
            variant="outline"
            onClick={handleStepForward}
            disabled={leadDay >= 10}
            title="Step forward 24h"
          >
            <StepForwardIcon size={12} />
          </Button>
        </div>
      </div>

      {/* Discrete 10-Day Button Bar */}
      <div className="lead-days-grid" role="tablist" aria-label="Lead Day Selection">
        {LEAD_DAYS.map((d) => {
          const isSelected = d.day === leadDay;
          const isBustProne = d.day >= 5;

          return (
            <button
              key={d.day}
              type="button"
              className={`lead-day-pill-btn ${isSelected ? 'active' : ''} ${isBustProne ? 'bust-prone-zone' : ''}`}
              onClick={() => {
                setIsPlaying(false);
                onChange(d.day);
              }}
              role="tab"
              aria-selected={isSelected}
              title={`Jump to Day ${d.day} (+${d.hours} hours)`}
            >
              <div className="lead-day-number">Day {d.day}</div>
              <div className="lead-day-hours">+{d.hours}h</div>
              {isBustProne && <div className="lead-day-risk-marker" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
