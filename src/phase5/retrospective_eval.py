"""
Phase 5 - Stage 10: retrospective evaluation. Does NOT assume analogs help
- reports honestly whichever way it goes.

For a sample of 2021 test-year forecasts (a stratified sample across
lead_day, not the full 446,520 rows - see performance_benchmark.md for why
a sample is used and how large it is), for EACH forecast:
  1. Take its forecast-only feature vector (already built - no re-derivation).
  2. Query historical analogs (as_of = this forecast's own init_time, so
     only genuinely-past data is retrievable - see analogs.py docstring).
  3. analog_estimated_bust_rate = fraction of the K analogs that busted.
  4. analog_expected_error = mean |analog forecast error|.

Then scores four methods on the SAME sample against the SAME actual
outcomes:
  Baseline 1: climatological bust rate (region x lead x month, train-only-fit)
  Baseline 2: Phase 4's frozen production ML model (rain_v1 / temperature_v1)
  Baseline 3: analog-only estimate (step 3 above)
  Baseline 4: ML + analog-derived features (ONLY if Baseline 3 shows real
              skill - see analog_enhanced_model.py, run separately)

Also runs the Stage 5/6 spatial/temporal constraint comparison BEFORE
picking a final analog configuration - the winning config is what
Baseline 3 above uses.

Usage:
    .venv/Scripts/python.exe -m src.phase5.retrospective_eval
"""
from __future__ import annotations

import os
import time

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ..phase3 import modeling
from ..production.inference import ProductionInferenceEngine
from .analogs import INDEX_DIR, AnalogIndex

OUT_DIR = os.path.join("outputs", "phase5")
SAMPLE_SIZE_PER_LEAD = 200  # x10 lead days = ~2000 sampled test forecasts
K_ANALOGS = 10
RANDOM_SEED = 42


def stratified_sample(ref: pd.DataFrame, n_per_lead: int = SAMPLE_SIZE_PER_LEAD) -> pd.DataFrame:
    test = ref[ref.split == "test"]
    rng = np.random.default_rng(RANDOM_SEED)
    parts = []
    for lead, g in test.groupby("lead_day"):
        n = min(n_per_lead, len(g))
        parts.append(g.sample(n=n, random_state=RANDOM_SEED))
    return pd.concat(parts, ignore_index=True)


def run_analog_queries(
    index: AnalogIndex, sample: pd.DataFrame, spatial: str, temporal: str, k: int = K_ANALOGS
) -> pd.DataFrame:
    rows = []
    for _, row in sample.iterrows():
        q = row.to_dict()
        result = index.query(
            q, k=k, spatial_constraint=spatial, temporal_constraint=temporal,
            exclude_key=(q["init_time"], q["lead_day"], q["latitude"], q["longitude"]),
        )
        if result.status != "ok":
            rows.append(
                {
                    "status": result.status, "analog_rain_bust_rate": np.nan,
                    "analog_temp_bust_rate": np.nan, "analog_precip_abs_error": np.nan,
                    "analog_temp_abs_error": np.nan, "n_analogs": 0,
                }
            )
            continue
        analogs = result.analogs
        rows.append(
            {
                "status": "ok",
                "analog_rain_bust_rate": np.mean([a.rain_bust for a in analogs]),
                "analog_temp_bust_rate": np.mean([a.temperature_bust for a in analogs]),
                "analog_precip_abs_error": np.mean([abs(a.precip_error_mm) for a in analogs]),
                "analog_temp_abs_error": np.mean([abs(a.temp_error_c) for a in analogs]),
                "n_analogs": len(analogs),
                "mean_distance": np.mean([a.distance for a in analogs]),
                "top1_distance": analogs[0].distance,
            }
        )
    return pd.DataFrame(rows)


