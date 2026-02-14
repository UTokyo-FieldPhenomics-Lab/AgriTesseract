"""Tests for ridge direction helpers."""

import numpy as np
import pytest

from src.utils.rename_ids.ridge_direction import (
    compute_rotation_angle_deg,
    normalize_direction_vector,
    resolve_direction_vector,
)


def test_resolve_direction_vector_boundary_source_variants() -> None:
    """Boundary source variants should map to expected unit vectors."""
    boundary_axes = {
        "x_axis": np.asarray([1.0, 0.0], dtype=np.float64),
        "y_axis": np.asarray([0.0, 1.0], dtype=np.float64),
    }
    x_vec = resolve_direction_vector("boundary_x", boundary_axes=boundary_axes)
    y_vec = resolve_direction_vector("boundary_y", boundary_axes=boundary_axes)
    neg_x_vec = resolve_direction_vector("boundary_-x", boundary_axes=boundary_axes)
    neg_y_vec = resolve_direction_vector("boundary_-y", boundary_axes=boundary_axes)
    assert np.allclose(x_vec, np.asarray([1.0, 0.0], dtype=np.float64))
    assert np.allclose(y_vec, np.asarray([0.0, 1.0], dtype=np.float64))
    assert np.allclose(neg_x_vec, np.asarray([-1.0, 0.0], dtype=np.float64))
    assert np.allclose(neg_y_vec, np.asarray([0.0, -1.0], dtype=np.float64))


def test_resolve_direction_vector_manual_draw_from_two_points() -> None:
    """Manual draw source should return normalized vector from p0 to p1."""
    p0 = np.asarray([10.0, 10.0], dtype=np.float64)
    p1 = np.asarray([13.0, 14.0], dtype=np.float64)
    vec = resolve_direction_vector("manual_draw", p0=p0, p1=p1)
    expected = np.asarray([0.6, 0.8], dtype=np.float64)
    assert np.allclose(vec, expected)


def test_normalize_direction_vector_raises_for_zero_length() -> None:
    """Zero-length direction vector should raise ValueError."""
    with pytest.raises(ValueError, match="zero-length"):
        normalize_direction_vector(np.asarray([0.0, 0.0], dtype=np.float64))


def test_compute_rotation_angle_deg_aligns_to_positive_y() -> None:
    """Rotation angle should align input direction vector to +Y axis."""
    assert compute_rotation_angle_deg(
        np.asarray([0.0, 1.0], dtype=np.float64)
    ) == pytest.approx(0.0)
    assert compute_rotation_angle_deg(
        np.asarray([1.0, 0.0], dtype=np.float64)
    ) == pytest.approx(90.0)
    assert compute_rotation_angle_deg(
        np.asarray([-1.0, 0.0], dtype=np.float64)
    ) == pytest.approx(-90.0)
