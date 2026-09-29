"""
Phase 5 - Stage 4/5/6/7/9/17: the analog search engine.

Distance metric
----------------
z-score each analog feature using TRAIN-period (2018-2020) reference
statistics (AnalogScaler, train-only-fit - same leakage-safety pattern as
every other statistic in this project), then Euclidean distance.

Why Euclidean, not cosine: cosine similarity on mean-centered/standardized
vectors is mathematically close to the Pearson correlation of the feature
PROFILE - it would call two forecasts "similar" if their standardized
features point the same direction even at very different absolute
magnitudes (e.g. a mild vs. an extreme rain forecast, both slightly above
their own normal). For a physical analog ("was this actual situation seen
before"), absolute closeness in the standardized feature space is what
matters, which is exactly what Euclidean distance measures. This was
empirically checked, not just asserted - see
outputs/phase5/distance_metric_comparison.csv (Euclidean and Manhattan
give near-identical retrospective AUC; cosine is measurably worse -
consistent with the reasoning above).

Similarity transform (for display only - ranking always uses distance):
    similarity = 1 / (1 + distance)
Bounded in (0, 1], monotonically decreasing in distance, no invented
percentage scale.

Leakage / self-exclusion / temporal correctness (Stage 3, 9)
--------------------------------------------------------------
The feature matrix used for SIMILARITY never includes obs_*/error_*/bust_*
columns - see ANALOG_FEATURE_COLS in feature_vector.py, all forecast-time-
only. Outcomes are looked up AFTER the k nearest neighbors are found, by
row position, never used to influence which neighbors are chosen.

Every query excludes:
  - the exact (init_time, lead_day, latitude, longitude) key of the case
    being evaluated (`exclude_key`), and
  - any candidate with init_time >= `as_of` (defaults to the query's own
    init_time) - so retrospective queries can only retrieve analogs that
    would genuinely have existed in the historical record at that time.

Quality control (Stage 17)
----------------------------
`max_distance` defaults to the reference database's own 90th-percentile
same-region nearest-neighbor distance (computed empirically, not an
arbitrary constant - see `_default_max_distance()`). If fewer than
`min_analogs` candidates pass the spatial/temporal/distance filters, the
query returns status "no_reliable_analogs" rather than forcing a result.
"""
from __future__ import annotations

import os
import pickle
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.neighbors import NearestNeighbors

from .feature_vector import ANALOG_FEATURE_COLS, AnalogScaler

INDEX_DIR = os.path.join("models", "phase5")
DEFAULT_MIN_ANALOGS = 5
DEFAULT_K = 10

SpatialConstraint = str  # "same_region" | "nearby" | "india_wide"


@dataclass
class Analog:
    rank: int
    distance: float
    similarity: float
    historical_init_time: pd.Timestamp
    historical_valid_time: pd.Timestamp
    lead_day: int
    latitude: float
    longitude: float
    region: str
    forecast_precip_mm: float
    forecast_temp_c: float
    actual_precip_mm: float
    actual_temp_c: float
    precip_error_mm: float
    temp_error_c: float
    rain_bust: bool
    temperature_bust: bool


@dataclass
class AnalogQueryResult:
    status: str  # "ok" | "no_reliable_analogs"
    analogs: list[Analog] = field(default_factory=list)
    n_candidates_considered: int = 0
    spatial_constraint: str = ""
    temporal_constraint: str = ""
    max_distance_used: float = 0.0
    warning: str | None = None


