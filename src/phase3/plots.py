"""
Phase 3 - plots for the ablation study (Stage F), year robustness (G), and
lead-time robustness (H). Separate from Phase 2's plots.py.

Usage:
    .venv/Scripts/python.exe -m src.phase3.plots
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

OUT_DIR = os.path.join("outputs", "phase3")
PLOT_DIR = os.path.join(OUT_DIR, "plots")

MODEL_ORDER = [
    "Model0_HistoricalBaseline",
    "Model1_LeadLocationMonth",
    "Model2_ForecastState",
    "Model3_RunToRunJump",
    "Model4_HistoricalStats",
    "Model5_SpatialAnomaly_FullPhase2",
    "Model6_Atmosphere_Wind",
]
# Model7 (ensemble) is NOT included here - it's evaluated on a much smaller
# pilot-window test subset (see ensemble_pilot_experiment.py), not directly
# comparable to Models 0-6's full 2021 test set on the same axis.


def plot_ablation_incremental(ablation: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for target, ax in zip(ablation.target.unique(), axes):
        d = ablation[ablation.target == target].set_index("model").reindex(MODEL_ORDER)
        x = range(len(d))
        ax.plot(x, d.roc_auc, marker="o", label="ROC-AUC")
        ax2 = ax.twinx()
        ax2.plot(x, d.brier_skill_score, marker="s", color="tab:orange", label="BSS")
        ax.set_xticks(list(x))
        ax.set_xticklabels(
            [m.replace("Model", "M").replace("_", "\n") for m in MODEL_ORDER],
            fontsize=7, rotation=0,
        )
        ax.set_ylabel("ROC-AUC")
        ax2.set_ylabel("Brier Skill Score")
        ax.set_title(target)
        ax.grid(alpha=0.3)
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="lower right")
    fig.suptitle("Ablation: incremental performance by feature group")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "ablation_incremental.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_year_robustness(year_df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.5))
    for target, ax in zip(year_df.target.unique(), axes):
        d = year_df[year_df.target == target]
        ax.bar(d.experiment, d.roc_auc, color="tab:blue", alpha=0.8)
        ax.set_ylabel("ROC-AUC")
        ax.set_title(target)
        ax.set_xticks(range(len(d)))
        ax.set_xticklabels(d.experiment, rotation=20, ha="right", fontsize=8)
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(0, 1)
    fig.suptitle("Robustness across years (chronological experiments)")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "year_robustness.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_lead_robustness(lead_df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for target, ax in zip(lead_df.target.unique(), axes):
        d = lead_df[lead_df.target == target].sort_values("lead_day")
        ax.plot(d.lead_day, d.roc_auc_baseline, marker="o", label="baseline")
        ax.plot(d.lead_day, d.roc_auc_phase2, marker="s", label="Phase 2 model")
        if "roc_auc_phase3" in d.columns:
            ax.plot(d.lead_day, d.roc_auc_phase3, marker="^", label="Phase 3 model")
        ax.set_xlabel("Lead day")
        ax.set_ylabel("ROC-AUC")
        ax.set_title(target)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle("ROC-AUC vs. forecast lead")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "lead_robustness_auc.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_lead_brier_bss(lead_df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for target, ax in zip(lead_df.target.unique(), axes):
        d = lead_df[lead_df.target == target].sort_values("lead_day")
        ax.plot(d.lead_day, d.brier_baseline, marker="o", label="baseline Brier")
        ax.plot(d.lead_day, d.brier_phase2, marker="s", label="Phase 2 Brier")
        ax.set_xlabel("Lead day")
        ax.set_ylabel("Brier score (lower is better)")
        ax.set_title(target)
        ax.legend(fontsize=8)
        ax.grid(alpha=0.3)
    fig.suptitle("Brier score vs. forecast lead")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "lead_robustness_brier.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_regional_robustness(region_df: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(14, 8))
    for target, ax in zip(region_df.target.unique(), axes):
        d = region_df[region_df.target == target].sort_values("roc_auc_phase2", ascending=True)
        ax.barh(d.region_v2, d.roc_auc_phase2, color="tab:blue", alpha=0.8)
        ax.set_xlabel("ROC-AUC (Phase 2 model)")
        ax.set_title(target)
        ax.tick_params(axis="y", labelsize=6)
        ax.grid(axis="x", alpha=0.3)
    fig.suptitle("Regional robustness - ROC-AUC by region (2021 holdout)")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "regional_robustness.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    ablation = pd.read_csv(os.path.join(OUT_DIR, "ablation_results.csv"))
    print(f"saved -> {plot_ablation_incremental(ablation)}")

    year_df = pd.read_csv(os.path.join(OUT_DIR, "year_robustness.csv"))
    print(f"saved -> {plot_year_robustness(year_df)}")

    lead_df = pd.read_csv(os.path.join(OUT_DIR, "lead_robustness.csv"))
    print(f"saved -> {plot_lead_robustness(lead_df)}")
    print(f"saved -> {plot_lead_brier_bss(lead_df)}")

    region_df = pd.read_csv(os.path.join(OUT_DIR, "regional_robustness.csv"))
    print(f"saved -> {plot_regional_robustness(region_df)}")


if __name__ == "__main__":
    main()
