"""
Phase 0 regression tests.

No automated test suite existed before Phase 1 (Phase 0 was validated via a
manual smoke test documented in README.md). These are the first automated
tests, covering the pieces of Phase 0 that Phase 1 depends on and reuses
unchanged: region assignment, the bust-definition constants, and the IMD
rainfall-category helper.

Run:
    .venv/Scripts/python.exe -m pytest tests/ -v
"""
from __future__ import annotations

import pandas as pd

from src import config
from src.label_busts import _rain_category
from src.regions import REGIONS, UNCLASSIFIED, assign_region


def test_assign_region_known_point():
    # Bhopal, Madhya Pradesh - should land in Central India
    assert assign_region(23.25, 77.4) == "Central India (MP/Chhattisgarh/Vidarbha)"


def test_assign_region_ocean_point_is_unclassified():
    # Arabian Sea, well off the west coast
    assert assign_region(12.0, 68.0) == UNCLASSIFIED


def test_region_boxes_are_well_formed():
    for name, (lat_min, lat_max, lon_min, lon_max) in REGIONS.items():
        assert lat_min < lat_max, name
        assert lon_min < lon_max, name
        assert 0 <= lat_min and lat_max <= 90, name


def test_imd_rain_bins_cover_full_range_and_are_increasing():
    bins = config.IMD_RAIN_BINS
    assert bins == sorted(bins)
    assert bins[0] < 0  # so 0 mm falls inside the first bin, not on an edge
    assert bins[-1] == float("inf")
    assert len(config.IMD_RAIN_LABELS) == len(bins) - 1


def test_heavy_or_above_index_matches_label():
    assert config.IMD_RAIN_LABELS[config.HEAVY_OR_ABOVE_INDEX] == "heavy"


def test_rain_category_classifies_known_values():
    # one value comfortably inside each of the 6 IMD bins
    mm = pd.Series([0.0, 10.0, 50.0, 90.0, 150.0, 300.0])
    cats = _rain_category(mm)
    assert list(cats.astype(str)) == [
        "no_rain", "light", "moderate", "heavy", "very_heavy", "extremely_heavy",
    ]


def test_lead_days_match_lead_hours():
    assert config.LEAD_HOURS == [24 * d for d in config.LEAD_DAYS]
    assert config.LEAD_DAYS == list(range(1, 11))
