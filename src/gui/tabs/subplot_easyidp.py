"""EasyIDP helpers for subplot generation workflow."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
import math

import easyidp as idp
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


def load_boundary_roi(shp_path: str | Path) -> idp.ROI:
    """Load boundary shapefile as a single-polygon ROI.

    Parameters
    ----------
    shp_path : str | Path
        Input boundary shapefile path.

    Returns
    -------
    idp.ROI
        Boundary ROI object containing exactly one polygon.

    Raises
    ------
    ValueError
        Raised when ROI item count is not exactly one.
    """
    boundary_roi = idp.ROI(str(shp_path))
    if len(boundary_roi) != 1:
        raise ValueError(
            f"Boundary must contain exactly one polygon, got {len(boundary_roi)}"
        )
    return boundary_roi


def build_generate_kwargs(
    mode_index: int,
    rows: int,
    cols: int,
    width: float,
    height: float,
    x_spacing: float,
    y_spacing: float,
    keep_mode: str,
) -> dict:
    """Build EasyIDP generate_subplots keyword arguments.

    Parameters
    ----------
    mode_index : int
        0 for grid mode, 1 for size mode.
    rows : int
        Row count for grid mode.
    cols : int
        Column count for grid mode.
    width : float
        Subplot width for size mode.
    height : float
        Subplot height for size mode.
    x_spacing : float
        Horizontal interval between subplots.
    y_spacing : float
        Vertical interval between subplots.
    keep_mode : str
        Keep filter mode in {"all", "touch", "inside"}.

    Returns
    -------
    dict
        Keyword arguments accepted by ``idp.geotools.generate_subplots``.
    """
    if keep_mode not in VALID_KEEP_MODES:
        raise ValueError(f"Unsupported keep mode: {keep_mode}")

    kwargs = {
        "x_interval": float(x_spacing),
        "y_interval": float(y_spacing),
        "keep": keep_mode,
    }
    if mode_index == 0:
        kwargs.update({"row_num": int(rows), "col_num": int(cols)})
        return kwargs

    kwargs.update({"width": float(width), "height": float(height)})
    return kwargs


def generate_subplots_roi(
    boundary_roi: idp.ROI,
    mode_index: int,
    rows: int,
    cols: int,
    width: float,
    height: float,
    x_spacing: float,
    y_spacing: float,
    keep_mode: str,
) -> idp.ROI:
    """Generate subplot ROI from boundary ROI and UI parameters.

    Parameters
    ----------
    boundary_roi : idp.ROI
        Input ROI with exactly one boundary polygon.
    mode_index : int
        0 for grid mode, 1 for size mode.
    rows, cols : int
        Grid dimensions for mode 0.
    width, height : float
        Cell dimensions for mode 1.
    x_spacing, y_spacing : float
        Intervals between cells.
    keep_mode : str
        EasyIDP keep mode.

    Returns
    -------
    idp.ROI
        Generated subplot ROI.
    """
    kwargs = build_generate_kwargs(
        mode_index,
        rows,
        cols,
        width,
        height,
        x_spacing,
        y_spacing,
        keep_mode,
    )
    return idp.geotools.generate_subplots(boundary_roi, **kwargs)


def generate_and_save(
    boundary_roi: idp.ROI,
    mode_index: int,
    rows: int,
    cols: int,
    width: float,
    height: float,
    x_spacing: float,
    y_spacing: float,
    keep_mode: str,
    output_path: str | Path,
) -> idp.ROI:
    """Generate subplots and save result with ROI.save.

    Parameters
    ----------
    boundary_roi : idp.ROI
        Input boundary ROI.
    mode_index : int
        0 for grid mode, 1 for size mode.
    rows, cols : int
        Grid dimensions for mode 0.
    width, height : float
        Cell dimensions for mode 1.
    x_spacing, y_spacing : float
        Intervals between cells.
    keep_mode : str
        EasyIDP keep mode.
    output_path : str | Path
        Output shapefile path.

    Returns
    -------
    idp.ROI
        Generated subplot ROI.
    """
    subplots = generate_subplots_roi(
        boundary_roi,
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
    subplots.save(str(normalized_path), name_field="id")
    return subplots


def calculate_optimal_rotation(boundary_roi: idp.ROI) -> Optional[float]:
    """Calculate angle of long MAR edge for current boundary.

    Parameters
    ----------
    boundary_roi : idp.ROI
        Boundary ROI with one polygon.

    Returns
    -------
    float | None
        Long-edge angle in degrees, or None when invalid.
    """
    if len(boundary_roi) != 1:
        return None

    # ``coords_xy`` shape: (N, 2) from ROI polygon points.
    coords_xy = np.asarray(next(iter(boundary_roi.values())))[:, :2]
    mar = Polygon(coords_xy).minimum_rotated_rectangle
    mar_coords = np.asarray(mar.exterior.coords)
    if mar_coords.shape[0] < 4:
        return None

    edge_1 = mar_coords[1] - mar_coords[0]
    edge_2 = mar_coords[2] - mar_coords[1]
    long_edge = edge_1 if np.linalg.norm(edge_1) >= np.linalg.norm(edge_2) else edge_2
    return math.degrees(math.atan2(long_edge[1], long_edge[0]))
