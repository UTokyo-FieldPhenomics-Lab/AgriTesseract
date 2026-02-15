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
    raise NotImplementedError("build_ridge_intervals is not implemented yet")


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
    raise NotImplementedError("assign_points_to_ridges is not implemented yet")


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
    raise NotImplementedError("build_ordering_result is not implemented yet")
