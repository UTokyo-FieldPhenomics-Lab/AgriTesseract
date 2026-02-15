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
    assert not host.isVisible()

    assert host.unregister_panel("a")
    assert not host.unregister_panel("missing")


def test_map_component_bottom_panel_default_collapsed_and_switch(qtbot) -> None:
    """Map component exposes bottom panel show/hide API."""
    component = MapComponent()
    qtbot.addWidget(component)

    diagnostics = QLabel("Diagnostics")
    component.bottom_panel_host.register_panel("ridge", diagnostics)

    assert component.bottom_panel_host.isHidden()
    assert component.show_panel("ridge")
    assert not component.bottom_panel_host.isHidden()
    assert component.bottom_panel_host.current_panel_name() == "ridge"

    component.hide_panel()
    assert component.bottom_panel_host.isHidden()
