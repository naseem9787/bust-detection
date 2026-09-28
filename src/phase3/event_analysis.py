"""
Phase 3 - K: event-level analysis, extending Phase 2's version with the
observed value and a confidence column. Events are still selected directly
from the 2021 test data (never from recalled news dates - see Phase 2's
event_analysis.py docstring for why), since that's the only period we have
genuinely out-of-sample model predictions for.

Usage:
    .venv/Scripts/python.exe -m src.phase3.event_analysis
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from ..phase1.dataset import build_phase1_dataset
from ..phase2.evaluate_model import load_split
from ..phase2.event_analysis import event_trajectory, find_events
from ..phase2.features import OUT_DIR as PHASE2_OUT_DIR
from ..phase2.features import TARGET_COLS

OUT_DIR = os.path.join("outputs", "phase3")
PLOT_DIR = os.path.join(OUT_DIR, "plots")
N_EVENTS_PER_TARGET = 4

OBS_COL = {"bust_precip_categorical": "obs_precip_mm", "bust_temp_hard": "obs_temp_c"}


def add_observed_values(trajectories: pd.DataFrame, target: str) -> pd.DataFrame:
    """Merge in the actual observed (truth) value for each event row, from
    Phase 1's dataset - for DISPLAY only, never as a model input (it's
    already excluded from FEATURE_COLS - see leakage_audit.csv)."""
    ds = build_phase1_dataset()
    obs_col = OBS_COL[target]
    truth = ds.df[["init_time", "lead_day", "latitude", "longitude", obs_col]].rename(
        columns={obs_col: "observed_value"}
    )
    merged = trajectories.merge(
        truth, on=["init_time", "lead_day", "latitude", "longitude"], how="left"
    )
    merged["confidence"] = 1.0 - merged["y_prob_lgbm"]
    return merged


def plot_events_with_observed(trajectories: pd.DataFrame, target: str) -> str:
    events = trajectories.drop_duplicates(["valid_time", "latitude", "longitude"])[
        ["valid_time", "region_v2", "latitude", "longitude"]
    ]
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for _, ev in events.iterrows():
        mask = (
            (trajectories.valid_time == ev.valid_time)
            & (trajectories.latitude == ev.latitude)
            & (trajectories.longitude == ev.longitude)
        )
        traj = trajectories[mask].sort_values("lead_day")
        label = f"{ev.region_v2}, {pd.Timestamp(ev.valid_time).date()}"
        axes[0].plot(traj.lead_day, traj.y_prob_lgbm * 100, marker="o", label=label)
        forecast_col = "fcst_precip_mm" if "precip" in target else "fcst_temp_c"
        axes[1].plot(traj.lead_day, traj[forecast_col], marker="s", label=label)
        axes[1].plot(
            traj.lead_day, traj.observed_value, linestyle="--", color="gray", alpha=0.5
        )
    axes[0].set_xlabel("Lead day")
    axes[0].set_ylabel("Predicted bust probability (%)")
    axes[0].set_title("Model probability vs. lead day")
    axes[0].invert_xaxis()
    axes[0].legend(fontsize=7)
    axes[0].grid(alpha=0.3)

    axes[1].set_xlabel("Lead day")
    axes[1].set_ylabel("Forecast value (dashed = observed)")
    axes[1].set_title(f"Forecast vs. observed - {target}")
    axes[1].invert_xaxis()
    axes[1].grid(alpha=0.3)

    fig.suptitle(f"Selected {target} events (2021)")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, f"event_analysis_{target}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    all_trajectories = []
    for target in TARGET_COLS:
        print(f"\n=== Phase 3 event analysis for {target} ===")
        _, test, _, _ = load_split(target)
        event_keys = find_events(test, target)
        if event_keys.empty:
            print("no qualifying events found - skipping")
            continue
        trajectories = event_trajectory(test, target, event_keys)
        trajectories["target"] = target
        trajectories = add_observed_values(trajectories, target)
        all_trajectories.append(trajectories)
        print(
            trajectories[
                ["valid_time", "region_v2", "lead_day", "fcst_precip_mm" if "precip" in target else "fcst_temp_c",
                 "observed_value", target, "y_prob_lgbm", "confidence"]
            ].to_string(index=False)
        )
        plot_path = plot_events_with_observed(trajectories, target)
        print(f"saved -> {plot_path}")

    if all_trajectories:
        out = pd.concat(all_trajectories, ignore_index=True)
        path = os.path.join(OUT_DIR, "event_analysis.csv")
        out.to_csv(path, index=False)
        print(f"\nsaved -> {path}")


if __name__ == "__main__":
    main()
