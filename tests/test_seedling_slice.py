"""Tests for seedling slice and geometry helpers."""

import numpy as np
from affine import Affine

from src.utils.seedling_detect.slice import (
    bbox_centers_xyxy,
    filter_slice_windows_by_boundary,
    generate_slice_windows,
    merge_slice_detections,
    nms_boxes_xyxy,
)


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


def test_filter_slice_windows_keeps_intersect_and_inside() -> None:
    """Boundary filtering keeps expected windows for each mode."""
    windows = generate_slice_windows(100, 100, 40, 0.0)
    boundary_xy = np.array(
        [[20.0, 20.0], [80.0, 20.0], [80.0, 80.0], [20.0, 80.0]],
        dtype=float,
    )
    filtered_intersect = filter_slice_windows_by_boundary(
        windows=windows,
        transform=Affine.identity(),
        boundary_xy=boundary_xy,
        mode="intersect",
    )
    filtered_inside = filter_slice_windows_by_boundary(
        windows=windows,
        transform=Affine.identity(),
        boundary_xy=boundary_xy,
        mode="inside",
    )

    assert len(filtered_intersect) >= len(filtered_inside)
    assert len(filtered_inside) > 0


def test_nms_boxes_merges_overlaps_and_keeps_high_score() -> None:
    """NMS keeps highest-scored box among heavy overlaps."""
    boxes_xyxy = np.array(
        [[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 11.0, 11.0], [30.0, 30.0, 40.0, 40.0]],
        dtype=float,
    )
    scores = np.array([0.7, 0.9, 0.8], dtype=float)
    keep_indices = nms_boxes_xyxy(boxes_xyxy, scores, iou_threshold=0.5)

    assert keep_indices == [1, 2]


def test_merge_slice_detections_applies_nms_and_centers() -> None:
    """Slice merge returns NMS-filtered boxes and center points."""
    slices = [
        {
            "boxes_geo": np.array(
                [[0.0, 0.0, 10.0, 10.0], [1.0, 1.0, 11.0, 11.0]],
                dtype=float,
            ),
            "scores": np.array([0.7, 0.9], dtype=float),
        },
        {
            "boxes_geo": np.array([[30.0, 30.0, 40.0, 40.0]], dtype=float),
            "scores": np.array([0.8], dtype=float),
        },
    ]
    merged = merge_slice_detections(slices, iou_threshold=0.5)

    assert merged["boxes_xyxy"].shape == (2, 4)
    assert np.allclose(merged["scores"], np.array([0.9, 0.8]))
    assert merged["points_xy"].shape == (2, 2)
