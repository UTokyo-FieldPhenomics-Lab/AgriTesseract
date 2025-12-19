"""
Ribbon Bar component for EasyPlantFieldID GUI.

This module provides an Office-style Ribbon toolbar with tabbed interface,
where each tab contains controls and parameters for its corresponding function.

The Ribbon consists of:
- Tab buttons at the top (Subplot, Seedling, Rename, TimeSeries, Annotate)
- Content area below showing controls for the selected tab
"""

from typing import Optional, Dict

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabBar,
    QStackedWidget,
    QPushButton,
    QLabel,
    QLineEdit,
    QSpinBox,
    QDoubleSpinBox,
    QComboBox,
    QCheckBox,
    QFrame,
    QSizePolicy,
    QGroupBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from loguru import logger


class RibbonGroup(QGroupBox):
    """
    A group of controls within a ribbon tab.

    This is similar to the grouped sections in Microsoft Office Ribbon.

    Parameters
    ----------
    title : str
        Title of the group.
    parent : QWidget, optional
        Parent widget.
    """

    def __init__(self, title: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #c0c0c0;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 8px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 5px;
                color: #505050;
            }
        """)

        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 16, 8, 8)
        self._layout.setSpacing(8)

    def add_widget(self, widget: QWidget) -> None:
        """Add a widget to the group."""
        self._layout.addWidget(widget)

    def add_stretch(self) -> None:
        """Add stretch to the group layout."""
        self._layout.addStretch()


class RibbonTabContent(QWidget):
    """
    Base class for ribbon tab content.

    Each tab module should subclass this to provide its controls.

    Parameters
    ----------
    parent : QWidget, optional
        Parent widget.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.setSpacing(8)

        self.setMinimumHeight(80)
        self.setMaximumHeight(100)

    def add_group(self, group: RibbonGroup) -> None:
        """Add a ribbon group to this tab."""
        self._layout.addWidget(group)

    def add_stretch(self) -> None:
        """Add stretch at the end."""
        self._layout.addStretch()


