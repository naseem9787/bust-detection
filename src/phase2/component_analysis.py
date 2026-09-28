"""
Phase 2 - A1: bust component analysis.

Phase 1's `bust_any` is an OR of 5 flags (see src/phase1/dataset.py). This
module scores EACH flag independently as its own binary target, using the
same train-only-fit region x lead_day x month climatology baseline as
Phase 1, evaluated on the 2021 holdout. The goal is to find out which
failure modes carry real predictive structure (Phase 1 already showed
bust_any mostly doesn't - see its README section) so Phase 2B trains on a
target that's actually learnable, not just convenient.

No new information is used: this reuses src.phase1.dataset's already
leak-free (train-only-fit) chronological split.

Usage:
    .venv/Scripts/python.exe -m src.phase2.component_analysis
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, brier_score_loss, roc_auc_score

from ..phase1.dataset import build_phase1_dataset

OUT_DIR = os.path.join("outputs", "phase2")
PLOT_DIR = os.path.join(OUT_DIR, "plots")

COMPONENTS = [
    "bust_precip_categorical",
    "bust_temp_hard",
    "bust_precip_percentile",
    "bust_temp_percentile",
    "bust_mslp_percentile",
    "bust_any",
]

GROUP_COLS = ["region", "lead_day", "month"]


def _fit_climatology(train: pd.DataFrame, target_col: str) -> tuple[pd.Series, float]:
    lookup = train.groupby(GROUP_COLS, observed=True)[target_col].mean()
    fallback = float(train[target_col].mean())
    return lookup, fallback


def _predict(df: pd.DataFrame, lookup: pd.Series, fallback: float) -> np.ndarray:
    keys = pd.MultiIndex.from_frame(df[GROUP_COLS])
    pred = keys.map(lookup)
    return pd.Series(pred, index=df.index, dtype=float).fillna(fallback).to_numpy()


def _safe_auc(y_true: np.ndarray, y_prob: np.ndarray) -> float:
    if y_true.min() == y_true.max():
        return float("nan")  # undefined - only one class present
    return roc_auc_score(y_true, y_prob)


def analyze_component(train: pd.DataFrame, test: pd.DataFrame, component: str) -> dict:
    lookup, fallback = _fit_climatology(train, component)
    y_true = test[component].to_numpy().astype(int)
    y_prob = _predict(test, lookup, fallback)

    by_lead = test.groupby("lead_day")[component].mean()
    by_region = test.loc[test.region != "Unclassified"].groupby("region")[component].mean()
    by_month = test.groupby("month")[component].mean()

    return {
        "component": component,
        "prevalence_train": float(train[component].mean()),
        "prevalence_test": float(test[component].mean()),
        "roc_auc_test": _safe_auc(y_true, y_prob),
        "pr_auc_test": average_precision_score(y_true, y_prob),
        "brier_test": brier_score_loss(y_true, y_prob),
        "lead_rate_min": float(by_lead.min()),
        "lead_rate_max": float(by_lead.max()),
        "lead_rate_range": float(by_lead.max() - by_lead.min()),
        "region_rate_min": float(by_region.min()),
        "region_rate_max": float(by_region.max()),
        "region_rate_range": float(by_region.max() - by_region.min()),
        "month_rate_min": float(by_month.min()),
        "month_rate_max": float(by_month.max()),
        "month_rate_range": float(by_month.max() - by_month.min()),
    }, by_lead, by_region, by_month


def build_breakdown_table(
    per_component: dict[str, tuple[pd.Series, pd.Series, pd.Series]]
) -> pd.DataFrame:
    rows = []
    for component, (by_lead, by_region, by_month) in per_component.items():
        for lead_day, rate in by_lead.items():
            rows.append(
                {"component": component, "dimension": "lead_day", "value": str(lead_day), "rate": rate}
            )
        for region, rate in by_region.items():
            rows.append(
                {"component": component, "dimension": "region", "value": region, "rate": rate}
            )
        for month, rate in by_month.items():
            rows.append(
                {"component": component, "dimension": "month", "value": str(month), "rate": rate}
            )
    return pd.DataFrame(rows)


def plot_rate_by_lead(per_component: dict[str, tuple[pd.Series, pd.Series, pd.Series]]) -> str:
    fig, ax = plt.subplots(figsize=(8, 5))
    for component, (by_lead, _, _) in per_component.items():
        ax.plot(by_lead.index, by_lead.values * 100, marker="o", label=component)
    ax.set_xlabel("Lead day")
    ax.set_ylabel("Component rate (%)")
    ax.set_title("Bust component rate vs. lead day (2021 holdout)")
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "component_rate_by_lead.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def _heatmap(matrix: pd.DataFrame, title: str, fname: str, xlabel: str) -> str:
    fig, ax = plt.subplots(figsize=(max(6, 0.9 * matrix.shape[1]), 0.6 * matrix.shape[0] + 2))
    im = ax.imshow(matrix.values * 100, aspect="auto", cmap="Reds")
    ax.set_xticks(range(matrix.shape[1]))
    ax.set_xticklabels(matrix.columns, rotation=45, ha="right", fontsize=8)
    ax.set_yticks(range(matrix.shape[0]))
    ax.set_yticklabels(matrix.index, fontsize=8)
    ax.set_xlabel(xlabel)
    ax.set_title(title)
    for i in range(matrix.shape[0]):
        for j in range(matrix.shape[1]):
            ax.text(j, i, f"{matrix.values[i, j] * 100:.1f}", ha="center", va="center", fontsize=7)
    fig.colorbar(im, ax=ax, label="rate (%)")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, fname)
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_rate_by_region(per_component: dict[str, tuple[pd.Series, pd.Series, pd.Series]]) -> str:
    matrix = pd.DataFrame({c: by_region for c, (_, by_region, _) in per_component.items()}).T
    return _heatmap(matrix, "Bust component rate by region (2021 holdout)", "component_rate_by_region.png", "region")


def plot_rate_by_month(per_component: dict[str, tuple[pd.Series, pd.Series, pd.Series]]) -> str:
    matrix = pd.DataFrame({c: by_month for c, (_, _, by_month) in per_component.items()}).T
    return _heatmap(matrix, "Bust component rate by month (2021 holdout)", "component_rate_by_month.png", "month")


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    ds = build_phase1_dataset()
    df = ds.df
    train = df[df.split == "train"]
    test = df[df.split == "test"]

    summary_rows = []
    per_component = {}
    for component in COMPONENTS:
        summary, by_lead, by_region, by_month = analyze_component(train, test, component)
        summary_rows.append(summary)
        per_component[component] = (by_lead, by_region, by_month)

    summary_df = pd.DataFrame(summary_rows)
    round_cols = summary_df.columns.difference(["component"])
    summary_df[round_cols] = summary_df[round_cols].round(4)
    out_path = os.path.join(OUT_DIR, "bust_component_analysis.csv")
    summary_df.to_csv(out_path, index=False)
    print(f"saved -> {out_path}")
    print(summary_df.to_string(index=False))

    breakdown = build_breakdown_table(per_component)
    breakdown_path = os.path.join(OUT_DIR, "bust_component_breakdown.csv")
    breakdown.to_csv(breakdown_path, index=False)
    print(f"saved -> {breakdown_path}")

    for p in [
        plot_rate_by_lead(per_component),
        plot_rate_by_region(per_component),
        plot_rate_by_month(per_component),
    ]:
        print(f"saved -> {p}")


if __name__ == "__main__":
    main()
