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


def test_add_point_layer_supports_per_point_color_lists(qtbot) -> None:
    """Per-point fill and border color lists should apply per marker."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)

    ok = canvas.add_point_layer(
        np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=float),
        "pts",
        fill_color=["#ff0000", "#00ff00"],
        border_color=["#0000ff", "#ff00ff"],
    )

    assert ok is True
    item = canvas._layers["pts"]["item"]
    point_items = item.points()
    assert len(point_items) == 2
    assert point_items[0].brush().color().name().lower() == "#ff0000"
    assert point_items[1].brush().color().name().lower() == "#00ff00"
    assert point_items[0].pen().color().name().lower() == "#0000ff"
    assert point_items[1].pen().color().name().lower() == "#ff00ff"


def test_add_point_layer_rejects_invalid_color_list_length(qtbot) -> None:
    """Per-point color lists must match point count."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)

    ok = canvas.add_point_layer(
        np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=float),
        "pts",
        fill_color=["#ff0000"],
    )

    assert ok is False
    assert "pts" not in canvas._layers


def test_add_point_layer_accepts_rgba_tuple_as_single_color(qtbot) -> None:
    """RGBA tuple should be treated as one color, not per-point list."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)

    ok = canvas.add_point_layer(
        np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=float),
        "pts",
        fill_color=(255, 59, 48, 180),
        border_color="#ff3b30",
    )

    assert ok is True
    assert "pts" in canvas._layers
