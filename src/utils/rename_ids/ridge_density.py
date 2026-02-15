"""Ridge density and peak detection helpers."""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np
from scipy.signal import find_peaks
from shapely.geometry import LineString

from src.utils.rename_ids.ridge_direction import normalize_direction_vector


def _validate_points(points_xy: np.ndarray) -> np.ndarray:
    """Validate points array shape.

    Parameters
    ----------
    points_xy : numpy.ndarray
        Input points with shape ``(N, 2)``.

    Returns
    -------
    numpy.ndarray
        Float64 points with shape ``(N, 2)``.
    """
    points_array = np.asarray(points_xy, dtype=np.float64)
    if points_array.ndim != 2 or points_array.shape[1] != 2:
        raise ValueError("points_xy must have shape (N, 2)")
    return points_array


def project_points_to_perp_axis(
    points_xy: np.ndarray,
    direction_vec: np.ndarray,
) -> np.ndarray:
    """Project points to axis perpendicular to ridge direction.

    Parameters
    ----------
    points_xy : numpy.ndarray
        Point coordinates with shape ``(N, 2)``.
    direction_vec : numpy.ndarray
        Ridge direction vector with shape ``(2,)``.

    Returns
    -------
    numpy.ndarray
        Projected x positions on perpendicular axis with shape ``(N,)``.

    Examples
    --------
    >>> points = np.asarray([[0.0, 0.0], [1.0, 1.0]])
    >>> project_points_to_perp_axis(points, np.asarray([0.0, 1.0])).shape
    (2,)
    """
    points_array = _validate_points(points_xy)
    if points_array.shape[0] == 0:
        return np.asarray([], dtype=np.float64)
    unit_direction = normalize_direction_vector(direction_vec)
    perp_axis = np.asarray([-unit_direction[1], unit_direction[0]], dtype=np.float64)
    origin = np.mean(points_array, axis=0)
    return np.dot(points_array - origin, perp_axis)


def build_density_histogram(
    projected_x: np.ndarray,
    strength_ratio: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Build binned density histogram from projected coordinates.

    Parameters
    ----------
    projected_x : numpy.ndarray
        Perpendicular projections with shape ``(N,)``.
    strength_ratio : float
        Histogram bin width in projected-axis units.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        ``(x_bins, counts)`` where ``x_bins`` has shape ``(M,)`` and
        ``counts`` has shape ``(M,)``.
    """
    if strength_ratio <= 0:
        raise ValueError("strength_ratio must be > 0")
    projected_array = np.asarray(projected_x, dtype=np.float64)
    if projected_array.ndim != 1:
        raise ValueError("projected_x must be 1D")
    if projected_array.size == 0:
        return np.asarray([], dtype=np.float64), np.asarray([], dtype=np.int64)
    bins = np.floor(projected_array / float(strength_ratio)) * float(strength_ratio)
    x_bins, counts = np.unique(bins, return_counts=True)
    return x_bins.astype(np.float64), counts.astype(np.int64)


def detect_ridge_peaks(
    counts: np.ndarray,
    distance: int,
    height: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Detect ridge peaks from histogram counts.

    Parameters
    ----------
    counts : numpy.ndarray
        Histogram counts with shape ``(M,)``.
    distance : int
        Minimum index distance between peaks.
    height : float
        Minimum peak height.

    Returns
    -------
    tuple[numpy.ndarray, numpy.ndarray]
        ``(peak_indices, peak_heights)`` with shapes ``(K,)`` and ``(K,)``.
    """
    if distance < 1:
        raise ValueError("distance must be >= 1")
    if height < 0:
        raise ValueError("height must be >= 0")
    count_array = np.asarray(counts, dtype=np.float64)
    if count_array.ndim != 1:
        raise ValueError("counts must be 1D")
    if count_array.size == 0:
        return np.asarray([], dtype=np.int64), np.asarray([], dtype=np.float64)
    peak_indices, props = find_peaks(count_array, distance=distance, height=height)
    peak_heights = np.asarray(props.get("peak_heights", []), dtype=np.float64)
    return peak_indices.astype(np.int64), peak_heights


def build_ridge_lines_from_peaks(
    peak_x: np.ndarray,
    points_xy: np.ndarray,
    direction_vec: np.ndarray,
    crs: Any = None,
) -> gpd.GeoDataFrame:
    """Build ridge candidate lines from peak locations.

    Parameters
    ----------
    peak_x : numpy.ndarray
        Peak coordinates on perpendicular axis with shape ``(K,)``.
    points_xy : numpy.ndarray
        Effective points with shape ``(N, 2)``.
    direction_vec : numpy.ndarray
        Ridge direction vector with shape ``(2,)``.
    crs : Any, optional
        CRS passed through to output ``GeoDataFrame``.

    Returns
    -------
    geopandas.GeoDataFrame
        Line geometries named by ``ridge_index``.
    """
    points_array = _validate_points(points_xy)
    peak_array = np.asarray(peak_x, dtype=np.float64)
    if peak_array.ndim != 1:
        raise ValueError("peak_x must be 1D")
    unit_direction = normalize_direction_vector(direction_vec)
    if points_array.shape[0] == 0 or peak_array.size == 0:
        return gpd.GeoDataFrame({"ridge_index": []}, geometry=[], crs=crs)
    perp_axis = np.asarray([-unit_direction[1], unit_direction[0]], dtype=np.float64)
    origin = np.mean(points_array, axis=0)
    direction_proj = np.dot(points_array - origin, unit_direction)
    t_min = float(np.min(direction_proj))
    t_max = float(np.max(direction_proj))
    line_list = _build_parallel_lines(
        origin, unit_direction, perp_axis, peak_array, t_min, t_max
    )
    return gpd.GeoDataFrame(
        {"ridge_index": np.arange(len(line_list), dtype=np.int64)},
        geometry=line_list,
        crs=crs,
    )


def _build_parallel_lines(
    origin: np.ndarray,
    unit_direction: np.ndarray,
    perp_axis: np.ndarray,
    peak_array: np.ndarray,
    t_min: float,
    t_max: float,
) -> list[LineString]:
    """Build line list for each peak location."""
    line_list: list[LineString] = []
    for peak_value in peak_array:
        start_xy = origin + unit_direction * t_min + perp_axis * peak_value
        end_xy = origin + unit_direction * t_max + perp_axis * peak_value
        line_list.append(LineString([tuple(start_xy), tuple(end_xy)]))
    return line_list
