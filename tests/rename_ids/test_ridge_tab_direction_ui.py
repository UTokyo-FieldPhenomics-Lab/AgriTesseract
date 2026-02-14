"""Tests for ridge direction UI controls in RenameTab."""

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

from src.gui.tabs.rename_ids import RenameTab


def _build_bundle(with_boundary: bool) -> dict:
    """Build minimal input bundle for ridge UI tests."""
    points_gdf = gpd.GeoDataFrame(
        {"fid": [1, 2]},
        geometry=[Point(0.0, 0.0), Point(1.0, 1.0)],
        crs="EPSG:4326",
    )
    bundle = {
        "points_gdf": points_gdf,
        "points_meta": {
            "source": "send_next",
            "id_field": "fid",
            "crs_wkt": "EPSG:4326",
            "source_tag": "test",
        },
        "effective_mask": np.asarray([True, True], dtype=np.bool_),
        "dom_layers": [],
    }
    if not with_boundary:
        return bundle
    boundary_gdf = gpd.GeoDataFrame(
        {"name": ["b"]},
        geometry=[Polygon([(-1, -1), (2, -1), (2, 2), (-1, -1)])],
        crs="EPSG:4326",
    )
    bundle["boundary_gdf"] = boundary_gdf
    bundle["boundary_axes"] = {
        "x_axis": np.asarray([1.0, 0.0], dtype=np.float64),
        "y_axis": np.asarray([0.0, 1.0], dtype=np.float64),
    }
    return bundle


def test_ridge_controls_are_disabled_when_points_not_loaded(qtbot) -> None:
    """Ridge controls should be disabled before points are loaded."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    assert tab.combo_direction.isEnabled() is False
    assert tab.btn_set_ridge_direction.isEnabled() is False
    assert tab.btn_focus_ridge.isEnabled() is False
    assert tab.spin_strength.isEnabled() is False
    assert tab.spin_distance.isEnabled() is False
    assert tab.spin_height.isEnabled() is False


def test_no_boundary_keeps_only_manual_draw_source(qtbot) -> None:
    """Direction source should only keep manual option without boundary."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_bundle(with_boundary=False))
    assert tab.combo_direction.count() == 1
    assert tab._current_direction_source() == "manual_draw"


def test_boundary_bundle_expands_direction_sources_to_five(qtbot) -> None:
    """Direction source should expose five options when boundary exists."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_bundle(with_boundary=True))
    assert tab.combo_direction.count() == 5


def test_click_set_direction_switches_combo_to_manual_draw(qtbot) -> None:
    """Clicking set-direction button should switch source to manual draw."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_bundle(with_boundary=True))
    tab.combo_direction.setCurrentIndex(0)
    tab.btn_set_ridge_direction.click()
    assert tab._current_direction_source() == "manual_draw"
