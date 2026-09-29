"""
Phase 4 - inference engine tests: calibration behavior, output schema
bounds, and reproducibility.
"""
from __future__ import annotations

import pytest

from src.production.inference import ProductionInferenceEngine


@pytest.fixture(scope="module")
def engine():
    return ProductionInferenceEngine()


SAMPLE_INPUT = dict(
    init_time="2021-07-20", lead_day=5, latitude=22.5, longitude=81.0,
    forecast_precip_mm=45.2, forecast_temp_c=28.1, forecast_mslp_hpa=1003.4,
    forecast_wind_speed_10m=4.5,
)


def test_predict_returns_both_variables_when_wind_supplied(engine):
    result = engine.predict(**SAMPLE_INPUT)
    assert result["rain_bust_probability"] is not None
    assert result["temperature_bust_probability"] is not None


def test_predict_skips_temperature_when_wind_not_supplied(engine):
    kwargs = dict(SAMPLE_INPUT)
    kwargs.pop("forecast_wind_speed_10m")
    result = engine.predict(**kwargs)
    assert result["rain_bust_probability"] is not None
    assert result["temperature_bust_probability"] is None


def test_probabilities_are_in_unit_interval(engine):
    result = engine.predict(**SAMPLE_INPUT)
    for key in ("rain_bust_probability", "temperature_bust_probability"):
        p = result[key]
        assert 0.0 <= p["raw"] <= 1.0
        assert 0.0 <= p["calibrated"] <= 1.0
        assert 0.0 <= p["confidence"] <= 1.0
        assert abs(p["confidence"] - (1.0 - p["calibrated"])) < 1e-9


def test_raw_probability_is_never_silently_overwritten(engine):
    """rain_v1's validated decision is 'raw preserved' (calibration didn't
    help) - raw and calibrated must be IDENTICAL for rain. temperature_v1's
    decision is isotonic - raw and calibrated must DIFFER (in general) for
    temperature, proving the calibrator actually ran rather than being a
    silent no-op."""
    result = engine.predict(**SAMPLE_INPUT)
    rain = result["rain_bust_probability"]
    assert rain["raw"] == rain["calibrated"], "rain_v1's validated decision was 'raw preserved'"

    temp = result["temperature_bust_probability"]
    assert temp["raw"] != temp["calibrated"], "temperature_v1's validated decision was 'isotonic'"


def test_reproducibility_same_input_same_output(engine):
    r1 = engine.predict(**SAMPLE_INPUT)
    r2 = engine.predict(**SAMPLE_INPUT)
    assert r1["rain_bust_probability"] == r2["rain_bust_probability"]
    assert r1["temperature_bust_probability"] == r2["temperature_bust_probability"]
    assert r1["region"] == r2["region"]


def test_reproducibility_across_fresh_engine_instances():
    """A fresh process/engine instance loading the same artifacts must
    produce the same result - proves no hidden notebook/global state."""
    e1 = ProductionInferenceEngine()
    e2 = ProductionInferenceEngine()
    r1 = e1.predict(**SAMPLE_INPUT)
    r2 = e2.predict(**SAMPLE_INPUT)
    assert r1["rain_bust_probability"] == r2["rain_bust_probability"]


def test_risk_level_is_consistent_with_thresholds(engine):
    from src.production.thresholds import DEFAULT_THRESHOLDS

    result = engine.predict(**SAMPLE_INPUT)
    p = result["rain_bust_probability"]["calibrated"]
    level = result["rain_bust_probability"]["risk_level"]
    if p >= DEFAULT_THRESHOLDS["high"]:
        assert level == "high"
    elif p >= DEFAULT_THRESHOLDS["moderate"]:
        assert level == "moderate"
    else:
        assert level == "low"


def test_model_version_and_calibration_version_present(engine):
    result = engine.predict(**SAMPLE_INPUT)
    assert result["model_version"]
    assert result["feature_version"]
    assert result["calibration_version"]
    assert "rain=" in result["calibration_version"]
    assert "temp=" in result["calibration_version"]
