"""Ridge diagnostics controller for figure and map sync."""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np

from src.utils.rename_ids.ridge_density import (
    build_density_histogram,
    build_ridge_lines_from_peaks,
    detect_ridge_peaks,
    project_points_to_perp_axis,
)


def distance_m_to_peak_bins(distance_m: float, strength_ratio: float) -> int:
    """Convert min ridge distance in meters to histogram-bin distance.

    Parameters
    ----------
    distance_m : float
        Minimum ridge separation in projected-axis meters.
    strength_ratio : float
        Histogram bin width in meters.

    Returns
    -------
    int
        Minimum distance in histogram bins for ``scipy.signal.find_peaks``.
    """
    if strength_ratio <= 0:
        return 1
    if distance_m <= 0:
        return 1
    return max(1, int(np.ceil(distance_m / strength_ratio)))


class RidgeDetectionController:
    """Drive ridge diagnostics rendering for panel and map overlay.

    Parameters
    ----------
    map_canvas : Any
        Map canvas object exposing ``remove_layer`` and ``add_vector_layer``.
    figure_panel : Any
        Figure panel exposing ``clear``, ``set_density_curve``, ``set_peaks`` and
        ``set_x_range`` methods.
    overlay_layer_name : str, optional
        Layer name for detected ridge lines.
    """

    def __init__(
        self,
        map_canvas: Any,
        figure_panel: Any,
        overlay_layer_name: str = "ridge_detected_lines",
    ) -> None:
        self._map_canvas = map_canvas
        self._figure_panel = figure_panel
        self._overlay_layer_name = overlay_layer_name

    def update(
        self,
        effective_points_xy: np.ndarray,
        direction_vector: np.ndarray | None,
        strength_ratio: float,
        distance: float,
        height: float,
        crs: Any = None,
    ) -> dict[str, Any]:
        """Recompute diagnostics and refresh panel/map outputs."""
        if direction_vector is None:
            return self._clear_outputs(crs)
        points_array = np.asarray(effective_points_xy, dtype=np.float64)
        if (
            points_array.ndim != 2
            or points_array.shape[1] != 2
            or len(points_array) < 2
        ):
            return self._clear_outputs(crs)
        return self._compute_and_render(
            points_array,
            np.asarray(direction_vector, dtype=np.float64),
            strength_ratio,
            distance,
            height,
            crs,
        )

    def _compute_and_render(
        self,
        points_array: np.ndarray,
        direction_vector: np.ndarray,
        strength_ratio: float,
        distance: float,
        height: float,
        crs: Any,
    ) -> dict[str, Any]:
        projected_x = project_points_to_perp_axis(points_array, direction_vector)
        x_bins, counts = build_density_histogram(projected_x, strength_ratio)
        distance_bins = distance_m_to_peak_bins(distance, strength_ratio)
        peak_indices, peak_heights = detect_ridge_peaks(counts, distance_bins, height)
        peak_x = x_bins[peak_indices] if len(peak_indices) > 0 else np.asarray([])
        lines_gdf = build_ridge_lines_from_peaks(
            peak_x, points_array, direction_vector, crs
        )
        self._render_figure(x_bins, counts, peak_x, peak_heights, height)
        self._replace_overlay(lines_gdf)
        return self._build_payload(
            x_bins, counts, peak_indices, peak_x, peak_heights, lines_gdf
        )

    def _render_figure(
        self,
        x_bins: np.ndarray,
        counts: np.ndarray,
        peak_x: np.ndarray,
        peak_heights: np.ndarray,
        threshold_height: float,
    ) -> None:
        self._figure_panel.set_density_curve(x_bins, counts)
        self._figure_panel.set_peaks(peak_x, peak_heights)
        self._figure_panel.set_threshold_line(float(threshold_height))
        if len(x_bins) > 0:
            self._figure_panel.set_x_range(float(np.min(x_bins)), float(np.max(x_bins)))

    def _replace_overlay(self, lines_gdf: gpd.GeoDataFrame) -> None:
        self._map_canvas.remove_layer(self._overlay_layer_name)
        if lines_gdf.empty:
            return
        self._map_canvas.add_vector_layer(
            lines_gdf,
            self._overlay_layer_name,
            color="#00D084",
            width=2,
        )

    def _clear_outputs(self, crs: Any) -> dict[str, Any]:
        self._figure_panel.clear()
        self._map_canvas.remove_layer(self._overlay_layer_name)
        empty_float = np.asarray([], dtype=np.float64)
        empty_int = np.asarray([], dtype=np.int64)
        lines_gdf = gpd.GeoDataFrame({"ridge_index": []}, geometry=[], crs=crs)
        return self._build_payload(
            empty_float, empty_int, empty_int, empty_float, empty_float, lines_gdf
        )

    def _build_payload(
        self,
        x_bins: np.ndarray,
        counts: np.ndarray,
        peak_indices: np.ndarray,
        peak_x: np.ndarray,
        peak_heights: np.ndarray,
        lines_gdf: gpd.GeoDataFrame,
    ) -> dict[str, Any]:
        return {
            "ridge_density_profile": {"x_bins": x_bins, "counts": counts},
            "ridge_peaks": {
                "peak_indices": peak_indices,
                "peak_x": peak_x,
                "peak_heights": peak_heights,
            },
            "ridge_lines_gdf": lines_gdf,
        }
