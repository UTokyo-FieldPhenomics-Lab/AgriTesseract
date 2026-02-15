"""Ordering controller for ridge assignment and map coloring."""

from __future__ import annotations

from typing import Any

import geopandas as gpd
import numpy as np

from src.utils.rename_ids.ridge_density import project_points_to_perp_axis
from src.utils.rename_ids.ridge_direction import normalize_direction_vector
from src.utils.rename_ids.ridge_ordering import (
    assign_points_to_ridges,
    build_ordering_result,
    build_ridge_intervals,
)


class RidgeOrderingController:
    """Drive ordering result generation and map-layer coloring updates."""

    def __init__(self, map_canvas: Any, layer_prefix: str = "ordering_ridge") -> None:
        self._map_canvas = map_canvas
        self._layer_prefix = layer_prefix
        self._ignored_layer_name = f"{layer_prefix}_ignored"

    def update(
        self,
        points_gdf: gpd.GeoDataFrame,
        effective_mask: np.ndarray,
        direction_vector: np.ndarray | None,
        ridge_peaks: np.ndarray,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        """Compute ordering result and refresh colored ordering layers."""
        if direction_vector is None:
            return self._clear_outputs(points_gdf)
        if len(points_gdf) == 0:
            return self._clear_outputs(points_gdf)
        peak_array = np.asarray(ridge_peaks, dtype=np.float64)
        if peak_array.ndim != 1 or peak_array.size == 0:
            return self._clear_outputs(points_gdf)
        return self._compute_and_render(
            points_gdf,
            effective_mask,
            direction_vector,
            peak_array,
            params,
        )

    def _compute_and_render(
        self,
        points_gdf: gpd.GeoDataFrame,
        effective_mask: np.ndarray,
        direction_vector: np.ndarray,
        ridge_peaks: np.ndarray,
        params: dict[str, Any],
    ) -> dict[str, Any]:
        points_xy = np.column_stack(
            (points_gdf.geometry.x.to_numpy(), points_gdf.geometry.y.to_numpy())
        )
        projected_x, projected_y = _project_points_axes(points_xy, direction_vector)
        ridge_intervals = build_ridge_intervals(ridge_peaks, float(params["buffer"]))
        ridge_id, is_inlier = assign_points_to_ridges(
            projected_x=projected_x,
            projected_y=projected_y,
            effective_mask=np.asarray(effective_mask, dtype=bool),
            ridge_intervals=ridge_intervals,
            ransac_enabled=bool(params["ransac_enabled"]),
            residual=float(params["residual"]),
            max_trials=int(params["max_trials"]),
        )
        result_gdf = build_ordering_result(points_gdf, ridge_id, is_inlier)
        stats = _build_ordering_stats(
            result_gdf, np.asarray(effective_mask, dtype=bool), ridge_intervals.shape[0]
        )
        self._render_layers(result_gdf)
        return {"ordering_result_gdf": result_gdf, "ordering_stats": stats}

    def _render_layers(self, result_gdf: gpd.GeoDataFrame) -> None:
        self._remove_existing_layers()
        if len(result_gdf) == 0:
            return
        self._map_canvas.set_layer_visibility("rename_points", False)
        ignored_mask = result_gdf["ridge_id"].to_numpy() < 0
        ignored_gdf = result_gdf.loc[ignored_mask]
        if len(ignored_gdf) > 0:
            self._map_canvas.add_point_layer(
                ignored_gdf,
                self._ignored_layer_name,
                size=7,
                fill_color=(156, 163, 175, 170),
                border_color="#4B5563",
                border_width=1.4,
                z_value=640,
                replace=True,
            )
        ridge_values = sorted(
            int(value)
            for value in np.unique(result_gdf["ridge_id"].to_numpy())
            if value >= 0
        )
        for ridge_id in ridge_values:
            ridge_gdf = result_gdf.loc[result_gdf["ridge_id"] == ridge_id]
            self._add_one_ridge_layer(ridge_id, ridge_gdf)

    def _add_one_ridge_layer(self, ridge_id: int, ridge_gdf: gpd.GeoDataFrame) -> None:
        """Render one ridge point subset using a stable color."""
        if len(ridge_gdf) == 0:
            return
        fill_rgba, border_hex = _stable_ridge_color(ridge_id)
        self._map_canvas.add_point_layer(
            ridge_gdf,
            f"{self._layer_prefix}_{ridge_id}",
            size=7,
            fill_color=fill_rgba,
            border_color=border_hex,
            border_width=1.2,
            z_value=645,
            replace=True,
        )

    def _remove_existing_layers(self) -> None:
        """Remove previously rendered ordering layers by prefix."""
        layer_names = list(self._map_canvas.get_layer_names())
        for layer_name in layer_names:
            if layer_name.startswith(f"{self._layer_prefix}_"):
                self._map_canvas.remove_layer(layer_name)

    def _clear_outputs(self, points_gdf: gpd.GeoDataFrame) -> dict[str, Any]:
        """Clear ordering layers and return empty ordering payload."""
        self._remove_existing_layers()
        self._map_canvas.set_layer_visibility("rename_points", True)
        empty_result = gpd.GeoDataFrame(
            {
                "fid": points_gdf.get("fid", np.asarray([], dtype=np.int64)),
                "ridge_id": np.full(len(points_gdf), -1, dtype=np.int64),
                "is_inlier": np.zeros(len(points_gdf), dtype=bool),
            },
            geometry=points_gdf.geometry,
            crs=points_gdf.crs,
        )
        stats = _build_ordering_stats(
            empty_result,
            np.zeros(len(points_gdf), dtype=bool),
            ridge_count=0,
        )
        return {"ordering_result_gdf": empty_result, "ordering_stats": stats}


def _project_points_axes(
    points_xy: np.ndarray,
    direction_vector: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """Project points onto perpendicular and direction axes."""
    points_array = np.asarray(points_xy, dtype=np.float64)
    if points_array.ndim != 2 or points_array.shape[1] != 2:
        raise ValueError("points_xy must have shape (N, 2)")
    if points_array.shape[0] == 0:
        empty = np.asarray([], dtype=np.float64)
        return empty, empty
    unit_direction = normalize_direction_vector(direction_vector)
    origin = np.mean(points_array, axis=0)
    projected_x = project_points_to_perp_axis(points_array, unit_direction)
    projected_y = np.dot(points_array - origin, unit_direction)
    return projected_x, projected_y


def _build_ordering_stats(
    result_gdf: gpd.GeoDataFrame,
    effective_mask: np.ndarray,
    ridge_count: int,
) -> dict[str, int]:
    """Build compact ordering summary stats for UI and downstream flow."""
    ridge_array = np.asarray(result_gdf["ridge_id"].to_numpy(), dtype=np.int64)
    effective_array = np.asarray(effective_mask, dtype=bool)
    assigned_count = int(np.count_nonzero(ridge_array >= 0))
    return {
        "total_points": int(len(result_gdf)),
        "effective_points": int(np.count_nonzero(effective_array)),
        "assigned_points": assigned_count,
        "ignored_points": int(len(result_gdf) - assigned_count),
        "ridge_count": int(ridge_count),
    }


def _stable_ridge_color(ridge_id: int) -> tuple[tuple[int, int, int, int], str]:
    """Return stable fill/border color pair for one ridge ID."""
    palette = [
        ((14, 165, 233, 180), "#0284C7"),
        ((34, 197, 94, 180), "#16A34A"),
        ((245, 158, 11, 180), "#D97706"),
        ((239, 68, 68, 180), "#DC2626"),
        ((168, 85, 247, 180), "#9333EA"),
        ((20, 184, 166, 180), "#0F766E"),
    ]
    return palette[ridge_id % len(palette)]
