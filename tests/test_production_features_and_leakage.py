"""
Phase 4 - feature validation, spatial/region correctness, and leakage
regression tests for the production feature builder.
"""
from __future__ import annotations

import pandas as pd
import pytest

from src.production import features as feat
from src.production.registry import EXPERIMENTAL_FEATURE_NAMES, load_entry

FUTURE_OBSERVATION_OR_LABEL_COLUMNS = {
    "obs_precip_mm", "obs_temp_c", "obs_mslp_hpa",
    "error_precip_mm", "error_temp_c", "error_mslp_hpa",
    "abs_error_precip_mm", "abs_error_temp_c", "abs_error_mslp_hpa",
    "bust_any", "bust_precip", "bust_temp",
    "bust_precip_categorical", "bust_temp_hard",
}


def _sample_row(**overrides):
    kwargs = dict(
        init_time=pd.Timestamp("2021-07-20"),
        lead_day=5,
        latitude=22.5,
        longitude=81.0,
        forecast_precip_mm=45.2,
        forecast_temp_c=28.1,
        forecast_mslp_hpa=1003.4,
    )
    kwargs.update(overrides)
    return feat.build_feature_row(**kwargs)


def test_build_feature_row_contains_no_future_observation_or_label_columns():
    built = _sample_row()
    assert not (set(built["features"]) & FUTURE_OBSERVATION_OR_LABEL_COLUMNS)


def test_build_feature_row_contains_no_experimental_features_by_default():
    built = _sample_row()
    assert not (set(built["features"]) & EXPERIMENTAL_FEATURE_NAMES)


def test_requesting_experimental_features_raises():
    from src.production.registry import ExperimentalFeatureRequestedError

    with pytest.raises(ExperimentalFeatureRequestedError):
        feat.build_feature_row(
            init_time=pd.Timestamp("2021-07-20"), lead_day=5, latitude=22.5, longitude=81.0,
            forecast_precip_mm=1.0, forecast_temp_c=25.0, forecast_mslp_hpa=1010.0,
            requested_experimental_features={"ensemble_std_precip"},
        )


def test_lead_day_range_enforced_by_registry_feature_order_and_schema():
    from src.production.schemas import PredictionRequest

    with pytest.raises(Exception):
        PredictionRequest(
            init_time="2021-07-20", lead_day=11, latitude=22.5, longitude=81.0,
            forecast_precip_mm=1.0, forecast_temp_c=25.0, forecast_mslp_hpa=1010.0,
        )
    with pytest.raises(Exception):
        PredictionRequest(
            init_time="2021-07-20", lead_day=0, latitude=22.5, longitude=81.0,
            forecast_precip_mm=1.0, forecast_temp_c=25.0, forecast_mslp_hpa=1010.0,
        )


def test_validate_feature_row_catches_missing_feature():
    from src.production.features import FeatureValidationError, validate_feature_row

    row = {"a": 1.0, "b": 2.0}
    with pytest.raises(FeatureValidationError):
        validate_feature_row(row, ["a", "b", "c"])


def test_validate_feature_row_catches_non_numeric():
    from src.production.features import FeatureValidationError, validate_feature_row

    row = {"a": "not-a-number", "region_v2": "Gujarat"}
    with pytest.raises(FeatureValidationError):
        validate_feature_row(row, ["a", "region_v2"])


def test_validate_feature_row_allows_correct_row():
    from src.production.features import validate_feature_row

    row = {"a": 1.0, "region_v2": "Gujarat"}
    validate_feature_row(row, ["a", "region_v2"])  # no raise


def test_region_lookup_matches_phase2_region_assignment():
    """Cross-check against Phase 2's own known assignment for a real city."""
    region, in_domain = feat.lookup_region(19.0760, 72.8777)  # Mumbai
    assert in_domain
    assert region == "Maharashtra"


def test_region_lookup_flags_ocean_point_as_outside_domain():
    _, in_domain = feat.lookup_region(0.0, 65.0)  # deep Arabian Sea
    assert not in_domain


def test_outside_domain_point_raises_in_build_feature_row():
    from src.production.features import UnknownRegionError

    with pytest.raises(UnknownRegionError):
        feat.build_feature_row(
            init_time=pd.Timestamp("2021-07-20"), lead_day=5, latitude=0.0, longitude=65.0,
            forecast_precip_mm=1.0, forecast_temp_c=25.0, forecast_mslp_hpa=1010.0,
        )


def test_region_grid_has_no_duplicate_grid_cells():
    grid = feat._load_region_grid()
    assert not grid.duplicated(["latitude", "longitude"]).any()


def test_region_categories_match_training_categories_exactly():
    """If this ever drifts from what the persisted models were trained on,
    LightGBM prediction would raise (or silently misbehave) - this is a
    standing regression guard."""
    cats = feat.region_categories().categories.tolist()
    entry = load_entry("rain_v1")
    # region_v2 must be one of the model's own features and its categorical
    # levels must all be real region names, never the "Outside India domain" label
    assert "region_v2" in entry.feature_order
    assert "Outside India domain (ocean/neighboring country)" not in cats
    assert len(cats) == 29


def test_historical_feature_value_falls_back_for_unseen_key():
    value = feat.historical_feature_value("hist_bust_temp_hard_rate", "NoSuchRegion", 1, 6)
    assert value == feat._load_historical_lookups()["hist_bust_temp_hard_rate"][1]
