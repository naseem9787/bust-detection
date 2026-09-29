/**
 * Responsive Mobile Navigation Drawer
 * Accessible slide-in menu for tablet and mobile viewports.
 */

import React, { useEffect } from 'react';
import { NAV_ITEMS } from '../../router/useRouter.js';
import {
  RadarIcon,
  TrendingUpIcon,
  MapPinIcon,
  DatabaseIcon,
  HelpCircleIcon,
  ClockIcon,
  XIcon,
} from '../icons/Icons.jsx';

const ICON_MAP = {
  RadarIcon,
  TrendingUpIcon,
  MapPinIcon,
  DatabaseIcon,
  HelpCircleIcon,
  ClockIcon,
};

function MobileNavComponent({ isOpen, onClose, currentRoute, onNavigate }) {
  // Close drawer on Escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="mobile-nav-backdrop" onClick={onClose}>
      <aside
        className="mobile-nav-drawer"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-label="Mobile Navigation"
      >
        <div className="mobile-nav-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <RadarIcon size={18} style={{ color: '#38BDF8' }} />
            <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)' }}>
              NCMRWF SIH 26079
            </span>
          </div>
          <button
            type="button"
            className="mobile-nav-close-btn"
            onClick={onClose}
            aria-label="Close navigation"
          >
            <XIcon size={16} />
          </button>
        </div>

        <nav className="mobile-nav-list">
          {NAV_ITEMS.map((item) => {
            const Icon = ICON_MAP[item.icon] || RadarIcon;
            const isActive = item.id === currentRoute;

            return (
              <button
                key={item.id}
                type="button"
                className={`mobile-nav-item ${isActive ? 'active' : ''}`}
                onClick={() => {
                  onNavigate(item.id);
                  onClose();
                }}
              >
                <Icon size={16} />
                <span>{item.label}</span>
                {item.id === 'forecast' && (
                  <span className="badge badge-neutral" style={{ marginLeft: 'auto', fontSize: '9px' }}>
                    Primary
                  </span>
                )}
              </button>
            );
          })}
        </nav>

        <div className="mobile-nav-footer">
          <div style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
            Ministry of Earth Sciences (MoES) &bull; Medium-Range Forecast Bust Detection
          </div>
        </div>
      </aside>
    </div>
  );
}
export const MobileNav = React.memo(MobileNavComponent);
