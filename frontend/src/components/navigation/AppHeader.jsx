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
  selectedCycle = '2021-09-30 12Z',
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

          {/* Team brand badge */}
          <div
            style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}
            onClick={() => onNavigate('forecast')}
            title="Go to Forecast"
          >
            <RadarIcon size={18} style={{ color: '#38BDF8' }} />
            <span className="brand-badge">TWP</span>
          </div>

          <div className="header-title-box">
            <div className="header-main-title">
              Forecast Bust Detection &amp; Verification
            </div>
            <div className="header-sub-title">
              SIH 2026 &bull; PS 26079 &bull; Research prototype on archived ECMWF HRES / ERA5 data
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
          <div className="header-status-pill" style={{ color: '#F59E0B' }} title="Serving archived 2018–2021 forecasts; no live NWP feed">
            <span className="badge-dot" style={{ backgroundColor: '#F59E0B' }} />
            <span className="desktop-only">ARCHIVE DATA</span>
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

