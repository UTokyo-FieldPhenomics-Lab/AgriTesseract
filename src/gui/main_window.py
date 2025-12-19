"""
Main Window for EasyPlantFieldID GUI Application.

This module provides the main application window with Sidebar Navigation UI,
featuring a flexible layout: Sidebar | Tool Bar (Top) | Content Panels.
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
    QStackedWidget,
)
from PySide6.QtCore import Qt, Signal
from loguru import logger
from qfluentwidgets import NavigationInterface, NavigationItemPosition, FluentIcon

from src.gui.pages.subplot_page import SubplotPage
from src.gui.pages.seedling_page import SeedlingPage
from src.gui.pages.rename_page import RenamePage
from src.gui.pages.timeseries_page import TimeSeriesPage
from src.gui.pages.annotate_page import AnnotatePage
from src.gui.pages.settings_page import SettingsPage

from src.gui.components.map_canvas import MapCanvas
from src.gui.components.layer_panel import LayerPanel
from src.gui.components.property_panel import PropertyPanel
from src.gui.i18n import tr, set_language


class MainWindow(QMainWindow):
    """
    Main application window with Sidebar Navigation UI.

    The window consists of:
    - NavigationInterface (left): Sidebar navigation
    - ToolStack (top right): Context-specific tool controls (formerly Ribbon)
    - Content Area (center right):
        - LayerPanel (left)
        - MapCanvas (center)
        - PropertyPanel (right)
    - StatusBar (bottom)
    """

    sigCoordinateChanged = Signal(float, float)
    sigZoomChanged = Signal(float)
    sigRotationChanged = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.setWindowTitle(tr("app.title"))
        self.setGeometry(100, 100, 1500, 900)

        # Initialize UI components
        self._init_ui()

        # Connect signals
        self._connect_signals()

        # Set initial style
        self.navigation_interface.setExpandWidth(200)

        logger.info("MainWindow initialized successfully")

    def _init_ui(self) -> None:
        """Initialize the user interface components."""
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Root layout (Horizontal: Nav | Content)
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # --- Navigation Interface (Left Sidebar) ---
        self.navigation_interface = NavigationInterface(self, showMenuButton=True, showReturnButton=False)
        root_layout.addWidget(self.navigation_interface)

        # --- Main Content Area (Right Side) ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        root_layout.addWidget(content_widget, 1) # Stretch factor 1 to take remaining space

        # 1. Tool Stack (Top Bar - formerly Ribbon Content)
        self.tool_stack = QStackedWidget()
        self.tool_stack.setStyleSheet("background-color: #f9f9f9; border-bottom: 1px solid #e0e0e0;")
        
        # Create and add pages
        self.subplot_page = SubplotPage()
        self.seedling_page = SeedlingPage()
        self.rename_page = RenamePage()
        self.timeseries_page = TimeSeriesPage()
        self.annotate_page = AnnotatePage()
        self.settings_page = SettingsPage(None)

        self.tool_stack.addWidget(self.subplot_page)
        self.tool_stack.addWidget(self.seedling_page)
        self.tool_stack.addWidget(self.rename_page)
        self.tool_stack.addWidget(self.timeseries_page)
        self.tool_stack.addWidget(self.annotate_page)
        self.tool_stack.addWidget(self.settings_page)

        # Add navigation items
        self._init_navigation()

        content_layout.addWidget(self.tool_stack)

        # 2. Panels Splitter (Center)
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setHandleWidth(1)

        # Left panel: Layer Panel
        self.layer_panel = LayerPanel()
        self.main_splitter.addWidget(self.layer_panel)

        # Center panel: Map Canvas
        self.map_canvas = MapCanvas()
        self.main_splitter.addWidget(self.map_canvas)

        # Right panel: Property Panel
        self.property_panel = PropertyPanel()
        self.main_splitter.addWidget(self.property_panel)

        # Set initial sizes (1:4:1 ratio)
        self.main_splitter.setSizes([200, 1000, 250])

        content_layout.addWidget(self.main_splitter, 1) # Stretch factor 1 to take remaining vertical space

        # --- Status Bar ---
        self._init_status_bar()

    def _init_navigation(self):
        """Initialize navigation items."""
        # Top-aligned items
        self.navigation_interface.addItem(
            routeKey="subplot",
            icon=FluentIcon.TILES,
            text=tr("nav.subplot"),
            onClick=lambda: self._switch_page(0)
        )
        self.navigation_interface.addItem(
            routeKey="seedling",
            icon=FluentIcon.LEAF,
            text=tr("nav.seedling"),
            onClick=lambda: self._switch_page(1)
        )
        self.navigation_interface.addItem(
            routeKey="rename",
            icon=FluentIcon.EDIT,
            text=tr("nav.rename"),
            onClick=lambda: self._switch_page(2)
        )
        self.navigation_interface.addItem(
            routeKey="timeseries",
            icon=FluentIcon.HISTORY,
            text=tr("nav.timeseries"),
            onClick=lambda: self._switch_page(3)
        )
        self.navigation_interface.addItem(
            routeKey="annotate",
            icon=FluentIcon.PENCIL_INK,
            text=tr("nav.annotate"),
            onClick=lambda: self._switch_page(4)
        )

        # Bottom items
        self.navigation_interface.addItem(
            routeKey="settings",
            icon=FluentIcon.SETTING,
            text=tr("nav.settings"),
            onClick=lambda: self._switch_page(5),
            position=NavigationItemPosition.BOTTOM
        )

        # Set initial selection
        self.navigation_interface.setCurrentItem("subplot")

    def _switch_page(self, index: int):
        """Switch tool stack and property panel."""
        self.tool_stack.setCurrentIndex(index)
        self.property_panel.set_current_tab(index)

    def _init_status_bar(self) -> None:
        """Initialize the status bar."""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        # Coordinate label
        self.coord_label = QLabel(tr("status.coord").format(x=0.0, y=0.0))
        self.coord_label.setMinimumWidth(200)
        self.status_bar.addWidget(self.coord_label)

        self.status_bar.addWidget(QLabel("|"))

        # Zoom label
        self.zoom_label = QLabel(tr("status.zoom").format(zoom=100))
        self.zoom_label.setMinimumWidth(100)
        self.status_bar.addWidget(self.zoom_label)

        self.status_bar.addWidget(QLabel("|"))

        # Rotation label
        self.rotation_label = QLabel(tr("status.rotation").format(angle=0.0))
        self.rotation_label.setMinimumWidth(120)
        self.status_bar.addWidget(self.rotation_label)

        # Stretch
        self.status_bar.addWidget(QLabel(""), 1)

        # Status message
        self.status_message = QLabel(tr("status.ready"))
        self.status_bar.addPermanentWidget(self.status_message)

    def _connect_signals(self) -> None:
        """Connect internal signals between components."""
        # Map canvas signals
        self.map_canvas.sigCoordinateChanged.connect(self._update_coordinates)
        self.map_canvas.sigZoomChanged.connect(self._update_zoom)
        self.map_canvas.sigRotationChanged.connect(self._update_rotation)

        # Layer panel signals
        self.layer_panel.sigLayerVisibilityChanged.connect(
            self.map_canvas.set_layer_visibility
        )
        self.layer_panel.sigLayerOrderChanged.connect(
            self.map_canvas.update_layer_order
        )

        # Connect new Page signals (examples from original code)
        # SubplotPage
        self.subplot_page.sigGenerate.connect(lambda: logger.info("Generate Subplot triggered"))
        
        # SeedlingPage
        self.seedling_page.sigDetect.connect(lambda: logger.info("Detect Seedling triggered"))

        # TODO: Connect other signals as implementation progresses

    def _update_coordinates(self, x: float, y: float) -> None:
        self.coord_label.setText(tr("status.coord").format(x=x, y=y))
        self.sigCoordinateChanged.emit(x, y)

    def _update_zoom(self, zoom_level: float) -> None:
        self.zoom_label.setText(tr("status.zoom").format(zoom=zoom_level))
        self.sigZoomChanged.emit(zoom_level)

    def _update_rotation(self, angle: float) -> None:
        self.rotation_label.setText(tr("status.rotation").format(angle=angle))
        self.sigRotationChanged.emit(angle)

    def set_status_message(self, message: str) -> None:
        self.status_message.setText(message)

    def closeEvent(self, event) -> None:
        logger.info("MainWindow closing")
        self.map_canvas.cleanup()
        super().closeEvent(event)
