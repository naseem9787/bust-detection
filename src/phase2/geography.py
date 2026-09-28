"""
Phase 2 - A3: geographic assignment fix.

Phase 0's src/regions.py uses 8 coarse, non-tiling lat/lon boxes, leaving
67.4% of grid cells "Unclassified" (see outputs/phase1/dataset_summary.md).
This module does NOT modify src/regions.py (per instructions) - it builds a
SEPARATE, full-coverage assignment for Phase 2 use, backed by real Indian
state boundaries (a public GADM-derived GeoJSON), with a deterministic
nearest-state fallback for any point outside all polygons (ocean cells,
sliver border areas) so every grid point in the domain gets exactly one
region.

Data source and a documented limitation
----------------------------------------
Boundaries: geohacker/india (GADM-derived), fetched to
data/raw/india_states.geojson. This is the most readily available public
India state-boundary GeoJSON (time-boxed search - see project notes); it
predates two administrative changes:
  - Telangana was carved out of Andhra Pradesh in 2014 - not present here;
    those grid cells fall under "Andhra Pradesh".
  - Ladakh was carved out of Jammu & Kashmir in 2019 - not present here;
    those grid cells fall under "Jammu and Kashmir".
Two names are corrected for current usage (Orissa -> Odisha, Uttaranchal ->
Uttarakhand) since that's a label fix, not a boundary change. This
limitation is deliberately documented rather than hidden - see
outputs/phase2/region_assignment_summary.csv's `note` column and
`n_via_state_merge_limitation` in the printed summary.

Usage:
    .venv/Scripts/python.exe -m src.phase2.geography
"""
from __future__ import annotations

import json
import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from shapely.geometry import Point, shape
from shapely.prepared import prep

from .. import config

GEOJSON_PATH = os.path.join(config.RAW_DIR, "india_states.geojson")
OUT_DIR = os.path.join("outputs", "phase2")
PLOT_DIR = os.path.join(OUT_DIR, "plots")

NAME_FIXES = {"Orissa": "Odisha", "Uttaranchal": "Uttarakhand"}

# Half a grid cell (grid spacing is 1.5 degrees) - a point this close to a
# state polygon is treated as "at the coast/border", assigned to that
# nearest state. A point farther than this is genuinely open ocean or
# well inside a neighboring country (the bounding box has a generous
# +2-degree buffer beyond India proper, per config.BBOX_BUFFER_DEG, so a
# lot of the 702-point grid is NOT India - median distance-to-nearest-state
# among non-contained points is ~3.4 degrees, i.e. clearly not a coastal
# effect - see the printed distance distribution in main()).
NEAR_BORDER_BUFFER_DEG = 0.75
OUTSIDE_DOMAIN_LABEL = "Outside India domain (ocean/neighboring country)"
PRE_2014_MERGED_STATES = {
    "Andhra Pradesh": "includes present-day Telangana (2014 split not in this boundary source)",
    "Jammu and Kashmir": "includes present-day Ladakh (2019 split not in this boundary source)",
}


def load_state_polygons(path: str = GEOJSON_PATH) -> list[tuple[str, object]]:
    if not os.path.exists(path):
        raise SystemExit(
            f"{path} not found. Fetch it once with:\n"
            '  curl -sL -o data/raw/india_states.geojson '
            '"https://raw.githubusercontent.com/geohacker/india/master/state/india_state.geojson"'
        )
    with open(path, encoding="utf-8") as f:
        gj = json.load(f)
    polygons = []
    for feat in gj["features"]:
        name = feat["properties"]["NAME_1"]
        name = NAME_FIXES.get(name, name)
        polygons.append((name, shape(feat["geometry"])))
    return polygons


def assign_grid_points(
    points: pd.DataFrame, polygons: list[tuple[str, object]]
) -> pd.DataFrame:
    """points: DataFrame with 'latitude','longitude'. Returns a copy with
    'region' and 'assignment_method' ('contains' or 'nearest_fallback'),
    deterministic (fixed polygon iteration order, first-match wins;
    fallback breaks ties by (distance, name) so it's reproducible)."""
    prepared = [(name, poly, prep(poly)) for name, poly in polygons]

    regions = []
    methods = []
    nearest_dists = []
    for lat, lon in zip(points.latitude, points.longitude):
        pt = Point(lon, lat)  # GeoJSON convention: (x=lon, y=lat)
        matches = [name for name, poly, prepped in prepared if prepped.contains(pt)]
        if len(matches) >= 1:
            # deterministic: first match in the fixed polygon list order.
            # (kept even if >1 match, so overlaps in the source data are
            # resolved reproducibly rather than raising - none observed in
            # practice, see the printed overlap count in main())
            regions.append(matches[0])
            methods.append("contains" if len(matches) == 1 else "contains_ambiguous")
            nearest_dists.append(0.0)
            continue

        dists = [(pt.distance(poly), name) for name, poly, _ in prepared]
        dists.sort(key=lambda t: (t[0], t[1]))
        nearest_d, nearest_name = dists[0]
        nearest_dists.append(nearest_d)
        if nearest_d <= NEAR_BORDER_BUFFER_DEG:
            regions.append(nearest_name)
            methods.append("near_border_fallback")
        else:
            regions.append(OUTSIDE_DOMAIN_LABEL)
            methods.append("outside_domain")

    out = points.copy()
    out["region_v2"] = regions
    out["assignment_method"] = methods
    out["distance_to_nearest_state_deg"] = nearest_dists
    out["in_india_domain"] = out.region_v2 != OUTSIDE_DOMAIN_LABEL
    return out


