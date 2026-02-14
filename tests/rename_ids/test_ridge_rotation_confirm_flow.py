"""Tests for ridge rotation confirmation flow."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from src.gui.tabs import rename_ids
from src.gui.tabs.rename_ids import RenameTab


class _DummyButton:
    """Dummy dialog button."""

    def setText(self, _text: str) -> None:
        """No-op text setter."""


class _FakeMessageBox:
    """Fake MessageBox with fixed exec result."""

    exec_result = False

    def __init__(self, _title: str, _content: str, _parent=None) -> None:
        self.yesButton = _DummyButton()
        self.cancelButton = _DummyButton()

    def exec(self) -> bool:
        """Return configured result."""
        return self.exec_result


def _build_boundary_bundle() -> dict:
    """Build input bundle with valid boundary axes and effective mask."""
    points_gdf = gpd.GeoDataFrame(
        {"fid": [1, 2, 3, 4]},
        geometry=[
            Point(0.0, 0.0),
            Point(2.0, 0.0),
            Point(2.0, 2.0),
            Point(6.0, 6.0),
        ],
        crs="EPSG:4326",
    )
    boundary_gdf = gpd.GeoDataFrame(
        {"name": ["b"]},
        geometry=[Polygon([(-1, -1), (3, -1), (3, 3), (-1, -1)])],
        crs="EPSG:4326",
    )
    return {
        "points_gdf": points_gdf,
        "points_meta": {
            "source": "file",
            "id_field": "fid",
            "crs_wkt": "EPSG:4326",
            "source_tag": "test",
        },
        "boundary_gdf": boundary_gdf,
        "boundary_axes": {
            "x_axis": np.asarray([1.0, 0.0], dtype=np.float64),
            "y_axis": np.asarray([0.0, 1.0], dtype=np.float64),
        },
        "effective_mask": np.asarray([True, True, True, False], dtype=np.bool_),
        "dom_layers": [],
    }


def test_boundary_confirm_yes_applies_rotation(qtbot, monkeypatch) -> None:
    """Confirming dialog should apply map rotation immediately."""
    monkeypatch.setattr(rename_ids, "MessageBox", _FakeMessageBox)
    _FakeMessageBox.exec_result = True
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    called_angles = []
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "set_rotation",
        lambda angle: called_angles.append(float(angle)),
    )
    tab.combo_direction.setCurrentIndex(0)
    assert len(called_angles) == 1
    assert called_angles[0] == pytest.approx(-90.0)


def test_boundary_confirm_cancel_keeps_saved_rotation_only(qtbot, monkeypatch) -> None:
    """Canceling dialog should keep saved angle without applying rotation."""
    monkeypatch.setattr(rename_ids, "MessageBox", _FakeMessageBox)
    _FakeMessageBox.exec_result = False
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    called_angles = []
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "set_rotation",
        lambda angle: called_angles.append(float(angle)),
    )
    tab.combo_direction.setCurrentIndex(0)
    assert called_angles == []
    assert tab._ridge_rotation_angle_deg is not None


def test_focus_ridge_button_applies_saved_rotation(qtbot, monkeypatch) -> None:
    """Focus ridge button should apply stored rotation angle."""
    monkeypatch.setattr(rename_ids, "MessageBox", _FakeMessageBox)
    _FakeMessageBox.exec_result = False
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    called_angles = []
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "set_rotation",
        lambda angle: called_angles.append(float(angle)),
    )
    tab.combo_direction.setCurrentIndex(0)
    assert called_angles == []
    tab.btn_focus_ridge.click()
    assert len(called_angles) == 1
    assert called_angles[0] == pytest.approx(-90.0)
