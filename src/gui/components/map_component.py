
from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Qt, Signal

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

        # 2. Vertical Splitter for Map | Status Bar
        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.v_splitter.setHandleWidth(1)

        self.h_splitter.addWidget(self.v_splitter)
        
        # 2. Map Canvas
        self.map_canvas = MapCanvas()
        self.v_splitter.addWidget(self.map_canvas)

        # 3. Status Bar
        self.status_bar = StatusBar()
        self.v_splitter.addWidget(self.status_bar)
        
        layout.addWidget(self.h_splitter, 1) # Take available vertical space


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

        # Map Canvas -> Self (re-emit)
        self.map_canvas.sigCoordinateChanged.connect(self.sigCoordinateChanged.emit)
        self.map_canvas.sigZoomChanged.connect(self.sigZoomChanged.emit)
        self.map_canvas.sigRotationChanged.connect(self.sigRotationChanged.emit)

    def cleanup(self):
        """Cleanup resources."""
        if hasattr(self.map_canvas, 'cleanup'):
            self.map_canvas.cleanup()
