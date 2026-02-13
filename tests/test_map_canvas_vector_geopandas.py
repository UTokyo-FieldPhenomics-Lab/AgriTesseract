"""MapCanvas vector loading tests with GeoPandas input."""

import geopandas as gpd
from shapely.geometry import Polygon

from src.gui.components.map_canvas import MapCanvas


def test_add_vector_layer_accepts_geodataframe(qtbot) -> None:
    """Map canvas should ingest a boundary GeoDataFrame directly."""
    canvas = MapCanvas()
    qtbot.addWidget(canvas)
    boundary_gdf = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Polygon([(0, 0), (1, 0), (1, 1), (0, 1), (0, 0)])],
        crs="EPSG:3857",
    )

    assert canvas.add_vector_layer(boundary_gdf, "Boundary")
