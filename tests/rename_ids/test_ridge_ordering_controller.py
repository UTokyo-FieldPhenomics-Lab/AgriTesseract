"""Tests for ordering controller and tab ordering updates."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from src.gui.tabs.rename_ids import RenameTab
from src.utils.rename_ids.ridge_ordering_controller import RidgeOrderingController


class _FakeOrderingMapCanvas:
    """Minimal map-canvas double for ordering controller tests."""

    def __init__(self) -> None:
        self.layer_names: list[str] = ["rename_points"]
        self.add_calls: list[str] = []
        self.remove_calls: list[str] = []
        self.visibility_calls: list[tuple[str, bool]] = []

    def get_layer_names(self) -> list[str]:
        return list(self.layer_names)

    def remove_layer(self, layer_name: str) -> bool:
        self.remove_calls.append(layer_name)
        if layer_name in self.layer_names:
            self.layer_names.remove(layer_name)
        return True

    def add_point_layer(self, _data, layer_name: str, **_kwargs) -> bool:
        self.add_calls.append(layer_name)
        if layer_name not in self.layer_names:
            self.layer_names.append(layer_name)
        return True

    def set_layer_visibility(self, layer_name: str, visible: bool) -> None:
        self.visibility_calls.append((layer_name, visible))


def _build_points_gdf() -> gpd.GeoDataFrame:
    """Build test points that form two ridge groups and one ignored point."""
    return gpd.GeoDataFrame(
        {"fid": [1, 2, 3, 4, 5]},
        geometry=[
            Point(0.0, -2.1),
            Point(1.0, -1.9),
            Point(0.0, 2.1),
            Point(1.0, 1.9),
            Point(0.0, 7.0),
        ],
        crs="EPSG:3857",
    )


def test_ordering_controller_builds_result_and_colored_layers() -> None:
    """Controller should emit ridge result and draw stable color layers."""
    map_canvas = _FakeOrderingMapCanvas()
    controller = RidgeOrderingController(map_canvas=map_canvas)
    points_gdf = _build_points_gdf()
    payload = controller.update(
        points_gdf=points_gdf,
        effective_mask=np.asarray([True, True, True, True, True]),
        direction_vector=np.asarray([1.0, 0.0], dtype=np.float64),
        ridge_peaks=np.asarray([-2.0, 2.0], dtype=np.float64),
        params={
            "buffer": 0.8,
            "ransac_enabled": False,
            "residual": 10,
            "max_trials": 100,
        },
    )

    result_gdf = payload["ordering_result_gdf"]
    stats = payload["ordering_stats"]

    assert {"fid", "ridge_id", "is_inlier", "geometry"} <= set(result_gdf.columns)
    assert stats["total_points"] == 5
    assert stats["assigned_points"] == 4
    assert stats["ignored_points"] == 1
    assert "ordering_ridge_0" in map_canvas.add_calls
    assert "ordering_ridge_1" in map_canvas.add_calls
    assert "ordering_ridge_ignored" in map_canvas.add_calls
    assert ("rename_points", False) in map_canvas.visibility_calls


def test_ordering_params_update_triggers_tab_controller_and_outputs(qtbot) -> None:
    """Ordering debounce timeout should refresh ordering outputs and layers."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    points_gdf = _build_points_gdf()
    tab.set_input_bundle(
        {
            "points_gdf": points_gdf,
            "points_meta": {
                "source": "file",
                "id_field": "fid",
                "crs_wkt": "EPSG:3857",
                "source_tag": "test",
            },
            "effective_mask": np.asarray([True, True, True, True, True]),
            "dom_layers": [],
        }
    )
    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._last_ridge_payload = {
        "ridge_peaks": {
            "peak_x": np.asarray([-2.0, 2.0], dtype=np.float64),
        }
    }
    tab.spin_buffer.setValue(0.8)
    tab._pending_update_type = "ordering"
    tab._on_parameter_update_timeout()

    ordering_stats = tab._input_bundle.get("ordering_stats")
    assert isinstance(ordering_stats, dict)
    assert ordering_stats["assigned_points"] == 4
    assert ordering_stats["ignored_points"] == 1
    assert "ordering_result_gdf" in tab._input_bundle
    layer_names = tab.map_component.map_canvas.get_layer_names()
    assert "ordering_ridge_0" in layer_names
    assert "ordering_ridge_1" in layer_names
