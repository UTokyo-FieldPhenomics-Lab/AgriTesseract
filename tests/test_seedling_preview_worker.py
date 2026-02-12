"""Tests for preview worker error formatting."""

from dataclasses import dataclass

import numpy as np
import rasterio
from affine import Affine

from src.utils.seedling_detect.qthread import format_worker_exception
from src.utils.seedling_detect.qthread import (
    SeedlingInferenceInput,
    SeedlingInferenceWorker,
)


@dataclass
class _DummyMasks:
    xy: list[np.ndarray]


@dataclass
class _DummyBoxes:
    conf: np.ndarray


@dataclass
class _DummyResult:
    masks: _DummyMasks
    boxes: _DummyBoxes


def test_format_worker_exception_includes_traceback_lines() -> None:
    """Worker exception formatter should include exception type and traceback."""
    try:
        raise RuntimeError("sam3 boom")
    except RuntimeError as exc:
        message = format_worker_exception(exc)
    assert "RuntimeError" in message
    assert "sam3 boom" in message
    assert "Traceback" in message


def test_seedling_inference_worker_emits_progress_and_finished(tmp_path) -> None:
    """Full-map worker should emit progress from 0 to 100."""
    dom_path = tmp_path / "demo.tif"
    data = np.zeros((3, 32, 32), dtype=np.uint8)
    transform = Affine(1, 0, 0, 0, -1, 32)
    with rasterio.open(
        dom_path,
        "w",
        driver="GTiff",
        height=32,
        width=32,
        count=3,
        dtype=data.dtype,
        transform=transform,
    ) as dataset:
        dataset.write(data)

    class _DummyPredictor:
        def __init__(self, overrides):
            self.overrides = overrides

        def set_image(self, image_rgb):
            self.image = image_rgb

        def __call__(self, text):
            _ = text
            result = _DummyResult(
                masks=_DummyMasks(xy=[np.array([[0, 0], [8, 0], [8, 8]])]),
                boxes=_DummyBoxes(conf=np.array([0.9], dtype=float)),
            )
            return [result]

    payload = SeedlingInferenceInput(
        dom_path=str(dom_path),
        weight_path="fake.pt",
        prompt="plants",
        conf=0.25,
        iou=0.45,
        slice_size=16,
        overlap_ratio=0.0,
    )
    worker = SeedlingInferenceWorker(payload, predictor_factory=_DummyPredictor)
    progress_values: list[int] = []
    finished_payload: list[dict] = []
    worker.sigProgress.connect(progress_values.append)
    worker.sigFinished.connect(finished_payload.append)

    worker.run()

    assert progress_values[0] == 0
    assert progress_values[-1] == 100
    assert finished_payload


def test_seedling_inference_worker_reuses_predictor_across_windows(tmp_path) -> None:
    """Full-map worker should initialize predictor only once."""
    dom_path = tmp_path / "demo_reuse.tif"
    data = np.zeros((3, 32, 32), dtype=np.uint8)
    transform = Affine(1, 0, 0, 0, -1, 32)
    with rasterio.open(
        dom_path,
        "w",
        driver="GTiff",
        height=32,
        width=32,
        count=3,
        dtype=data.dtype,
        transform=transform,
    ) as dataset:
        dataset.write(data)

    init_counter = {"count": 0}

    class _CountingPredictor:
        def __init__(self, overrides):
            _ = overrides
            init_counter["count"] += 1

        def set_image(self, image_rgb):
            self.image = image_rgb

        def __call__(self, text):
            _ = text
            result = _DummyResult(
                masks=_DummyMasks(xy=[np.array([[0, 0], [8, 0], [8, 8]])]),
                boxes=_DummyBoxes(conf=np.array([0.9], dtype=float)),
            )
            return [result]

    payload = SeedlingInferenceInput(
        dom_path=str(dom_path),
        weight_path="fake.pt",
        prompt="plants",
        conf=0.25,
        iou=0.45,
        slice_size=16,
        overlap_ratio=0.0,
    )
    worker = SeedlingInferenceWorker(payload, predictor_factory=_CountingPredictor)

    worker.run()

    assert init_counter["count"] == 1
