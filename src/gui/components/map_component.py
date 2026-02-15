from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal

from src.gui.components.bottom_panel import BottomPanelHost
from src.gui.components.layer_panel import LayerPanel
from src.gui.components.map_canvas import MapCanvas
from src.gui.components.status_bar import StatusBar


class MapComponent(QWidget):
    """
    Composite component containing:
    - Layer Panel (Left)
    - Map Canvas (Center)
    - Status Bar (Bottom)
    """

    # Re-expose map signals
    sigCoordinateChanged = Signal(float, float)
    sigZoomChanged = Signal(float)
    sigRotationChanged = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._is_adjusting_bottom_panel = False
        self._bottom_auto_hide_height_px = 24
        self._bottom_collapsed_height_px = 8

        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter for Layer | Map
        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.h_splitter.setHandleWidth(1)
        # Initial sizes (Layer:Map = 1:4)
        self.h_splitter.setSizes([200, 800])

        # 1. Layer Panel
        self.layer_panel = LayerPanel()
        self.h_splitter.addWidget(self.layer_panel)

        # 2. Vertical Splitter for Map | Bottom Panel | Status Bar
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(1)

        self.h_splitter.addWidget(self.v_splitter)

        # 2. Map Canvas
        self.map_canvas = MapCanvas()
        self.v_splitter.addWidget(self.map_canvas)

        # 3. Bottom Panel Host
        self.bottom_panel_host = BottomPanelHost()
        self.v_splitter.addWidget(self.bottom_panel_host)

        # 4. Status Bar
        self.status_bar = StatusBar()
        self.v_splitter.addWidget(self.status_bar)

        self.v_splitter.setStretchFactor(0, 4)
        self.v_splitter.setStretchFactor(1, 1)
        self.v_splitter.setStretchFactor(2, 0)
        self.v_splitter.setCollapsible(1, True)
        self.v_splitter.setCollapsible(2, False)
        self._apply_vertical_sizes(map_height=800, panel_height=200)
        self.hide_panel()

        layout.addWidget(self.h_splitter, 1)  # Take available vertical space

    def _connect_signals(self) -> None:
        # Layer Panel -> Map Canvas
        self.layer_panel.sigLayerVisibilityChanged.connect(
            self.map_canvas.set_layer_visibility
        )
        self.layer_panel.sigLayerOrderChanged.connect(
            self.map_canvas.update_layer_order
        )

        # Map Canvas -> Status Bar
        self.map_canvas.sigCoordinateChanged.connect(self.status_bar.update_coordinates)
        self.map_canvas.sigZoomChanged.connect(self.status_bar.update_zoom)
        self.map_canvas.sigRotationChanged.connect(self.status_bar.update_rotation)

        # Status Bar -> Map Canvas (Control)
        self.status_bar.sigZoomChanged.connect(self.map_canvas.set_zoom)
        self.status_bar.sigRotationChanged.connect(self.map_canvas.set_rotation)

        # Map Canvas -> Self (re-emit)
        self.map_canvas.sigCoordinateChanged.connect(self.sigCoordinateChanged.emit)
        self.map_canvas.sigZoomChanged.connect(self.sigZoomChanged.emit)
        self.map_canvas.sigRotationChanged.connect(self.sigRotationChanged.emit)

        # Map Canvas <-> Layer Panel Sync
        self.layer_panel.sigZoomToLayer.connect(self.map_canvas.zoom_to_layer)
        self.map_canvas.sigLayerAdded.connect(self.layer_panel.add_layer)
        self.map_canvas.sigLayerRemoved.connect(self.layer_panel.remove_layer)
        self.layer_panel.sigLayerDeleted.connect(self.map_canvas.remove_layer)
        self.map_canvas.sigLayerVisibilityChanged.connect(
            self.layer_panel.set_layer_visibility
        )
        self.map_canvas.sigLayerOrderChanged.connect(self.layer_panel.set_layer_order)
        self.map_canvas.sigLayerRenamed.connect(self.layer_panel.rename_layer)
        self.v_splitter.splitterMoved.connect(self._on_vertical_splitter_moved)

    def _apply_vertical_sizes(self, map_height: int, panel_height: int) -> None:
        """Apply vertical splitter sizes with fixed status bar.

        Parameters
        ----------
        map_height : int
            Desired height of map canvas section in pixels.
        panel_height : int
            Desired height of bottom panel host section in pixels.
        """
        status_height = max(1, self.status_bar.height())
        self.v_splitter.setSizes(
            [max(0, map_height), max(0, panel_height), status_height]
        )

    def _on_vertical_splitter_moved(self, _pos: int, _index: int) -> None:
        """Enforce bottom panel behavior after user drags splitter."""
        if self._is_adjusting_bottom_panel:
            return
        map_height, panel_height, _ = self.v_splitter.sizes()
        if panel_height <= self._bottom_auto_hide_height_px:
            self.hide_panel()
            return
        if panel_height <= map_height:
            return
        self._clamp_bottom_panel_half_ratio(map_height, panel_height)

    def _clamp_bottom_panel_half_ratio(
        self, map_height: int, panel_height: int
    ) -> None:
        """Clamp bottom panel max height to 1:1 ratio against map area."""
        total = max(0, map_height + panel_height)
        clamped_panel = total // 2
        clamped_map = total - clamped_panel
        self._is_adjusting_bottom_panel = True
        self._apply_vertical_sizes(clamped_map, clamped_panel)
        self._is_adjusting_bottom_panel = False

    def show_panel(self, name: str) -> bool:
        """Show registered panel in bottom host.

        Parameters
        ----------
        name : str
            Registered panel name in ``BottomPanelHost``.

        Returns
        -------
        bool
            ``True`` when panel exists and is shown.
        """
        if not self.bottom_panel_host.show_panel(name):
            return False
        map_height, panel_height, _ = self.v_splitter.sizes()
        available = max(0, map_height + panel_height)
        next_panel_height = max(120, available // 5)
        next_map_height = max(0, available - next_panel_height)
        self._apply_vertical_sizes(next_map_height, next_panel_height)
        return True

    def hide_panel(self) -> None:
        """Hide bottom panel host and return space back to map."""
        self.bottom_panel_host.hide_panel()
        map_height, panel_height, _ = self.v_splitter.sizes()
        self._apply_vertical_sizes(
            map_height + panel_height - self._bottom_collapsed_height_px,
            self._bottom_collapsed_height_px,
        )

    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self.map_canvas, "cleanup"):
            self.map_canvas.cleanup()
