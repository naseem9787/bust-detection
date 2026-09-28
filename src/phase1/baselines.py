"""
Phase 1 - baseline bust-probability predictors. All are simple, non-leaky
historical-frequency lookups: fit (i.e. compute a group-mean bust rate) on
the TRAIN split (2018-2020) only, then applied unchanged to both splits.
No model training, no deep learning, no per-row information that wouldn't
have been available before knowing the outcome.

Baseline A - historical climatology: P(bust | region, lead_day, month)
Baseline B - lead-time-only:          P(bust | lead_day)
Baseline C - ensemble spread:         NOT AVAILABLE in Phase 0/1's data.
  The forecast source is ECMWF HRES, a single deterministic run (see
  src/config.py FORECAST_STORE) - there are no ensemble members to compute
  a spread from. Fabricating a spread proxy would misrepresent what the
  data supports, so this baseline is left undone and documented here
  instead. To add it: point src/fetch_data.py-style fetching at the
  WeatherBench2 `ifs_ens` zarr store (real ensemble forecasts, confirmed to
  exist in the bucket - see the project's data-source notes) and derive
  per-grid-cell/lead spread as a feature.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

BASELINE_C_STATUS = (
    "NOT AVAILABLE - Phase 0/1 forecast source (ECMWF HRES) is a single "
    "deterministic run with no ensemble members, so no spread can be "
    "computed without fabricating one. Add once ensemble data (e.g. "
    "WeatherBench2's `ifs_ens` store) is ingested."
)


@dataclass
class FittedBaseline:
    name: str
    group_cols: list[str]
    lookup: pd.Series  # indexed by group_cols -> P(bust)
    global_fallback: float  # used for any (test) group unseen in training


def fit_climatology(train: pd.DataFrame, group_cols: list[str], name: str) -> FittedBaseline:
    lookup = train.groupby(group_cols, observed=True).bust_any.mean()
    return FittedBaseline(
        name=name,
        group_cols=group_cols,
        lookup=lookup,
        global_fallback=float(train.bust_any.mean()),
    )


def predict(baseline: FittedBaseline, df: pd.DataFrame) -> np.ndarray:
    if len(baseline.group_cols) == 1:
        keys = df[baseline.group_cols[0]]
    else:
        keys = pd.MultiIndex.from_frame(df[baseline.group_cols])
    pred = keys.map(baseline.lookup)
    pred = pd.Series(pred, index=df.index, dtype=float).fillna(baseline.global_fallback)
    return pred.to_numpy()


def fit_all_baselines(train: pd.DataFrame) -> dict[str, FittedBaseline]:
    """Baseline A and B only - see BASELINE_C_STATUS for why C is absent."""
    return {
        "historical_climatology": fit_climatology(
            train, ["region", "lead_day", "month"], "Historical baseline (region x lead x month)"
        ),
        "lead_time_only": fit_climatology(train, ["lead_day"], "Lead-time-only baseline"),
    }


def fit_global_reference(train: pd.DataFrame) -> float:
    """Constant train-period overall bust rate - the reference forecast used
    for Brier Skill Score (BSS = 1 - BS_model / BS_reference)."""
    return float(train.bust_any.mean())
