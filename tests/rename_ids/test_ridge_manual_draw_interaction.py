"""Tests for manual draw interaction in RenameTab ridge direction flow."""

import numpy as np
from PySide6.QtCore import Qt

from src.gui.tabs.rename_ids import RenameTab


def test_manual_draw_clicks_build_direction_vector(qtbot) -> None:
    """Two left clicks in manual mode should produce one unit direction vector."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab._activate_manual_draw_mode()
    tab._on_ridge_manual_click(10.0, 20.0, Qt.MouseButton.LeftButton)
    tab._on_ridge_manual_hover(13.0, 24.0)
    consumed = tab._on_ridge_manual_click(13.0, 24.0, Qt.MouseButton.LeftButton)
    assert consumed is True
    assert tab._manual_start_point_array is not None
    assert tab._manual_end_point_array is not None
    assert np.allclose(tab._manual_direction_vector_array, np.asarray([0.6, 0.8]))


def test_manual_draw_repeated_definition_overwrites_vector(qtbot) -> None:
    """A second two-click sequence should overwrite previous manual vector."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab._activate_manual_draw_mode()
    tab._on_ridge_manual_click(0.0, 0.0, Qt.MouseButton.LeftButton)
    tab._on_ridge_manual_click(0.0, 2.0, Qt.MouseButton.LeftButton)
    first_vec = tab._manual_direction_vector_array.copy()
    tab._on_ridge_manual_click(0.0, 0.0, Qt.MouseButton.LeftButton)
    tab._on_ridge_manual_click(2.0, 0.0, Qt.MouseButton.LeftButton)
    second_vec = tab._manual_direction_vector_array
    assert np.allclose(first_vec, np.asarray([0.0, 1.0]))
    assert np.allclose(second_vec, np.asarray([1.0, 0.0]))


def test_switch_manual_to_boundary_clears_manual_state(qtbot) -> None:
    """Switching source from manual draw to boundary should clear manual state."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.combo_direction.setCurrentIndex(4)
    tab._activate_manual_draw_mode()
    tab._on_ridge_manual_click(1.0, 1.0, Qt.MouseButton.LeftButton)
    tab._on_ridge_manual_click(3.0, 1.0, Qt.MouseButton.LeftButton)
    tab.combo_direction.setCurrentIndex(0)
    assert tab._manual_start_point_array is None
    assert tab._manual_end_point_array is None
    assert tab._manual_direction_vector_array is None
    assert tab._manual_preview_line_item is None
    assert tab._manual_fixed_line_item is None
