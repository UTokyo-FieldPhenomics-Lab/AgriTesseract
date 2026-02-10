"""Seedling detection tab with Office-style top tabs."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
from qfluentwidgets import (
    DoubleSpinBox,
    InfoBar,
    LineEdit,
    PrimaryPushButton,
    PushButton,
    SpinBox,
)

from src.gui.components.base_interface import PageGroup, TabInterface
from src.gui.config import cfg, tr


class SeedlingTab(TabInterface):
    """Main interface for SAM3-based seedling detection workflow."""

    sigLoadDom = Signal(str)
    sigPreviewDetect = Signal()
    sigFullDetect = Signal()
    sigSaveCache = Signal()
    sigLoadCache = Signal()
    sigSavePoints = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._dom_path: str = ""
        self._init_controls()
        self._apply_weight_availability()
        cfg.sam3WeightPath.valueChanged.connect(
            lambda _: self._apply_weight_availability()
        )

    def _init_controls(self) -> None:
        """Initialize Office-style tab control area."""
        office_group = PageGroup(tr("page.seedling.group.office"))
        office_group.add_widget(self._build_top_tabs())
        self.add_group(office_group)
        self.add_stretch()
        self.property_panel.set_current_tab(1)

    def _build_top_tabs(self) -> QWidget:
        """Build top tab widget container."""
        container = QWidget()
        container.setMinimumWidth(920)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        self.top_tabs = QTabWidget()
        self.tab_file = self._build_file_tab()
        self.tab_sam3 = self._build_sam3_tab()
        self.tab_points = self._build_points_tab()
        self.top_tabs.addTab(self.tab_file, tr("page.seedling.tab.file"))
        self.top_tabs.addTab(self.tab_sam3, tr("page.seedling.tab.sam3"))
        self.top_tabs.addTab(self.tab_points, tr("page.seedling.tab.points"))
        layout.addWidget(self.top_tabs)
        return container

    def _build_file_tab(self) -> QWidget:
        """Build DOM file tab content."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 6, 8, 6)

        self.btn_load_dom = PushButton(tr("page.seedling.btn.load_dom"))
        self.btn_load_dom.clicked.connect(self._on_load_dom)
        layout.addWidget(self.btn_load_dom)

        self.label_dom = QLabel(tr("page.seedling.label.no_dom"))
        self.label_dom.setMinimumWidth(380)
        layout.addWidget(self.label_dom)
        layout.addStretch()
        return tab

    def _build_sam3_tab(self) -> QWidget:
        """Build SAM3 parameter and execution tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(12)

        layout.addLayout(self._build_model_panel())
        layout.addLayout(self._build_preview_panel())
        layout.addLayout(self._build_execute_panel())
        layout.addLayout(self._build_cache_panel())
        layout.addStretch()
        return tab

    def _build_points_tab(self) -> QWidget:
        """Build point editing and export tab."""
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 6, 8, 6)

        self.btn_view = PushButton(tr("page.seedling.btn.view"))
        self.btn_view.setCheckable(True)
        self.btn_view.setChecked(True)
        layout.addWidget(self.btn_view)

        self.btn_add = PushButton(tr("page.seedling.btn.add"))
        self.btn_add.setCheckable(True)
        layout.addWidget(self.btn_add)

        self.btn_move = PushButton(tr("page.seedling.btn.move"))
        self.btn_move.setCheckable(True)
        layout.addWidget(self.btn_move)

        self.btn_delete = PushButton(tr("page.seedling.btn.delete"))
        self.btn_delete.setCheckable(True)
        layout.addWidget(self.btn_delete)

        self.btn_undo = PushButton(tr("page.seedling.btn.undo"))
        layout.addWidget(self.btn_undo)

        self.btn_save_points = PrimaryPushButton(tr("page.common.save"))
        self.btn_save_points.clicked.connect(self.sigSavePoints.emit)
        layout.addWidget(self.btn_save_points)
        layout.addStretch()
        return tab

    def _build_model_panel(self) -> QFormLayout:
        """Build model parameter controls."""
        form = QFormLayout()
        self.edit_prompt = LineEdit()
        self.edit_prompt.setText("plants")
        form.addRow(tr("page.seedling.label.prompt"), self.edit_prompt)

        self.spin_conf = DoubleSpinBox()
        self.spin_conf.setRange(0.01, 1.0)
        self.spin_conf.setValue(0.5)
        self.spin_conf.setSingleStep(0.05)
        form.addRow(tr("prop.label.confidence"), self.spin_conf)

        self.spin_iou = DoubleSpinBox()
        self.spin_iou.setRange(0.01, 0.95)
        self.spin_iou.setValue(0.4)
        self.spin_iou.setSingleStep(0.05)
        form.addRow(tr("prop.label.nms_iou"), self.spin_iou)
        return form

    def _build_preview_panel(self) -> QFormLayout:
        """Build preview region controls."""
        form = QFormLayout()
        self.spin_preview_size = SpinBox()
        self.spin_preview_size.setRange(128, 2048)
        self.spin_preview_size.setValue(640)
        self.spin_preview_size.setSingleStep(32)
        form.addRow(tr("page.seedling.label.preview_size"), self.spin_preview_size)

        self.btn_pick_preview = PushButton(tr("page.seedling.btn.pick_preview"))
        form.addRow("", self.btn_pick_preview)

        self.btn_preview_detect = PrimaryPushButton(
            tr("page.seedling.btn.preview_detect")
        )
        self.btn_preview_detect.clicked.connect(self.sigPreviewDetect.emit)
        form.addRow("", self.btn_preview_detect)
        return form

    def _build_execute_panel(self) -> QFormLayout:
        """Build full-image slicing execution controls."""
        form = QFormLayout()
        self.spin_slice_size = SpinBox()
        self.spin_slice_size.setRange(256, 2048)
        self.spin_slice_size.setValue(640)
        self.spin_slice_size.setSingleStep(64)
        form.addRow(tr("page.seedling.label.size"), self.spin_slice_size)

        self.spin_overlap = DoubleSpinBox()
        self.spin_overlap.setRange(0.0, 0.8)
        self.spin_overlap.setValue(0.2)
        self.spin_overlap.setSingleStep(0.05)
        form.addRow(tr("page.seedling.label.overlap"), self.spin_overlap)

        self.btn_full_detect = PrimaryPushButton(tr("page.seedling.btn.detect"))
        self.btn_full_detect.clicked.connect(self.sigFullDetect.emit)
        form.addRow("", self.btn_full_detect)
        return form

    def _build_cache_panel(self) -> QFormLayout:
        """Build cache save/load controls."""
        form = QFormLayout()
        self.btn_save_cache = PushButton(tr("page.seedling.btn.save_cache"))
        self.btn_save_cache.clicked.connect(self.sigSaveCache.emit)
        form.addRow("", self.btn_save_cache)

        self.btn_load_cache = PushButton(tr("page.seedling.btn.load_cache"))
        self.btn_load_cache.clicked.connect(self.sigLoadCache.emit)
        form.addRow("", self.btn_load_cache)
        return form

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
        self.sigLoadDom.emit(file_path)

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
