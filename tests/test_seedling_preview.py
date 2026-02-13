"""Tests for preview-box geometry helpers."""

from affine import Affine

from src.utils.seedling_detect.preview import (
    clamp_preview_size,
    pixel_square_bounds_from_geo_center,
    preview_bounds_from_center,
)
from src.utils.seedling_detect.preview_controller import result_instance_color


def test_clamp_preview_size_limits_range() -> None:
    """Preview size should clamp to configured min/max."""
    assert clamp_preview_size(64) == 128
    assert clamp_preview_size(640) == 640
    assert clamp_preview_size(4096) == 2048


def test_preview_bounds_from_center_returns_square_bounds() -> None:
    """Bounds should be centered on input point with expected side length."""
    bounds = preview_bounds_from_center(center_x=100.0, center_y=200.0, size=640)
    assert bounds == (-220.0, -120.0, 420.0, 520.0)


def test_pixel_square_bounds_from_geo_center_uses_pixel_size() -> None:
    """Geo bounds should match square size in pixel space."""
    transform = Affine(0.1, 0.0, 100.0, 0.0, -0.1, 200.0)
    bounds = pixel_square_bounds_from_geo_center(
        center_x=110.0,
        center_y=190.0,
        size_px=640,
        transform=transform,
    )
    assert bounds == (78.0, 158.0, 142.0, 222.0)


def test_result_instance_color_is_bright_and_distinct() -> None:
    """Result polygon colors should be vivid and index-distinct."""
    color_a = result_instance_color(0)
    color_b = result_instance_color(1)

    assert color_a.getHsv()[1] >= 200
    assert color_a.getHsv()[2] >= 220
    assert color_a.hue() != color_b.hue()
