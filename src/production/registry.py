"""
Phase 4 - the production model registry LOADER (the builder lives in
build_registry.py). The inference system must load this rather than
guessing which model/feature-set/calibration to use - nothing in
src/production/ hard-codes a feature list or model path outside this
module.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from functools import lru_cache

REGISTRY_DIR = os.path.join("models", "registry")
ARTIFACT_DIR = os.path.join("models", "artifacts")

PRODUCTION_MODELS = ("rain_v1", "temperature_v1")


@dataclass(frozen=True)
class ModelEntry:
    key: str
    raw: dict

    @property
    def target_variable(self) -> str:
        return self.raw["target_variable"]

    @property
    def feature_order(self) -> list[str]:
        return self.raw["feature_order"]

    @property
    def model_artifact_path(self) -> str:
        return self.raw["model_artifact_path"]

    @property
    def calibration_method(self) -> str:
        return self.raw["calibration"]["method"]

    @property
    def calibration_artifact_path(self) -> str | None:
        return self.raw["calibration"]["artifact_path"]

    @property
    def status(self) -> str:
        return self.raw["status"]

    @property
    def lead_curve(self) -> dict:
        return self.raw["metrics_2021_test"]


class UnknownModelError(KeyError):
    pass


class ExperimentalFeatureRequestedError(RuntimeError):
    """Raised when a caller asks production inference to use a feature that
    only exists in the experimental (pilot-scope) research pipeline - per
    instructions, this must fail clearly, never silently substitute."""


@lru_cache(maxsize=None)
def load_entry(model_key: str) -> ModelEntry:
    if model_key not in PRODUCTION_MODELS:
        raise UnknownModelError(
            f"'{model_key}' is not a known production model. "
            f"Available: {PRODUCTION_MODELS}. "
            "Experimental models (e.g. the ensemble pilot) are never loadable "
            "through this registry - see src/phase3/ensemble_pilot_experiment.py."
        )
    path = os.path.join(REGISTRY_DIR, f"{model_key}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} not found - run `.venv/Scripts/python.exe -m "
            "src.production.build_registry` (after build_artifacts.py and "
            "build_calibration.py) to generate it."
        )
    with open(path) as f:
        raw = json.load(f)
    return ModelEntry(key=model_key, raw=raw)


def all_entries() -> dict[str, ModelEntry]:
    return {k: load_entry(k) for k in PRODUCTION_MODELS}


EXPERIMENTAL_FEATURE_NAMES = frozenset(
    {
        "ensemble_mean_precip", "ensemble_std_precip", "ensemble_min_precip",
        "ensemble_max_precip", "ensemble_iqr_precip", "ensemble_cv_precip",
        "ensemble_mean_temp", "ensemble_std_temp", "ensemble_min_temp",
        "ensemble_max_temp", "ensemble_iqr_temp",
        "domain_mean_ensemble_std_precip", "domain_mean_ensemble_std_temp",
        "humidity_850hpa", "geopotential_500hpa",
    }
)


def assert_no_experimental_features(requested: set[str]) -> None:
    leaked = requested & EXPERIMENTAL_FEATURE_NAMES
    if leaked:
        raise ExperimentalFeatureRequestedError(
            f"Requested feature(s) {sorted(leaked)} are experimental "
            "(pilot-scope ensemble/atmosphere - see "
            "src/phase3/ensemble_pilot_experiment.py) and are NOT part of any "
            "production model. Production inference refuses to silently drop "
            "or substitute them."
        )
