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
from src.gui.config import tr
from qfluentwidgets import (
    ComboBox,
    SpinBox,
    DoubleSpinBox,
    LineEdit,
    CheckBox,
    BodyLabel,
    BodyLabel,
    StrongBodyLabel,
    SubtitleLabel,
    ScrollArea,
    Theme,
    PrimaryPushButton,
    PushButton
)
from src.gui.config import cfg
from pathlib import Path
import darkdetect


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

    def add_row(self, label: str, widget: QWidget) -> None:
        """Add a row with label and widget."""
        self._layout.addRow(label, widget)


class SubplotPropertyPanel(QWidget):
    """Property panel content for Subplot Generation tab."""
    
    sigParamChanged = Signal()
    sigGenerate = Signal()
    sigReset = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self) -> None:
        """Initialize the UI."""
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(16)
        self.layout.setContentsMargins(14, 16, 14, 14)
        self.layout.setAlignment(Qt.AlignTop)

        # --- Layout Group ---
        self.layout.addWidget(StrongBodyLabel(tr("page.subplot.group.layout")))

        self.def_mode_group = QWidget()
        layout_def_mode = QVBoxLayout(self.def_mode_group)
        layout_def_mode.setContentsMargins(0, 0, 0, 0)
        layout_def_mode.setSpacing(8)

        self.lbl_def_mode = BodyLabel(tr("page.subplot.label.def_mode"))
        layout_def_mode.addWidget(self.lbl_def_mode)
        
        self.combo_def_mode = ComboBox()
        self.combo_def_mode.addItems([tr("page.subplot.combo.rc"), tr("page.subplot.combo.size")])

        layout_def_mode.addWidget(self.combo_def_mode)

        self.layout.addWidget(self.def_mode_group)

        # --- Dimensions Group ---
        # We use a Stacked Widget to switch between Row/Col and Width/Height inputs
        self.dim_stack = QStackedWidget()
        
        # Page 1: Rows / Cols
        self.page_rc = QWidget()
        layout_rc = QVBoxLayout(self.page_rc)
        layout_rc.setContentsMargins(0, 0, 0, 0)
        layout_rc.setSpacing(8)
        
        # Cols (Width count)
        self.lbl_cols = BodyLabel(tr("page.subplot.label.cols"))
        layout_rc.addWidget(self.lbl_cols)
        self.spin_cols = SpinBox()
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(5)
        layout_rc.addWidget(self.spin_cols)
        
        # Rows (Height count)
        self.lbl_rows = BodyLabel(tr("page.subplot.label.rows"))
        layout_rc.addWidget(self.lbl_rows)
        self.spin_rows = SpinBox()
        self.spin_rows.setRange(1, 100)
        self.spin_rows.setValue(5)
        layout_rc.addWidget(self.spin_rows)
        
        self.dim_stack.addWidget(self.page_rc)

        # Page 2: Width / Height (Size in meters)
        self.page_size = QWidget()
        layout_size = QVBoxLayout(self.page_size)
        layout_size.setContentsMargins(0, 0, 0, 0)
        layout_size.setSpacing(8)
        
        # Width
        self.lbl_width = BodyLabel(tr("page.subplot.label.width_m")) # Need to add this key or reuse "Width"
        layout_size.addWidget(self.lbl_width)
        self.spin_width = DoubleSpinBox()
        self.spin_width.setRange(0.1, 1000.0)
        self.spin_width.setValue(2.0)
        self.spin_width.setSuffix(" m")
        layout_size.addWidget(self.spin_width)
        
        # Height
        self.lbl_height = BodyLabel(tr("page.subplot.label.height_m")) # Need to add key
        layout_size.addWidget(self.lbl_height)
        self.spin_height = DoubleSpinBox()
        self.spin_height.setRange(0.1, 1000.0)
        self.spin_height.setValue(2.0)
        self.spin_height.setSuffix(" m")
        layout_size.addWidget(self.spin_height)
        
        self.dim_stack.addWidget(self.page_size)
        
        self.layout.addWidget(self.dim_stack)
        
        # X Spacing
        self.layout.addWidget(BodyLabel(tr("page.subplot.label.x_space")))
        self.spin_x_spacing = DoubleSpinBox()
        self.spin_x_spacing.setRange(-10, 100)
        self.spin_x_spacing.setValue(0.0)
        self.spin_x_spacing.setSuffix(" m")
        self.layout.addWidget(self.spin_x_spacing)

        # Y Spacing
        self.layout.addWidget(BodyLabel(tr("page.subplot.label.y_space")))
        self.spin_y_spacing = DoubleSpinBox()
        self.spin_y_spacing.setRange(-10, 100)
        self.spin_y_spacing.setValue(0.0)
        self.spin_y_spacing.setSuffix(" m")
        self.layout.addWidget(self.spin_y_spacing)
        
        self.layout.addSpacing(8)

        # --- Numbering Rules Group ---
        self.layout.addWidget(StrongBodyLabel(tr("prop.group.numbering")))

        self.layout.addWidget(BodyLabel(tr("prop.label.numbering_mode")))
        self.combo_numbering = ComboBox()
        self.combo_numbering.addItems([
            "行列命名 (R1C1, R1C2...)",
            "连续编号 (1, 2, 3...)",
            "蛇形编号",
            "自定义格式"
        ])
        self.layout.addWidget(self.combo_numbering)
        
        self.layout.addWidget(BodyLabel(tr("prop.label.start_row")))
        self.spin_start_row = SpinBox()
        self.spin_start_row.setRange(0, 1000)
        self.spin_start_row.setValue(1)
        self.layout.addWidget(self.spin_start_row)
        
        self.layout.addWidget(BodyLabel(tr("prop.label.start_col")))
        self.spin_start_col = SpinBox()
        self.spin_start_col.setRange(0, 1000)
        self.spin_start_col.setValue(1)
        self.layout.addWidget(self.spin_start_col)
        
        self.layout.addWidget(BodyLabel(tr("prop.label.prefix")))
        self.edit_prefix = LineEdit()
        self.edit_prefix.setPlaceholderText("例如: Plot_")
        self.layout.addWidget(self.edit_prefix)
        
        self.layout.addWidget(BodyLabel(tr("prop.label.suffix")))
        self.edit_suffix = LineEdit()
        self.edit_suffix.setPlaceholderText("例如: _2024")
        self.layout.addWidget(self.edit_suffix)

        self.layout.addStretch()

        # --- Action Buttons ---
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)
        
        self.btn_reset = PushButton(tr("btn.reset")) # Need key
        self.btn_reset.clicked.connect(self.sigReset)
        action_layout.addWidget(self.btn_reset)
        
        self.btn_generate = PrimaryPushButton(tr("page.subplot.btn.save"))
        self.btn_generate.clicked.connect(self.sigGenerate)
        action_layout.addWidget(self.btn_generate)
        
        self.layout.addLayout(action_layout)

    def _connect_signals(self):
        """Connect internal signals."""
        self.combo_def_mode.currentIndexChanged.connect(self._on_mode_changed)
        
        # Param changed signals for auto-preview
        self.spin_cols.valueChanged.connect(self.sigParamChanged)
        self.spin_rows.valueChanged.connect(self.sigParamChanged)
        self.spin_width.valueChanged.connect(self.sigParamChanged)
        self.spin_height.valueChanged.connect(self.sigParamChanged)
        self.spin_x_spacing.valueChanged.connect(self.sigParamChanged)
        self.spin_y_spacing.valueChanged.connect(self.sigParamChanged)
        self.combo_def_mode.currentIndexChanged.connect(self.sigParamChanged)

    def _on_mode_changed(self, index: int):
        """Switch input stack based on mode."""
        self.dim_stack.setCurrentIndex(index)
        # Update labels if needed or handled by stack visibility


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
        self.setObjectName("PropertyPanel")
        self._init_ui()
        self.setQss()
        cfg.themeChanged.connect(self.setQss)

    def _init_ui(self) -> None:
        """Initialize the UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Header
        header_label = QLabel(tr("prop.title"))
        header_label.setObjectName("PropertyTitle")
        layout.addWidget(header_label)

        # Scroll area for content
        scroll_area = ScrollArea()
        scroll_area.setObjectName("PropertyScroll")
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Make transparent
        scroll_area.setStyleSheet("background-color: transparent; border: none;")
        scroll_area.viewport().setStyleSheet("background-color: transparent;")

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

    def setQss(self):
        """Apply QSS."""
        theme = cfg.themeMode.value
        if theme == Theme.AUTO:
            theme_name = "dark" if darkdetect.isDark() else "light"
        else:
            theme_name = theme.value.lower()
            
        qss_path = Path(__file__).parent.parent / "resource" / "qss" / theme_name / "property_panel.qss"
        if qss_path.exists():
            with open(qss_path, encoding='utf-8') as f:
                self.setStyleSheet(f.read())
