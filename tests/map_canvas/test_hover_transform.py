"""Tests for hover coordinate transform consistency."""

from __future__ import annotations

from PySide6.QtCore import QPoint

from src.gui.components.map_canvas import MapCanvas


def test_hover_uses_same_item_transform_as_click_path(qtbot) -> None:
    """Hover coordinates should be mapped through item-group transform."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)
    canvas._item_group.setRotation(-30.0)

    captured: list[tuple[float, float]] = []
    canvas.register_hover_handler(lambda x, y: captured.append((x, y)))

    scene_pos = canvas._plot_widget.mapToScene(QPoint(30, 30))
    view_pos = canvas._view_box.mapSceneToView(scene_pos)
    expected_item = canvas._item_group.mapFromParent(view_pos)

    canvas._on_mouse_moved((scene_pos,))

    assert len(captured) == 1
    assert captured[0][0] == expected_item.x()
    assert captured[0][1] == expected_item.y()
