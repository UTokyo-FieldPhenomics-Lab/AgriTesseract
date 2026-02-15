"""GeoPandas subplot generator behavior tests."""

from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from src.utils.subplot_generate.io import (
    generate_and_save_gdf,
    generate_subplots_gdf,
    load_boundary_gdf,
)


def _make_boundary_gdf() -> gpd.GeoDataFrame:
    """Create square boundary in EPSG:3857 coordinates."""
    polygon = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
    return gpd.GeoDataFrame({"id": [1]}, geometry=[polygon], crs="EPSG:3857")


def test_load_boundary_from_shp_returns_single_row_gdf(tmp_path: Path) -> None:
    """Boundary loader should return one-row GeoDataFrame."""
    source_gdf = _make_boundary_gdf()
    shp_path = tmp_path / "boundary.shp"
    source_gdf.to_file(shp_path)

    boundary_gdf = load_boundary_gdf(shp_path)
    assert len(boundary_gdf) == 1


def test_grid_generation_returns_four_polygons() -> None:
    """2x2 grid should produce four subplot polygons."""
    subplots_gdf = generate_subplots_gdf(
        boundary_gdf=_make_boundary_gdf(),
        mode_index=0,
        rows=2,
        cols=2,
        width=0.0,
        height=0.0,
        x_spacing=0.0,
        y_spacing=0.0,
        keep_mode="all",
    )
    assert len(subplots_gdf) == 4


def test_spacing_math_uses_expected_cell_size() -> None:
    """100m square with 2x2 and 10m spacing yields 45m cells."""
    subplots_gdf = generate_subplots_gdf(
        boundary_gdf=_make_boundary_gdf(),
        mode_index=0,
        rows=2,
        cols=2,
        width=0.0,
        height=0.0,
        x_spacing=10.0,
        y_spacing=10.0,
        keep_mode="all",
    )

    first_bounds = subplots_gdf.geometry.iloc[0].bounds
    cell_width = first_bounds[2] - first_bounds[0]
    cell_height = first_bounds[3] - first_bounds[1]
    assert cell_width == pytest.approx(45.0)
    assert cell_height == pytest.approx(45.0)


def test_output_shapefile_can_be_reread_by_geopandas(tmp_path: Path) -> None:
    """Saved subplot shapefile should be readable and CRS-preserved."""
    output_path = tmp_path / "subplot_result"
    saved_gdf = generate_and_save_gdf(
        boundary_gdf=_make_boundary_gdf(),
        mode_index=0,
        rows=2,
        cols=2,
        width=0.0,
        height=0.0,
        x_spacing=0.0,
        y_spacing=0.0,
        keep_mode="all",
        output_path=output_path,
    )
    reread_gdf = gpd.read_file(tmp_path / "subplot_result.shp")
    assert len(reread_gdf) == 4
    assert reread_gdf.crs == saved_gdf.crs
