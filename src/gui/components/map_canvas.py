"""
Map Canvas component for EasyPlantFieldID GUI.

This module provides a GeoTiff viewer based on PyQtGraph with support for:
- Large GeoTiff lazy loading with rasterio
- Pan, zoom, and rotation
- Multiple layer support
- Coordinate transformation

References
----------
- dev.notes/02_demo_load_big_geotiff.py: Large GeoTiff loading
- dev.notes/06_demo_layer_rotation.py: Rotation and pixel picking
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import darkdetect
import numpy as np
import pyqtgraph as pg
from loguru import logger
from PySide6.QtCore import QEvent, QPointF, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QAction, QKeyEvent, QTransform
from PySide6.QtWidgets import QMenu, QVBoxLayout, QWidget
from qfluentwidgets import Theme

# Move global config to instance level or handle dynamically
# pg.setConfigOptions(antialias=True)
from src.gui.config import cfg

try:
    import rasterio
    import rasterio.enums

    HAS_RASTERIO = True
except ImportError:
    HAS_RASTERIO = False
    logger.warning("rasterio not installed. GeoTiff loading will be disabled.")

try:
    import geopandas as gpd

    HAS_GEOPANDAS = True
except ImportError:
    gpd = None
    HAS_GEOPANDAS = False
    logger.warning("geopandas not installed. Vector loading will be disabled.")


@dataclass
class LayerBounds:
    """Simple bounds container for vector and raster layers.

    Attributes
    ----------
    left : float
        Minimum x coordinate.
    bottom : float
        Minimum y coordinate.
    right : float
        Maximum x coordinate.
    top : float
        Maximum y coordinate.
    """

    left: float
    bottom: float
    right: float
    top: float


class CustomViewBox(pg.ViewBox):
    """
    Custom ViewBox with enhanced mouse handling.

    Supports mode switching between Pan, Pick, and Draw modes.
    Emits signals for canvas interactions.

    Signals
    -------
    sigClicked : Signal(object)
        Emitted when the canvas is clicked in non-pan mode.
    sigCoordinateHover : Signal(float, float)
        Emitted when mouse moves over the canvas.
    """

    sigClicked = Signal(object)
    sigCoordinateHover = Signal(float, float)

    # Mode constants
    MODE_PAN = 0
    MODE_PICK = 1
    MODE_DRAW = 2

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.setMouseMode(pg.ViewBox.PanMode)
        self._current_mode = self.MODE_PAN

    def set_mode(self, mode: int) -> None:
        """
        Set the interaction mode.

        Parameters
        ----------
        mode : int
            One of MODE_PAN, MODE_PICK, MODE_DRAW.
        """
        self._current_mode = mode
        if mode == self.MODE_PAN:
            self.setMouseMode(pg.ViewBox.PanMode)
        else:
            self.setMouseMode(pg.ViewBox.RectMode)

    def mouseDragEvent(self, ev, *, axis=None) -> None:
        """Handle mouse drag events."""
        if self._current_mode == self.MODE_PAN:
            ev.accept()
            p_now = self.mapToView(ev.pos())
            p_last = self.mapToView(ev.lastPos())
            delta = p_now - p_last

            if delta.x() == 0 and delta.y() == 0:
                return

            current_rect = self.viewRect()
            new_center = current_rect.center() - delta
            current_rect.moveCenter(new_center)
            self.setRange(current_rect, padding=0)
        else:
            ev.ignore()
            super().mouseDragEvent(ev, axis=axis)

    def mouseClickEvent(self, ev) -> None:
        """Handle mouse click events."""
        if ev.button() == Qt.MouseButton.LeftButton:
            self.sigClicked.emit(ev)
            ev.accept()
        else:
            super().mouseClickEvent(ev)

    def mouseMoveEvent(self, ev) -> None:
        """Handle mouse move events for coordinate tracking."""
        pos = self.mapToView(ev.pos())
        self.sigCoordinateHover.emit(pos.x(), pos.y())
        super().mouseMoveEvent(ev)


class MapCanvas(QWidget):
    """
    GeoTiff viewer widget with PyQtGraph backend.

    Features:
    - Lazy loading of large GeoTiff files
    - Smooth pan and zoom
    - Layer management with visibility control
    - Rotation support
    - Coordinate display

    Signals
    -------
    sigCoordinateChanged : Signal(float, float)
        Emitted when cursor moves, providing geo coordinates.
    sigZoomChanged : Signal(float)
        Emitted when zoom level changes.
    sigRotationChanged : Signal(float)
        Emitted when rotation angle changes.
    sigLayerClicked : Signal(str, float, float)
        Emitted when a point is clicked on a layer.

    Examples
    --------
    >>> canvas = MapCanvas()
    >>> canvas.load_geotiff("path/to/image.tif")
    >>> canvas.sigCoordinateChanged.connect(lambda x, y: print(f"({x}, {y})"))
    """

    sigCoordinateChanged = Signal(float, float)
    sigZoomChanged = Signal(float)
    sigRotationChanged = Signal(float)
    sigLayerClicked = Signal(str, float, float)
    # Signals for layer panel sync
    sigLayerAdded = Signal(str, str)  # name, type
    sigLayerRemoved = Signal(str)
    sigLayerVisibilityChanged = Signal(str, bool)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the Map Canvas.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        # Layer registry: {name: {'item': GraphicsItem, 'dataset': rasterio dataset}}
        self._layers: Dict[str, Dict[str, Any]] = {}
        self._layer_order: List[str] = []

        # Current rotation angle
        self._rotation_angle: float = 0.0

        # External key-event handlers (callables returning bool)
        self._key_handlers: List = []
        # External hover handlers (callables receiving x, y)
        self._hover_handlers: List = []
        # External click handlers (callables receiving x, y, button → bool)
        self._click_handlers: List = []

        # Debounce timer for view updates
        self._update_timer = QTimer()
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(150)
        self._update_timer.timeout.connect(self._update_visible_tiles)

        # Initialize UI
        self._init_ui()

        # Theme handling
        self._update_theme()
        cfg.themeChanged.connect(self._update_theme)

        logger.debug("MapCanvas initialized")

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create custom ViewBox
        self._view_box = CustomViewBox()
        self._view_box.sigClicked.connect(self._on_canvas_clicked)
        self._view_box.sigCoordinateHover.connect(self._on_coordinate_hover)

        # Create PlotWidget with custom ViewBox
        self._plot_widget = pg.PlotWidget(viewBox=self._view_box)
        self.setFocusProxy(self._plot_widget)
        self._plot_widget.installEventFilter(self)
        self._plot_widget.viewport().installEventFilter(self)

        # Enable custom context menu
        self._plot_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._plot_widget.customContextMenuRequested.connect(self._show_context_menu)

        # Background set in _update_theme
        self._plot_widget.setAspectLocked(True)

        # Enable mouse tracking for coordinate display
        self._plot_widget.setMouseTracking(True)
        self._plot_widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._proxy = pg.SignalProxy(
            self._plot_widget.scene().sigMouseMoved,
            rateLimit=60,
            slot=self._on_mouse_moved,
        )

        # Hide axes for map-like view
        plot_item = self._plot_widget.getPlotItem()
        plot_item.hideAxis("left")
        plot_item.hideAxis("bottom")
        plot_item.hideButtons()

        # Connect view change signal
        self._plot_widget.sigRangeChanged.connect(self._on_view_changed)

        layout.addWidget(self._plot_widget)

        # Create item group for rotation
        self._item_group = pg.ItemGroup()
        self._view_box.addItem(self._item_group)

        # Create primary image item for raster display
        self._image_item = pg.ImageItem()
        self._item_group.addItem(self._image_item)

    def _show_context_menu(self, pos: QPointF):
        """Show custom context menu."""
        menu = QMenu(self)

        # Focus Action (Zoom to Boundary & Align)
        action_focus = QAction("Focus", self)
        action_focus.triggered.connect(self._focus_content)
        menu.addAction(action_focus)

        # Rotate Action (Set Rotation)
        action_rotate = QAction("Rotate...", self)
        action_rotate.triggered.connect(self._request_rotation)
        menu.addAction(action_rotate)

        menu.addSeparator()

        # Add "Zoom to Layer" options if layers exist
        if self._layers:
            zoom_menu = menu.addMenu("Zoom to Layer")
            for name in self._layer_order:
                action = QAction(name, self)
                action.triggered.connect(lambda checked, n=name: self.zoom_to_layer(n))
                zoom_menu.addAction(action)

        menu.exec_(self._plot_widget.mapToGlobal(pos.toPoint()))

    def _focus_content(self):
        """Zoom to fit all content and reset rotation."""
        self.set_rotation(0)
        # Calculate bounds of all layers
        if not self._layers:
            return

        # Prioritize Boundary
        if "Boundary" in self._layers:
            self.zoom_to_layer("Boundary")
        else:
            # Zoom to first visible
            for name, layer in self._layers.items():
                if layer["visible"]:
                    self.zoom_to_layer(name)
                    break

    def _request_rotation(self):
        """Request rotation via dialog (placeholder) or toggle auto-rotation."""
        # For now, just reset to 0 or 90
        # In real app, this should open a dialog or be handled by the controller
        # Emitting a signal for controller to handle is better, but here we keep it simple.
        # Let's iterate 90 degrees for basic interaction
        new_angle = (self._rotation_angle + 90) % 360
        self.set_rotation(new_angle)

    def zoom_to_layer(self, layer_name: str) -> None:
        """
        Zoom to the extent of a specific layer.

        Parameters
        ----------
        layer_name : str
            Name of the layer.
        """
        if layer_name not in self._layers:
            return

        layer_info = self._layers[layer_name]
        if "bounds" in layer_info:
            b = layer_info["bounds"]
            width = b.right - b.left
            height = b.top - b.bottom
            rect = QRectF(b.left, b.bottom, width, height)

            # Apply current rotation to view
            # Standard setRange works on unrotated coords typically in pyqtgraph

            self._view_box.setRange(rect, padding=0.05)
            logger.debug(f"Zoomed to layer: {layer_name}")

    def add_raster_layer(self, filepath: str, layer_name: Optional[str] = None) -> bool:
        """
        Load a GeoTiff file as a layer.

        Parameters
        ----------
        filepath : str
            Path to the GeoTiff file.
        layer_name : str, optional
            Name for the layer. If None, uses filename.

        Returns
        -------
        bool
            True if loading was successful, False otherwise.
        """
        if not HAS_RASTERIO:
            logger.error("rasterio is not installed")
            return False

        filepath = Path(filepath)
        if not filepath.exists():
            logger.error(f"File not found: {filepath}")
            return False

        if layer_name is None:
            layer_name = filepath.stem

        try:
            # Close existing dataset if layer exists
            if layer_name in self._layers:
                self.remove_layer(layer_name)

            # Open dataset (keeps file handle open for lazy loading)
            dataset = rasterio.open(filepath)
            logger.info(f"Loading GeoTiff: {filepath}")
            logger.debug(f"  Size: {dataset.width} x {dataset.height}")
            logger.debug(f"  Bounds: {dataset.bounds}")
            logger.debug(f"  CRS: {dataset.crs}")

            # Create ImageItem for this layer
            image_item = pg.ImageItem()
            image_item.setZValue(-100)  # Raster at bottom

            # Store layer info
            self._layers[layer_name] = {
                "item": image_item,
                "dataset": dataset,
                "filepath": str(filepath),
                "visible": True,
                "bounds": dataset.bounds,
            }
            self._layer_order.append(layer_name)

            # Add to item group
            self._item_group.addItem(image_item)

            # Set view to image extent
            bounds = dataset.bounds
            width = bounds.right - bounds.left
            height = bounds.top - bounds.bottom

            image_rect = QRectF(bounds.left, bounds.bottom, width, height)
            self._view_box.setRange(image_rect)

            # Trigger initial tile load
            self._update_visible_tiles()

            self.sigLayerAdded.emit(layer_name, "Raster")
            return True

        except Exception as e:
            logger.error(f"Failed to load GeoTiff: {e}")
            return False

    def _normalize_to_gdf(self, data: Any) -> Optional[Any]:
        """Normalize vector input to ``GeoDataFrame``.

        Parameters
        ----------
        data : Any
            Vector source as GeoDataFrame or shapefile path.

        Returns
        -------
        geopandas.GeoDataFrame | None
            Parsed GeoDataFrame when successful.
        """
        if not HAS_GEOPANDAS:
            logger.error("geopandas not installed")
            return None
        if isinstance(data, (str, Path)):
            return gpd.read_file(Path(data))
        if isinstance(data, gpd.GeoDataFrame):
            return data
        logger.error(f"Invalid vector data type: {type(data)}")
        return None

    def _gdf_to_plot_arrays(self, vector_gdf: Any) -> Tuple[np.ndarray, np.ndarray]:
        """Convert polygon geometries into flattened plotting arrays.

        Parameters
        ----------
        vector_gdf : geopandas.GeoDataFrame
            GeoDataFrame with polygon or multipolygon geometry.

        Returns
        -------
        tuple[np.ndarray, np.ndarray]
            Flattened x and y arrays separated by ``NaN`` breaks.
        """
        x_values: List[float] = []
        y_values: List[float] = []
        for geom in vector_gdf.geometry:
            polygons = [geom] if geom.geom_type == "Polygon" else list(geom.geoms)
            for polygon in polygons:
                coords_xy = np.asarray(polygon.exterior.coords)
                if coords_xy.ndim != 2 or coords_xy.shape[0] < 3:
                    continue
                x_values.extend(coords_xy[:, 0].tolist())
                y_values.extend(coords_xy[:, 1].tolist())
                x_values.append(np.nan)
                y_values.append(np.nan)
        return np.asarray(x_values, dtype=float), np.asarray(y_values, dtype=float)

    def _calc_bounds_from_gdf(self, vector_gdf: Any) -> Optional[LayerBounds]:
        """Calculate layer bounds from GeoDataFrame coordinates.

        Parameters
        ----------
        vector_gdf : geopandas.GeoDataFrame
            Polygon GeoDataFrame.

        Returns
        -------
        LayerBounds | None
            Computed bounds or None when geometry is empty.
        """
        if len(vector_gdf) == 0:
            return None
        left, bottom, right, top = vector_gdf.total_bounds
        return LayerBounds(
            left=float(left),
            bottom=float(bottom),
            right=float(right),
            top=float(top),
        )

    def add_vector_layer(
        self, data: Any, layer_name: str, color: str = "g", width: int = 2
    ) -> bool:
        """Add vector layer from GeoDataFrame or shapefile path.

        Parameters
        ----------
        data : Any
            ``GeoDataFrame`` object or path to shapefile.
        layer_name : str
            Layer name shown in layer panel.
        color : str, optional
            Vector line color.
        width : int, optional
            Vector line width in pixels.

        Returns
        -------
        bool
            True when layer is loaded successfully.
        """
        try:
            vector_gdf = self._normalize_to_gdf(data)
            if vector_gdf is None:
                return False

            x_data, y_data = self._gdf_to_plot_arrays(vector_gdf)
            if x_data.size == 0:
                logger.warning("No vector geometry to draw")
                return False

            bounds = self._calc_bounds_from_gdf(vector_gdf)
            if bounds is None:
                return False

            curve = pg.PlotCurveItem(
                x=x_data,
                y=y_data,
                pen=pg.mkPen(color=color, width=width),
                connect="finite",
            )
            curve.setZValue(100)

            if layer_name in self._layers:
                self.remove_layer(layer_name)

            self._layers[layer_name] = {
                "item": curve,
                "data": vector_gdf,
                "visible": True,
                "bounds": bounds,
            }
            self._layer_order.append(layer_name)
            self._item_group.addItem(curve)

            if len(self._layers) == 1:
                rect = QRectF(
                    bounds.left,
                    bounds.bottom,
                    bounds.right - bounds.left,
                    bounds.top - bounds.bottom,
                )
                self._view_box.setRange(rect)

            logger.info(f"Loaded vector layer: {layer_name}")
            self.sigLayerAdded.emit(layer_name, "Vector")
            return True
        except Exception as exc:
            logger.error(f"Failed to load vector layer: {exc}")
            return False

    def remove_layer(self, layer_name: str) -> bool:
        """
        Remove a layer from the canvas.

        Parameters
        ----------
        layer_name : str
            Name of the layer to remove.

        Returns
        -------
        bool
            True if layer was removed, False if not found.
        """
        if layer_name not in self._layers:
            return False

        layer_info = self._layers[layer_name]

        # Remove item from scene
        layer_info["item"].setParentItem(None)
        if layer_info["item"].scene():
            layer_info["item"].scene().removeItem(layer_info["item"])

        # Close dataset
        if "dataset" in layer_info and layer_info["dataset"] is not None:
            layer_info["dataset"].close()

        # Remove from registry
        del self._layers[layer_name]
        if layer_name in self._layer_order:
            self._layer_order.remove(layer_name)

        logger.debug(f"Layer removed: {layer_name}")
        self.sigLayerRemoved.emit(layer_name)
        return True

    def set_layer_visibility(self, layer_name: str, visible: bool) -> None:
        """
        Set visibility of a layer.

        Parameters
        ----------
        layer_name : str
            Name of the layer.
        visible : bool
            Whether the layer should be visible.
        """
        if layer_name in self._layers:
            self._layers[layer_name]["visible"] = visible
            self._layers[layer_name]["item"].setVisible(visible)
            # Emit signal so LayerPanel can sync (e.g. checkbox)
            self.sigLayerVisibilityChanged.emit(layer_name, visible)
            logger.debug(f"Layer '{layer_name}' visibility: {visible}")

    def update_layer_order(self, order: List[str]) -> None:
        """
        Update the Z-order of layers.

        Parameters
        ----------
        order : List[str]
            List of layer names from top to bottom.
        """
        self._layer_order = order
        for i, name in enumerate(reversed(order)):
            if name in self._layers:
                z_value = -100 + i
                self._layers[name]["item"].setZValue(z_value)
        logger.debug(f"Layer order updated: {order}")

    def set_rotation(self, angle: float) -> None:
        """
        Set the rotation angle of the map.

        Parameters
        ----------
        angle : float
            Rotation angle in degrees.
        """
        self._rotation_angle = angle

        # Calculate center of all visible layers
        center = self._get_content_center()
        if center:
            self._item_group.setTransformOriginPoint(center)

        self._item_group.setRotation(-angle)
        self.sigRotationChanged.emit(angle)
        logger.debug(f"Rotation set to: {angle}° around {center}")

        # Trigger update of visible tiles
        self._update_timer.start()

    def get_rotation(self) -> float:
        """Get the current rotation angle."""
        return self._rotation_angle

    def _get_content_center(self) -> Optional[QPointF]:
        """Calculate the center of all layers."""
        if not self._layers:
            return None

        # If boundary layer exists, use its center
        if "Boundary" in self._layers:
            bounds = self._layers["Boundary"].get("bounds")
            if bounds:
                center_x = (bounds.left + bounds.right) / 2
                center_y = (bounds.bottom + bounds.top) / 2
                return QPointF(center_x, center_y)

        # Otherwise use the first visible layer
        for layer in self._layers.values():
            if layer["visible"] and "bounds" in layer:
                bounds = layer["bounds"]
                center_x = (bounds.left + bounds.right) / 2
                center_y = (bounds.bottom + bounds.top) / 2
                return QPointF(center_x, center_y)

        return None

    def set_mode(self, mode: int) -> None:
        """
        Set the interaction mode.

        Parameters
        ----------
        mode : int
            0=Pan, 1=Pick, 2=Draw
        """
        self._view_box.set_mode(mode)

        # Update cursor
        if mode == 0:
            self._plot_widget.setCursor(Qt.CursorShape.OpenHandCursor)
        elif mode == 1:
            self._plot_widget.setCursor(Qt.CursorShape.CrossCursor)
        elif mode == 2:
            self._plot_widget.setCursor(Qt.CursorShape.CrossCursor)

    def _on_view_changed(self) -> None:
        """Handle view range change (pan/zoom)."""
        self._update_timer.start()

        # Emit zoom changed signal
        view_rect = self._view_box.viewRect()
        # Calculate approximate zoom level
        if self._layers:
            first_layer = next(iter(self._layers.values()))
            if "bounds" in first_layer:
                b = first_layer["bounds"]
                full_width = b.right - b.left
                visible_width = view_rect.width()
                if visible_width > 0:
                    zoom_percent = (full_width / visible_width) * 100
                    self.sigZoomChanged.emit(zoom_percent)

    def _update_visible_tiles(self) -> None:
        """Update the visible tiles based on current view."""
        if not self._layers:
            return

        view_rect = self._view_box.viewRect()

        for name, layer_info in self._layers.items():
            if not layer_info["visible"]:
                continue

            dataset = layer_info.get("dataset")
            if dataset is None:
                continue

            self._load_visible_region(layer_info, view_rect)

    def _load_visible_region(self, layer_info: Dict, view_rect: QRectF) -> None:
        """
        Load the visible region of a raster layer.

        Parameters
        ----------
        layer_info : Dict
            Layer information dictionary.
        view_rect : QRectF
            Current visible rectangle in geo coordinates.
        """
        dataset = layer_info["dataset"]
        image_item = layer_info["item"]

        # Calculate visible rect in ItemGroup coordinates (Geo coords, rotated)
        view_rect = self._view_box.viewRect()

        # Use simple mapping if no rotation or manual transform if rotated
        if self._rotation_angle == 0:
            bbox = view_rect
        else:
            center = self._item_group.transformOriginPoint()
            transform = QTransform()
            transform.translate(center.x(), center.y())
            transform.rotate(self._rotation_angle)  # Inverse of -angle
            transform.translate(-center.x(), -center.y())
            bbox = transform.mapRect(view_rect)

        geo_left = bbox.left()
        geo_right = bbox.right()
        geo_bottom = bbox.top()
        geo_top = bbox.bottom()

        try:
            # Convert geo coordinates to rasterio window
            # Ensure proper ordering for rasterio (bottom < top) (Y-up logic)

            w_left, w_bottom, w_right, w_top = (
                bbox.left(),
                bbox.top(),
                bbox.right(),
                bbox.bottom(),
            )

            # Use min/max to be safe regardless of axis direction assumptions
            r_left = min(w_left, w_right)
            r_right = max(w_left, w_right)
            r_bottom = min(w_bottom, w_top)
            r_top = max(w_bottom, w_top)

            # Pad the window slightly to avoid edge artifacts during rotation
            # padding = max(r_right - r_left, r_top - r_bottom) * 0.05
            # r_left -= padding
            # r_right += padding
            # r_bottom -= padding
            # r_top += padding

            window = dataset.window(r_left, r_bottom, r_right, r_top)
            # logger.debug(f"View Rect: {view_rect}, Bbox: {bbox}, Window: {window}")
        except rasterio.errors.WindowError:
            # View is outside image bounds
            # logger.debug("View outside image bounds")
            image_item.clear()
            return

        # Determine target resolution (match screen pixels)
        view_px_width = int(self._view_box.width())
        view_px_height = int(self._view_box.height())

        if view_px_width <= 0 or view_px_height <= 0:
            return

        target_shape = (max(1, view_px_height), max(1, view_px_width))

        try:
            # Read data with downsampling
            data = dataset.read(
                window=window,
                out_shape=target_shape,
                resampling=rasterio.enums.Resampling.nearest,
                boundless=True,
            )

            logger.debug(
                f"Read data shape: {data.shape}, Range: {data.min()} - {data.max()}"
            )

            # Transpose from (B, H, W) to (W, H, B) for pyqtgraph (x, y, c)
            if data.ndim == 3:
                data = data.transpose((2, 1, 0))
                # Flip Y axis (axis 1) because rasterio is Top-Down, pg is Bottom-Up
                data = np.flip(data, axis=1)

                # Handle alpha channel if present
                if data.shape[2] == 4:
                    # RGBA - keep as is
                    pass
                elif data.shape[2] >= 3:
                    # RGB or more - take first 3 channels
                    data = data[:, :, :3]

            # Simple normalization if data is typically 16-bit or not 0-255
            # This is a basic check. For now just log.
            if data.dtype != np.uint8:
                # logger.debug(f"Data type is {data.dtype}, normalizing for display")
                # Normalize to 0-255 for display if not uint8
                # This might be slow for real-time, but good for testing visibility
                if data.max() > 0:
                    data = (data / data.max() * 255).astype(np.uint8)
                else:
                    data = data.astype(np.uint8)

            # Update image item
            image_item.clear()
            image_item.setImage(data)

            # Set correct geo position
            img_rect = QRectF(
                geo_left, geo_bottom, geo_right - geo_left, geo_top - geo_bottom
            )
            image_item.setRect(img_rect)
            # logger.debug(f"Image updated. Rect: {img_rect}")

        except Exception as e:
            logger.error(f"Error loading visible region: {e}")

    # -- overlay API -------------------------------------------------------

    def add_overlay_item(self, item: Any) -> None:
        """Add a graphics overlay item to the canvas item group.

        Parameters
        ----------
        item : Any
            A PyQtGraph or Qt graphics item to attach.
        """
        self._item_group.addItem(item)

    def remove_overlay_item(self, item: Any) -> None:
        """Remove a graphics overlay item from the canvas item group.

        Parameters
        ----------
        item : Any
            Previously added overlay item to detach.
        """
        item.setParentItem(None)
        scene = item.scene()
        if scene is not None:
            scene.removeItem(item)

    # -- event handlers ----------------------------------------------------

    def _on_mouse_moved(self, evt: tuple) -> None:
        """Handle mouse move events for coordinate tracking."""
        pos = evt[0]
        if self._plot_widget.sceneBoundingRect().contains(pos):
            mouse_point = self._view_box.mapSceneToView(pos)
            self._on_coordinate_hover(mouse_point.x(), mouse_point.y())

    def _on_coordinate_hover(self, x_coord: float, y_coord: float) -> None:
        """Emit coordinate change signal on mouse hover."""
        self.sigCoordinateChanged.emit(x_coord, y_coord)
        for handler in self._hover_handlers:
            handler(x_coord, y_coord)

    def _on_canvas_clicked(self, ev: Any) -> None:
        """Handle canvas click events."""
        pos = self._view_box.mapToView(ev.pos())
        item_pos = self._item_group.mapFromParent(pos)
        for handler in self._click_handlers:
            if handler(item_pos.x(), item_pos.y(), ev.button()):
                return
        self.sigLayerClicked.emit("", item_pos.x(), item_pos.y())
        logger.debug(f"Canvas clicked at: ({item_pos.x():.2f}, {item_pos.y():.2f})")

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Delegate key events to registered handlers, then super.

        Parameters
        ----------
        event : QKeyEvent
            The key event to handle.
        """
        for handler in self._key_handlers:
            if handler(event):
                return
        super().keyPressEvent(event)

    def eventFilter(self, watched: Any, event: QEvent) -> bool:
        """Filter events for child widgets (PlotWidget)."""
        if (
            watched == self._plot_widget or watched == self._plot_widget.viewport()
        ) and event.type() == QEvent.Type.KeyPress:
            logger.debug(f"MapCanvas eventFilter caught KeyPress: {event.key()}")
            # Delegate to registered handlers first
            for handler in self._key_handlers:
                # cast event to QKeyEvent if needed, or rely on duck typing
                if handler(event):
                    logger.debug(
                        f"Key event {event.key()} consumed by handler: {handler}"
                    )
                    return True
        return super().eventFilter(watched, event)

    # -- utility methods ---------------------------------------------------

    def cleanup(self) -> None:
        """Clean up resources (close file handles)."""
        for name in list(self._layers.keys()):
            self.remove_layer(name)
        logger.debug("MapCanvas cleanup complete")

    def get_layer_names(self) -> List[str]:
        """Get list of layer names in display order.

        Returns
        -------
        list[str]
            Layer names ordered by ``_layer_order``.
        """
        return list(self._layer_order)

    def set_zoom(self, zoom_percent: float) -> None:
        """Set zoom level (percentage relative to full extent).

        Parameters
        ----------
        zoom_percent : float
            Zoom level in percent (e.g., 100).
        """
        if not self._layers or zoom_percent <= 0:
            return
        first_layer = next(iter(self._layers.values()))
        if "bounds" not in first_layer:
            return

    def _update_theme(self) -> None:
        """Update canvas theme (background color)."""
        theme = cfg.themeMode.value
        is_dark = False
        if theme == Theme.AUTO:
            is_dark = darkdetect.isDark()
        else:
            is_dark = theme == Theme.DARK

        if is_dark:
            bg_color = "#272727"
        else:
            bg_color = "#FFFFFF"

        self._plot_widget.setBackground(bg_color)
        logger.debug(f"MapCanvas theme updated. Dark: {is_dark}")
