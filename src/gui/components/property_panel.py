"""
Property Panel component for AgriTesseract GUI.

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
    StrongBodyLabel,
    SubtitleLabel,
    ScrollArea,
    Theme,
    PrimaryPushButton,
    PushButton,
    Pivot,
    InfoBadge,
)
from src.gui.config import cfg
from pathlib import Path
import darkdetect


class PropBase(QWidget):
    """Base class for property widgets with a label and a control."""

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.layout.setSpacing(4)

        self.label = BodyLabel(title)
        self.layout.addWidget(self.label)

    def add_widget(self, widget: QWidget):
        self.layout.addWidget(widget)


class PropComboBox(PropBase):
    """Property widget with a ComboBox."""

    currentIndexChanged = Signal(int)

    def __init__(
        self, title: str, items: list[str] = None, parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(title, parent)
        self.combo = ComboBox()
        if items:
            self.combo.addItems(items)
        self.combo.currentIndexChanged.connect(self.currentIndexChanged)
        self.add_widget(self.combo)

    def setCurrentIndex(self, index: int):
        self.combo.setCurrentIndex(index)

    def currentIndex(self) -> int:
        return self.combo.currentIndex()

    def addItems(self, items: list[str]):
        self.combo.addItems(items)


class PropSpinBox(PropBase):
    """Property widget with a SpinBox."""

    valueChanged = Signal(int)

    def __init__(
        self,
        title: str,
        range: tuple[int, int] = (0, 100),
        value: int = 0,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)
        self.spin = SpinBox()
        self.spin.setRange(*range)
        self.spin.setValue(value)
        self.spin.valueChanged.connect(self.valueChanged)
        self.add_widget(self.spin)

    def setValue(self, value: int):
        self.spin.setValue(value)

    def value(self) -> int:
        return self.spin.value()


class PropDoubleSpinBox(PropBase):
    """Property widget with a DoubleSpinBox."""

    valueChanged = Signal(float)

    def __init__(
        self,
        title: str,
        range: tuple[float, float] = (0.0, 100.0),
        value: float = 0.0,
        suffix: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)
        self.spin = DoubleSpinBox()
        self.spin.setRange(*range)
        self.spin.setValue(value)
        if suffix:
            self.spin.setSuffix(suffix)
        self.spin.valueChanged.connect(self.valueChanged)
        self.add_widget(self.spin)

    def setValue(self, value: float):
        self.spin.setValue(value)

    def value(self) -> float:
        return self.spin.value()


class PropLineEdit(PropBase):
    """Property widget with a LineEdit."""

    textChanged = Signal(str)

    def __init__(
        self, title: str, placeholder: str = "", parent: Optional[QWidget] = None
    ) -> None:
        super().__init__(title, parent)
        self.edit = LineEdit()
        if placeholder:
            self.edit.setPlaceholderText(placeholder)
        self.edit.textChanged.connect(self.textChanged)
        self.add_widget(self.edit)

    def text(self) -> str:
        return self.edit.text()

    def setText(self, text: str):
        self.edit.setText(text)


class PropInfo(PropBase):
    """Property widget with an InfoBadge."""

    def __init__(
        self,
        title: str,
        value: str = "",
        badge_type="info",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)
        # InfoBadge in qfluentwidgets usually takes just parent.
        # Using a custom wrapper or just BodyLabel/InfoBadge if available.
        # Assuming InfoBadge exists and works like a label or small indicator.
        # If InfoBadge is not suitable for generic text, we might use BodyLabel with styling.
        self.badge = InfoBadge.info(value)
        # badge_type: info, success, warning, error, attribution
        # Adjust method based on type if needed, but 'info' static method is common pattern in Fluent?
        # Actually InfoBadge init is InfoBadge(text, parent, type).
        # We will assume generic usage.

        # Re-creating simple badge logic if InfoBadge static methods differ
        # Using standard instantiation
        self.badge = InfoBadge(text=value)
        self.layout.addWidget(self.badge)  # add_widget wrapper

    def setText(self, text: str):
        self.badge.setText(text)


class PropertyGroup(QGroupBox):
    """
    A collapsible group of properties.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)
        self.setCheckable(True)
        self.setChecked(True)
        self._layout = QFormLayout(self)
        self._layout.setContentsMargins(8, 16, 8, 8)
        self._layout.setSpacing(6)

    def add_row(self, label: str, widget: QWidget) -> None:
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
        """
        Initialize the UI.

        Layout Structure:
        SubplotPropertyPanel (QVBoxLayout)
        ├── pivot (Pivot)
        ├── content_stack (QStackedWidget)
        │   ├── stack_layout (QWidget, QVBoxLayout)
        │   │   ├── prop_def_mode (PropComboBox)
        │   │   ├── prop_cols (PropSpinBox) [Visible if mode=RC]
        │   │   ├── prop_rows (PropSpinBox) [Visible if mode=RC]
        │   │   ├── prop_width (PropDoubleSpinBox) [Visible if mode=Size]
        │   │   ├── prop_height (PropDoubleSpinBox) [Visible if mode=Size]
        │   │   ├── prop_x_spacing (PropDoubleSpinBox)
        │   │   └── prop_y_spacing (PropDoubleSpinBox)
        │   └── stack_numbering (QWidget, QVBoxLayout)
        │       ├── prop_mode (PropComboBox)
        │       ├── prop_start_row (PropSpinBox)
        │       ├── prop_start_col (PropSpinBox)
        │       ├── prop_prefix (PropLineEdit)
        │       └── prop_suffix (PropLineEdit)
        └── action_layout (QHBoxLayout)
            ├── btn_reset (PushButton)
            └── btn_generate (PrimaryPushButton)
        """
        self.layout = QVBoxLayout(self)
        self.layout.setSpacing(8)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setAlignment(Qt.AlignTop)

        # --- Pivot Navigation ---
        self.pivot = Pivot(self)
        self.layout.addWidget(self.pivot)

        # --- Content Stack ---
        self.content_stack = QStackedWidget(self)
        self.layout.addWidget(self.content_stack)

        # ==========================================
        # Stack 1: Layout Settings
        # ==========================================
        # --- Layout Group Content (Def Mode, Dim, Spacing) ---
        self.stack_layout = QWidget()

        stack_layout_inner = QVBoxLayout(self.stack_layout)
        stack_layout_inner.setContentsMargins(0, 0, 0, 0)
        stack_layout_inner.setSpacing(16)
        stack_layout_inner.setAlignment(Qt.AlignTop)

        # --- Def Mode Group ---

        self.prop_def_mode = PropComboBox(
            title=tr("page.subplot.label.def_mode"),
            items=[tr("page.subplot.combo.rc"), tr("page.subplot.combo.size")],
        )
        # Map internal widget
        self.combo_def_mode = self.prop_def_mode.combo
        stack_layout_inner.addWidget(self.prop_def_mode)

        # --- Dimensions Group ---
        # Rows / Cols
        self.prop_cols = PropSpinBox(
            title=tr("page.subplot.label.cols"), range=(1, 100), value=5
        )
        self.spin_cols = self.prop_cols.spin
        stack_layout_inner.addWidget(self.prop_cols)

        self.prop_rows = PropSpinBox(
            title=tr("page.subplot.label.rows"), range=(1, 100), value=5
        )
        self.spin_rows = self.prop_rows.spin
        stack_layout_inner.addWidget(self.prop_rows)

        # Width / Height (Size in meters)
        self.prop_width = PropDoubleSpinBox(
            title=tr("page.subplot.label.width_m"),
            range=(0.1, 1000.0),
            value=2.0,
            suffix=" m",
        )
        self.spin_width = self.prop_width.spin
        stack_layout_inner.addWidget(self.prop_width)

        self.prop_height = PropDoubleSpinBox(
            title=tr("page.subplot.label.height_m"),
            range=(0.1, 1000.0),
            value=2.0,
            suffix=" m",
        )
        self.spin_height = self.prop_height.spin
        stack_layout_inner.addWidget(self.prop_height)

        # Initial visibility state
        self.prop_width.hide()
        self.prop_height.hide()

        # X Spacing
        self.prop_x_spacing = PropDoubleSpinBox(
            title=tr("page.subplot.label.x_space"),
            range=(-10, 100),
            value=0.0,
            suffix=" m",
        )
        self.spin_x_spacing = self.prop_x_spacing.spin
        stack_layout_inner.addWidget(self.prop_x_spacing)

        # Y Spacing
        self.prop_y_spacing = PropDoubleSpinBox(
            title=tr("page.subplot.label.y_space"),
            range=(-10, 100),
            value=0.0,
            suffix=" m",
        )
        self.spin_y_spacing = self.prop_y_spacing.spin
        stack_layout_inner.addWidget(self.prop_y_spacing)

        self.prop_keep = PropComboBox(
            title=tr("page.subplot.label.keep"),
            items=[
                tr("page.subplot.keep.all"),
                tr("page.subplot.keep.touch"),
                tr("page.subplot.keep.inside"),
            ],
        )
        self.combo_keep = self.prop_keep.combo
        self.combo_keep.setCurrentIndex(0)
        stack_layout_inner.addWidget(self.prop_keep)

        self.content_stack.addWidget(self.stack_layout)

        # ==========================================
        # Stack 2: Numbering Rules
        # ==========================================
        self.stack_numbering = QWidget()
        stack_numbering_inner = QVBoxLayout(self.stack_numbering)
        stack_numbering_inner.setContentsMargins(0, 0, 0, 0)
        stack_numbering_inner.setSpacing(16)
        stack_numbering_inner.setAlignment(Qt.AlignTop)

        self.prop_mode = PropComboBox(
            title=tr("prop.label.numbering_mode"),
            items=[
                "行列命名 (R1C1, R1C2...)",
                "连续编号 (1, 2, 3...)",
                "蛇形编号",
                "自定义格式",
            ],
        )
        self.combo_numbering = self.prop_mode.combo
        stack_numbering_inner.addWidget(self.prop_mode)

        self.prop_start_row = PropSpinBox(tr("prop.label.start_row"), (0, 1000), 1)
        self.spin_start_row = self.prop_start_row.spin
        stack_numbering_inner.addWidget(self.prop_start_row)

        self.prop_start_col = PropSpinBox(tr("prop.label.start_col"), (0, 1000), 1)
        self.spin_start_col = self.prop_start_col.spin
        stack_numbering_inner.addWidget(self.prop_start_col)

        self.prop_prefix = PropLineEdit(tr("prop.label.prefix"), "例如: Plot_")
        self.edit_prefix = self.prop_prefix.edit
        stack_numbering_inner.addWidget(self.prop_prefix)

        self.prop_suffix = PropLineEdit(tr("prop.label.suffix"), "例如: _2024")
        self.edit_suffix = self.prop_suffix.edit
        stack_numbering_inner.addWidget(self.prop_suffix)

        self.content_stack.addWidget(self.stack_numbering)

        # --- Setup Pivot ---
        self.pivot.addItem(routeKey="layout", text=tr("page.subplot.group.layout"))
        self.pivot.addItem(routeKey="numbering", text=tr("prop.group.numbering"))
        self.pivot.currentItemChanged.connect(
            lambda k: self.content_stack.setCurrentIndex(0 if k == "layout" else 1)
        )
        self.pivot.setCurrentItem("layout")

        # --- Action Buttons ---
        action_layout = QHBoxLayout()
        action_layout.setSpacing(8)

        self.btn_reset = PushButton(tr("page.subplot.btn.reset"))  # Need key
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
        self.combo_keep.currentIndexChanged.connect(self.sigParamChanged)
        self.combo_def_mode.currentIndexChanged.connect(self.sigParamChanged)

    def _on_mode_changed(self, index: int):
        """Switch input visibility based on mode."""
        is_rc = index == 0
        self.prop_cols.setVisible(is_rc)
        self.prop_rows.setVisible(is_rc)
        self.prop_width.setVisible(not is_rc)
        self.prop_height.setVisible(not is_rc)
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

        self.label_model_status = QLabel(
            tr("prop.label.model_status")
        )  # This might need dynamic update
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

        qss_path = (
            Path(__file__).parent.parent
            / "resource"
            / "qss"
            / theme_name
            / "property_panel.qss"
        )
        if qss_path.exists():
            with open(qss_path, encoding="utf-8") as f:
                self.setStyleSheet(f.read())
