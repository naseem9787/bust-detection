"""
Phase 3 - F: feature ablation study. Nested feature groups, each one a
superset of the previous, quantifying where the Phase 2 model's predictive
signal actually comes from.

Model 5 uses the exact same feature set as Phase 2's full model, so its
numbers should match outputs/phase2/model_comparison.csv (a further
consistency check beyond Stage E's direct replication).

Models 6 (+atmosphere) and 7 (+ensemble) are added by
run_ablation_extended() once the new Phase 3 data is available - see
run_phase3.py for the two-stage call.

Usage:
    .venv/Scripts/python.exe -m src.phase3.ablation
"""
from __future__ import annotations

import os

import pandas as pd

from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR
from ..phase2.features import TARGET_COLS
from . import modeling

OUT_DIR = os.path.join("outputs", "phase3")
PLOT_DIR = os.path.join(OUT_DIR, "plots")

GROUP1 = ["lead_day", "month", "latitude", "longitude", "region_v2"]
GROUP2 = GROUP1 + ["fcst_precip_mm", "fcst_temp_c", "fcst_mslp_hpa"]
GROUP3 = GROUP2 + ["precip_forecast_jump", "temp_forecast_jump"]
GROUP4 = GROUP3 + [
    "hist_bust_precip_categorical_rate", "hist_bust_temp_hard_rate",
    "hist_mean_abs_error_precip_mm", "hist_mean_abs_error_temp_c",
]
GROUP5 = GROUP4 + ["fcst_precip_anomaly_vs_domain_mean", "fcst_temp_anomaly_vs_domain_mean"]

FEATURE_GROUPS = [
    ("Model1_LeadLocationMonth", GROUP1),
    ("Model2_ForecastState", GROUP2),
    ("Model3_RunToRunJump", GROUP3),
    ("Model4_HistoricalStats", GROUP4),
    ("Model5_SpatialAnomaly_FullPhase2", GROUP5),
]


def _load_base_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    train = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_train.parquet"))
    test = pd.read_parquet(os.path.join(PHASE2_OUT_DIR, "features_test.parquet"))
    train["region_v2"] = train["region_v2"].astype("category")
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].cat.categories)
    )
    return train, test


def run_ablation_for_target(train: pd.DataFrame, test: pd.DataFrame, target: str) -> pd.DataFrame:
    reference_prob = float(train[target].mean())
    threshold = reference_prob
    rows = []

    y_true = test[target].to_numpy().astype(int)
    y_hist = modeling.historical_climatology_predict(
        train, test, target, ["region_v2", "lead_day", "month"]
    )
    hist_metrics = modeling.score(y_true, y_hist, threshold, reference_prob)
    rows.append({"model": "Model0_HistoricalBaseline", "target": target, **hist_metrics})

    for name, cols in FEATURE_GROUPS:
        print(f"  training {name} ({len(cols)} features)...")
        res = modeling.train_lgbm(train, test, target, cols)
        metrics = modeling.score(res["y_test"], res["y_prob"], threshold, reference_prob)
        rows.append(
            {
                "model": name,
                "target": target,
                "n_features": len(cols),
                "best_iteration": res["best_iteration"],
                **metrics,
            }
        )

    return pd.DataFrame(rows)


def main() -> pd.DataFrame:
    os.makedirs(OUT_DIR, exist_ok=True)
    train, test = _load_base_tables()

    all_rows = []
    for target in TARGET_COLS:
        print(f"\n=== ablation for {target} ===")
        df = run_ablation_for_target(train, test, target)
        all_rows.append(df)
        print(df[["model", "roc_auc", "pr_auc", "brier_score", "brier_skill_score"]].to_string(index=False))

    result = pd.concat(all_rows, ignore_index=True)
    result_path = os.path.join(OUT_DIR, "ablation_results.csv")
    result.to_csv(result_path, index=False)
    print(f"\nsaved -> {result_path}")
    return result


if __name__ == "__main__":
    main()
