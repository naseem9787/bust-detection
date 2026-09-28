"""
Phase 3 - C deliverable: variable_inventory.md - exact documentation of the
new atmospheric variables added in Phase 3.

Usage:
    .venv/Scripts/python.exe -m src.phase3.variable_inventory
"""
from __future__ import annotations

import os

OUT_DIR = os.path.join("outputs", "phase3")

VARIABLES = [
    {
        "name": "10m_wind_speed",
        "priority": "1 - wind",
        "source_variable": "10m_wind_speed (HRES forecast store - already a derived magnitude in WeatherBench2, not computed here from u/v)",
        "units": "m/s",
        "pressure_level": "surface (10m) - no pressure level, hence no 13x chunk-bundling cost (see below)",
        "spatial_resolution": "1.5 degree (240x121 grid) - same grid as all Phase 0-2 variables, no regridding",
        "temporal_resolution": "6-hourly lead steps, same init cadence (00Z/12Z) as HRES. FULL JJAS 2018-2021 scale.",
        "transformation": "none - used as-is",
    },
    {
        "name": "specific_humidity",
        "priority": "2 - humidity/moisture",
        "source_variable": "specific_humidity @ 850hPa (classic low-level monsoon moisture-flux level)",
        "units": "g/kg (converted from kg/kg by x1000 for readability, matching the project's existing unit-conversion convention)",
        "pressure_level": "850 hPa",
        "spatial_resolution": "1.5 degree (240x121 grid)",
        "temporal_resolution": "6-hourly lead steps. PILOT WINDOW ONLY (2021-07-15..2021-08-04) - see the cost note below.",
        "transformation": "kg/kg -> g/kg (x1000)",
    },
    {
        "name": "geopotential",
        "priority": "3 - geopotential",
        "source_variable": "geopotential @ 500hPa (classic synoptic-scale pattern / trough-ridge indicator)",
        "units": "m (geopotential height, converted from geopotential in m^2/s^2 by dividing by standard gravity 9.80665)",
        "pressure_level": "500 hPa",
        "spatial_resolution": "1.5 degree (240x121 grid)",
        "temporal_resolution": "6-hourly lead steps. PILOT WINDOW ONLY (2021-07-15..2021-08-04) - see the cost note below.",
        "transformation": "geopotential (m^2/s^2) / 9.80665 -> geopotential height (m)",
    },
]

NOT_ADDED = [
    "u/v wind components at pressure levels (kept only the surface wind-speed magnitude, "
    "to avoid an explosion of near-duplicate directional features for a first pass)",
    "temperature/humidity/wind at OTHER pressure levels (only one representative level per "
    "variable was kept - 850hPa for moisture, 500hPa for geopotential - per the instruction "
    "to keep the feature set meteorologically interpretable, not exhaustive)",
    "vertical velocity, relative humidity, total cloud cover - available in the source stores "
    "but not prioritized for this pass (wind/humidity/geopotential were the explicit priorities)",
]


def render_markdown() -> str:
    lines = [
        "# Phase 3 Variable Inventory",
        "",
        "New atmospheric variables added on top of Phase 0-2's "
        "(total_precipitation_24hr, 2m_temperature, mean_sea_level_pressure), "
        "fetched via src/phase3/atmospheric_features.py at FULL JJAS 2018-2021 "
        "scale (deterministic HRES/ERA5 stores - no ensemble dimension, so "
        "full-scale fetch is affordable, unlike the ensemble pilot).",
        "",
        "| Variable | Priority | Source | Units | Pressure level | Spatial res. | Temporal res. | Transformation |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for v in VARIABLES:
        lines.append(
            f"| `{v['name']}` | {v['priority']} | {v['source_variable']} | {v['units']} | "
            f"{v['pressure_level']} | {v['spatial_resolution']} | {v['temporal_resolution']} | "
            f"{v['transformation']} |"
        )
    lines += [
        "",
        "## Cost discovery that shaped this scope",
        "",
        "`geopotential` and `specific_humidity` are chunked as "
        "`(1, 8, 13, 240, 121)` in the source store - ALL 13 pressure levels "
        "bundled per chunk, so `.sel(level=X)` does not reduce network bytes "
        "fetched. A naive full-JJAS-2018-2021 fetch of both projected to "
        "10+ hours and was stopped after ~30 minutes once this became clear "
        "(see outputs/phase3/ensemble_data_audit.md for the full account). "
        "`10m_wind_speed` has no level dimension and was NOT affected - it "
        "stays at full 4-season scale.",
        "",
        "## Deliberately not added this pass",
        "",
    ] + [f"- {n}" for n in NOT_ADDED]
    lines += [
        "",
        "## Truth (ERA5) equivalents",
        "",
        "Also fetched (data/raw/atmo_truth_*.nc) for potential future use "
        "(e.g. defining a wind- or moisture-based bust target), but NOT used "
        "as a model input anywhere in Phase 3 - only the FORECAST values feed "
        "the feature table, per the leakage rules (see "
        "outputs/phase3/feature_registry.csv).",
    ]
    return "\n".join(lines)


def main() -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "variable_inventory.md")
    with open(path, "w") as f:
        f.write(render_markdown())
    print(f"saved -> {path}")


if __name__ == "__main__":
    main()
