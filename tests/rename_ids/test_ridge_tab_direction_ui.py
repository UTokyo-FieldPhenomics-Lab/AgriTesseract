"""Tests for ridge direction UI controls in RenameTab."""

from src.gui.tabs.rename_ids import RenameTab


def test_ridge_direction_combo_has_five_sources(qtbot) -> None:
    """Ridge direction combo should provide five source options."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    assert tab.combo_direction.count() == 5


def test_click_set_direction_switches_combo_to_manual_draw(qtbot) -> None:
    """Clicking set-direction button should switch source to manual draw."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.combo_direction.setCurrentIndex(0)
    tab.btn_set_ridge_direction.click()
    assert tab.combo_direction.currentIndex() == 4
