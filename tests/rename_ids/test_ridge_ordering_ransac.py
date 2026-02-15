"""Tests for optional RANSAC filtering in ridge ordering."""

from __future__ import annotations

import numpy as np

from src.utils.rename_ids.ridge_ordering import (
    assign_points_to_ridges,
    build_ridge_intervals,
)


def test_ransac_disabled_keeps_all_assigned_points_as_inliers() -> None:
    """Disabling RANSAC should preserve all assigned points as inliers."""
    ridge_intervals = build_ridge_intervals(np.asarray([0.0]), buffer=2.0)
    ridge_id, is_inlier = assign_points_to_ridges(
        projected_x=np.asarray([0.1, 0.2, 0.3, 4.5], dtype=np.float64),
        projected_y=np.asarray([0.0, 1.0, 2.0, 3.0], dtype=np.float64),
        effective_mask=np.asarray([True, True, True, False]),
        ridge_intervals=ridge_intervals,
        ransac_enabled=False,
        residual=0.05,
        max_trials=100,
    )

    assert np.all(ridge_id[:3] == 0)
    assert np.all(is_inlier[:3])
    assert int(ridge_id[3]) == -1
    assert bool(is_inlier[3]) is False


def test_ransac_enabled_marks_outlier_but_keeps_ridge_assignment() -> None:
    """RANSAC should flag outlier points while preserving ridge IDs."""
    ridge_intervals = build_ridge_intervals(np.asarray([0.0]), buffer=8.0)
    ridge_id, is_inlier = assign_points_to_ridges(
        projected_x=np.asarray([0.0, 1.0, 2.0, 7.0], dtype=np.float64),
        projected_y=np.asarray([0.0, 1.0, 2.0, 3.0], dtype=np.float64),
        effective_mask=np.asarray([True, True, True, True]),
        ridge_intervals=ridge_intervals,
        ransac_enabled=True,
        residual=0.2,
        max_trials=200,
    )

    assert np.all(ridge_id == 0)
    assert np.count_nonzero(is_inlier) == 3
    assert bool(is_inlier[-1]) is False


def test_ransac_residual_changes_inlier_count() -> None:
    """Residual threshold should control strictness of inlier filtering."""
    ridge_intervals = build_ridge_intervals(np.asarray([0.0]), buffer=8.0)
    projected_x = np.asarray([0.0, 1.0, 2.0, 3.8], dtype=np.float64)
    projected_y = np.asarray([0.0, 1.0, 2.0, 3.0], dtype=np.float64)
    mask = np.asarray([True, True, True, True])

    _, loose_inlier = assign_points_to_ridges(
        projected_x=projected_x,
        projected_y=projected_y,
        effective_mask=mask,
        ridge_intervals=ridge_intervals,
        ransac_enabled=True,
        residual=1.0,
        max_trials=200,
    )
    _, strict_inlier = assign_points_to_ridges(
        projected_x=projected_x,
        projected_y=projected_y,
        effective_mask=mask,
        ridge_intervals=ridge_intervals,
        ransac_enabled=True,
        residual=0.2,
        max_trials=200,
    )

    assert np.count_nonzero(loose_inlier) > np.count_nonzero(strict_inlier)
