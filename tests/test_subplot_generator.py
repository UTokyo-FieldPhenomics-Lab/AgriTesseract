"""
Test SubplotGenerator core logic.
"""

import sys
from pathlib import Path
import tempfile
import pytest
import geopandas as gpd
from shapely.geometry import Polygon

# Add src to path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

try:
    from src.core.subplot_generator import SubplotGenerator
except ImportError:
    # If package structure is different in test env
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from src.core.subplot_generator import SubplotGenerator


@pytest.fixture
def sample_boundary(tmp_path):
    """Create a sample rect boundary shapefile."""
    # 100x100 rect at 0,0
    poly = Polygon([(0, 0), (100, 0), (100, 100), (0, 100), (0, 0)])
    gdf = gpd.GeoDataFrame({'id': [1]}, geometry=[poly], crs="EPSG:3857")
    
    path = tmp_path / "boundary.shp"
    gdf.to_file(path)
    return str(path)


def test_generator_load(sample_boundary):
    generator = SubplotGenerator()
    gdf = generator.load_boundary(sample_boundary)
    assert gdf is not None
    assert len(gdf) == 1
    assert gdf.crs == "EPSG:3857"


def test_generate_grid(sample_boundary, tmp_path):
    generator = SubplotGenerator()
    gdf_bound = generator.load_boundary(sample_boundary)
    
    # 2x2 grid, no spacing
    # 100x100 -> cell 50x50
    out_path = tmp_path / "output.shp"
    
    result = generator.generate(
        gdf_bound, 
        rows=2, 
        cols=2, 
        x_space=0, 
        y_space=0, 
        output_path=str(out_path)
    )
    
    assert result is not None
    assert len(result) == 4
    
    # Check dimensions of first cell
    cell = result.geometry.iloc[0]
    minx, miny, maxx, maxy = cell.bounds
    assert (maxx - minx) == pytest.approx(50.0)
    assert (maxy - miny) == pytest.approx(50.0)
    
    # Check save
    assert out_path.exists()
    saved = gpd.read_file(out_path)
    assert len(saved) == 4


def test_generate_spacing(sample_boundary):
    generator = SubplotGenerator()
    gdf_bound = generator.load_boundary(sample_boundary)
    
    # 2x2 grid, 10m spacing
    # Available width = 100 - (1)*10 = 90
    # Cell width = 90 / 2 = 45
    
    result = generator.generate(
        gdf_bound, 
        rows=2, 
        cols=2, 
        x_space=10, 
        y_space=10
    )
    
    cell = result.geometry.iloc[0]
    minx, miny, maxx, maxy = cell.bounds
    assert (maxx - minx) == pytest.approx(45.0)
    assert (maxy - miny) == pytest.approx(45.0)
