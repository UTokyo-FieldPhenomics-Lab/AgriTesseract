"""Tests for generic bottom panel figure."""

from __future__ import annotations

import numpy as np

from src.gui.components.bottom_panel import BottomPanelFigure


def test_figure_panel_refresh_and_clear(qtbot) -> None:
    """Figure panel updates curve, peaks, threshold and clear state."""
    panel = BottomPanelFigure()
    qtbot.addWidget(panel)

    x_bins = np.asarray([0.0, 1.0, 2.0], dtype=np.float64)
    counts = np.asarray([2, 5, 3], dtype=np.int64)
    peak_x = np.asarray([1.0], dtype=np.float64)
    peak_h = np.asarray([5.0], dtype=np.float64)

    panel.set_density_curve(x_bins, counts)
    panel.set_peaks(peak_x, peak_h)
    panel.set_threshold_line(4.0)
    panel.set_x_range(0.0, 2.0)

    curve_x, curve_y = panel.curve_item.getData()
    peaks_x, peaks_y = panel.peaks_item.getData()
    x_range, _ = panel.plot_widget.viewRange()

    assert np.allclose(curve_x, x_bins)
    assert np.allclose(curve_y, counts)
    assert np.allclose(peaks_x, peak_x)
    assert np.allclose(peaks_y, peak_h)
    assert panel.threshold_item is not None
    assert x_range[0] == 0.0
    assert x_range[1] == 2.0

    panel.clear()
    curve_x, curve_y = panel.curve_item.getData()
    peaks_x, peaks_y = panel.peaks_item.getData()

    assert curve_x is None
    assert curve_y is None
    assert peaks_x is None
    assert peaks_y is None
    assert panel.threshold_item is None
