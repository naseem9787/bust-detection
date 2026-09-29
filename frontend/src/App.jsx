/**
 * Main Application Shell
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 * Ministry of Earth Sciences (MoES) / NCMRWF
 */

import React, { useState, Suspense, lazy, useCallback } from 'react';
import './App.css';

// Router
import { useRouter, ROUTES } from './router/useRouter.js';

// Shell Navigation Components
import { AppHeader } from './components/navigation/AppHeader.jsx';
import { MobileNav } from './components/navigation/MobileNav.jsx';

// Global Feedback States
import { LoadingState } from './components/feedback/LoadingState.jsx';
import { ErrorState } from './components/feedback/ErrorState.jsx';

// Route-level code splitting: Pages loaded on demand with suspense
const ForecastPage = lazy(() =>
  import('./pages/ForecastPage.jsx').then((m) => ({ default: m.ForecastPage }))
);
const HistoricalPerformancePage = lazy(() =>
  import('./pages/HistoricalPerformancePage.jsx').then((m) => ({ default: m.HistoricalPerformancePage }))
);
const HistoricalReplayPage = lazy(() =>
  import('./pages/HistoricalReplayPage.jsx').then((m) => ({ default: m.HistoricalReplayPage }))
);
const RegionsPage = lazy(() =>
  import('./pages/RegionsPage.jsx').then((m) => ({ default: m.RegionsPage }))
);
const ModelInsightsPage = lazy(() =>
  import('./pages/ModelInsightsPage.jsx').then((m) => ({ default: m.ModelInsightsPage }))
);
const AboutPage = lazy(() =>
  import('./pages/AboutPage.jsx').then((m) => ({ default: m.AboutPage }))
);

export default function App() {
  const { currentRoute, navigate } = useRouter();

  // Application Shell State
  const [isMobileNavOpen, setIsMobileNavOpen] = useState(false);
  const [selectedCycle, setSelectedCycle] = useState('2026-09-29 00Z');
  const [isLoading, setIsLoading] = useState(false);
  const [globalError, setGlobalError] = useState(null);

  const handleOpenMobileNav = useCallback(() => setIsMobileNavOpen(true), []);
  const handleCloseMobileNav = useCallback(() => setIsMobileNavOpen(false), []);

  // Simulated cycle change with brief realistic loading state
  const handleCycleChange = useCallback((newCycle) => {
    setSelectedCycle(newCycle);
    setIsLoading(true);
    setGlobalError(null);
    setTimeout(() => {
      setIsLoading(false);
    }, 450);
  }, []);

  const handleRetry = useCallback(() => {
    setGlobalError(null);
    setIsLoading(true);
    setTimeout(() => {
      setIsLoading(false);
    }, 400);
  }, []);

  // Render active page based on Information Architecture
  const renderActivePage = () => {
    if (globalError) {
      return (
        <ErrorState
          title="Forecast Feed Error"
          message={globalError}
          onRetry={handleRetry}
        />
      );
    }

    if (isLoading) {
      return (
        <LoadingState
          message={`Loading Forecast Cycle: ${selectedCycle}...`}
          subtext="Calibrating pointwise ECMWF HRES error thresholds"
        />
      );
    }

    return (
      <Suspense fallback={<LoadingState message="Loading operational view..." />}>
        {currentRoute === ROUTES.HISTORICAL && <HistoricalPerformancePage />}
        {currentRoute === ROUTES.REPLAY && <HistoricalReplayPage />}
        {currentRoute === ROUTES.REGIONS && <RegionsPage />}
        {currentRoute === ROUTES.INSIGHTS && <ModelInsightsPage />}
        {currentRoute === ROUTES.ABOUT && <AboutPage />}
        {currentRoute === ROUTES.FORECAST && <ForecastPage selectedCycle={selectedCycle} />}
        {!Object.values(ROUTES).includes(currentRoute) && <ForecastPage selectedCycle={selectedCycle} />}
      </Suspense>
    );
  };

  return (
    <div className="app-container">
      {/* 1. Application Header with Cycle Selector & Desktop Navigation */}
      <AppHeader
        currentRoute={currentRoute}
        onNavigate={navigate}
        selectedCycle={selectedCycle}
        onCycleChange={handleCycleChange}
        onOpenMobileNav={handleOpenMobileNav}
      />

      {/* 2. Responsive Mobile Navigation Drawer */}
      <MobileNav
        isOpen={isMobileNavOpen}
        onClose={handleCloseMobileNav}
        currentRoute={currentRoute}
        onNavigate={navigate}
      />

      {/* 3. Main Content Container */}
      <main className="main-content" id="main-content">
        {renderActivePage()}
      </main>
    </div>
  );
}
