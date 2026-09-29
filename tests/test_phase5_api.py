"""
Phase 5 - API endpoint tests for /analogs, /analog-summary,
/events/{event_id}, and the extended /explain.
"""
from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

from src.phase5.analogs import INDEX_DIR

INDEX_AVAILABLE = os.path.exists(os.path.join(INDEX_DIR, "reference.parquet"))
EVENT_INDEX_AVAILABLE = os.path.exists(os.path.join(INDEX_DIR, "event_index.parquet"))
pytestmark = pytest.mark.skipif(not INDEX_AVAILABLE, reason="analog index not built yet")


@pytest.fixture(scope="module")
def client():
    from src.production.api import app

    with TestClient(app) as c:
        yield c


def test_analogs_valid_request(client):
    r = client.get(
        "/analogs",
        params={
            "init_time": "2021-07-20", "lead_day": 5, "latitude": 22.5, "longitude": 81.0,
            "forecast_precip_mm": 8.0, "forecast_temp_c": 27.0, "forecast_mslp_hpa": 1005.0,
            "k": 5,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "no_reliable_analogs")
    assert body["spatial_constraint"] == "same_region"


def test_analogs_invalid_lead_day(client):
    r = client.get(
        "/analogs",
        params={"init_time": "2021-07-20", "lead_day": 20, "latitude": 22.5, "longitude": 81.0},
    )
    assert r.status_code == 422


def test_analogs_invalid_coordinates(client):
    r = client.get(
        "/analogs",
        params={"init_time": "2021-07-20", "lead_day": 5, "latitude": 999.0, "longitude": 81.0},
    )
    assert r.status_code == 422


def test_analogs_outside_domain_region(client):
    r = client.get(
        "/analogs",
        params={"init_time": "2021-07-20", "lead_day": 5, "latitude": 0.0, "longitude": 65.0},
    )
    assert r.status_code == 422


def test_analogs_no_reliable_analogs_for_extreme_forecast(client):
    """An extreme, unrealistic forecast value should trigger the quality-
    control path rather than force a result."""
    r = client.get(
        "/analogs",
        params={
            "init_time": "2021-07-20", "lead_day": 5, "latitude": 22.5, "longitude": 81.0,
            "forecast_precip_mm": 5000.0, "forecast_temp_c": 90.0, "forecast_mslp_hpa": 1005.0,
        },
    )
    assert r.status_code == 200
    assert r.json()["status"] == "no_reliable_analogs"


def test_analog_summary_valid_request(client):
    r = client.get(
        "/analog-summary",
        params={
            "init_time": "2021-07-20", "lead_day": 5, "latitude": 22.5, "longitude": 81.0,
            "forecast_precip_mm": 8.0, "forecast_temp_c": 27.0, "forecast_mslp_hpa": 1005.0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] in ("ok", "low_analog_confidence", "no_reliable_analogs")
    if body["status"] == "ok":
        assert 0 <= body["historical_rain_bust_rate"] <= 1


@pytest.mark.skipif(not EVENT_INDEX_AVAILABLE, reason="event index not built yet")
def test_get_event_unknown_id_returns_404(client):
    r = client.get("/events/not_a_real_event_id")
    assert r.status_code == 404


@pytest.mark.skipif(not EVENT_INDEX_AVAILABLE, reason="event index not built yet")
def test_get_event_known_id_returns_record(client):
    import pandas as pd

    events = pd.read_parquet(os.path.join(INDEX_DIR, "event_index.parquet"))
    known_id = events.iloc[0].event_id
    r = client.get(f"/events/{known_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["event_id"] == known_id
    assert "severity_score" in body
    assert "source" in body


def test_explain_separates_model_and_historical_evidence(client):
    r = client.get(
        "/explain",
        params={
            "variable": "rain", "init_time": "2021-08-01", "lead_day": 9,
            "latitude": 24.0, "longitude": 85.5,
            "forecast_precip_mm": 92.8, "forecast_temp_c": 26.1, "forecast_mslp_hpa": 1001.0,
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert "model_evidence" in body
    assert "historical_analogs" in body
    assert "top_features" in body["model_evidence"]
    assert "framing" in body["historical_analogs"]
    assert "not proof" in body["historical_analogs"]["framing"] or "evidence" in body["historical_analogs"]["framing"]


def test_explain_historical_analogs_never_labeled_as_cause(client):
    r = client.get(
        "/explain",
        params={
            "variable": "rain", "init_time": "2021-07-20", "lead_day": 5,
            "latitude": 22.5, "longitude": 81.0,
            "forecast_precip_mm": 8.0, "forecast_temp_c": 27.0, "forecast_mslp_hpa": 1005.0,
        },
    )
    body = r.json()
    framing = body["historical_analogs"]["framing"].lower()
    assert "cause" not in framing
    # the framing SHOULD say similarity does not guarantee an outcome (a
    # negated claim, per Stage 21) - what must never appear is a positive
    # causal/certainty claim
    for forbidden in ["this proves", "will happen", "guaranteed to", "definitely"]:
        assert forbidden not in framing
