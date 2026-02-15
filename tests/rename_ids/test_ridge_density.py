"""Tests for ridge density helper functions."""

from __future__ import annotations

import numpy as np
import pytest

from src.utils.rename_ids.ridge_density import (
    build_density_histogram,
    build_ridge_lines_from_peaks,
    detect_ridge_peaks,
    project_points_to_perp_axis,
)


def test_project_points_to_perp_axis_returns_empty_for_empty_points() -> None:
    """Projection keeps empty input as empty output."""
    result = project_points_to_perp_axis(
        np.empty((0, 2), dtype=np.float64),
        np.asarray([1.0, 0.0], dtype=np.float64),
    )
    assert result.shape == (0,)


def test_build_density_histogram_and_single_peak_detection() -> None:
    """Histogram bins and peak detection work for one dominant ridge."""
    projected = np.asarray([0.0, 0.1, 0.2, 2.0, 2.1], dtype=np.float64)
    x_bins, counts = build_density_histogram(projected, strength_ratio=1.0)
    peak_indices, peak_heights = detect_ridge_peaks(counts, distance=1, height=2)
    peak_x = x_bins[peak_indices]

    assert np.allclose(x_bins, np.asarray([0.0, 2.0]))
    assert np.allclose(counts, np.asarray([3, 2]))
    assert np.allclose(peak_x, np.asarray([0.0]))
    assert np.allclose(peak_heights, np.asarray([3.0]))


def test_detect_ridge_peaks_finds_multiple_peaks() -> None:
    """Peak detection returns separated peaks with distance constraint."""
    counts = np.asarray([0, 5, 0, 4, 0, 6, 0], dtype=np.int64)
    peak_indices, peak_heights = detect_ridge_peaks(counts, distance=2, height=3)

    assert np.allclose(peak_indices, np.asarray([1, 3, 5]))
    assert np.allclose(peak_heights, np.asarray([5.0, 4.0, 6.0]))


def test_build_ridge_lines_from_peaks_returns_parallel_lines() -> None:
    """Generated ridge lines are parallel to direction vector."""
    points = np.asarray(
        [[0.0, 0.0], [4.0, 0.0], [0.0, 4.0], [4.0, 4.0]],
        dtype=np.float64,
    )
    peak_x = np.asarray([-1.0, 1.0], dtype=np.float64)
    lines_gdf = build_ridge_lines_from_peaks(peak_x, points, np.asarray([1.0, 0.0]))

    assert len(lines_gdf) == 2
    first_coords = list(lines_gdf.geometry.iloc[0].coords)
    second_coords = list(lines_gdf.geometry.iloc[1].coords)
    assert first_coords[0][1] == first_coords[1][1]
    assert second_coords[0][1] == second_coords[1][1]


@pytest.mark.parametrize(
    "strength_ratio,distance,height",
    [
        (0.0, 1, 0),
        (-1.0, 1, 0),
        (1.0, 0, 0),
        (1.0, 1, -1),
    ],
)
def test_invalid_parameters_raise(
    strength_ratio: float,
    distance: int,
    height: float,
) -> None:
    """Invalid parameters raise ValueError as contract requires."""
    if strength_ratio <= 0:
        with pytest.raises(ValueError):
            build_density_histogram(np.asarray([0.0]), strength_ratio)
        return
    with pytest.raises(ValueError):
        detect_ridge_peaks(np.asarray([1, 2, 3]), distance=distance, height=height)


def test_invalid_shapes_raise_value_error() -> None:
    """Shape errors are rejected for points and peaks inputs."""
    with pytest.raises(ValueError):
        project_points_to_perp_axis(np.asarray([1.0, 2.0]), np.asarray([1.0, 0.0]))
    with pytest.raises(ValueError):
        build_ridge_lines_from_peaks(
            peak_x=np.asarray([[1.0]]),
            points_xy=np.asarray([[0.0, 0.0]]),
            direction_vec=np.asarray([1.0, 0.0]),
        )
