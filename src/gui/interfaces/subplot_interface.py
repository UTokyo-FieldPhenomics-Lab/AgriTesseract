
from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel, QFileDialog, QMessageBox
from PySide6.QtCore import Signal, Slot
from qfluentwidgets import (
    PushButton,
    PrimaryPushButton,
    ComboBox,
    SpinBox,
    DoubleSpinBox,
    CheckBox,
    InfoBar,
    InfoBarPosition
)

from src.gui.interfaces.base_interface import MapInterface, PageGroup
from src.gui.config import tr
from src.core.subplot_generator import SubplotGenerator


class SubplotInterface(MapInterface):
    """
    Interface content for Subplot Generation.
    """

    sigLoadImage = Signal()
    sigLoadBoundary = Signal()
    sigPreview = Signal()
    sigGenerate = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for subplot generation."""
        # --- File Group ---
        # TODO: Add i18n keys for group titles
        file_group = PageGroup(tr("page.subplot.group.file"))

        self.btn_load_image = PushButton(tr("page.subplot.btn.load_image"))
        self.btn_load_image.clicked.connect(self._on_load_image)
        file_group.add_widget(self.btn_load_image)

        self.btn_load_boundary = PushButton(tr("page.subplot.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self._on_load_boundary)
        file_group.add_widget(self.btn_load_boundary)

        self.add_group(file_group)

        # --- Definition Group ---
        def_group = PageGroup(tr("page.subplot.group.def"))

        self.combo_def_mode = ComboBox()
        self.combo_def_mode.addItems([tr("page.subplot.combo.rc"), tr("page.subplot.combo.size")])
        self.combo_def_mode.currentIndexChanged.connect(self._on_mode_changed)
        def_group.add_widget(self.combo_def_mode)

        self.add_group(def_group)

        # --- Parameters Group ---
        param_group = PageGroup(tr("page.subplot.group.param"))

        # Row/Col or Width/Height
        self.lbl_cols = QLabel(tr("page.subplot.label.cols"))
        param_group.add_widget(self.lbl_cols)
        self.spin_cols = SpinBox()
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(5)
        self.spin_cols.setMinimumWidth(60)
        self.spin_cols.valueChanged.connect(self._auto_preview)
        param_group.add_widget(self.spin_cols)

        self.lbl_rows = QLabel(tr("page.subplot.label.rows"))
        param_group.add_widget(self.lbl_rows)
        self.spin_rows = SpinBox()
        self.spin_rows.setRange(1, 100)
        self.spin_rows.setValue(5)
        self.spin_rows.setMinimumWidth(60)
        self.spin_rows.valueChanged.connect(self._auto_preview)
        param_group.add_widget(self.spin_rows)

        param_group.add_widget(QLabel(tr("page.subplot.label.x_space")))
        self.spin_x_spacing = DoubleSpinBox()
        self.spin_x_spacing.setRange(-10, 100)
        self.spin_x_spacing.setValue(0.0)
        self.spin_x_spacing.setSuffix(" m")
        self.spin_x_spacing.setMinimumWidth(70)
        self.spin_x_spacing.valueChanged.connect(self._auto_preview)
        param_group.add_widget(self.spin_x_spacing)

        param_group.add_widget(QLabel(tr("page.subplot.label.y_space")))
        self.spin_y_spacing = DoubleSpinBox()
        self.spin_y_spacing.setRange(-10, 100)
        self.spin_y_spacing.setValue(0.0)
        self.spin_y_spacing.setSuffix(" m")
        self.spin_y_spacing.setMinimumWidth(70)
        self.spin_y_spacing.valueChanged.connect(self._auto_preview)
        param_group.add_widget(self.spin_y_spacing)

        self.add_group(param_group)

        # --- Actions Group ---
        action_group = PageGroup(tr("page.subplot.group.action"))

        self.check_preview = CheckBox(tr("page.subplot.check.preview"))
        self.check_preview.setChecked(True)
        self.check_preview.stateChanged.connect(self._auto_preview)
        action_group.add_widget(self.check_preview)

        self.btn_focus = PushButton(tr("page.subplot.btn.focus"))
        self.btn_focus.clicked.connect(self._on_focus)
        action_group.add_widget(self.btn_focus)

        self.btn_generate = PrimaryPushButton(tr("page.subplot.btn.generate"))
        self.btn_generate.clicked.connect(self._on_generate)
        action_group.add_widget(self.btn_generate)

        self.add_group(action_group)

        self.add_stretch()

        # Init Generator
        self.generator = SubplotGenerator()
        self.boundary_gdf = None

        # Init Maps
        # self.map_component comes from MapInterface

    @Slot()
    def _on_load_image(self):
        """Load background image (DOM)."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("page.subplot.dialog.load_image"), "", "Image Files (*.tif *.tiff *.png *.jpg);;All Files (*)"
        )
        if file_path:
            self.map_component.map_canvas.load_geotiff(file_path)

    @Slot()
    def _on_load_boundary(self):
        """Load boundary SHP."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("page.subplot.dialog.load_boundary"), "", "Shapefile (*.shp);;All Files (*)"
        )
        if file_path:
            gdf = self.generator.load_boundary(file_path)
            if gdf is not None:
                self.boundary_gdf = gdf
                self.map_component.map_canvas.add_vector_layer(
                    gdf, "Boundary", color='#FF0000', width=2
                )
                self._auto_preview()
            else:
                InfoBar.error(
                    title=tr("error"),
                    content=tr("page.subplot.error.invalid_boundary"),
                    parent=self
                )

    @Slot()
    def _on_mode_changed(self, index: int):
        """Handle definition mode change."""
        pass  # TODO: Update UI labels based on mode (RC vs Size)

    @Slot()
    def _auto_preview(self):
        """Generate preview if checkbox is checked."""
        if not self.check_preview.isChecked() or self.boundary_gdf is None:
            return
        
        try:
            rows = self.spin_rows.value()
            cols = self.spin_cols.value()
            x_space = self.spin_x_spacing.value()
            y_space = self.spin_y_spacing.value()

            gdf = self.generator.generate(
                self.boundary_gdf, rows, cols, x_space, y_space, output_path=None
            )
            
            if gdf is not None:
                self.map_component.map_canvas.add_vector_layer(
                    gdf, "Preview", color='#00FF00', width=1
                )
        except Exception as e:
            # Don't show popup on auto preview error, just log
            print(f"Preview error: {e}")

    @Slot()
    def _on_focus(self):
        """Focus on boundary layer."""
        if self.boundary_gdf is not None:
            self.map_component.map_canvas.zoom_to_layer("Boundary")

    @Slot()
    def _on_generate(self):
        """Generate and save subplots."""
        if self.boundary_gdf is None:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.subplot.warning.no_boundary"),
                parent=self
            )
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, tr("page.subplot.dialog.save_shp"), "", "Shapefile (*.shp)"
        )
        if not file_path:
            return

        try:
            rows = self.spin_rows.value()
            cols = self.spin_cols.value()
            x_space = self.spin_x_spacing.value()
            y_space = self.spin_y_spacing.value()

            self.generator.generate(
                self.boundary_gdf, rows, cols, x_space, y_space, output_path=file_path
            )
            
            InfoBar.success(
                title=tr("success"),
                content=tr("page.subplot.success.generated"),
                parent=self
            )
            
            # Load the generated result
            self.map_component.map_canvas.add_vector_layer(
                file_path, "Result", color='#0000FF', width=2
            )
            
        except Exception as e:
            InfoBar.error(
                title=tr("error"),
                content=f"Generation failed: {e}",
                parent=self
            )
