"""SAM3 preview inference helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from loguru import logger


def _extract_polygons_from_mask_xy(result_obj: Any) -> list[np.ndarray]:
    """Extract polygon arrays from ``masks.xy`` fallback field."""
    masks_obj = getattr(result_obj, "masks", None)
    if masks_obj is None:
        return []
    xy_list = getattr(masks_obj, "xy", None)
    if xy_list is None:
        return []
    return [
        np.asarray(poly_xy, dtype=float) for poly_xy in xy_list if len(poly_xy) >= 3
    ]


def _extract_scores(result_obj: Any, polygon_count: int) -> np.ndarray:
    """Extract score array with fallback default confidence."""
    boxes_obj = getattr(result_obj, "boxes", None)
    if boxes_obj is None or getattr(boxes_obj, "conf", None) is None:
        return np.ones((polygon_count,), dtype=float)
    conf_data = boxes_obj.conf
    if hasattr(conf_data, "detach"):
        return conf_data.detach().cpu().numpy().astype(float)
    return np.asarray(conf_data, dtype=float)


def run_preview_inference(
    image_rgb: np.ndarray,
    weight_path: str,
    prompt: str,
    conf: float,
    iou: float,
    cache_dir: str | None = None,
    _predictor_override: Any | None = None,
) -> dict[str, Any]:
    """Run SAM3 preview inference and return polygon masks.

    Parameters
    ----------
    image_rgb : numpy.ndarray
        Preview image with shape ``(H, W, 3)``.
    weight_path : str
        Path to SAM3 model weight file.
    prompt : str
        Text prompt for SAM3.
    conf : float
        Confidence threshold.
    iou : float
        IoU threshold.
    _predictor_override : Any | None, optional
        Internal parameter for testing dependency injection.
    """
    prepared_image = _prepare_preview_image(image_rgb)
    predictor = _build_semantic_predictor(
        weight_path,
        conf,
        iou,
        cache_dir,
        _predictor_override,
    )
    predictor.set_image(prepared_image)
    results = predictor(text=[prompt])
    if not isinstance(results, (list, tuple)):
        results = [results]
    if not results:
        return {"polygons_px": [], "scores": np.zeros((0,), dtype=float)}

    result_obj = results[0]
    logger.info(result_obj)

    polygons_px = _extract_polygons_from_mask_xy(result_obj)
    scores = _extract_scores(result_obj, len(polygons_px))
    masks_obj = getattr(result_obj, "masks", None)
    xy_list = [] if masks_obj is None else (getattr(masks_obj, "xy", None) or [])
    mask_data = None if masks_obj is None else getattr(masks_obj, "data", None)
    mask_count = 0
    if mask_data is not None:
        mask_array = (
            mask_data.detach().cpu().numpy()
            if hasattr(mask_data, "detach")
            else np.asarray(mask_data)
        )
        mask_count = int(mask_array.shape[0]) if mask_array.ndim == 3 else 0
    logger.info(
        f"Preview SAM3 counts raw_masks_data={mask_count} "
        f"scores={scores}"
        f"raw_masks_xy={len(xy_list)} "
        f"raw_polygons={len(polygons_px)}"
    )
    return {
        "polygons_px": polygons_px,
        "scores": scores,
    }


def run_slice_inference(
    image_rgb: np.ndarray,
    weight_path: str,
    prompt: str,
    conf: float,
    iou: float,
    cache_dir: str | None = None,
    _predictor_override: Any | None = None,
) -> dict[str, Any]:
    """Run one slice inference and return polygons, boxes, and scores.

    Parameters
    ----------
    image_rgb : numpy.ndarray
        Slice image with shape ``(H, W, C)``.
    weight_path : str
        SAM3 model path.
    prompt : str
        Text prompt.
    conf : float
        Confidence threshold.
    iou : float
        IoU threshold.
    cache_dir : str | None, optional
        Optional cache directory for predictor outputs.
    _predictor_override : Any | None, optional
        Test-only predictor class override.
    """
    preview_data = run_preview_inference(
        image_rgb=image_rgb,
        weight_path=weight_path,
        prompt=prompt,
        conf=conf,
        iou=iou,
        cache_dir=cache_dir,
        _predictor_override=_predictor_override,
    )
    polygons_px = preview_data["polygons_px"]
    boxes_xyxy = polygons_to_boxes_xyxy(polygons_px)
    return {
        "polygons_px": polygons_px,
        "boxes_xyxy": boxes_xyxy,
        "scores": np.asarray(preview_data["scores"], dtype=float),
    }


def polygons_to_boxes_xyxy(polygons_px: list[np.ndarray]) -> np.ndarray:
    """Compute xyxy boxes from polygon list."""
    if not polygons_px:
        return np.zeros((0, 4), dtype=float)
    box_list: list[list[float]] = []
    for polygon_xy in polygons_px:
        poly_xy = np.asarray(polygon_xy, dtype=float)
        if poly_xy.ndim != 2 or poly_xy.shape[0] < 3:
            continue
        x_min = float(np.min(poly_xy[:, 0]))
        y_min = float(np.min(poly_xy[:, 1]))
        x_max = float(np.max(poly_xy[:, 0]))
        y_max = float(np.max(poly_xy[:, 1]))
        box_list.append([x_min, y_min, x_max, y_max])
    if not box_list:
        return np.zeros((0, 4), dtype=float)
    return np.asarray(box_list, dtype=float)


def _prepare_preview_image(image_rgb: np.ndarray) -> np.ndarray:
    """Normalize preview image for Ultralytics predictor input."""
    image_data = np.asarray(image_rgb)
    if image_data.dtype != np.uint8:
        max_value = float(np.max(image_data))
        image_data = (
            np.zeros_like(image_data, dtype=np.uint8)
            if max_value <= 0
            else (image_data / max_value * 255).astype(np.uint8)
        )
    if image_data.ndim == 2:
        image_data = np.stack([image_data, image_data, image_data], axis=2)
    if image_data.shape[2] > 3:
        image_data = image_data[:, :, :3]
    return np.ascontiguousarray(image_data)


def _load_predictor_class() -> Any:
    """Load SAM3 semantic predictor class from ultralytics."""
    try:
        from ultralytics.models.sam import SAM3SemanticPredictor
    except Exception as exc:
        raise RuntimeError(
            "SAM3SemanticPredictor is required for SAM3 preview inference"
        ) from exc
    return SAM3SemanticPredictor


def _build_semantic_predictor(
    weight_path: str,
    conf: float,
    iou: float,
    cache_dir: str | None,
    _predictor_override: Any | None,
) -> Any:
    """Build SAM3 semantic predictor instance."""
    predictor_type = (
        _load_predictor_class() if _predictor_override is None else _predictor_override
    )
    if predictor_type is None:
        raise RuntimeError("Invalid SAM3 predictor class")
    project_dir = _resolve_preview_project_dir(cache_dir)
    overrides = {
        "conf": conf,
        "iou": iou,
        "task": "segment",
        "mode": "predict",
        "model": weight_path,
        "project": str(project_dir),
        "name": "sam3_preview",
        "exist_ok": True,
        "save": True,
        "verbose": False,
    }
    return predictor_type(overrides=overrides)


def _resolve_preview_project_dir(cache_dir: str | None) -> Path:
    """Resolve preview output project directory for Ultralytics."""
    if cache_dir:
        base_dir = Path(cache_dir)
    else:
        base_dir = Path("app") / "cache"
    target_dir = base_dir / "ultralytics"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir
