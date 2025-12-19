"""
Property Panel component for EasyPlantFieldID GUI.

This module provides a property/parameter panel that displays
context-specific options based on the current active tab.

The panel shows:
- Tab-specific parameters and settings
- Selected layer properties
- Additional configuration options
"""

from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QScrollArea,
    QLabel,
    QStackedWidget,
    QGroupBox,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QPushButton,
    QFormLayout,
)
from PySide6.QtCore import Qt, Signal
from loguru import logger

from src.gui.i18n import tr


class PropertyGroup(QGroupBox):
    """
    A collapsible group of properties.

    Parameters
    ----------
    title : str
        Title of the group.
    parent : QWidget, optional
        Parent widget.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)

        self._layout = QFormLayout(self)
        self._layout.setContentsMargins(8, 16, 8, 8)
        self._layout.setSpacing(6)

        # Style
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px;
                color: #505050;
            }
        """)

    def add_row(self, label: str, widget: QWidget) -> None:
        """Add a row with label and widget."""
        self._layout.addRow(label, widget)


class SubplotPropertyPanel(QWidget):
    """Property panel content for Subplot Generation tab."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Numbering Rules Group
        numbering_group = PropertyGroup(tr("prop.group.numbering"))

        self.combo_numbering = QComboBox()
        self.combo_numbering.addItems([
            "行列命名 (R1C1, R1C2...)",
            "连续编号 (1, 2, 3...)",
            "蛇形编号",
            "自定义格式"
        ])
        numbering_group.add_row(tr("prop.label.numbering_mode"), self.combo_numbering)

        self.spin_start_row = QSpinBox()
        self.spin_start_row.setRange(0, 1000)
        self.spin_start_row.setValue(1)
        numbering_group.add_row(tr("prop.label.start_row"), self.spin_start_row)

        self.spin_start_col = QSpinBox()
        self.spin_start_col.setRange(0, 1000)
        self.spin_start_col.setValue(1)
        numbering_group.add_row(tr("prop.label.start_col"), self.spin_start_col)

        self.edit_prefix = QLineEdit()
        self.edit_prefix.setPlaceholderText("例如: Plot_")
        numbering_group.add_row(tr("prop.label.prefix"), self.edit_prefix)

        self.edit_suffix = QLineEdit()
        self.edit_suffix.setPlaceholderText("例如: _2024")
        numbering_group.add_row(tr("prop.label.suffix"), self.edit_suffix)

        layout.addWidget(numbering_group)

        # Rotation Group
        rotation_group = PropertyGroup(tr("prop.group.rotation"))

        self.spin_rotation = QDoubleSpinBox()
        self.spin_rotation.setRange(-180, 180)
        self.spin_rotation.setValue(0)
        self.spin_rotation.setSuffix("°")
        rotation_group.add_row(tr("prop.label.rotation"), self.spin_rotation)

        self.check_auto_rotate = QCheckBox(tr("prop.check.auto_rotate"))
        self.check_auto_rotate.setChecked(True)
        rotation_group.add_row("", self.check_auto_rotate)

        layout.addWidget(rotation_group)

        # Add stretch
        layout.addStretch()


class SeedlingPropertyPanel(QWidget):
    """Property panel content for Seedling Detection tab."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Detection Settings Group
        detect_group = PropertyGroup(tr("prop.group.detect"))

        self.spin_confidence = QDoubleSpinBox()
        self.spin_confidence.setRange(0.1, 1.0)
        self.spin_confidence.setValue(0.5)
        self.spin_confidence.setSingleStep(0.05)
        detect_group.add_row(tr("prop.label.confidence"), self.spin_confidence)

        self.spin_iou = QDoubleSpinBox()
        self.spin_iou.setRange(0.1, 0.9)
        self.spin_iou.setValue(0.4)
        self.spin_iou.setSingleStep(0.05)
        detect_group.add_row(tr("prop.label.nms_iou"), self.spin_iou)

        layout.addWidget(detect_group)

        # Statistics Group
        stats_group = PropertyGroup(tr("prop.group.stats"))

        self.label_total = QLabel("0")
        stats_group.add_row(tr("prop.label.total"), self.label_total)

        self.label_selected = QLabel("0")
        stats_group.add_row(tr("prop.label.selected"), self.label_selected)

        layout.addWidget(stats_group)

        layout.addStretch()


