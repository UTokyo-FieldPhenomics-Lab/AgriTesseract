"""Tests for ridge parameter enable and bottom panel visibility rules."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

from src.gui.tabs.rename_ids import RenameTab


def _build_boundary_bundle() -> dict:
    """Build minimal bundle with points and boundary axes."""
    points_gdf = gpd.GeoDataFrame(
        {"fid": [1, 2, 3, 4]},
        geometry=[
            Point(0.0, 0.0),
            Point(2.0, 0.0),
            Point(2.0, 2.0),
            Point(6.0, 6.0),
        ],
        crs="EPSG:3857",
    )
    boundary_gdf = gpd.GeoDataFrame(
        {"name": ["b"]},
        geometry=[Polygon([(-1, -1), (3, -1), (3, 3), (-1, -1)])],
        crs="EPSG:3857",
    )
    return {
        "points_gdf": points_gdf,
        "points_meta": {
            "source": "file",
            "id_field": "fid",
            "crs_wkt": "EPSG:3857",
            "source_tag": "test",
        },
        "boundary_gdf": boundary_gdf,
        "boundary_axes": {
            "x_axis": np.asarray([1.0, 0.0], dtype=np.float64),
            "y_axis": np.asarray([0.0, 1.0], dtype=np.float64),
        },
        "effective_mask": np.asarray([True, True, True, False], dtype=np.bool_),
        "dom_layers": [],
    }


def test_ridge_params_disabled_until_direction_is_valid(qtbot) -> None:
    """Ridge numeric params should stay disabled before direction is resolved."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())

    assert tab.spin_strength.isEnabled() is False
    assert tab.spin_distance.isEnabled() is False
    assert tab.spin_height.isEnabled() is False

    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._refresh_ridge_ui_state()

    assert tab.spin_strength.isEnabled() is True
    assert tab.spin_distance.isEnabled() is True
    assert tab.spin_height.isEnabled() is True


def test_leaving_ridge_top_tab_auto_hides_bottom_panel(qtbot) -> None:
    """Bottom diagnostics panel should auto-hide when leaving ridge tab."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.show()
    tab.set_input_bundle(_build_boundary_bundle())
    tab.map_component.show_panel("ridge_figure")

    tab.stacked_widget.setCurrentIndex(2)

    assert tab.map_component.bottom_panel_host._stack.isHidden() is True


def test_hiding_rename_tab_auto_hides_bottom_panel(qtbot) -> None:
    """Switching away from Rename nav should hide bottom diagnostics panel."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.show()
    tab.set_input_bundle(_build_boundary_bundle())
    tab.map_component.show_panel("ridge_figure")

    tab.hide()
    qtbot.wait(10)

    assert tab.map_component.bottom_panel_host._stack.isHidden() is True


def test_returning_to_ridge_tab_auto_restores_bottom_panel(qtbot) -> None:
    """Re-entering ridge tab should restore diagnostics panel visibility."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.show()
    tab.set_input_bundle(_build_boundary_bundle())
    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._refresh_ridge_ui_state()

    tab.map_component.show_panel("ridge_figure")
    tab.stacked_widget.setCurrentIndex(2)
    assert tab.map_component.bottom_panel_host._stack.isHidden() is True

    tab.stacked_widget.setCurrentIndex(1)

    assert tab.map_component.bottom_panel_host._stack.isHidden() is False
