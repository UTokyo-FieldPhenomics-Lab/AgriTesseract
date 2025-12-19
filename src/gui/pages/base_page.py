"""
Base classes for tool pages (formerly Ribbon components).
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
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


class BasePage(QWidget):
    """
    Base class for tool pages.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(8)

        self.setMinimumHeight(80)
        self.setMaximumHeight(100)

    def add_group(self, group: PageGroup) -> None:
        """Add a group to this page."""
        self._layout.addWidget(group)

    def add_stretch(self) -> None:
        """Add stretch at the end."""
        self._layout.addStretch()
