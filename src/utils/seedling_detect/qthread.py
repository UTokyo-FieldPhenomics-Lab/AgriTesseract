"""QThread worker for SAM3 preview inference."""

from __future__ import annotations

from dataclasses import dataclass
import traceback
from affine import Affine

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
from loguru import logger

from src.utils.seedling_detect.sam3 import run_preview_inference
from src.utils.seedling_detect.preview import polygon_px_to_geo


@dataclass
class PreviewInferenceInput:
    """Input payload for preview inference worker."""

    image_rgb: np.ndarray
    transform: Affine
    weight_path: str
    prompt: str
    conf: float
    iou: float
    cache_dir: str


class SeedlingPreviewWorker(QObject):
    """Background worker running SAM3 preview inference."""

    sigFinished = Signal(list, list)
    sigFailed = Signal(str)
    sigCancelled = Signal()

    def __init__(self, payload: PreviewInferenceInput) -> None:
        super().__init__()
        self.payload = payload
        self._cancelled = False

    def request_cancel(self) -> None:
        """Request best-effort cancellation."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Execute preview inference and emit results."""
        if self._cancelled:
            self.sigCancelled.emit()
            return
        try:
            result_data = run_preview_inference(
                image_rgb=self.payload.image_rgb,
                weight_path=self.payload.weight_path,
                prompt=self.payload.prompt,
                conf=self.payload.conf,
                iou=self.payload.iou,
                cache_dir=self.payload.cache_dir,
            )
        except Exception as exc:
            message = format_worker_exception(exc)
            logger.error(message)
            self.sigFailed.emit(message)
            return
        if self._cancelled:
            self.sigCancelled.emit()
            return
        polygons_geo = [
            polygon_px_to_geo(poly_px, self.payload.transform)
            for poly_px in result_data["polygons_px"]
        ]

        score_list = np.asarray(result_data["scores"], dtype=float).tolist()
        self.sigFinished.emit(polygons_geo, score_list)


def format_worker_exception(exc: Exception) -> str:
    """Format exception into message with traceback details.

    Parameters
    ----------
    exc : Exception
        The exception to format.

    Returns
    -------
    str
        Formatted message with traceback text.
    """
    trace_text = traceback.format_exc()
    if not trace_text or trace_text == "NoneType: None\n":
        trace_text = "\n".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
    return f"{type(exc).__name__}: {exc}\n{trace_text.strip()}"