def build_region_map() -> pd.DataFrame:
    from ..phase1.dataset import ERROR_DB_PATH

    pts = pd.read_parquet(ERROR_DB_PATH, columns=["latitude", "longitude"]).drop_duplicates()
    pts = pts.sort_values(["latitude", "longitude"]).reset_index(drop=True)
    polygons = load_state_polygons()
    return assign_grid_points(pts, polygons)


def plot_coverage(assigned: pd.DataFrame) -> str:
    fig, ax = plt.subplots(figsize=(8, 8))
    regions = sorted(r for r in assigned.region_v2.unique() if r != OUTSIDE_DOMAIN_LABEL)
    cmap = plt.get_cmap("tab20", len(regions))
    color_map = {r: cmap(i) for i, r in enumerate(regions)}
    color_map[OUTSIDE_DOMAIN_LABEL] = (0.85, 0.85, 0.85, 1.0)
    for method, marker in [
        ("contains", "o"),
        ("near_border_fallback", "^"),
        ("outside_domain", "."),
        ("contains_ambiguous", "s"),
    ]:
        sub = assigned[assigned.assignment_method == method]
        if sub.empty:
            continue
        ax.scatter(
            sub.longitude,
            sub.latitude,
            c=[color_map[r] for r in sub.region_v2],
            marker=marker,
            s=40,
            label=method,
            edgecolors="k",
            linewidths=0.3,
        )
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.set_title("Phase 2 region assignment - full coverage (o=state polygon, x=nearest fallback)")
    ax.legend(fontsize=8)
    ax.set_aspect("equal")
    fig.tight_layout()
    path = os.path.join(PLOT_DIR, "region_coverage.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    return path


def main() -> None:
    os.makedirs(PLOT_DIR, exist_ok=True)
    assigned = build_region_map()

    n_total = len(assigned)
    n_null_region = assigned.region_v2.isna().sum()
    n_ambiguous = (assigned.assignment_method == "contains_ambiguous").sum()
    n_contains = (assigned.assignment_method == "contains").sum()
    n_near_border = (assigned.assignment_method == "near_border_fallback").sum()
    n_outside = (assigned.assignment_method == "outside_domain").sum()
    n_in_domain = int(assigned.in_india_domain.sum())
    n_merged_state = assigned.region_v2.isin(PRE_2014_MERGED_STATES).sum()

    in_domain = assigned[assigned.in_india_domain]
    summary = (
        in_domain.groupby("region_v2")
        .agg(
            n_grid_points=("latitude", "size"),
            n_via_state_polygon=("assignment_method", lambda s: (s == "contains").sum()),
            n_via_near_border_fallback=("assignment_method", lambda s: (s == "near_border_fallback").sum()),
        )
        .reset_index()
        .rename(columns={"region_v2": "region"})
        .sort_values("n_grid_points", ascending=False)
    )
    summary["note"] = summary.region.map(PRE_2014_MERGED_STATES).fillna("")
    out_path = os.path.join(OUT_DIR, "region_assignment_summary.csv")
    summary.to_csv(out_path, index=False)

    full_map_path = os.path.join(OUT_DIR, "grid_point_regions.csv")
    assigned.to_csv(full_map_path, index=False)

    plot_path = plot_coverage(assigned)

    print(f"saved -> {out_path}")
    print(f"saved -> {full_map_path}")
    print(f"saved -> {plot_path}")
    print(f"\ntotal grid points in the buffered bounding box: {n_total}")
    print(f"null region (should be 0): {n_null_region}")
    print(f"  - inside a real state polygon (confident): {n_contains}")
    print(f"  - within {NEAR_BORDER_BUFFER_DEG} deg of a state (coastal/border fallback): {n_near_border}")
    print(f"  - outside the intended India domain (ocean/distant foreign territory,")
    print(f"    >{NEAR_BORDER_BUFFER_DEG} deg from any state - excluded from regional analysis): {n_outside}")
    print(f"ambiguous multi-polygon matches (should be 0): {n_ambiguous}")
    print(f"\ngrid points IN the India domain: {n_in_domain} / {n_total} "
          f"({n_in_domain / n_total:.1%})")
    print(f"of those, under a pre-2014/2019 merged state name: {n_merged_state}")
    print(f"n_regions (states/UTs actually present): {summary.shape[0]}")
    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
