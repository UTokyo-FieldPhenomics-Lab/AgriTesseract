"""Tests for rename IDs points input IO helpers."""

import geopandas as gpd
from shapely.geometry import Point, Polygon

from src.utils.rename_ids.io import normalize_input_points


def test_normalize_input_points_adds_missing_fid() -> None:
    """Normalize should add sequential fid when missing."""
    points_gdf = gpd.GeoDataFrame(
        {"score": [0.1, 0.9]},
        geometry=[Point(0, 0), Point(1, 1)],
        crs="EPSG:4326",
    )
    normalized_gdf, points_meta = normalize_input_points(points_gdf)
    assert normalized_gdf["fid"].tolist() == [0, 1]
    assert points_meta["id_field"] == "fid"


def test_normalize_input_points_rejects_non_point_geometry() -> None:
    """Normalize should reject non-point geometry rows."""
    bad_gdf = gpd.GeoDataFrame(
        {"fid": [1]},
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 0)])],
        crs="EPSG:4326",
    )
    try:
        normalize_input_points(bad_gdf)
    except ValueError as exc:
        assert "Point" in str(exc)
        return
    raise AssertionError("Expected ValueError for non-point geometry")


def test_normalize_input_points_sets_none_crs_wkt_when_missing() -> None:
    """Metadata should keep ``crs_wkt`` as None when CRS is missing."""
    points_gdf = gpd.GeoDataFrame({"fid": [10]}, geometry=[Point(2, 2)], crs=None)
    _, points_meta = normalize_input_points(points_gdf)
    assert points_meta["crs_wkt"] is None
