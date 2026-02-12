"""QThread worker for SAM3 preview inference."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import traceback
from affine import Affine

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
from loguru import logger
from rasterio.windows import Window
import rasterio

from src.utils.seedling_detect.slice import SliceWindow, generate_slice_windows
from src.utils.seedling_detect.sam3 import run_preview_inference
from src.utils.seedling_detect.preview import polygon_px_to_geo
from src.utils.seedling_detect.sam3 import build_semantic_predictor, run_slice_inference


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


@dataclass
class SeedlingInferenceInput:
    """Input payload for full-map slice inference worker."""

    dom_path: str
    weight_path: str
    prompt: str
    conf: float
    iou: float
    slice_size: int
    overlap_ratio: float
    cache_dir: str = ""


class SeedlingInferenceWorker(QObject):
    """Background worker running full-map SAM3 slice inference."""

    sigProgress = Signal(int)
    sigFinished = Signal(dict)
    sigFailed = Signal(str)
    sigCancelled = Signal()

    def __init__(
        self,
        payload: SeedlingInferenceInput,
        predictor_factory: object | None = None,
    ) -> None:
        super().__init__()
        self.payload = payload
        self._predictor_factory = predictor_factory
        self._cancelled = False

    def request_cancel(self) -> None:
        """Request best-effort cancellation."""
        self._cancelled = True

    @Slot()
    def run(self) -> None:
        """Execute full-map slice inference and emit progress/results."""
        if self._cancelled:
            self.sigCancelled.emit()
            return
        self.sigProgress.emit(0)
        try:
            result_payload = self._run_full_map_inference()
        except Exception as exc:
            message = format_worker_exception(exc)
            logger.error(message)
            self.sigFailed.emit(message)
            return
        if self._cancelled:
            self.sigCancelled.emit()
            return
        self.sigProgress.emit(100)
        self.sigFinished.emit(result_payload)

    def _run_full_map_inference(self) -> dict:
        """Run slice inference loop over the full raster."""
        with rasterio.open(self.payload.dom_path) as dataset:
            windows = generate_slice_windows(
                image_width=dataset.width,
                image_height=dataset.height,
                slice_size=self.payload.slice_size,
                overlap_ratio=self.payload.overlap_ratio,
            )
            return self._infer_windows(dataset, windows)

    def _infer_windows(self, dataset, windows: list[SliceWindow]) -> dict:
        """Infer all windows and collect per-slice outputs."""
        total = max(1, len(windows))
        slice_results: list[dict] = []
        predictor = build_semantic_predictor(
            weight_path=self.payload.weight_path,
            conf=self.payload.conf,
            iou=self.payload.iou,
            cache_dir=self.payload.cache_dir,
            _predictor_override=self._predictor_factory,
        )
        for idx, window in enumerate(windows):
            if self._cancelled:
                return {"slices": slice_results}
            image_rgb, transform = _read_window_image(dataset, window)
            slice_width = int(window.x1 - window.x0)
            slice_height = int(window.y1 - window.y0)
            edge_flags = {
                "left": window.x0 == 0,
                "top": window.y0 == 0,
                "right": window.x1 >= dataset.width,
                "bottom": window.y1 >= dataset.height,
            }
            result = run_slice_inference(
                image_rgb=image_rgb,
                weight_path=self.payload.weight_path,
                prompt=self.payload.prompt,
                conf=self.payload.conf,
                iou=self.payload.iou,
                cache_dir=self.payload.cache_dir,
                predictor=predictor,
            )
            slice_results.append(
                _build_slice_result(
                    result=result,
                    transform=transform,
                    window=window,
                    slice_shape=(slice_width, slice_height),
                    is_edge=edge_flags,
                )
            )
            percent = int(((idx + 1) / total) * 100)
            self.sigProgress.emit(percent)
        return {
            "slices": slice_results,
            "meta": {
                "dom_path": str(Path(self.payload.dom_path)),
                "slice_size": int(self.payload.slice_size),
                "overlap_ratio": float(self.payload.overlap_ratio),
            },
        }


def _read_window_image(dataset, window: SliceWindow) -> tuple[np.ndarray, Affine]:
    """Read one slice image and its local affine transform."""
    raster_window = Window(
        window.x0,
        window.y0,
        window.x1 - window.x0,
        window.y1 - window.y0,
    )
    image = dataset.read(window=raster_window, boundless=True)
    image = np.transpose(image, (1, 2, 0))
    if image.shape[2] > 3:
        image = image[:, :, :3]
    transform = dataset.window_transform(raster_window)
    return image, transform


def _boxes_px_to_geo(boxes_xyxy: np.ndarray, transform: Affine) -> np.ndarray:
    """Convert slice-local boxes from pixel to geo coordinates."""
    if boxes_xyxy.size == 0:
        return np.zeros((0, 4), dtype=float)
    box_rows: list[list[float]] = []
    for x0, y0, x1, y1 in boxes_xyxy:
        gx0, gy0 = _affine_xy(transform, float(x0), float(y0))
        gx1, gy1 = _affine_xy(transform, float(x1), float(y1))
        box_rows.append([min(gx0, gx1), min(gy0, gy1), max(gx0, gx1), max(gy0, gy1)])
    return np.asarray(box_rows, dtype=float)


def _affine_xy(
    transform: Affine, x_value: float, y_value: float
) -> tuple[float, float]:
    """Apply affine transform and return x/y as floats."""
    point_xy = transform * (x_value, y_value)
    return float(point_xy[0]), float(point_xy[1])


def _build_slice_result(
    result: dict,
    transform: Affine,
    window: SliceWindow,
    slice_shape: tuple[int, int],
    is_edge: dict[str, bool],
) -> dict:
    """Build one serializable slice result payload."""
    polygons_geo = [
        polygon_px_to_geo(poly, transform) for poly in result["polygons_px"]
    ]
    boxes_px = np.asarray(result["boxes_xyxy"], dtype=float)
    boxes_geo = _boxes_px_to_geo(
        boxes_px,
        transform,
    )
    return {
        "row": int(window.row),
        "col": int(window.col),
        "boxes_px": boxes_px,
        "boxes_geo": boxes_geo,
        "scores": np.asarray(result["scores"], dtype=float),
        "polygons_geo": polygons_geo,
        "slice_shape": (int(slice_shape[0]), int(slice_shape[1])),
        "is_edge": {
            "left": bool(is_edge.get("left", False)),
            "top": bool(is_edge.get("top", False)),
            "right": bool(is_edge.get("right", False)),
            "bottom": bool(is_edge.get("bottom", False)),
        },
    }


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
