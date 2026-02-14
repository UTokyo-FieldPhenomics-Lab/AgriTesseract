"""Tests for manual draw interaction in RenameTab ridge direction flow."""

import numpy as np
from PySide6.QtCore import Qt
import geopandas as gpd
from shapely.geometry import Point, Polygon
import pytest

from src.gui.tabs import rename_ids
from src.gui.tabs.rename_ids import RenameTab


class _DummyButton:
    """Dummy dialog button."""

    def setText(self, _text: str) -> None:
        """No-op setter."""


class _FakeMessageBox:
    """Fake MessageBox that always cancels rotation."""

    def __init__(self, _title: str, _content: str, _parent=None) -> None:
        self.yesButton = _DummyButton()
        self.cancelButton = _DummyButton()

    def exec(self) -> bool:
        """Always return cancel in tests."""
        return False


@pytest.fixture(autouse=True)
def _mock_rotation_messagebox(monkeypatch):
    """Patch MessageBox to avoid blocking dialogs during tests."""
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
    assert tab._manual_fixed_arrow_item is None
    assert "ridge_direction" in tab.map_component.map_canvas._layers


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
    tab._set_direction_source_options(has_boundary=True)
    tab.combo_direction.setCurrentIndex(4)
    tab._activate_manual_draw_mode()
    tab._on_ridge_manual_click(1.0, 1.0, Qt.MouseButton.LeftButton)
    tab._on_ridge_manual_click(3.0, 1.0, Qt.MouseButton.LeftButton)
    tab.combo_direction.setCurrentIndex(0)
    assert tab._manual_start_point_array is None
    assert tab._manual_end_point_array is None
    assert tab._manual_direction_vector_array is None
    assert tab._manual_preview_line_item is None
    assert tab._manual_fixed_arrow_item is None


def test_boundary_source_builds_ridge_direction_multiline_layer(qtbot) -> None:
    """Selecting boundary source should build ridge_direction multiline layer."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    tab.combo_direction.setCurrentIndex(0)
    ridge_layer = tab.map_component.map_canvas._layers.get("ridge_direction")
    assert ridge_layer is not None
    ridge_gdf = ridge_layer["data"]
    geom = ridge_gdf.geometry.iloc[0]
    assert geom.geom_type == "MultiLineString"
    assert len(geom.geoms) == 3


def test_switch_boundary_to_manual_removes_boundary_ridge_layer(qtbot) -> None:
    """Switching from boundary source to manual should clear old ridge layer."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab.set_input_bundle(_build_boundary_bundle())
    tab.combo_direction.setCurrentIndex(0)
    assert "ridge_direction" in tab.map_component.map_canvas._layers
    tab.combo_direction.setCurrentIndex(4)
    assert "ridge_direction" not in tab.map_component.map_canvas._layers
