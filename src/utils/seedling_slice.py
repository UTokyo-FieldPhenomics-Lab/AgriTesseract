"""Slice helpers for SAM3 inference on large DOM images."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class SliceWindow:
    """Single slice window in pixel space.

    Parameters
    ----------
    row : int
        Grid row index.
    col : int
        Grid column index.
    x0, y0, x1, y1 : int
        Pixel bounds in ``[x0, y0, x1, y1]`` format.
    """

    row: int
    col: int
    x0: int
    y0: int
    x1: int
    y1: int


def _axis_windows(full_size: int, slice_size: int, stride: int) -> list[int]:
    """Build axis start offsets with edge clamping."""
    if full_size <= slice_size:
        return [0]
    starts: list[int] = []
    current = 0
    last_start = full_size - slice_size
    while current < last_start:
        starts.append(current)
        current += stride
    starts.append(last_start)
    return starts


def generate_slice_windows(
    image_width: int,
    image_height: int,
    slice_size: int,
    overlap_ratio: float,
) -> list[SliceWindow]:
    """Generate overlapping square slice windows.

    Parameters
    ----------
    image_width : int
        Full image width in pixels.
    image_height : int
        Full image height in pixels.
    slice_size : int
        Side length of each square slice.
    overlap_ratio : float
        Ratio in ``[0, 0.95)`` controlling overlap size.

    Returns
    -------
    list[SliceWindow]
        Ordered windows in row-major order.
    """
    overlap_ratio = max(0.0, min(0.95, overlap_ratio))
    stride = max(1, int(slice_size * (1.0 - overlap_ratio)))
    x_starts = _axis_windows(image_width, slice_size, stride)
    y_starts = _axis_windows(image_height, slice_size, stride)
    windows: list[SliceWindow] = []
    for row, y0 in enumerate(y_starts):
        for col, x0 in enumerate(x_starts):
            windows.append(
                SliceWindow(
                    row=row,
                    col=col,
                    x0=x0,
                    y0=y0,
                    x1=min(image_width, x0 + slice_size),
                    y1=min(image_height, y0 + slice_size),
                )
            )
    return windows


def bbox_centers_xyxy(boxes_xyxy: np.ndarray) -> np.ndarray:
    """Convert xyxy boxes into center points.

    Parameters
    ----------
    boxes_xyxy : numpy.ndarray
        Array with shape ``(N, 4)`` storing ``[x0, y0, x1, y1]``.

    Returns
    -------
    numpy.ndarray
        Center array with shape ``(N, 2)``.
    """
    if boxes_xyxy.size == 0:
        return np.zeros((0, 2), dtype=float)
    centers_x = (boxes_xyxy[:, 0] + boxes_xyxy[:, 2]) * 0.5
    centers_y = (boxes_xyxy[:, 1] + boxes_xyxy[:, 3]) * 0.5
    return np.stack([centers_x, centers_y], axis=1)
