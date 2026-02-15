"""Ridge ordering helpers for module 05."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from sklearn.linear_model import RANSACRegressor


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
    projected_y: np.ndarray | None = None,
    ransac_enabled: bool = False,
    residual: float = 50.0,
    max_trials: int = 1000,
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
    projected_y : numpy.ndarray | None, optional
        Projection along ridge direction, shape ``(N,)``; required when
        ``ransac_enabled`` is ``True``.
    ransac_enabled : bool, optional
        Whether to run RANSAC filtering inside each assigned ridge.
    residual : float, optional
        Residual threshold for ``RANSACRegressor``.
    max_trials : int, optional
        Maximum number of RANSAC iterations.

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
        scalar_index = int(point_index)
        ridge_index = _pick_ridge_for_value(
            float(projected_array[scalar_index]), interval_array, centers
        )
        if ridge_index < 0:
            continue
        ridge_id[scalar_index] = ridge_index
        is_inlier[scalar_index] = True
    if not ransac_enabled:
        return ridge_id, is_inlier
    y_array = _validate_projected_y(projected_y, projected_array.shape[0])
    _apply_ransac_filter(
        projected_array, y_array, ridge_id, is_inlier, residual, max_trials
    )
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
    output = result[["fid", "ridge_id", "is_inlier", "geometry"]]
    return gpd.GeoDataFrame(output, geometry="geometry", crs=points_gdf.crs)


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


def _validate_projected_y(projected_y: np.ndarray | None, size: int) -> np.ndarray:
    """Validate and normalize projected y-axis values for RANSAC."""
    if projected_y is None:
        raise ValueError("projected_y is required when ransac_enabled=True")
    y_array = np.asarray(projected_y, dtype=np.float64)
    if y_array.ndim != 1:
        raise ValueError("projected_y must be 1D")
    if y_array.size != size:
        raise ValueError("projected_y length must match projected_x")
    return y_array


def _apply_ransac_filter(
    projected_x: np.ndarray,
    projected_y: np.ndarray,
    ridge_id: np.ndarray,
    is_inlier: np.ndarray,
    residual: float,
    max_trials: int,
) -> None:
    """Apply per-ridge RANSAC and update inlier flags in place."""
    if residual <= 0:
        raise ValueError("residual must be > 0")
    if max_trials < 1:
        raise ValueError("max_trials must be >= 1")
    unique_ridges = np.unique(ridge_id[ridge_id >= 0])
    for ridge_value in unique_ridges:
        point_indices = np.where(ridge_id == ridge_value)[0]
        if point_indices.size < 2:
            continue
        x_data = projected_y[point_indices].reshape(-1, 1)
        y_data = projected_x[point_indices]
        ransac = RANSACRegressor(
            residual_threshold=float(residual),
            max_trials=int(max_trials),
            random_state=0,
        )
        try:
            ransac.fit(x_data, y_data)
        except ValueError:
            continue
        inlier_mask = np.asarray(ransac.inlier_mask_, dtype=bool)
        is_inlier[point_indices] = inlier_mask
