"""GeoPandas helpers for subplot generation workflow."""

from __future__ import annotations

import math
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.geometry import Polygon

VALID_KEEP_MODES = ("all", "touch", "inside")


def _normalize_shp_output_path(output_path: str | Path) -> Path:
    """Normalize output path and enforce ``.shp`` suffix.

    Parameters
    ----------
    output_path : str | Path
        User-provided output file path.

    Returns
    -------
    pathlib.Path
        Path with ``.shp`` extension.
    """
    path_obj = Path(output_path)
    if path_obj.suffix.lower() == ".shp":
        return path_obj
    return path_obj.with_suffix(".shp")


def _validate_keep_mode(keep_mode: str) -> None:
    """Validate keep mode value.

    Parameters
    ----------
    keep_mode : str
        Keep filter mode in {"all", "touch", "inside"}.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        Raised when mode value is unsupported.
    """
    if keep_mode in VALID_KEEP_MODES:
        return
    raise ValueError(f"Unsupported keep mode: {keep_mode}")


def _validate_boundary_gdf(boundary_gdf: gpd.GeoDataFrame) -> None:
    """Validate boundary GeoDataFrame shape and geometry types.

    Parameters
    ----------
    boundary_gdf : geopandas.GeoDataFrame
        Boundary data expected to contain exactly one row.

    Returns
    -------
    None

    Raises
    ------
    ValueError
        Raised when boundary is empty, multi-row, or non-polygon.
    """
    if len(boundary_gdf) != 1:
        raise ValueError(
            f"Boundary must contain exactly one polygon, got {len(boundary_gdf)}"
        )

    geom = boundary_gdf.geometry.iloc[0]
    if geom.geom_type in {"Polygon", "MultiPolygon"}:
        return
    raise ValueError(f"Boundary geometry must be polygon-like, got {geom.geom_type}")


def load_boundary_gdf(shp_path: str | Path) -> gpd.GeoDataFrame:
    """Load boundary shapefile as one-row polygon GeoDataFrame.

    Parameters
    ----------
    Parameters
    ----------
    shp_path : str | Path
        Input boundary shapefile path.

    Returns
    -------
    geopandas.GeoDataFrame
        Boundary data containing exactly one polygon-like row.
    """
    boundary_gdf = gpd.read_file(Path(shp_path))
    _validate_boundary_gdf(boundary_gdf)
    return boundary_gdf


def _mar_axes(
    boundary_geom: Polygon,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float]:
    """Resolve minimum-area-rectangle origin and unit axes.

    Parameters
    ----------
    boundary_geom : shapely.geometry.Polygon
        Boundary geometry used to estimate row/column axes.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray, numpy.ndarray, float, float]
        Rectangle origin, width unit vector, height unit vector,
        total width, and total height.
    """
    mar = boundary_geom.minimum_rotated_rectangle
    mar_xy = np.asarray(mar.exterior.coords)[:4, :2]
    origin_xy = mar_xy[0]
    edge_w = mar_xy[1] - mar_xy[0]
    edge_h = mar_xy[3] - mar_xy[0]
    width_len = float(np.linalg.norm(edge_w))
    height_len = float(np.linalg.norm(edge_h))
    width_dir = edge_w / width_len
    height_dir = edge_h / height_len
    return origin_xy, width_dir, height_dir, width_len, height_len


