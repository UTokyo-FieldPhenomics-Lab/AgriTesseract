"""End-to-end regression test for ordering pipeline contract."""

from __future__ import annotations

import geopandas as gpd
import numpy as np
from shapely.geometry import Point

from src.utils.rename_ids.ridge_detection_controller import RidgeDetectionController
from src.utils.rename_ids.ridge_ordering_controller import RidgeOrderingController


class _FakeFigurePanel:
    """Figure panel double that accepts ridge controller updates."""

    def clear(self) -> None:
        return

    def set_density_curve(self, _x_bins: np.ndarray, _counts: np.ndarray) -> None:
        return

    def set_peaks(self, _peak_x: np.ndarray, _peak_h: np.ndarray) -> None:
        return

    def set_x_range(self, _x_min: float, _x_max: float) -> None:
        return

    def set_threshold_line(self, _value: float | None) -> None:
        return

    def set_y_range(self, _y_min: float, _y_max: float) -> None:
        return


class _FakeMapCanvas:
    """Map canvas double used by both ridge and ordering controllers."""

    def __init__(self) -> None:
        self.layer_names: list[str] = ["rename_points"]

    def remove_layer(self, layer_name: str) -> bool:
        if layer_name in self.layer_names:
            self.layer_names.remove(layer_name)
        return True

    def add_vector_layer(self, _data, layer_name: str, **_kwargs) -> bool:
        if layer_name not in self.layer_names:
            self.layer_names.append(layer_name)
        return True

    def add_point_layer(self, _data, layer_name: str, **_kwargs) -> bool:
        if layer_name not in self.layer_names:
            self.layer_names.append(layer_name)
        return True

    def get_layer_names(self) -> list[str]:
        return list(self.layer_names)

    def set_layer_visibility(self, _layer_name: str, _visible: bool) -> None:
        return


def _build_points_case() -> tuple[gpd.GeoDataFrame, np.ndarray]:
    """Build sample containing boundary-outside and outlier-like points."""
    points_gdf = gpd.GeoDataFrame(
        {"fid": [1, 2, 3, 4, 5, 6]},
        geometry=[
            Point(0.0, -2.1),
            Point(1.0, -1.9),
            Point(0.0, 2.0),
            Point(1.0, 2.1),
            Point(2.0, 6.0),
            Point(20.0, 3.4),
        ],
        crs="EPSG:3857",
    )
    effective_mask = np.asarray([True, True, True, True, False, True], dtype=np.bool_)
    return points_gdf, effective_mask


def test_ordering_end_to_end_contract_and_stats_consistency() -> None:
    """Direction + peaks + ordering flow should satisfy output contract."""
    map_canvas = _FakeMapCanvas()
    figure_panel = _FakeFigurePanel()
    ridge_controller = RidgeDetectionController(
        map_canvas=map_canvas, figure_panel=figure_panel
    )
    ordering_controller = RidgeOrderingController(map_canvas=map_canvas)
    points_gdf, effective_mask = _build_points_case()

    points_xy = np.column_stack(
        (points_gdf.geometry.x.to_numpy(), points_gdf.geometry.y.to_numpy())
    )
    ridge_payload = ridge_controller.update(
        effective_points_xy=points_xy[effective_mask],
        direction_vector=np.asarray([1.0, 0.0], dtype=np.float64),
        strength_ratio=0.5,
        distance=2.0,
        height=1.0,
        crs=points_gdf.crs,
    )
    ordering_payload = ordering_controller.update(
        points_gdf=points_gdf,
        effective_mask=effective_mask,
        direction_vector=np.asarray([1.0, 0.0], dtype=np.float64),
        ridge_peaks=np.asarray(
            ridge_payload["ridge_peaks"]["peak_x"], dtype=np.float64
        ),
        params={
            "buffer": 0.8,
            "ransac_enabled": True,
            "residual": 0.3,
            "max_trials": 200,
        },
    )

    result_gdf = ordering_payload["ordering_result_gdf"]
    stats = ordering_payload["ordering_stats"]

    assert {"fid", "ridge_id", "is_inlier", "geometry"} <= set(result_gdf.columns)
    assert len(result_gdf) == len(points_gdf)
    assert stats["total_points"] == len(points_gdf)
    assert stats["effective_points"] == int(np.count_nonzero(effective_mask))
    assert stats["assigned_points"] + stats["ignored_points"] == stats["total_points"]
    ignored_rows = result_gdf.loc[result_gdf["ridge_id"] == -1]
    if len(ignored_rows) > 0:
        assert ignored_rows["is_inlier"].to_numpy().sum() == 0
