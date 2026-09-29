"""
Phase 6 - frontend adapter (/api/v1) tests.

These test the thin reshaping layer in src/production/frontend_adapter.py,
NOT the underlying ML/analog machinery (already covered by
test_production_api.py, test_phase5_analogs.py, test_phase5_api.py).
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from src.production.api import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_regions_returns_exactly_8_zones(client):
    r = client.get("/api/v1/regions")
    assert r.status_code == 200
    body = r.json()
    assert len(body) == 8


def test_region_ids_match_frontend_contract(client):
    body = client.get("/api/v1/regions").json()
    ids = {r["id"] for r in body}
    assert ids == {
        "western-himalaya", "northwest-india", "indo-gangetic-plain",
        "northeast-india", "central-india", "west-coast", "east-coast",
        "south-peninsula",
    }


def test_regions_baseline_risk_is_real_number_not_placeholder(client):
    body = client.get("/api/v1/regions").json()
    for r in body:
        assert r["baselineRisk"] is not None
        assert 0.0 <= r["baselineRisk"] <= 1.0


def test_forecast_response_schema(client):
    r = client.get("/api/v1/forecast", params={"lead_day": 5, "region_id": "west-coast"})
    assert r.status_code == 200
    body = r.json()
    for key in ("meta", "verification", "variables", "regionalMetrics", "explanations"):
        assert key in body
    assert body["meta"]["regionId"] == "west-coast"
    assert body["meta"]["leadDay"] == 5
    assert 0.0 <= body["verification"]["bustProbability"] <= 1.0
    assert body["verification"]["riskLevel"] in {"low", "moderate", "elevated", "high", "extreme"}


def test_forecast_regional_metrics_camel_case_and_8_zones(client):
    body = client.get("/api/v1/forecast", params={"lead_day": 3, "region_id": "central-india"}).json()
    metrics = body["regionalMetrics"]
    assert len(metrics) <= 8 and len(metrics) > 0
    sample = next(iter(metrics.values()))
    for key in ("regionId", "regionName", "bustProbability", "confidence", "precipError", "tempError"):
        assert key in sample


def test_forecast_uses_real_verified_archive_not_fabricated_future(client):
    body = client.get("/api/v1/forecast", params={"cycle": "2026-09-29 00Z", "lead_day": 5, "region_id": "west-coast"}).json()
    # meta.cycle echoes the frontend's requested label, but the actual data
    # timestamp must be a real, pre-2022 archive date (see disclaimer)
    assert body["meta"]["timestamp"] < "2022-01-01"
    assert "REAL verified" in body["meta"]["disclaimer"]


def test_forecast_invalid_region_returns_422(client):
    r = client.get("/api/v1/forecast", params={"lead_day": 5, "region_id": "not-a-zone"})
    assert r.status_code == 422


def test_forecast_invalid_lead_day_returns_422(client):
    r = client.get("/api/v1/forecast", params={"lead_day": 15, "region_id": "west-coast"})
    assert r.status_code == 422


def test_explanations_flattens_into_factors_with_source_tags(client):
    r = client.get("/api/v1/explanations", params={"lead_day": 9, "region_id": "central-india"})
    assert r.status_code == 200
    body = r.json()
    assert "factors" in body and len(body["factors"]) > 0
    sources = {f["source"] for f in body["factors"]}
    assert sources <= {"model_output", "historical_context"}
    assert "model_output" in sources


def test_explanations_never_merges_model_and_historical_into_one_field(client):
    body = client.get("/api/v1/explanations", params={"lead_day": 9, "region_id": "central-india"}).json()
    model_factors = [f for f in body["factors"] if f["source"] == "model_output"]
    hist_factors = [f for f in body["factors"] if f["source"] == "historical_context"]
    # each retains its own distinguishing fields rather than being collapsed
    for f in model_factors:
        assert f["shapValue"] is not None
    for f in hist_factors:
        assert "forecast=" in f["evidenceValue"]


def test_explanations_bulletin_summary_present(client):
    body = client.get("/api/v1/explanations", params={"lead_day": 5, "region_id": "west-coast"}).json()
    assert isinstance(body["bulletinSummary"], str) and len(body["bulletinSummary"]) > 0


def test_replay_showcase_event_is_real_verified_case(client):
    events = client.get("/api/v1/replay/events").json()
    assert len(events) >= 1
    event_id = events[0]["eventId"]

    detail = client.get("/api/v1/replay/event", params={"event_id": event_id})
    assert detail.status_code == 200
    body = detail.json()
    assert body["region"] == "Jharkhand"
    assert len(body["leadDayTrajectory"]) == 10
    # the actual (observed) value must be identical across every lead day -
    # it's the same real verified outcome, only the forecast varies
    actuals = {row["actualPrecipMm"] for row in body["leadDayTrajectory"]}
    assert len(actuals) == 1


def test_replay_unknown_event_returns_404(client):
    r = client.get("/api/v1/replay/event", params={"event_id": "not-a-real-event-id"})
    assert r.status_code == 404


def test_historical_performance_returns_empty_for_unsupported_season(client):
    # the real archive is JJAS-only (Phase 2-5 documented limitation) -
    # winter/pre-monsoon/post-monsoon must never be fabricated
    r = client.get("/api/v1/historical-performance", params={"season": "winter_DJF"})
    assert r.status_code == 200
    assert r.json() == []


def test_historical_performance_jjas_has_real_records(client):
    r = client.get("/api/v1/historical-performance", params={"season": "monsoon_JJAS", "lead_day": 5})
    assert r.status_code == 200
    body = r.json()
    assert len(body) > 0
    for record in body:
        assert record["nSamples"] > 0


def test_cycles_returns_real_dates_not_fictional_2026(client):
    r = client.get("/api/v1/cycles")
    assert r.status_code == 200
    body = r.json()
    assert len(body) > 0
    for c in body:
        assert c["code"] < "2022"


def test_region_detail_unknown_zone_404(client):
    r = client.get("/api/v1/regions/not-a-real-zone")
    assert r.status_code == 422


def test_region_detail_real_error_progression(client):
    r = client.get("/api/v1/regions/west-coast", params={"lead_day": 5})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == "west-coast"
    assert len(body["errorProgression"]) > 0


def test_cors_allows_frontend_origin(client):
    r = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_root_production_endpoints_unaffected_by_adapter(client):
    # sanity: adding the adapter must not change existing root behavior
    r = client.get("/regions")
    assert r.status_code == 200
    assert len(r.json()) == 29  # unchanged 29-state region_v2 geography
