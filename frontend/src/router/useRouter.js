/**
 * Lightweight Client-Side Router Hook
 * Syncs route state with window.location.hash for deep linking and back/forward navigation.
 * Zero external dependencies.
 */

import { useState, useEffect, useCallback } from 'react';

export const ROUTES = {
  FORECAST: 'forecast',
  HISTORICAL: 'historical',
  REPLAY: 'replay',
  REGIONS: 'regions',
  INSIGHTS: 'insights',
  ABOUT: 'about',
};

export const NAV_ITEMS = [
  { id: ROUTES.FORECAST, label: 'Forecast', icon: 'RadarIcon' },
  { id: ROUTES.HISTORICAL, label: 'Historical Performance', icon: 'TrendingUpIcon' },
  { id: ROUTES.REPLAY, label: 'Historical Replay', icon: 'ClockIcon' },
  { id: ROUTES.REGIONS, label: 'Regions', icon: 'MapPinIcon' },
  { id: ROUTES.INSIGHTS, label: 'Model Insights', icon: 'DatabaseIcon' },
  { id: ROUTES.ABOUT, label: 'About', icon: 'HelpCircleIcon' },
];

function getRouteFromHash() {
  const hash = window.location.hash.replace(/^#\/?/, '').trim().toLowerCase();
  const validRoutes = Object.values(ROUTES);
  return validRoutes.includes(hash) ? hash : ROUTES.FORECAST;
}

export function useRouter() {
  const [currentRoute, setCurrentRoute] = useState(getRouteFromHash);

  useEffect(() => {
    const handleHashChange = () => {
      setCurrentRoute(getRouteFromHash());
    };

    window.addEventListener('hashchange', handleHashChange);
    return () => window.removeEventListener('hashchange', handleHashChange);
  }, []);

  const navigate = useCallback((route) => {
    if (Object.values(ROUTES).includes(route)) {
      window.location.hash = `#/${route}`;
      setCurrentRoute(route);
    }
  }, []);

  return { currentRoute, navigate };
}