def compare_spatial_temporal_constraints(index: AnalogIndex, sample: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for spatial in ["same_region", "nearby", "india_wide"]:
        for temporal in ["none", "exact_month", "jjas"]:
            t0 = time.time()
            analog_df = run_analog_queries(index, sample, spatial, temporal)
            elapsed = time.time() - t0
            merged = pd.concat([sample.reset_index(drop=True), analog_df], axis=1)
            valid = merged[merged.status == "ok"]
            n_ok = len(valid)
            if n_ok < 20:
                rows.append(
                    {"spatial": spatial, "temporal": temporal, "n_ok": n_ok, "roc_auc_rain": np.nan,
                     "corr_precip_error": np.nan, "elapsed_s": elapsed}
                )
                continue
            y_true = valid.bust_precip_categorical.astype(int)
            y_score = valid.analog_rain_bust_rate
            roc = roc_auc_score(y_true, y_score) if y_true.nunique() > 1 else np.nan
            corr = np.corrcoef(valid.analog_precip_abs_error, valid.abs_error_precip_mm)[0, 1]
            rows.append(
                {
                    "spatial": spatial, "temporal": temporal, "n_ok": n_ok,
                    "roc_auc_rain": roc, "corr_precip_error": corr, "elapsed_s": elapsed,
                }
            )
            print(f"  spatial={spatial:12s} temporal={temporal:12s} n_ok={n_ok:4d} "
                  f"roc_auc_rain={roc if roc==roc else float('nan'):.4f} corr_err={corr:.4f} "
                  f"({elapsed:.1f}s)")
    return pd.DataFrame(rows)


def score_probability(name: str, y_true: np.ndarray, y_prob: np.ndarray, reference_prob: float) -> dict:
    if len(y_true) == 0 or pd.isna(y_prob).all():
        return {"method": name, "n": 0}
    mask = ~pd.isna(y_prob)
    y_true, y_prob = y_true[mask], y_prob[mask]
    if y_true.sum() == 0 or y_true.sum() == len(y_true):
        roc = float("nan")
    else:
        roc = roc_auc_score(y_true, y_prob)
    return {
        "method": name,
        "n": int(len(y_true)),
        "roc_auc": roc,
        "pr_auc": average_precision_score(y_true, y_prob) if y_true.max() > 0 else float("nan"),
        "brier_score": brier_score_loss(y_true, y_prob),
        "brier_skill_score": 1 - brier_score_loss(y_true, y_prob) / brier_score_loss(
            y_true, np.full_like(y_prob, reference_prob)
        ),
    }


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    print("loading analog index...")
    index = AnalogIndex.load(INDEX_DIR)
    index.warm_cache()

    ref = index.reference_df
    sample = stratified_sample(ref)
    print(f"stratified sample: {len(sample):,} test-year forecasts across {sample.lead_day.nunique()} lead days")

    print("\n=== Stage 5/6: spatial x temporal constraint comparison ===")
    constraint_results = compare_spatial_temporal_constraints(index, sample)
    constraint_path = os.path.join(OUT_DIR, "constraint_comparison.csv")
    constraint_results.to_csv(constraint_path, index=False)
    print(f"saved -> {constraint_path}")

    valid_constraints = constraint_results.dropna(subset=["roc_auc_rain"])
    best = valid_constraints.loc[valid_constraints.roc_auc_rain.idxmax()]
    print(f"\nbest config: spatial={best.spatial} temporal={best.temporal} "
          f"(ROC-AUC={best.roc_auc_rain:.4f})")

    print("\n=== Stage 10: main retrospective comparison (using the best config) ===")
    analog_df = run_analog_queries(index, sample, best.spatial, best.temporal)
    merged = pd.concat([sample.reset_index(drop=True), analog_df], axis=1)
    merged.to_csv(os.path.join(OUT_DIR, "retrospective_sample_with_analogs.csv"), index=False)

    train_ref = ref[ref.split == "train"]
    reference_prob_rain = float(train_ref.bust_precip_categorical.mean())
    reference_prob_temp = float(train_ref.bust_temp_hard.mean())

    y_hist_rain = modeling.historical_climatology_predict(
        train_ref, merged, "bust_precip_categorical", ["region_v2", "lead_day", "month"]
    )
    y_hist_temp = modeling.historical_climatology_predict(
        train_ref, merged, "bust_temp_hard", ["region_v2", "lead_day", "month"]
    )

    print("running Phase 4 production ML on the same sample...")
    engine = ProductionInferenceEngine()
    ml_rain_probs, ml_temp_probs = [], []
    for _, row in merged.iterrows():
        result = engine.predict(
            init_time=row.init_time, lead_day=int(row.lead_day),
            latitude=float(row.latitude), longitude=float(row.longitude),
            forecast_precip_mm=float(row.fcst_precip_mm), forecast_temp_c=float(row.fcst_temp_c),
            forecast_mslp_hpa=float(row.fcst_mslp_hpa), forecast_wind_speed_10m=float(row.wind_speed_10m),
        )
        ml_rain_probs.append(result["rain_bust_probability"]["calibrated"])
        ml_temp_probs.append(result["temperature_bust_probability"]["calibrated"])
    merged["ml_rain_prob"] = ml_rain_probs
    merged["ml_temp_prob"] = ml_temp_probs

    y_true_rain = merged.bust_precip_categorical.to_numpy().astype(int)
    y_true_temp = merged.bust_temp_hard.to_numpy().astype(int)

    comparison_rows = [
        score_probability("Baseline1_Climatology", y_true_rain, y_hist_rain, reference_prob_rain) | {"target": "rain"},
        score_probability("Baseline2_Phase4_ML", y_true_rain, merged.ml_rain_prob.to_numpy(), reference_prob_rain) | {"target": "rain"},
        score_probability("Baseline3_AnalogOnly", y_true_rain, merged.analog_rain_bust_rate.to_numpy(), reference_prob_rain) | {"target": "rain"},
        score_probability("Baseline1_Climatology", y_true_temp, y_hist_temp, reference_prob_temp) | {"target": "temp"},
        score_probability("Baseline2_Phase4_ML", y_true_temp, merged.ml_temp_prob.to_numpy(), reference_prob_temp) | {"target": "temp"},
        score_probability("Baseline3_AnalogOnly", y_true_temp, merged.analog_temp_bust_rate.to_numpy(), reference_prob_temp) | {"target": "temp"},
    ]
    comparison = pd.DataFrame(comparison_rows)
    comparison_path = os.path.join(OUT_DIR, "retrospective_comparison.csv")
    comparison.to_csv(comparison_path, index=False)
    print(f"\nsaved -> {comparison_path}")
    print(comparison.to_string(index=False))

    valid = merged.dropna(subset=["analog_precip_abs_error"])
    corr_precip = np.corrcoef(valid.analog_precip_abs_error, valid.abs_error_precip_mm)[0, 1]
    corr_temp = np.corrcoef(valid.analog_temp_abs_error, valid.abs_error_temp_c)[0, 1]
    print(f"\ncorrelation(analog expected |error|, actual |error|): "
          f"precip={corr_precip:.4f}  temp={corr_temp:.4f}")

    with open(os.path.join(OUT_DIR, "error_correlation.txt"), "w") as f:
        f.write(f"corr_analog_expected_vs_actual_abs_error_precip={corr_precip:.4f}\n")
        f.write(f"corr_analog_expected_vs_actual_abs_error_temp={corr_temp:.4f}\n")
        f.write(f"best_spatial_constraint={best.spatial}\n")
        f.write(f"best_temporal_constraint={best.temporal}\n")


if __name__ == "__main__":
    main()
