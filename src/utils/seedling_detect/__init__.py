"""Seedling detection submodule for SAM3 inference workflows.

Re-exports all public API symbols for backward compatibility.
"""

from src.utils.seedling_detect.cache import (
    export_slice_preview_pdf,
    load_results_pth,
    save_results_pth,
)
from src.utils.seedling_detect.io import (
    save_bbox_shp,
    save_mask_polygon_shp,
    save_point_shp,
)
from src.utils.seedling_detect.points import (
    PointAction,
    SeedlingPoint,
    SeedlingPointStore,
)
from src.utils.seedling_detect.preview import (
    clamp_preview_size,
    pixel_square_bounds_from_geo_center,
    polygon_px_to_geo,
    preview_bounds_from_center,
)
from src.utils.seedling_detect.sam3 import run_preview_inference
from src.utils.seedling_detect.qthread import (
    SeedlingInferenceInput,
    SeedlingInferenceWorker,
)
from src.utils.seedling_detect.slice import (
    SliceWindow,
    bbox_centers_xyxy,
    generate_slice_windows,
)

__all__ = [
    "PointAction",
    "SeedlingPoint",
    "SeedlingPointStore",
    "SliceWindow",
    "bbox_centers_xyxy",
    "clamp_preview_size",
    "export_slice_preview_pdf",
    "generate_slice_windows",
    "load_results_pth",
    "pixel_square_bounds_from_geo_center",
    "polygon_px_to_geo",
    "preview_bounds_from_center",
    "run_preview_inference",
    "SeedlingInferenceInput",
    "SeedlingInferenceWorker",
    "save_bbox_shp",
    "save_mask_polygon_shp",
    "save_point_shp",
    "save_results_pth",
]
