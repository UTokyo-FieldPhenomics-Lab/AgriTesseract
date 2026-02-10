"""Shapefile export helpers for seedling detection outputs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import shapefile


def _normalize_shp_base_path(path: str | Path) -> Path:
    """Normalize path to shapefile base path.

    Parameters
    ----------
    path : str | Path
        Input file path that may include ``.shp`` suffix.

    Returns
    -------
    pathlib.Path
        Base path without suffix.
    """
    path_obj = Path(path)
    if path_obj.suffix.lower() != ".shp":
        return path_obj
    return path_obj.with_suffix("")


def _write_prj(base_path: Path, crs_wkt: str | None) -> None:
    """Write PRJ file when CRS WKT text is provided."""
    if not crs_wkt:
        return
    prj_path = base_path.with_suffix(".prj")
    prj_path.write_text(crs_wkt, encoding="utf-8")


def save_point_shp(
    points_df: pd.DataFrame,
    out_path: str | Path,
    crs_wkt: str | None,
) -> None:
    """Save center points to shapefile.

    Parameters
    ----------
    points_df : pandas.DataFrame
        Point table with columns: ``fid, x, y, source, conf``.
    out_path : str | Path
        Output shapefile path or base path.
    crs_wkt : str | None
        CRS in WKT text for optional PRJ file.
    """
    base_path = _normalize_shp_base_path(out_path)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    with shapefile.Writer(str(base_path), shapeType=shapefile.POINT) as shp_writer:
        shp_writer.field("fid", "N", decimal=0)
        shp_writer.field("source", "C")
        shp_writer.field("conf", "F", decimal=6)
        for row in points_df.itertuples(index=False):
            shp_writer.point(float(row.x), float(row.y))
            shp_writer.record(int(row.fid), str(row.source), float(row.conf))
    _write_prj(base_path, crs_wkt)


def save_bbox_shp(
    bbox_df: pd.DataFrame,
    out_path: str | Path,
    crs_wkt: str | None,
) -> None:
    """Save bbox polygons to shapefile.

    Parameters
    ----------
    bbox_df : pandas.DataFrame
        Table with ``fid, xmin, ymin, xmax, ymax, score`` columns.
    out_path : str | Path
        Output shapefile path or base path.
    crs_wkt : str | None
        CRS in WKT text for optional PRJ file.
    """
    base_path = _normalize_shp_base_path(out_path)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    with shapefile.Writer(str(base_path), shapeType=shapefile.POLYGON) as shp_writer:
        shp_writer.field("fid", "N", decimal=0)
        shp_writer.field("score", "F", decimal=6)
        for row in bbox_df.itertuples(index=False):
            # coord_list shape: (5, 2) closed polygon.
            coord_list = [
                [float(row.xmin), float(row.ymin)],
                [float(row.xmax), float(row.ymin)],
                [float(row.xmax), float(row.ymax)],
                [float(row.xmin), float(row.ymax)],
                [float(row.xmin), float(row.ymin)],
            ]
            shp_writer.poly([coord_list])
            shp_writer.record(int(row.fid), float(row.score))
    _write_prj(base_path, crs_wkt)


def save_mask_polygon_shp(
    mask_df: pd.DataFrame,
    out_path: str | Path,
    crs_wkt: str | None,
) -> None:
    """Save mask polygons to shapefile.

    Parameters
    ----------
    mask_df : pandas.DataFrame
        Table with ``fid, score, polygon`` columns. Polygon is list of ``(x, y)``.
    out_path : str | Path
        Output shapefile path or base path.
    crs_wkt : str | None
        CRS in WKT text for optional PRJ file.
    """
    base_path = _normalize_shp_base_path(out_path)
    base_path.parent.mkdir(parents=True, exist_ok=True)
    with shapefile.Writer(str(base_path), shapeType=shapefile.POLYGON) as shp_writer:
        shp_writer.field("fid", "N", decimal=0)
        shp_writer.field("score", "F", decimal=6)
        for row in mask_df.itertuples(index=False):
            polygon_xy = [[float(x), float(y)] for x, y in row.polygon]
            if not polygon_xy:
                continue
            if polygon_xy[0] != polygon_xy[-1]:
                polygon_xy.append(polygon_xy[0])
            shp_writer.poly([polygon_xy])
            shp_writer.record(int(row.fid), float(row.score))
    _write_prj(base_path, crs_wkt)
