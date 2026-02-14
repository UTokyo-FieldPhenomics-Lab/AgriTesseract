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
    QTreeWidgetItem,
    QLabel,
    QAbstractItemView,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal, QPoint
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent, QAction
from loguru import logger

from qfluentwidgets import (
    TreeWidget,
    CommandBar,
    Action,
    FluentIcon as FIF,
    Flyout,
    FlyoutAnimationType,
    RoundMenu,
    MenuAnimationType,
)

from src.gui.config import tr, cfg
from qfluentwidgets import Theme
import darkdetect
from pathlib import Path


class DraggableTreeWidget(TreeWidget):
    """
    TreeWidget subclass with drag-drop reordering support.

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
    Layer management panel with fluent tree-based layer list.

    Features:
    - Drag-drop layer reordering
    - Visibility toggle via checkbox
    - Fluent context menu (CommandBarFlyout)
    - Double-click to rename

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
        Emitted when add layer is requested from menu.
    sigContextMenuRequested : Signal(object, object)
        Emitted when context menu is creating. Args: (menu, layer_name_or_none)
        Allows external interfaces to add actions.
    """

    sigLayerVisibilityChanged = Signal(str, bool)
    sigLayerOrderChanged = Signal(list)
    sigLayerSelected = Signal(str)
    sigLayerDeleted = Signal(str)
    sigAddLayerRequested = Signal()
    sigContextMenuRequested = Signal(
        object, object
    )  # menu object, layer name (or None)
    sigZoomToLayer = Signal(str)

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
        self.setQss()
        cfg.themeChanged.connect(self.setQss)

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
        self._tree = DraggableTreeWidget(self)
        self._tree.setObjectName("LayerTree")
        self._tree.setHeaderLabels([tr("layer_panel.title")])
        self._tree.setHeaderHidden(True)
        self._tree.setRootIsDecorated(False)
        self._tree.setIndentation(0)

        # TreeWidget style tweaks
        self._tree.setBorderVisible(True)
        self._tree.setBorderRadius(8)

        # Enable right-click context menu
        self._tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self._tree.customContextMenuRequested.connect(self._show_context_menu)

        # Connect signals
        self._tree.sigOrderChanged.connect(self._on_order_changed)
        self._tree.itemChanged.connect(self._on_item_changed)
        self._tree.currentItemChanged.connect(self._on_selection_changed)
        self._tree.itemDoubleClicked.connect(self._start_rename)

        layout.addWidget(self._tree, 1)

        # Set minimum width
        self.setMinimumWidth(200)
        self.setMaximumWidth(400)

    def add_layer(
        self, name: str, layer_type: str = "raster", visible: bool = True
    ) -> None:
        """Add a layer to the panel."""
        if name in self._layers:
            logger.warning(f"Layer '{name}' already exists")
            return

        # Block signals during setup
        self._tree.blockSignals(True)

        # Create tree item
        item = QTreeWidgetItem([name])
        item.setFlags(
            Qt.ItemFlag.ItemIsUserCheckable
            | Qt.ItemFlag.ItemIsEditable
            | Qt.ItemFlag.ItemIsEnabled
            | Qt.ItemFlag.ItemIsSelectable
            | Qt.ItemFlag.ItemIsDragEnabled
        )
        item.setCheckState(
            0, Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
        )

        # Set icon based on type (Use text prefix as icon substitute or actual Icon if available)
        # Using emoji for now as per previous design, but could use FluentIcon
        if layer_type == "raster":
            item.setText(0, name)
            item.setIcon(0, FIF.IMAGE_EXPORT.icon())
        else:
            item.setText(0, name)
            item.setIcon(0, FIF.TRANSPARENT.icon())

        # Insert at top
        self._tree.insertTopLevelItem(0, item)

        # Register layer
        self._layers[name] = {"type": layer_type, "visible": visible, "item": item}

        self._tree.blockSignals(False)
        self._tree.setCurrentItem(item)

        # Emit order changed
        self._on_order_changed()

        logger.debug(
            f"Layer added: {name} ({layer_type}). Tree count: {self._tree.topLevelItemCount()}"
        )

    def remove_layer(self, name: str) -> bool:
        """Remove a layer from the panel."""
        if name not in self._layers:
            return False

        layer_info = self._layers[name]
        item = layer_info.get("item")

        if item:
            root = self._tree.invisibleRootItem()
            root.removeChild(item)

        del self._layers[name]
        self.sigLayerDeleted.emit(name)

        logger.debug(f"Layer removed: {name}")
        return True

    def get_layer_order(self) -> List[str]:
        """Get the current layer order (top to bottom)."""
        order = []
        for i in range(self._tree.topLevelItemCount()):
            item = self._tree.topLevelItem(i)
            name = item.text(0)
            order.append(name)
        return order

    def set_layer_visibility(self, name: str, visible: bool) -> None:
        """Set visibility of a layer."""
        if name not in self._layers:
            return

        self._layers[name]["visible"] = visible
        item = self._layers[name].get("item")
        if item:
            self._tree.blockSignals(True)
            item.setCheckState(
                0, Qt.CheckState.Checked if visible else Qt.CheckState.Unchecked
            )
            self._tree.blockSignals(False)

    def set_layer_order(self, order: List[str]) -> None:
        """Apply external layer order to tree without re-emitting signals.

        Parameters
        ----------
        order : list[str]
            Layer names from top to bottom.
        """
        item_list = []
        for layer_name in order:
            if layer_name not in self._layers:
                continue
            item_obj = self._layers[layer_name].get("item")
            if item_obj is not None:
                item_list.append(item_obj)
        if not item_list:
            return
        self._tree.blockSignals(True)
        root = self._tree.invisibleRootItem()
        for item_obj in item_list:
            root.removeChild(item_obj)
        for index, item_obj in enumerate(item_list):
            self._tree.insertTopLevelItem(index, item_obj)
        self._tree.blockSignals(False)

    def rename_layer(self, old_name: str, new_name: str) -> bool:
        """Rename one layer in panel tree and internal registry."""
        if old_name not in self._layers or new_name in self._layers:
            return False
        layer_info = self._layers.pop(old_name)
        item_obj = layer_info.get("item")
        if item_obj is not None:
            self._tree.blockSignals(True)
            item_obj.setText(0, new_name)
            self._tree.blockSignals(False)
        self._layers[new_name] = layer_info
        return True

    def _on_order_changed(self) -> None:
        """Handle layer order change."""
        order = self.get_layer_order()
        self.sigLayerOrderChanged.emit(order)
        logger.debug(f"Layer order changed: {order}")

    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle item changes (visibility toggle or rename)."""
        if column != 0:
            return

        # Check if this is a rename operation (text changed)
        current_name = item.text(0)

        # Determine if check state matches internal state
        is_checked = item.checkState(0) == Qt.CheckState.Checked

        if self._old_rename_key:
            # Finishing rename
            old_name = self._old_rename_key
            self._old_rename_key = None

            if old_name != current_name:
                self._process_rename(old_name, current_name, item)
            return

        # Visibility Check
        found_name = None
        for name, info in self._layers.items():
            if info["item"] == item:
                found_name = name
                break

        if found_name:
            # Check visibility mismatch
            if self._layers[found_name]["visible"] != is_checked:
                self._process_visibility_change(found_name, is_checked)

    def _process_visibility_change(self, name: str, visible: bool) -> None:
        """Process visibility checkbox change."""
        self._layers[name]["visible"] = visible
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
                tr("layer_panel.rename.fail.msg").format(name=new_name),
            )
            # Revert to old name
            self._tree.blockSignals(True)
            item.setText(0, old_name)
            self._tree.blockSignals(False)
            return

        # Update registry
        self._layers[new_name] = self._layers.pop(old_name)
        logger.debug(f"Layer renamed: '{old_name}' -> '{new_name}'")

    def _on_selection_changed(
        self, current: QTreeWidgetItem, previous: QTreeWidgetItem
    ) -> None:
        """Handle layer selection change."""
        if current:
            name = current.text(0)
            self.sigLayerSelected.emit(name)

    def _start_rename(self, item: QTreeWidgetItem, column: int) -> None:
        """Start rename operation on double-click."""
        if column == 0:
            self._old_rename_key = item.text(0)
            self._tree.editItem(item, 0)

    def _show_context_menu(self, position: QPoint) -> None:
        """Show context menu on right-click using CommandBarFlyout."""
        logger.debug(f"Context menu requested at {position}")
        item = self._tree.itemAt(position)

        layer_name = None
        if item:
            logger.debug(f"Item found at pos: {item.text(0)}")
            layer_name = item.text(0)
        else:
            logger.debug("No item found at pos")

        # Create CommandBar
        # We can't put CommandBar directly in menu, but we can use RoundMenu which is standard
        # Or Flyout with a view.
        # User requested: "Command bar flyout in blank space"
        # Let's use RoundMenu for now as it's more standard for Right Click context
        # But if user insists on CommandBarFlyout view style:

        menu = RoundMenu(parent=self)

        if layer_name:
            # Item Context Menu
            menu.addAction(
                Action(
                    FIF.ZOOM_IN,
                    tr("layer_panel.menu.zoom"),
                    triggered=lambda: self._zoom_to_layer(layer_name),
                )
            )
            menu.addSeparator()
            menu.addAction(
                Action(
                    FIF.DELETE,
                    tr("layer_panel.menu.delete"),
                    triggered=lambda: self._delete_layer(layer_name),
                )
            )

            # Emit signal for external actions
            self.sigContextMenuRequested.emit(menu, layer_name)

        else:
            # Blank Space Context Menu
            menu.addAction(
                Action(
                    FIF.ADD, tr("layer_panel.menu.add"), triggered=self._on_add_clicked
                )
            )

            # Emit signal for external actions (e.g. "Add Subplots")
            self.sigContextMenuRequested.emit(menu, None)

        try:
            menu.exec(self._tree.mapToGlobal(position))
        except Exception as e:
            logger.error(f"Failed to show context menu: {e}")

    def _zoom_to_layer(self, name: str) -> None:
        """Zoom to layer extent."""
        self.sigZoomToLayer.emit(name)
        logger.debug(f"Zoom to layer: {name}")

    def _delete_layer(self, name: str) -> None:
        """Delete a layer after confirmation."""
        reply = QMessageBox.question(
            self,
            tr("layer_panel.confirm.delete.title"),
            tr("layer_panel.confirm.delete.msg").format(name=name),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.remove_layer(name)

    def _on_add_clicked(self) -> None:
        """Handle add layer request."""
        self.sigAddLayerRequested.emit()

    def clear(self) -> None:
        """Remove all layers."""
        for name in list(self._layers.keys()):
            self.remove_layer(name)

    def setQss(self):
        """Apply QSS."""
        theme = cfg.themeMode.value
        if theme == Theme.AUTO:
            theme_name = "dark" if darkdetect.isDark() else "light"
        else:
            theme_name = theme.value.lower()

        qss_path = (
            Path(__file__).parent.parent
            / "resource"
            / "qss"
            / theme_name
            / "layer_panel.qss"
        )
        if qss_path.exists():
            with open(qss_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
