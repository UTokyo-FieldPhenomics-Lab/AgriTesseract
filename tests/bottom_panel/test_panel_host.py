"""Tests for bottom panel host behavior."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel

from src.gui.components.bottom_panel import BottomPanelHost
from src.gui.components.map_component import MapComponent


def test_panel_host_register_show_switch_hide_and_unregister(qtbot) -> None:
    """Panel host handles registration lifecycle and switching."""
    host = BottomPanelHost()
    qtbot.addWidget(host)

    panel_a = QLabel("A")
    panel_b = QLabel("B")

    assert host.register_panel("a", panel_a)
    assert host.register_panel("b", panel_b)
    assert not host.register_panel("a", QLabel("A2"))

    assert host.show_panel("a")
    assert host.isVisible()
    assert host.current_panel_name() == "a"

    assert host.show_panel("b")
    assert host.current_panel_name() == "b"

    host.hide_panel()
    assert host.current_panel_name() == "b"

    assert host.unregister_panel("a")
    assert not host.unregister_panel("missing")


def test_map_component_bottom_panel_default_collapsed_and_switch(qtbot) -> None:
    """Map component exposes bottom panel show/hide API."""
    component = MapComponent()
    qtbot.addWidget(component)

    diagnostics = QLabel("Diagnostics")
    component.bottom_panel_host.register_panel("ridge", diagnostics)

    _, collapsed_height, _ = component.v_splitter.sizes()
    assert collapsed_height > 0
    assert component.show_panel("ridge")
    _, expanded_height, _ = component.v_splitter.sizes()
    assert expanded_height > collapsed_height
    assert component.bottom_panel_host.current_panel_name() == "ridge"

    component.hide_panel()
    _, next_collapsed_height, _ = component.v_splitter.sizes()
    assert next_collapsed_height > 0
    assert next_collapsed_height < expanded_height


def test_drag_up_from_collapsed_restores_panel_content(qtbot) -> None:
    """Dragging panel up after auto-hide should restore stack content."""
    component = MapComponent()
    qtbot.addWidget(component)

    diagnostics = QLabel("Diagnostics")
    component.bottom_panel_host.register_panel("ridge", diagnostics)
    assert component.show_panel("ridge")

    component.hide_panel()
    map_height, _, status_height = component.v_splitter.sizes()
    component.v_splitter.setSizes([map_height - 80, 80, status_height])
    component._on_vertical_splitter_moved(0, 1)

    assert component.bottom_panel_host._stack.isHidden() is False
