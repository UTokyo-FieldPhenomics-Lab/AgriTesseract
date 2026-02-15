"""Tests for ridge focus workflow (rotation + fit width)."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point, Polygon

from src.gui.tabs.rename_ids import RenameTab


def _build_boundary_bundle() -> dict:
    """Build minimal input bundle for ridge focus tests."""
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


def test_focus_ridge_executes_rotation_then_fit_width(qtbot) -> None:
    """Focus ridge should call map rotation and fit-width in order."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    tab._ridge_rotation_angle_deg = -90.0

    call_order: list[str] = []

    def _set_rotation(angle: float) -> None:
        _ = angle
        call_order.append("rotation")

    def _fit_layer_to_x(layer_name: str, padding: float = 0.05) -> bool:
        _ = layer_name
        _ = padding
        call_order.append("fit_x")
        return True

    tab.map_component.map_canvas.set_rotation = _set_rotation
    tab.map_component.map_canvas.fit_layer_to_x = _fit_layer_to_x

    tab._on_focus_ridge_clicked()

    assert call_order == ["rotation", "fit_x"]


def test_ridge_update_timeout_triggers_focus_workflow(qtbot) -> None:
    """Ridge debounce update should execute runtime focus flow."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    tab._ridge_direction_source = "boundary_x"
    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._ridge_rotation_angle_deg = -90.0

    fit_calls: list[tuple[str, float]] = []

    def _fit_layer_to_x(layer_name: str, padding: float = 0.05) -> bool:
        fit_calls.append((layer_name, padding))
        return True

    tab.map_component.map_canvas.fit_layer_to_x = _fit_layer_to_x
    tab._pending_update_type = "ridge"
    tab._on_parameter_update_timeout()

    assert fit_calls[-1][0] == "rename_points"


def test_focus_button_also_refreshes_ridge_panel(qtbot, monkeypatch) -> None:
    """Focus ridge click should re-run diagnostics for panel sync."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    tab._ridge_direction_source = "boundary_x"
    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._ridge_rotation_angle_deg = -90.0

    calls: list[dict] = []

    def _update(**kwargs):
        calls.append(kwargs)
        return {}

    monkeypatch.setattr(tab._ridge_controller, "update", _update)
    tab._on_focus_ridge_clicked()

    assert len(calls) == 1
