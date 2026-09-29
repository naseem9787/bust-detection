/**
 * Operational Platform Header
 * Scientific identification, run cycle selector, active lead day, and responsive menu trigger.
 */

import React from 'react';
import { RadarIcon, MenuIcon } from '../icons/Icons.jsx';
import { DesktopNav } from './DesktopNav.jsx';
import { FORECAST_CYCLES } from './forecastCycles.js';

function AppHeaderComponent({
  currentRoute = 'forecast',
  onNavigate,
  selectedCycle = '2026-09-29 00Z',
  onCycleChange,
  onOpenMobileNav,
}) {
  return (
    <header className="app-header-container">
      <div className="app-header-top">
        <div className="header-left">
          {/* Mobile hamburger menu toggle */}
          <button
            type="button"
            className="mobile-menu-trigger"
            onClick={onOpenMobileNav}
            aria-label="Open mobile navigation"
          >
            <MenuIcon size={18} />
          </button>

          {/* NCMRWF MoES Brand Badge */}
          <div
            style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
            onClick={() => onNavigate('forecast')}
            title="Go to Forecast"
          >
            <RadarIcon size={18} style={{ color: '#38BDF8' }} />
            <span className="brand-badge">NCMRWF</span>
          </div>

          <div className="header-title-box">
            <div className="header-main-title">
              Forecast Bust Detection &amp; Verification
            </div>
            <div className="header-sub-title">
              SIH 26079 &bull; Ministry of Earth Sciences &bull; Medium-Range NWP
            </div>
          </div>
        </div>

        {/* Operational Context Controls */}
        <div className="header-right">
          {/* Forecast Cycle Selector */}
          <div className="header-cycle-wrapper">
            <span className="header-cycle-label">
              Cycle:
            </span>
            <select
              className="select-control header-cycle-select"
              value={selectedCycle}
              onChange={(e) => onCycleChange && onCycleChange(e.target.value)}
              aria-label="Select Forecast Initialization Cycle"
            >
              {FORECAST_CYCLES.map((cycle) => (
                <option key={cycle.id} value={cycle.id}>
                  {cycle.label}
                </option>
              ))}
            </select>
          </div>

          {/* Operational Status Dot */}
          <div className="header-status-pill" style={{ color: '#10B981' }} title="Phase 0/1 Model Feed Online">
            <span className="badge-dot" style={{ backgroundColor: '#10B981' }} />
            <span className="desktop-only">ONLINE</span>
          </div>
        </div>
      </div>

      {/* Desktop Navigation Row (Subtle, visually quiet tabs) */}
      <div className="desktop-nav-bar">
        <DesktopNav currentRoute={currentRoute} onNavigate={onNavigate} />
      </div>
    </header>
  );
}

export const AppHeader = React.memo(AppHeaderComponent);

