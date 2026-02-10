"""Preview-box geometry helpers for seedling workflows."""

from __future__ import annotations

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