class RenamePropertyPanel(QWidget):
    """Property panel content for ID Renaming tab."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # RANSAC Parameters Group
        ransac_group = PropertyGroup(tr("prop.group.ransac"))

        self.spin_distance_thresh = QDoubleSpinBox()
        self.spin_distance_thresh.setRange(0.1, 50)
        self.spin_distance_thresh.setValue(3.0)
        ransac_group.add_row(tr("prop.label.dist_thresh"), self.spin_distance_thresh)

        self.spin_height_thresh = QDoubleSpinBox()
        self.spin_height_thresh.setRange(1, 100)
        self.spin_height_thresh.setValue(20.0)
        ransac_group.add_row(tr("prop.label.height_thresh"), self.spin_height_thresh)

        layout.addWidget(ransac_group)

        # Numbering Group
        numbering_group = PropertyGroup(tr("prop.group.numbering_opt"))

        self.combo_order = QComboBox()
        self.combo_order.addItems(["从小到大", "从大到小"])
        numbering_group.add_row(tr("prop.label.order"), self.combo_order)

        self.spin_start_id = QSpinBox()
        self.spin_start_id.setRange(0, 10000)
        self.spin_start_id.setValue(1)
        numbering_group.add_row(tr("prop.label.start_id"), self.spin_start_id)

        layout.addWidget(numbering_group)

        # Ridge Statistics Group
        ridge_stats_group = PropertyGroup(tr("prop.group.ridge_stats"))

        self.label_ridge_count = QLabel("0")
        ridge_stats_group.add_row(tr("prop.label.ridge_count"), self.label_ridge_count)

        self.label_plant_count = QLabel("0")
        ridge_stats_group.add_row(tr("prop.label.plant_count"), self.label_plant_count)

        layout.addWidget(ridge_stats_group)

        layout.addStretch()


class TimeSeriesPropertyPanel(QWidget):
    """Property panel content for Time Series tab."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Data Sources Group
        data_group = PropertyGroup(tr("prop.group.data"))

        self.label_date_count = QLabel("0")
        data_group.add_row(tr("prop.label.date_count"), self.label_date_count)

        self.label_point_count = QLabel("0")
        data_group.add_row(tr("prop.label.point_count"), self.label_point_count)

        layout.addWidget(data_group)

        # Output Options Group
        output_group = PropertyGroup(tr("prop.group.output"))

        self.combo_format = QComboBox()
        self.combo_format.addItems(["PNG", "JPG", "TIFF"])
        output_group.add_row(tr("prop.label.format"), self.combo_format)

        self.check_create_subfolders = QCheckBox()
        self.check_create_subfolders.setChecked(True)
        output_group.add_row(tr("prop.check.subfolders"), self.check_create_subfolders)

        layout.addWidget(output_group)

        layout.addStretch()


