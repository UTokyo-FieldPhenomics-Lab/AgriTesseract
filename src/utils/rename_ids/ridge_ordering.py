"""Ridge ordering helpers for module 05."""

from __future__ import annotations

import geopandas as gpd
import numpy as np


def build_ridge_intervals(ridge_peaks: np.ndarray, buffer: float) -> np.ndarray:
    """Build interval bounds centered on each ridge peak.

    Parameters
    ----------
    ridge_peaks : numpy.ndarray
        Ridge peak positions on the perpendicular projection axis, shape ``(K,)``.
    buffer : float
        Half width used for single-ridge interval or minimal extension for edges.

    Returns
    -------
    numpy.ndarray
        Interval array with shape ``(K, 2)`` where each row is
        ``[left_bound, right_bound]``.

    Examples
    --------
    >>> build_ridge_intervals(np.asarray([0.0]), buffer=0.5).shape
    (1, 2)
    """
    if buffer <= 0:
        raise ValueError("buffer must be > 0")
    peak_array = np.asarray(ridge_peaks, dtype=np.float64)
    if peak_array.ndim != 1:
        raise ValueError("ridge_peaks must be 1D")
    if peak_array.size == 0:
        return np.empty((0, 2), dtype=np.float64)
    peak_array = np.sort(peak_array)
    if peak_array.size == 1:
        return np.asarray([[peak_array[0] - buffer, peak_array[0] + buffer]])
    return _build_multi_ridge_intervals(peak_array, float(buffer))


def assign_points_to_ridges(
    projected_x: np.ndarray,
    effective_mask: np.ndarray,
    ridge_intervals: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Assign projected points to ridge intervals.

    Parameters
    ----------
    projected_x : numpy.ndarray
        Perpendicular projections for all points, shape ``(N,)``.
    effective_mask : numpy.ndarray
        Boolean mask indicating valid points, shape ``(N,)``.
    ridge_intervals : numpy.ndarray
        Ridge interval bounds from ``build_ridge_intervals``, shape ``(K, 2)``.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        ``(ridge_id, is_inlier)`` with both arrays shaped ``(N,)``.
    """
    projected_array = np.asarray(projected_x, dtype=np.float64)
    mask_array = np.asarray(effective_mask, dtype=bool)
    interval_array = np.asarray(ridge_intervals, dtype=np.float64)
    if projected_array.ndim != 1:
        raise ValueError("projected_x must be 1D")
    if mask_array.ndim != 1:
        raise ValueError("effective_mask must be 1D")
    if projected_array.size != mask_array.size:
        raise ValueError("projected_x and effective_mask must match length")
    if interval_array.ndim != 2 or interval_array.shape[1] != 2:
        raise ValueError("ridge_intervals must have shape (K, 2)")
    ridge_id = np.full(projected_array.shape[0], -1, dtype=np.int64)
    is_inlier = np.zeros(projected_array.shape[0], dtype=bool)
    if interval_array.shape[0] == 0:
        return ridge_id, is_inlier
    centers = interval_array.mean(axis=1)
    for point_index in np.where(mask_array)[0]:
        ridge_index = _pick_ridge_for_value(
            projected_array[point_index], interval_array, centers
        )
        if ridge_index < 0:
            continue
        ridge_id[point_index] = ridge_index
        is_inlier[point_index] = True
    return ridge_id, is_inlier


def build_ordering_result(
    points_gdf: gpd.GeoDataFrame,
    ridge_id: np.ndarray,
    is_inlier: np.ndarray,
) -> gpd.GeoDataFrame:
    """Build ordering result frame preserving input row order.

    Parameters
    ----------
    points_gdf : geopandas.GeoDataFrame
        Input point records containing at least ``fid`` and ``geometry``.
    ridge_id : numpy.ndarray
        Assigned ridge IDs with shape ``(N,)``.
    is_inlier : numpy.ndarray
        Inlier flags with shape ``(N,)``.

    Returns
    -------
    geopandas.GeoDataFrame
        Ordering result with columns ``fid``, ``ridge_id``, ``is_inlier``,
        and ``geometry``.
    """
    if "fid" not in points_gdf.columns:
        raise ValueError("points_gdf must include 'fid' column")
    ridge_array = np.asarray(ridge_id, dtype=np.int64)
    inlier_array = np.asarray(is_inlier, dtype=bool)
    if ridge_array.ndim != 1 or inlier_array.ndim != 1:
        raise ValueError("ridge_id and is_inlier must be 1D")
    if len(points_gdf) != ridge_array.size or len(points_gdf) != inlier_array.size:
        raise ValueError("points_gdf length must match ridge_id and is_inlier")
    result = gpd.GeoDataFrame(
        {
            "fid": points_gdf["fid"].to_numpy(copy=False),
            "ridge_id": ridge_array,
            "is_inlier": inlier_array,
        },
        geometry=points_gdf.geometry,
        crs=points_gdf.crs,
    )
    return result[["fid", "ridge_id", "is_inlier", "geometry"]]


def _build_multi_ridge_intervals(peak_array: np.ndarray, buffer: float) -> np.ndarray:
    """Build interval bounds for multiple sorted ridge peaks."""
    interval_array = np.empty((peak_array.size, 2), dtype=np.float64)
    middle_bounds = 0.5 * (peak_array[:-1] + peak_array[1:])
    left_extent = max(buffer, 0.5 * (peak_array[1] - peak_array[0]))
    right_extent = max(buffer, 0.5 * (peak_array[-1] - peak_array[-2]))
    interval_array[0, 0] = peak_array[0] - left_extent
    interval_array[0, 1] = middle_bounds[0]
    interval_array[-1, 0] = middle_bounds[-1]
    interval_array[-1, 1] = peak_array[-1] + right_extent
    if peak_array.size == 2:
        return interval_array
    interval_array[1:-1, 0] = middle_bounds[:-1]
    interval_array[1:-1, 1] = middle_bounds[1:]
    return interval_array


def _pick_ridge_for_value(
    value: float,
    interval_array: np.ndarray,
    centers: np.ndarray,
) -> int:
    """Pick a ridge index whose interval contains the given projection value."""
    matches = np.where(
        (interval_array[:, 0] <= value) & (value <= interval_array[:, 1])
    )[0]
    if matches.size == 0:
        return -1
    if matches.size == 1:
        return int(matches[0])
    offset = np.abs(centers[matches] - value)
    return int(matches[int(np.argmin(offset))])
