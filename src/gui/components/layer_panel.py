"""
Layer Panel component for EasyPlantFieldID GUI.

This module provides a layer management panel with:
- Tree-based layer list with drag-drop reordering
- Visibility toggle (checkbox)
- Right-click context menu
- Double-click rename

References
----------
- dev.notes/04_demo_layer_manage_drag.py: Layer management with drag-drop
"""

from typing import Optional, List, Dict

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTreeWidget,
    QTreeWidgetItem,
    QPushButton,
    QMenu,
    QLabel,
    QAbstractItemView,
    QMessageBox,
    QFileDialog,
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QAction, QDragEnterEvent, QDropEvent, QDragMoveEvent
from loguru import logger

from src.gui.config import tr


class DraggableTreeWidget(QTreeWidget):
    """
    QTreeWidget subclass with drag-drop reordering support.

    Signals
    -------
    sigOrderChanged : Signal()
        Emitted when item order changes via drag-drop.
    """

    sigOrderChanged = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        # Enable drag-drop
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        """Accept drag enter events."""
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        """Accept drag move events."""
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        """Handle drop events and emit order changed signal."""
        super().dropEvent(event)
        if event.isAccepted():
            self.sigOrderChanged.emit()


class LayerPanel(QWidget):
    """
    Layer management panel with tree-based layer list.

    Features:
    - Drag-drop layer reordering
    - Visibility toggle via checkbox
    - Right-click context menu (delete, zoom to, properties)
    - Double-click to rename
    - Add/remove layer buttons

    Signals
    -------
    sigLayerVisibilityChanged : Signal(str, bool)
        Emitted when layer visibility changes. Args: (layer_name, visible)
    sigLayerOrderChanged : Signal(list)
        Emitted when layer order changes. Args: (ordered_layer_names)
    sigLayerSelected : Signal(str)
        Emitted when a layer is selected. Args: (layer_name)
    sigLayerDeleted : Signal(str)
        Emitted when a layer is deleted. Args: (layer_name)
    sigAddLayerRequested : Signal()
        Emitted when add layer button is clicked.

    Examples
    --------
    >>> panel = LayerPanel()
    >>> panel.add_layer("DOM", "raster")
    >>> panel.add_layer("Points", "vector")
    >>> panel.sigLayerVisibilityChanged.connect(lambda n, v: print(f"{n}: {v}"))
    """

    sigLayerVisibilityChanged = Signal(str, bool)
    sigLayerOrderChanged = Signal(list)
    sigLayerSelected = Signal(str)
    sigLayerDeleted = Signal(str)
    sigAddLayerRequested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the Layer Panel.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)

        # Layer registry: {name: {'type': str, 'visible': bool}}
        self._layers: Dict[str, Dict] = {}

        # Store old name for rename tracking
        self._old_rename_key: Optional[str] = None

        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI components."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel(tr("layer_panel.title"))
        header_layout.addWidget(header_label)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Tree widget for layers
        self._tree = DraggableTreeWidget()
        self._tree.setHeaderLabels([tr("layer_panel.title")])
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)
        self._tree.setIndentation(0)

        # Enable right-click context menu
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        # Connect signals
        self._tree.sigOrderChanged.connect(self._on_order_changed)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.currentItemChanged.connect(self._on_selection_changed)
        self._tree.itemDoubleClicked.connect(self._start_rename)

        layout.addWidget(self._tree, 1)

        # Button bar
        btn_layout = QHBoxLayout()

        self._btn_add = QPushButton("+")
        self._btn_add.setMaximumWidth(30)
        self._btn_add.setToolTip(tr("layer_panel.add_tooltip"))
        self._btn_add.clicked.connect(self._on_add_clicked)
        btn_layout.addWidget(self._btn_add)

        self._btn_remove = QPushButton("-")
        self._btn_remove.setMaximumWidth(30)
        self._btn_remove.setToolTip(tr("layer_panel.remove_tooltip"))
        self._btn_remove.setEnabled(False)
        self._btn_remove.clicked.connect(self._on_remove_clicked)
        btn_layout.addWidget(self._btn_remove)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Set minimum width
        self.setMinimumWidth(150)
        self.setMaximumWidth(300)

    def add_layer(
        self,
        name: str,
        layer_type: str = "raster",
        visible: bool = True
    ) -> None:
        """
        Add a layer to the panel.

        Parameters
        ----------
        name : str
            Layer name.
        layer_type : str, optional
            Type of layer ("raster" or "vector"), by default "raster".
        visible : bool, optional
            Initial visibility, by default True.
        """
        if name in self._layers:
            logger.warning(f"Layer '{name}' already exists")
            return

        # Block signals during setup
        self._tree.blockSignals(True)

        # Create tree item
        item = QTreeWidgetItem([name])
        item.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable |
            Qt.ItemFlag.ItemIsEditable |
            Qt.ItemFlag.ItemIsEnabled |
            Qt.ItemFlag.ItemIsSelectable |
            Qt.ItemFlag.ItemIsDragEnabled
        )
        item.setCheckState(0, Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)

        # Set icon based on type
        if layer_type == "raster":
            item.setText(0, f"🗺️ {name}")
        else:
            item.setText(0, f"📍 {name}")

        # Insert at top
        self._tree.insertTopLevelItem(0, item)

        # Register layer
        self._layers[name] = {
            'type': layer_type,
            'visible': visible,
            'item': item
        }

        self._tree.blockSignals(False)
        self._tree.setCurrentItem(item)

        # Emit order changed
        self._on_order_changed()

        logger.debug(f"Layer added: {name} ({layer_type})")

    def remove_layer(self, name: str) -> bool:
        """
        Remove a layer from the panel.

        Parameters
        ----------
        name : str
            Name of the layer to remove.

        Returns
        -------
        bool
            True if layer was removed, False if not found.
        """
        if name not in self._layers:
            return False

        layer_info = self._layers[name]
        item = layer_info.get('item')

        if item:
            root = self._tree.invisibleRootItem()
            root.removeChild(item)

        del self._layers[name]
        self.sigLayerDeleted.emit(name)

        logger.debug(f"Layer removed: {name}")
        return True

    def get_layer_order(self) -> List[str]:
        """
        Get the current layer order (top to bottom).

        Returns
        -------
        List[str]
            List of layer names from top to bottom.
        """
        order = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            # Extract name from display text (remove icon)
            text = item.text(0)
            # Remove emoji prefix if present
            if text.startswith("🗺️ ") or text.startswith("📍 "):
                name = text[3:]
            else:
                name = text
            order.append(name)
        return order

    def set_layer_visibility(self, name: str, visible: bool) -> None:
        """
        Set visibility of a layer.

        Parameters
        ----------
        name : str
            Layer name.
        visible : bool
            Visibility state.
        """
        if name not in self._layers:
            return

        self._layers[name]['visible'] = visible
        item = self._layers[name].get('item')
        if item:
            self._tree.blockSignals(True)
            item.setCheckState(0, Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked)
            self._tree.blockSignals(False)

    def _on_order_changed(self) -> None:
        """Handle layer order change."""
        order = self.get_layer_order()
        self.sigLayerOrderChanged.emit(order)

        # Update Z-values
        count = self._tree.topLevelItemCount()
        for i in range(count):
            item = self._tree.topLevelItem(i)
            # Higher index = lower Z-value (bottom layers)
            # Items at top of list should have highest Z
            pass  # Z-value management is done in MapCanvas

        logger.debug(f"Layer order changed: {order}")

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item changes (visibility toggle or rename)."""
        if column != 0:
            return

        # Check if this is a rename operation
        if self._old_rename_key is not None:
            old_name = self._old_rename_key
            new_text = item.text(0)

            # Extract new name (remove icon)
            if new_text.startswith("🗺️ ") or new_text.startswith("📍 "):
                new_name = new_text[3:]
            else:
                new_name = new_text

            self._old_rename_key = None

            if old_name != new_name:
                self._process_rename(old_name, new_name, item)
            return

        # Otherwise, handle visibility change
        self._process_visibility_change(item)

    def _process_visibility_change(self, item: QTreeWidgetItem) -> None:
        """Process visibility checkbox change."""
        text = item.text(0)
        if text.startswith("🗺️ ") or text.startswith("📍 "):
            name = text[3:]
        else:
            name = text

        if name not in self._layers:
            return

        visible = item.checkState(0) == Qt.CheckState.Checked
        self._layers[name]['visible'] = visible
        self.sigLayerVisibilityChanged.emit(name, visible)

        logger.debug(f"Layer '{name}' visibility: {visible}")

    def _process_rename(
        self, old_name: str, new_name: str, item: QTreeWidgetItem
    ) -> None:
        """Process layer rename."""
        # Check if new name already exists
        if new_name in self._layers:
            QMessageBox.warning(
                self, 
                tr("layer_panel.rename.fail.title"), 
                tr("layer_panel.rename.fail.msg").format(name=new_name)
            )
            # Revert to old name
            self._tree.blockSignals(True)
            layer_type = self._layers[old_name]['type']
            icon = "🗺️ " if layer_type == "raster" else "📍 "
            item.setText(0, f"{icon}{old_name}")
            self._tree.blockSignals(False)
            return

        # Update registry
        self._layers[new_name] = self._layers.pop(old_name)
        logger.debug(f"Layer renamed: '{old_name}' -> '{new_name}'")

    def _on_selection_changed(
        self,
        current: QTreeWidgetItem,
        previous: QTreeWidgetItem
    ) -> None:
        """Handle layer selection change."""
        self._btn_remove.setEnabled(current is not None)

        if current:
            text = current.text(0)
            if text.startswith("🗺️ ") or text.startswith("📍 "):
                name = text[3:]
            else:
                name = text
            self.sigLayerSelected.emit(name)

    def _start_rename(self, item: QTreeWidgetItem, column: int) -> None:
        """Start rename operation on double-click."""
        if column == 0:
            text = item.text(0)
            if text.startswith("🗺️ ") or text.startswith("📍 "):
                self._old_rename_key = text[3:]
            else:
                self._old_rename_key = text
            self._tree.editItem(item, 0)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu on right-click."""
        item = self._tree.itemAt(position)
        if not item:
            return

        text = item.text(0)
        if text.startswith("🗺️ ") or text.startswith("📍 "):
            name = text[3:]
        else:
            name = text

        menu = QMenu(self)

        # Zoom to layer action
        zoom_action = QAction(tr("layer_panel.menu.zoom"), self)
        zoom_action.triggered.connect(lambda: self._zoom_to_layer(name))
        menu.addAction(zoom_action)

        menu.addSeparator()

        # Delete action
        delete_action = QAction(tr("layer_panel.menu.delete"), self)
        delete_action.triggered.connect(lambda: self._delete_layer(name))
        menu.addAction(delete_action)

        menu.exec(self._tree.mapToGlobal(position))

    def _zoom_to_layer(self, name: str) -> None:
        """Zoom to layer extent."""
        # This will be connected to MapCanvas externally
        logger.debug(f"Zoom to layer: {name}")

    def _delete_layer(self, name: str) -> None:
        """Delete a layer after confirmation."""
        reply = QMessageBox.question(
            self,
            tr("layer_panel.confirm.delete.title"),
            tr("layer_panel.confirm.delete.msg").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.remove_layer(name)

    def _on_add_clicked(self) -> None:
        """Handle add layer button click."""
        self.sigAddLayerRequested.emit()

    def _on_remove_clicked(self) -> None:
        """Handle remove layer button click."""
        current = self._tree.currentItem()
        if current:
            text = current.text(0)
            if text.startswith("🗺️ ") or text.startswith("📍 "):
                name = text[3:]
            else:
                name = text
            self._delete_layer(name)

    def clear(self) -> None:
        """Remove all layers."""
        for name in list(self._layers.keys()):
            self.remove_layer(name)
