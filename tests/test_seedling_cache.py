"""Tests for seedling cache save/load and PDF rendering."""

from pathlib import Path

import numpy as np

from src.utils.seedling_cache import (
    export_slice_preview_pdf,
    load_results_pth,
    save_results_pth,
)


def test_save_and_load_results_pth_round_trip(tmp_path: Path) -> None:
    """PTH cache should preserve nested dictionaries."""
    data = {
        "meta": {"prompt": "plants", "slice_size": 640},
        "slices": [{"slice_id": 0, "scores": [0.9]}],
        "merged": {"boxes": [[0.0, 0.0, 1.0, 1.0]]},
    }
    pth_path = tmp_path / "results.pth"

    save_results_pth(data, pth_path)
    loaded = load_results_pth(pth_path)

    assert loaded["meta"]["prompt"] == "plants"
    assert loaded["slices"][0]["slice_id"] == 0


def test_export_slice_preview_pdf_creates_pdf(tmp_path: Path) -> None:
    """Preview PDF export should generate non-empty file."""
    pages = [
        {
            "slice_image": np.zeros((64, 64, 3), dtype=np.uint8),
            "boxes": np.array([[10.0, 10.0, 30.0, 40.0]]),
            "centers": np.array([[20.0, 25.0]]),
            "polygons": [[(10.0, 10.0), (30.0, 10.0), (30.0, 40.0), (10.0, 40.0)]],
            "slice_bounds": (0.0, 0.0, 64.0, 64.0),
            "full_bounds": (0.0, 0.0, 256.0, 256.0),
            "title": "slice_0_0",
        }
    ]
    pdf_path = tmp_path / "preview.pdf"

    export_slice_preview_pdf(pages, pdf_path)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0
