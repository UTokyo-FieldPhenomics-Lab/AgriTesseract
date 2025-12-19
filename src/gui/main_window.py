"""
Main Window for EasyPlantFieldID GUI Application.

This module provides the main application window with Ribbon-style UI,
featuring a three-panel layout: Layer Panel | Map Canvas | Property Panel.

References
----------
- dev.notes/06_demo_layer_rotation.py: Rotation and status bar implementation
"""

import sys
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSplitter,
    QStatusBar,
    QLabel,
)
from PySide6.QtCore import Qt, Signal
from loguru import logger

from src.gui.components.ribbon_bar import RibbonBar
from src.gui.components.map_canvas import MapCanvas
from src.gui.components.layer_panel import LayerPanel
from src.gui.components.property_panel import PropertyPanel


class MainWindow(QMainWindow):
    """
    Main application window with Ribbon-style UI.

    The window consists of:
    - RibbonBar (top): Office-style tabbed toolbar
    - LayerPanel (left 1/6): Layer management
    - MapCanvas (center 2/3): GeoTiff viewer
    - PropertyPanel (right 1/6): Parameter panel
    - StatusBar (bottom): Coordinates, zoom, rotation

    Attributes
    ----------
    ribbon_bar : RibbonBar
        The Ribbon-style toolbar at the top.
    layer_panel : LayerPanel
        The layer management panel on the left.
    map_canvas : MapCanvas
        The main GeoTiff viewer in the center.
    property_panel : PropertyPanel
        The property/parameter panel on the right.

    Signals
    -------
    sigCoordinateChanged : Signal(float, float)
        Emitted when cursor position changes on map.
    sigZoomChanged : Signal(float)
        Emitted when zoom level changes.
    sigRotationChanged : Signal(float)
        Emitted when rotation angle changes.

    Examples
    --------
    >>> app = QApplication(sys.argv)
    >>> window = MainWindow()
    >>> window.show()
    >>> sys.exit(app.exec())
    """

    sigCoordinateChanged = Signal(float, float)
    sigZoomChanged = Signal(float)
    sigRotationChanged = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the main window.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget, by default None.
        """
        super().__init__(parent)

        self.setWindowTitle("EasyPlantFieldID - GIS Preprocessing Tool")
        self.setGeometry(100, 100, 1400, 900)

        # Initialize UI components
        self._init_ui()

        # Connect signals
        self._connect_signals()

        logger.info("MainWindow initialized successfully")

    def _init_ui(self) -> None:
        """Initialize the user interface components."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main vertical layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- Ribbon Bar ---
        self.ribbon_bar = RibbonBar()
        main_layout.addWidget(self.ribbon_bar)

        # --- Main Content Area (Splitter) ---
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left panel: Layer Panel (1/6 width)
        self.layer_panel = LayerPanel()
        self.main_splitter.addWidget(self.layer_panel)

        # Center panel: Map Canvas (2/3 width)
        self.map_canvas = MapCanvas()
        self.main_splitter.addWidget(self.map_canvas)

        # Right panel: Property Panel (1/6 width)
        self.property_panel = PropertyPanel()
        self.main_splitter.addWidget(self.property_panel)

        # Set initial sizes (1:4:1 ratio)
        self.main_splitter.setSizes([200, 800, 200])

        main_layout.addWidget(self.main_splitter)

        # --- Status Bar ---
        self._init_status_bar()

    def _init_status_bar(self) -> None:
        """Initialize the status bar with coordinate, zoom, and rotation display."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Coordinate label
        self.coord_label = QLabel("坐标: X: 0.00, Y: 0.00")
        self.coord_label.setMinimumWidth(200)
        self.status_bar.addWidget(self.coord_label)

        # Separator
        self.status_bar.addWidget(QLabel("|"))

        # Zoom label
        self.zoom_label = QLabel("缩放: 100%")
        self.zoom_label.setMinimumWidth(100)
        self.status_bar.addWidget(self.zoom_label)

        # Separator
        self.status_bar.addWidget(QLabel("|"))

        # Rotation label
        self.rotation_label = QLabel("旋转角度: 0.00°")
        self.rotation_label.setMinimumWidth(120)
        self.status_bar.addWidget(self.rotation_label)

        # Stretch to push progress bar to the right
        self.status_bar.addWidget(QLabel(""), 1)

        # Status message (right side)
        self.status_message = QLabel("就绪")
        self.status_bar.addPermanentWidget(self.status_message)

    def _connect_signals(self) -> None:
        """Connect internal signals between components."""
        # Connect map canvas signals to status bar updates
        self.map_canvas.sigCoordinateChanged.connect(self._update_coordinates)
        self.map_canvas.sigZoomChanged.connect(self._update_zoom)
        self.map_canvas.sigRotationChanged.connect(self._update_rotation)

        # Connect ribbon bar tab changes
        self.ribbon_bar.sigTabChanged.connect(self._on_tab_changed)

        # Connect layer panel signals to map canvas
        self.layer_panel.sigLayerVisibilityChanged.connect(
            self.map_canvas.set_layer_visibility
        )
        self.layer_panel.sigLayerOrderChanged.connect(
            self.map_canvas.update_layer_order
        )

    def _update_coordinates(self, x: float, y: float) -> None:
        """
        Update coordinate display in status bar.

        Parameters
        ----------
        x : float
            X coordinate (longitude or easting).
        y : float
            Y coordinate (latitude or northing).
        """
        self.coord_label.setText(f"坐标: X: {x:.2f}, Y: {y:.2f}")
        self.sigCoordinateChanged.emit(x, y)

    def _update_zoom(self, zoom_level: float) -> None:
        """
        Update zoom level display in status bar.

        Parameters
        ----------
        zoom_level : float
            Current zoom level as percentage.
        """
        self.zoom_label.setText(f"缩放: {zoom_level:.0f}%")
        self.sigZoomChanged.emit(zoom_level)

    def _update_rotation(self, angle: float) -> None:
        """
        Update rotation angle display in status bar.

        Parameters
        ----------
        angle : float
            Current rotation angle in degrees.
        """
        self.rotation_label.setText(f"旋转角度: {angle:.2f}°")
        self.sigRotationChanged.emit(angle)

    def _on_tab_changed(self, tab_index: int) -> None:
        """
        Handle ribbon bar tab change.

        Parameters
        ----------
        tab_index : int
            Index of the newly selected tab.
        """
        logger.debug(f"Tab changed to index: {tab_index}")
        # Update property panel based on current tab
        self.property_panel.set_current_tab(tab_index)

    def set_status_message(self, message: str) -> None:
        """
        Set the status bar message.

        Parameters
        ----------
        message : str
            Message to display in the status bar.
        """
        self.status_message.setText(message)

    def closeEvent(self, event) -> None:
        """
        Handle window close event.

        Parameters
        ----------
        event : QCloseEvent
            The close event.
        """
        logger.info("MainWindow closing")
        # Clean up resources
        self.map_canvas.cleanup()
        super().closeEvent(event)


def main() -> None:
    """Main entry point for the application."""
    import pyqtgraph as pg

    # Configure PyQtGraph
    pg.setConfigOptions(imageAxisOrder='row-major')

    app = QApplication(sys.argv)
    app.setApplicationName("EasyPlantFieldID")
    app.setApplicationVersion("0.1.0")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
