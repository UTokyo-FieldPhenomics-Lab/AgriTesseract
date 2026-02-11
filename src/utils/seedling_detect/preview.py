"""Preview-box geometry helpers for seedling workflows."""

from __future__ import annotations

import numpy as np
from affine import Affine


PREVIEW_MIN_SIZE = 128
PREVIEW_MAX_SIZE = 2048


def clamp_preview_size(size: int) -> int:
    """Clamp preview box side length.

    Parameters
    ----------
    size : int
        Requested preview box size in pixels.

    Returns
    -------
    int
        Clamped side length in ``[128, 2048]``.
    """
    if size < PREVIEW_MIN_SIZE:
        return PREVIEW_MIN_SIZE
    if size > PREVIEW_MAX_SIZE:
        return PREVIEW_MAX_SIZE
    return int(size)


def preview_bounds_from_center(
    center_x: float,
    center_y: float,
    size: int,
) -> tuple[float, float, float, float]:
    """Create square bounds centered at given coordinate.

    Parameters
    ----------
    center_x : float
        Center x coordinate.
    center_y : float
        Center y coordinate.
    size : int
        Side length in map units.

    Returns
    -------
    tuple[float, float, float, float]
        Bounds in ``(x_min, y_min, x_max, y_max)`` order.
    """
    half = float(size) * 0.5
    return center_x - half, center_y - half, center_x + half, center_y + half


def pixel_square_bounds_from_geo_center(
    center_x: float,
    center_y: float,
    size_px: int,
    transform: Affine,
) -> tuple[float, float, float, float]:
    """Convert a pixel-square around geo center into geo bounds.

    Parameters
    ----------
    center_x : float
        Center x in geo coordinate.
    center_y : float
        Center y in geo coordinate.
    size_px : int
        Square side length in pixel units.
    transform : affine.Affine
        Geo transform mapping ``(col, row) -> (x, y)``.

    Returns
    -------
    tuple[float, float, float, float]
        Bounds in ``(x_min, y_min, x_max, y_max)`` order.
    """
    half_px = float(size_px) * 0.5
    inv_transform = ~transform
    center_col = (
        inv_transform.c + inv_transform.a * center_x + inv_transform.b * center_y
    )
    center_row = (
        inv_transform.f + inv_transform.d * center_x + inv_transform.e * center_y
    )
    col_min = center_col - half_px
    col_max = center_col + half_px
    row_min = center_row - half_px
    row_max = center_row + half_px
    x0 = transform.c + transform.a * col_min + transform.b * row_min
    y0 = transform.f + transform.d * col_min + transform.e * row_min
    x1 = transform.c + transform.a * col_max + transform.b * row_max
    y1 = transform.f + transform.d * col_max + transform.e * row_max
    x_min = float(min(x0, x1))
    x_max = float(max(x0, x1))
    y_min = float(min(y0, y1))
    y_max = float(max(y0, y1))
    return x_min, y_min, x_max, y_max


def polygon_px_to_geo(
    polygon_px: np.ndarray,
    transform: Affine,
) -> np.ndarray:
    """Convert polygon from patch pixel coordinates to geo coordinates.

    Parameters
    ----------
    polygon_px : numpy.ndarray
        Polygon vertices with shape ``(N, 2)`` in ``(x, y)`` pixel order.
    transform : affine.Affine
        Affine transform mapping ``(col, row) -> (geo_x, geo_y)``.

    Returns
    -------
    numpy.ndarray
        Transformed polygon with shape ``(N, 2)`` in geo coordinates.

    Examples
    --------
    >>> from affine import Affine
    >>> t = Affine(0.1, 0.0, 100.0, 0.0, -0.1, 200.0)
    >>> poly = np.array([[0, 0], [10, 0], [10, 10]])
    >>> polygon_px_to_geo(poly, t)
    array([[100. , 200. ],
           [101. , 200. ],
           [101. , 199. ]])
    """
    poly_xy = np.asarray(polygon_px, dtype=float)  # shape: (N, 2)
    geo_points = []
    for x_coord, y_coord in poly_xy:
        x_geo = (
            transform.c + transform.a * float(x_coord) + transform.b * float(y_coord)
        )
        y_geo = (
            transform.f + transform.d * float(x_coord) + transform.e * float(y_coord)
        )
        geo_points.append([float(x_geo), float(y_geo)])
    return np.asarray(geo_points, dtype=float)
