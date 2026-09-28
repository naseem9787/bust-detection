"""
Phase 1 - static plots for the Forecast Error Atlas. Matplotlib only (no
internet/tile dependency), saved as PNGs under outputs/phase1/plots/.

Note on the "regional error map": Phase 0's regions.py defines 8 coarse
lat/lon bounding boxes, not a real shapefile (see its docstring), so a true
choropleth map isn't meaningful yet. This plots a ranked bar chart per
region instead - accurate to what the data actually supports, and flagged
here rather than dressed up as a geographic map.

Usage:
    .venv/Scripts/python.exe -m src.phase1.plots
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .dataset import build_phase1_dataset
from .error_atlas import build_atlas

OUT_DIR = os.path.join("outputs", "phase1")
PLOT_DIR = os.path.join(OUT_DIR, "plots")


def plot_error_vs_lead(by_lead: pd.DataFrame) -> str:
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    axes[0].plot(by_lead.lead_day, by_lead.mae_precip_mm, marker="o", label="MAE")
    axes[0].plot(by_lead.lead_day, by_lead.rmse_precip_mm, marker="s", label="RMSE")
    axes[0].set_title("Precipitation error vs. lead day")
    axes[0].set_xlabel("Lead day")
    axes[0].set_ylabel("mm")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(by_lead.lead_day, by_lead.mae_temp_c, marker="o", color="tab:red", label="MAE")
    axes[1].plot(
        by_lead.lead_day, by_lead.rmse_temp_c, marker="s", color="tab:orange", label="RMSE"
    )
    axes[1].set_title("2m temperature error vs. lead day")
    axes[1].set_xlabel("Lead day")
    axes[1].set_ylabel("degC")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "error_vs_lead.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_bust_rate_vs_lead(bust_rate_by_lead: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.plot(bust_rate_by_lead.lead_day, bust_rate_by_lead.bust_rate * 100, marker="o")
    ax.set_title("Bust rate vs. lead day (JJAS 2018-2021)")
    ax.set_xlabel("Lead day")
    ax.set_ylabel("Bust rate (%)")
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "bust_rate_vs_lead.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_error_by_region(by_region: pd.DataFrame) -> str:
    d = by_region.sort_values("bust_rate", ascending=True)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.barh(d.region, d.bust_rate * 100, color="tab:blue")
    ax.set_xlabel("Bust rate (%)")
    ax.set_title("Bust rate by region (JJAS 2018-2021, 'Unclassified' grid cells excluded)")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "bust_rate_by_region.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_error_by_month(by_month: pd.DataFrame) -> str:
    order = ["Jun", "Jul", "Aug", "Sep"]
    d = by_month.set_index("month_name").reindex(order).reset_index()
    fig, ax1 = plt.subplots(figsize=(6, 4))
    ax1.bar(d.month_name, d.mae_precip_mm, color="tab:blue", alpha=0.7, label="Precip MAE (mm)")
    ax1.set_ylabel("Precip MAE (mm)", color="tab:blue")
    ax2 = ax1.twinx()
    ax2.plot(d.month_name, d.bust_rate * 100, color="tab:red", marker="o", label="Bust rate (%)")
    ax2.set_ylabel("Bust rate (%)", color="tab:red")
    ax1.set_title("Seasonal (within-JJAS) error and bust rate")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "error_by_month.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def plot_miss_vs_false_alarm(bust_rate_by_lead: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(6, 4))
    width = 0.35
    x = bust_rate_by_lead.lead_day
    ax.bar(
        x - width / 2,
        bust_rate_by_lead.heavy_rain_miss_rate * 100,
        width,
        label="Missed heavy-rain rate",
    )
    ax.bar(
        x + width / 2,
        bust_rate_by_lead.heavy_rain_false_alarm_rate * 100,
        width,
        label="False-alarm heavy-rain rate",
    )
    ax.set_xlabel("Lead day")
    ax.set_ylabel("Rate (%)")
    ax.set_title("Heavy-rain miss vs. false alarm, by lead day")
    ax.legend()
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "heavy_rain_miss_vs_false_alarm.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    ds = build_phase1_dataset()
    atlas = build_atlas(ds.df)

    paths = [
        plot_error_vs_lead(atlas["error_by_lead"]),
        plot_bust_rate_vs_lead(atlas["bust_rate_by_lead"]),
        plot_error_by_region(atlas["error_by_region"]),
        plot_error_by_month(atlas["error_by_month"]),
        plot_miss_vs_false_alarm(atlas["bust_rate_by_lead"]),
    ]
    for p in paths:
        print(f"saved -> {p}")


if __name__ == "__main__":
    main()
