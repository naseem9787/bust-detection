"""
Phase 2 - A4: predictive feature inventory.

Documents exactly what forecast-time information is available for Phase 2B
modeling, and - just as important - what is NOT available and why, so
nothing gets silently fabricated. See src/phase2/features.py for where
these are actually built.

Ensemble data check (done once, evidence recorded here, not re-run every
time this module runs - the check involved live network calls documented
in the project's working notes):
  - The WeatherBench2 bucket DOES list an `ifs_ens` (IFS ensemble) dataset
    folder, and chunk *data* objects exist under it
    (datasets/ifs_ens/2016-2024-240x121_equiangular_with_poles_conservative.zarr/...).
  - However, neither its per-variable `.zarray`/`.zattrs` metadata nor a
    root `.zgroup` are retrievable (direct HTTP -> 404; `xarray.open_zarr`
    -> GroupNotFoundError), the same failure mode Phase 0 hit and worked
    around for the ERA5 full-res store by switching to a different,
    properly-formed store - no equivalently well-formed ensemble store at
    matching resolution was found in the time available.
  - Per the "don't spend the whole night on one dependency" rule, this was
    time-boxed and NOT resolved tonight. Ensemble spread features are
    UNAVAILABLE this pass - not fabricated, exactly as Phase 1's Baseline C
    already documented. Revisiting this (e.g. via a different WB2 ensemble
    store, or fetching the ensemble members directly from ECMWF's own
    archive) is a reasonable Phase 3 task.

Usage:
    .venv/Scripts/python.exe -m src.phase2.feature_inventory
"""
from __future__ import annotations

import os

OUT_DIR = os.path.join("outputs", "phase2")

FEATURES = [
    # (name, category, description, available_now)
    ("fcst_precip_mm", "forecast state", "HRES forecast 24h precip, this row's lead day", True),
    ("fcst_temp_c", "forecast state", "HRES forecast 2m temperature", True),
    ("fcst_mslp_hpa", "forecast state", "HRES forecast mean sea level pressure", True),
    ("latitude", "spatial", "grid cell latitude", True),
    ("longitude", "spatial", "grid cell longitude", True),
    ("region_v2", "spatial", "Phase-2 full-coverage state/UT region (src/phase2/geography.py)", True),
    (
        "fcst_precip_anomaly_vs_domain_mean",
        "spatial structure",
        "this cell's forecast minus the domain-wide mean forecast at the same "
        "(init_time, lead_day) - a cheap, vectorized proxy for 'how unusual is "
        "this forecast relative to the broader pattern that day', computed "
        "from forecast data alone (no truth involved)",
        True,
    ),
    (
        "fcst_temp_anomaly_vs_domain_mean",
        "spatial structure",
        "same, for temperature",
        True,
    ),
    ("lead_day", "temporal", "forecast lead day (1-10)", True),
    ("month", "temporal", "calendar month of the valid date (6-9, JJAS)", True),
    (
        "precip_forecast_jump",
        "temporal - forecast evolution",
        "this forecast's precip minus the PREVIOUS day's forecast run for the "
        "SAME valid_time/grid-cell (i.e. lead_day+1 issued 24h earlier) - "
        "'did the model change its mind since yesterday's run', standard "
        "operational run-to-run consistency signal. Only defined for "
        "lead_day 1-9 and where the earlier run exists in the JJAS window.",
        True,
    ),
    ("temp_forecast_jump", "temporal - forecast evolution", "same, for temperature", True),
    (
        "hist_bust_rate_region_lead_month",
        "historical behaviour",
        "train-only-fit climatological rate of the TARGET label for this "
        "(region, lead_day, month) - i.e. Phase 1's Baseline A, fed in as a "
        "feature rather than used only as a standalone baseline",
        True,
    ),
    (
        "hist_mean_abs_error_region_lead_month",
        "historical behaviour",
        "train-only-fit mean |forecast error| for this (region, lead_day, "
        "month), for the same variable the target is defined on",
        True,
    ),
    ("ensemble_mean / ensemble_std / ensemble_spread", "ensemble", "SEE MODULE DOCSTRING", False),
    (
        "wind, humidity, geopotential height",
        "forecast state (not fetched)",
        "confirmed available in the source HRES zarr store (verified variable "
        "listing during Phase 0) but not downloaded into data/raw/ this pass - "
        "adding them means re-running fetch_data.py-style downloads for JJAS "
        "2018-2021, deferred to keep this pass modest per instructions",
        False,
    ),
]


def render_markdown() -> str:
    lines = [
        "# Phase 2 Feature Availability",
        "",
        "| Feature | Category | Available now | Description |",
        "|---|---|---|---|",
    ]
    for name, cat, desc, available in FEATURES:
        lines.append(f"| `{name}` | {cat} | {'YES' if available else 'NO'} | {desc} |")
    lines += [
        "",
        "## Ensemble data availability check",
        "",
        "See this module's docstring for the full account. Summary: the "
        "`ifs_ens` dataset exists in the WeatherBench2 bucket (chunk data "
        "confirmed present) but its zarr metadata could not be read via "
        "direct HTTP or `xarray.open_zarr` in the time available - the same "
        "'missing .zgroup' failure mode Phase 0 hit and worked around for "
        "ERA5 by using a different, well-formed store; no equivalent "
        "well-formed ensemble store was found tonight. Not fabricated - "
        "documented as unavailable, matching Phase 1's Baseline C.",
        "",
        "## Deferred (not fabricated, not modeled this pass)",
        "",
        "- Ensemble mean/std/spread/quantiles - blocked, see above.",
        "- Wind, humidity, geopotential height - available in the source "
        "store but not yet downloaded; would require extending "
        "`src/config.py VARIABLES` and re-running the Phase-0 fetch for "
        "JJAS 2018-2021, out of scope for tonight's modest first model.",
        "- Full neighbor-adjacency spatial gradients (as opposed to the "
        "cheap domain-mean-anomaly proxy actually used) - a reasonable "
        "next enhancement, not built tonight to keep scope modest.",
    ]
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "feature_availability.md")
    with open(path, "w") as f:
        f.write(render_markdown())
    print(f"saved -> {path}")


if __name__ == "__main__":
    main()
