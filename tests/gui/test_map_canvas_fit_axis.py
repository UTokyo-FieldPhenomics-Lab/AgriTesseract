"""Tests for map canvas single-axis fit APIs."""

from __future__ import annotations

import pyqtgraph as pg
import pytest

from src.gui.components.map_canvas import LayerBounds, MapCanvas


def _add_dummy_layer(canvas: MapCanvas, layer_name: str, bounds: LayerBounds) -> None:
    """Register one in-memory layer with explicit bounds."""
    curve_item = pg.PlotCurveItem(x=[0.0, 1.0], y=[0.0, 1.0])
    canvas.add_overlay_item(curve_item)
    canvas._layers[layer_name] = {
        "item": curve_item,
        "visible": True,
        "bounds": bounds,
    }
    canvas._layer_order.append(layer_name)


def test_fit_layer_to_x_preserves_aspect_ratio(qtbot) -> None:
    """Fit-width should keep view ratio and adjust y span accordingly."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)
    _add_dummy_layer(canvas, "points", LayerBounds(2.0, 3.0, 6.0, 9.0))
    canvas._view_box.setRange(xRange=(0.0, 10.0), yRange=(-5.0, 5.0), padding=0.0)

    before_x, before_y = canvas._view_box.viewRange()
    before_ratio = (before_x[1] - before_x[0]) / (before_y[1] - before_y[0])
    ok = canvas.fit_layer_to_x("points", padding=0.1)

    assert ok is True
    x_range, y_range = canvas._view_box.viewRange()
    after_ratio = (x_range[1] - x_range[0]) / (y_range[1] - y_range[0])
    assert x_range == pytest.approx([1.6, 6.4])
    assert after_ratio == pytest.approx(before_ratio)


def test_fit_layer_to_y_preserves_aspect_ratio(qtbot) -> None:
    """Fit-height should keep view ratio and adjust x span accordingly."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)
    _add_dummy_layer(canvas, "points", LayerBounds(2.0, 3.0, 6.0, 9.0))
    canvas._view_box.setRange(xRange=(0.0, 10.0), yRange=(-5.0, 5.0), padding=0.0)
    before_x, before_y = canvas._view_box.viewRange()
    before_ratio = (before_x[1] - before_x[0]) / (before_y[1] - before_y[0])

    ok = canvas.fit_layer_to_y("points", padding=0.25)

    assert ok is True
    x_range, y_range = canvas._view_box.viewRange()
    after_ratio = (x_range[1] - x_range[0]) / (y_range[1] - y_range[0])
    assert after_ratio == pytest.approx(before_ratio)
    assert y_range == pytest.approx([1.5, 10.5])


def test_fit_layer_to_axis_returns_false_when_layer_missing(qtbot) -> None:
    """Missing layer should return False for both axis-fit APIs."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)

    assert canvas.fit_layer_to_x("missing") is False
    assert canvas.fit_layer_to_y("missing") is False