class AnnotatePropertyPanel(QWidget):
    """Property panel content for Annotation Training tab."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Image Adjustment Group
        adjust_group = PropertyGroup(tr("prop.group.adjust"))

        self.spin_brightness = QDoubleSpinBox()
        self.spin_brightness.setRange(0.0, 2.0)
        self.spin_brightness.setValue(1.0)
        self.spin_brightness.setSingleStep(0.1)
        adjust_group.add_row(tr("prop.label.brightness"), self.spin_brightness)

        self.spin_contrast = QDoubleSpinBox()
        self.spin_contrast.setRange(0.0, 2.0)
        self.spin_contrast.setValue(1.0)
        self.spin_contrast.setSingleStep(0.1)
        adjust_group.add_row(tr("prop.label.contrast"), self.spin_contrast)

        self.spin_gamma = QDoubleSpinBox()
        self.spin_gamma.setRange(0.1, 3.0)
        self.spin_gamma.setValue(1.0)
        self.spin_gamma.setSingleStep(0.1)
        adjust_group.add_row(tr("prop.label.gamma"), self.spin_gamma)

        layout.addWidget(adjust_group)

        # Instance List Group
        instance_group = PropertyGroup(tr("prop.group.instance"))

        self.label_instance_count = QLabel("0")
        instance_group.add_row(tr("prop.label.current_img"), self.label_instance_count)

        layout.addWidget(instance_group)

        # Class Management Group
        class_group = PropertyGroup(tr("prop.group.class"))

        self.combo_current_class = QComboBox()
        self.combo_current_class.addItems(["leaf", "stem", "background"])
        class_group.add_row(tr("prop.label.current_class"), self.combo_current_class)

        self.btn_add_class = QPushButton(tr("prop.btn.add_class"))
        class_group.add_row("", self.btn_add_class)

        layout.addWidget(class_group)

        # Training Status Group
        train_group = PropertyGroup(tr("prop.group.train"))

        self.label_annotated_count = QLabel("0 / 0")
        train_group.add_row(tr("prop.label.annotated"), self.label_annotated_count)

        self.label_model_status = QLabel(tr("prop.label.model_status")) # This might need dynamic update
        train_group.add_row(tr("prop.label.model_status"), self.label_model_status)

        layout.addWidget(train_group)

        layout.addStretch()


class PropertyPanel(QWidget):
    """
    Property panel that shows context-specific options.

    The panel content changes based on the current active tab.

    Examples
    --------
    >>> panel = PropertyPanel()
    >>> panel.set_current_tab(0)  # Show subplot properties
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the Property Panel.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header
        header_label = QLabel(tr("prop.title"))
        header_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        layout.addWidget(header_label)

        # Scroll area for content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)

        # Stacked widget for different tab contents
        self._content_stack = QStackedWidget()

        # Add tab-specific panels
        self._subplot_panel = SubplotPropertyPanel()
        self._content_stack.addWidget(self._subplot_panel)

        self._seedling_panel = SeedlingPropertyPanel()
        self._content_stack.addWidget(self._seedling_panel)

        self._rename_panel = RenamePropertyPanel()
        self._content_stack.addWidget(self._rename_panel)

        self._timeseries_panel = TimeSeriesPropertyPanel()
        self._content_stack.addWidget(self._timeseries_panel)

        self._annotate_panel = AnnotatePropertyPanel()
        self._content_stack.addWidget(self._annotate_panel)

        scroll_area.setWidget(self._content_stack)
        layout.addWidget(scroll_area)

        # Set minimum width
        self.setMinimumWidth(180)
        self.setMaximumWidth(300)

    def set_current_tab(self, index: int) -> None:
        """
        Set the current tab to show corresponding properties.

        Parameters
        ----------
        index : int
            Tab index (0-4).
        """
        if 0 <= index < self._content_stack.count():
            self._content_stack.setCurrentIndex(index)
            logger.debug(f"Property panel switched to tab {index}")

    def get_subplot_panel(self) -> SubplotPropertyPanel:
        """Get the subplot property panel."""
        return self._subplot_panel

    def get_seedling_panel(self) -> SeedlingPropertyPanel:
        """Get the seedling property panel."""
        return self._seedling_panel

    def get_rename_panel(self) -> RenamePropertyPanel:
        """Get the rename property panel."""
        return self._rename_panel

    def get_timeseries_panel(self) -> TimeSeriesPropertyPanel:
        """Get the time series property panel."""
        return self._timeseries_panel

    def get_annotate_panel(self) -> AnnotatePropertyPanel:
        """Get the annotate property panel."""
        return self._annotate_panel
