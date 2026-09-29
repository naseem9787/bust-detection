/**
 * Primary Destination: Forecast Page
 * SIH 26079: AI-Based Forecast Bust Detection for Medium-Range Weather Forecasts
 *
 * Directly answers the primary user question:
 * "Where is the forecast most likely to bust, at what lead time, and why?"
 *
 * Visual Hierarchy:
 * - TOP: Forecast initialization date/time, cycle, and Day 1–10 lead-time selector
 * - MAIN AREA: The India risk map dominates the screen; side panel shows selected region deep dive
 * - SECONDARY AREA: Integrated lead-time error trend chart and supporting historical performance
 */

import React, { useState, useEffect, useMemo } from 'react';

// API Service Layer
import {
  getForecast,
  getExplanation,
  getRegions,
  getHistoricalPerformance,
} from '../services/api.js';

// Modular Forecast Components
import { ForecastHeader } from '../components/forecast/ForecastHeader.jsx';
import { LeadDaySelector } from '../components/forecast/LeadDaySelector.jsx';
import { IndiaRiskMap } from '../components/forecast/IndiaRiskMap.jsx';
import { RegionalSummary } from '../components/forecast/RegionalSummary.jsx';
import { ForecastErrorChart } from '../components/forecast/ForecastErrorChart.jsx';
import { HistoricalPerformance } from '../components/forecast/HistoricalPerformance.jsx';

import { LoadingState } from '../components/feedback/LoadingState.jsx';
import { ErrorState } from '../components/feedback/ErrorState.jsx';
import { EmptyState } from '../components/feedback/EmptyState.jsx';

const EMPTY_REGIONAL_METRICS = {};

