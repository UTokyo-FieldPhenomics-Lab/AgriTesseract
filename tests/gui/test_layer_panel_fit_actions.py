"""Tests for layer panel fit-width/fit-height actions."""

from __future__ import annotations

from src.gui.components.layer_panel import LayerPanel


def test_fit_actions_emit_selected_layer_name(qtbot) -> None:
    """Layer panel fit actions should emit selected target layer."""
    panel = LayerPanel()
    qtbot.addWidget(panel)
    panel.add_layer("rename_points", "Vector")

    fit_x_calls: list[str] = []
    fit_y_calls: list[str] = []
    panel.sigFitLayerToX.connect(fit_x_calls.append)
    panel.sigFitLayerToY.connect(fit_y_calls.append)

    panel._fit_layer_width("rename_points")
    panel._fit_layer_height("rename_points")

    assert fit_x_calls == ["rename_points"]
    assert fit_y_calls == ["rename_points"]
