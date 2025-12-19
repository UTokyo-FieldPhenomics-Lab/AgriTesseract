"""
Subplot Generation Page.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QComboBox,
    QLabel,
    QSpinBox,
    QDoubleSpinBox,
    QCheckBox,
)
from PySide6.QtCore import Signal

from src.gui.pages.base_page import BasePage, PageGroup
from src.gui.i18n import tr


class SubplotPage(BasePage):
    """
    Page content for Subplot Generation.
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

        self.btn_load_image = QPushButton(tr("page.subplot.btn.load_image"))
        self.btn_load_image.clicked.connect(self.sigLoadImage.emit)
        file_group.add_widget(self.btn_load_image)

        self.btn_load_boundary = QPushButton(tr("page.subplot.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self.sigLoadBoundary.emit)
        file_group.add_widget(self.btn_load_boundary)

        self.add_group(file_group)

        # --- Definition Group ---
        def_group = PageGroup(tr("page.subplot.group.def"))

        self.combo_def_mode = QComboBox()
        self.combo_def_mode.addItems([tr("page.subplot.combo.rc"), tr("page.subplot.combo.size")])
        def_group.add_widget(self.combo_def_mode)

        self.add_group(def_group)

        # --- Parameters Group ---
        param_group = PageGroup(tr("page.subplot.group.param"))

        # Row/Col or Width/Height
        param_group.add_widget(QLabel(tr("page.subplot.label.cols")))
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(5)
        self.spin_cols.setMinimumWidth(60)
        param_group.add_widget(self.spin_cols)

        param_group.add_widget(QLabel(tr("page.subplot.label.rows")))
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 100)
        self.spin_rows.setValue(5)
        self.spin_rows.setMinimumWidth(60)
        param_group.add_widget(self.spin_rows)

        param_group.add_widget(QLabel(tr("page.subplot.label.x_space")))
        self.spin_x_spacing = QDoubleSpinBox()
        self.spin_x_spacing.setRange(-10, 100)
        self.spin_x_spacing.setValue(0.0)
        self.spin_x_spacing.setSuffix(" m")
        self.spin_x_spacing.setMinimumWidth(70)
        param_group.add_widget(self.spin_x_spacing)

        param_group.add_widget(QLabel(tr("page.subplot.label.y_space")))
        self.spin_y_spacing = QDoubleSpinBox()
        self.spin_y_spacing.setRange(-10, 100)
        self.spin_y_spacing.setValue(0.0)
        self.spin_y_spacing.setSuffix(" m")
        self.spin_y_spacing.setMinimumWidth(70)
        param_group.add_widget(self.spin_y_spacing)

        self.add_group(param_group)

        # --- Actions Group ---
        action_group = PageGroup(tr("page.subplot.group.action"))

        self.check_preview = QCheckBox(tr("page.subplot.check.preview"))
        self.check_preview.setChecked(True)
        action_group.add_widget(self.check_preview)

        self.btn_focus = QPushButton(tr("page.subplot.btn.focus"))
        action_group.add_widget(self.btn_focus)

        self.btn_generate = QPushButton(tr("page.subplot.btn.generate"))
        self.btn_generate.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }"
        )
        self.btn_generate.clicked.connect(self.sigGenerate.emit)
        action_group.add_widget(self.btn_generate)

        self.add_group(action_group)

        self.add_stretch()
