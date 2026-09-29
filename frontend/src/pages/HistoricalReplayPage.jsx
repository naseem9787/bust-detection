/**
 * Historical Replay Page
 * SIH 26079: AI-Based Forecast Bust Detection Platform
 *
 * PURPOSE:
 * Operational case study replay interface allowing judges and forecasters
 * to select a verified historical weather event and examine how the AI bust detection
 * system evaluated forecast confidence and bust probability across lead horizons (Day 1–10).
 *
 * USER FLOW:
 * Select Event -> Select Cycle -> Select Day 1–10 -> View India Map
 * -> Inspect Affected Region -> Inspect Bust Probability -> Inspect Explanation
 * -> Compare Forecast vs Observed Outcome
 */

import React, { useState, useEffect } from 'react';
import { getReplayEvents, getReplayData } from '../services/api.js';
import { ReplayControlBar } from '../components/replay/ReplayControlBar.jsx';
import { ReplayOutcomeComparison } from '../components/replay/ReplayOutcomeComparison.jsx';
import { IndiaRiskMap } from '../components/forecast/IndiaRiskMap.jsx';
import { LeadDaySelector } from '../components/forecast/LeadDaySelector.jsx';
import { ExplanationPanel } from '../components/explainability/ExplanationPanel.jsx';
import { LoadingState } from '../components/feedback/LoadingState.jsx';
import { ErrorState } from '../components/feedback/ErrorState.jsx';
import { EmptyState } from '../components/feedback/EmptyState.jsx';
import {
  ClockIcon,
  ShieldCheckIcon,
  RefreshCwIcon,
} from '../components/icons/Icons.jsx';

