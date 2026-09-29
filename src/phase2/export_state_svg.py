"""
One-off script: converts the real GADM-derived India state boundaries
(data/raw/india_states.geojson - the same file src/phase2/geography.py uses
to assign region_v2) into lightweight SVG paths for the frontend map,
using the exact linear lon/lat -> pixel projection already implied by
frontend/src/data/indiaGeoData.js's hardcoded graticule lines:
  x = 18*lon - 1185
  y = -21*lat + 805
Only emits the 29 states that actually have real production grid points
(outputs/phase2/region_assignment_summary.csv) - the other 6 GADM features
(Chandigarh, Delhi, Puducherry, Dadra & Nagar Haveli, Daman & Diu,
Nagaland) never receive a real prediction in this 1.5-degree grid, so
they are NOT rendered as data-bearing regions (see project's own
"never fabricate" rule).
Output: frontend/src/data/indiaStatesGeo.js

Usage (from repo root):
    .venv/Scripts/python.exe -m src.phase2.export_state_svg
"""
import json
import os
import re

from shapely.geometry import shape
from shapely.ops import unary_union

NAME_FIXES = {"Orissa": "Odisha", "Uttaranchal": "Uttarakhand"}

with open("outputs/phase2/region_assignment_summary.csv", encoding="utf-8") as f:
    real_states = [line.split(",")[0].strip() for line in f.readlines()[1:] if line.strip()]

with open("data/raw/india_states.geojson", encoding="utf-8") as f:
    gj = json.load(f)

polys_by_name = {}
for feat in gj["features"]:
    name = NAME_FIXES.get(feat["properties"]["NAME_1"], feat["properties"]["NAME_1"])
    geom = shape(feat["geometry"])
    polys_by_name.setdefault(name, []).append(geom)

def slugify(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def project(lon, lat):
    x = 18 * lon - 1185
    y = -21 * lat + 805
    return x, y

def ring_to_path(coords):
    pts = [project(lon, lat) for lon, lat in coords]
    d = f"M {pts[0][0]:.1f},{pts[0][1]:.1f} " + " ".join(f"L {x:.1f},{y:.1f}" for x, y in pts[1:]) + " Z"
    return d

def geom_to_path(geom):
    parts = []
    polys = geom.geoms if geom.geom_type == "MultiPolygon" else [geom]
    for poly in polys:
        parts.append(ring_to_path(list(poly.exterior.coords)))
    return " ".join(parts)

missing = [s for s in real_states if s not in polys_by_name]
if missing:
    raise SystemExit(f"states with real production data but no polygon found: {missing}")

# Standard short codes for compact hover labels - display only, has no
# effect on the real region_v2 name used for data lookups.
SHORT_CODES = {
    "Rajasthan": "RJ", "Maharashtra": "MH", "Andhra Pradesh": "AP", "Madhya Pradesh": "MP",
    "Uttar Pradesh": "UP", "Gujarat": "GJ", "Arunachal Pradesh": "AR", "Jammu and Kashmir": "JK",
    "Andaman and Nicobar": "AN", "Karnataka": "KA", "Tamil Nadu": "TN", "Odisha": "OD",
    "Bihar": "BH", "West Bengal": "WB", "Chhattisgarh": "CG", "Uttarakhand": "UK",
    "Jharkhand": "JH", "Assam": "AS", "Lakshadweep": "LD", "Himachal Pradesh": "HP",
    "Kerala": "KL", "Mizoram": "MZ", "Haryana": "HR", "Manipur": "MN", "Meghalaya": "ML",
    "Tripura": "TR", "Punjab": "PB", "Goa": "GA", "Sikkim": "SK",
}

entries = []
for name in real_states:
    geom = unary_union(polys_by_name[name])
    simplified = geom.simplify(0.02, preserve_topology=True)
    if simplified.is_empty:
        simplified = geom
    path_d = geom_to_path(simplified)
    rep = geom.representative_point()
    lx, ly = project(rep.x, rep.y)
    minx, miny, maxx, maxy = geom.bounds  # lon_min, lat_min, lon_max, lat_max
    entries.append({
        "id": slugify(name),
        "name": name,
        "shortName": name,
        "shortCode": SHORT_CODES.get(name, name[:2].upper()),
        "svgPath": path_d,
        "labelPoint": {"x": round(lx, 1), "y": round(ly, 1)},
        "bbox": [round(minx, 2), round(miny, 2), round(maxx, 2), round(maxy, 2)],
        "centroid": [round(rep.x, 2), round(rep.y, 2)],
    })

js_entries = ",\n  ".join(
    "{\n"
    f'    id: {json.dumps(e["id"])},\n'
    f'    name: {json.dumps(e["name"])},\n'
    f'    shortName: {json.dumps(e["shortName"])},\n'
    f'    shortCode: {json.dumps(e["shortCode"])},\n'
    f'    svgPath: {json.dumps(e["svgPath"])},\n'
    f'    labelPoint: {{ x: {e["labelPoint"]["x"]}, y: {e["labelPoint"]["y"]} }},\n'
    f'    bbox: {json.dumps(e["bbox"])},\n'
    f'    centroid: {json.dumps(e["centroid"])},\n'
    "  }"
    for e in entries
)

out = f"""/**
 * Real India state/UT boundaries for the production 29-state geography
 * (region_v2 - see src/phase2/geography.py), generated from the actual
 * GADM-derived boundary file (data/raw/india_states.geojson) - the SAME
 * source the backend uses to assign every real grid point to a state.
 * NOT hand-drawn approximations.
 *
 * Projection matches the fixed lon/lat -> pixel mapping already used by
 * the map's graticule lines (frontend/src/components/forecast/IndiaRiskMap.jsx):
 *   x = 18*lon - 1185, y = -21*lat + 805
 *
 * Regenerate with: .venv/Scripts/python.exe -m src.phase2.export_state_svg
 * (repo root, needs data/raw/india_states.geojson - see
 * src/phase2/geography.py's fetch instructions if missing).
 *
 * Only the 29 states/UTs with real production grid points are included
 * (outputs/phase2/region_assignment_summary.csv). 6 small union
 * territories in the source boundary file (Chandigarh, Delhi, Puducherry,
 * Dadra & Nagar Haveli, Daman & Diu, Nagaland) never receive a real
 * prediction on this 1.5-degree grid and are intentionally omitted rather
 * than shown with fabricated data.
 */

export const INDIA_STATE_REGIONS = [
  {js_entries},
];
"""

with open("frontend/src/data/indiaStatesGeo.js", "w", encoding="utf-8") as f:
    f.write(out)

# Small metadata-only copy (id/name/bbox/centroid, no SVG paths) for the
# backend adapter (src/production/frontend_adapter.py) - same source of
# truth as the frontend geometry, so bbox/centroid never drift apart.
meta_only = [{k: e[k] for k in ("id", "name", "bbox", "centroid")} for e in entries]
with open(os.path.join("outputs", "phase2", "state_geo_meta.json"), "w", encoding="utf-8") as f:
    json.dump(meta_only, f, indent=2)

print(f"wrote {len(entries)} states to frontend/src/data/indiaStatesGeo.js")
print(f"wrote {len(entries)} states to outputs/phase2/state_geo_meta.json")
