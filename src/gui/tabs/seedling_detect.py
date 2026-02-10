"""Seedling detection tab with Fluent SegmentedWidget top tabs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    Action,
    BodyLabel,
    CommandBar,
    DoubleSpinBox,
    FluentIcon as FIF,
    InfoBar,
    LineEdit,
    SegmentedWidget,
    PrimaryPushButton,
    PushButton,
    SpinBox,
    qrouter,
)

from src.gui.components.base_interface import TabInterface
from src.gui.config import cfg, tr


def seedling_top_tab_keys() -> tuple[str, ...]:
    """Return ordered i18n keys for seedling top tabs."""
    return (
        "page.seedling.tab.file",
        "page.seedling.tab.sam3_params",
        "page.seedling.tab.sam3_preview",
        "page.seedling.tab.slice_infer",
        "page.seedling.tab.points",
    )


class SeedlingTab(TabInterface):
    """Main interface for SAM3-based seedling detection workflow."""

    sigLoadDom = Signal(str)
    sigPreviewDetect = Signal()
    sigFullDetect = Signal()
    sigSaveCache = Signal()
    sigLoadCache = Signal()
    sigSavePoints = Signal()
    sigPreviewModeToggled = Signal(bool)
    sigPreviewSizeRequested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dom_path: str = ""
        self._init_controls()
        self._connect_preview_interaction()
        self._apply_weight_availability()
        cfg.sam3WeightPath.valueChanged.connect(
            lambda _: self._apply_weight_availability()
        )

    def _connect_preview_interaction(self) -> None:
        """Connect preview controls with map canvas interactions."""
        map_canvas = self.map_component.map_canvas
        self.sigPreviewModeToggled.connect(map_canvas.set_preview_mode_enabled)
        self.sigPreviewSizeRequested.connect(map_canvas.set_preview_box_size)
        map_canvas.sigPreviewSizeChanged.connect(self.sync_preview_size)
        map_canvas.sigPreviewBoxLocked.connect(self._on_preview_locked)
        map_canvas.set_preview_box_size(self.spin_preview_size.value())

    @Slot(float, float, float, float)
    def _on_preview_locked(
        self,
        x_min: float,
        y_min: float,
        x_max: float,
        y_max: float,
    ) -> None:
        """Show short status when preview area is locked."""
        _ = (x_min, y_min, x_max, y_max)
        InfoBar.success(
            title=tr("success"),
            content=tr("page.seedling.msg.preview_locked"),
            parent=self,
            duration=1500,
        )

    def _init_controls(self) -> None:
        """Initialize Fluent tab controls."""
        top_tabs_widget = self._build_top_tabs()
        top_tabs_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        self._tool_layout.addWidget(top_tabs_widget, 1)
        self.property_panel.set_current_tab(1)

    def _build_top_tabs(self) -> QWidget:
        """Build top tab (SegmentedWidget | Pivot) and stacked content container."""
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)

        self.nav = SegmentedWidget(self)  # change to Pivot() if necessary
        self.stacked_widget = QStackedWidget(self)
        tab_definitions = [
            ("seedlingFileTab", self._build_file_tab(), seedling_top_tab_keys()[0]),
            (
                "seedlingSam3ParamsTab",
                self._build_sam3_params_tab(),
                seedling_top_tab_keys()[1],
            ),
            (
                "seedlingSam3PreviewTab",
                self._build_sam3_preview_tab(),
                seedling_top_tab_keys()[2],
            ),
            (
                "seedlingSliceInferTab",
                self._build_slice_infer_tab(),
                seedling_top_tab_keys()[3],
            ),
            (
                "seedlingPointsTab",
                self._build_points_tab(),
                seedling_top_tab_keys()[4],
            ),
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

    def _build_file_tab(self) -> QWidget:
        """Build file tab command bar."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        self.btn_load_dom = PushButton(tr("page.seedling.btn.load_dom"))
        self.btn_load_dom.clicked.connect(self._on_load_dom)
        self.label_dom = BodyLabel(tr("page.seedling.label.no_dom"))
        self.label_dom.setMinimumWidth(280)

        bar.addAction(Action(FIF.ROBOT, tr("page.seedling.group.sam")))
        bar.addSeparator()
        bar.addWidget(self.btn_load_dom)
        bar.addSeparator()
        bar.addWidget(self.label_dom)
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _new_command_bar(self) -> CommandBar:
        """Create command bar with fluent display style."""
        bar = CommandBar(self)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return bar

    def _bar_spacer(self) -> QWidget:
        """Create expanding spacer widget for command bars."""
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return spacer

    def _build_labeled_spin(self, label_key: str, widget: QWidget) -> QWidget:
        """Wrap one label-control pair in horizontal layout."""
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(BodyLabel(tr(label_key)))
        layout.addWidget(widget)
        return wrapper

    def _build_sam3_params_tab(self) -> QWidget:
        """Build SAM3 parameter tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        bar.addWidget(self._build_model_section())
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _build_sam3_preview_tab(self) -> QWidget:
        """Build SAM3 preview inference tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        bar.addWidget(self._build_preview_section())
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _build_slice_infer_tab(self) -> QWidget:
        """Build slice inference tab with cache actions."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()
        bar.addWidget(self._build_execute_section())
        bar.addSeparator()
        bar.addWidget(self._build_cache_section())
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _build_points_tab(self) -> QWidget:
        """Build point tab with command bar sections."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()

        self.btn_view = PushButton(tr("page.seedling.btn.view"))
        self.btn_view.setCheckable(True)
        self.btn_view.setChecked(True)
        bar.addWidget(self.btn_view)

        self.btn_add = PushButton(tr("page.seedling.btn.add"))
        self.btn_add.setCheckable(True)
        bar.addWidget(self.btn_add)

        self.btn_move = PushButton(tr("page.seedling.btn.move"))
        self.btn_move.setCheckable(True)
        bar.addWidget(self.btn_move)

        self.btn_delete = PushButton(tr("page.seedling.btn.delete"))
        self.btn_delete.setCheckable(True)
        bar.addWidget(self.btn_delete)

        bar.addSeparator()

        self.btn_undo = PushButton(tr("page.seedling.btn.undo"))
        bar.addWidget(self.btn_undo)

        bar.addSeparator()

        self.btn_save_points = PrimaryPushButton(tr("page.common.save"))
        self.btn_save_points.clicked.connect(self.sigSavePoints.emit)
        bar.addWidget(self.btn_save_points)
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _build_model_section(self) -> QWidget:
        """Build model parameter section widget."""
        self.edit_prompt = LineEdit()
        self.edit_prompt.setText("plants")
        self.spin_conf = DoubleSpinBox()
        self.spin_conf.setRange(0.01, 1.0)
        self.spin_conf.setValue(0.5)
        self.spin_conf.setSingleStep(0.05)
        self.spin_iou = DoubleSpinBox()
        self.spin_iou.setRange(0.01, 0.95)
        self.spin_iou.setValue(0.4)
        self.spin_iou.setSingleStep(0.05)
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(
            self._build_labeled_spin("page.seedling.label.prompt", self.edit_prompt)
        )
        layout.addWidget(
            self._build_labeled_spin("prop.label.confidence", self.spin_conf)
        )
        layout.addWidget(self._build_labeled_spin("prop.label.nms_iou", self.spin_iou))
        return wrapper

    def _build_preview_section(self) -> QWidget:
        """Build preview region section widget."""
        self.spin_preview_size = SpinBox()
        self.spin_preview_size.setRange(128, 2048)
        self.spin_preview_size.setValue(640)
        self.spin_preview_size.setSingleStep(32)
        self.btn_pick_preview = PushButton(tr("page.seedling.btn.pick_preview"))
        self.btn_pick_preview.setCheckable(True)
        self.btn_pick_preview.toggled.connect(self._on_pick_preview_toggled)
        self.btn_preview_detect = PrimaryPushButton(
            tr("page.seedling.btn.preview_detect")
        )
        self.btn_preview_detect.clicked.connect(self.sigPreviewDetect.emit)
        self.spin_preview_size.valueChanged.connect(self.sigPreviewSizeRequested.emit)
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(
            self._build_labeled_spin(
                "page.seedling.label.preview_size", self.spin_preview_size
            )
        )
        layout.addWidget(self.btn_pick_preview)
        layout.addWidget(self.btn_preview_detect)
        return wrapper

    @Slot(int)
    def sync_preview_size(self, size: int) -> None:
        """Sync preview size from canvas shortcut events."""
        if self.spin_preview_size.value() == size:
            return
        self.spin_preview_size.blockSignals(True)
        self.spin_preview_size.setValue(size)
        self.spin_preview_size.blockSignals(False)
        self.sigPreviewSizeRequested.emit(size)

    @Slot(bool)
    def _on_pick_preview_toggled(self, checked: bool) -> None:
        """Update pick-preview button visual state and emit mode signal."""
        if checked:
            self.btn_pick_preview.setText(tr("page.seedling.btn.pick_preview_stop"))
        else:
            self.btn_pick_preview.setText(tr("page.seedling.btn.pick_preview"))
        self.sigPreviewModeToggled.emit(checked)

    def _build_execute_section(self) -> QWidget:
        """Build full-image slicing section widget."""
        self.spin_slice_size = SpinBox()
        self.spin_slice_size.setRange(256, 2048)
        self.spin_slice_size.setValue(640)
        self.spin_slice_size.setSingleStep(64)
        self.spin_overlap = DoubleSpinBox()
        self.spin_overlap.setRange(0.0, 0.8)
        self.spin_overlap.setValue(0.2)
        self.spin_overlap.setSingleStep(0.05)
        self.btn_full_detect = PrimaryPushButton(tr("page.seedling.btn.detect"))
        self.btn_full_detect.clicked.connect(self.sigFullDetect.emit)
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(
            self._build_labeled_spin("page.seedling.label.size", self.spin_slice_size)
        )
        layout.addWidget(
            self._build_labeled_spin("page.seedling.label.overlap", self.spin_overlap)
        )
        layout.addWidget(self.btn_full_detect)
        return wrapper

    def _build_cache_section(self) -> QWidget:
        """Build save/load cache section widget."""
        self.btn_save_cache = PushButton(tr("page.seedling.btn.save_cache"))
        self.btn_save_cache.clicked.connect(self.sigSaveCache.emit)
        self.btn_load_cache = PushButton(tr("page.seedling.btn.load_cache"))
        self.btn_load_cache.clicked.connect(self.sigLoadCache.emit)
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.addWidget(self.btn_save_cache)
        layout.addWidget(self.btn_load_cache)
        return wrapper

    @Slot()
    def _on_load_dom(self) -> None:
        """Open DOM selector and emit selected path."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("page.seedling.dialog.load_dom"),
            "",
            "GeoTIFF (*.tif *.tiff);;All Files (*)",
        )
        if not file_path:
            return
        self._dom_path = file_path
        self.label_dom.setText(Path(file_path).name)
        self._load_dom_to_canvas(file_path)
        self.sigLoadDom.emit(file_path)

    def _load_dom_to_canvas(self, file_path: str) -> None:
        """Load selected DOM into map canvas and update user feedback."""
        map_canvas = self.map_component.map_canvas
        is_ok = map_canvas.add_raster_layer(file_path)
        if not is_ok:
            InfoBar.error(
                title=tr("error"),
                content=f"Failed to load DOM: {Path(file_path).name}",
                parent=self,
                duration=3500,
            )
            return
        map_canvas.zoom_to_layer(Path(file_path).stem)
        InfoBar.success(
            title=tr("success"),
            content=f"Loaded DOM: {Path(file_path).name}",
            parent=self,
            duration=1800,
        )

    def _apply_weight_availability(self) -> None:
        """Enable or disable SAM3 controls by weight availability."""
        weight_path = (
            Path(cfg.sam3WeightPath.value) if cfg.sam3WeightPath.value else None
        )
        is_ready = bool(weight_path and weight_path.exists())
        for button in [
            self.btn_pick_preview,
            self.btn_preview_detect,
            self.btn_full_detect,
            self.btn_save_cache,
            self.btn_load_cache,
        ]:
            button.setEnabled(is_ready)
        if is_ready:
            return
        InfoBar.warning(
            title=tr("warning"),
            content=tr("page.seedling.msg.weight_unavailable"),
            parent=self,
            duration=4000,
        )
