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
