"""Tests for seedling slice and geometry helpers."""

import numpy as np

from src.utils.seedling_detect.slice import bbox_centers_xyxy, generate_slice_windows


def test_generate_slice_windows_cover_image_extent() -> None:
    """Slice windows should cover image and clamp edges."""
    windows = generate_slice_windows(
        image_width=1000,
        image_height=1000,
        slice_size=400,
        overlap_ratio=0.5,
    )

    assert len(windows) == 16
    assert windows[0].x0 == 0
    assert windows[0].y0 == 0
    assert windows[-1].x1 == 1000
    assert windows[-1].y1 == 1000


def test_bbox_centers_xyxy_calculates_center_points() -> None:
    """BBox center extraction should return Nx2 center array."""
    boxes_xyxy = np.array([[0.0, 0.0, 4.0, 2.0], [2.0, 2.0, 6.0, 6.0]])
    centers_xy = bbox_centers_xyxy(boxes_xyxy)

    assert centers_xy.shape == (2, 2)
    assert np.allclose(centers_xy[0], [2.0, 1.0])
    assert np.allclose(centers_xy[1], [4.0, 4.0])
