"""Tests for ridge mode exclusion and payload contract."""

import geopandas as gpd
import numpy as np
import pytest
from shapely.geometry import Point, Polygon

from src.gui.tabs import rename_ids
from src.gui.tabs.rename_ids import RenameTab


class _DummyButton:
    """Dummy message box button."""

    def setText(self, _text: str) -> None:
        """No-op setter."""


class _FakeMessageBox:
    """Fake MessageBox used for non-blocking tests."""

    def __init__(self, _title: str, _content: str, _parent=None) -> None:
        self.yesButton = _DummyButton()
        self.cancelButton = _DummyButton()

    def exec(self) -> bool:
        """Always return cancel."""
        return False


@pytest.fixture(autouse=True)
def _mock_rotation_messagebox(monkeypatch):
    """Patch MessageBox for all tests in this module."""
    monkeypatch.setattr(rename_ids, "MessageBox", _FakeMessageBox)


def _build_boundary_bundle() -> dict:
    """Build input bundle with boundary and effective mask."""
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


def test_manual_draw_mode_disables_edit_tools(qtbot) -> None:
    """Manual draw mode should disable add/move/delete tools."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    tab.btn_add.setChecked(True)
    tab._activate_manual_draw_mode()
    assert tab.btn_add.isEnabled() is False
    assert tab.btn_move.isEnabled() is False
    assert tab.btn_delete.isEnabled() is False


def test_ridge_payload_uses_source_vector_angle_contract(qtbot) -> None:
    """Ridge payload should use source/vector/angle instead of direction index."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    tab.combo_direction.setCurrentIndex(0)
    payload_list = []
    tab.sigRidgeParamsChanged.connect(payload_list.append)
    tab._pending_update_type = "ridge"
    tab._on_parameter_update_timeout()
    assert len(payload_list) == 1
    payload = payload_list[0]
    assert "direction_index" not in payload
    assert payload["ridge_direction_source"] == "boundary_x"
    assert payload["ridge_direction_vector"].shape == (2,)
    assert isinstance(payload["rotation_angle_deg"], float)
