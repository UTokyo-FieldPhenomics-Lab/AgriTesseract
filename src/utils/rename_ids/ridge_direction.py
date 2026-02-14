"""Ridge direction vector and rotation helpers.

This module converts UI source selections into a normalized 2D direction vector
and calculates the corresponding angle used to align the vector to +Y.
"""

from __future__ import annotations

import math
from typing import Mapping

import numpy as np


def normalize_direction_vector(vector: np.ndarray) -> np.ndarray:
    """Normalize one 2D direction vector.

    Parameters
    ----------
    vector : numpy.ndarray
        Input vector with shape ``(2,)``.

    Returns
    -------
    numpy.ndarray
        Unit vector with shape ``(2,)`` and dtype ``float64``.

    Raises
    ------
    ValueError
        Raised when vector shape is invalid or length is zero.

    Examples
    --------
    >>> normalize_direction_vector(np.asarray([3.0, 4.0]))
    array([0.6, 0.8])
    """
    vec_array = np.asarray(vector, dtype=np.float64)
    if vec_array.shape != (2,):
        raise ValueError("direction vector must have shape (2,)")
    vec_norm = float(np.linalg.norm(vec_array))
    if vec_norm <= 1e-12:
        raise ValueError("zero-length direction vector")
    return vec_array / vec_norm


def _boundary_vector_by_source(
    source: str,
    boundary_axes: Mapping[str, np.ndarray],
) -> np.ndarray:
    """Read one boundary-based direction vector by source key.

    Parameters
    ----------
    source : str
        Source key in ``boundary_x``, ``boundary_y``, ``boundary_-x``,
        ``boundary_-y``.
    boundary_axes : Mapping[str, numpy.ndarray]
        Boundary axes map containing ``x_axis`` and ``y_axis``.

    Returns
    -------
    numpy.ndarray
        Direction vector with shape ``(2,)``.
    """
    if source == "boundary_x":
        return np.asarray(boundary_axes["x_axis"], dtype=np.float64)
    if source == "boundary_y":
        return np.asarray(boundary_axes["y_axis"], dtype=np.float64)
    if source == "boundary_-x":
        return -np.asarray(boundary_axes["x_axis"], dtype=np.float64)
    if source == "boundary_-y":
        return -np.asarray(boundary_axes["y_axis"], dtype=np.float64)
    raise ValueError(f"unsupported boundary direction source: {source}")


def resolve_direction_vector(
    source: str,
    boundary_axes: Mapping[str, np.ndarray] | None = None,
    p0: np.ndarray | None = None,
    p1: np.ndarray | None = None,
) -> np.ndarray:
    """Resolve a normalized direction vector from source and inputs.

    Parameters
    ----------
    source : str
        Source key in ``boundary_x``, ``boundary_y``, ``boundary_-x``,
        ``boundary_-y``, ``manual_draw``.
    boundary_axes : Mapping[str, numpy.ndarray], optional
        Boundary axis dictionary used by boundary-based sources.
    p0 : numpy.ndarray, optional
        Manual draw start point with shape ``(2,)``.
    p1 : numpy.ndarray, optional
        Manual draw end point with shape ``(2,)``.

    Returns
    -------
    numpy.ndarray
        Normalized direction vector with shape ``(2,)``.

    Raises
    ------
    ValueError
        Raised when required inputs are missing or invalid.

    Examples
    --------
    >>> resolve_direction_vector("manual_draw", p0=np.array([0, 0]), p1=np.array([1, 0]))
    array([1., 0.])
    """
    if source == "manual_draw":
        if p0 is None or p1 is None:
            raise ValueError("manual_draw requires both p0 and p1")
        return normalize_direction_vector(
            np.asarray(p1, dtype=np.float64) - np.asarray(p0, dtype=np.float64)
        )
    if boundary_axes is None:
        raise ValueError("boundary source requires boundary_axes")
    return normalize_direction_vector(_boundary_vector_by_source(source, boundary_axes))


def compute_rotation_angle_deg(direction_vector: np.ndarray) -> float:
    """Compute rotation angle to align direction vector with +Y axis.

    Parameters
    ----------
    direction_vector : numpy.ndarray
        Direction vector with shape ``(2,)``.

    Returns
    -------
    float
        Rotation angle in degrees compatible with ``MapCanvas.set_rotation``.

    Examples
    --------
    >>> compute_rotation_angle_deg(np.asarray([1.0, 0.0]))
    -90.0
    """
    unit_vec = normalize_direction_vector(direction_vector)
    return float(-math.degrees(math.atan2(unit_vec[0], unit_vec[1])))
