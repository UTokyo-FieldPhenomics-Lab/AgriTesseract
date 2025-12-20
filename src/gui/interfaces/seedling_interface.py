"""
Seedling Detection Page.
"""

from typing import Optional

from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Signal
from qfluentwidgets import (
    PushButton,
    PrimaryPushButton,
    LineEdit,
    SpinBox,
    DoubleSpinBox,
)

from src.gui.interfaces.map_interface import MapInterface
from src.gui.interfaces.base_interface import PageGroup
from src.gui.config import tr


class SeedlingInterface(MapInterface):
    """
    Interface content for Seedling Detection.
    """

    sigDetect = Signal()
    sigSave = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for seedling detection."""
        # --- SAM3 Group ---
        sam_group = PageGroup(tr("page.seedling.group.sam"))

        sam_group.add_widget(QLabel(tr("page.seedling.label.prompt")))
        self.edit_prompt = LineEdit()
        self.edit_prompt.setText("seedling")
        self.edit_prompt.setMinimumWidth(100)
        sam_group.add_widget(self.edit_prompt)

        self.btn_detect = PrimaryPushButton(tr("page.seedling.btn.detect"))
        self.btn_detect.clicked.connect(self.sigDetect.emit)
        sam_group.add_widget(self.btn_detect)

        self.add_group(sam_group)

        # --- Slice Parameters Group ---
        slice_group = PageGroup(tr("page.seedling.group.slice"))

        slice_group.add_widget(QLabel(tr("page.seedling.label.size")))
        self.spin_slice_size = SpinBox()
        self.spin_slice_size.setRange(256, 2048)
        self.spin_slice_size.setValue(640)
        self.spin_slice_size.setSingleStep(64)
        slice_group.add_widget(self.spin_slice_size)

        slice_group.add_widget(QLabel(tr("page.seedling.label.overlap")))
        self.spin_overlap = DoubleSpinBox()
        self.spin_overlap.setRange(0.0, 0.5)
        self.spin_overlap.setValue(0.2)
        self.spin_overlap.setSingleStep(0.05)
        slice_group.add_widget(self.spin_overlap)

        self.add_group(slice_group)

        # --- Tools Group ---
        tools_group = PageGroup(tr("page.seedling.group.tools"))

        self.btn_view = PushButton(tr("page.seedling.btn.view"))
        self.btn_view.setCheckable(True)
        self.btn_view.setChecked(True)
        tools_group.add_widget(self.btn_view)

        self.btn_add = PushButton(tr("page.seedling.btn.add"))
        self.btn_add.setCheckable(True)
        tools_group.add_widget(self.btn_add)

        self.btn_move = PushButton(tr("page.seedling.btn.move"))
        self.btn_move.setCheckable(True)
        tools_group.add_widget(self.btn_move)

        self.btn_delete = PushButton(tr("page.seedling.btn.delete"))
        self.btn_delete.setCheckable(True)
        tools_group.add_widget(self.btn_delete)

        self.btn_undo = PushButton(tr("page.seedling.btn.undo"))
        tools_group.add_widget(self.btn_undo)

        self.add_group(tools_group)

        # --- Save Group ---
        save_group = PageGroup(tr("page.seedling.group.save"))

        self.btn_save = PushButton(tr("page.common.save"))
        self.btn_save.clicked.connect(self.sigSave.emit)
        save_group.add_widget(self.btn_save)

        self.add_group(save_group)

        self.add_stretch()
