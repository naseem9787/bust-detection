/**
 * ForecastErrorChart Component
 * Real lead-time trend for the selected state: how the chance of a major
 * forecast error changes from Day 1 through Day 10. Driven entirely by
 * `errorProgression` (from GET /api/v1/regions/{id}, itself computed from
 * the real 2018-2021 ECMWF HRES / ERA5 archive) - never a hardcoded curve.
 */

import React, { useMemo } from 'react';
import { ChartContainer } from '../ui/ChartContainer.jsx';

const CHART_LEGEND = [
  { label: 'Chance of Major Forecast Error', color: '#EF4444' },
];

const VIEWBOX_W = 900;
const VIEWBOX_H = 120;
const X_LEFT = 50;
const X_RIGHT = 860;
const Y_TOP = 12;
const Y_BOTTOM = 108;

function ForecastErrorChartComponent({
  regionName = '',
  leadDay = 5,
  errorProgression = [],
  className = '',
}) {
  const xPosActive = X_LEFT + (leadDay - 1) * ((X_RIGHT - X_LEFT) / 9);

  const { points, maxRate } = useMemo(() => {
    if (!errorProgression || errorProgression.length === 0) {
      return { points: '', maxRate: 0 };
    }
    const byLead = new Map(errorProgression.map((r) => [r.leadDay, r.bustRate]));
    const rates = Array.from({ length: 10 }, (_, i) => byLead.get(i + 1) ?? null);
    const known = rates.filter((r) => r !== null);
    const max = Math.max(...known, 0.1); // never divide by zero; keeps a flat real-0 line visible
    const coords = rates
      .map((rate, i) => {
        if (rate === null) return null;
        const x = X_LEFT + i * ((X_RIGHT - X_LEFT) / 9);
        const y = Y_BOTTOM - (rate / max) * (Y_BOTTOM - Y_TOP);
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .filter(Boolean);
    return { points: coords.join(' '), maxRate: max };
  }, [errorProgression]);

  const hasData = points.length > 0;

  return (
    <ChartContainer
      title={`How Forecast Risk Changes with Lead Time • ${regionName}`}
      subtitle="Real historical bust rate by lead day (2018–2021 ECMWF HRES / ERA5 archive)"
      unit="% chance of error"
      legend={CHART_LEGEND}
      className={className}
    >
      <svg className="curve-svg" viewBox={`0 0 ${VIEWBOX_W} ${VIEWBOX_H}`} preserveAspectRatio="none" role="img" aria-label="Real chance of forecast error by lead day">
        {hasData ? (
          <>
            <text x={X_RIGHT + 5} y={Y_TOP + 4} fill="rgba(255, 255, 255, 0.4)" fontSize="9" fontFamily="var(--font-mono)">
              {maxRate.toFixed(1)}%
            </text>
            <polyline fill="none" stroke="#EF4444" strokeWidth="2.5" points={points} />
          </>
        ) : (
          <text x={VIEWBOX_W / 2} y={VIEWBOX_H / 2} textAnchor="middle" fill="var(--text-muted)" fontSize="11">
            No historical data available for this state/lead day yet
          </text>
        )}

        {/* Active Lead Day Marker */}
        <line x1={xPosActive} y1="0" x2={xPosActive} y2={VIEWBOX_H} stroke="#38BDF8" strokeWidth="1.75" strokeDasharray="3 3" />
        <circle cx={xPosActive} cy={VIEWBOX_H / 2} r="4.5" fill="#38BDF8" stroke="var(--bg-canvas)" strokeWidth="1.5" />
        <text x={xPosActive} y={VIEWBOX_H - 6} textAnchor="middle" fill="#38BDF8" fontSize="10" fontWeight="600" fontFamily="var(--font-mono)">
          Day {leadDay}
        </text>
      </svg>
    </ChartContainer>
  );
}

export const ForecastErrorChart = React.memo(ForecastErrorChartComponent);
