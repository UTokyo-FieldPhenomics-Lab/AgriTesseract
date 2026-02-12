"""Seedling detection tab with Fluent SegmentedWidget top tabs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from loguru import logger

from PySide6.QtCore import QThread, Qt, Signal, Slot
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
    StateToolTip,
    qrouter,
)

from src.gui.components.base_interface import TabInterface
from src.gui.config import cfg, tr
from src.utils.subplot_generate.io import load_boundary_roi
from src.utils.seedling_detect.qthread import (
    PreviewInferenceInput,
    SeedlingPreviewWorker,
)
from src.utils.seedling_detect.preview_controller import SeedlingPreviewController


def seedling_top_tab_keys() -> tuple[str, ...]:
    """Return ordered i18n keys for seedling top tabs."""
    return (
        "page.seedling.tab.file",
        "page.seedling.tab.sam3_params",
        "page.seedling.tab.sam3_preview",
        "page.seedling.tab.slice_infer",
        "page.seedling.tab.slice_infer",
    )


class SeedlingTab(TabInterface):
    """Main interface for SAM3-based seedling detection workflow."""

    sigLoadDom = Signal(str)
    sigPreviewDetect = Signal()
    sigFullInference = Signal()
    sigSaveCache = Signal()
    sigLoadCache = Signal()
    sigSavePoints = Signal()
    sigPreviewModeToggled = Signal(bool)
    sigPreviewSizeRequested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dom_path: str = ""
        self._boundary_roi = None
        self._boundary_file_path: str = ""
        self._preview_thread: Optional[QThread] = None
        self._preview_worker: Optional[SeedlingPreviewWorker] = None
        self.stateTooltip: Optional[StateToolTip] = None
        self._init_controls()
        self._connect_preview_interaction()
        self._update_button_states()
        cfg.sam3WeightPath.valueChanged.connect(lambda _: self._update_button_states())

    def _connect_preview_interaction(self) -> None:
        """Connect preview controls with map canvas interactions."""
        map_canvas = self.map_component.map_canvas
        self._preview_ctrl = SeedlingPreviewController(map_canvas)
        map_canvas._key_handlers.append(self._preview_ctrl.handle_key_press)
        map_canvas._hover_handlers.append(self._preview_ctrl.handle_coordinate_hover)
        map_canvas._click_handlers.append(self._preview_ctrl.handle_click)
        self.sigPreviewModeToggled.connect(self._preview_ctrl.set_preview_mode_enabled)
        self.spin_preview_size.valueChanged.connect(
            self._preview_ctrl.set_preview_box_size
        )
        self.spin_preview_size.valueChanged.connect(self._sync_slice_size)
        self._preview_ctrl.sigPreviewSizeChanged.connect(self.sync_preview_size)
        self._preview_ctrl.sigPreviewBoxLocked.connect(self._on_preview_locked)
        self._preview_ctrl.sigRequestPreviewModeStop.connect(
            self._on_request_stop_preview
        )
        self._preview_ctrl.set_preview_box_size(self.spin_preview_size.value())

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

    @Slot()
    def _on_request_stop_preview(self) -> None:
        """Handle request to stop preview mode (e.g. via Escape key)."""
        self.btn_pick_preview.setChecked(False)

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

        # Toggle preview layers visibility: only visible in Preview tab
        is_preview_tab = widget.objectName() == "seedlingSam3PreviewTab"
        self._preview_ctrl.set_preview_layers_visibility(is_preview_tab)

        # Toggle slice grid visibility: only visible in Slice Inference tab
        is_slice_tab = widget.objectName() == "seedlingSliceInferTab"
        self._preview_ctrl.set_slice_grid_visibility(is_slice_tab)

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

        # bar.addAction(Action(FIF.ROBOT, tr("page.seedling.group.sam")))
        # bar.addSeparator()
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
        self.btn_load_boundary = PushButton(tr("page.seedling.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self._on_load_boundary)
        self.label_boundary = BodyLabel(tr("page.seedling.label.no_boundary"))
        self.label_boundary.setMinimumWidth(220)
        bar.addWidget(self.btn_load_boundary)
        bar.addWidget(self.label_boundary)
        bar.addSeparator()
        bar.addWidget(self._build_execute_section())
        bar.addSeparator()

        self.btn_save_shp = PrimaryPushButton(tr("page.seedling.btn.save_shp"))
        self.btn_save_shp.clicked.connect(self.sigSavePoints.emit)

        bar.addWidget(self.btn_save_shp)
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
        self.btn_preview_detect.clicked.connect(self._on_preview_inference_clicked)
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

    @Slot(int)
    def _sync_slice_size(self, size: int) -> None:
        """One-way sync: Preview Size -> Slice Size."""
        if self.spin_slice_size.value() != size:
            self.spin_slice_size.setValue(size)

    @Slot(bool)
    def _on_pick_preview_toggled(self, checked: bool) -> None:
        """Update pick-preview button visual state and emit mode signal."""
        if checked:
            self.btn_pick_preview.setText(tr("page.seedling.btn.pick_preview_stop"))
            self.map_component.map_canvas.setFocus()
        else:
            self.btn_pick_preview.setText(tr("page.seedling.btn.pick_preview"))
            self._preview_ctrl.clear_preview_result_layer()
        self.sigPreviewModeToggled.emit(checked)

    @Slot(bool)
    def _on_slice_preview_toggled(self, checked: bool) -> None:
        """Handle slice preview toggle."""
        if checked:
            self.btn_slice_preview.setText(tr("page.seedling.btn.slice_preview_stop"))
            size = self.spin_slice_size.value()
            overlap = self.spin_overlap.value()
            boundary_xy = self._get_boundary_xy()
            boundary_mode = self._slice_boundary_mode()
            self._preview_ctrl.show_slice_grid(
                size,
                overlap,
                boundary_xy=boundary_xy,
                boundary_mode=boundary_mode,
            )
        else:
            self.btn_slice_preview.setText(tr("page.seedling.btn.slice_preview"))
            self._preview_ctrl.clear_slice_grid_layer()

    def _get_boundary_xy(self) -> Optional[list[list[float]]]:
        """Return boundary coordinates from loaded ROI for filtering."""
        if self._boundary_roi is None:
            return None
        if len(self._boundary_roi) != 1:
            return None
        coords = next(iter(self._boundary_roi.values()))
        return coords[:, :2].tolist()

    def _slice_boundary_mode(self) -> str:
        """Return boundary mode for slice filtering."""
        if self._boundary_roi is None:
            return "all"
        return "intersect"

    @Slot()
    def _on_load_boundary(self) -> None:
        """Load boundary shapefile for slice filtering."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            tr("page.seedling.dialog.load_boundary"),
            "",
            "Shapefile (*.shp);;All Files (*)",
        )
        if not file_path:
            return
        try:
            self._boundary_roi = load_boundary_roi(file_path)
        except Exception as exc:
            logger.exception("Failed to load seedling boundary")
            InfoBar.error(
                title=tr("error"),
                content=f"{tr('page.seedling.msg.boundary_invalid')}: {exc}",
                parent=self,
                duration=3500,
            )
            return
        self._boundary_file_path = file_path
        self.label_boundary.setText(Path(file_path).name)
        self.map_component.map_canvas.add_vector_layer(
            self._boundary_roi,
            "Boundary",
            color="#FF0000",
            width=2,
        )
        InfoBar.success(
            title=tr("success"),
            content=tr("page.seedling.msg.boundary_loaded"),
            parent=self,
            duration=1800,
        )

    @Slot()
    def _on_preview_inference_clicked(self) -> None:
        """Start or stop preview inference thread."""
        if self._preview_thread is not None:
            self._stop_preview_inference()
            return
        self._start_preview_inference()

    def _start_preview_inference(self) -> None:
        """Start preview inference in a background thread."""
        bounds_geo = self._preview_ctrl.get_locked_preview_bounds()
        if bounds_geo is None:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.seedling.msg.pick_preview_first"),
                parent=self,
                duration=2500,
            )
            return
        patch_data = self._preview_ctrl.read_preview_patch(bounds_geo)
        if patch_data is None:
            InfoBar.error(
                title=tr("error"),
                content=tr("page.seedling.msg.preview_patch_failed"),
                parent=self,
                duration=3000,
            )
            return
        payload = PreviewInferenceInput(
            image_rgb=patch_data["image"],
            transform=patch_data["transform"],
            weight_path=str(cfg.sam3WeightPath.value),
            prompt=self.edit_prompt.text().strip() or "plants",
            conf=float(self.spin_conf.value()),
            iou=float(self.spin_iou.value()),
            cache_dir=self._preview_cache_dir(),
        )
        self._preview_thread = QThread(self)
        self._preview_worker = SeedlingPreviewWorker(payload)
        self._preview_worker.moveToThread(self._preview_thread)
        self._preview_thread.started.connect(self._preview_worker.run)
        self._preview_worker.sigFinished.connect(self._on_preview_inference_finished)
        self._preview_worker.sigFailed.connect(self._on_preview_inference_failed)
        self._preview_worker.sigCancelled.connect(self._on_preview_inference_cancelled)
        self._preview_thread.start()
        self._set_preview_running_ui(True)

    def _preview_cache_dir(self) -> str:
        """Return app-level preview cache directory for Ultralytics outputs."""
        if cfg.modelDir.value:
            return str(Path(cfg.modelDir.value) / "app" / "cache")
        return str(Path.cwd() / "app" / "cache")

    def _stop_preview_inference(self) -> None:
        """Request cancellation for running preview inference."""
        if self._preview_worker is None:
            return
        self._preview_worker.request_cancel()
        InfoBar.info(
            title=tr("info"),
            content=tr("page.seedling.msg.preview_stopping"),
            parent=self,
            duration=2000,
        )

    def _teardown_preview_thread(self) -> None:
        """Disconnect and cleanup preview inference thread."""
        if self._preview_thread is None:
            return
        self._preview_thread.quit()
        self._preview_thread.wait(1000)
        self._preview_thread.deleteLater()
        self._preview_thread = None
        self._preview_worker = None
        self._set_preview_running_ui(False)

    def _set_preview_running_ui(self, running: bool) -> None:
        """Update preview-run button text and status bar notification."""
        if running:
            self.btn_preview_detect.setText(tr("page.seedling.btn.stop_inference"))
            if self.stateTooltip:
                self.stateTooltip.setState(True)
                self.stateTooltip = None

            self.stateTooltip = StateToolTip(
                tr("info"),
                tr("page.seedling.msg.preview_running"),
                self.window(),
            )
            # Position the tooltip nicely
            self.stateTooltip.move(self.stateTooltip.getSuitablePos())
            self.stateTooltip.show()
            self.map_component.status_bar.set_progress(None)
            return

        if self.stateTooltip:
            # If not None here, it means it wasn't handled by finished (so failed or cancelled)
            self.stateTooltip.close()
            self.stateTooltip = None

        self.btn_preview_detect.setText(tr("page.seedling.btn.preview_detect"))
        self.map_component.status_bar.set_progress(-1)
        # self.map_component.status_bar.set_status("success", "Inf finished")

    @Slot(list, list)
    def _on_preview_inference_finished(
        self,
        polygons_geo: list,
        _scores: list,
    ) -> None:
        """Render preview inference result polygons."""
        self._preview_ctrl.show_preview_result_polygons(polygons_geo)

        if self.stateTooltip:
            self.stateTooltip.setContent(
                tr("page.seedling.msg.preview_finished") + " 😆"
            )
            self.stateTooltip.setState(True)
            self.stateTooltip = None

        # InfoBar.success(
        #     title=tr("success"),
        #     content=tr("page.seedling.msg.preview_finished"),
        #     parent=self,
        #     duration=2000,
        # )
        self._teardown_preview_thread()

    @Slot(str)
    def _on_preview_inference_failed(self, message: str) -> None:
        """Handle preview inference failure message."""
        logger.error("Preview inference failed:\n{}", message)
        short_message = message.splitlines()[0] if message else tr("error")
        InfoBar.error(
            title=tr("error"),
            content=f"{short_message} (details in log)",
            parent=self,
            duration=12000,
        )
        if self.stateTooltip:
            # If not None here, it means it wasn't handled by finished (so failed or cancelled)
            self.stateTooltip.close()
            self.stateTooltip = None
        self._teardown_preview_thread()

    @Slot()
    def _on_preview_inference_cancelled(self) -> None:
        """Handle preview inference cancellation."""
        InfoBar.warning(
            title=tr("warning"),
            content=tr("page.seedling.msg.preview_cancelled"),
            parent=self,
            duration=1800,
        )
        self._teardown_preview_thread()

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

        self.btn_start_inference = PrimaryPushButton(
            tr("page.seedling.btn.start_inference")
        )
        self.btn_start_inference.clicked.connect(self.sigFullInference.emit)
        self.btn_start_inference.setEnabled(False)

        self.btn_slice_preview = PushButton(tr("page.seedling.btn.slice_preview"))
        self.btn_slice_preview.setCheckable(True)
        self.btn_slice_preview.toggled.connect(self._on_slice_preview_toggled)

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
        layout.addWidget(self.btn_slice_preview)
        layout.addWidget(self.btn_start_inference)
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

        # DOM loaded successfully
        self._update_button_states()

        map_canvas.zoom_to_layer(Path(file_path).stem)
        InfoBar.success(
            title=tr("success"),
            content=f"Loaded DOM: {Path(file_path).name}",
            parent=self,
            duration=1800,
        )

    def _update_button_states(self) -> None:
        """Enable or disable controls based on DOM and model weight availability."""
        weight_path = (
            Path(cfg.sam3WeightPath.value) if cfg.sam3WeightPath.value else None
        )
        is_weight_ready = bool(weight_path and weight_path.exists())
        is_dom_ready = bool(self._dom_path)

        # Buttons that require model weights only (file agnostic or file tab specific?)
        # Actually most require DOM.

        # Preview tab buttons require DOM + Weights
        is_preview_ready = is_weight_ready and is_dom_ready

        self.btn_pick_preview.setEnabled(is_preview_ready)
        self.btn_preview_detect.setEnabled(is_preview_ready)

        # Slice inference require DOM + Weights
        self.btn_slice_preview.setEnabled(is_preview_ready)
        self.btn_start_inference.setEnabled(is_preview_ready)

        self.btn_start_inference.setEnabled(is_preview_ready)

        # Save SHP should be enabled if we have points? Or always?
        # Usually checking if there are points to save is better, but here we stick to basic logic.
        # It handles "save points" which might be available after inference.
        # For now, let's enable it if DOM is ready (assuming workflow flow).
        self.btn_save_shp.setEnabled(is_dom_ready)

        if not is_weight_ready:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.seedling.msg.weight_unavailable"),
                parent=self,
                duration=4000,
            )