export function HistoricalReplayPage() {
  const [events, setEvents] = useState([]);
  const [selectedEventId, setSelectedEventId] = useState('kerala-2018');
  const [selectedCycle, setSelectedCycle] = useState('2018-08-14 00Z');
  const [selectedLeadDay, setSelectedLeadDay] = useState(5);
  const [selectedRegionId, setSelectedRegionId] = useState('West Coast');

  const [replayData, setReplayData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Load initial event catalog
  useEffect(() => {
    let isMounted = true;
    getReplayEvents()
      .then((evtList) => {
        if (isMounted && evtList?.length) {
          setEvents(evtList);
          const firstEvt = evtList[0];
          setSelectedEventId(firstEvt.id);
          setSelectedCycle(firstEvt.initializations[0]?.id || '2018-08-14 00Z');
          setSelectedRegionId(firstEvt.primaryRegionName || 'West Coast');
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('Failed to load replay events:', err);
          setError('Unable to load historical replay events catalogue.');
        }
      });

    return () => {
      isMounted = false;
    };
  }, []);

  // Fetch replay state when event, cycle, leadDay, or region changes
  useEffect(() => {
    let isMounted = true;
    getReplayData({
      eventId: selectedEventId,
      cycle: selectedCycle,
      leadDay: selectedLeadDay,
      regionId: selectedRegionId,
    })
      .then((data) => {
        if (isMounted) {
          setReplayData(data);
          setLoading(false);
          setError(null);
        }
      })
      .catch((err) => {
        if (isMounted) {
          console.error('Failed to fetch replay data:', err);
          setError('Failed to load verification record for selected event parameters.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedEventId, selectedCycle, selectedLeadDay, selectedRegionId]);

  // When user switches event, sync cycle and primary region
  const handleEventChange = (newEventId) => {
    setSelectedEventId(newEventId);
    const eventObj = events.find((e) => e.id === newEventId);
    if (eventObj) {
      if (eventObj.initializations?.length) {
        setSelectedCycle(eventObj.initializations[0].id);
      }
      if (eventObj.primaryRegionName) {
        setSelectedRegionId(eventObj.primaryRegionName);
      }
    }
  };

  const handleRefresh = () => {
    setLoading(true);
    getReplayData({
      eventId: selectedEventId,
      cycle: selectedCycle,
      leadDay: selectedLeadDay,
      regionId: selectedRegionId,
    })
      .then((data) => {
        setReplayData(data);
        setLoading(false);
        setError(null);
      })
      .catch((_err) => {
        setError('Failed to refresh replay data.');
        setLoading(false);
      });
  };

  if (loading && !replayData) {
    return (
      <div className="page-container">
        <LoadingState message="Loading historical re-analysis archive and ECMWF forecast progression..." />
      </div>
    );
  }

  if (error && !replayData) {
    return (
      <div className="page-container">
        <ErrorState
          title="Historical Replay Unavailable"
          message={error}
          onRetry={handleRefresh}
        />
      </div>
    );
  }

  if (!loading && !error && !replayData) {
    return (
      <div className="page-container">
        <EmptyState
          title="No Historical Replay Data Found"
          message={`No analytical replay record matches the selected event (${selectedEventId}).`}
          onAction={handleRefresh}
          actionLabel="Reset Replay"
        />
      </div>
    );
  }

  const {
    meta = {},
    predictionSummary = {},
    historicalOutcome = {},
    regionalMetrics = {},
    explanationFactors = [],
    bulletinSummary = '',
  } = replayData || {};

  return (
    <div className="page-container" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      {/* 1. Page Header Panel */}
      <div className="analysis-header-panel">
        <div className="analysis-header-eyebrow">
          <ClockIcon size={14} style={{ color: '#38BDF8' }} />
          <span>Operational Verification Case Study &bull; Multi-Horizon Ground Truth Replay</span>
        </div>

        <div className="analysis-header-top">
          <div className="analysis-title-group">
            <h1>Historical Replay: Verified Meteorological Case Studies</h1>
            <div style={{ fontSize: '12.5px', color: 'var(--text-secondary)', marginTop: '4px', maxWidth: '880px', lineHeight: 1.5 }}>
              Select verified high-impact historical weather events and replay how the AI bust detection system evaluated medium-range forecast skill, calibrated confidence, and systematic error growth against verified ground truth.
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0 }}>
            <span className="badge badge-neutral" style={{ fontFamily: 'var(--font-mono)' }}>CASE STUDY ARCHIVE</span>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={handleRefresh}
              title="Reload simulation"
              style={{ height: '32px' }}
            >
              <RefreshCwIcon size={13} className={loading ? 'spin' : ''} style={{ marginRight: '6px' }} />
              Reset Replay
            </button>
          </div>
        </div>
      </div>

      {/* 2. Replay Control Bar: Event Selector & Initializations */}
      <ReplayControlBar
        events={events}
        selectedEventId={selectedEventId}
        onSelectEvent={handleEventChange}
        selectedCycle={selectedCycle}
        onSelectCycle={setSelectedCycle}
        currentEventMeta={meta}
      />

      {/* 3. Horizon Scrubber: Day 1 through Day 10 Stepper / Player */}
      <LeadDaySelector
        leadDay={selectedLeadDay}
        onChange={setSelectedLeadDay}
        cycleTimestamp={selectedCycle}
      />

      {/* 4. Primary Replay Workspace: Map (Dominant Visual) + Side Analytical Panels */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.35fr) minmax(0, 1fr)',
          gap: '20px',
          alignItems: 'start',
        }}
        className="replay-workspace-grid"
      >
        {/* Left: India Geographic Risk Map (Primary Visual Element) */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          <IndiaRiskMap
            selectedRegionId={selectedRegionId}
            onSelectRegion={setSelectedRegionId}
            leadDay={selectedLeadDay}
            regionalMetrics={regionalMetrics}
          />

          <div
            style={{
              padding: '10px 14px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '11.5px',
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: '8px',
            }}
          >
            <span>
              Inspecting region: <strong style={{ color: 'var(--text-primary)' }}>{selectedRegionId}</strong> (Click any region to inspect localized risk).
            </span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '11px', color: 'var(--text-muted)' }}>
              Horizon: T+{selectedLeadDay * 24}h &bull; Cycle: {selectedCycle}
            </span>
          </div>
        </div>

        {/* Right: Analytical Ground Truth vs Prediction Comparison */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <ReplayOutcomeComparison
            predictionSummary={predictionSummary}
            historicalOutcome={historicalOutcome}
            leadDay={selectedLeadDay}
            regionName={selectedRegionId}
          />
        </div>
      </div>

      {/* 5. Explainability Diagnostic Workspace */}
      <div style={{ marginTop: '10px' }}>
        <div style={{ marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <ShieldCheckIcon size={16} style={{ color: '#38BDF8' }} />
          <h2 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', margin: 0 }}>
            Explainability Attribution &bull; Why was confidence assessed at this level?
          </h2>
        </div>

        <ExplanationPanel
          confidence={predictionSummary.confidence ?? 0.22}
          factors={explanationFactors}
          regionName={selectedRegionId}
          leadDay={selectedLeadDay}
          cycle={selectedCycle}
          bulletinSummary={bulletinSummary}
        />
      </div>
    </div>
  );
}
