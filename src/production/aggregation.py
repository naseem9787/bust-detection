"""
Phase 4 - region/state aggregation utilities. Exposes multiple statistics
rather than picking one "the truth" aggregation, per instructions - the
frontend decides how to display these.
"""
from __future__ import annotations

import pandas as pd

from .thresholds import DEFAULT_THRESHOLDS


def aggregate_region(
    grid_df: pd.DataFrame,
    probability_col: str,
    confidence_col: str,
    forecast_value_col: str,
    threshold: float = DEFAULT_THRESHOLDS["high"],
) -> pd.DataFrame:
    """grid_df: one row per grid cell, must include 'region', 'lead_day',
    'valid_time', and the named probability/confidence/forecast columns.
    Returns one row per (region, lead_day, valid_time) with several named
    aggregation statistics - see docs/api_contract.md for field meanings."""
    group_cols = ["region", "lead_day", "valid_time"]

    def _agg(g: pd.DataFrame) -> pd.Series:
        p = g[probability_col]
        return pd.Series(
            {
                "n_grid_cells": len(g),
                "region_max_probability": float(p.max()),
                "region_mean_probability": float(p.mean()),
                "region_high_risk_fraction": float((p >= threshold).mean()),
                "high_risk_threshold_used": threshold,
                "representative_forecast_value": float(g[forecast_value_col].median()),
                "representative_confidence": float(g[confidence_col].median()),
            }
        )

    return grid_df.groupby(group_cols, observed=True).apply(_agg, include_groups=False).reset_index()
