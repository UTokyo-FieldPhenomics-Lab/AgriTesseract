"""
ID Renaming Page with SegmentedWidget top tabs.
"""

from typing import Optional
from pathlib import Path

from PySide6.QtCore import Qt, Slot, Signal, QTimer
from PySide6.QtWidgets import (
    QWidget, 
    QVBoxLayout, 
    QHBoxLayout, 
    QSizePolicy, 
    QStackedWidget,
    QFileDialog
)
from qfluentwidgets import (
    SegmentedWidget,
    CommandBar,
    PushButton,
    PrimaryPushButton,
    ComboBox,
    SpinBox,
    DoubleSpinBox,
    BodyLabel,
    CheckBox,
    InfoBar,
    qrouter
)

from src.gui.components.base_interface import TabInterface
from src.gui.config import tr


def rename_top_tab_keys() -> tuple[str, ...]:
    """Return ordered i18n keys for rename top tabs."""
    return (
        "page.rename.tab.file",
        "page.rename.tab.ridge",
        "page.rename.tab.ordering",
        "page.rename.tab.numbering",
    )


class RenameTab(TabInterface):
    """
    Interface content for Seedling ID Renaming and Adjustment.
    """

    sigLoadShp = Signal(str)
    sigLoadBoundary = Signal(str)
    sigLoadDom = Signal(list)  # List of file paths
    
    # Signals for parameters (can be connected to backend logic)
    sigRidgeParamsChanged = Signal(dict)
    sigOrderingParamsChanged = Signal(dict)
    sigNumberingParamsChanged = Signal(dict)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # Debounce timer for reactive updates
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(800)  # 800ms delay
        self._update_timer.timeout.connect(self._on_parameter_update_timeout)
        
        # Track which type of parameter changed
        self._pending_update_type: Optional[str] = None
        
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for seedling renaming."""
        top_tabs_widget = self._build_top_tabs()
        top_tabs_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        # Assuming TabInterface has a layout where we can add this. 
        # Checking base_interface might be needed, but usually it has a layout.
        # If standard TabInterface doesn't have a direct layout accessible, 
        # we might need to check how seedling_detect uses it.
        # seedling_detect uses: self._tool_layout.addWidget(top_tabs_widget, 1)
        # But 'rename_ids.py' original code used 'self.add_group'.
        # 'TabInterface' likely inherits from 'GalleryInterface' or has similar structure.
        # Let's assume we can use the same approach as seedling_detect if it inherits correctly.
        # However, checking rename_ids.py original code:
        # class RenameTab(TabInterface): ... super().__init__ ... self.add_group(file_group)
        # It seems TabInterface provides `add_group`. 
        # But here we want to replace the whole content with the top tab structure.
        # We should access the main layout.
        # In seedling_detect: self._tool_layout.addWidget(top_tabs_widget, 1)
        # We will try to use _tool_layout if available, or clear existing layout.
        
        if hasattr(self, "_tool_layout"):
             self._tool_layout.addWidget(top_tabs_widget, 1)
        else:
            # Fallback if _tool_layout is not directly available (though it should be)
            layout = QVBoxLayout(self)
            layout.addWidget(top_tabs_widget)
            
        # We don't use property_panel here based on the requirement to duplicate seedling_detect structure?
        # distinct structure.
        
    def _build_top_tabs(self) -> QWidget:
        """Build top tab (SegmentedWidget) and stacked content container."""
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)

        self.nav = SegmentedWidget(self)
        self.stacked_widget = QStackedWidget(self)
        
        tab_definitions = [
            ("renameFileTab", self._build_file_tab(), rename_top_tab_keys()[0]),
            ("renameRidgeTab", self._build_ridge_tab(), rename_top_tab_keys()[1]),
            ("renameOrderingTab", self._build_ordering_tab(), rename_top_tab_keys()[2]),
            ("renameNumberingTab", self._build_numbering_tab(), rename_top_tab_keys()[3]),
        ]
        
        self.tab_file = tab_definitions[0][1]
        for route_key, widget, text_key in tab_definitions:
            self._add_sub_tab(widget, route_key, tr(text_key))

        self.stacked_widget.currentChanged.connect(self._on_tab_changed)
        self.stacked_widget.setCurrentWidget(self.tab_file)
        self.nav.setCurrentItem(self.tab_file.objectName())
        qrouter.setDefaultRouteKey(self.stacked_widget, self.tab_file.objectName())

        self.nav.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.nav)
        layout.addWidget(self.stacked_widget)
        return container

    def _add_sub_tab(self, widget: QWidget, route_key: str, text: str) -> None:
        """Register one top tab and its stacked page."""
        widget.setObjectName(route_key)
        self.stacked_widget.addWidget(widget)
        self.nav.addItem(
            routeKey=route_key,
            text=text,
            onClick=lambda: self.stacked_widget.setCurrentWidget(widget),
        )

    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        """Sync top tab selection when stacked page changed."""
        widget = self.stacked_widget.widget(index)
        if widget is None:
            return
        self.nav.setCurrentItem(widget.objectName())
        qrouter.push(self.stacked_widget, widget.objectName())

    def _new_command_bar(self) -> CommandBar:
        """Create command bar with display style."""
        bar = CommandBar(self)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return bar

    def _bar_spacer(self) -> QWidget:
        """Create expanding spacer widget for command bars."""
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return spacer

    def _build_labeled_widget(self, label_key: str, widget: QWidget) -> QWidget:
        """Wrap one label-control pair in horizontal layout."""
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(BodyLabel(tr(label_key)))
        layout.addWidget(widget)
        return wrapper

    # --- Tab Builders ---

    def _build_file_tab(self) -> QWidget:
        """Build File tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        
        self.btn_load_shp = PushButton(tr("page.common.load_shp"))
        self.btn_load_shp.clicked.connect(self._on_load_shp)
        
        self.btn_load_boundary = PushButton(tr("page.rename.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self._on_load_boundary)
        
        self.btn_load_dom = PushButton(tr("page.rename.btn.load_dom"))  # New DOM load button
        self.btn_load_dom.clicked.connect(self._on_load_dom)
        
        bar.addWidget(self.btn_load_shp)
        bar.addWidget(self.btn_load_boundary)
        bar.addWidget(self.btn_load_dom)
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _build_ridge_tab(self) -> QWidget:
        """Build Ridge Detection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        
        self.combo_direction = ComboBox()
        self.combo_direction.addItems([
            tr("page.rename.combo.auto"), 
            tr("page.rename.combo.x"), 
            tr("page.rename.combo.y")
        ])
        self.combo_direction.currentIndexChanged.connect(lambda: self._schedule_update("ridge"))
        
        self.spin_strength = SpinBox()
        self.spin_strength.setRange(1, 100)
        self.spin_strength.setValue(10)
        self.spin_strength.valueChanged.connect(lambda: self._schedule_update("ridge"))
        
        self.spin_distance = SpinBox()
        self.spin_distance.setRange(1, 50)
        self.spin_distance.setValue(3)
        self.spin_distance.valueChanged.connect(lambda: self._schedule_update("ridge"))
        
        self.spin_height = SpinBox()
        self.spin_height.setRange(1, 200)
        self.spin_height.setValue(20)
        self.spin_height.valueChanged.connect(lambda: self._schedule_update("ridge"))
        
        bar.addWidget(self._build_labeled_widget("page.rename.label.direction", self.combo_direction))
        bar.addWidget(self._build_labeled_widget("page.rename.label.strength", self.spin_strength))
        bar.addWidget(self._build_labeled_widget("page.rename.label.distance", self.spin_distance))
        bar.addWidget(self._build_labeled_widget("page.rename.label.height", self.spin_height))
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _build_ordering_tab(self) -> QWidget:
        """Build Ordering tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        
        self.spin_buffer = DoubleSpinBox()
        self.spin_buffer.setRange(0.01, 1.0)
        self.spin_buffer.setValue(0.5)
        self.spin_buffer.setSingleStep(0.05)
        self.spin_buffer.valueChanged.connect(lambda: self._schedule_update("ordering"))
        
        self.check_ransac = CheckBox(tr("page.rename.check.ransac"))
        self.check_ransac.stateChanged.connect(lambda: self._schedule_update("ordering"))
        
        self.spin_residual = SpinBox()
        self.spin_residual.setRange(1, 100)
        self.spin_residual.setValue(35)
        self.spin_residual.valueChanged.connect(lambda: self._schedule_update("ordering"))
        
        self.spin_trials = SpinBox()
        self.spin_trials.setRange(100, 10000)
        self.spin_trials.setValue(2000)
        self.spin_trials.valueChanged.connect(lambda: self._schedule_update("ordering"))
        
        bar.addWidget(self._build_labeled_widget("page.rename.label.buffer", self.spin_buffer))
        bar.addWidget(self.check_ransac)
        bar.addWidget(self._build_labeled_widget("page.rename.label.residual", self.spin_residual))
        bar.addWidget(self._build_labeled_widget("page.rename.label.max_trials", self.spin_trials))
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        
        # Link RANSAC enable state to numeric inputs
        self.check_ransac.stateChanged.connect(self._update_ransac_ui_state)
        self._update_ransac_ui_state()
        
        return tab
        
    def _update_ransac_ui_state(self):
        enabled = self.check_ransac.isChecked()
        self.spin_residual.setEnabled(enabled)
        self.spin_trials.setEnabled(enabled)

    def _build_numbering_tab(self) -> QWidget:
        """Build Numbering tab with Edit tools."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        
        # Edit Tools (Moved from Seedling Detect)
        self.btn_view = PushButton(tr("page.rename.btn.view"))
        self.btn_view.setCheckable(True)
        self.btn_view.setChecked(True)
        
        self.btn_add = PushButton(tr("page.rename.btn.add"))
        self.btn_add.setCheckable(True)
        
        self.btn_move = PushButton(tr("page.rename.btn.move"))
        self.btn_move.setCheckable(True)
        
        self.btn_delete = PushButton(tr("page.rename.btn.delete"))
        self.btn_delete.setCheckable(True)
        
        self.btn_undo = PushButton(tr("page.rename.btn.undo"))
        
        bar.addWidget(self.btn_view)
        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_move)
        bar.addWidget(self.btn_delete)
        bar.addSeparator()
        bar.addWidget(self.btn_undo)
        bar.addSeparator()

        # Numbering Tools
        self.combo_format = ComboBox()
        self.combo_format.addItems([
            tr("page.rename.combo.rc_plant"),
            tr("page.rename.combo.numeric"),
            tr("page.rename.combo.custom")
        ])
        self.combo_format.currentIndexChanged.connect(lambda: self._schedule_update("numbering"))
        
        bar.addWidget(self._build_labeled_widget("page.rename.label.format", self.combo_format))
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    # --- Event Handlers ---

    def _on_load_shp(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("page.common.load_shp"), "", "Shapefile (*.shp)"
        )
        if file_path:
            self.sigLoadShp.emit(file_path)

    def _on_load_boundary(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("page.rename.btn.load_boundary"), "", "Shapefile (*.shp)"
        )
        if file_path:
            self.sigLoadBoundary.emit(file_path)

    def _on_load_dom(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, tr("page.rename.btn.load_dom"), "", "GeoTIFF (*.tif *.tiff)"
        )
        if file_paths:
            self.sigLoadDom.emit(file_paths)

    def _schedule_update(self, update_type: str):
        """Schedule a delayed update to avoid spamming calculations."""
        self._pending_update_type = update_type
        self._update_timer.start()

    def _on_parameter_update_timeout(self):
        """Timer finished, emit the update signal."""
        if not self._pending_update_type:
            return
            
        if self._pending_update_type == "ridge":
            params = {
                "direction_index": self.combo_direction.currentIndex(),
                "strength": self.spin_strength.value(),
                "distance": self.spin_distance.value(),
                "height": self.spin_height.value(),
            }
            self.sigRidgeParamsChanged.emit(params)
            
        elif self._pending_update_type == "ordering":
            params = {
                "buffer": self.spin_buffer.value(),
                "ransac_enabled": self.check_ransac.isChecked(),
                "residual": self.spin_residual.value(),
                "max_trials": self.spin_trials.value(),
            }
            self.sigOrderingParamsChanged.emit(params)
            
        elif self._pending_update_type == "numbering":
            params = {
                "format_index": self.combo_format.currentIndex()
            }
            self.sigNumberingParamsChanged.emit(params)
            
        self._pending_update_type = None

