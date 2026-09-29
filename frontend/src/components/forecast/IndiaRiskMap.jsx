/**
 * IndiaRiskMap Component
 * Real map of India's 29 production states/UTs, colored by how likely
 * this forecast is to be substantially wrong in each one:
 * - Low risk -> green
 * - Moderate/Elevated risk -> yellow/orange
 * - High risk -> red
 */

import React, { useState, useMemo } from 'react';
import { INDIA_STATE_REGIONS } from '../../data/indiaStatesGeo.js';
import { OCEANIC_LANDMARKS, ISLAND_GROUPS } from '../../data/indiaGeoData.js';
import { MapLegend } from '../ui/MapLegend.jsx';
import { SegmentedControl } from '../ui/SegmentedControl.jsx';
import { MapPinIcon } from '../icons/Icons.jsx';
import { getBustRiskLevel, getConfidenceTier } from '../../utils/weatherRules.js';
import { TOKENS } from '../../design-system/tokens.js';

const INDIA_GEO_REGIONS = INDIA_STATE_REGIONS;

// Static Layer Switcher Options (hoisted to prevent re-instantiation)
const MAP_LAYER_OPTIONS = [
  { id: 'risk', label: 'Chance of Error' },
  { id: 'confidence', label: 'Reliability' },
  { id: 'precip', label: 'Rain Forecast Error' },
];

// Atmospheric Graticule Lines (10° to 35°N, 70° to 95°E)
const GRATICULES_LAT = [
  { lat: 35, y: 70, label: '35°N' },
  { lat: 30, y: 175, label: '30°N' },
  { lat: 25, y: 280, label: '25°N' },
  { lat: 20, y: 385, label: '20°N' },
  { lat: 15, y: 490, label: '15°N' },
  { lat: 10, y: 595, label: '10°N' },
];

const GRATICULES_LON = [
  { lon: 70, x: 75, label: '70°E' },
  { lon: 75, x: 165, label: '75°E' },
  { lon: 80, x: 255, label: '80°E' },
  { lon: 85, x: 345, label: '85°E' },
  { lon: 90, x: 435, label: '90°E' },
  { lon: 95, x: 525, label: '95°E' },
];

/**
 * Completely static geographic backdrop:
 * Atmospheric graticules, oceanic landmarks, island territories, and accessibility hatch defs.
 * Separated into a memoized component so region hovering and scrubbing do not re-reconcile 30+ static SVG nodes.
 */
const StaticMapBackdrop = React.memo(function StaticMapBackdrop() {
  return (
    <>
      {/* SVG Definitions: Severe Risk Hatch Pattern for Accessibility */}
      <defs>
        <pattern
          id="severe-bust-hatch"
          width="8"
          height="8"
          patternTransform="rotate(45 0 0)"
          patternUnits="userSpaceOnUse"
        >
          <line x1="0" y1="0" x2="0" y2="8" stroke="rgba(255, 255, 255, 0.25)" strokeWidth="1.5" />
        </pattern>
      </defs>

      {/* Oceanic Water Body Labels */}
      <g className="ocean-labels-group" fill="rgba(148, 163, 184, 0.35)" fontSize="10" fontWeight="600" letterSpacing="0.12em" fontFamily="var(--font-sans)">
        {OCEANIC_LANDMARKS.map((ocean) => (
          <text key={ocean.name} x={ocean.x} y={ocean.y} textAnchor="middle">
            {ocean.name}
          </text>
        ))}
      </g>

      {/* Atmospheric Graticules (Dashed Latitude & Longitude) */}
      <g className="graticule-group" stroke="rgba(255, 255, 255, 0.06)" strokeDasharray="3 4">
        {GRATICULES_LAT.map((g) => (
          <g key={`lat-${g.lat}`}>
            <line x1="30" y1={g.y} x2="590" y2={g.y} strokeWidth="1" />
            <text x="34" y={g.y - 3} fill="rgba(255, 255, 255, 0.3)" fontSize="8.5" fontFamily="var(--font-mono)">
              {g.label}
            </text>
          </g>
        ))}

        {GRATICULES_LON.map((g) => (
          <g key={`lon-${g.lon}`}>
            <line x1={g.x} y1="20" x2={g.x} y2="640" strokeWidth="1" />
            <text x={g.x + 3} y="655" fill="rgba(255, 255, 255, 0.3)" fontSize="8.5" fontFamily="var(--font-mono)">
              {g.label}
            </text>
          </g>
        ))}
      </g>

      {/* Island Territories (Lakshadweep & Andaman) */}
      <g className="islands-group" fill="#38BDF8" fillOpacity="0.4" stroke="#38BDF8" strokeWidth="1">
        {ISLAND_GROUPS.map((grp) => (
          <g key={grp.name}>
            {grp.points.map((pt, i) => (
              <circle key={i} cx={pt.cx} cy={pt.cy} r="3" />
            ))}
            <text
              x={grp.points[0].cx}
              y={grp.points[0].cy - 6}
              fill="rgba(148, 163, 184, 0.5)"
              fontSize="8"
              fontFamily="var(--font-sans)"
              textAnchor="middle"
            >
              {grp.name}
            </text>
          </g>
        ))}
      </g>
    </>
  );
});

