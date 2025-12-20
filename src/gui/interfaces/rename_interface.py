"""
ID Renaming Page.
"""

from typing import Optional

from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel
from qfluentwidgets import (
    PushButton,
    PrimaryPushButton,
    ComboBox,
    SpinBox,
)

from src.gui.interfaces.map_interface import MapInterface
from src.gui.interfaces.base_interface import PageGroup
from src.gui.config import tr


class RenameInterface(MapInterface):
    """
    Interface content for Seedling ID Renaming.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for seedling renaming."""
        # --- File Group ---
        file_group = PageGroup(tr("page.common.file"))

        self.btn_load_shp = PushButton(tr("page.common.load_shp"))
        file_group.add_widget(self.btn_load_shp)

        self.add_group(file_group)

        # --- Ridge Group ---
        ridge_group = PageGroup(tr("page.rename.group.ridge"))

        ridge_group.add_widget(QLabel(tr("page.rename.label.direction")))
        self.combo_direction = ComboBox()
        self.combo_direction.addItems([
            tr("page.rename.combo.auto"), 
            tr("page.rename.combo.x"), 
            tr("page.rename.combo.y")
        ])
        ridge_group.add_widget(self.combo_direction)

        ridge_group.add_widget(QLabel(tr("page.rename.label.strength")))
        self.spin_strength = SpinBox()
        self.spin_strength.setRange(1, 50)
        self.spin_strength.setValue(10)
        ridge_group.add_widget(self.spin_strength)

        self.btn_detect_ridge = PushButton(tr("page.rename.btn.detect"))
        ridge_group.add_widget(self.btn_detect_ridge)

        self.add_group(ridge_group)

        # --- Numbering Group ---
        num_group = PageGroup(tr("page.rename.group.num"))

        num_group.add_widget(QLabel(tr("page.rename.label.format")))
        self.combo_format = ComboBox()
        self.combo_format.addItems([
            tr("page.rename.combo.rc_plant"),
            tr("page.rename.combo.numeric"),
            tr("page.rename.combo.custom")
        ])
        num_group.add_widget(self.combo_format)

        self.btn_apply_numbering = PushButton(tr("page.rename.btn.apply"))
        num_group.add_widget(self.btn_apply_numbering)

        self.add_group(num_group)

        # --- Save Group ---
        save_group = PageGroup(tr("page.seedling.group.save"))

        self.btn_save = PrimaryPushButton(tr("page.common.save"))
        save_group.add_widget(self.btn_save)

        self.add_group(save_group)

        self.add_stretch()
