"""
Base classes for tool pages (formerly Ribbon components).
"""

from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QGroupBox,
    QStatusBar,
)

from src.gui.components.map_component import MapComponent
from src.gui.components.property_panel import PropertyPanel
from src.gui.config import cfg
from qfluentwidgets import Theme
from pathlib import Path

class PageGroup(QGroupBox):
    """
    A group of controls within a tool page.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)
        self.setObjectName("PageGroup")

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 16, 8, 8)
        self._layout.setSpacing(8)

    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the group."""
        self._layout.addWidget(widget)

    def add_stretch(self) -> None:
        """Add stretch to the group layout."""
        self._layout.addStretch()


class BaseInterface(QWidget):
    """
    Base class for all functional interfaces.
    """
    """
    Structure:
    - Top: Tool Bar (contains PageGroups)
    - Center: Content Area (page specific content)
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # Main Layout (Vertical)
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        # 1. Tool Bar Area (Top)
        self.tool_bar = QWidget()
        self.tool_bar.setObjectName("ToolBar")
        self.tool_bar.setMinimumHeight(80)
        self.tool_bar.setMaximumHeight(120)
        
        self._tool_layout = QHBoxLayout(self.tool_bar)
        self._tool_layout.setContentsMargins(4, 4, 4, 4)
        self._tool_layout.setSpacing(8)
        
        self._main_layout.addWidget(self.tool_bar)
        
        # Load theme styles
        self.setQss()
        cfg.themeChanged.connect(self.setQss)

        # 2. Content Area (Center)
        self.content_area = QWidget()
        self.content_area.setObjectName("ContentArea")
        self._content_layout = QVBoxLayout(self.content_area)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(0)
        
        self._main_layout.addWidget(self.content_area, 1) # Stretch factor 1

    def add_group(self, group: PageGroup) -> None:
        """Add a group to the tool bar."""
        self._tool_layout.addWidget(group)

    def add_stretch(self) -> None:
        """Add stretch at the end of tool bar."""
        self._tool_layout.addStretch()

    def setQss(self):
        """Apply QSS."""
        theme = cfg.themeMode.value
        if theme == Theme.AUTO:
            import darkdetect
            theme_name = "dark" if darkdetect.isDark() else "light"
        else:
            theme_name = theme.value.lower()
            
        qss_path = Path(__file__).parent.parent / "resource" / "qss" / theme_name / "base_interface.qss"
        if qss_path.exists():
            with open(qss_path, encoding='utf-8') as f:
                self.setStyleSheet(f.read())

class TabInterface(BaseInterface):
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
        # self.splitter.addWidget(self.property_panel)
        self.property_panel.hide()  # Hide globally as per requirement

        self.splitter.setSizes([800, 200])

        # Add to Content Area of BaseInterface
        self._content_layout.addWidget(self.splitter)

        # Forward signals from MapComponent
        self.map_component.sigCoordinateChanged.connect(self.sigCoordinateChanged.emit)
        self.map_component.sigZoomChanged.connect(self.sigZoomChanged.emit)
        self.map_component.sigRotationChanged.connect(self.sigRotationChanged.emit)