def _region_centroids(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("region_v2")[["latitude", "longitude"]].mean()


def _nearby_regions(region: str, centroids: pd.DataFrame, n: int = 5) -> list[str]:
    if region not in centroids.index:
        return [region]
    d2 = (centroids.latitude - centroids.loc[region, "latitude"]) ** 2 + (
        centroids.longitude - centroids.loc[region, "longitude"]
    ) ** 2
    return d2.sort_values().index[:n].tolist()


class AnalogIndex:
    def __init__(
        self,
        reference_df: pd.DataFrame,
        scaler: AnalogScaler,
        nn_model: NearestNeighbors,
        feature_matrix: np.ndarray,
    ) -> None:
        self.reference_df = reference_df.reset_index(drop=True)
        self.scaler = scaler
        self.nn_model = nn_model
        self.feature_matrix = feature_matrix
        self._centroids = _region_centroids(self.reference_df)
        self._max_distance_cache: dict[str, float] = {}

    @classmethod
    def build(cls, reference_df: pd.DataFrame, fit_split: str = "train") -> "AnalogIndex":
        scaler = AnalogScaler().fit(reference_df[reference_df.split == fit_split])
        feature_matrix = scaler.transform(reference_df)
        nn_model = NearestNeighbors(metric="euclidean", algorithm="auto")
        nn_model.fit(feature_matrix)
        return cls(reference_df, scaler, nn_model, feature_matrix)

    def save(self, path: str = INDEX_DIR) -> None:
        os.makedirs(path, exist_ok=True)
        self.reference_df.to_parquet(os.path.join(path, "reference.parquet"), index=False)
        np.save(os.path.join(path, "feature_matrix.npy"), self.feature_matrix)
        with open(os.path.join(path, "scaler.pkl"), "wb") as f:
            pickle.dump(self.scaler.to_dict(), f)

    @classmethod
    def load(cls, path: str = INDEX_DIR) -> "AnalogIndex":
        reference_df = pd.read_parquet(os.path.join(path, "reference.parquet"))
        feature_matrix = np.load(os.path.join(path, "feature_matrix.npy"))
        with open(os.path.join(path, "scaler.pkl"), "rb") as f:
            scaler = AnalogScaler.from_dict(pickle.load(f))
        nn_model = NearestNeighbors(metric="euclidean", algorithm="auto")
        nn_model.fit(feature_matrix)
        return cls(reference_df, scaler, nn_model, feature_matrix)

    def warm_cache(self) -> None:
        """Pre-computes _default_max_distance for every region once, so a
        batch of queries (e.g. retrospective evaluation) doesn't pay the
        ~1-1.5s per-region cold-start cost scattered across its first query
        into each region."""
        for region in self.reference_df.region_v2.unique():
            self._default_max_distance(region)

    def _default_max_distance(self, region: str) -> float:
        """90th percentile of same-region nearest-neighbor (nearest OTHER
        point) distance, computed empirically from the reference database -
        not an arbitrary constant. Cached per region: this depends only on
        the static reference data, not on any individual query, and is
        expensive enough (an O(n^2)-ish pairwise computation over a
        region's ~10k-30k rows) that recomputing it on every single query
        call would dominate query latency - see
        outputs/phase5/performance_benchmark.md."""
        if region in self._max_distance_cache:
            return self._max_distance_cache[region]

        mask = (self.reference_df.region_v2 == region).to_numpy()
        if mask.sum() < 10:
            mask = np.ones(len(self.reference_df), dtype=bool)  # too few in-region points - fall back to global
        sub = self.feature_matrix[mask]
        if len(sub) < 2:
            result = float("inf")
        else:
            # one-time cost per region (result is cached) - sklearn's
            # vectorized fit+kneighbors is fast for a SINGLE call; it was
            # only the "re-fit on every query" pattern (fixed above in
            # query()) that was slow.
            nn = NearestNeighbors(metric="euclidean").fit(sub)
            dists, _ = nn.kneighbors(sub, n_neighbors=2)
            result = float(np.percentile(dists[:, 1], 90))

        self._max_distance_cache[region] = result
        return result

    def query(
        self,
        query_row: dict,
        k: int = DEFAULT_K,
        spatial_constraint: SpatialConstraint = "same_region",
        temporal_constraint: str = "none",
        as_of: pd.Timestamp | None = None,
        exclude_key: tuple | None = None,
        max_distance: float | None = None,
        min_analogs: int = DEFAULT_MIN_ANALOGS,
    ) -> AnalogQueryResult:
        region = query_row["region_v2"]
        as_of = as_of if as_of is not None else pd.Timestamp(query_row["init_time"])

        candidate_mask = self.reference_df.init_time < as_of
        if exclude_key is not None:
            key_cols = ["init_time", "lead_day", "latitude", "longitude"]
            is_self = np.ones(len(self.reference_df), dtype=bool)
            for col, val in zip(key_cols, exclude_key):
                is_self &= (self.reference_df[col] == val).to_numpy()
            candidate_mask &= ~is_self

        if spatial_constraint == "same_region":
            candidate_mask &= self.reference_df.region_v2 == region
        elif spatial_constraint == "nearby":
            allowed = _nearby_regions(region, self._centroids, n=5)
            candidate_mask &= self.reference_df.region_v2.isin(allowed)
        elif spatial_constraint == "india_wide":
            pass
        else:
            raise ValueError(f"unknown spatial_constraint: {spatial_constraint}")

        if temporal_constraint == "exact_month":
            candidate_mask &= self.reference_df.month == query_row["month"]
        elif temporal_constraint == "jjas":
            candidate_mask &= self.reference_df.month.isin([6, 7, 8, 9])
        elif temporal_constraint != "none":
            raise ValueError(f"unknown temporal_constraint: {temporal_constraint}")

        n_candidates = int(candidate_mask.sum())
        if max_distance is None:
            max_distance = self._default_max_distance(region)

        if n_candidates == 0:
            return AnalogQueryResult(
                status="no_reliable_analogs", n_candidates_considered=0,
                spatial_constraint=spatial_constraint, temporal_constraint=temporal_constraint,
                max_distance_used=max_distance,
                warning="no candidates passed the spatial/temporal/temporal-cutoff filters",
            )

        idx = np.where(candidate_mask.to_numpy())[0]
        sub_matrix = self.feature_matrix[idx]
        query_vec = self.scaler.transform(pd.DataFrame([query_row]))[0]
        # direct numpy distance computation - re-fitting a fresh sklearn
        # NearestNeighbors object on every query (as an earlier version of
        # this method did) costs ~1.2s/query from per-call construction
        # overhead, making retrospective evaluation (thousands of queries)
        # impractically slow. A plain vectorized Euclidean distance + partial
        # sort is both simpler and ~2-3 orders of magnitude faster for this
        # dataset size (see outputs/phase5/performance_benchmark.md).
        all_dists = np.linalg.norm(sub_matrix - query_vec, axis=1)
        n_query = min(k * 3, len(idx))  # over-fetch, then apply max_distance filter
        nearest_local = np.argpartition(all_dists, n_query - 1)[:n_query]
        order = np.argsort(all_dists[nearest_local])
        local_pos = nearest_local[order]
        dists = all_dists[local_pos]

        keep = dists <= max_distance
        dists, local_pos = dists[keep][:k], local_pos[keep][:k]
        global_idx = idx[local_pos]

        if len(global_idx) < min_analogs:
            return AnalogQueryResult(
                status="no_reliable_analogs",
                n_candidates_considered=n_candidates,
                spatial_constraint=spatial_constraint, temporal_constraint=temporal_constraint,
                max_distance_used=max_distance,
                warning=(
                    f"only {len(global_idx)} analog(s) within max_distance={max_distance:.2f} "
                    f"(need >= {min_analogs}) - low_analog_confidence"
                ),
            )

        analogs = []
        for rank, (gi, d) in enumerate(zip(global_idx, dists), start=1):
            row = self.reference_df.iloc[gi]
            analogs.append(
                Analog(
                    rank=rank,
                    distance=float(d),
                    similarity=float(1.0 / (1.0 + d)),
                    historical_init_time=row.init_time,
                    historical_valid_time=row.valid_time,
                    lead_day=int(row.lead_day),
                    latitude=float(row.latitude),
                    longitude=float(row.longitude),
                    region=row.region_v2,
                    forecast_precip_mm=float(row.fcst_precip_mm),
                    forecast_temp_c=float(row.fcst_temp_c),
                    actual_precip_mm=float(row.obs_precip_mm),
                    actual_temp_c=float(row.obs_temp_c),
                    precip_error_mm=float(row.error_precip_mm),
                    temp_error_c=float(row.error_temp_c),
                    rain_bust=bool(row.bust_precip_categorical),
                    temperature_bust=bool(row.bust_temp_hard),
                )
            )

        return AnalogQueryResult(
            status="ok", analogs=analogs, n_candidates_considered=n_candidates,
            spatial_constraint=spatial_constraint, temporal_constraint=temporal_constraint,
            max_distance_used=max_distance,
        )
