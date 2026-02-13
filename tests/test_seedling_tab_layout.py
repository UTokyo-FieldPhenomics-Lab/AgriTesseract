"""Tests for seedling top-tab layout metadata."""

import geopandas as gpd
from shapely.geometry import Polygon

from src.gui.tabs.seedling_detect import SeedlingTab, seedling_top_tab_keys


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


def test_get_boundary_xy_reads_geodataframe_polygon() -> None:
    """Boundary XY helper should read first geometry from GeoDataFrame."""
    seedling_tab = SeedlingTab.__new__(SeedlingTab)
    seedling_tab._boundary_gdf = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Polygon([(0, 0), (2, 0), (2, 1), (0, 1), (0, 0)])],
        crs="EPSG:3857",
    )

    boundary_xy = SeedlingTab._get_boundary_xy(seedling_tab)
    assert boundary_xy is not None
    assert boundary_xy[0] == [0.0, 0.0]
    assert boundary_xy[2] == [2.0, 1.0]
