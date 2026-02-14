"""Tests for ridge state synchronization on layer deletion."""

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

from src.gui.tabs.rename_ids import RenameTab


def _build_bundle(with_boundary: bool) -> dict:
    """Build points bundle optionally including boundary fields."""
    points_gdf = gpd.GeoDataFrame(
        {"fid": [1, 2, 3]},
        geometry=[Point(0.0, 0.0), Point(1.0, 1.0), Point(2.0, 0.0)],
        crs="EPSG:4326",
    )
    bundle = {
        "points_gdf": points_gdf,
        "points_meta": {
            "source": "file",
            "id_field": "fid",
            "crs_wkt": "EPSG:4326",
            "source_tag": "test",
        },
        "effective_mask": np.asarray([True, True, True], dtype=np.bool_),
        "dom_layers": [],
    }
    if not with_boundary:
        return bundle
    boundary_gdf = gpd.GeoDataFrame(
        {"name": ["b"]},
        geometry=[Polygon([(-1, -1), (3, -1), (3, 2), (-1, -1)])],
        crs="EPSG:4326",
    )
    bundle["boundary_gdf"] = boundary_gdf
    bundle["boundary_axes"] = {
        "x_axis": np.asarray([1.0, 0.0], dtype=np.float64),
        "y_axis": np.asarray([0.0, 1.0], dtype=np.float64),
    }
    return bundle


def test_remove_boundary_layer_reverts_direction_to_manual_only(qtbot) -> None:
    """Deleting Boundary layer should keep only manual direction source."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    bundle = _build_bundle(with_boundary=True)
    tab.set_input_bundle(bundle)
    tab.map_component.map_canvas.add_vector_layer(bundle["boundary_gdf"], "Boundary")
    assert tab.combo_direction.count() == 5
    tab.map_component.map_canvas.remove_layer("Boundary")
    assert tab.combo_direction.count() == 1
    assert tab._current_direction_source() == "manual_draw"


def test_remove_points_layer_disables_ridge_controls(qtbot) -> None:
    """Deleting points layer should disable ridge controls."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_bundle(with_boundary=False))
    assert tab.combo_direction.isEnabled() is True
    tab.map_component.map_canvas.remove_layer("rename_points")
    assert tab.combo_direction.isEnabled() is False
    assert tab.btn_set_ridge_direction.isEnabled() is False
    assert tab.btn_focus_ridge.isEnabled() is False
