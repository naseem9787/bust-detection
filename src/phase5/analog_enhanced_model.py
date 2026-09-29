"""
Phase 5 - Stage 11: analog-enhanced EXPERIMENTAL model.

Only built because Stage 10's retrospective evaluation justified it for
temperature (analog-only BSS 0.094 > Phase 4 ML's 0.064) and it's worth
testing for rain too, even though rain's analog-ONLY calibration was poor
(BSS -0.111) - an ML model might learn to properly weight/recalibrate the
analog signal rather than using it as a raw probability.

Scale limitation (documented, not hidden): computing analog features for
the FULL 1,339,560-row training set at ~40ms/query would take ~15 hours -
infeasible for this phase. Instead, both the "baseline" (no analog
features) and "analog-enhanced" models here are trained on the SAME
stratified sample (a few thousand rows), so the comparison isolates the
effect of adding analog features rather than confounding it with a sample-
size difference. This is explicitly a small-scale proof-of-concept, not a
claim that analog features would perform identically at full production
training scale - see docs/historical_analogs.md Limitations.

NEITHER model here replaces rain_v1/temperature_v1. Both are saved with an
"_experimental" suffix and are NOT registered in models/registry/ - the
production registry (src/production/registry.py) has no path to load them.

Usage:
    .venv/Scripts/python.exe -m src.phase5.analog_enhanced_model
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from ..phase3 import modeling
from ..phase3.ablation import GROUP5
from ..phase3.atmo_merge import WIND_FEATURE_COLS
from .analogs import INDEX_DIR, AnalogIndex
from .retrospective_eval import K_ANALOGS, RANDOM_SEED, run_analog_queries

OUT_DIR = os.path.join("outputs", "phase5")
MODEL_DIR = os.path.join("models", "phase5")

BASE_FEATURES = GROUP5 + WIND_FEATURE_COLS
ANALOG_DERIVED_FEATURES = [
    "analog_rain_bust_rate", "analog_temp_bust_rate",
    "analog_precip_abs_error", "analog_temp_abs_error",
    "mean_distance", "top1_distance", "n_analogs",
]
ENHANCED_FEATURES = BASE_FEATURES + ANALOG_DERIVED_FEATURES

TRAIN_SAMPLE_PER_LEAD = 400  # x10 leads = ~4000 train rows (scale-limited, see docstring)


def build_experiment_sample(index: AnalogIndex) -> tuple[pd.DataFrame, pd.DataFrame]:
    ref = index.reference_df
    rng = np.random.default_rng(RANDOM_SEED)

    train_parts = []
    for lead, g in ref[ref.split == "train"].groupby("lead_day"):
        n = min(TRAIN_SAMPLE_PER_LEAD, len(g))
        train_parts.append(g.sample(n=n, random_state=RANDOM_SEED))
    train_sample = pd.concat(train_parts, ignore_index=True)

    test_sample_path = os.path.join(OUT_DIR, "retrospective_sample_with_analogs.csv")
    test_sample = pd.read_csv(test_sample_path, parse_dates=["init_time", "valid_time"])
    test_sample = test_sample[test_sample.status == "ok"].reset_index(drop=True)

    # retrospective_eval.py's saved CSV predates the hist_*/anomaly_* columns
    # being added to the reference table (see dataset.py's KEEP_COLS) -
    # merge them back in from the index's reference table by natural key,
    # rather than re-running the ~15min constraint sweep (whose results are
    # unaffected - those columns aren't part of ANALOG_FEATURE_COLS).
    key_cols = ["init_time", "lead_day", "latitude", "longitude"]
    extra_cols = [
        "fcst_precip_anomaly_vs_domain_mean", "fcst_temp_anomaly_vs_domain_mean",
        "hist_bust_precip_categorical_rate", "hist_bust_temp_hard_rate",
        "hist_mean_abs_error_precip_mm", "hist_mean_abs_error_temp_c",
    ]
    lookup = ref[key_cols + extra_cols].drop_duplicates(key_cols)
    test_sample = test_sample.merge(lookup, on=key_cols, how="left")
    missing = test_sample[extra_cols].isna().any(axis=1).sum()
    if missing:
        print(f"warning: {missing} test rows failed to merge extra columns - dropping")
        test_sample = test_sample.dropna(subset=extra_cols).reset_index(drop=True)

    print(f"computing analog features for {len(train_sample):,} train rows "
          "(this is the scale-limited step - see module docstring)...")
    train_analog = run_analog_queries(index, train_sample, "same_region", "exact_month", k=K_ANALOGS)
    train_merged = pd.concat([train_sample.reset_index(drop=True), train_analog], axis=1)
    train_merged = train_merged[train_merged.status == "ok"].reset_index(drop=True)

    return train_merged, test_sample


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    index = AnalogIndex.load(INDEX_DIR)
    index.warm_cache()

    train_df, test_df = build_experiment_sample(index)
    print(f"train sample (with analogs, status=ok): {len(train_df):,}")
    print(f"test sample (reused from retrospective_eval): {len(test_df):,}")

    train_df["region_v2"] = train_df["region_v2"].astype("category")
    test_df["region_v2"] = test_df["region_v2"].astype(
        pd.CategoricalDtype(categories=train_df["region_v2"].cat.categories)
    )
    # small-sample fit: no separate validation year carve-out at this scale -
    # a fixed modest tree count is used instead of early stopping, documented
    # explicitly rather than pretending this matches Phase 3/4 rigor.
    import lightgbm as lgb

    results = []
    for target, label in [("bust_precip_categorical", "rain"), ("bust_temp_hard", "temp")]:
        reference_prob = float(train_df[target].mean())
        for name, cols in [("baseline_no_analog", BASE_FEATURES), ("analog_enhanced", ENHANCED_FEATURES)]:
            model = lgb.LGBMClassifier(n_estimators=200, **{**modeling.BASE_PARAMS})
            model.fit(train_df[cols], train_df[target].astype(int))
            y_prob = model.predict_proba(test_df[cols])[:, 1]
            metrics = modeling.score(
                test_df[target].to_numpy().astype(int), y_prob, reference_prob, reference_prob
            )
            results.append({"target": label, "model": name, "n_train": len(train_df), **metrics})
            print(f"{label:5s} {name:20s} ROC-AUC={metrics['roc_auc']:.4f} "
                  f"PR-AUC={metrics['pr_auc']:.4f} Brier={metrics['brier_score']:.4f} "
                  f"BSS={metrics['brier_skill_score']:.4f}")

            if name == "analog_enhanced":
                exp_path = os.path.join(MODEL_DIR, f"{label}_v2_experimental.txt")
                model.booster_.save_model(exp_path)
                print(f"  saved EXPERIMENTAL model -> {exp_path} (NOT registered in models/registry/)")

    result_df = pd.DataFrame(results)
    path = os.path.join(OUT_DIR, "analog_enhanced_model_results.csv")
    result_df.to_csv(path, index=False)
    print(f"\nsaved -> {path}")


if __name__ == "__main__":
    main()
