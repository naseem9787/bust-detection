"""
Phase 3 - shared base-table assembly, reused by year/lead/region robustness
stages that each need a DIFFERENT train/test year split (so historical
features must be refit per-experiment, never using a fixed 2018-2020/2021
split baked in). Reuses Phase 1/2's own functions unmodified - this just
skips Phase 2's fixed split so callers can supply their own.
"""
from __future__ import annotations

import pandas as pd

from ..phase1.dataset import build_phase1_dataset
from ..phase2.features import add_domain_mean_anomaly, add_forecast_jump, apply_historical_features, fit_historical_features
from ..phase2.geography import build_region_map


def build_full_domain_base() -> pd.DataFrame:
    """All 4 years (2018-2021), in-India-domain rows only, with domain-mean
    anomaly and forecast-jump already computed (both are split-independent -
    no leakage risk regardless of how train/test years are later chosen).
    Historical (train-only-fit) features are NOT yet applied - callers must
    call build_experiment_features() with their own train/test year split."""
    ds = build_phase1_dataset()
    df = ds.df

    region_map = build_region_map()[["latitude", "longitude", "region_v2", "in_india_domain"]]
    df = df.merge(region_map, on=["latitude", "longitude"], how="left")

    df = add_domain_mean_anomaly(df)
    df = add_forecast_jump(df)

    in_domain = df[df.in_india_domain].copy()
    in_domain["region_v2"] = in_domain["region_v2"].astype("category")
    return in_domain


def build_experiment_features(
    base_df: pd.DataFrame, train_years: list[int], test_year: int
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Historical features fit ONLY on `train_years` rows, applied to both
    the resulting train and test frames - a fresh, leakage-safe fit for
    THIS specific experiment's split (never reusing another split's fit)."""
    train = base_df[base_df.init_time.dt.year.isin(train_years)].copy()
    test = base_df[base_df.init_time.dt.year == test_year].copy()
    assert len(train) > 0 and len(test) > 0

    fitted = fit_historical_features(train)
    train = apply_historical_features(train, fitted)
    test = apply_historical_features(test, fitted)
    return train, test
