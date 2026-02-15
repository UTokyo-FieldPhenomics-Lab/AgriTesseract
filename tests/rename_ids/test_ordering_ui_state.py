"""Tests for ordering UI enabled-state and summary text."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from src.gui.tabs.rename_ids import RenameTab


def _build_points_bundle() -> dict:
    """Build minimal points bundle for ordering UI tests."""
    points_gdf = gpd.GeoDataFrame(
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
    return {
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


def _ordered_subset(layer_names: list[str], priority: list[str]) -> list[str]:
    """Return existing layers ordered by one priority list."""
    return [name for name in priority if name in layer_names]


def test_ordering_controls_disabled_without_ridge_peaks(qtbot) -> None:
    """Ordering controls should stay disabled before ridge peaks are available."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_points_bundle())

    assert tab.spin_buffer.isEnabled() is False
    assert tab.check_ransac.isEnabled() is False
    assert tab.spin_residual.isEnabled() is False
    assert tab.spin_trials.isEnabled() is False


def test_ordering_controls_enable_after_ridge_result_ready(qtbot) -> None:
    """Ordering controls should enable once ridge direction and peaks are present."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_points_bundle())
    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._last_ridge_payload = {
        "ridge_peaks": {
            "peak_x": np.asarray([-2.0, 2.0], dtype=np.float64),
        }
    }
    tab._refresh_ordering_ui_state()

    assert tab.spin_buffer.isEnabled() is True
    assert tab.check_ransac.isEnabled() is True


def test_ordering_stats_summary_text_updates_after_run(qtbot) -> None:
    """Ordering summary label should show assigned, ignored and total counts."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_points_bundle())
    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._last_ridge_payload = {
        "ridge_peaks": {
            "peak_x": np.asarray([-2.0, 2.0], dtype=np.float64),
        }
    }
    tab._refresh_ordering_ui_state()
    tab._run_ordering_diagnostics(tab._current_ordering_params())

    stats_text = tab.label_ordering_stats.text()
    assert "4" in stats_text
    assert "1" in stats_text
    assert "5" in stats_text


def test_ridge_update_does_not_run_ordering_while_not_in_ordering_tab(qtbot) -> None:
    """Ridge refresh should not execute ordering pipeline outside ordering tab."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_points_bundle())
    tab._set_ridge_direction_state(np.asarray([1.0, 0.0], dtype=np.float64), "x")

    tab._run_ridge_diagnostics(tab._current_ridge_params(), apply_focus=False)

    assert "ordering_result_gdf" not in tab._input_bundle
    assert "ordering_stats" not in tab._input_bundle


def test_switch_to_ordering_tab_triggers_ordering_run(qtbot) -> None:
    """Entering ordering tab should run ordering once when inputs are ready."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_points_bundle())
    tab._ridge_direction_vector_array = np.asarray([1.0, 0.0], dtype=np.float64)
    tab._last_ridge_payload = {
        "ridge_peaks": {
            "peak_x": np.asarray([-2.0, 2.0], dtype=np.float64),
        }
    }

    tab.stacked_widget.setCurrentIndex(2)

    assert "ordering_result_gdf" in tab._input_bundle
    assert "ordering_stats" in tab._input_bundle


def test_switch_ordering_to_ridge_toggles_layer_visibility_and_order(qtbot) -> None:
    """Switching tabs should keep deterministic layer order and visibility."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_points_bundle())
    tab._set_ridge_direction_state(np.asarray([1.0, 0.0], dtype=np.float64), "x")
    tab._last_ridge_payload = {
        "ridge_peaks": {
            "peak_x": np.asarray([-2.0, 2.0], dtype=np.float64),
        }
    }

    tab.stacked_widget.setCurrentIndex(2)
    ordering_order = tab.map_component.map_canvas.get_layer_names()
    assert ordering_order.index("ordering_points") < ordering_order.index(
        "rename_points"
    )
    if "ridge_detected_lines" in ordering_order:
        assert ordering_order.index("ordering_points") < ordering_order.index(
            "ridge_detected_lines"
        )
    if "ridge_direction" in ordering_order:
        assert ordering_order.index("ridge_detected_lines") < ordering_order.index(
            "ridge_direction"
        )

    tab.stacked_widget.setCurrentIndex(1)
    map_canvas = tab.map_component.map_canvas
    assert map_canvas._layers["ordering_points"]["visible"] is False
    assert map_canvas._layers["rename_points"]["visible"] is True
    ridge_order = map_canvas.get_layer_names()
    assert ridge_order.index("ordering_points") < ridge_order.index("rename_points")
    if "ridge_detected_lines" in ridge_order:
        assert ridge_order.index("ridge_detected_lines") < ridge_order.index(
            "ordering_points"
        )