class SubplotTabContent(RibbonTabContent):
    """
    Ribbon content for Subplot Generation tab.

    Controls:
    - Load Image, Load Boundary SHP
    - Definition mode (rows/cols or size)
    - Parameters (width, height, spacing)
    - Preview, Generate buttons
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
        file_group = RibbonGroup("文件")

        self.btn_load_image = QPushButton("加载影像")
        self.btn_load_image.clicked.connect(self.sigLoadImage.emit)
        file_group.add_widget(self.btn_load_image)

        self.btn_load_boundary = QPushButton("加载边界SHP")
        self.btn_load_boundary.clicked.connect(self.sigLoadBoundary.emit)
        file_group.add_widget(self.btn_load_boundary)

        self.add_group(file_group)

        # --- Definition Group ---
        def_group = RibbonGroup("定义方式")

        self.combo_def_mode = QComboBox()
        self.combo_def_mode.addItems(["按行列数", "按尺寸(米)"])
        def_group.add_widget(self.combo_def_mode)

        self.add_group(def_group)

        # --- Parameters Group ---
        param_group = RibbonGroup("参数")

        # Row/Col or Width/Height
        param_group.add_widget(QLabel("列数/宽度:"))
        self.spin_cols = QSpinBox()
        self.spin_cols.setRange(1, 100)
        self.spin_cols.setValue(5)
        self.spin_cols.setMinimumWidth(60)
        param_group.add_widget(self.spin_cols)

        param_group.add_widget(QLabel("行数/高度:"))
        self.spin_rows = QSpinBox()
        self.spin_rows.setRange(1, 100)
        self.spin_rows.setValue(5)
        self.spin_rows.setMinimumWidth(60)
        param_group.add_widget(self.spin_rows)

        param_group.add_widget(QLabel("X间距:"))
        self.spin_x_spacing = QDoubleSpinBox()
        self.spin_x_spacing.setRange(-10, 100)
        self.spin_x_spacing.setValue(0.0)
        self.spin_x_spacing.setSuffix(" m")
        self.spin_x_spacing.setMinimumWidth(70)
        param_group.add_widget(self.spin_x_spacing)

        param_group.add_widget(QLabel("Y间距:"))
        self.spin_y_spacing = QDoubleSpinBox()
        self.spin_y_spacing.setRange(-10, 100)
        self.spin_y_spacing.setValue(0.0)
        self.spin_y_spacing.setSuffix(" m")
        self.spin_y_spacing.setMinimumWidth(70)
        param_group.add_widget(self.spin_y_spacing)

        self.add_group(param_group)

        # --- Actions Group ---
        action_group = RibbonGroup("操作")

        self.check_preview = QCheckBox("实时预览")
        self.check_preview.setChecked(True)
        action_group.add_widget(self.check_preview)

        self.btn_focus = QPushButton("聚焦旋转")
        action_group.add_widget(self.btn_focus)

        self.btn_generate = QPushButton("生成保存")
        self.btn_generate.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }"
        )
        self.btn_generate.clicked.connect(self.sigGenerate.emit)
        action_group.add_widget(self.btn_generate)

        self.add_group(action_group)

        self.add_stretch()


class SeedlingTabContent(RibbonTabContent):
    """
    Ribbon content for Seedling Position Detection tab.

    Controls:
    - SAM3 prompt input
    - Detect button
    - Slice parameters
    - Editing tools (add, move, delete)
    - Save button
    """

    sigDetect = Signal()
    sigSave = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for seedling detection."""
        # --- SAM3 Group ---
        sam_group = RibbonGroup("SAM3 检测")

        sam_group.add_widget(QLabel("提示词:"))
        self.edit_prompt = QLineEdit("seedling")
        self.edit_prompt.setMinimumWidth(100)
        sam_group.add_widget(self.edit_prompt)

        self.btn_detect = QPushButton("检测 ▶")
        self.btn_detect.setStyleSheet(
            "QPushButton { background-color: #2196F3; color: white; font-weight: bold; }"
        )
        self.btn_detect.clicked.connect(self.sigDetect.emit)
        sam_group.add_widget(self.btn_detect)

        self.add_group(sam_group)

        # --- Slice Parameters Group ---
        slice_group = RibbonGroup("切片参数")

        slice_group.add_widget(QLabel("大小:"))
        self.spin_slice_size = QSpinBox()
        self.spin_slice_size.setRange(256, 2048)
        self.spin_slice_size.setValue(640)
        self.spin_slice_size.setSingleStep(64)
        slice_group.add_widget(self.spin_slice_size)

        slice_group.add_widget(QLabel("重叠率:"))
        self.spin_overlap = QDoubleSpinBox()
        self.spin_overlap.setRange(0.0, 0.5)
        self.spin_overlap.setValue(0.2)
        self.spin_overlap.setSingleStep(0.05)
        slice_group.add_widget(self.spin_overlap)

        self.add_group(slice_group)

        # --- Tools Group ---
        tools_group = RibbonGroup("编辑工具")

        self.btn_view = QPushButton("🔍 查看")
        self.btn_view.setCheckable(True)
        self.btn_view.setChecked(True)
        tools_group.add_widget(self.btn_view)

        self.btn_add = QPushButton("➕ 添加")
        self.btn_add.setCheckable(True)
        tools_group.add_widget(self.btn_add)

        self.btn_move = QPushButton("✏️ 移动")
        self.btn_move.setCheckable(True)
        tools_group.add_widget(self.btn_move)

        self.btn_delete = QPushButton("❌ 删除")
        self.btn_delete.setCheckable(True)
        tools_group.add_widget(self.btn_delete)

        self.btn_undo = QPushButton("↩️ 撤销")
        tools_group.add_widget(self.btn_undo)

        self.add_group(tools_group)

        # --- Save Group ---
        save_group = RibbonGroup("保存")

        self.btn_save = QPushButton("保存 SHP")
        self.btn_save.clicked.connect(self.sigSave.emit)
        save_group.add_widget(self.btn_save)

        self.add_group(save_group)

        self.add_stretch()


