"""
Annotation Page.
"""

from typing import Optional

from typing import Optional
from PySide6.QtWidgets import QWidget, QLabel
from PySide6.QtCore import Qt
from qfluentwidgets import (
    PushButton,
    PrimaryPushButton,
)

from src.gui.interfaces.map_interface import MapInterface
from src.gui.interfaces.base_interface import PageGroup
from src.gui.config import tr


class AnnotateInterface(MapInterface):
    """
    Interface content for Annotation Training.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for annotation and training."""
        # --- File Group ---
        file_group = PageGroup(tr("page.common.file"))

        self.btn_load_images = PushButton(tr("page.anno.btn.load_img"))
        file_group.add_widget(self.btn_load_images)

        self.btn_save = PushButton(tr("page.common.save"))
        file_group.add_widget(self.btn_save)

        self.add_group(file_group)

        # --- Navigation Group ---
        nav_group = PageGroup(tr("page.anno.group.nav"))

        self.btn_prev = PushButton(tr("page.anno.btn.prev"))
        nav_group.add_widget(self.btn_prev)

        self.label_progress = QLabel("0 / 0")
        self.label_progress.setMinimumWidth(60)
        self.label_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_group.add_widget(self.label_progress)

        self.btn_next = PushButton(tr("page.anno.btn.next"))
        nav_group.add_widget(self.btn_next)

        self.add_group(nav_group)

        # --- Annotation Tools Group ---
        tools_group = PageGroup(tr("page.anno.group.tools"))

        self.btn_sam_click = PushButton(tr("page.anno.btn.sam_click"))
        self.btn_sam_click.setCheckable(True)
        tools_group.add_widget(self.btn_sam_click)

        self.btn_sam_prompt = PushButton(tr("page.anno.btn.sam_prompt"))
        self.btn_sam_prompt.setCheckable(True)
        tools_group.add_widget(self.btn_sam_prompt)

        self.btn_edit_polygon = PushButton(tr("page.anno.btn.edit"))
        self.btn_edit_polygon.setCheckable(True)
        tools_group.add_widget(self.btn_edit_polygon)

        self.btn_delete_instance = PushButton(tr("page.seedling.btn.delete"))
        tools_group.add_widget(self.btn_delete_instance)

        self.add_group(tools_group)

        # --- Training Group ---
        train_group = PageGroup(tr("page.anno.group.train"))

        self.btn_train = PrimaryPushButton(tr("page.anno.btn.train"))
        train_group.add_widget(self.btn_train)

        self.btn_switch_model = PushButton(tr("page.anno.btn.switch"))
        train_group.add_widget(self.btn_switch_model)

        self.add_group(train_group)

        self.add_stretch()
