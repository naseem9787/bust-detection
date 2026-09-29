"""
Phase 4 - FastAPI endpoint tests.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.production.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["models_loaded"]) == {"rain_v1", "temperature_v1"}


def test_metadata(client):
    r = client.get("/metadata")
    assert r.status_code == 200
    body = r.json()
    assert len(body["models"]) == 2
    assert body["supported_lead_days"] == list(range(1, 11))
    assert "risk_thresholds" in body
    assert "not a weather forecast" not in body["scientific_framing"]  # sanity: field is populated
    assert "probability" in body["scientific_framing"].lower()


def test_metadata_does_not_overclaim(client):
    body = client.get("/metadata").json()
    framing = body["scientific_framing"].lower()
    for forbidden in ["100% accurate", "guaranteed", "perfect confidence", "solves weather"]:
        assert forbidden not in framing


def test_predict_valid_request(client):
    r = client.post(
        "/predict",
        json={
            "init_time": "2021-07-20T00:00:00", "lead_day": 5, "latitude": 22.5, "longitude": 81.0,
            "forecast_precip_mm": 45.2, "forecast_temp_c": 28.1, "forecast_mslp_hpa": 1003.4,
            "forecast_wind_speed_10m": 4.5,
        },
    )
    assert r.status_code == 200
    pred = r.json()["prediction"]
    assert pred["region"] == "Madhya Pradesh"
    assert 0 <= pred["rain_bust_probability"]["calibrated"] <= 1


def test_predict_invalid_lead_day(client):
    r = client.post(
        "/predict",
        json={
            "init_time": "2021-07-20", "lead_day": 15, "latitude": 22.5, "longitude": 81.0,
            "forecast_precip_mm": 1.0, "forecast_temp_c": 25.0, "forecast_mslp_hpa": 1010.0,
        },
    )
    assert r.status_code == 422


def test_predict_invalid_latitude(client):
    r = client.post(
        "/predict",
        json={
            "init_time": "2021-07-20", "lead_day": 5, "latitude": 999.0, "longitude": 81.0,
            "forecast_precip_mm": 1.0, "forecast_temp_c": 25.0, "forecast_mslp_hpa": 1010.0,
        },
    )
    assert r.status_code == 422


def test_predict_negative_precip_rejected(client):
    r = client.post(
        "/predict",
        json={
            "init_time": "2021-07-20", "lead_day": 5, "latitude": 22.5, "longitude": 81.0,
            "forecast_precip_mm": -5.0, "forecast_temp_c": 25.0, "forecast_mslp_hpa": 1010.0,
        },
    )
    assert r.status_code == 422


def test_predict_outside_domain_coordinates(client):
    r = client.post(
        "/predict",
        json={
            "init_time": "2021-07-20", "lead_day": 5, "latitude": 0.0, "longitude": 65.0,
            "forecast_precip_mm": 1.0, "forecast_temp_c": 25.0, "forecast_mslp_hpa": 1010.0,
        },
    )
    assert r.status_code == 422
    assert r.json()["error"] == "outside_domain"


def test_regions_endpoint_returns_29_regions(client):
    r = client.get("/regions")
    assert r.status_code == 200
    assert len(r.json()) == 29


def test_predictions_endpoint_structured_error_when_no_batch_run(client, tmp_path, monkeypatch):
    import src.production.api as api_module

    monkeypatch.setattr(api_module, "PREDICTIONS_DIR", str(tmp_path / "nonexistent"))
    r = client.get("/predictions")
    assert r.status_code == 404
    assert r.json()["error"] == "no_persisted_predictions"


def test_timeseries_missing_data_returns_structured_error(client):
    r = client.get(
        "/timeseries",
        params={"valid_time": "1900-01-01T00:00:00", "latitude": 22.5, "longitude": 81.0},
    )
    assert r.status_code == 404
    assert "error" in r.json()


def test_explain_rain(client):
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
    # Phase 5 restructured /explain into separate model/historical evidence
    # (see docs/historical_analogs.md) - updated assertion accordingly
    assert len(body["model_evidence"]["top_features"]) > 0
    assert len(body["model_evidence"]["human_readable_reasons"]) > 0
    assert "historical_analogs" in body


def test_explain_temperature_requires_wind(client):
    r = client.get(
        "/explain",
        params={
            "variable": "temperature", "init_time": "2021-08-01", "lead_day": 9,
            "latitude": 24.0, "longitude": 85.5,
            "forecast_precip_mm": 1.0, "forecast_temp_c": 26.1, "forecast_mslp_hpa": 1001.0,
        },
    )
    assert r.status_code == 422


def test_unknown_model_via_registry_returns_404_shape():
    from src.production.registry import UnknownModelError, load_entry

    with pytest.raises(UnknownModelError):
        load_entry("not_a_real_model")
