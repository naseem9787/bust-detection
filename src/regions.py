"""
Coarse Indian meteorological regions, approximated as lat/lon bounding boxes.

Phase 0 has no shapefile dependency so it stays offline-friendly. These boxes
loosely follow IMD's homogeneous-region groupings and are good enough to
aggregate a 1.5-degree grid into a handful of interpretable regions.

Phase 1: replace `assign_region` with a proper point-in-polygon lookup against
the Survey of India / IMD state or meteorological-subdivision shapefile
(e.g. via geopandas + `naturalearth`/`bhuvan` boundaries), so region edges
are administratively/meteorologically exact rather than boxy.
"""
from __future__ import annotations

# name -> (lat_min, lat_max, lon_min, lon_max)
REGIONS: dict[str, tuple[float, float, float, float]] = {
    "Western Himalaya (J&K/HP/Uttarakhand)": (28.0, 36.0, 73.0, 81.0),
    "Northwest India (Punjab/Haryana/Rajasthan)": (24.0, 32.0, 69.0, 79.0),
    "Indo-Gangetic Plain (UP/Bihar)": (24.0, 30.0, 79.0, 88.0),
    "Northeast India": (22.0, 29.5, 88.0, 97.5),
    "Central India (MP/Chhattisgarh/Vidarbha)": (18.0, 26.0, 74.0, 84.0),
    "West Coast (Konkan/Goa/Kerala)": (8.0, 20.0, 72.0, 77.0),
    "East Coast (Andhra/Odisha/TN coast)": (8.0, 20.0, 78.0, 87.0),
    "South Peninsula (Interior Karnataka/TN)": (8.0, 16.0, 74.5, 80.0),
}

UNCLASSIFIED = "Unclassified"


def assign_region(lat: float, lon: float) -> str:
    """Return the first region box containing (lat, lon), else UNCLASSIFIED.

    Boxes are allowed to overlap slightly at their edges; the dict's
    insertion order decides precedence, which is fine for a coarse Phase-0
    aggregation.
    """
    for name, (lat_min, lat_max, lon_min, lon_max) in REGIONS.items():
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return name
    return UNCLASSIFIED
