"""Tests for ridge ordering core helpers."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from src.utils.rename_ids.ridge_ordering import (
    assign_points_to_ridges,
    build_ordering_result,
    build_ridge_intervals,
)


def _build_points(values: list[tuple[int, float, float]]) -> gpd.GeoDataFrame:
    """Build test GeoDataFrame from ``(fid, x, y)`` rows.

    Parameters
    ----------
    values : list[tuple[int, float, float]]
        Input rows where each tuple stores ``fid``, ``x`` and ``y``.

    Returns
    -------
    geopandas.GeoDataFrame
        Point table with ``fid`` and ``geometry`` columns.
    """
    return gpd.GeoDataFrame(
        {"fid": [row[0] for row in values]},
        geometry=[Point(row[1], row[2]) for row in values],
        crs="EPSG:3857",
    )


def test_build_ordering_result_handles_empty_input() -> None:
    """Empty points keep a valid empty ordering result schema."""
    points_gdf = _build_points([])
    result_gdf = build_ordering_result(
        points_gdf=points_gdf,
        ridge_id=np.asarray([], dtype=np.int64),
        is_inlier=np.asarray([], dtype=bool),
    )

    assert list(result_gdf.columns) == ["fid", "ridge_id", "is_inlier", "geometry"]
    assert len(result_gdf) == 0


def test_single_ridge_assignment_returns_zero_index() -> None:
    """Single ridge should absorb all effective points inside interval."""
    ridge_intervals = build_ridge_intervals(np.asarray([0.0]), buffer=0.5)
    ridge_id, is_inlier = assign_points_to_ridges(
        projected_x=np.asarray([-0.2, 0.0, 0.3]),
        effective_mask=np.asarray([True, True, True]),
        ridge_intervals=ridge_intervals,
    )

    assert np.all(ridge_id == 0)
    assert np.all(is_inlier)


def test_multi_ridge_assignment_uses_nearest_interval() -> None:
    """Multiple ridge intervals should map points to correct ridge IDs."""
    ridge_intervals = build_ridge_intervals(np.asarray([-2.0, 2.0]), buffer=0.5)
    ridge_id, is_inlier = assign_points_to_ridges(
        projected_x=np.asarray([-2.1, -1.8, 1.9, 2.2]),
        effective_mask=np.asarray([True, True, True, True]),
        ridge_intervals=ridge_intervals,
    )

    assert np.all(ridge_id == np.asarray([0, 0, 1, 1]))
    assert np.all(is_inlier)


def test_ignored_rule_keeps_ridge_minus_one_and_non_inlier() -> None:
    """Ignored points must be marked as ``ridge_id=-1`` and ``is_inlier=False``."""
    ridge_intervals = build_ridge_intervals(np.asarray([0.0]), buffer=0.2)
    ridge_id, is_inlier = assign_points_to_ridges(
        projected_x=np.asarray([0.0, 1.0]),
        effective_mask=np.asarray([True, False]),
        ridge_intervals=ridge_intervals,
    )

    assert int(ridge_id[0]) == 0
    assert bool(is_inlier[0]) is True
    assert int(ridge_id[1]) == -1
    assert bool(is_inlier[1]) is False
