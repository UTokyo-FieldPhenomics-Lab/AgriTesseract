"""Slice helpers for SAM3 inference on large DOM images."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from affine import Affine
from shapely.geometry import Polygon


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


def _window_to_geo_polygon(window: SliceWindow, transform: Affine) -> Polygon:
    """Convert one pixel window to geo polygon."""
    x_tl, y_tl = _affine_xy(transform, float(window.x0), float(window.y0))
    x_tr, y_tr = _affine_xy(transform, float(window.x1), float(window.y0))
    x_br, y_br = _affine_xy(transform, float(window.x1), float(window.y1))
    x_bl, y_bl = _affine_xy(transform, float(window.x0), float(window.y1))
    return Polygon(
        [
            (float(x_tl), float(y_tl)),
            (float(x_tr), float(y_tr)),
            (float(x_br), float(y_br)),
            (float(x_bl), float(y_bl)),
        ]
    )


def filter_slice_windows_by_boundary(
    windows: list[SliceWindow],
    transform: Affine,
    boundary_xy: np.ndarray | None,
    mode: str,
) -> list[SliceWindow]:
    """Filter slice windows against a boundary polygon.

    Parameters
    ----------
    windows : list[SliceWindow]
        Input slice windows.
    transform : affine.Affine
        Pixel-to-geo transform.
    boundary_xy : numpy.ndarray | None
        Boundary coordinates with shape ``(N, 2)``.
    mode : str
        ``"inside"`` keeps only fully inside windows.
        ``"intersect"`` keeps intersecting windows.
    """
    if boundary_xy is None or np.asarray(boundary_xy).shape[0] < 3:
        return windows
    boundary_poly = Polygon(np.asarray(boundary_xy, dtype=float))
    if boundary_poly.is_empty:
        return windows
    keep_inside = mode == "inside"
    kept_windows: list[SliceWindow] = []
    for window in windows:
        window_poly = _window_to_geo_polygon(window, transform)
        if keep_inside and window_poly.within(boundary_poly):
            kept_windows.append(window)
            continue
        if not keep_inside and window_poly.intersects(boundary_poly):
            kept_windows.append(window)
    return kept_windows


def _affine_xy(
    transform: Affine, x_value: float, y_value: float
) -> tuple[float, float]:
    """Apply affine transform and return x/y as floats."""
    point_xy = transform * (x_value, y_value)
    return float(point_xy[0]), float(point_xy[1])


def nms_boxes_xyxy(
    boxes_xyxy: np.ndarray,
    scores: np.ndarray,
    iou_threshold: float,
) -> list[int]:
    """Run greedy NMS and return kept indices.

    Parameters
    ----------
    boxes_xyxy : numpy.ndarray
        Array with shape ``(N, 4)`` in ``[x0, y0, x1, y1]``.
    scores : numpy.ndarray
        Score array with shape ``(N,)``.
    iou_threshold : float
        IoU threshold for suppression.

    Returns
    -------
    list[int]
        Kept original indices sorted by descending score.
    """
    if boxes_xyxy.size == 0:
        return []
    order = np.argsort(-np.asarray(scores, dtype=float))
    keep: list[int] = []
    while order.size > 0:
        best_idx = int(order[0])
        keep.append(best_idx)
        if order.size == 1:
            return keep
        remain = order[1:]
        iou_values = _pairwise_iou_xyxy(boxes_xyxy[best_idx], boxes_xyxy[remain])
        order = remain[iou_values <= float(iou_threshold)]
    return keep


def _pairwise_iou_xyxy(base_box: np.ndarray, candidate_boxes: np.ndarray) -> np.ndarray:
    """Compute IoU between one box and many boxes."""
    xx0 = np.maximum(base_box[0], candidate_boxes[:, 0])
    yy0 = np.maximum(base_box[1], candidate_boxes[:, 1])
    xx1 = np.minimum(base_box[2], candidate_boxes[:, 2])
    yy1 = np.minimum(base_box[3], candidate_boxes[:, 3])
    inter_w = np.maximum(0.0, xx1 - xx0)
    inter_h = np.maximum(0.0, yy1 - yy0)
    inter_area = inter_w * inter_h
    base_area = max(0.0, (base_box[2] - base_box[0]) * (base_box[3] - base_box[1]))
    cand_area = np.maximum(
        0.0,
        (candidate_boxes[:, 2] - candidate_boxes[:, 0])
        * (candidate_boxes[:, 3] - candidate_boxes[:, 1]),
    )
    union_area = np.maximum(1e-9, base_area + cand_area - inter_area)
    return inter_area / union_area


def _pairwise_ios_xyxy(base_box: np.ndarray, candidate_boxes: np.ndarray) -> np.ndarray:
    """Compute IoS against candidate boxes."""
    xx0 = np.maximum(base_box[0], candidate_boxes[:, 0])
    yy0 = np.maximum(base_box[1], candidate_boxes[:, 1])
    xx1 = np.minimum(base_box[2], candidate_boxes[:, 2])
    yy1 = np.minimum(base_box[3], candidate_boxes[:, 3])
    inter_w = np.maximum(0.0, xx1 - xx0)
    inter_h = np.maximum(0.0, yy1 - yy0)
    inter_area = inter_w * inter_h
    base_area = max(0.0, (base_box[2] - base_box[0]) * (base_box[3] - base_box[1]))
    cand_area = np.maximum(
        0.0,
        (candidate_boxes[:, 2] - candidate_boxes[:, 0])
        * (candidate_boxes[:, 3] - candidate_boxes[:, 1]),
    )
    smaller_area = np.maximum(1e-9, np.minimum(base_area, cand_area))
    return inter_area / smaller_area


def nms_with_ios_xyxy(
    boxes_xyxy: np.ndarray,
    scores: np.ndarray,
    iou_threshold: float,
    ios_threshold: float,
) -> list[int]:
    """Apply IoU NMS first, then IoS-based containment suppression."""
    keep = nms_boxes_xyxy(boxes_xyxy, scores, iou_threshold)
    if len(keep) < 2:
        return keep
    kept_boxes = boxes_xyxy[keep]
    suppressed = np.zeros((len(keep),), dtype=bool)
    for idx in range(len(keep)):
        if suppressed[idx]:
            continue
        if idx + 1 >= len(keep):
            break
        ios_values = _pairwise_ios_xyxy(kept_boxes[idx], kept_boxes[idx + 1 :])
        suppressed[idx + 1 :] |= ios_values > float(ios_threshold)
    return [keep[idx] for idx in range(len(keep)) if not suppressed[idx]]


def _filter_slice_boundary_boxes(
    boxes_px: np.ndarray,
    slice_shape: tuple[int, int],
    is_edge: dict[str, bool],
    border_threshold_px: float,
) -> np.ndarray:
    """Return keep mask for boxes not touching non-global slice borders."""
    if boxes_px.size == 0:
        return np.zeros((0,), dtype=bool)
    slice_width, slice_height = slice_shape
    x0 = boxes_px[:, 0]
    y0 = boxes_px[:, 1]
    x1 = boxes_px[:, 2]
    y1 = boxes_px[:, 3]
    keep_mask = np.ones((boxes_px.shape[0],), dtype=bool)
    if not is_edge.get("left", False):
        keep_mask &= x0 > border_threshold_px
    if not is_edge.get("top", False):
        keep_mask &= y0 > border_threshold_px
    if not is_edge.get("right", False):
        keep_mask &= x1 < (float(slice_width) - border_threshold_px)
    if not is_edge.get("bottom", False):
        keep_mask &= y1 < (float(slice_height) - border_threshold_px)
    return keep_mask


def merge_slice_detections(
    slice_result_list: list[dict],
    iou_threshold: float,
    ios_threshold: float = 0.95,
    remove_boundary: bool = True,
    remove_overlay: bool = True,
    border_threshold_px: float = 2.0,
) -> dict[str, np.ndarray]:
    """Merge per-slice detection boxes with global NMS.

    Parameters
    ----------
    slice_result_list : list[dict]
        List of per-slice result dicts containing ``boxes_geo`` and ``scores``.
    iou_threshold : float
        IoU threshold for NMS.
    ios_threshold : float, optional
        IoS threshold for containment suppression.
    remove_boundary : bool, optional
        Whether to remove detections touching non-global slice borders.
    remove_overlay : bool, optional
        Whether to remove contain/contained boxes via IoS.
    border_threshold_px : float, optional
        Pixel threshold for edge-touch filtering.

    Returns
    -------
    dict[str, numpy.ndarray]
        Keys: ``boxes_xyxy``, ``scores``, ``points_xy``.
    """
    box_chunks: list[np.ndarray] = []
    score_chunks: list[np.ndarray] = []
    for result in slice_result_list:
        boxes_geo = np.asarray(result.get("boxes_geo", np.zeros((0, 4))), dtype=float)
        boxes_px = np.asarray(result.get("boxes_px", np.zeros((0, 4))), dtype=float)
        scores = np.asarray(result.get("scores", np.zeros((0,))), dtype=float)
        if boxes_geo.size == 0 or scores.size == 0:
            continue
        keep_mask = np.ones((scores.shape[0],), dtype=bool)
        if remove_boundary and boxes_px.shape[0] == scores.shape[0]:
            keep_mask &= _filter_slice_boundary_boxes(
                boxes_px=boxes_px,
                slice_shape=tuple(result.get("slice_shape", (0, 0))),
                is_edge=result.get("is_edge", {}),
                border_threshold_px=border_threshold_px,
            )
        if not np.any(keep_mask):
            continue
        box_chunks.append(boxes_geo[keep_mask])
        score_chunks.append(scores[keep_mask])
    if not box_chunks:
        empty_boxes = np.zeros((0, 4), dtype=float)
        return {
            "boxes_xyxy": empty_boxes,
            "scores": np.zeros((0,), dtype=float),
            "points_xy": np.zeros((0, 2), dtype=float),
        }
    all_boxes = np.concatenate(box_chunks, axis=0)
    all_scores = np.concatenate(score_chunks, axis=0)
    if remove_overlay:
        keep_indices = nms_with_ios_xyxy(
            all_boxes,
            all_scores,
            iou_threshold=iou_threshold,
            ios_threshold=ios_threshold,
        )
    else:
        keep_indices = nms_boxes_xyxy(
            all_boxes, all_scores, iou_threshold=iou_threshold
        )
    merged_boxes = all_boxes[keep_indices]
    merged_scores = all_scores[keep_indices]
    return {
        "boxes_xyxy": merged_boxes,
        "scores": merged_scores,
        "points_xy": bbox_centers_xyxy(merged_boxes),
    }
