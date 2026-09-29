/**
 * ForecastErrorChart Component
 * Integrated lead-time error trend curve from Day 1 through Day 10 for the selected region.
 * Highlights the active lead time cursor and 90th percentile bust threshold.
 */

import React from 'react';
import { ChartContainer } from '../ui/ChartContainer.jsx';

const CHART_LEGEND = [
  { label: 'Forecast Bust Probability', color: '#EF4444' },
  { label: 'Rainfall Category Shift Risk', color: '#0284C7', dashed: true },
  { label: '90th Percentile Threshold', color: 'rgba(255, 255, 255, 0.4)', dashed: true },
];

function ForecastErrorChartComponent({
  regionName = 'West Coast',
  leadDay = 5,
  className = '',
}) {
  // Pre-calculated Day 1 to Day 10 progression points for the SVG viewBox (0 0 900 120)
  // Day 1 at x=50, Day 10 at x=860. Higher bust rate = lower y (higher on graph)
  const xPosActive = 50 + (leadDay - 1) * 90;

  return (
    <ChartContainer
      title={`Lead-Time Error Trend & Bust Trajectory &bull; ${regionName}`}
      subtitle="Evaluated across 240h medium-range forecast window (ECMWF HRES deterministic)"
      unit="% Risk / Error"
      legend={CHART_LEGEND}
      className={className}
    >
      <svg className="curve-svg" viewBox="0 0 900 120" preserveAspectRatio="none" role="img" aria-label="Error growth trajectory curve">
        {/* 90th Percentile Threshold Reference Line */}
        <line
          x1="50"
          y1="70"
          x2="860"
          y2="70"
          stroke="rgba(255, 255, 255, 0.35)"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
        <text x="865" y="74" fill="rgba(255, 255, 255, 0.4)" fontSize="9" fontFamily="var(--font-mono)">
          90th %ile
        </text>

        {/* Forecast Bust Probability Trajectory Curve (Red) */}
        <polyline
          fill="none"
          stroke="#EF4444"
          strokeWidth="2.5"
          points="
            50,92
            140,85
            230,78
            320,68
            410,54
            500,42
            590,32
            680,24
            770,18
            860,12
          "
        />

        {/* Rainfall Category Shift Curve (Blue) */}
        <polyline
          fill="none"
          stroke="#0284C7"
          strokeWidth="1.8"
          strokeDasharray="4 3"
          points="
            50,98
            140,93
            230,87
            320,81
            410,71
            500,60
            590,51
            680,43
            770,36
            860,29
          "
        />

        {/* Active Lead Day Marker (Cyan vertical rule and pinpoint) */}
        <line
          x1={xPosActive}
          y1="0"
          x2={xPosActive}
          y2="120"
          stroke="#38BDF8"
          strokeWidth="1.75"
          strokeDasharray="3 3"
        />
        <circle cx={xPosActive} cy="54" r="4.5" fill="#38BDF8" stroke="var(--bg-canvas)" strokeWidth="1.5" />
        <text
          x={xPosActive}
          y="112"
          textAnchor="middle"
          fill="#38BDF8"
          fontSize="10"
          fontWeight="600"
          fontFamily="var(--font-mono)"
        >
          Day {leadDay}
        </text>
      </svg>
    </ChartContainer>
  );
}

export const ForecastErrorChart = React.memo(ForecastErrorChartComponent);
