"""
Phase 2 - B3-B7: compare LightGBM against Phase-1-style baselines, feature
importance, probability calibration, and per-lead/per-region breakdowns.

Usage:
    .venv/Scripts/python.exe -m src.phase2.evaluate_model
"""
from __future__ import annotations

import os

import lightgbm as lgb
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss

from ..phase1.evaluate import score_baseline
from .features import OUT_DIR, TARGET_COLS

# Phase 2's own climatology grouping - region_v2 (full-coverage geography
# fix, src/phase2/geography.py), NOT component_analysis.GROUP_COLS (which
# is tied to Phase 1's coarse 8-box "region" column, not present in the
# Phase 2 feature tables).
HIST_GROUP_COLS = ["region_v2", "lead_day", "month"]


def _fit_climatology(train: pd.DataFrame, target_col: str):
    lookup = train.groupby(HIST_GROUP_COLS, observed=True)[target_col].mean()
    return lookup, float(train[target_col].mean())


def _predict(df: pd.DataFrame, lookup: pd.Series, fallback: float) -> np.ndarray:
    keys = pd.MultiIndex.from_frame(df[HIST_GROUP_COLS])
    pred = keys.map(lookup)
    return pd.Series(pred, index=df.index, dtype=float).fillna(fallback).to_numpy()

PLOT_DIR = os.path.join(OUT_DIR, "plots")


def load_split(target: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    train = pd.read_parquet(os.path.join(OUT_DIR, "features_train.parquet"))
    test = pd.read_parquet(os.path.join(OUT_DIR, "features_test.parquet"))
    train["region_v2"] = train["region_v2"].astype("category")
    test["region_v2"] = test["region_v2"].astype(
        pd.CategoricalDtype(categories=train["region_v2"].cat.categories)
    )
    preds = pd.read_parquet(os.path.join(OUT_DIR, f"predictions_{target}.parquet"))
    val_preds = pd.read_parquet(os.path.join(OUT_DIR, f"val_predictions_{target}.parquet"))
    assert len(preds) == len(test), "prediction/test row-count mismatch - regenerate both"
    test = test.reset_index(drop=True)
    test["y_prob_lgbm"] = preds["y_prob"].to_numpy()
    return train, test, preds, val_preds


def fit_baselines(train: pd.DataFrame, test: pd.DataFrame, target: str) -> dict[str, np.ndarray]:
    hist_lookup, hist_fallback = _fit_climatology(train, target)
    lead_lookup = train.groupby(["lead_day"], observed=True)[target].mean()
    lead_fallback = float(train[target].mean())

    y_hist = _predict(test, hist_lookup, hist_fallback)
    y_lead = test["lead_day"].map(lead_lookup).fillna(lead_fallback).to_numpy()
    return {"Historical baseline (region x lead x month)": y_hist, "Lead-time-only baseline": y_lead}


def build_comparison_table(train: pd.DataFrame, test: pd.DataFrame, target: str) -> pd.DataFrame:
    y_true = test[target].to_numpy().astype(int)
    reference_prob = float(train[target].mean())
    threshold = reference_prob

    methods = fit_baselines(train, test, target)
    methods["LightGBM"] = test["y_prob_lgbm"].to_numpy()

    rows = []
    for name, y_prob in methods.items():
        row = score_baseline(name, y_true, y_prob, threshold, reference_prob)
        row["target"] = target
        rows.append(row)
    return pd.DataFrame(rows)


def feature_importance(target: str) -> pd.DataFrame:
    booster = lgb.Booster(model_file=os.path.join(OUT_DIR, f"lightgbm_{target}.txt"))
    gain = booster.feature_importance(importance_type="gain")
    split = booster.feature_importance(importance_type="split")
    df = pd.DataFrame(
        {"feature": booster.feature_name(), "gain": gain, "split": split, "target": target}
    ).sort_values("gain", ascending=False)
    return df


def plot_feature_importance(df: pd.DataFrame, target: str) -> str:
    d = df.sort_values("gain", ascending=True)
    fig, ax = plt.subplots(figsize=(7, 5))
    ax.barh(d.feature, d.gain)
    ax.set_xlabel("Gain importance")
    ax.set_title(f"LightGBM feature importance - {target}")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, f"feature_importance_{target}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def calibrate_and_plot(
    target: str, val_preds: pd.DataFrame, test: pd.DataFrame
) -> tuple[np.ndarray, dict]:
    """Isotonic calibration fit on the 2020 validation predictions (from the
    probe model, never trained on 2020) - applied to the 2021 test
    predictions from the FINAL model (trained on 2018-2020)."""
    iso = IsotonicRegression(out_of_bounds="clip")
    iso.fit(val_preds["y_prob"], val_preds["y_true"])

    y_true = test[target].to_numpy().astype(int)
    y_prob_raw = test["y_prob_lgbm"].to_numpy()
    y_prob_cal = iso.predict(y_prob_raw)

    brier_raw = brier_score_loss(y_true, y_prob_raw)
    brier_cal = brier_score_loss(y_true, y_prob_cal)

    fig, ax = plt.subplots(figsize=(5.5, 5.5))
    ax.plot([0, 1], [0, 1], "k--", label="perfectly calibrated")
    frac_pos, mean_pred = calibration_curve(y_true, y_prob_raw, n_bins=10, strategy="quantile")
    ax.plot(mean_pred, frac_pos, marker="o", label=f"raw (Brier={brier_raw:.4f})")
    frac_pos_c, mean_pred_c = calibration_curve(y_true, y_prob_cal, n_bins=10, strategy="quantile")
    ax.plot(mean_pred_c, frac_pos_c, marker="s", label=f"isotonic-calibrated (Brier={brier_cal:.4f})")
    ax.set_xlabel("Mean predicted probability")
    ax.set_ylabel("Observed rate")
    ax.set_title(f"Reliability diagram - {target} (2021 holdout)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, f"reliability_{target}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)

    return y_prob_cal, {
        "target": target,
        "brier_raw": float(brier_raw),
        "brier_calibrated": float(brier_cal),
        "calibration_improved": bool(brier_cal < brier_raw),
        "calibration_fit_on": "2020 (validation year, probe model out-of-fold)",
        "plot": path,
    }


