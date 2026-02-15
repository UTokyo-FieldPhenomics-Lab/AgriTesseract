"""Tests for SAM3 preview helper extraction logic."""

from dataclasses import dataclass

import numpy as np

from src.utils.seedling_detect.sam3 import (
    _extract_polygons_from_mask_xy,
    _extract_scores,
    run_preview_inference,
    run_slice_inference,
)


@dataclass
class _DummyMasks:
    xy: list[np.ndarray]
    data: object | None = None


@dataclass
class _DummyBoxes:
    conf: np.ndarray


@dataclass
class _DummyResult:
    masks: _DummyMasks
    boxes: _DummyBoxes


def test_extract_polygons_from_mask_xy_filters_invalid() -> None:
    """Polygon extraction should keep only valid polygon arrays."""
    result_obj = _DummyResult(
        masks=_DummyMasks(xy=[np.array([[0, 0], [1, 0], [1, 1]]), np.array([[0, 0]])]),
        boxes=_DummyBoxes(conf=np.array([0.8, 0.2])),
    )
    polygons = _extract_polygons_from_mask_xy(result_obj)
    assert len(polygons) == 1
    assert polygons[0].shape == (3, 2)


def test_extract_scores_returns_default_when_boxes_missing() -> None:
    """Score extraction should return ones when boxes are absent."""

    class _NoBoxes:
        boxes = None

    scores = _extract_scores(_NoBoxes(), polygon_count=3)
    assert np.allclose(scores, np.ones((3,), dtype=float))


def test_run_preview_inference_uses_text_prompt_list() -> None:
    """Preview inference should call predictor with text list API."""
    seen_overrides = {}

    class _DummyPredictor:
        def __init__(self, overrides):
            seen_overrides.update(overrides)
            self.overrides = overrides
            self.image = None
            self.text_kwargs = None

        def set_image(self, image_rgb):
            self.image = image_rgb

        def __call__(self, text):
            self.text_kwargs = text
            result = _DummyResult(
                masks=_DummyMasks(xy=[np.array([[0, 0], [1, 0], [1, 1]])]),
                boxes=_DummyBoxes(conf=np.array([0.9])),
            )
            return [result]

    image_rgb = np.zeros((10, 10, 3), dtype=np.uint8)
    output = run_preview_inference(
        image_rgb=image_rgb,
        weight_path="sam3.pt",
        prompt="plants",
        conf=0.3,
        iou=0.4,
        _predictor_override=_DummyPredictor,
    )

    assert len(output["polygons_px"]) == 1
    assert np.allclose(output["scores"], np.array([0.9]))
    assert seen_overrides["save"] is True
    assert "project" in seen_overrides


def test_run_preview_inference_converts_image_to_contiguous() -> None:
    """Preview inference should pass C-contiguous image to predictor."""

    class _DummyPredictor:
        def __init__(self, overrides):
            self.overrides = overrides

        def set_image(self, image_rgb):
            assert image_rgb.flags["C_CONTIGUOUS"]

        def __call__(self, text):
            result = _DummyResult(
                masks=_DummyMasks(xy=[np.array([[0, 0], [1, 0], [1, 1]])]),
                boxes=_DummyBoxes(conf=np.array([0.9])),
            )
            return [result]

    base_image = np.zeros((12, 14, 3), dtype=np.uint8)
    non_contiguous = base_image[:, ::-1, :]
    assert not non_contiguous.flags["C_CONTIGUOUS"]

    output = run_preview_inference(
        image_rgb=non_contiguous,
        weight_path="sam3.pt",
        prompt="plants",
        conf=0.3,
        iou=0.4,
        _predictor_override=_DummyPredictor,
    )
    assert len(output["polygons_px"]) == 1


def test_run_slice_inference_returns_boxes_and_scores() -> None:
    """Slice inference should return derived xyxy boxes."""

    class _DummyPredictor:
        def __init__(self, overrides):
            self.overrides = overrides

        def set_image(self, image_rgb):
            self.image = image_rgb

        def __call__(self, text):
            result = _DummyResult(
                masks=_DummyMasks(xy=[np.array([[1, 2], [5, 2], [5, 6], [1, 6]])]),
                boxes=_DummyBoxes(conf=np.array([0.91], dtype=float)),
            )
            return [result]

    output = run_slice_inference(
        image_rgb=np.zeros((8, 8, 3), dtype=np.uint8),
        weight_path="sam3.pt",
        prompt="plants",
        conf=0.2,
        iou=0.3,
        _predictor_override=_DummyPredictor,
    )

    assert output["boxes_xyxy"].shape == (1, 4)
    assert np.allclose(output["boxes_xyxy"][0], [1.0, 2.0, 5.0, 6.0])
    assert np.allclose(output["scores"], np.array([0.91]))
