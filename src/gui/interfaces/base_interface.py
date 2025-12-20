"""
Base classes for tool pages (formerly Ribbon components).
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QStatusBar,
)

class PageGroup(QGroupBox):
    """
    A group of controls within a tool page.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #505050;
            }
        """)

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
        # Add a bottom border style
        self.tool_bar.setStyleSheet("#ToolBar { background-color: #f9f9f9; border-bottom: 1px solid #e0e0e0; }")
        
        self._tool_layout = QHBoxLayout(self.tool_bar)
        self._tool_layout.setContentsMargins(4, 4, 4, 4)
        self._tool_layout.setSpacing(8)
        
        self._main_layout.addWidget(self.tool_bar)

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