def per_group_metrics(test: pd.DataFrame, target: str, group_col: str) -> pd.DataFrame:
    rows = []
    for key, g in test.groupby(group_col, observed=True):
        y_true = g[target].to_numpy().astype(int)
        if y_true.min() == y_true.max():
            auc = float("nan")
        else:
            from sklearn.metrics import roc_auc_score

            auc = roc_auc_score(y_true, g["y_prob_lgbm"])
        from sklearn.metrics import average_precision_score

        rows.append(
            {
                group_col: key,
                "target": target,
                "n": len(g),
                "prevalence": float(y_true.mean()),
                "roc_auc": auc,
                "pr_auc": average_precision_score(y_true, g["y_prob_lgbm"]),
                "brier": brier_score_loss(y_true, g["y_prob_lgbm"]),
            }
        )
    df = pd.DataFrame(rows)
    round_cols = df.columns.difference([group_col, "target", "n"])
    df[round_cols] = df[round_cols].round(4)
    return df


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    all_comparisons = []
    all_importances = []
    all_calibration = []
    all_per_lead = []
    all_per_region = []

    for target in TARGET_COLS:
        print(f"\n=== evaluating {target} ===")
        train, test, preds, val_preds = load_split(target)

        comparison = build_comparison_table(train, test, target)
        all_comparisons.append(comparison)
        print(comparison[["method", "roc_auc", "pr_auc", "brier_score", "brier_skill_score"]])

        importance = feature_importance(target)
        all_importances.append(importance)
        plot_path = plot_feature_importance(importance, target)
        print(f"saved -> {plot_path}")
        print(importance.head(5).to_string(index=False))

        _, cal_info = calibrate_and_plot(target, val_preds, test)
        all_calibration.append(cal_info)
        print(f"calibration: {cal_info}")

        per_lead = per_group_metrics(test, target, "lead_day")
        all_per_lead.append(per_lead)

        per_region = per_group_metrics(test, target, "region_v2")
        all_per_region.append(per_region)

    comparison_path = os.path.join(OUT_DIR, "model_comparison.csv")
    pd.concat(all_comparisons, ignore_index=True).to_csv(comparison_path, index=False)
    print(f"\nsaved -> {comparison_path}")

    importance_path = os.path.join(OUT_DIR, "feature_importance.csv")
    pd.concat(all_importances, ignore_index=True).to_csv(importance_path, index=False)
    print(f"saved -> {importance_path}")

    calibration_path = os.path.join(OUT_DIR, "calibration_summary.csv")
    pd.DataFrame(all_calibration).to_csv(calibration_path, index=False)
    print(f"saved -> {calibration_path}")

    per_lead_path = os.path.join(OUT_DIR, "per_lead_metrics.csv")
    pd.concat(all_per_lead, ignore_index=True).to_csv(per_lead_path, index=False)
    print(f"saved -> {per_lead_path}")

    per_region_path = os.path.join(OUT_DIR, "per_region_metrics.csv")
    pd.concat(all_per_region, ignore_index=True).to_csv(per_region_path, index=False)
    print(f"saved -> {per_region_path}")


if __name__ == "__main__":
    main()
