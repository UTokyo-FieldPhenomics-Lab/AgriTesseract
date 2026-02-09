"""Subplot generation tab based on EasyIDP."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from loguru import logger
from PySide6.QtCore import Signal, Slot
from PySide6.QtWidgets import QFileDialog, QWidget
from qfluentwidgets import CheckBox, InfoBar, PushButton

from src.gui.components.base_interface import PageGroup, TabInterface
from src.gui.config import tr
from src.gui.tabs.subplot_easyidp import (
    calculate_optimal_rotation,
    generate_and_save,
    generate_subplots_roi,
    load_boundary_roi,
)


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
        """Initialize tab controls and panel signal wiring."""
        self._build_file_group()
        self._build_view_group()
        self.add_stretch()

        panel = self.property_panel.get_subplot_panel()
        panel.sigGenerate.connect(self._on_generate)
        panel.sigReset.connect(self._on_reset)
        panel.sigParamChanged.connect(self._auto_preview)

    def _build_file_group(self) -> None:
        """Build file loading control group."""
        file_group = PageGroup(tr("page.subplot.group.file"))

        self.btn_load_image = PushButton(tr("page.subplot.btn.load_image"))
        self.btn_load_image.clicked.connect(self._on_load_image)
        file_group.add_widget(self.btn_load_image)

        self.btn_load_boundary = PushButton(tr("page.subplot.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self._on_load_boundary)
        file_group.add_widget(self.btn_load_boundary)

        self.add_group(file_group)

    def _build_view_group(self) -> None:
        """Build map-view control group."""
        view_group = PageGroup(tr("page.subplot.group.view"))
        self.check_preview = CheckBox(tr("page.subplot.check.preview"))
        self.check_preview.setChecked(True)
        self.check_preview.stateChanged.connect(self._auto_preview)
        view_group.add_widget(self.check_preview)

        self.btn_focus = PushButton(tr("page.subplot.btn.focus"))
        self.btn_focus.clicked.connect(self._on_focus)
        view_group.add_widget(self.btn_focus)

        self.add_group(view_group)

    def _collect_params(self) -> dict:
        """Collect subplot parameters from property panel widgets.

        Returns
        -------
        dict
            Runtime parameters mapped to EasyIDP helper call schema.
        """
        panel = self.property_panel.get_subplot_panel()
        keep_values = ("all", "touch", "inside")
        keep_mode = keep_values[panel.combo_keep.currentIndex()]
        return {
            "mode_index": panel.combo_def_mode.currentIndex(),
            "rows": panel.spin_rows.value(),
            "cols": panel.spin_cols.value(),
            "width": panel.spin_width.value(),
            "height": panel.spin_height.value(),
            "x_spacing": panel.spin_x_spacing.value(),
            "y_spacing": panel.spin_y_spacing.value(),
            "keep_mode": keep_mode,
        }

    def _show_preview(self) -> None:
        """Generate and render preview layer when boundary exists."""
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

    @Slot(float)
    def _on_canvas_rotation_changed(self, angle: float) -> None:
        """Update rotation widget when map rotation changes.

        Parameters
        ----------
        angle : float
            Rotation angle in degrees.
        """
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
            InfoBar.success(
                title=tr("success"),
                content=f"Loaded: {Path(file_path).name}",
                parent=self,
                duration=3000,
            )
            if self.boundary_roi is None:
                self.map_component.map_canvas.zoom_to_layer(Path(file_path).stem)
            return

        InfoBar.error(
            title=tr("error"),
            content=f"Failed to load image: {file_path}",
            parent=self,
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
        except Exception as exc:  # pragma: no cover - UI feedback branch
            logger.exception("Failed to load boundary")
            InfoBar.error(
                title=tr("error"),
                content=f"{tr('page.subplot.error.invalid_boundary')} ({exc})",
                parent=self,
            )

    @Slot()
    def _auto_preview(self) -> None:
        """Trigger preview refresh when enabled."""
        if not self.check_preview.isChecked() or self.boundary_roi is None:
            return

        try:
            self._show_preview()
        except Exception as exc:  # pragma: no cover - UI feedback branch
            logger.debug(f"Preview error: {exc}")

    @Slot()
    def _on_focus(self) -> None:
        """Zoom to boundary and apply MAR-based auto-rotation."""
        if self.boundary_roi is None:
            return

        self.map_component.map_canvas.zoom_to_layer("Boundary")
        angle = calculate_optimal_rotation(self.boundary_roi)
        self.map_component.map_canvas.set_rotation(0 if angle is None else angle)

    @Slot()
    def _on_generate(self) -> None:
        """Generate subplots and save as shapefile."""
        if self.boundary_roi is None:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.subplot.warning.no_boundary"),
                parent=self,
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            tr("page.subplot.dialog.save"),
            "",
            "Shapefile (*.shp)",
        )
        if not file_path:
            return

        try:
            params = self._collect_params()
            generate_and_save(self.boundary_roi, output_path=file_path, **params)
            InfoBar.success(
                title=tr("success"),
                content=tr("page.subplot.msg.success"),
                parent=self,
            )
        except Exception as exc:  # pragma: no cover - UI feedback branch
            logger.exception("Subplot save failed")
            InfoBar.error(
                title=tr("error"),
                content=f"Generation failed: {exc}",
                parent=self,
            )

    @Slot()
    def _on_reset(self) -> None:
        """Reset action placeholder for future extension."""
        logger.debug("Subplot reset clicked")