export function ForecastPage({ selectedCycle = '2026-09-29 00Z' }) {
  // Page State
  const [leadDay, setLeadDay] = useState(5);
  const [selectedRegionShortName, setSelectedRegionShortName] = useState('West Coast');
  const [allRegions, setAllRegions] = useState([]);
  const [forecastPayload, setForecastPayload] = useState(null);
  const [explanationPayload, setExplanationPayload] = useState(null);
  const [historicalData, setHistoricalData] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  const handleRetry = () => {
    setError(null);
    setIsLoading(true);
    setRetryCount((c) => c + 1);
  };

  // 1. Initial Load: Fetch Regions List
  useEffect(() => {
    let isMounted = true;
    getRegions()
      .then((regions) => {
        if (isMounted) setAllRegions(regions);
      })
      .catch((err) => {
        console.error('Error fetching regions:', err);
      });
    return () => {
      isMounted = false;
    };
  }, []);

  // 2. Fetch Forecast, Explanation & Historical when Cycle, LeadDay, or SelectedRegion changes
  useEffect(() => {
    let isMounted = true;
    const forceReload = retryCount > 0;

    Promise.all([
      getForecast({
        cycle: selectedCycle,
        leadDay,
        regionId: selectedRegionShortName,
        forceReload,
      }),
      getExplanation({
        cycle: selectedCycle,
        leadDay,
        regionId: selectedRegionShortName,
        forceReload,
      }),
      getHistoricalPerformance({
        leadDay,
        regionId: selectedRegionShortName,
        forceReload,
      }),
    ])
      .then(([fcst, exp, hist]) => {
        if (!isMounted) return;
        setForecastPayload(fcst);
        setExplanationPayload(exp);
        setHistoricalData(hist);
        setIsLoading(false);
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Error in forecast page data pipeline:', err);
        setError('Failed to fetch verification metrics for the selected lead time.');
        setIsLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [selectedCycle, leadDay, selectedRegionShortName, retryCount]);

  // Find active region object
  const activeRegion = useMemo(() => {
    return (
      allRegions.find(
        (r) =>
          r.shortName === selectedRegionShortName ||
          r.id === selectedRegionShortName ||
          r.name.includes(selectedRegionShortName)
      ) || allRegions[5] || {
        id: 'west-coast',
        name: 'West Coast (Konkan/Goa/Kerala)',
        shortName: 'West Coast',
        baselineRisk: 0.451,
      }
    );
  }, [allRegions, selectedRegionShortName]);

  // Regional metrics for the choropleth map supplied by the forecast API layer
  const regionalMetrics = forecastPayload?.regionalMetrics || EMPTY_REGIONAL_METRICS;

  // Identify the highest risk region at current lead time from API regional metrics
  const topRiskItem = useMemo(() => {
    let topName = 'West Coast';
    let maxProb = 0;
    Object.entries(regionalMetrics).forEach(([key, m]) => {
      if (m?.bustProbability > maxProb) {
        maxProb = m.bustProbability;
        topName = m.regionName || m.shortName || key;
      }
    });
    return { name: topName, probability: maxProb };
  }, [regionalMetrics]);

  return (
    <div className="forecast-page-layout">
      {/* =========================================================================
          1. TOP: Initialization Metadata, Cycle, and Core Finding Callout
          ========================================================================= */}
      <ForecastHeader
        cycle={selectedCycle}
        leadDay={leadDay}
        topRiskRegion={topRiskItem.name}
        topRiskProbability={topRiskItem.probability}
        primaryTrigger="IMD heavy rainfall categorical shift (moderate -> heavy miss)"
      />

      {/* =========================================================================
          2. TOP CONTROLS: Day 1–Day 10 Lead-Time Selector
          ========================================================================= */}
      <LeadDaySelector
        leadDay={leadDay}
        onChange={setLeadDay}
        cycleTimestamp={selectedCycle}
      />

      {/* Loading, Error & Empty States */}
      {error && !forecastPayload && (
        <ErrorState
          title="Forecast Service Error"
          message={error}
          onRetry={handleRetry}
        />
      )}

      {isLoading && !forecastPayload && (
        <LoadingState
          message={`Loading Medium-Range Forecast & Verification: Day ${leadDay}...`}
          subtext="Fetching ECMWF HRES 1.5° pointwise comparison against ERA5 truth"
        />
      )}

      {!isLoading && !error && !forecastPayload && (
        <EmptyState
          title="Forecast Record Unavailable"
          message={`No forecast verification records available for ${selectedRegionShortName} at Day ${leadDay}.`}
          onAction={handleRetry}
          actionLabel="Retry Forecast Query"
        />
      )}

      {/* =========================================================================
          3. MAIN AREA: Dominant India Risk Map + Selected Region Deep Dive
          ========================================================================= */}
      {forecastPayload && (
        <div className="map-and-summary-grid">
          {/* Dominant Map Component */}
          <div className="dominant-map-container">
            <IndiaRiskMap
              selectedRegionId={selectedRegionShortName}
              onSelectRegion={setSelectedRegionShortName}
              leadDay={leadDay}
              regionalMetrics={regionalMetrics}
            />
          </div>

          {/* Regional Summary Deep Dive Sidebar */}
          <div className="regional-summary-sidebar">
            <RegionalSummary
              region={activeRegion}
              forecastData={forecastPayload}
              explanationData={explanationPayload}
            />
          </div>
        </div>
      )}

      {/* =========================================================================
          4. SECONDARY AREA: Integrated Error Trajectory & Climatological Verification
          ========================================================================= */}
      {forecastPayload && (
        <div className="secondary-analysis-grid">
          {/* Lead-Time Error Trend Chart */}
          <ForecastErrorChart
            regionName={activeRegion.shortName}
            leadDay={leadDay}
            bustProbability={forecastPayload.verification?.bustProbability ?? 0.45}
          />

          {/* Supporting Historical Climatology Context */}
          <HistoricalPerformance
            regionName={activeRegion.shortName}
            leadDay={leadDay}
            historicalData={historicalData}
          />
        </div>
      )}
    </div>
  );
}
