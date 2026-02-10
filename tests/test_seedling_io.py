"""Tests for seedling shapefile I/O helpers."""

from pathlib import Path

import pandas as pd

from src.utils.seedling_io import (
    save_bbox_shp,
    save_mask_polygon_shp,
    save_point_shp,
)


def test_save_point_shp_writes_expected_sidecars(tmp_path: Path) -> None:
    """Point writer should write shp/shx/dbf sidecar files."""
    points_df = pd.DataFrame(
        {
            "fid": [0, 1],
            "x": [100.0, 101.5],
            "y": [200.0, 201.5],
            "source": ["sam3", "manual"],
            "conf": [0.8, 1.0],
        }
    )
    out_path = tmp_path / "points"

    save_point_shp(points_df, out_path, crs_wkt=None)

    assert (tmp_path / "points.shp").exists()
    assert (tmp_path / "points.shx").exists()
    assert (tmp_path / "points.dbf").exists()


def test_save_bbox_and_mask_shp_writes_files(tmp_path: Path) -> None:
    """BBox and polygon exporters should create shapefile datasets."""
    bbox_df = pd.DataFrame(
        {
            "fid": [0],
            "xmin": [0.0],
            "ymin": [0.0],
            "xmax": [10.0],
            "ymax": [6.0],
            "score": [0.95],
        }
    )
    mask_df = pd.DataFrame(
        {
            "fid": [0],
            "score": [0.95],
            "polygon": [[(0.0, 0.0), (10.0, 0.0), (10.0, 6.0), (0.0, 6.0)]],
        }
    )

    save_bbox_shp(bbox_df, tmp_path / "bbox", crs_wkt=None)
    save_mask_polygon_shp(mask_df, tmp_path / "mask", crs_wkt=None)

    assert (tmp_path / "bbox.shp").exists()
    assert (tmp_path / "mask.shp").exists()
