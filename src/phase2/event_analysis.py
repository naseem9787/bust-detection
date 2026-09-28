"""
Phase 2 - B8: event-level analysis (exploratory only - no causal claims).

Rather than relying on recalled news event dates (a citation risk), events
here are selected DIRECTLY FROM THE 2021 TEST DATA: grid cells/valid-dates
where the target actually occurred (bust=1) AND where we have model
predictions across multiple lead days for that same valid date (i.e.
several different forecast issuances all targeting that date), so we can
show how the model's predicted probability evolved as the event approached -
"did confidence change before the event actually happened", the same
framing the SIH problem statement asks for.

Usage:
    .venv/Scripts/python.exe -m src.phase2.event_analysis
"""
from __future__ import annotations

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from .evaluate_model import load_split
from .features import OUT_DIR, TARGET_COLS

PLOT_DIR = os.path.join(OUT_DIR, "plots")
N_EVENTS_PER_TARGET = 4


def find_events(test: pd.DataFrame, target: str) -> pd.DataFrame:
    key_cols = ["valid_time", "region_v2", "latitude", "longitude"]
    occurred = test[test[target] == 1]
    # keep only (valid_time, grid cell) combos with a full or near-full
    # lead-day trajectory available, so the "did confidence change" plot is
    # meaningful rather than a single point
    counts = test.groupby(key_cols, observed=True).size().rename("n_lead_days")
    occurred = occurred.merge(counts.reset_index(), on=key_cols, how="left")
    candidates = occurred[occurred.n_lead_days >= 8]
    if candidates.empty:
        candidates = occurred  # fall back if the >=8 filter is too strict

    ranked = (
        candidates.groupby(key_cols, observed=True)["y_prob_lgbm"]
        .mean()
        .rename("mean_pred_prob")
        .reset_index()
        .sort_values("mean_pred_prob", ascending=False)
        .head(N_EVENTS_PER_TARGET)
    )
    return ranked[key_cols]


def event_trajectory(test: pd.DataFrame, target: str, event_keys: pd.DataFrame) -> pd.DataFrame:
    key_cols = ["valid_time", "region_v2", "latitude", "longitude"]
    merged = test.merge(event_keys, on=key_cols, how="inner")
    cols = key_cols + ["init_time", "lead_day", "fcst_precip_mm", "fcst_temp_c", target, "y_prob_lgbm"]
    return merged[cols].sort_values(key_cols + ["lead_day"])


def plot_events(trajectories: pd.DataFrame, target: str) -> str:
    events = trajectories.drop_duplicates(["valid_time", "latitude", "longitude"])[
        ["valid_time", "region_v2", "latitude", "longitude"]
    ]
    fig, ax = plt.subplots(figsize=(8, 5))
    for _, ev in events.iterrows():
        mask = (
            (trajectories.valid_time == ev.valid_time)
            & (trajectories.latitude == ev.latitude)
            & (trajectories.longitude == ev.longitude)
        )
        traj = trajectories[mask].sort_values("lead_day")
        label = f"{ev.region_v2}, {pd.Timestamp(ev.valid_time).date()}"
        ax.plot(traj.lead_day, traj.y_prob_lgbm * 100, marker="o", label=label)
    ax.set_xlabel("Lead day (forecast issued this many days before the event date)")
    ax.set_ylabel("Model-predicted bust probability (%)")
    ax.set_title(f"Predicted probability vs. lead day - selected {target} events (2021)")
    ax.invert_xaxis()
    ax.legend(fontsize=7)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, f"event_trajectories_{target}.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    all_trajectories = []
    for target in TARGET_COLS:
        print(f"\n=== events for {target} ===")
        _, test, _, _ = load_split(target)
        event_keys = find_events(test, target)
        if event_keys.empty:
            print("no qualifying events found (target too rare in this split) - skipping")
            continue
        trajectories = event_trajectory(test, target, event_keys)
        trajectories["target"] = target
        all_trajectories.append(trajectories)
        print(trajectories.to_string(index=False))
        plot_path = plot_events(trajectories, target)
        print(f"saved -> {plot_path}")

    if all_trajectories:
        out = pd.concat(all_trajectories, ignore_index=True)
        path = os.path.join(OUT_DIR, "event_level_analysis.csv")
        out.to_csv(path, index=False)
        print(f"\nsaved -> {path}")


if __name__ == "__main__":
    main()
