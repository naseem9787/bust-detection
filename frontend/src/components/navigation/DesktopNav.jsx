/**
 * Desktop Navigation Component
 * Visually quiet, restrained horizontal navigation modeled on professional tools (Google Maps / YouTube).
 * Avoids glowing cards or sidebar clutter.
 */

import React from 'react';
import { NAV_ITEMS } from '../../router/useRouter.js';
import {
  RadarIcon,
  TrendingUpIcon,
  MapPinIcon,
  DatabaseIcon,
  HelpCircleIcon,
  ClockIcon,
} from '../icons/Icons.jsx';

const ICON_MAP = {
  RadarIcon,
  TrendingUpIcon,
  MapPinIcon,
  DatabaseIcon,
  HelpCircleIcon,
  ClockIcon,
};

function DesktopNavComponent({ currentRoute, onNavigate }) {
  return (
    <nav className="desktop-nav" aria-label="Main Application Views">
      {NAV_ITEMS.map((item) => {
        const Icon = ICON_MAP[item.icon] || RadarIcon;
        const isActive = item.id === currentRoute;

        return (
          <button
            key={item.id}
            type="button"
            className={`nav-tab-btn ${isActive ? 'active' : ''}`}
            onClick={() => onNavigate(item.id)}
            aria-selected={isActive}
            role="tab"
          >
            <Icon size={14} className="nav-tab-icon" />
            <span>{item.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export const DesktopNav = React.memo(DesktopNavComponent);
