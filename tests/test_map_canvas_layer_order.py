"""Tests for map canvas layer ordering utilities."""

import pyqtgraph as pg

from src.gui.components.map_component import MapComponent
from src.gui.components.map_canvas import LayerBounds, MapCanvas
from src.gui.tabs.rename_ids import RenameTab


def _add_dummy_layer(canvas: MapCanvas, layer_name: str, z_value: float = 0.0) -> None:
    """Add in-memory layer entry for ordering tests."""
    curve_item = pg.PlotCurveItem(x=[0.0, 1.0], y=[0.0, 1.0])
    curve_item.setZValue(z_value)
    canvas.add_overlay_item(curve_item)
    canvas._layers[layer_name] = {
        "item": curve_item,
        "visible": True,
        "bounds": LayerBounds(0.0, 0.0, 1.0, 1.0),
    }
    canvas._layer_order.append(layer_name)


def test_ensure_layers_bottom_keeps_dom_group_at_end(qtbot) -> None:
    """DOM layers should be moved to the bottom of mixed layer stack."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)
    _add_dummy_layer(canvas, "points")
    _add_dummy_layer(canvas, "dom_old")
    _add_dummy_layer(canvas, "boundary")
    _add_dummy_layer(canvas, "dom_new")

    canvas.ensure_layers_bottom(["dom_new", "dom_old"])

    assert canvas.get_layer_names() == ["points", "boundary", "dom_new", "dom_old"]


def test_dedupe_layer_name_creates_incremental_suffix() -> None:
    """Duplicate DOM name should be resolved to unique suffixed name."""
    used_names = {"demo", "demo_1", "other"}

    unique_name = RenameTab._dedupe_layer_name("demo", used_names)

    assert unique_name == "demo_2"


def test_layer_panel_order_syncs_from_map_canvas(qtbot) -> None:
    """Layer panel order should follow map canvas order updates."""
    map_component = MapComponent()
    qtbot.addWidget(map_component)
    panel = map_component.layer_panel
    canvas = map_component.map_canvas
    panel.add_layer("points", "Vector")
    panel.add_layer("boundary", "Vector")
    panel.add_layer("dom", "Raster")

    canvas.update_layer_order(["points", "boundary", "dom"])

    assert panel.get_layer_order() == ["points", "boundary", "dom"]