def _resolve_rows_cols(
    mode_index: int,
    rows: int,
    cols: int,
    width: float,
    height: float,
    x_spacing: float,
    y_spacing: float,
    total_width: float,
    total_height: float,
) -> tuple[int, int, float, float]:
    """Resolve row/column counts and final cell dimensions.

    Parameters
    ----------
    mode_index : int
        0 for grid mode, 1 for fixed cell size mode.
    rows, cols : int
        Requested row and column counts in grid mode.
    width, height : float
        Requested cell dimensions in size mode.
    x_spacing, y_spacing : float
        Spacing between neighboring cells.
    total_width, total_height : float
        MAR dimensions used as generation envelope.

    Returns
    -------
    tuple[int, int, float, float]
        Row count, column count, cell width, and cell height.
    """
    if mode_index == 0:
        cell_width = (total_width - (cols - 1) * x_spacing) / cols
        cell_height = (total_height - (rows - 1) * y_spacing) / rows
        return rows, cols, cell_width, cell_height

    cols_fit = int((total_width + x_spacing) // (width + x_spacing))
    rows_fit = int((total_height + y_spacing) // (height + y_spacing))
    return rows_fit, cols_fit, width, height


def _build_cell_polygons(
    rows: int,
    cols: int,
    origin_xy: np.ndarray,
    width_dir: np.ndarray,
    height_dir: np.ndarray,
    cell_width: float,
    cell_height: float,
    x_spacing: float,
    y_spacing: float,
) -> list[Polygon]:
    """Generate cell polygons from rectangle basis vectors."""
    polygons: list[Polygon] = []
    for row_index in range(rows):
        for col_index in range(cols):
            start_xy = (
                origin_xy
                + col_index * (cell_width + x_spacing) * width_dir
                + row_index * (cell_height + y_spacing) * height_dir
            )
            p0 = start_xy
            p1 = p0 + cell_width * width_dir
            p2 = p1 + cell_height * height_dir
            p3 = p0 + cell_height * height_dir
            polygons.append(Polygon([p0, p1, p2, p3, p0]))
    return polygons


def _apply_keep_mode(
    polygons: list[Polygon], boundary_geom: Polygon, keep_mode: str
) -> list[Polygon]:
    """Filter generated polygons with keep-mode rule."""
    if keep_mode == "all":
        return polygons
    if keep_mode == "inside":
        return [poly for poly in polygons if poly.within(boundary_geom)]
    return [poly for poly in polygons if poly.intersects(boundary_geom)]


def generate_subplots_gdf(
    boundary_gdf: gpd.GeoDataFrame,
    mode_index: int,
    rows: int,
    cols: int,
    width: float,
    height: float,
    x_spacing: float,
    y_spacing: float,
    keep_mode: str,
) -> gpd.GeoDataFrame:
    """Generate subplot polygons from boundary and UI parameters.

    Parameters
    ----------
    boundary_gdf : geopandas.GeoDataFrame
        Input boundary with exactly one polygon-like row.
    mode_index : int
        0 for grid mode, 1 for size mode.
    rows, cols : int
        Grid dimensions for mode 0.
    width, height : float
        Cell dimensions for mode 1.
    x_spacing, y_spacing : float
        Intervals between cells.
    keep_mode : str
        Keep rule in {"all", "touch", "inside"}.

    Returns
    -------
    geopandas.GeoDataFrame
        Generated subplot polygons with stable ``id`` column.
    """
    _validate_boundary_gdf(boundary_gdf)
    _validate_keep_mode(keep_mode)
    boundary_geom = boundary_gdf.geometry.iloc[0]
    origin_xy, width_dir, height_dir, total_width, total_height = _mar_axes(
        boundary_geom
    )
    rows, cols, cell_width, cell_height = _resolve_rows_cols(
        mode_index,
        rows,
        cols,
        width,
        height,
        x_spacing,
        y_spacing,
        total_width,
        total_height,
    )
    polygons = _build_cell_polygons(
        rows,
        cols,
        origin_xy,
        width_dir,
        height_dir,
        cell_width,
        cell_height,
        x_spacing,
        y_spacing,
    )
    kept_polygons = _apply_keep_mode(polygons, boundary_geom, keep_mode)
    subplot_ids = np.arange(1, len(kept_polygons) + 1, dtype=int)
    return gpd.GeoDataFrame(
        {"id": subplot_ids}, geometry=kept_polygons, crs=boundary_gdf.crs
    )


def generate_and_save_gdf(
    boundary_gdf: gpd.GeoDataFrame,
    mode_index: int,
    rows: int,
    cols: int,
    width: float,
    height: float,
    x_spacing: float,
    y_spacing: float,
    keep_mode: str,
    output_path: str | Path,
) -> gpd.GeoDataFrame:
    """Generate subplots and write them to a shapefile.

    Parameters
    ----------
    boundary_gdf : geopandas.GeoDataFrame
        Boundary geometry input.
    mode_index : int
        0 for grid mode, 1 for fixed size mode.
    rows, cols : int
        Grid dimensions when ``mode_index`` is 0.
    width, height : float
        Cell dimensions when ``mode_index`` is 1.
    x_spacing, y_spacing : float
        Spacing between cells.
    keep_mode : str
        Keep rule in {"all", "touch", "inside"}.
    output_path : str | Path
        Destination shapefile path.

    Returns
    -------
    geopandas.GeoDataFrame
        Generated subplot polygons.
    """
    subplots_gdf = generate_subplots_gdf(
        boundary_gdf,
        mode_index,
        rows,
        cols,
        width,
        height,
        x_spacing,
        y_spacing,
        keep_mode,
    )
    normalized_path = _normalize_shp_output_path(output_path)
    subplots_gdf.to_file(normalized_path)
    return subplots_gdf


def calculate_optimal_rotation(boundary_gdf: gpd.GeoDataFrame) -> float | None:
    """Calculate angle of the long MAR edge in degrees.

    Parameters
    ----------
    boundary_gdf : geopandas.GeoDataFrame
        One-row polygon boundary GeoDataFrame.

    Returns
    -------
    float | None
        Long edge angle in degrees, or ``None`` when invalid.
    """
    try:
        _validate_boundary_gdf(boundary_gdf)
    except ValueError:
        return None

    boundary_geom = boundary_gdf.geometry.iloc[0]
    mar_coords = np.asarray(boundary_geom.minimum_rotated_rectangle.exterior.coords)
    if mar_coords.shape[0] < 4:
        return None
    edge_1 = mar_coords[1] - mar_coords[0]
    edge_2 = mar_coords[2] - mar_coords[1]
    long_edge = edge_1 if np.linalg.norm(edge_1) >= np.linalg.norm(edge_2) else edge_2
    return math.degrees(math.atan2(long_edge[1], long_edge[0]))
