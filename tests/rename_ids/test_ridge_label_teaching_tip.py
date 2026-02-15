"""Tests for ridge parameter labels and flyout tips."""

from __future__ import annotations

from PySide6.QtCore import QEvent
from qfluentwidgets import BodyLabel

from src.gui.tabs import rename_ids
from src.gui.tabs.rename_ids import RenameTab
from src.gui.config import tr


def test_ridge_labels_use_recommended_names(qtbot) -> None:
    """Ridge command labels should use the new recommended names."""
    tab = RenameTab()
    qtbot.addWidget(tab)

    label_strength = tab.findChild(BodyLabel, "label_page_rename_label_strength")
    label_distance = tab.findChild(BodyLabel, "label_page_rename_label_distance")
    label_height = tab.findChild(BodyLabel, "label_page_rename_label_height")

    assert label_strength is not None
    assert label_distance is not None
    assert label_height is not None
    assert label_strength.text() == tr("page.rename.label.strength")
    assert label_distance.text() == tr("page.rename.label.distance")
    assert label_height.text() == tr("page.rename.label.height")


def test_click_on_ridge_label_shows_simple_flyout(qtbot, monkeypatch) -> None:
    """Clicking a ridge label should trigger simple flyout."""
    tab = RenameTab()
    qtbot.addWidget(tab)

    captured: list[dict] = []

    def _fake_create(**kwargs):
        captured.append(kwargs)

    class _DummyFlyout:
        @staticmethod
        def create(**kwargs):
            _fake_create(**kwargs)

    monkeypatch.setattr(rename_ids, "Flyout", _DummyFlyout, raising=False)

    label_strength = tab.findChild(BodyLabel, "label_page_rename_label_strength")
    assert label_strength is not None

    click_event = QEvent(QEvent.Type.MouseButtonPress)
    tab.eventFilter(label_strength, click_event)

    assert len(captured) == 1
    assert captured[0]["target"] == label_strength