class RenameTabContent(RibbonTabContent):
    """
    Ribbon content for Seedling ID Renaming tab.

    Controls:
    - Load SHP button
    - Ridge direction and RANSAC parameters
    - Detect ridges button
    - Numbering options
    - Save button
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for seedling renaming."""
        # --- File Group ---
        file_group = RibbonGroup("文件")

        self.btn_load_shp = QPushButton("加载苗位置SHP")
        file_group.add_widget(self.btn_load_shp)

        self.add_group(file_group)

        # --- Ridge Group ---
        ridge_group = RibbonGroup("垄检测")

        ridge_group.add_widget(QLabel("方向:"))
        self.combo_direction = QComboBox()
        self.combo_direction.addItems(["自动检测", "X方向", "Y方向"])
        ridge_group.add_widget(self.combo_direction)

        ridge_group.add_widget(QLabel("强度比:"))
        self.spin_strength = QSpinBox()
        self.spin_strength.setRange(1, 50)
        self.spin_strength.setValue(10)
        ridge_group.add_widget(self.spin_strength)

        self.btn_detect_ridge = QPushButton("检测垄")
        ridge_group.add_widget(self.btn_detect_ridge)

        self.add_group(ridge_group)

        # --- Numbering Group ---
        num_group = RibbonGroup("编号规则")

        num_group.add_widget(QLabel("格式:"))
        self.combo_format = QComboBox()
        self.combo_format.addItems(["垄号-苗号", "纯数字", "自定义"])
        num_group.add_widget(self.combo_format)

        self.btn_apply_numbering = QPushButton("应用编号")
        num_group.add_widget(self.btn_apply_numbering)

        self.add_group(num_group)

        # --- Save Group ---
        save_group = RibbonGroup("保存")

        self.btn_save = QPushButton("保存 SHP")
        save_group.add_widget(self.btn_save)

        self.add_group(save_group)

        self.add_stretch()


class TimeSeriesTabContent(RibbonTabContent):
    """
    Ribbon content for Time Series Cropping tab.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for time series cropping."""
        # --- File Group ---
        file_group = RibbonGroup("文件")

        self.btn_load_points = QPushButton("加载苗位置SHP")
        file_group.add_widget(self.btn_load_points)

        self.btn_add_date = QPushButton("添加日期 +")
        file_group.add_widget(self.btn_add_date)

        self.add_group(file_group)

        # --- Crop Parameters Group ---
        param_group = RibbonGroup("切块参数")

        param_group.add_widget(QLabel("尺寸类型:"))
        self.combo_size_type = QComboBox()
        self.combo_size_type.addItems(["实际尺寸(m)", "像素"])
        param_group.add_widget(self.combo_size_type)

        param_group.add_widget(QLabel("边长:"))
        self.spin_crop_size = QDoubleSpinBox()
        self.spin_crop_size.setRange(0.1, 100)
        self.spin_crop_size.setValue(1.0)
        param_group.add_widget(self.spin_crop_size)

        self.add_group(param_group)

        # --- Output Group ---
        output_group = RibbonGroup("输出")

        output_group.add_widget(QLabel("目录:"))
        self.edit_output_dir = QLineEdit()
        self.edit_output_dir.setMinimumWidth(150)
        output_group.add_widget(self.edit_output_dir)

        self.btn_browse = QPushButton("浏览...")
        output_group.add_widget(self.btn_browse)

        self.btn_start_crop = QPushButton("开始切块 ▶")
        self.btn_start_crop.setStyleSheet(
            "QPushButton { background-color: #4CAF50; color: white; font-weight: bold; }"
        )
        output_group.add_widget(self.btn_start_crop)

        self.add_group(output_group)

        self.add_stretch()


