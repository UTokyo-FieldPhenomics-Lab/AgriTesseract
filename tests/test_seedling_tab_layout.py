"""Tests for seedling top-tab layout metadata."""

from src.gui.tabs.seedling_detect import seedling_top_tab_keys
from src.gui.tabs.seedling_detect import SeedlingTab


def test_seedling_top_tab_keys_include_five_sections() -> None:
    """Top tab config should expose five sections after split."""
    keys = seedling_top_tab_keys()
    assert len(keys) == 5
    assert keys == (
        "page.seedling.tab.file",
        "page.seedling.tab.sam3_params",
        "page.seedling.tab.sam3_preview",
        "page.seedling.tab.slice_infer",
        "page.seedling.tab.points",
    )


def test_start_inference_updates_status_progress() -> None:
    """Full inference slot should clamp and forward progress value."""

    class _StatusBar:
        def __init__(self) -> None:
            self.progress = -1

        def set_progress(self, value):
            self.progress = value

    class _MapComponent:
        def __init__(self) -> None:
            self.status_bar = _StatusBar()

    class _FakeTab:
        def __init__(self) -> None:
            self.map_component = _MapComponent()

    fake_tab = _FakeTab()
    SeedlingTab._on_full_inference_progress(fake_tab, 135)
    assert fake_tab.map_component.status_bar.progress == 100
