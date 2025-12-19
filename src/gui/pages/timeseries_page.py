"""
Time Series Crop Page.
"""

from typing import Optional

from PySide6.QtWidgets import (
    QWidget,
    QPushButton,
    QComboBox,
    QLabel,
    QLineEdit,
    QDoubleSpinBox,
)

from src.gui.pages.base_page import BasePage, PageGroup
from src.gui.i18n import tr


class TimeSeriesPage(BasePage):
    """
    Page content for Time Series Cropping.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for time series cropping."""
        # --- File Group ---
        file_group = PageGroup(tr("page.common.file"))

        self.btn_load_points = QPushButton(tr("page.ts.btn.load_points"))
        file_group.add_widget(self.btn_load_points)

        self.btn_add_date = QPushButton(tr("page.ts.btn.add_date"))
        file_group.add_widget(self.btn_add_date)

        self.add_group(file_group)

        # --- Crop Parameters Group ---
        param_group = PageGroup(tr("page.ts.group.param"))

        param_group.add_widget(QLabel(tr("page.ts.label.type")))
        self.combo_size_type = QComboBox()
        self.combo_size_type.addItems([tr("page.ts.combo.real"), tr("page.ts.combo.pixel")])
        param_group.add_widget(self.combo_size_type)

        param_group.add_widget(QLabel(tr("page.ts.label.side")))
        self.spin_crop_size = QDoubleSpinBox()
        self.spin_crop_size.setRange(0.1, 100)
        self.spin_crop_size.setValue(1.0)
        param_group.add_widget(self.spin_crop_size)

        self.add_group(param_group)

        # --- Output Group ---
        output_group = PageGroup(tr("page.ts.group.output"))

        output_group.add_widget(QLabel(tr("page.ts.label.dir")))
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setMinimumWidth(150)
        output_group.add_widget(self.edit_output_dir)

        self.btn_browse = QPushButton(tr("page.ts.btn.browse"))
        output_group.add_widget(self.btn_browse)

        self.btn_start_crop = QPushButton(tr("page.ts.btn.start"))
        self.btn_start_crop.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }"
        )
        output_group.add_widget(self.btn_start_crop)

        self.add_group(output_group)

        self.add_stretch()
