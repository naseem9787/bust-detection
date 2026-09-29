"""
Phase 5 - Stage 12/13: historical event record schema + severity score.

`event_id` is a deterministic string derived from the record's own natural
key (init_time, lead_day, latitude, longitude) - stable across rebuilds,
never a random UUID, so the same historical forecast/observation pair
always resolves to the same event_id.

Severity score (documented formula, not a subjective label):

    rain_severity = category_gap / 5          (IMD category gap, 0-5 steps, /5 -> [0,1])
    temp_severity = |temp error C| / 3.0       (normalized by the bust hard-threshold, 3 degC)
    severity_score = max(rain_severity, temp_severity)

A severity_score >= 1.0 means at least one variable crossed its bust
threshold (a category gap of 5, i.e. no_rain<->extremely_heavy, or a temp
error of >=3degC); values below 1.0 are sub-threshold but still show how
close a case came. This is a simple, fully transparent MAX of two
already-defined, already-documented quantities (IMD category bins,
config.TEMP_BUST_ABS_ERROR_K) - nothing new is invented.
"""
from __future__ import annotations

import hashlib

import pandas as pd

from ..label_busts import _rain_category
from .. import config


def make_event_id(init_time: pd.Timestamp, lead_day: int, latitude: float, longitude: float) -> str:
    key = f"{pd.Timestamp(init_time).isoformat()}|{lead_day}|{latitude:.4f}|{longitude:.4f}"
    return hashlib.sha1(key.encode()).hexdigest()[:16]


def compute_severity(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    fcst_cat = _rain_category(df.fcst_precip_mm).cat.codes.astype(int)
    obs_cat = _rain_category(df.obs_precip_mm).cat.codes.astype(int)
    category_gap = (fcst_cat - obs_cat).abs()
    df["rain_severity"] = category_gap / (len(config.IMD_RAIN_LABELS) - 1)
    df["temp_severity"] = df["error_temp_c"].abs() / config.TEMP_BUST_ABS_ERROR_K
    df["severity_score"] = df[["rain_severity", "temp_severity"]].max(axis=1)
    df["event_id"] = [
        make_event_id(it, ld, lat, lon)
        for it, ld, lat, lon in zip(df.init_time, df.lead_day, df.latitude, df.longitude)
    ]
    return df


EVENT_RECORD_FIELDS = [
    "event_id", "init_time", "valid_time", "region_v2", "latitude", "longitude", "lead_day",
    "fcst_precip_mm", "fcst_temp_c", "fcst_mslp_hpa", "wind_speed_10m",
    "obs_precip_mm", "obs_temp_c",
    "error_precip_mm", "error_temp_c", "abs_error_precip_mm", "abs_error_temp_c",
    "bust_precip_categorical", "bust_temp_hard",
    "rain_severity", "temp_severity", "severity_score",
]


def to_event_record(row: pd.Series) -> dict:
    record = {f: row[f] for f in EVENT_RECORD_FIELDS if f in row}
    record["source"] = {
        "forecast_source": "ECMWF HRES (deterministic)",
        "truth_source": "ERA5 reanalysis",
        "wind_source": "ECMWF HRES 10m_wind_speed (Phase 3)",
    }
    return record
