"""QThread worker for SAM3 preview inference."""

from __future__ import annotations

from dataclasses import dataclass
import traceback
from affine import Affine

import numpy as np
from PySide6.QtCore import QObject, Signal, Slot
from loguru import logger

from src.utils.seedling_sam3 import run_preview_inference


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
            _polygon_px_to_geo(poly_px, self.payload.transform)
            for poly_px in result_data["polygons_px"]
        ]

        # _visualize_preview_results(
        #     self.payload.image_rgb,
        #     result_data["polygons_px"],
        #     polygons_geo,
        #     "./app/cache/ultralytics/sam3_preview/debug_matplotlib.png",
        # )

        score_list = np.asarray(result_data["scores"], dtype=float).tolist()
        self.sigFinished.emit(polygons_geo, score_list)


def _visualize_preview_results(
    image_rgb: np.ndarray,
    polygons_px: list[np.ndarray],
    polygons_geo: list[np.ndarray],
    output_path: str,
) -> None:
    """Debug visualization for transform verification."""
    try:
        import matplotlib.pyplot as plt
        from matplotlib.collections import PatchCollection
        from matplotlib.patches import Polygon
    except ImportError:
        logger.warning("Matplotlib not available for preview debug visualization")
        return

    try:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 8))

        # Generate distinct colors
        num_polygons = len(polygons_px)
        cmap = plt.get_cmap("hsv")
        colors = [cmap(i / num_polygons) for i in range(num_polygons)]

        # Left: Pixel space
        ax1.imshow(image_rgb)
        patches_px = [Polygon(poly, closed=True) for poly in polygons_px]
        p_px = PatchCollection(
            patches_px, alpha=0.4, facecolor=colors, edgecolor="white", linewidth=1
        )
        ax1.add_collection(p_px)
        ax1.set_title(f"Pixel Space (n={num_polygons})")
        ax1.set_xlabel("X (px)")
        ax1.set_ylabel("Y (px)")

        # Right: Geo space
        patches_geo = [Polygon(poly, closed=True) for poly in polygons_geo]
        p_geo = PatchCollection(
            patches_geo, alpha=0.4, facecolor=colors, edgecolor="black", linewidth=1
        )
        ax2.add_collection(p_geo)
        ax2.autoscale()
        ax2.set_aspect("equal")
        ax2.set_title(f"Geo Space (n={num_polygons})")
        ax2.set_xlabel("X (geo)")
        ax2.set_ylabel("Y (geo)")

        # Save
        from pathlib import Path

        save_path = Path(output_path)
        save_path.parent.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(save_path)
        plt.close(fig)
        logger.info(f"Saved debug visualization to {save_path}")
    except Exception as exc:
        logger.warning(f"Failed to save debug visualization: {exc}")


def _polygon_px_to_geo(polygon_px: np.ndarray, transform: Affine) -> np.ndarray:
    """Convert polygon from patch pixel coordinates to geo coordinates."""
    poly_xy = np.asarray(polygon_px, dtype=float)
    geo_points = []
    for x_coord, y_coord in poly_xy:
        x_geo = (
            transform.c + transform.a * float(x_coord) + transform.b * float(y_coord)
        )
        y_geo = (
            transform.f + transform.d * float(x_coord) + transform.e * float(y_coord)
        )
        geo_points.append([float(x_geo), float(y_geo)])
    return np.asarray(geo_points, dtype=float)


def format_worker_exception(exc: Exception) -> str:
    """Format exception into message with traceback details."""
    trace_text = traceback.format_exc()
    if not trace_text or trace_text == "NoneType: None\n":
        trace_text = "\n".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
    return f"{type(exc).__name__}: {exc}\n{trace_text.strip()}"
