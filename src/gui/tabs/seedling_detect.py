"""Seedling detection tab with Fluent SegmentedWidget top tabs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import pyqtgraph as pg
import rasterio
from loguru import logger
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    BodyLabel,
    CheckBox,
    CommandBar,
    DoubleSpinBox,
    InfoBar,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SegmentedWidget,
    SpinBox,
    StateToolTip,
    qrouter,
)

from src.gui.components.base_interface import TabInterface
from src.gui.components.map_canvas import LayerBounds
from src.gui.config import cfg, tr
from src.utils.seedling_detect.io import export_inference_outputs
from src.utils.seedling_detect.preview_controller import SeedlingPreviewController
from src.utils.seedling_detect.qthread import (
    PreviewInferenceInput,
    SeedlingInferenceInput,
    SeedlingInferenceWorker,
    SeedlingPreviewWorker,
)
from src.utils.seedling_detect.slice import merge_slice_detections
from src.utils.subplot_generate.io import load_boundary_gdf


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
    sigFullInference = Signal()
    sigSaveCache = Signal()
    sigLoadCache = Signal()
    sigSavePoints = Signal()
    sigPreviewModeToggled = Signal(bool)
    sigPreviewSizeRequested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dom_path: str = ""
        self._boundary_gdf = None
        self._boundary_file_path: str = ""
        self._preview_thread: Optional[QThread] = None
        self._preview_worker: Optional[SeedlingPreviewWorker] = None
        self._full_thread: Optional[QThread] = None
        self._full_worker: Optional[SeedlingInferenceWorker] = None
        self._last_full_result: Optional[dict] = None
        self._last_export_points_path: str = ""
        self._last_export_prefix_path: str = ""
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
        self.btn_load_boundary = PushButton(tr("page.seedling.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self._on_load_boundary)
        self.label_boundary_path = BodyLabel(tr("page.seedling.label.no_boundary"))
        self.label_boundary_path.setMinimumWidth(220)

        # bar.addAction(Action(FIF.ROBOT, tr("page.seedling.group.sam")))
        # bar.addSeparator()
        bar.addWidget(self.btn_load_dom)
        bar.addSeparator()
        bar.addWidget(self.label_dom)
        bar.addSeparator()
        bar.addWidget(self.btn_load_boundary)
        bar.addSeparator()
        bar.addWidget(self.label_boundary_path)
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

        self.btn_save_shp = PrimaryPushButton(tr("page.seedling.btn.save_shp"))
        self.btn_save_shp.clicked.connect(self._on_save_shp_clicked)
        self.btn_send_to_next = PushButton(tr("page.seedling.btn.send_to_next"))
        self.btn_send_to_next.clicked.connect(self._on_send_to_next_clicked)
        self.btn_send_to_next.setEnabled(False)

        bar.addWidget(self.btn_save_shp)
        bar.addWidget(self.btn_send_to_next)
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
        """Return boundary coordinates from loaded GeoDataFrame for filtering."""
        if self._boundary_gdf is None:
            return None
        if len(self._boundary_gdf) != 1:
            return None
        geometry = self._boundary_gdf.geometry.iloc[0]
        if geometry.geom_type == "MultiPolygon":
            geometry = list(geometry.geoms)[0]
        return [list(coord[:2]) for coord in geometry.exterior.coords]

    def _slice_boundary_mode(self) -> str:
        """Return boundary mode for slice filtering."""
        if self._boundary_gdf is None:
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
            self._boundary_gdf = load_boundary_gdf(file_path)
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
        self.label_boundary_path.setText(file_path)
        self.map_component.map_canvas.add_vector_layer(
            self._boundary_gdf,
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

        self.spin_iou_thresh = DoubleSpinBox()
        self.spin_iou_thresh.setRange(0.05, 0.95)
        self.spin_iou_thresh.setValue(0.5)
        self.spin_iou_thresh.setSingleStep(0.05)

        self.check_rm_boundary = CheckBox(tr("page.seedling.check.rm_boundary"))
        self.check_rm_boundary.setChecked(True)

        self.check_rm_overlay = CheckBox(tr("page.seedling.check.rm_overlay"))
        self.check_rm_overlay.setChecked(True)

        self.spin_ios_thresh = DoubleSpinBox()
        self.spin_ios_thresh.setRange(0.5, 1.0)
        self.spin_ios_thresh.setValue(0.95)
        self.spin_ios_thresh.setSingleStep(0.01)

        self.btn_start_inference = PrimaryPushButton(
            tr("page.seedling.btn.start_inference")
        )
        self.btn_start_inference.clicked.connect(self._on_full_inference_clicked)
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
        layout.addWidget(
            self._build_labeled_spin(
                "page.seedling.label.iou_thresh", self.spin_iou_thresh
            )
        )
        layout.addWidget(self.check_rm_boundary)
        layout.addWidget(self.check_rm_overlay)
        layout.addWidget(
            self._build_labeled_spin(
                "page.seedling.label.ios_thresh", self.spin_ios_thresh
            )
        )

        self.check_rm_boundary.toggled.connect(self._refresh_full_inference_layers)
        self.check_rm_overlay.toggled.connect(self._refresh_full_inference_layers)
        self.spin_iou_thresh.valueChanged.connect(self._refresh_full_inference_layers)
        self.spin_ios_thresh.valueChanged.connect(self._refresh_full_inference_layers)
        return wrapper

    @Slot()
    def _on_full_inference_clicked(self) -> None:
        """Start or stop full-map inference worker."""
        if self._full_thread is not None:
            self._stop_full_inference()
            return
        self._start_full_inference()

    def _start_full_inference(self) -> None:
        """Create and start full-map inference worker thread."""
        if not self._dom_path:
            return
        payload = SeedlingInferenceInput(
            dom_path=self._dom_path,
            weight_path=str(cfg.sam3WeightPath.value),
            prompt=self.edit_prompt.text().strip() or "plants",
            conf=float(self.spin_conf.value()),
            iou=float(self.spin_iou.value()),
            slice_size=int(self.spin_slice_size.value()),
            overlap_ratio=float(self.spin_overlap.value()),
            cache_dir=self._preview_cache_dir(),
        )
        self._full_thread = QThread(self)
        self._full_worker = SeedlingInferenceWorker(payload)
        self._full_worker.moveToThread(self._full_thread)
        self._full_thread.started.connect(self._full_worker.run)
        self._full_worker.sigProgress.connect(self._on_full_inference_progress)
        self._full_worker.sigFinished.connect(self._on_full_inference_finished)
        self._full_worker.sigFailed.connect(self._on_full_inference_failed)
        self._full_worker.sigCancelled.connect(self._on_full_inference_cancelled)
        self._full_thread.start()
        self.btn_start_inference.setText(tr("page.seedling.btn.stop_inference"))
        self.map_component.status_bar.set_progress(None)

    def _stop_full_inference(self) -> None:
        """Request cancellation for running full-map inference."""
        if self._full_worker is None:
            return
        self._full_worker.request_cancel()

    def _teardown_full_thread(self) -> None:
        """Cleanup full-map worker thread and restore UI state."""
        if self._full_thread is not None:
            self._full_thread.quit()
            self._full_thread.wait(1000)
            self._full_thread.deleteLater()
        self._full_thread = None
        self._full_worker = None
        self.btn_start_inference.setText(tr("page.seedling.btn.start_inference"))
        self.map_component.status_bar.set_progress(-1)

    @Slot(int)
    def _on_full_inference_progress(self, percent: int) -> None:
        """Update status bar progress for full-map inference."""
        value = max(0, min(100, int(percent)))
        self.map_component.status_bar.set_progress(value)

    @Slot(dict)
    def _on_full_inference_finished(self, result_payload: dict) -> None:
        """Store full-map inference result and cleanup worker."""
        self._last_full_result = result_payload
        self._refresh_full_inference_layers(notify=True)
        self._teardown_full_thread()

    def _refresh_full_inference_layers(self, *_args, notify: bool = False) -> None:
        """Apply selected post-filters and refresh result layers."""
        if self._last_full_result is None:
            return
        merged_result = merge_slice_detections(
            slice_result_list=self._last_full_result.get("slices", []),
            iou_threshold=float(self.spin_iou_thresh.value()),
            ios_threshold=float(self.spin_ios_thresh.value()),
            remove_boundary=bool(self.check_rm_boundary.isChecked()),
            remove_overlay=bool(self.check_rm_overlay.isChecked()),
        )
        self._last_full_result["merged"] = merged_result
        boxes_xyxy = np.asarray(merged_result.get("boxes_xyxy", np.zeros((0, 4))))
        raw_polygons = merged_result.get("polygons_xy", [])
        polygon_list = raw_polygons if isinstance(raw_polygons, list) else []
        polygons_xy = [np.asarray(poly_xy, dtype=float) for poly_xy in polygon_list]
        points_xy = np.asarray(merged_result.get("points_xy", np.zeros((0, 2))))
        self._preview_ctrl.show_inference_result_layers(
            boxes_xyxy=boxes_xyxy,
            polygons_xy=polygons_xy,
            points_xy=points_xy,
        )
        self.btn_save_shp.setEnabled(bool(boxes_xyxy.shape[0] > 0))
        self.btn_send_to_next.setEnabled(bool(boxes_xyxy.shape[0] > 0))
        if notify:
            InfoBar.success(
                title=tr("success"),
                content=f"Full inference done: {boxes_xyxy.shape[0]} objects",
                parent=self,
                duration=2500,
            )

    @Slot(str)
    def _on_full_inference_failed(self, message: str) -> None:
        """Handle full-map inference failure and cleanup worker."""
        logger.error("Full-map inference failed: {}", message)
        InfoBar.error(
            title=tr("error"),
            content=message.splitlines()[0] if message else tr("error"),
            parent=self,
            duration=5000,
        )
        self._teardown_full_thread()

    @Slot()
    def _on_full_inference_cancelled(self) -> None:
        """Handle full-map inference cancellation signal."""
        InfoBar.warning(
            title=tr("warning"),
            content=tr("page.seedling.msg.preview_cancelled"),
            parent=self,
            duration=1800,
        )
        self._teardown_full_thread()

    @Slot()
    def _on_save_shp_clicked(self) -> None:
        """Export merged inference bbox/points results to shapefiles."""
        if self._last_full_result is None or "merged" not in self._last_full_result:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.seedling.msg.no_merged_results"),
                parent=self,
                duration=2500,
            )
            return
        out_prefix_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("page.seedling.dialog.save_results"),
            "",
            "Shapefile Prefix (*.shp);;All Files (*)",
        )
        if not out_prefix_path:
            return
        export_prefix = Path(out_prefix_path)
        if export_prefix.suffix.lower() == ".shp":
            export_prefix = export_prefix.with_suffix("")
        bbox_df, points_df, polygon_df = self._build_export_frames(
            self._last_full_result["merged"]
        )
        export_inference_outputs(
            out_prefix=export_prefix,
            bbox_df=bbox_df,
            points_df=points_df,
            polygon_df=polygon_df,
            crs_wkt=self._current_dom_crs_wkt(),
        )
        self._last_export_prefix_path = str(export_prefix)
        self._last_export_points_path = str(
            export_prefix.parent / f"{export_prefix.name}_points.shp"
        )
        self.btn_send_to_next.setEnabled(True)
        InfoBar.success(
            title=tr("success"),
            content=tr("page.seedling.msg.save_results_success"),
            parent=self,
            duration=2500,
        )

    def _build_export_frames(
        self, merged_result: dict
    ) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Build bbox/point dataframes from merged inference payload."""
        boxes_xyxy = np.asarray(merged_result.get("boxes_xyxy", np.zeros((0, 4))))
        scores = np.asarray(merged_result.get("scores", np.zeros((0,))))
        points_xy = np.asarray(merged_result.get("points_xy", np.zeros((0, 2))))
        polygons_xy = list(merged_result.get("polygons_xy", []))
        fid_values = np.arange(boxes_xyxy.shape[0], dtype=int)
        bbox_df = pd.DataFrame(
            {
                "fid": fid_values,
                "xmin": boxes_xyxy[:, 0] if boxes_xyxy.size else [],
                "ymin": boxes_xyxy[:, 1] if boxes_xyxy.size else [],
                "xmax": boxes_xyxy[:, 2] if boxes_xyxy.size else [],
                "ymax": boxes_xyxy[:, 3] if boxes_xyxy.size else [],
                "score": scores if scores.size else [],
            }
        )
        points_df = pd.DataFrame(
            {
                "fid": fid_values,
                "x": points_xy[:, 0] if points_xy.size else [],
                "y": points_xy[:, 1] if points_xy.size else [],
                "source": ["sam3"] * len(fid_values),
                "conf": scores if scores.size else [],
            }
        )
        if len(polygons_xy) != len(fid_values):
            polygons_xy = [
                [
                    (float(box_row[0]), float(box_row[1])),
                    (float(box_row[2]), float(box_row[1])),
                    (float(box_row[2]), float(box_row[3])),
                    (float(box_row[0]), float(box_row[3])),
                    (float(box_row[0]), float(box_row[1])),
                ]
                for box_row in boxes_xyxy
            ]
        polygon_df = pd.DataFrame(
            {
                "fid": fid_values,
                "score": scores if scores.size else [],
                "polygon": [
                    [(float(x), float(y)) for x, y in np.asarray(poly_xy, dtype=float)]
                    for poly_xy in polygons_xy
                ],
            }
        )
        return bbox_df, points_df, polygon_df

    @Slot()
    def _on_send_to_next_clicked(self) -> None:
        """Send exported points shapefile path to rename tab."""
        if (
            not self._last_export_points_path
            and self._last_export_prefix_path == ""
            and self._last_full_result is not None
        ):
            self._export_points_to_default_cache()
        if (
            not self._last_export_points_path
            or not Path(self._last_export_points_path).exists()
        ):
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.seedling.msg.save_first_before_send"),
                parent=self,
                duration=2500,
            )
            return
        window_obj = self.window()
        rename_tab = getattr(window_obj, "rename_tab", None)
        if rename_tab is None:
            return
        rename_tab.sigLoadShp.emit(self._last_export_points_path)
        self._copy_points_overlay_to_rename_tab(rename_tab)
        switch_method = getattr(window_obj, "switchTo", None)
        if callable(switch_method):
            switch_method(rename_tab)
        rename_map_component = getattr(rename_tab, "map_component", None)
        rename_canvas = (
            getattr(rename_map_component, "map_canvas", None)
            if rename_map_component is not None
            else None
        )
        if rename_canvas is not None:
            rename_canvas.zoom_to_layer("result_points")
        InfoBar.success(
            title=tr("success"),
            content=tr("page.seedling.msg.sent_to_next"),
            parent=self,
            duration=1800,
        )

    def _export_points_to_default_cache(self) -> None:
        """Export current merged points to cache path for send-next action."""
        if self._last_full_result is None or "merged" not in self._last_full_result:
            return
        out_dir = Path(self._preview_cache_dir()) / "seedling_send_next"
        out_prefix = out_dir / "seedling_result"
        bbox_df, points_df, polygon_df = self._build_export_frames(
            self._last_full_result["merged"]
        )
        export_inference_outputs(
            out_prefix=out_prefix,
            bbox_df=bbox_df,
            points_df=points_df,
            polygon_df=polygon_df,
            crs_wkt=self._current_dom_crs_wkt(),
        )
        self._last_export_prefix_path = str(out_prefix)
        self._last_export_points_path = str(out_dir / "seedling_result_points.shp")

    def _copy_points_overlay_to_rename_tab(self, rename_tab: object) -> None:
        """Copy merged points as overlay layer onto rename tab map canvas."""
        if self._last_full_result is None:
            return
        merged = self._last_full_result.get("merged", {})
        points_xy = np.asarray(merged.get("points_xy", np.zeros((0, 2))), dtype=float)
        if points_xy.size == 0:
            return
        map_component = getattr(rename_tab, "map_component", None)
        if map_component is None:
            return
        map_canvas = getattr(map_component, "map_canvas", None)
        if map_canvas is None:
            return
        layer_name = "result_points"
        map_canvas.remove_layer(layer_name)
        scatter_item = pg.ScatterPlotItem(
            x=points_xy[:, 0],
            y=points_xy[:, 1],
            symbol="o",
            size=8,
            pen=pg.mkPen(color="#FFAA00", width=1.2),
            brush=pg.mkBrush(255, 120, 0, 180),
        )
        scatter_item.setZValue(630)
        map_canvas.add_overlay_item(scatter_item)
        x_min = float(np.min(points_xy[:, 0]))
        y_min = float(np.min(points_xy[:, 1]))
        x_max = float(np.max(points_xy[:, 0]))
        y_max = float(np.max(points_xy[:, 1]))
        map_canvas._layers[layer_name] = {
            "item": scatter_item,
            "visible": True,
            "bounds": LayerBounds(x_min, y_min, x_max, y_max),
        }
        map_canvas._layer_order.append(layer_name)
        map_canvas.sigLayerAdded.emit(layer_name, "Vector")

    def _current_dom_crs_wkt(self) -> str | None:
        """Read current DOM CRS WKT text for PRJ export."""
        if not self._dom_path:
            return None
        with rasterio.open(self._dom_path) as dataset:
            if dataset.crs is None:
                return None
            return dataset.crs.to_wkt()

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
        self._last_full_result = None
        self._last_export_points_path = ""
        self._last_export_prefix_path = ""
        self._preview_ctrl.clear_inference_result_layers()
        self.label_dom.setText(file_path)
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

        has_merged = bool(
            self._last_full_result is not None
            and isinstance(self._last_full_result.get("merged", {}), dict)
            and np.asarray(
                self._last_full_result.get("merged", {}).get(
                    "boxes_xyxy", np.zeros((0, 4))
                ),
                dtype=float,
            ).shape[0]
            > 0
        )
        self.btn_save_shp.setEnabled(has_merged)
        self.btn_send_to_next.setEnabled(
            bool(
                self._last_export_points_path
                and Path(self._last_export_points_path).exists()
            )
            or has_merged
        )

        if not is_weight_ready:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.seedling.msg.weight_unavailable"),
                parent=self,
                duration=4000,
            )
