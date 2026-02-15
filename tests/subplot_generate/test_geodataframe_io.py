"""Tests for GeoPandas-based subplot generation IO."""

from pathlib import Path

import geopandas as gpd
from shapely.geometry import Polygon

from src.utils.subplot_generate.io import (
    generate_and_save_gdf,
    load_boundary_gdf,
)


def test_load_boundary_gdf_reads_single_polygon(tmp_path: Path) -> None:
    """Boundary loader should return a one-row polygon GeoDataFrame."""
    poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
    src = gpd.GeoDataFrame({"id": [1]}, geometry=[poly], crs="EPSG:3857")
    shp_path = tmp_path / "boundary.shp"
    src.to_file(shp_path)

    boundary_gdf = load_boundary_gdf(shp_path)
    assert len(boundary_gdf) == 1
    assert boundary_gdf.geometry.iloc[0].geom_type in {"Polygon", "MultiPolygon"}


def test_generate_and_save_gdf_writes_shapefile(tmp_path: Path) -> None:
    """Generator should produce grid polygons and persist them as shapefile."""
    poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
    boundary_gdf = gpd.GeoDataFrame({"id": [1]}, geometry=[poly], crs="EPSG:3857")
    output_path = tmp_path / "subplots.shp"

    result = generate_and_save_gdf(
        boundary_gdf=boundary_gdf,
        mode_index=0,
        rows=2,
        cols=2,
        width=2.0,
        height=2.0,
        x_spacing=0.0,
        y_spacing=0.0,
        keep_mode="all",
        output_path=output_path,
    )
    assert len(result) == 4
    assert output_path.exists()
