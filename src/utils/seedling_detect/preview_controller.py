"""Seedling preview interaction controller over MapCanvas.

Encapsulates all preview-box overlay, mouse tracking, key shortcuts,
and SAM3 result visualization logic, using only generic MapCanvas APIs.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from loguru import logger
from PySide6.QtCore import QObject, QPointF, Qt, Signal
from PySide6.QtGui import (
    QBrush,
    QColor,
    QKeyEvent,
    QPainterPath,
    QPen,
)
from PySide6.QtWidgets import QGraphicsPathItem

from src.utils.seedling_detect.preview import (
    clamp_preview_size,
    pixel_square_bounds_from_geo_center,
    preview_bounds_from_center,
)

if TYPE_CHECKING:
    from src.gui.components.map_canvas import MapCanvas


# -- Layer name constants ---------------------------------------------------
PREVIEW_LAYER_NAME = "Preview Regions"
PREVIEW_RESULT_LAYER_NAME = "Preview Result"


class SeedlingPreviewController(QObject):
    """Seedling preview interaction adapter over MapCanvas.

    Uses only MapCanvas generic public APIs:
    - ``add_overlay_item()`` / ``remove_overlay_item()``
    - ``remove_layer()``
    - ``_layers`` / ``_layer_order`` (for layer registration)
    - ``sigLayerAdded``

    Parameters
    ----------
    map_canvas : MapCanvas
        The host map canvas instance.

    Signals
    -------
    sigPreviewBoxLocked : Signal(float, float, float, float)
        Emitted when preview area is locked by click.
    sigPreviewSizeChanged : Signal(int)
        Emitted when preview box size changes via shortcuts.
    """

    sigPreviewBoxLocked = Signal(float, float, float, float)
    sigPreviewSizeChanged = Signal(int)
    sigRequestPreviewModeStop = Signal()

    def __init__(self, map_canvas: MapCanvas) -> None:
        super().__init__(map_canvas)
        self._canvas = map_canvas

        # -- preview state --------------------------------------------------
        self._preview_mode_enabled: bool = False
        self._preview_box_size: int = 640  # pixels
        self._preview_hover_center: Optional[Tuple[float, float]] = None
        self._preview_locked_center: Optional[Tuple[float, float]] = None

        # -- preview box overlay (dashed rect) ------------------------------
        self._preview_box_item = pg.PlotCurveItem(
            pen=pg.mkPen(
                color="#00AAFF", width=2, style=Qt.PenStyle.DashLine
            ),
            connect="finite",
        )
        self._preview_box_item.setVisible(False)
        self._preview_box_item.setZValue(500)
        self._canvas.add_overlay_item(self._preview_box_item)

    # -- public API ---------------------------------------------------------

    def set_preview_mode_enabled(self, enabled: bool) -> None:
        """Enable or disable preview-box interaction mode.

        Parameters
        ----------
        enabled : bool
            When True, hover / click / +/- shortcuts are active.
        """
        self._preview_mode_enabled = enabled
        self._ensure_preview_layer_registered()
        if enabled:
            self._update_preview_overlay()
            return
        self._clear_preview_layers()

    def set_preview_box_size(self, size: int) -> None:
        """Set preview box size and refresh overlay.

        Parameters
        ----------
        size : int
            Preview box side length in pixels.
        """
        clamped_size = clamp_preview_size(size)
        if clamped_size == self._preview_box_size:
            return
        self._preview_box_size = clamped_size
        self.sigPreviewSizeChanged.emit(clamped_size)
        self._update_preview_overlay()

    def adjust_preview_box_size(self, delta: int) -> None:
        """Adjust preview box size by delta pixels.

        Parameters
        ----------
        delta : int
            Pixel increment (positive) or decrement (negative).
        """
        self.set_preview_box_size(self._preview_box_size + delta)

    def preview_box_size(self) -> int:
        """Return current preview box size in pixels."""
        return self._preview_box_size

    def clear_preview_box_lock(self) -> None:
        """Clear locked preview center and redraw hover box."""
        self._preview_locked_center = None
        self._update_preview_overlay()

    def get_locked_preview_bounds(
        self,
    ) -> Optional[Tuple[float, float, float, float]]:
        """Return locked preview bounds when preview area exists.

        Returns
        -------
        tuple | None
            ``(x_min, y_min, x_max, y_max)`` or None if not locked.
        """
        if self._preview_locked_center is None:
            return None
        return self._preview_bounds()

    def read_preview_patch(
        self,
        bounds_geo: Tuple[float, float, float, float],
    ) -> Optional[Dict[str, Any]]:
        """Read preview patch image and transform from active raster.

        Parameters
        ----------
        bounds_geo : tuple
            ``(x_min, y_min, x_max, y_max)`` in geo coordinates.

        Returns
        -------
        dict | None
            Dict with ``image`` (ndarray) and ``transform`` (Affine),
            or None on failure.
        """
        dataset = self._active_raster_dataset()
        if dataset is None:
            return None
        return self._read_patch_from_dataset(dataset, bounds_geo)

    def show_preview_result_polygons(
        self,
        polygons_geo: List[np.ndarray],
    ) -> None:
        """Render preview inference polygons with per-instance colors.

        Parameters
        ----------
        polygons_geo : list[numpy.ndarray]
            List of polygon arrays, each with shape ``(N, 2)``.
        """
        self.clear_preview_result_layer()
        if not polygons_geo:
            return
        group_item = pg.ItemGroup()
        group_item.setZValue(650)
        self._canvas.add_overlay_item(group_item)
        for idx, polygon in enumerate(polygons_geo):
            poly_xy = np.asarray(polygon, dtype=float)
            if poly_xy.ndim != 2 or poly_xy.shape[0] < 3:
                continue
            self._add_polygon_to_group(group_item, poly_xy, idx)
        self._register_result_layer(group_item, polygons_geo)

    def clear_preview_result_layer(self) -> None:
        """Remove preview inference result layer if present."""
        self._canvas.remove_layer(PREVIEW_RESULT_LAYER_NAME)

    # -- event handlers (called by MapCanvas) -------------------------------

    def handle_key_press(self, event: QKeyEvent) -> bool:
        """Handle preview size shortcuts.

        Parameters
        ----------
        event : QKeyEvent
            Key press event from MapCanvas.

        Returns
        -------
        bool
            True if the event was consumed by preview logic.
        """
        logger.debug(f"PreviewController received key: {event.key()} (enabled={self._preview_mode_enabled})")
        if not self._preview_mode_enabled:
            return False
        if event.key() == Qt.Key.Key_Escape:
            logger.debug("Escape key detected, stopping preview mode")
            self.sigRequestPreviewModeStop.emit()
            event.accept()
            return True
        if event.key() in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            logger.debug("Plus/Equal key detected, increasing size")
            self.adjust_preview_box_size(delta=32)
            event.accept()
            return True
        if event.key() == Qt.Key.Key_Minus:
            logger.debug("Minus key detected, decreasing size")
            self.adjust_preview_box_size(delta=-32)
            event.accept()
            return True
        return False

    def handle_coordinate_hover(
        self, x_coord: float, y_coord: float
    ) -> None:
        """Update preview overlay on mouse hover.

        Parameters
        ----------
        x_coord, y_coord : float
            Hover coordinate in view space.
        """
        if not self._preview_mode_enabled:
            return
        item_pos = self._canvas._item_group.mapFromParent(
            QPointF(x_coord, y_coord)
        )
        self._preview_hover_center = (item_pos.x(), item_pos.y())
        self._update_preview_overlay()

    def handle_click(
        self, x_pos: float, y_pos: float, button: Qt.MouseButton
    ) -> bool:
        """Handle canvas click for preview locking.

        Parameters
        ----------
        x_pos, y_pos : float
            Click coordinate in item-group space.
        button : Qt.MouseButton
            Which mouse button was clicked.

        Returns
        -------
        bool
            True if click was consumed by preview logic.
        """
        if not self._preview_mode_enabled:
            return False
        if button != Qt.MouseButton.LeftButton:
            return False
        self._preview_locked_center = (x_pos, y_pos)
        self._update_preview_overlay()
        self.sigPreviewBoxLocked.emit(*self._preview_bounds())
        return True

    # -- internal helpers ---------------------------------------------------

    def _preview_bounds(self) -> tuple[float, float, float, float]:
        """Get current preview bounds from active center."""
        center_xy = (
            self._preview_locked_center or self._preview_hover_center
        )
        if center_xy is None:
            return 0.0, 0.0, 0.0, 0.0
        active_dataset = self._active_raster_dataset()
        if active_dataset is None:
            return preview_bounds_from_center(
                center_xy[0], center_xy[1], int(self._preview_box_size)
            )
        return pixel_square_bounds_from_geo_center(
            center_x=center_xy[0],
            center_y=center_xy[1],
            size_px=self._preview_box_size,
            transform=active_dataset.transform,
        )

    def _active_raster_dataset(self) -> Any:
        """Get top-most visible raster dataset for preview conversion."""
        for layer_name in reversed(self._canvas._layer_order):
            layer_info = self._canvas._layers.get(layer_name, {})
            if not layer_info.get("visible", False):
                continue
            dataset = layer_info.get("dataset")
            if dataset is not None:
                return dataset
        return None

    def _ensure_preview_layer_registered(self) -> None:
        """Register preview overlay into layer tree as vector layer."""
        if self._preview_box_item.parentItem() is None:
            self._canvas.add_overlay_item(self._preview_box_item)
        if PREVIEW_LAYER_NAME in self._canvas._layers:
            return
        self._canvas._layers[PREVIEW_LAYER_NAME] = {
            "item": self._preview_box_item,
            "visible": True,
            "bounds": None,
            "is_preview": True,
        }
        self._canvas._layer_order.append(PREVIEW_LAYER_NAME)
        self._canvas.sigLayerAdded.emit(PREVIEW_LAYER_NAME, "Vector")

    def _clear_preview_layers(self) -> None:
        """Clear preview box and preview-result layers from canvas."""
        self._preview_hover_center = None
        self._preview_locked_center = None
        self._preview_box_item.setVisible(False)
        self._canvas.remove_layer(PREVIEW_LAYER_NAME)
        self.clear_preview_result_layer()

    def _update_preview_overlay(self) -> None:
        """Update preview box polyline rendering."""
        if not self._preview_mode_enabled:
            self._preview_box_item.setVisible(False)
            return
        center_xy = (
            self._preview_locked_center or self._preview_hover_center
        )
        if center_xy is None:
            self._preview_box_item.setVisible(False)
            return
        x_min, y_min, x_max, y_max = self._preview_bounds()
        x_values = np.asarray(
            [x_min, x_max, x_max, x_min, x_min], dtype=float
        )
        y_values = np.asarray(
            [y_min, y_min, y_max, y_max, y_min], dtype=float
        )
        self._preview_box_item.setData(x=x_values, y=y_values)
        self._update_preview_layer_bounds(x_min, y_min, x_max, y_max)
        self._preview_box_item.setVisible(True)

    def _update_preview_layer_bounds(
        self,
        x_min: float, y_min: float, x_max: float, y_max: float,
    ) -> None:
        """Sync preview layer bounds in canvas layer registry."""
        from src.gui.components.map_canvas import LayerBounds

        preview_layer = self._canvas._layers.get(PREVIEW_LAYER_NAME)
        if preview_layer is None:
            return
        preview_layer["bounds"] = LayerBounds(
            left=x_min, bottom=y_min, right=x_max, top=y_max,
        )

    def _add_polygon_to_group(
        self,
        group_item: pg.ItemGroup,
        poly_xy: np.ndarray,
        idx: int,
    ) -> None:
        """Add a single polygon path item to the group.

        Parameters
        ----------
        group_item : pg.ItemGroup
            Parent group for result polygons.
        poly_xy : numpy.ndarray
            Polygon vertices with shape ``(N, 2)``.
        idx : int
            Instance index for color assignment.
        """
        path = QPainterPath()
        path.moveTo(float(poly_xy[0, 0]), float(poly_xy[0, 1]))
        for point_xy in poly_xy[1:]:
            path.lineTo(float(point_xy[0]), float(point_xy[1]))
        path.closeSubpath()
        graphics_item = QGraphicsPathItem(path)
        color = QColor.fromHsv((idx * 47) % 360, 220, 255, 130)
        pen = QPen(color, 2)
        pen.setCosmetic(True)
        graphics_item.setPen(pen)
        graphics_item.setBrush(QBrush(color))
        graphics_item.setParentItem(group_item)

    def _register_result_layer(
        self,
        group_item: pg.ItemGroup,
        polygons_geo: List[np.ndarray],
    ) -> None:
        """Register result polygon group as a canvas layer."""
        from src.gui.components.map_canvas import LayerBounds

        bounds = self._polygon_bounds(polygons_geo)
        self._canvas._layers[PREVIEW_RESULT_LAYER_NAME] = {
            "item": group_item,
            "visible": True,
            "bounds": bounds,
        }
        self._canvas._layer_order.append(PREVIEW_RESULT_LAYER_NAME)
        self._canvas.sigLayerAdded.emit(
            PREVIEW_RESULT_LAYER_NAME, "Vector"
        )

    @staticmethod
    def _polygon_bounds(
        polygons_geo: List[np.ndarray],
    ) -> Optional[Any]:
        """Compute layer bounds from polygon list."""
        from src.gui.components.map_canvas import LayerBounds

        if not polygons_geo:
            return None
        coords = [
            np.asarray(poly, dtype=float)
            for poly in polygons_geo
            if len(poly) >= 3
        ]
        if not coords:
            return None
        stacked = np.vstack(coords)
        return LayerBounds(
            left=float(np.min(stacked[:, 0])),
            bottom=float(np.min(stacked[:, 1])),
            right=float(np.max(stacked[:, 0])),
            top=float(np.max(stacked[:, 1])),
        )

    @staticmethod
    def _read_patch_from_dataset(
        dataset: Any,
        bounds_geo: Tuple[float, float, float, float],
    ) -> Optional[Dict[str, Any]]:
        """Read image patch from rasterio dataset.

        Parameters
        ----------
        dataset : rasterio.DatasetReader
            Open rasterio dataset.
        bounds_geo : tuple
            ``(x_min, y_min, x_max, y_max)`` in geo coordinates.

        Returns
        -------
        dict | None
            ``{"image": ndarray, "transform": Affine}`` or None.
        """
        x_min, y_min, x_max, y_max = bounds_geo
        try:
            window = dataset.window(x_min, y_min, x_max, y_max)
            window = window.round_offsets().round_lengths()
            if window.width <= 0 or window.height <= 0:
                return None
            patch = dataset.read(window=window, boundless=True)
            if patch.ndim != 3:
                return None
            patch = patch.transpose((1, 2, 0))  # (B,H,W) -> (H,W,B)
            if patch.shape[2] > 3:
                patch = patch[:, :, :3]
            if patch.dtype != np.uint8:
                max_value = float(np.max(patch))
                patch = (
                    np.zeros_like(patch, dtype=np.uint8)
                    if max_value <= 0
                    else (patch / max_value * 255).astype(np.uint8)
                )
            patch_transform = dataset.window_transform(window)
            return {"image": patch, "transform": patch_transform}
        except Exception as exc:
            logger.error(f"Failed to read preview patch: {exc}")
            return None
