"""Cache helpers for seedling SAM3 intermediate outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import torch
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Polygon, Rectangle


def save_results_pth(results: dict[str, Any], file_path: str | Path) -> None:
    """Save inference cache dictionary as ``.pth`` file."""
    target_path = Path(file_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(results, target_path)


def load_results_pth(file_path: str | Path) -> dict[str, Any]:
    """Load inference cache dictionary from ``.pth`` file."""
    return torch.load(Path(file_path), map_location="cpu")


def _bright_colors(count: int) -> list[tuple[float, float, float]]:
    """Generate bright RGB colors in ``[0, 1]`` range."""
    if count <= 0:
        return []
    cmap = plt.get_cmap("hsv")
    return [cmap(i / max(1, count))[:3] for i in range(count)]


def _draw_slice_page(page_data: dict[str, Any]) -> plt.Figure:
    """Draw one PDF page for a single slice result."""
    fig, (ax_img, ax_map) = plt.subplots(1, 2, figsize=(11.7, 8.3), dpi=200)
    image_rgb = np.asarray(page_data["slice_image"])
    boxes_xyxy = np.asarray(page_data["boxes"])
    centers_xy = np.asarray(page_data["centers"])
    polygons = page_data["polygons"]
    colors = _bright_colors(len(polygons))

    ax_img.imshow(image_rgb)
    for idx, polygon_xy in enumerate(polygons):
        color = colors[idx]
        ax_img.add_patch(Polygon(polygon_xy, closed=True, facecolor=color, alpha=0.5))
        bbox = boxes_xyxy[idx]
        ax_img.add_patch(
            Rectangle(
                (bbox[0], bbox[1]),
                bbox[2] - bbox[0],
                bbox[3] - bbox[1],
                linewidth=1.5,
                edgecolor=color,
                facecolor="none",
            )
        )
    if centers_xy.size:
        ax_img.scatter(centers_xy[:, 0], centers_xy[:, 1], color="red", s=10)
    ax_img.set_title(str(page_data["title"]))
    ax_img.axis("off")

    full_bounds = page_data["full_bounds"]
    slice_bounds = page_data["slice_bounds"]
    ax_map.add_patch(
        Rectangle(
            (full_bounds[0], full_bounds[1]),
            full_bounds[2] - full_bounds[0],
            full_bounds[3] - full_bounds[1],
            linewidth=1.0,
            edgecolor="black",
            facecolor="none",
        )
    )
    ax_map.add_patch(
        Rectangle(
            (slice_bounds[0], slice_bounds[1]),
            slice_bounds[2] - slice_bounds[0],
            slice_bounds[3] - slice_bounds[1],
            linewidth=2.0,
            edgecolor="red",
            facecolor="none",
        )
    )
    ax_map.set_xlim(full_bounds[0], full_bounds[2])
    ax_map.set_ylim(full_bounds[1], full_bounds[3])
    ax_map.set_title("Slice Position")
    ax_map.set_aspect("equal", adjustable="box")
    return fig


def export_slice_preview_pdf(
    page_data_list: list[dict[str, Any]],
    output_path: str | Path,
) -> None:
    """Export per-slice visual pages to a single PDF file.

    Parameters
    ----------
    page_data_list : list[dict[str, Any]]
        Per-page drawing payload.
    output_path : str | Path
        Target PDF path.
    """
    pdf_path = Path(output_path)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(pdf_path) as pdf:
        for page_data in page_data_list:
            fig = _draw_slice_page(page_data)
            pdf.savefig(fig)
            plt.close(fig)
