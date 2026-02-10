"""Tests for seedling top-tab layout metadata."""

from src.gui.tabs.seedling_detect import seedling_top_tab_keys


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
