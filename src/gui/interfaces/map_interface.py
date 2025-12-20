from typing import Optional

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PySide6.QtCore import Signal, Qt

from src.gui.interfaces.base_interface import BaseInterface, PageGroup
from src.gui.components.map_component import MapComponent
from src.gui.components.property_panel import PropertyPanel

class MapInterface(BaseInterface):
    """
    Base Interface for GIS functionality.
    Layout:
    [ Toolbar ]
    [ MapComponent | PropertyPanel ]
    """

    sigCoordinateChanged = Signal(float, float)
    sigZoomChanged = Signal(float)
    sigRotationChanged = Signal(float)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_layout()

    def _init_layout(self):
        # Create Splitter for MapComponent | PropertyPanel
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # 1. Map Component (Left)
        self.map_component = MapComponent()
        self.splitter.addWidget(self.map_component)

        # 2. Property Panel (Right)
        self.property_panel = PropertyPanel()
        self.splitter.addWidget(self.property_panel)

        self.splitter.setSizes([800, 200])

        # Add to Content Area of BaseInterface
        self._content_layout.addWidget(self.splitter)

        # Forward signals from MapComponent
        self.map_component.sigCoordinateChanged.connect(self.sigCoordinateChanged.emit)
        self.map_component.sigZoomChanged.connect(self.sigZoomChanged.emit)
        self.map_component.sigRotationChanged.connect(self.sigRotationChanged.emit)