function IndiaRiskMapComponent({
  selectedRegionId = 'West Coast',
  onSelectRegion,
  leadDay = 5,
  regionalMetrics = {}, // { [regionShortName]: { bustProbability, confidence, precipError, tempError } }
  className = '',
}) {
  const [mapLayer, setMapLayer] = useState('risk'); // 'risk' | 'confidence' | 'precip'
  const [zoomLevel, setZoomLevel] = useState(1);
  const [hoveredRegion, setHoveredRegion] = useState(null);

  const handleZoomIn = () => setZoomLevel((z) => Math.min(1.8, Number((z + 0.2).toFixed(1))));
  const handleZoomOut = () => setZoomLevel((z) => Math.max(0.9, Number((z - 0.2).toFixed(1))));
  const handleResetZoom = () => setZoomLevel(1);

  // Pre-calculate region fill colors and display metrics in a single memoized lookup
  // Prevents re-computing color logic on every hover or unrelated re-render
  const regionVisuals = useMemo(() => {
    const map = new Map();
    INDIA_GEO_REGIONS.forEach((region) => {
      const metrics = regionalMetrics[region.id] || regionalMetrics[region.shortName] || {};
      // Defaults only apply if a state is somehow missing from a live
      // response - real calibrated bust probability is almost always well
      // under 1%, so a near-zero default (not the old mock-era 35%) avoids
      // misleadingly painting an undata'd state red.
      const bustProb = metrics.bustProbability ?? 0.01;
      const confidence = metrics.confidence ?? 0.99;
      const precipError = metrics.precipError ?? 3.0;

      // The map's fill color and the legend below it (MapLegend.jsx) both
      // come from this SAME function (getBustRiskLevel) and the SAME real
      // percentage cutoffs - a state's color on the map always matches
      // exactly one legend band, never an independent color choice.
      let fillColor = '#10B981';
      if (mapLayer === 'confidence') {
        const tier = getConfidenceTier(confidence);
        fillColor = TOKENS.colors.confidence[tier]?.color || '#EAB308';
      } else if (mapLayer === 'precip') {
        if (precipError > 12) fillColor = '#0284C7';
        else if (precipError > 6) fillColor = '#0EA5E9';
        else fillColor = '#38BDF8';
      } else {
        const riskLevel = getBustRiskLevel(bustProb);
        switch (riskLevel) {
          case 'low':
            fillColor = '#10B981'; // green - matches legend "Low <1%"
            break;
          case 'moderate':
            fillColor = '#EAB308'; // yellow - matches legend "Moderate 1-3%"
            break;
          case 'elevated':
            fillColor = '#F97316'; // orange - matches legend "Elevated 3-6%"
            break;
          case 'high':
          default:
            fillColor = '#EF4444'; // red - matches legend "High >6%"
            break;
        }
      }

      // Shown with one decimal place below 1% (e.g. "0.3%") since almost
      // every real value falls under 1% - rounding to whole percent would
      // display "0%" for nearly the entire map and hide real differences.
      const bustPercent = bustProb < 0.01 ? Math.round(bustProb * 1000) / 10 : Math.round(bustProb * 100);
      const isSevere = bustProb >= 0.06; // matches legend "High >6%" band
      const displayValue =
        mapLayer === 'confidence'
          ? `${Math.round(confidence * 100)}%`
          : mapLayer === 'precip'
          ? `${precipError.toFixed(1)}mm`
          : `${bustPercent}%`;

      const visualData = {
        fillColor,
        bustPercent,
        confidencePercent: Math.round(confidence * 100),
        isSevere,
        displayValue,
      };

      map.set(region.shortName, visualData);
      map.set(region.id, visualData);
    });
    return map;
  }, [regionalMetrics, mapLayer]);

  const hoveredVisual = hoveredRegion ? regionVisuals.get(hoveredRegion.shortName) : null;

  return (
    <div className={`india-risk-map-shell ${className}`}>
      {/* 1. Sleek, Minimal Map Toolbar */}
      <div className="map-toolbar-row">
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <MapPinIcon size={16} style={{ color: '#38BDF8' }} />
          <div>
            <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--text-primary)' }}>
              Map of India &bull; Forecast Risk by State
            </div>
            <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
              {leadDay} day{leadDay === 1 ? '' : 's'} ahead
            </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
          <SegmentedControl
            options={MAP_LAYER_OPTIONS}
            value={mapLayer}
            onChange={setMapLayer}
          />

          {/* Minimal Zoom Stepper */}
          <div className="map-zoom-group">
            <button
              type="button"
              className="map-zoom-btn"
              onClick={handleZoomIn}
              title="Zoom In"
              aria-label="Zoom In"
            >
              +
            </button>
            <button
              type="button"
              className="map-zoom-btn"
              onClick={handleResetZoom}
              title="Reset Zoom"
              aria-label="Reset Zoom"
            >
              {Math.round(zoomLevel * 100)}%
            </button>
            <button
              type="button"
              className="map-zoom-btn"
              onClick={handleZoomOut}
              title="Zoom Out"
              aria-label="Zoom Out"
            >
              &minus;
            </button>
          </div>
        </div>
      </div>

      {/* 2. Interactive SVG Map Viewport */}
      <div className="map-interactive-viewport">
        {/* Subtle Coordinates Bar */}
        <div className="map-coordinates-bar">
          <span>Click any state to see its full forecast</span>
        </div>

        {/* Scalable Transform Wrapper */}
        <div
          className="map-svg-transform-container"
          style={{
            transform: `scale(${zoomLevel})`,
            transformOrigin: 'center center',
            transition: 'transform 180ms ease-out',
          }}
        >
          <svg
            viewBox="0 0 620 680"
            className="india-svg-element"
            role="img"
            aria-label="Recognizable meteorological map of India with regional bust risk boundaries"
          >
            {/* Memoized Static Backdrop */}
            <StaticMapBackdrop />

            {/* India's 29 real states/UTs - colored by chance of a major forecast error */}
            {INDIA_GEO_REGIONS.map((region) => {
              const isSelected = region.shortName === selectedRegionId || region.id === selectedRegionId;
              const isHovered = region.shortName === hoveredRegion?.shortName || region.id === hoveredRegion?.id;
              const visual = regionVisuals.get(region.shortName) || {
                fillColor: '#10B981',
                bustPercent: 1,
                isSevere: false,
                displayValue: '1%',
              };

              return (
                <g
                  key={region.id}
                  className={`region-feature-group ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectRegion(region.shortName)}
                  onMouseEnter={() => setHoveredRegion(region)}
                  onMouseLeave={() => setHoveredRegion(null)}
                  style={{ cursor: 'pointer' }}
                  role="button"
                  tabIndex={0}
                  aria-label={`${region.name}: ${visual.bustPercent}% chance of a major forecast error`}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      onSelectRegion(region.shortName);
                    }
                  }}
                >
                  {/* Base Geographic Boundary Path */}
                  <path
                    d={region.svgPath}
                    fill={visual.fillColor}
                    fillOpacity={isSelected ? 0.55 : isHovered ? 0.45 : 0.28}
                    stroke={isSelected ? '#38BDF8' : isHovered ? '#CBD5E1' : 'rgba(255, 255, 255, 0.24)'}
                    strokeWidth={isSelected ? '2.5' : isHovered ? '2' : '1.2'}
                    strokeLinejoin="round"
                    strokeLinecap="round"
                    style={{ transition: 'all 120ms ease-out' }}
                  />

                  {/* Accessibility Hatch for Severe Risk Zones (Non-color reliant) */}
                  {visual.isSevere && mapLayer === 'risk' && (
                    <path
                      d={region.svgPath}
                      fill="url(#severe-bust-hatch)"
                      pointerEvents="none"
                    />
                  )}

                  {/* Selected State Marker */}
                  {isSelected && (
                    <circle
                      cx={region.labelPoint.x}
                      cy={region.labelPoint.y - 14}
                      r="5"
                      fill="#38BDF8"
                      stroke="#FFFFFF"
                      strokeWidth="1.5"
                    />
                  )}

                  {/* With 29 states on screen, showing every full name/value
                      permanently would be unreadable clutter - only a short
                      2-letter code is always shown. The full name and value
                      appear on hover (tooltip below) and for the selected
                      state (sidebar panel), per the product's own "readable
                      map, details on demand" guidance. */}
                  <text
                    x={region.labelPoint.x}
                    y={region.labelPoint.y + 3}
                    textAnchor="middle"
                    fill={isSelected || isHovered ? '#F8FAFC' : 'rgba(248, 250, 252, 0.55)'}
                    fontSize={isSelected ? '10.5' : '8.5'}
                    fontWeight={isSelected ? '700' : '600'}
                    fontFamily="var(--font-mono)"
                    style={{
                      pointerEvents: 'none',
                      userSelect: 'none',
                      textShadow: '0 1px 3px rgba(0, 0, 0, 0.9)',
                    }}
                  >
                    {region.shortCode}
                  </text>

                  {isSelected && (
                    <text
                      x={region.labelPoint.x}
                      y={region.labelPoint.y + 16}
                      textAnchor="middle"
                      fill="#38BDF8"
                      fontSize="9.5"
                      fontWeight="700"
                      fontFamily="var(--font-mono)"
                      style={{
                        pointerEvents: 'none',
                        userSelect: 'none',
                        textShadow: '0 1px 3px rgba(0, 0, 0, 0.9)',
                      }}
                    >
                      {visual.displayValue}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* 7. Hover Tooltip (Concise, Clean Weather HUD) */}
        {hoveredRegion && hoveredVisual && (
          <div className="map-hover-tooltip" role="tooltip">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
              <span style={{ fontWeight: 700, color: '#38BDF8', fontSize: '12px' }}>
                {hoveredRegion.shortName}
              </span>
              <span className="badge badge-neutral" style={{ fontSize: '9px', padding: '1px 5px' }}>
                {leadDay} day{leadDay === 1 ? '' : 's'} ahead
              </span>
            </div>

            <div style={{ display: 'flex', alignItems: 'baseline', gap: '8px', marginTop: '2px' }}>
              <div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Chance of major error: </span>
                <strong style={{ color: '#F87171', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                  {hoveredVisual.bustPercent}%
                </strong>
              </div>
              <div>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>Reliability: </span>
                <strong style={{ color: '#34D399', fontSize: '12px', fontFamily: 'var(--font-mono)' }}>
                  {hoveredVisual.confidencePercent}%
                </strong>
              </div>
            </div>
          </div>
        )}

        {/* 8. Docked Map Legend */}
        <div className="map-legend-dock">
          <MapLegend mode={mapLayer} />
        </div>
      </div>
    </div>
  );
}

export const IndiaRiskMap = React.memo(IndiaRiskMapComponent);
