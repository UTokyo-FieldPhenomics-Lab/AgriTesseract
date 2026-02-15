"""Tests for seedling-to-rename tab handoff logic."""

from __future__ import annotations

import numpy as np
from types import SimpleNamespace

from src.gui.components.map_canvas import MapCanvas
from src.gui.tabs.seedling_detect import SeedlingTab


class _SignalStub:
    """Minimal signal stub with emit recorder."""

    def __init__(self) -> None:
        self.payload_list: list[str] = []

    def emit(self, payload: str) -> None:
        """Record emitted payload for assertions."""
        self.payload_list.append(payload)


class _RenameTabStub:
    """Simple rename tab stub for handoff tests."""

    def __init__(self, fail_setter: bool = False) -> None:
        self.fail_setter = fail_setter
        self.bundle_payload: dict | None = None
        self.sigLoadShp = _SignalStub()

    def set_input_bundle(self, bundle: dict) -> None:
        """Store bundle or raise to trigger fallback path."""
        if self.fail_setter:
            raise RuntimeError("mock handoff failure")
        self.bundle_payload = bundle


def test_object_first_handoff_prefers_bundle_transfer() -> None:
    """Bundle handoff should call ``set_input_bundle`` before fallback."""
    seedling_tab = SeedlingTab.__new__(SeedlingTab)
    seedling_tab._last_export_points_path = "/tmp/export_points.shp"
    seedling_tab._build_rename_input_bundle = lambda: {"points_gdf": "dummy"}
    rename_tab = _RenameTabStub()

    is_object_handoff = SeedlingTab._handoff_bundle_or_fallback(
        seedling_tab, rename_tab
    )

    assert is_object_handoff is True
    assert rename_tab.bundle_payload == {"points_gdf": "dummy"}
    assert rename_tab.sigLoadShp.payload_list == []


def test_handoff_fallback_emits_shapefile_path_when_object_fails() -> None:
    """Fallback should emit shapefile path when object-first handoff fails."""
    seedling_tab = SeedlingTab.__new__(SeedlingTab)
    seedling_tab._last_export_points_path = "/tmp/export_points.shp"
    seedling_tab._build_rename_input_bundle = lambda: {"points_gdf": "dummy"}
    rename_tab = _RenameTabStub(fail_setter=True)

    is_object_handoff = SeedlingTab._handoff_bundle_or_fallback(
        seedling_tab, rename_tab
    )

    assert is_object_handoff is False
    assert rename_tab.sigLoadShp.payload_list == ["/tmp/export_points.shp"]


def test_build_rename_bundle_contains_required_fields() -> None:
    """Rename bundle builder should return contract fields for send-next."""
    seedling_tab = SeedlingTab.__new__(SeedlingTab)
    seedling_tab._last_full_result = {"merged": {"points_xy": np.array([[1.0, 2.0]])}}
    seedling_tab._boundary_gdf = None
    seedling_tab._dom_path = "/tmp/dom/demo.tif"
    seedling_tab._current_dom_crs_wkt = lambda: None

    bundle = SeedlingTab._build_rename_input_bundle(seedling_tab)

    assert bundle is not None
    assert bundle["points_meta"]["source"] == "send_next"
    assert bundle["dom_layers"] == [{"name": "demo", "path": "/tmp/dom/demo.tif"}]
    assert bundle["effective_mask"].tolist() == [True]


def test_copy_points_overlay_to_rename_tab_builds_red_result_layer(qtbot) -> None:
    """Fallback copy should register result_points with planned red style."""
    seedling_tab = SeedlingTab.__new__(SeedlingTab)
    seedling_tab._last_full_result = {
        "merged": {"points_xy": np.asarray([[1.0, 2.0], [4.0, 5.0]], dtype=float)}
    }
    rename_tab = SimpleNamespace(map_component=SimpleNamespace(map_canvas=MapCanvas()))
    qtbot.addWidget(rename_tab.map_component.map_canvas)

    SeedlingTab._copy_points_overlay_to_rename_tab(seedling_tab, rename_tab)

    layer_info = rename_tab.map_component.map_canvas._layers.get("result_points")
    assert layer_info is not None
    item = layer_info["item"]
    assert item.opts["pen"].color().name().lower() == "#ff3b30"
    assert item.opts["brush"].color().name().lower() == "#ff3b30"
