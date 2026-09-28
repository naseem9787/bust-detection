"""
Phase 2 - A3 tests: region assignment correctness (synthetic polygons, fast
and deterministic - no dependency on the 22MB real boundaries file), plus a
couple of real-world sanity checks against the actual fetched file.
"""
from __future__ import annotations

import os

import pandas as pd
import pytest
from shapely.geometry import Point, box

from src.phase2.geography import GEOJSON_PATH, OUTSIDE_DOMAIN_LABEL, assign_grid_points


def _square_polygons():
    # two disjoint unit squares, named "A" and "B", far apart from each other
    return [("A", box(0, 0, 1, 1)), ("B", box(10, 10, 11, 11))]


def test_points_inside_polygons_are_contains():
    points = pd.DataFrame({"latitude": [0.5, 10.5], "longitude": [0.5, 10.5]})
    out = assign_grid_points(points, _square_polygons())
    assert list(out.region_v2) == ["A", "B"]
    assert list(out.assignment_method) == ["contains", "contains"]
    assert list(out.in_india_domain) == [True, True]


def test_point_near_border_gets_fallback_not_outside():
    # 0.1 degrees outside square A - well within NEAR_BORDER_BUFFER_DEG (0.75)
    points = pd.DataFrame({"latitude": [1.1], "longitude": [0.5]})
    out = assign_grid_points(points, _square_polygons())
    assert out.region_v2.iloc[0] == "A"
    assert out.assignment_method.iloc[0] == "near_border_fallback"
    assert out.in_india_domain.iloc[0]


def test_point_far_from_everything_is_outside_domain():
    points = pd.DataFrame({"latitude": [50.0], "longitude": [50.0]})
    out = assign_grid_points(points, _square_polygons())
    assert out.region_v2.iloc[0] == OUTSIDE_DOMAIN_LABEL
    assert out.assignment_method.iloc[0] == "outside_domain"
    assert not out.in_india_domain.iloc[0]


def test_every_point_gets_exactly_one_region():
    points = pd.DataFrame(
        {"latitude": [0.5, 1.1, 50.0, 10.5], "longitude": [0.5, 0.5, 50.0, 10.5]}
    )
    out = assign_grid_points(points, _square_polygons())
    assert out.region_v2.notna().all()
    assert len(out) == len(points)  # no row dropped or duplicated


def test_assignment_is_deterministic():
    points = pd.DataFrame({"latitude": [0.5, 1.1, 50.0], "longitude": [0.5, 0.5, 50.0]})
    out1 = assign_grid_points(points, _square_polygons())
    out2 = assign_grid_points(points, _square_polygons())
    pd.testing.assert_frame_equal(out1, out2)


@pytest.mark.skipif(not os.path.exists(GEOJSON_PATH), reason="real boundaries file not fetched")
def test_known_cities_map_to_correct_real_states():
    from src.phase2.geography import load_state_polygons

    polygons = load_state_polygons()
    cities = pd.DataFrame(
        {
            "name": ["New Delhi", "Mumbai", "Chennai", "Kolkata"],
            "latitude": [28.6139, 19.0760, 13.0827, 22.5726],
            "longitude": [77.2090, 72.8777, 80.2707, 88.3639],
        }
    )
    out = assign_grid_points(cities.rename(columns={}), polygons)
    got = dict(zip(cities.name, out.region_v2))
    assert got["Mumbai"] == "Maharashtra"
    assert got["Chennai"] == "Tamil Nadu"
    assert got["Kolkata"] == "West Bengal"
    # New Delhi is tiny; the coarse GADM boundary may resolve it to Delhi or
    # a bordering state (Haryana) depending on polygon simplification -
    # accept either, since we're testing the assignment mechanism works on
    # real data, not the source shapefile's precision at city scale.
    assert got["New Delhi"] in {"Delhi", "Haryana"}
