"""Subplot generation tab based on EasyIDP."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import QFileDialog, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QSizePolicy
from qfluentwidgets import (
    CheckBox, InfoBar, PushButton, PrimaryPushButton, 
    SegmentedWidget, CommandBar, ComboBox, SpinBox, DoubleSpinBox, 
    LineEdit, BodyLabel
)

from src.gui.components.base_interface import PageGroup, TabInterface
from src.gui.config import tr
from src.utils.subplot_generate.io import (
    calculate_optimal_rotation,
    generate_and_save,
    generate_subplots_roi,
    load_boundary_roi,
)


class AdaptiveStackedWidget(QStackedWidget):
    """QStackedWidget that adjusts its size to the current page."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)

    def sizeHint(self):
        current = self.currentWidget()
        if current:
            return current.sizeHint()
        return super().sizeHint()

    def minimumSizeHint(self):
        current = self.currentWidget()
        if current:
            return current.minimumSizeHint()
        return super().minimumSizeHint()

    def setCurrentIndex(self, index):
        super().setCurrentIndex(index)
        self.updateGeometry()

    def setCurrentWidget(self, widget):
        super().setCurrentWidget(widget)
        self.updateGeometry()

class SubplotTab(TabInterface):
    """UI workflow for subplot generation using EasyIDP."""

    sigLoadImage = Signal()
    sigLoadBoundary = Signal()
    sigPreview = Signal()
    sigGenerate = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.boundary_roi = None
        self.last_preview_roi = None
        self._init_ui()

    def _init_layout(self) -> None:
        """Initialize layout and map signal forwarding."""
        super()._init_layout()
        self.map_component.map_canvas.sigRotationChanged.connect(
            self._on_canvas_rotation_changed
        )

    def _init_ui(self) -> None:
        """Initialize tab controls."""
        # Top Bar Container
        top_tabs_widget = self._build_top_tabs()
        top_tabs_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        
        # Add to main layout (TabInterface usually has _tool_layout or similar)
        # TabInterface doesn't expose _tool_layout directly in __init__ but BaseInterface does.
        # We need to add it to the top toolbar area.
        if hasattr(self, "_tool_layout"):
             self._tool_layout.addWidget(top_tabs_widget, 1)
        else:
            # Fallback
            layout = QVBoxLayout(self)
            layout.addWidget(top_tabs_widget)
            
        # self.add_stretch() # Not needed if using top bar layout

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
        
        # Tab Definitions
        self.tab_file = self._build_file_tab()
        self.tab_layout = self._build_layout_tab()
        self.tab_numbering = self._build_numbering_tab()
        
        tabs = [
            ("subplotFileTab", self.tab_file, "File"),
            ("subplotLayoutTab", self.tab_layout, "Layout"),
            ("subplotNumberingTab", self.tab_numbering, "Numbering")
        ]
        
        for route_key, widget, text in tabs:
            widget.setObjectName(route_key)
            self.stacked_widget.addWidget(widget)
            self.nav.addItem(
                routeKey=route_key,
                text=text,
                onClick=lambda checked=False, w=widget: self.stacked_widget.setCurrentWidget(w)
            )

        self.stacked_widget.currentChanged.connect(self._on_tab_changed)
        self.stacked_widget.setCurrentWidget(self.tab_file)
        self.nav.setCurrentItem(self.tab_file.objectName())
        
        self.nav.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.nav)
        layout.addWidget(self.stacked_widget)
        return container

    def _on_tab_changed(self, index: int) -> None:
        """Sync top tab selection."""
        widget = self.stacked_widget.widget(index)
        if widget:
            self.nav.setCurrentItem(widget.objectName())

    def _new_command_bar(self) -> CommandBar:
        bar = CommandBar(self)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return bar
        
    def _bar_spacer(self) -> QWidget:
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return spacer

    def _build_labeled_widget(self, label: str, widget: QWidget) -> QWidget:
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(BodyLabel(label))
        layout.addWidget(widget)
        return wrapper

    # --- Tab Builders ---

    def _build_file_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        
        self.btn_load_image = PushButton(tr("page.subplot.btn.load_image"))
        self.btn_load_image.clicked.connect(self._on_load_image)

        self.btn_load_boundary = PushButton(tr("page.subplot.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self._on_load_boundary)

        self.btn_focus = PushButton(tr("page.subplot.btn.focus"))
        self.btn_focus.clicked.connect(self._on_focus)

        self.btn_generate = PrimaryPushButton(tr("page.subplot.btn.save"))
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_generate.setEnabled(False)
        
        bar.addWidget(self.btn_load_image)
        bar.addSeparator()
        bar.addWidget(self.btn_load_boundary)
        bar.addWidget(self.btn_focus)
        # bar.addWidget(self._bar_spacer())
        bar.addSeparator()
        bar.addWidget(self.btn_generate)

        layout.addWidget(bar)
        return tab

    def _build_layout_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        
        # Def Mode
        self.combo_def_mode = ComboBox()
        self.combo_def_mode.addItems([tr("page.subplot.combo.rc"), tr("page.subplot.combo.size")])
        self.combo_def_mode.setFixedWidth(140)
        self.combo_def_mode.currentIndexChanged.connect(self._on_def_mode_changed)
        self.combo_def_mode.currentIndexChanged.connect(self._auto_preview)
        
        # Rows/Cols
        self.spin_rows = SpinBox()
        self.spin_rows.setRange(1, 100)
        self.spin_rows.setValue(5)
        self.spin_rows.setFixedWidth(160)
        self.spin_rows.valueChanged.connect(self._auto_preview)
        
        self.spin_cols = SpinBox()
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(5)
        self.spin_cols.setFixedWidth(160)
        self.spin_cols.valueChanged.connect(self._auto_preview)
        
        # Width/Height
        self.spin_width = DoubleSpinBox()
        self.spin_width.setRange(0.1, 1000.0)
        self.spin_width.setValue(2.0)
        # self.spin_width.setSuffix(" m")
        # self.spin_width.setFixedWidth(160)
        self.spin_width.valueChanged.connect(self._auto_preview)
        self.spin_width.hide() # Initial hidden
        
        self.spin_height = DoubleSpinBox()
        self.spin_height.setRange(0.1, 1000.0)
        self.spin_height.setValue(2.0)
        # self.spin_height.setSuffix(" m")
        # self.spin_height.setFixedWidth(160)
        self.spin_height.valueChanged.connect(self._auto_preview)
        self.spin_height.hide() # Initial hidden
        
        # Spacing
        self.spin_x_spacing = DoubleSpinBox()
        self.spin_x_spacing.setRange(-10, 100)
        self.spin_x_spacing.setValue(0.0)
        self.spin_x_spacing.setSuffix(" m")
        self.spin_x_spacing.setFixedWidth(140)
        self.spin_x_spacing.valueChanged.connect(self._auto_preview)
        
        self.spin_y_spacing = DoubleSpinBox()
        self.spin_y_spacing.setRange(-10, 100)
        self.spin_y_spacing.setValue(0.0)
        self.spin_y_spacing.setSuffix(" m")
        self.spin_y_spacing.setFixedWidth(140)
        self.spin_y_spacing.valueChanged.connect(self._auto_preview)
        
        # Keep Mode
        self.combo_keep = ComboBox()
        self.combo_keep.addItems([
            tr("page.subplot.keep.all"),
            tr("page.subplot.keep.touch"),
            tr("page.subplot.keep.inside"),
        ])
        self.combo_keep.currentIndexChanged.connect(self._auto_preview)
        
        # Reset
        self.btn_reset = PushButton(tr("page.subplot.btn.reset"))
        self.btn_reset.clicked.connect(self._on_reset)
        
        # Wrappers
        self.container_rc = QWidget()
        layout_rc = QHBoxLayout(self.container_rc)
        layout_rc.setContentsMargins(0,0,0,0)
        layout_rc.setSpacing(10)
        layout_rc.addWidget(self._build_labeled_widget(tr("page.subplot.label.rows"), self.spin_rows))
        layout_rc.addWidget(self._build_labeled_widget(tr("page.subplot.label.cols"), self.spin_cols))
        
        self.container_size = QWidget()
        layout_size = QHBoxLayout(self.container_size)
        layout_size.setContentsMargins(0,0,0,0)
        layout_size.setSpacing(10)
        layout_size.addWidget(self._build_labeled_widget(tr("page.subplot.label.width_m"), self.spin_width))
        layout_size.addWidget(self._build_labeled_widget(tr("page.subplot.label.height_m"), self.spin_height))

        # Stacked Widget for Mode Switching
        self.stack_layout_mode = AdaptiveStackedWidget()
        self.stack_layout_mode.addWidget(self.container_rc)
        self.stack_layout_mode.addWidget(self.container_size)

        bar.addWidget(self._build_labeled_widget(tr("page.subplot.label.def_mode"), self.combo_def_mode))
        bar.addWidget(self.stack_layout_mode)
        bar.addWidget(self._build_labeled_widget(tr("page.subplot.label.x_space"), self.spin_x_spacing))
        bar.addWidget(self._build_labeled_widget(tr("page.subplot.label.y_space"), self.spin_y_spacing))
        bar.addWidget(self._build_labeled_widget(tr("page.subplot.label.keep"), self.combo_keep))
        bar.addSeparator()
        bar.addWidget(self.btn_reset)
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        
        # Initialize visibility state
        self._on_def_mode_changed(0)
        
        return tab

    def _build_numbering_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        
        self.combo_numbering_mode = ComboBox()
        self.combo_numbering_mode.addItems([
            "行列命名 (R1C1, R1C2...)",
            "连续编号 (1, 2, 3...)",
            "蛇形编号",
            "自定义格式",
        ])
        
        self.spin_start_row = SpinBox()
        self.spin_start_row.setRange(0, 1000)
        self.spin_start_row.setValue(1)
        
        self.spin_start_col = SpinBox()
        self.spin_start_col.setRange(0, 1000)
        self.spin_start_col.setValue(1)
        
        self.edit_prefix = LineEdit()
        self.edit_prefix.setPlaceholderText("例如: Plot_")
        self.edit_prefix.setFixedWidth(100)
        
        self.edit_suffix = LineEdit()
        self.edit_suffix.setPlaceholderText("例如: _2024")
        self.edit_suffix.setFixedWidth(100)
        
        bar.addWidget(self._build_labeled_widget(tr("prop.label.numbering_mode"), self.combo_numbering_mode))
        bar.addWidget(self._build_labeled_widget(tr("prop.label.start_row"), self.spin_start_row))
        bar.addWidget(self._build_labeled_widget(tr("prop.label.start_col"), self.spin_start_col))
        bar.addWidget(self._build_labeled_widget(tr("prop.label.prefix"), self.edit_prefix))
        bar.addWidget(self._build_labeled_widget(tr("prop.label.suffix"), self.edit_suffix))
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab
        
    def _on_def_mode_changed(self, index: int):
        self.stack_layout_mode.setCurrentIndex(index)
        is_rc = (index == 0)
        if is_rc:
            self.spin_width.hide() # Keep spinboxes hidden if needed for logic, but view is handled by stack
            self.spin_height.hide()
            self.spin_rows.show() # Ensure these are shown within the stack page
            self.spin_cols.show()
        else:
            self.spin_width.show()
            self.spin_height.show()
            self.spin_rows.hide()
            self.spin_cols.hide()
            
    def _collect_params(self) -> dict:
        """Collect subplot parameters."""
        keep_values = ("all", "touch", "inside")
        keep_mode = keep_values[self.combo_keep.currentIndex()]
        return {
            "mode_index": self.combo_def_mode.currentIndex(),
            "rows": self.spin_rows.value(),
            "cols": self.spin_cols.value(),
            "width": self.spin_width.value(),
            "height": self.spin_height.value(),
            "x_spacing": self.spin_x_spacing.value(),
            "y_spacing": self.spin_y_spacing.value(),
            "keep_mode": keep_mode,
        }

    def _show_preview(self) -> None:
        """Generate and render preview layer when boundary exists."""
        # Always preview if boundary exists (forced enabled)
        if self.boundary_roi is None:
            return

        params = self._collect_params()
        preview_roi = generate_subplots_roi(self.boundary_roi, **params)
        self.last_preview_roi = preview_roi
        self.map_component.map_canvas.add_vector_layer(
            preview_roi,
            "Preview",
            color="#00FF00",
            width=1,
        )
        self.btn_generate.setEnabled(True)

    @Slot(float)
    def _on_canvas_rotation_changed(self, angle: float) -> None:
        """Update rotation (no-op or status update)."""
        logger.debug(f"Canvas rotation changed: {angle:.2f} degree")

    @Slot()
    def _on_load_image(self) -> None:
        """Load a raster image as base layer."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("page.subplot.dialog.load_image"),
            "",
            "Image Files (*.tif *.tiff *.png *.jpg);;All Files (*)",
        )
        if not file_path:
            return

        if self.map_component.map_canvas.add_raster_layer(file_path):
            logger.info("Image loaded successfully.")
            InfoBar.success(
                    title=tr("success"),
                    content=f"Loaded: {Path(file_path).name}",
                    parent=self,
                    duration=3000
            )
            # self.map_component.status_bar.set_status('success', f"DOM loaded: {Path(file_path).name}")
            if self.boundary_roi is None:
                self.map_component.map_canvas.zoom_to_layer(Path(file_path).stem)
            return


        logger.error(f"Failed to load image: {file_path}")
        InfoBar.error(
            title=tr("error"),
            content=f"Failed to load image: {file_path}",
            parent=self
        )

    @Slot()
    def _on_load_boundary(self) -> None:
        """Load boundary shapefile into ROI model."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("page.subplot.dialog.load_boundary"),
            "",
            "Shapefile (*.shp);;All Files (*)",
        )
        if not file_path:
            return

        try:
            self.boundary_roi = load_boundary_roi(file_path)
            self.map_component.map_canvas.add_vector_layer(
                self.boundary_roi,
                "Boundary",
                color="#FF0000",
                width=2,
            )
            self._auto_preview()
            logger.info("Boundary loaded successfully.")
            InfoBar.success(
                    title=tr("success"),
                    content=tr("page.subplot.msg.boundary_loaded"),
                    parent=self,
                    duration=3000
            )
            # self.map_component.status_bar.set_status('success', tr("page.subplot.msg.boundary_loaded"))
        except Exception as exc:  # pragma: no cover - UI feedback branch
            logger.exception("Failed to load boundary")
            InfoBar.error(
                    title=tr("error"),
                    content=tr("page.subplot.error.invalid_boundary"),
                    parent=self
                )
            # self.map_component.status_bar.set_status('error', f"IO error")

    @Slot()
    def _auto_preview(self) -> None:
        """Trigger preview refresh."""
        if self.boundary_roi is None:
            return

        try:
            self._show_preview()
        except Exception as exc:  # pragma: no cover - UI feedback branch
            self.btn_generate.setEnabled(False)
            logger.debug(f"Preview error: {exc}")

    @Slot()
    def _on_focus(self) -> None:
        """Focus on the boundary layer."""
        if self.boundary_roi is not None:
            # Focus logic here (usually handled by map_component)
            self.map_component.map_canvas.zoom_to_layer("Boundary")

            # Auto-rotate
            angle = calculate_optimal_rotation(self.boundary_roi)
            if angle is not None:
                self.map_component.map_canvas.set_rotation(angle)
            else:
                self.map_component.map_canvas.set_rotation(0)

    @Slot()
    def _on_generate(self) -> None:
        """Generate subplots and save as shapefile."""
        if self.boundary_roi is None:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.subplot.msg.no_boundary"),
                parent=self
            )
            # self.map_component.status_bar.set_status('warning', tr("page.subplot.warning.no_boundary"))
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("page.subplot.dialog.save"),
            "",
            "Shapefile (*.shp)",
        )
        if not file_path:
            return

        self.map_component.status_bar.set_progress(None) # Busy
        # self.map_component.status_bar.set_status('info', "Generating...")
        
        try:
            params = self._collect_params()
            generate_and_save(self.boundary_roi, output_path=file_path, **params)
            InfoBar.success(
                title=tr("success"),
                content=tr("page.subplot.msg.success"),
                parent=self
            )
            self.map_component.status_bar.set_status('success', tr("success"))
        except Exception as exc:  # pragma: no cover - UI feedback branch
            logger.exception("Subplot save failed")
            InfoBar.error(
                title=tr("error"),
                content=f"Generation failed: {exc}",
                parent=self
            )
            # self.map_component.status_bar.set_status('error', f"Generation failed: {exc}")
        # finally:
        #     self.map_component.status_bar.set_progress(100)
            # Or hide after delay?
            # self.map_component.status_bar.set_progress(-1) 

    @Slot()
    def _on_reset(self) -> None:
        """Reset params."""
        logger.debug("Subplot reset clicked")
        self.spin_rows.setValue(5)
        self.spin_cols.setValue(5)
        self.spin_x_spacing.setValue(0.0)
        self.spin_y_spacing.setValue(0.0)
        self.combo_def_mode.setCurrentIndex(0)

