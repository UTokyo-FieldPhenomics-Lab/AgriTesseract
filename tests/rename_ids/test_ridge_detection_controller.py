"""Tests for ridge diagnostics controller."""

from __future__ import annotations

import numpy as np

from src.utils.rename_ids.ridge_detection_controller import (
    RidgeDetectionController,
    distance_m_to_peak_bins,
)


class _FakeFigurePanel:
    """Minimal figure panel double for controller tests."""

    def __init__(self) -> None:
        self.clear_count = 0
        self.curve_x = None
        self.curve_y = None
        self.peaks_x = None
        self.peaks_y = None
        self.x_range = None
        self.threshold = None
        self.y_range = None

    def clear(self) -> None:
        self.clear_count += 1

    def set_density_curve(self, x_bins: np.ndarray, counts: np.ndarray) -> None:
        self.curve_x = x_bins
        self.curve_y = counts

    def set_peaks(self, peak_x: np.ndarray, peak_h: np.ndarray) -> None:
        self.peaks_x = peak_x
        self.peaks_y = peak_h

    def set_x_range(self, x_min: float, x_max: float) -> None:
        self.x_range = (x_min, x_max)

    def set_threshold_line(self, value: float | None) -> None:
        self.threshold = value

    def set_y_range(self, y_min: float, y_max: float) -> None:
        self.y_range = (y_min, y_max)


class _FakeMapCanvas:
    """Minimal map canvas double for controller tests."""

    def __init__(self) -> None:
        self.remove_calls: list[str] = []
        self.add_calls: list[tuple[str, str, int]] = []

    def remove_layer(self, layer_name: str) -> bool:
        self.remove_calls.append(layer_name)
        return True

    def add_vector_layer(
        self,
        data,
        layer_name: str,
        color: str = "g",
        width: int = 2,
    ) -> bool:
        _ = data
        self.add_calls.append((layer_name, color, width))
        return True


def _build_points() -> np.ndarray:
    """Build synthetic points with two ridge-like bands."""
    return np.asarray(
        [
            [0.0, -2.0],
            [1.0, -2.1],
            [2.0, -1.9],
            [0.0, 2.0],
            [1.0, 2.1],
            [2.0, 1.9],
        ],
        dtype=np.float64,
    )


def test_controller_returns_payload_and_updates_overlay() -> None:
    """Controller should compute payload and refresh map overlay."""
    map_canvas = _FakeMapCanvas()
    figure_panel = _FakeFigurePanel()
    controller = RidgeDetectionController(
        map_canvas=map_canvas, figure_panel=figure_panel
    )

    payload = controller.update(
        effective_points_xy=_build_points(),
        direction_vector=np.asarray([1.0, 0.0], dtype=np.float64),
        strength_ratio=0.5,
        distance=1,
        height=2,
    )

    assert payload["ridge_density_profile"]["x_bins"].shape[0] > 0
    assert payload["ridge_peaks"]["peak_indices"].shape[0] > 0
    assert len(payload["ridge_lines_gdf"]) > 0
    assert map_canvas.remove_calls == ["ridge_detected_lines"]
    assert map_canvas.add_calls[0][0] == "ridge_detected_lines"
    assert figure_panel.curve_x is not None
    assert figure_panel.peaks_x is not None
    assert figure_panel.threshold == 2.0
    assert figure_panel.y_range is not None


def test_controller_replaces_overlay_layer_on_repeated_updates() -> None:
    """Each update should clear old layer then add new one."""
    map_canvas = _FakeMapCanvas()
    figure_panel = _FakeFigurePanel()
    controller = RidgeDetectionController(
        map_canvas=map_canvas, figure_panel=figure_panel
    )

    points = _build_points()
    controller.update(points, np.asarray([1.0, 0.0]), 0.5, 1, 2)
    controller.update(points, np.asarray([1.0, 0.0]), 0.5, 1, 2)

    assert map_canvas.remove_calls == ["ridge_detected_lines", "ridge_detected_lines"]
    assert len(map_canvas.add_calls) == 2


def test_controller_clears_when_direction_missing() -> None:
    """Missing direction should clear figure and remove overlay only."""
    map_canvas = _FakeMapCanvas()
    figure_panel = _FakeFigurePanel()
    controller = RidgeDetectionController(
        map_canvas=map_canvas, figure_panel=figure_panel
    )

    payload = controller.update(
        effective_points_xy=_build_points(),
        direction_vector=None,
        strength_ratio=1.0,
        distance=1,
        height=1,
    )

    assert payload["ridge_density_profile"]["x_bins"].shape == (0,)
    assert figure_panel.clear_count == 1
    assert map_canvas.remove_calls == ["ridge_detected_lines"]
    assert len(map_canvas.add_calls) == 0


def test_distance_m_to_peak_bins_supports_float_params() -> None:
    """Distance in meters should map to at least one histogram-bin step."""
    assert distance_m_to_peak_bins(distance_m=0.2, strength_ratio=1.0) == 1
    assert distance_m_to_peak_bins(distance_m=1.1, strength_ratio=0.5) == 3
