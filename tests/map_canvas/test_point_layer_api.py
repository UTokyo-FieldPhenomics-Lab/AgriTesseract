"""Tests for MapCanvas point-layer API."""

import numpy as np

from src.gui.components.map_canvas import MapCanvas


def test_add_point_layer_with_color_sets_fill_and_border(qtbot) -> None:
    """Color should apply to both fill and border when overrides missing."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)

    ok = canvas.add_point_layer(
        np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=float),
        "pts",
        color="#FFAA00",
    )

    assert ok is True
    assert "pts" in canvas._layers
    item = canvas._layers["pts"]["item"]
    assert item.opts["pen"].color().name().lower() == "#ffaa00"
    assert item.opts["brush"].color().name().lower() == "#ffaa00"


def test_add_point_layer_explicit_fill_or_border_overrides_color(qtbot) -> None:
    """Explicit fill and border colors should override base color channels."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)

    ok = canvas.add_point_layer(
        np.asarray([[1.0, 2.0]], dtype=float),
        "pts",
        color="#FFAA00",
        fill_color="#00FF00",
        border_color="#0000FF",
    )

    assert ok is True
    item = canvas._layers["pts"]["item"]
    assert item.opts["pen"].color().name().lower() == "#0000ff"
    assert item.opts["brush"].color().name().lower() == "#00ff00"


def test_add_point_layer_replaces_existing_layer_without_duplicate_order(qtbot) -> None:
    """Replacing same-name point layer should keep order list deduplicated."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)
    canvas.add_point_layer(np.asarray([[0.0, 0.0]], dtype=float), "pts")
    canvas.add_point_layer(np.asarray([[1.0, 1.0]], dtype=float), "pts")

    assert canvas._layer_order.count("pts") == 1
