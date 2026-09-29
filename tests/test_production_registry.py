"""
Phase 4 - registry/model-loading tests.
"""
from __future__ import annotations

import os

import lightgbm as lgb
import pytest

from src.production import registry


def test_production_models_are_exactly_rain_and_temperature():
    assert set(registry.PRODUCTION_MODELS) == {"rain_v1", "temperature_v1"}


def test_unknown_model_key_raises():
    with pytest.raises(registry.UnknownModelError):
        registry.load_entry("ensemble_v1_pilot")


def test_experimental_ensemble_model_is_not_a_valid_key():
    """The pilot ensemble model must never be loadable as a production model."""
    with pytest.raises(registry.UnknownModelError):
        registry.load_entry("rain_ensemble_pilot")


@pytest.mark.parametrize("model_key", list(registry.PRODUCTION_MODELS))
def test_model_artifact_exists_and_loads(model_key):
    entry = registry.load_entry(model_key)
    assert os.path.exists(entry.model_artifact_path)
    booster = lgb.Booster(model_file=entry.model_artifact_path)
    assert booster.num_feature() == len(entry.feature_order)


@pytest.mark.parametrize("model_key", list(registry.PRODUCTION_MODELS))
def test_registry_feature_order_matches_persisted_model_exactly(model_key):
    """This is the check build_registry.py itself performs at build time -
    re-verified here as a standing regression test."""
    entry = registry.load_entry(model_key)
    booster = lgb.Booster(model_file=entry.model_artifact_path)
    assert booster.feature_name() == entry.feature_order


@pytest.mark.parametrize("model_key", list(registry.PRODUCTION_MODELS))
def test_registry_status_is_production(model_key):
    assert registry.load_entry(model_key).status == "production"


def test_assert_no_experimental_features_passes_for_clean_set():
    registry.assert_no_experimental_features({"fcst_precip_mm", "lead_day", "region_v2"})  # no raise


def test_assert_no_experimental_features_blocks_ensemble_columns():
    with pytest.raises(registry.ExperimentalFeatureRequestedError):
        registry.assert_no_experimental_features({"fcst_precip_mm", "ensemble_std_precip"})


def test_wind_is_a_production_feature_not_experimental():
    """wind_speed_10m is validated production (Model 6), unlike the
    ensemble/humidity/geopotential pilot features - must not be blocked."""
    registry.assert_no_experimental_features({"wind_speed_10m"})  # no raise
    assert "wind_speed_10m" not in registry.EXPERIMENTAL_FEATURE_NAMES


def test_rain_v1_does_not_include_wind():
    """Wind was tested for rain (Phase 3 Model 6) and did not help - rain_v1
    must be the no-wind feature set."""
    entry = registry.load_entry("rain_v1")
    assert "wind_speed_10m" not in entry.feature_order


def test_temperature_v1_includes_wind():
    entry = registry.load_entry("temperature_v1")
    assert "wind_speed_10m" in entry.feature_order
