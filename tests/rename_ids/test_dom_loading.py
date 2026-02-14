"""Tests for RenameTab DOM loading behaviors."""

from pathlib import Path

from src.gui.tabs.rename_ids import RenameTab


def test_on_load_dom_ensures_new_dom_above_old_dom(qtbot, monkeypatch) -> None:
    """New DOM should be above old DOM within bottom DOM group."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    tab._dom_layers_cache = [{"name": "old_dom", "path": "/tmp/old/old_dom.tif"}]
    monkeypatch.setattr(
        "src.gui.tabs.rename_ids.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: (["/tmp/new/new_dom.tif"], "GeoTIFF"),
    )
    monkeypatch.setattr(tab, "_ask_dom_duplicate_action", lambda *_: "rename")
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "get_layer_names",
        lambda: ["rename_points", "Boundary", "old_dom"],
    )
    monkeypatch.setattr(tab.map_component.map_canvas, "rename_layer", lambda *_: True)
    monkeypatch.setattr(
        tab.map_component.map_canvas, "add_raster_layer", lambda *_: True
    )
    captured_order: list[str] = []
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "ensure_layers_bottom",
        lambda names: captured_order.extend(names),
    )
    tab._on_load_dom()
    assert captured_order == ["new_dom", "old_dom"]


def test_same_stem_diff_path_renames_existing_and_new(qtbot, monkeypatch) -> None:
    """Same filename in different folders should rename both layers."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    old_path = "/home/crest/d/field.tif"
    new_path = "/home/crest/e/field.tif"
    tab._dom_layers_cache = [{"name": "field", "path": old_path}]
    monkeypatch.setattr(
        "src.gui.tabs.rename_ids.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([new_path], "GeoTIFF"),
    )
    monkeypatch.setattr(tab, "_ask_dom_duplicate_action", lambda *_: "rename")
    monkeypatch.setattr(
        tab.map_component.map_canvas, "get_layer_names", lambda: ["field"]
    )
    rename_calls: list[tuple[str, str]] = []
    add_calls: list[str] = []
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "rename_layer",
        lambda old, new: rename_calls.append((old, new)) or True,
    )
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "add_raster_layer",
        lambda _path, name: add_calls.append(name) or True,
    )
    monkeypatch.setattr(
        tab.map_component.map_canvas, "ensure_layers_bottom", lambda *_: None
    )
    tab._on_load_dom()
    assert ("field", "field (.../d/...)") in rename_calls
    assert add_calls == ["field (.../e/...)"]


def test_on_load_dom_skips_exact_duplicate_when_policy_is_skip(
    qtbot,
    monkeypatch,
) -> None:
    """Exact duplicate paths should be skipped when user chooses skip."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    existing_path = str(Path("/tmp/dom/field.tif"))
    tab._dom_layers_cache = [{"name": "field", "path": existing_path}]
    monkeypatch.setattr(
        "src.gui.tabs.rename_ids.QFileDialog.getOpenFileNames",
        lambda *args, **kwargs: ([existing_path], "GeoTIFF"),
    )
    monkeypatch.setattr(tab, "_ask_dom_duplicate_action", lambda *_: "skip")
    monkeypatch.setattr(
        tab.map_component.map_canvas, "get_layer_names", lambda: ["field"]
    )
    monkeypatch.setattr(tab.map_component.map_canvas, "rename_layer", lambda *_: True)
    call_count = {"add": 0}
    monkeypatch.setattr(
        tab.map_component.map_canvas,
        "add_raster_layer",
        lambda *_: call_count.__setitem__("add", call_count["add"] + 1),
    )
    monkeypatch.setattr(
        tab.map_component.map_canvas, "ensure_layers_bottom", lambda *_: None
    )
    tab._on_load_dom()
    assert call_count["add"] == 0


def test_duplicate_action_uses_fluent_message_box(qtbot, monkeypatch) -> None:
    """Duplicate confirmation should use qfluentwidgets MessageBox API."""
    tab = RenameTab()
    qtbot.addWidget(tab)
    msg_call = {"title": "", "content": "", "yes": "", "cancel": ""}

    class _Button:
        def __init__(self) -> None:
            self.text = ""

        def setText(self, text: str) -> None:
            self.text = text

    class _MockMessageBox:
        def __init__(self, title: str, content: str, _parent: object) -> None:
            msg_call["title"] = title
            msg_call["content"] = content
            self.yesButton = _Button()
            self.cancelButton = _Button()

        def exec(self) -> bool:
            msg_call["yes"] = self.yesButton.text
            msg_call["cancel"] = self.cancelButton.text
            return True

    monkeypatch.setattr("src.gui.tabs.rename_ids.MessageBox", _MockMessageBox)
    action = tab._ask_dom_duplicate_action(["/tmp/dom/a.tif"])
    assert action == "skip"
    assert msg_call["title"] == "Duplicate DOM detected"
    assert msg_call["yes"] == "Skip duplicates"
    assert msg_call["cancel"] == "Load and rename"
