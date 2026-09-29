"""
Phase 5 - Stage 16: analog summary statistics for a query result. Only
computes metrics when there are enough samples to be meaningful - flags
`low_analog_confidence` rather than fabricating certainty from too few or
too-distant analogs.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .analogs import AnalogQueryResult

MIN_SAMPLES_FOR_RATE_METRICS = 5


@dataclass
class AnalogSummary:
    status: str
    n_analogs: int
    mean_distance: float | None
    median_distance: float | None
    historical_rain_bust_rate: float | None
    historical_temp_bust_rate: float | None
    mean_abs_precip_error_mm: float | None
    median_abs_precip_error_mm: float | None
    mean_abs_temp_error_c: float | None
    median_abs_temp_error_c: float | None
    precip_outcome_range_mm: tuple[float, float] | None
    temp_outcome_range_c: tuple[float, float] | None
    fraction_heavy_rain_miss: float | None
    fraction_temperature_bust: float | None
    warning: str | None


def summarize(result: AnalogQueryResult) -> AnalogSummary:
    if result.status != "ok" or len(result.analogs) < MIN_SAMPLES_FOR_RATE_METRICS:
        return AnalogSummary(
            status="low_analog_confidence" if result.status == "ok" else result.status,
            n_analogs=len(result.analogs),
            mean_distance=None, median_distance=None,
            historical_rain_bust_rate=None, historical_temp_bust_rate=None,
            mean_abs_precip_error_mm=None, median_abs_precip_error_mm=None,
            mean_abs_temp_error_c=None, median_abs_temp_error_c=None,
            precip_outcome_range_mm=None, temp_outcome_range_c=None,
            fraction_heavy_rain_miss=None, fraction_temperature_bust=None,
            warning=result.warning or f"fewer than {MIN_SAMPLES_FOR_RATE_METRICS} analogs available",
        )

    analogs = result.analogs
    distances = np.array([a.distance for a in analogs])
    precip_abs_err = np.array([abs(a.precip_error_mm) for a in analogs])
    temp_abs_err = np.array([abs(a.temp_error_c) for a in analogs])
    actual_precip = np.array([a.actual_precip_mm for a in analogs])
    actual_temp = np.array([a.actual_temp_c for a in analogs])
    rain_bust = np.array([a.rain_bust for a in analogs])
    temp_bust = np.array([a.temperature_bust for a in analogs])

    return AnalogSummary(
        status="ok",
        n_analogs=len(analogs),
        mean_distance=float(distances.mean()),
        median_distance=float(np.median(distances)),
        historical_rain_bust_rate=float(rain_bust.mean()),
        historical_temp_bust_rate=float(temp_bust.mean()),
        mean_abs_precip_error_mm=float(precip_abs_err.mean()),
        median_abs_precip_error_mm=float(np.median(precip_abs_err)),
        mean_abs_temp_error_c=float(temp_abs_err.mean()),
        median_abs_temp_error_c=float(np.median(temp_abs_err)),
        precip_outcome_range_mm=(float(actual_precip.min()), float(actual_precip.max())),
        temp_outcome_range_c=(float(actual_temp.min()), float(actual_temp.max())),
        fraction_heavy_rain_miss=float(rain_bust.mean()),
        fraction_temperature_bust=float(temp_bust.mean()),
        warning=None,
    )
