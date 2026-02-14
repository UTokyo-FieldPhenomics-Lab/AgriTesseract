"""Tests for rename IDs boundary processing helpers."""

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

from src.utils.rename_ids.boundary import (
    align_boundary_crs,
    build_effective_mask,
    compute_boundary_axes,
)


def test_align_boundary_crs_converts_to_points_crs() -> None:
    """Boundary CRS should be converted to points CRS when different."""
    points_ll = gpd.GeoDataFrame(
        {"fid": [1, 2]},
        geometry=[Point(0.0, 0.0), Point(0.005, 0.005)],
        crs="EPSG:4326",
    )
    points_m = points_ll.to_crs("EPSG:3857")
    boundary_ll = gpd.GeoDataFrame(
        {"name": ["b"]},
        geometry=[
            Polygon([(-0.01, -0.01), (0.02, -0.01), (0.02, 0.02), (-0.01, -0.01)])
        ],
        crs="EPSG:4326",
    )
    _, boundary_aligned = align_boundary_crs(points_m, boundary_ll)
    assert boundary_aligned.crs == points_m.crs


def test_build_effective_mask_marks_inside_and_outside_points() -> None:
    """Effective mask should follow point-inside-boundary logic."""
    points_gdf = gpd.GeoDataFrame(
        {"fid": [1, 2, 3]},
        geometry=[Point(0.0, 0.0), Point(0.9, 0.9), Point(2.0, 2.0)],
        crs="EPSG:4326",
    )
    boundary_gdf = gpd.GeoDataFrame(
        {"name": ["b"]},
        geometry=[Polygon([(-0.5, -0.5), (1.5, -0.5), (1.5, 1.5), (-0.5, -0.5)])],
        crs="EPSG:4326",
    )
    mask_array = build_effective_mask(points_gdf, boundary_gdf)
    assert mask_array.dtype == np.bool_
    assert mask_array.tolist() == [True, True, False]


def test_boundary_helpers_raise_on_empty_boundary() -> None:
    """Boundary helper should raise clear error for empty boundary input."""
    points_gdf = gpd.GeoDataFrame(
        {"fid": [1]}, geometry=[Point(0.0, 0.0)], crs="EPSG:4326"
    )
    empty_boundary = gpd.GeoDataFrame({"name": []}, geometry=[], crs="EPSG:4326")
    try:
        build_effective_mask(points_gdf, empty_boundary)
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty boundary")
    try:
        compute_boundary_axes(empty_boundary)
    except ValueError as exc:
        assert "empty" in str(exc)
    else:
        raise AssertionError("Expected ValueError for empty boundary axes")
