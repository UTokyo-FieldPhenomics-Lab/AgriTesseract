"""Tests for ridge-specific figure panel."""

from __future__ import annotations

import numpy as np

from src.gui.tabs.rename_ids import RidgeFigurePanel


def test_ridge_figure_panel_supports_density_and_peaks(qtbot) -> None:
    """Ridge panel inherits plotting APIs and updates x-range."""
    panel = RidgeFigurePanel()
    qtbot.addWidget(panel)

    x_bins = np.asarray([-2.0, 0.0, 2.0], dtype=np.float64)
    counts = np.asarray([1, 4, 1], dtype=np.int64)
    peak_x = np.asarray([0.0], dtype=np.float64)
    peak_h = np.asarray([4.0], dtype=np.float64)

    panel.set_density_curve(x_bins, counts)
    panel.set_peaks(peak_x, peak_h)
    panel.set_x_range(-2.0, 2.0)

    curve_x, curve_y = panel.curve_item.getData()
    peaks_x, peaks_y = panel.peaks_item.getData()
    x_range, _ = panel.plot_widget.viewRange()

    assert np.allclose(curve_x, x_bins)
    assert np.allclose(curve_y, counts)
    assert np.allclose(peaks_x, peak_x)
    assert np.allclose(peaks_y, peak_h)
    assert x_range[0] == -2.0
    assert x_range[1] == 2.0