class AnnotateTabContent(RibbonTabContent):
    """
    Ribbon content for Annotation Training tab.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._init_controls()

    def _init_controls(self) -> None:
        """Initialize the controls for annotation and training."""
        # --- File Group ---
        file_group = RibbonGroup("文件")

        self.btn_load_images = QPushButton("📁 加载图片目录")
        file_group.add_widget(self.btn_load_images)

        self.btn_save = QPushButton("💾 保存")
        file_group.add_widget(self.btn_save)

        self.add_group(file_group)

        # --- Navigation Group ---
        nav_group = RibbonGroup("导航")

        self.btn_prev = QPushButton("⬅️ 上一张")
        nav_group.add_widget(self.btn_prev)

        self.label_progress = QLabel("0 / 0")
        self.label_progress.setMinimumWidth(60)
        self.label_progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        nav_group.add_widget(self.label_progress)

        self.btn_next = QPushButton("➡️ 下一张")
        nav_group.add_widget(self.btn_next)

        self.add_group(nav_group)

        # --- Annotation Tools Group ---
        tools_group = RibbonGroup("标注工具")

        self.btn_sam_click = QPushButton("🔵 SAM点击")
        self.btn_sam_click.setCheckable(True)
        tools_group.add_widget(self.btn_sam_click)

        self.btn_sam_prompt = QPushButton("📝 SAM提示词")
        self.btn_sam_prompt.setCheckable(True)
        tools_group.add_widget(self.btn_sam_prompt)

        self.btn_edit_polygon = QPushButton("✏️ 编辑")
        self.btn_edit_polygon.setCheckable(True)
        tools_group.add_widget(self.btn_edit_polygon)

        self.btn_delete_instance = QPushButton("❌ 删除")
        tools_group.add_widget(self.btn_delete_instance)

        self.add_group(tools_group)

        # --- Training Group ---
        train_group = RibbonGroup("模型训练")

        self.btn_train = QPushButton("🚀 训练 YOLO")
        self.btn_train.setStyleSheet(
            "QPushButton { background-color: #FF9800; color: white; font-weight: bold; }"
        )
        train_group.add_widget(self.btn_train)

        self.btn_switch_model = QPushButton("🔄 切换模型")
        train_group.add_widget(self.btn_switch_model)

        self.add_group(train_group)

        self.add_stretch()


class RibbonBar(QWidget):
    """
    Office-style Ribbon Bar with tabbed interface.

    The ribbon bar contains multiple tabs, each with its own set of controls
    relevant to the corresponding functionality.

    Signals
    -------
    sigTabChanged : Signal(int)
        Emitted when the active tab changes.

    Examples
    --------
    >>> ribbon = RibbonBar()
    >>> ribbon.sigTabChanged.connect(lambda idx: print(f"Tab changed to {idx}"))
    """

    sigTabChanged = Signal(int)

    # Tab indices
    TAB_SUBPLOT = 0
    TAB_SEEDLING = 1
    TAB_RENAME = 2
    TAB_TIMESERIES = 3
    TAB_ANNOTATE = 4

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        """
        Initialize the Ribbon Bar.

        Parameters
        ----------
        parent : QWidget, optional
            Parent widget.
        """
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        """Initialize the ribbon bar UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Tab Bar ---
        self.tab_bar = QTabBar()
        self.tab_bar.setExpanding(False)
        self.tab_bar.setDocumentMode(True)

        # Set tab style
        self.tab_bar.setStyleSheet("""
            QTabBar::tab {
                background: #f0f0f0;
                border: 1px solid #c0c0c0;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                padding: 8px 20px;
                margin-right: 2px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: white;
                border-bottom: 2px solid #4CAF50;
            }
            QTabBar::tab:hover:!selected {
                background: #e0e0e0;
            }
        """)

        # Add tabs
        self.tab_bar.addTab("小样地生成")
        self.tab_bar.addTab("苗位置检测")
        self.tab_bar.addTab("苗ID重命名")
        self.tab_bar.addTab("时间序列切块")
        self.tab_bar.addTab("标注训练")

        self.tab_bar.currentChanged.connect(self._on_tab_changed)

        layout.addWidget(self.tab_bar)

        # --- Content Area ---
        self.content_stack = QStackedWidget()
        self.content_stack.setStyleSheet("""
            QStackedWidget {
                background: white;
                border: 1px solid #c0c0c0;
                border-top: none;
            }
        """)

        # Add tab contents
        self.subplot_tab = SubplotTabContent()
        self.content_stack.addWidget(self.subplot_tab)

        self.seedling_tab = SeedlingTabContent()
        self.content_stack.addWidget(self.seedling_tab)

        self.rename_tab = RenameTabContent()
        self.content_stack.addWidget(self.rename_tab)

        self.timeseries_tab = TimeSeriesTabContent()
        self.content_stack.addWidget(self.timeseries_tab)

        self.annotate_tab = AnnotateTabContent()
        self.content_stack.addWidget(self.annotate_tab)

        layout.addWidget(self.content_stack)

    def _on_tab_changed(self, index: int) -> None:
        """Handle tab change."""
        self.content_stack.setCurrentIndex(index)
        self.sigTabChanged.emit(index)
        logger.debug(f"Ribbon tab changed to: {index}")

    def get_current_tab_index(self) -> int:
        """Get the current tab index."""
        return self.tab_bar.currentIndex()

    def get_subplot_tab(self) -> SubplotTabContent:
        """Get the subplot tab content widget."""
        return self.subplot_tab

    def get_seedling_tab(self) -> SeedlingTabContent:
        """Get the seedling tab content widget."""
        return self.seedling_tab

    def get_rename_tab(self) -> RenameTabContent:
        """Get the rename tab content widget."""
        return self.rename_tab

    def get_timeseries_tab(self) -> TimeSeriesTabContent:
        """Get the time series tab content widget."""
        return self.timeseries_tab

    def get_annotate_tab(self) -> AnnotateTabContent:
        """Get the annotate tab content widget."""
        return self.annotate_tab
