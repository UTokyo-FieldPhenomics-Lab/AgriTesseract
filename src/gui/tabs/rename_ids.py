"""
ID Renaming Page with SegmentedWidget top tabs.
"""

from typing import Any, Optional
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyqtgraph as pg
from shapely.geometry import LineString, MultiLineString, MultiPoint

from PySide6.QtCore import Qt, Slot, Signal, QTimer, QEvent
from PySide6.QtGui import QHideEvent
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSizePolicy,
    QStackedWidget,
    QFileDialog,
)
from qfluentwidgets import (
    SegmentedWidget,
    CommandBar,
    PushButton,
    ToggleButton,
    PrimaryPushButton,
    ComboBox,
    SpinBox,
    DoubleSpinBox,
    BodyLabel,
    CheckBox,
    InfoBar,
    InfoBarIcon,
    Flyout,
    MessageBox,
    qrouter,
)

from src.gui.components.base_interface import TabInterface
from src.gui.components.bottom_panel import BottomPanelFigure
from src.gui.config import tr
from src.utils.rename_ids.boundary import (
    align_boundary_crs,
    build_effective_mask,
    compute_boundary_axes,
)
from src.utils.rename_ids.io import load_points_data, normalize_input_points
from src.utils.rename_ids.ridge_direction import (
    compute_rotation_angle_deg,
    normalize_direction_vector,
    resolve_direction_vector,
)
from src.utils.rename_ids.ridge_detection_controller import RidgeDetectionController
from src.utils.rename_ids.ridge_ordering_controller import RidgeOrderingController


def rename_top_tab_keys() -> tuple[str, ...]:
    """Return ordered i18n keys for rename top tabs."""
    return (
        "page.rename.tab.file",
        "page.rename.tab.ridge",
        "page.rename.tab.ordering",
        "page.rename.tab.numbering",
    )


def projected_x_unit_label(crs_obj: Any) -> str:
    """Resolve projected-axis unit label from CRS metadata.

    Parameters
    ----------
    crs_obj : Any
        CRS object compatible with ``pyproj.CRS`` axis metadata.

    Returns
    -------
    str
        Axis unit label, preferring ``m`` when CRS unit is meter.
    """
    if crs_obj is None:
        return "unit"
    axis_info = getattr(crs_obj, "axis_info", None)
    if not axis_info:
        return "unit"
    unit_name = str(getattr(axis_info[0], "unit_name", "unit")).lower()
    if "metre" in unit_name or "meter" in unit_name:
        return "m"
    if "degree" in unit_name:
        return "deg"
    return unit_name or "unit"


class RidgeFigurePanel(BottomPanelFigure):
    """Density and peak diagnostics panel for ridge detection.

    Notes
    -----
    This panel intentionally keeps one plot only (density + peaks)
    as required by module 04.
    """

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.plot_widget.setLabel("left", "Count")
        self.plot_widget.setLabel("bottom", "")
        self.plot_widget.setTitle("Ridge Density", size="10pt")

    def set_projected_x_unit(self, unit_text: str) -> None:
        """Keep projected axis label hidden for compact diagnostics view.

        Parameters
        ----------
        unit_text : str
            Unit suffix displayed as ``Projected X (<unit>)``.
        """
        _ = unit_text
        self.plot_widget.setLabel("bottom", "")


class RenameTab(TabInterface):
    """
    Interface content for Seedling ID Renaming and Adjustment.
    """

    sigLoadShp = Signal(str)
    sigLoadBoundary = Signal(str)
    sigLoadDom = Signal(list)  # List of file paths
    sigInputReady = Signal(dict)

    # Signals for parameters (can be connected to backend logic)
    sigRidgeParamsChanged = Signal(dict)
    sigOrderingParamsChanged = Signal(dict)
    sigNumberingParamsChanged = Signal(dict)

    _RIDGE_LABEL_TIP_KEYS = {
        "page.rename.label.strength": "page.rename.tip.strength",
        "page.rename.label.distance": "page.rename.tip.distance",
        "page.rename.label.height": "page.rename.tip.height",
    }
    RIDGE_DIRECTION_SOURCE_LIST = [
        "boundary_x",
        "boundary_y",
        "boundary_-x",
        "boundary_-y",
        "manual_draw",
    ]
    DIRECTION_LABEL_KEY_MAP = {
        "boundary_x": "page.rename.combo.boundary_x",
        "boundary_y": "page.rename.combo.boundary_y",
        "boundary_-x": "page.rename.combo.boundary_neg_x",
        "boundary_-y": "page.rename.combo.boundary_neg_y",
        "manual_draw": "page.rename.combo.manual_draw",
    }

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._input_bundle: dict[str, Any] | None = None
        self._current_points_source: str = ""
        self._dom_layers_cache: list[dict[str, str]] = []

        self._manual_draw_active: bool = False
        self._manual_start_point_array: np.ndarray | None = None
        self._manual_end_point_array: np.ndarray | None = None
        self._manual_direction_vector_array: np.ndarray | None = None
        self._manual_preview_line_item: pg.PlotCurveItem | None = None
        self._manual_fixed_arrow_item: pg.ArrowItem | None = None
        self._manual_handlers_registered: bool = False
        self._active_direction_source_list: list[str] = ["manual_draw"]
        self._ridge_direction_vector_array: np.ndarray | None = None
        self._ridge_rotation_angle_deg: float | None = None
        self._ridge_direction_source: str | None = None
        self._suspend_layer_remove_sync: bool = False
        self._last_ridge_payload: dict[str, Any] = {}
        self._last_ordering_payload: dict[str, Any] = {}

        # Debounce timer for reactive updates
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(800)  # 800ms delay
        self._update_timer.timeout.connect(self._on_parameter_update_timeout)

        # Track which type of parameter changed
        self._pending_update_type: Optional[str] = None
        self._tip_content_key_by_label: dict[QWidget, str] = {}

        self._init_controls()
        self._ridge_figure_panel = RidgeFigurePanel(self)
        self.map_component.bottom_panel_host.register_panel(
            "ridge_figure", self._ridge_figure_panel
        )
        self._ridge_controller = RidgeDetectionController(
            map_canvas=self.map_component.map_canvas,
            figure_panel=self._ridge_figure_panel,
        )
        self._ordering_controller = RidgeOrderingController(
            map_canvas=self.map_component.map_canvas,
        )
        self._refresh_ridge_ui_state()

    def _init_controls(self) -> None:
        """Initialize the controls for seedling renaming."""
        top_tabs_widget = self._build_top_tabs()
        top_tabs_widget.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        # Assuming TabInterface has a layout where we can add this.
        # Checking base_interface might be needed, but usually it has a layout.
        # If standard TabInterface doesn't have a direct layout accessible,
        # we might need to check how seedling_detect uses it.
        # seedling_detect uses: self._tool_layout.addWidget(top_tabs_widget, 1)
        # But 'rename_ids.py' original code used 'self.add_group'.
        # 'TabInterface' likely inherits from 'GalleryInterface' or has similar structure.
        # Let's assume we can use the same approach as seedling_detect if it inherits correctly.
        # However, checking rename_ids.py original code:
        # class RenameTab(TabInterface): ... super().__init__ ... self.add_group(file_group)
        # It seems TabInterface provides `add_group`.
        # But here we want to replace the whole content with the top tab structure.
        # We should access the main layout.
        # In seedling_detect: self._tool_layout.addWidget(top_tabs_widget, 1)
        # We will try to use _tool_layout if available, or clear existing layout.

        if hasattr(self, "_tool_layout"):
            self._tool_layout.addWidget(top_tabs_widget, 1)
        else:
            # Fallback if _tool_layout is not directly available (though it should be)
            layout = QVBoxLayout(self)
            layout.addWidget(top_tabs_widget)
        self.map_component.map_canvas.sigLayerRemoved.connect(
            self._on_canvas_layer_removed
        )

        # We don't use property_panel here based on the requirement to duplicate seedling_detect structure?
        # distinct structure.

    def _build_top_tabs(self) -> QWidget:
        """Build top tab (SegmentedWidget) and stacked content container."""
        container = QWidget()
        container.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred
        )
        layout = QVBoxLayout(container)
        layout.setContentsMargins(6, 0, 6, 0)
        layout.setSpacing(4)

        self.nav = SegmentedWidget(self)
        self.stacked_widget = QStackedWidget(self)

        tab_definitions = [
            ("renameFileTab", self._build_file_tab(), rename_top_tab_keys()[0]),
            ("renameRidgeTab", self._build_ridge_tab(), rename_top_tab_keys()[1]),
            ("renameOrderingTab", self._build_ordering_tab(), rename_top_tab_keys()[2]),
            (
                "renameNumberingTab",
                self._build_numbering_tab(),
                rename_top_tab_keys()[3],
            ),
        ]

        self.tab_file = tab_definitions[0][1]
        for route_key, widget, text_key in tab_definitions:
            self._add_sub_tab(widget, route_key, tr(text_key))

        self.stacked_widget.currentChanged.connect(self._on_tab_changed)
        self.stacked_widget.setCurrentWidget(self.tab_file)
        self.nav.setCurrentItem(self.tab_file.objectName())
        qrouter.setDefaultRouteKey(self.stacked_widget, self.tab_file.objectName())

        self.nav.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(self.nav)
        layout.addWidget(self.stacked_widget)
        return container

    def _add_sub_tab(self, widget: QWidget, route_key: str, text: str) -> None:
        """Register one top tab and its stacked page."""
        widget.setObjectName(route_key)
        self.stacked_widget.addWidget(widget)
        self.nav.addItem(
            routeKey=route_key,
            text=text,
            onClick=lambda: self.stacked_widget.setCurrentWidget(widget),
        )

    @Slot(int)
    def _on_tab_changed(self, index: int) -> None:
        """Sync top tab selection when stacked page changed."""
        widget = self.stacked_widget.widget(index)
        if widget is None:
            return
        object_name = widget.objectName()
        self.nav.setCurrentItem(object_name)
        qrouter.push(self.stacked_widget, object_name)
        if object_name == "renameRidgeTab":
            if self._ridge_direction_vector_array is None:
                return
            self._run_ridge_diagnostics(self._current_ridge_params(), apply_focus=False)
            return
        self.map_component.hide_panel()
        if not self._is_ordering_tab_active():
            return
        if not self._is_ordering_ready():
            self.map_component.hide_panel()
            return
        self._run_ordering_diagnostics(self._current_ordering_params())

    def _is_ordering_tab_active(self) -> bool:
        """Return whether Ordering top-tab is currently visible."""
        current_widget = self.stacked_widget.currentWidget()
        if current_widget is None:
            return False
        return current_widget.objectName() == "renameOrderingTab"

    def _is_ordering_ready(self) -> bool:
        """Return whether ordering has required inputs from ridge stage."""
        if self._input_bundle is None:
            return False
        if self._ridge_direction_vector_array is None:
            return False
        ridge_peak_payload = self._last_ridge_payload.get("ridge_peaks", {})
        ridge_peaks = np.asarray(ridge_peak_payload.get("peak_x", np.asarray([])))
        return ridge_peaks.ndim == 1 and ridge_peaks.size > 0

    def hideEvent(self, event: QHideEvent) -> None:
        """Auto-hide bottom diagnostics when Rename tab becomes hidden."""
        self.map_component.hide_panel()
        super().hideEvent(event)

    def _new_command_bar(self) -> CommandBar:
        """Create command bar with display style."""
        bar = CommandBar(self)
        bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        return bar

    def _bar_spacer(self) -> QWidget:
        """Create expanding spacer widget for command bars."""
        spacer = QWidget(self)
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        return spacer

    def _build_labeled_widget(self, label_key: str, widget: QWidget) -> QWidget:
        """Wrap one label-control pair in horizontal layout."""
        wrapper = QWidget()
        wrapper.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        label = BodyLabel(tr(label_key))
        label.setObjectName(f"label_{label_key.replace('.', '_')}")
        layout.addWidget(label)
        tip_key = self._RIDGE_LABEL_TIP_KEYS.get(label_key)
        if tip_key is not None:
            self._bind_teaching_tip(label, tip_key)
        layout.addWidget(widget)
        return wrapper

    def _bind_teaching_tip(self, label: BodyLabel, content_key: str) -> None:
        """Bind click-to-show simple flyout to one label."""
        self._tip_content_key_by_label[label] = content_key
        label.installEventFilter(self)
        label.setCursor(Qt.CursorShape.PointingHandCursor)

    def _show_teaching_tip(self, label: QWidget) -> None:
        """Show simple flyout for one ridge parameter label."""
        content_key = self._tip_content_key_by_label.get(label)
        if content_key is None:
            return
        Flyout.create(
            target=label,
            icon=InfoBarIcon.SUCCESS,
            title=tr("page.rename.tip.title"),
            content=tr(content_key),
            parent=self,
        )

    def eventFilter(self, watched: Any, event: QEvent) -> bool:
        """Handle click-triggered flyouts for ridge parameter labels."""
        if watched not in self._tip_content_key_by_label:
            return super().eventFilter(watched, event)
        if event.type() == QEvent.Type.MouseButtonPress:
            self._show_teaching_tip(watched)
            return True
        return super().eventFilter(watched, event)

    # --- Tab Builders ---

    def _build_file_tab(self) -> QWidget:
        """Build File tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()

        self.btn_load_shp = PushButton(tr("page.rename.btn.load_points"))
        self.btn_load_shp.clicked.connect(self._on_load_shp)

        self.btn_load_boundary = PushButton(tr("page.rename.btn.load_boundary"))
        self.btn_load_boundary.clicked.connect(self._on_load_boundary)

        self.btn_load_dom = PushButton(
            tr("page.rename.btn.load_dom")
        )  # New DOM load button
        self.btn_load_dom.clicked.connect(self._on_load_dom)

        bar.addWidget(self.btn_load_shp)
        bar.addWidget(self.btn_load_boundary)
        bar.addWidget(self.btn_load_dom)
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _build_ridge_tab(self) -> QWidget:
        """Build Ridge Detection tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()

        self.combo_direction = ComboBox()
        self._set_direction_source_options(has_boundary=False)
        self.combo_direction.currentIndexChanged.connect(
            self._on_direction_source_changed
        )

        self.btn_set_ridge_direction = ToggleButton(
            tr("page.rename.btn.set_ridge_direction")
        )
        self.btn_set_ridge_direction.toggled.connect(
            self._on_set_ridge_direction_toggled
        )
        self.btn_focus_ridge = PushButton(tr("page.rename.btn.focus_ridge"))
        self.btn_focus_ridge.clicked.connect(self._on_focus_ridge_clicked)

        self.spin_strength = DoubleSpinBox()
        self.spin_strength.setRange(0.01, 100.0)
        self.spin_strength.setDecimals(2)
        self.spin_strength.setSingleStep(0.1)
        self.spin_strength.setValue(1)
        self.spin_strength.valueChanged.connect(lambda: self._schedule_update("ridge"))

        self.spin_distance = DoubleSpinBox()
        self.spin_distance.setRange(0.01, 50.0)
        self.spin_distance.setDecimals(2)
        self.spin_distance.setSingleStep(0.1)
        self.spin_distance.setValue(0.5)
        self.spin_distance.valueChanged.connect(lambda: self._schedule_update("ridge"))

        self.spin_height = DoubleSpinBox()
        self.spin_height.setRange(0.1, 200.0)
        self.spin_height.setDecimals(2)
        self.spin_height.setSingleStep(0.1)
        self.spin_height.setValue(20)
        self.spin_height.valueChanged.connect(lambda: self._schedule_update("ridge"))

        bar.addWidget(
            self._build_labeled_widget(
                "page.rename.label.direction", self.combo_direction
            )
        )
        bar.addWidget(self.btn_set_ridge_direction)
        bar.addWidget(self.btn_focus_ridge)
        bar.addSeparator()
        bar.addWidget(
            self._build_labeled_widget("page.rename.label.strength", self.spin_strength)
        )
        bar.addWidget(
            self._build_labeled_widget("page.rename.label.distance", self.spin_distance)
        )
        bar.addWidget(
            self._build_labeled_widget("page.rename.label.height", self.spin_height)
        )
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def _on_set_ridge_direction_toggled(self, checked: bool) -> None:
        """Toggle manual draw mode via accent toggle button state."""
        if not checked:
            if self._manual_draw_active:
                self._deactivate_manual_draw_mode(clear_vector=False)
            return
        if self._current_direction_source() != "manual_draw":
            self.combo_direction.setCurrentIndex(self._manual_direction_index())
            return
        self._activate_manual_draw_mode()

    def _manual_direction_index(self) -> int:
        """Return combo index of manual draw source."""
        return self._active_direction_source_list.index("manual_draw")

    def _current_direction_source(self) -> str:
        """Return current ridge direction source key."""
        index_value = self.combo_direction.currentIndex()
        if index_value < 0 or index_value >= len(self._active_direction_source_list):
            return "manual_draw"
        return self._active_direction_source_list[index_value]

    def _set_direction_source_options(self, has_boundary: bool) -> None:
        """Set direction source options by boundary availability."""
        target_source_list = ["manual_draw"]
        if has_boundary:
            target_source_list = self.RIDGE_DIRECTION_SOURCE_LIST.copy()
        if (
            target_source_list == self._active_direction_source_list
            and self.combo_direction.count() == len(target_source_list)
        ):
            return
        current_source = self._current_direction_source()
        self.combo_direction.blockSignals(True)
        self.combo_direction.clear()
        for source_key in target_source_list:
            label_key = self.DIRECTION_LABEL_KEY_MAP[source_key]
            self.combo_direction.addItem(tr(label_key))
        self._active_direction_source_list = target_source_list
        next_source = current_source
        if next_source not in self._active_direction_source_list:
            next_source = "manual_draw"
        self.combo_direction.setCurrentIndex(
            self._active_direction_source_list.index(next_source)
        )
        self.combo_direction.blockSignals(False)

    def _has_points_input(self) -> bool:
        """Return whether usable points are loaded in current input bundle."""
        if self._input_bundle is None:
            return False
        points_gdf = self._input_bundle.get("points_gdf")
        if not isinstance(points_gdf, gpd.GeoDataFrame):
            return False
        return len(points_gdf) > 0

    def _has_boundary_input(self) -> bool:
        """Return whether boundary geometry exists in current input bundle."""
        if self._input_bundle is None:
            return False
        boundary_gdf = self._input_bundle.get("boundary_gdf")
        if boundary_gdf is None:
            return False
        if not isinstance(boundary_gdf, gpd.GeoDataFrame):
            return False
        return not boundary_gdf.empty

    def _set_ridge_controls_enabled(self, enabled: bool) -> None:
        """Set enabled state for ridge source and action controls."""
        self.combo_direction.setEnabled(enabled)
        self.btn_set_ridge_direction.setEnabled(enabled)
        self.btn_focus_ridge.setEnabled(enabled)

    def _set_ridge_param_controls_enabled(self, enabled: bool) -> None:
        """Set enabled state for ridge numeric parameter controls."""
        self.spin_strength.setEnabled(enabled)
        self.spin_distance.setEnabled(enabled)
        self.spin_height.setEnabled(enabled)

    def _remove_map_layer_with_sync_guard(self, layer_name: str) -> None:
        """Remove map layer while suppressing removal sync side effects."""
        self._suspend_layer_remove_sync = True
        try:
            self.map_component.map_canvas.remove_layer(layer_name)
        finally:
            self._suspend_layer_remove_sync = False

    @Slot(str)
    def _on_canvas_layer_removed(self, layer_name: str) -> None:
        """Sync input and ridge UI state when user deletes key layers."""
        if self._suspend_layer_remove_sync:
            return
        if self._input_bundle is None:
            return
        if layer_name == "Boundary":
            self._input_bundle["boundary_gdf"] = None
            self._input_bundle["boundary_axes"] = None
            points_gdf = self._input_bundle.get("points_gdf")
            if isinstance(points_gdf, gpd.GeoDataFrame):
                self._input_bundle["effective_mask"] = np.ones(
                    len(points_gdf), dtype=np.bool_
                )
            if self._ridge_direction_source and self._ridge_direction_source.startswith(
                "boundary_"
            ):
                self._ridge_direction_source = None
                self._ridge_direction_vector_array = None
                self._ridge_rotation_angle_deg = None
                self._remove_map_layer_with_sync_guard("ridge_direction")
            self._refresh_ridge_ui_state()
            return
        if layer_name != "rename_points":
            return
        self._input_bundle = None
        self._current_points_source = ""
        self._ridge_direction_source = None
        self._ridge_direction_vector_array = None
        self._ridge_rotation_angle_deg = None
        if self._manual_draw_active:
            self._deactivate_manual_draw_mode(clear_vector=True)
        self._refresh_ridge_ui_state()

    def _refresh_ridge_ui_state(self) -> None:
        """Refresh ridge tab source options and enabled state."""
        has_points = self._has_points_input()
        has_boundary = self._has_boundary_input()
        self._set_direction_source_options(has_boundary=has_boundary)
        self._set_ridge_controls_enabled(has_points)
        has_direction = self._ridge_direction_vector_array is not None
        self._set_ridge_param_controls_enabled(has_points and has_direction)
        self._refresh_ordering_ui_state()
        if has_points:
            return
        self._deactivate_manual_draw_mode(clear_vector=True)

    def _on_direction_source_changed(self, _index: int) -> None:
        """Handle ridge direction source change and cleanup transitions."""
        source_key = self._current_direction_source()
        if source_key == "manual_draw":
            self._ridge_direction_source = "manual_draw"
            self._ridge_direction_vector_array = None
            self._ridge_rotation_angle_deg = None
            self._reset_manual_draw_state(clear_layer=True)
            if self.btn_set_ridge_direction.isChecked():
                self._activate_manual_draw_mode()
            self._refresh_ridge_ui_state()
            self._schedule_update("ridge")
            return
        if self.btn_set_ridge_direction.isChecked():
            self.btn_set_ridge_direction.setChecked(False)
        if self._manual_draw_active:
            self._deactivate_manual_draw_mode(clear_vector=True)
        self._sync_boundary_direction_layer(source_key)
        self._schedule_update("ridge")

    def _set_ridge_direction_state(
        self,
        direction_vector_array: np.ndarray,
        source_key: str,
    ) -> None:
        """Store ridge direction vector, source, and derived rotation angle."""
        unit_vec = normalize_direction_vector(direction_vector_array)
        self._ridge_direction_vector_array = unit_vec
        self._ridge_rotation_angle_deg = compute_rotation_angle_deg(unit_vec)
        self._ridge_direction_source = source_key
        self._refresh_ridge_ui_state()

    def _ask_apply_rotation(self) -> bool:
        """Ask user whether current ridge direction should rotate map now."""
        msg_box = MessageBox(
            tr("page.rename.msg.rotation_confirm_title"),
            tr("page.rename.msg.rotation_confirm_content"),
            self.window(),
        )
        msg_box.yesButton.setText(tr("page.rename.btn.apply_rotation_now"))
        msg_box.cancelButton.setText(tr("cancel"))
        return bool(msg_box.exec())

    def _apply_saved_rotation(self) -> bool:
        """Apply stored ridge rotation angle to map canvas."""
        if self._ridge_rotation_angle_deg is None:
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.rename.msg.no_ridge_rotation"),
                parent=self,
                duration=2200,
            )
            return False
        self.map_component.map_canvas.set_rotation(self._ridge_rotation_angle_deg)
        return True

    def _on_focus_ridge_clicked(self) -> None:
        """Rotate map to follow stored ridge direction angle."""
        if not self._focus_ridge_runtime():
            return
        self._run_ridge_diagnostics(self._current_ridge_params(), apply_focus=False)

    def _focus_ridge_runtime(self) -> bool:
        """Apply ridge focus pipeline: rotation then x-axis fit.

        Returns
        -------
        bool
            ``True`` when both rotation and fit-width succeed.
        """
        if not self._apply_saved_rotation():
            return False
        return bool(
            self.map_component.map_canvas.fit_layer_to_x(
                "rename_points",
                padding=0.05,
            )
        )

    def _set_edit_mode_exclusion_for_manual(self, manual_active: bool) -> None:
        """Toggle numbering edit tools when manual ridge draw is active.

        Parameters
        ----------
        manual_active : bool
            Whether manual ridge draw mode is active.
        """
        for button in (self.btn_add, self.btn_move, self.btn_delete):
            button.setEnabled(not manual_active)
            if manual_active:
                button.setChecked(False)

    def _activate_manual_draw_mode(self) -> None:
        """Activate manual draw interaction mode for ridge direction."""
        self._manual_draw_active = True
        self._register_manual_draw_handlers()
        self._set_edit_mode_exclusion_for_manual(True)

    def _deactivate_manual_draw_mode(self, clear_vector: bool) -> None:
        """Deactivate manual draw mode and clear transient overlays.

        Parameters
        ----------
        clear_vector : bool
            Whether manual points and vector should be fully cleared.
        """
        self._manual_draw_active = False
        self._unregister_manual_draw_handlers()
        self._remove_manual_overlay_items()
        self._set_edit_mode_exclusion_for_manual(False)
        if clear_vector:
            self._manual_start_point_array = None
            self._manual_end_point_array = None
            self._manual_direction_vector_array = None
            self._remove_map_layer_with_sync_guard("ridge_direction")

    def _register_manual_draw_handlers(self) -> None:
        """Register map canvas handlers for manual draw mode."""
        if self._manual_handlers_registered:
            return
        map_canvas = self.map_component.map_canvas
        map_canvas.register_click_handler(self._on_ridge_manual_click)
        map_canvas.register_hover_handler(self._on_ridge_manual_hover)
        self._manual_handlers_registered = True

    def _unregister_manual_draw_handlers(self) -> None:
        """Unregister map canvas handlers for manual draw mode."""
        if not self._manual_handlers_registered:
            return
        map_canvas = self.map_component.map_canvas
        map_canvas.unregister_click_handler(self._on_ridge_manual_click)
        map_canvas.unregister_hover_handler(self._on_ridge_manual_hover)
        self._manual_handlers_registered = False

    def _remove_manual_overlay_items(self) -> None:
        """Remove manual draw preview and fixed line overlay items."""
        map_canvas = self.map_component.map_canvas
        if self._manual_preview_line_item is not None:
            map_canvas.remove_overlay_item(self._manual_preview_line_item)
            self._manual_preview_line_item = None
        if self._manual_fixed_arrow_item is not None:
            map_canvas.remove_overlay_item(self._manual_fixed_arrow_item)
            self._manual_fixed_arrow_item = None

    def _reset_manual_draw_state(self, clear_layer: bool) -> None:
        """Reset manual draw points, vector, and transient overlays."""
        self._manual_start_point_array = None
        self._manual_end_point_array = None
        self._manual_direction_vector_array = None
        self._remove_manual_overlay_items()
        if not clear_layer:
            return
        self._remove_map_layer_with_sync_guard("ridge_direction")
        if self._ridge_direction_source != "manual_draw":
            return
        self._ridge_direction_vector_array = None
        self._ridge_rotation_angle_deg = None
        self._ridge_direction_source = None

    def _build_manual_line_item(self, color_hex: str) -> pg.PlotCurveItem:
        """Create one manual draw line item.

        Parameters
        ----------
        color_hex : str
            Line color string in hex format.

        Returns
        -------
        pyqtgraph.PlotCurveItem
            Empty curve item ready for coordinates.
        """
        line_item = pg.PlotCurveItem(
            pen=pg.mkPen(color=color_hex, width=2.0),
            connect="all",
        )
        line_item.setZValue(760)
        return line_item

    def _on_ridge_manual_click(self, x_coord: float, y_coord: float, button) -> bool:
        """Handle manual draw click events from map canvas.

        Parameters
        ----------
        x_coord : float
            Click x coordinate in map space.
        y_coord : float
            Click y coordinate in map space.
        button : Any
            Mouse button enum from Qt.

        Returns
        -------
        bool
            True when the click was consumed by manual draw mode.
        """
        if not self._manual_draw_active:
            return False
        if button != Qt.MouseButton.LeftButton:
            return False
        point_array = np.asarray([x_coord, y_coord], dtype=np.float64)
        if (
            self._manual_start_point_array is None
            or self._manual_end_point_array is not None
        ):
            self._manual_start_point_array = point_array
            self._manual_end_point_array = None
            self._remove_manual_overlay_items()
            return True
        self._manual_end_point_array = point_array
        try:
            vector_array = normalize_direction_vector(
                self._manual_end_point_array - self._manual_start_point_array
            )
        except ValueError:
            self._manual_end_point_array = None
            InfoBar.warning(
                title=tr("warning"),
                content=tr("page.rename.msg.manual_vector_invalid"),
                parent=self,
                duration=2200,
            )
            return True
        self._manual_direction_vector_array = vector_array
        self._set_ridge_direction_state(vector_array, "manual_draw")
        self._draw_manual_fixed_line()
        self.btn_set_ridge_direction.setChecked(False)
        if self._ask_apply_rotation():
            self._apply_saved_rotation()
        self._schedule_update("ridge")
        return True

    def _on_ridge_manual_hover(self, x_coord: float, y_coord: float) -> None:
        """Handle manual draw hover updates for preview segment."""
        if not self._manual_draw_active:
            return
        if self._manual_start_point_array is None:
            return
        if self._manual_end_point_array is not None:
            return
        if self._manual_preview_line_item is None:
            self._manual_preview_line_item = self._build_manual_line_item("#00A3FF")
            self.map_component.map_canvas.add_overlay_item(
                self._manual_preview_line_item
            )
        x_data = [self._manual_start_point_array[0], float(x_coord)]
        y_data = [self._manual_start_point_array[1], float(y_coord)]
        self._manual_preview_line_item.setData(x=x_data, y=y_data)

    def _build_ridge_direction_arrow_geometry(
        self,
        start_point_array: np.ndarray,
        end_point_array: np.ndarray,
    ) -> MultiLineString:
        """Build one arrow multiline geometry for ridge_direction layer."""
        shaft_vec = end_point_array - start_point_array
        shaft_len = float(np.linalg.norm(shaft_vec))
        unit_vec = normalize_direction_vector(shaft_vec)
        head_len = max(shaft_len * 0.18, 1e-6)
        head_width = head_len * 0.7
        tip_point = end_point_array
        back_point = tip_point - unit_vec * head_len
        ortho_vec = np.asarray([-unit_vec[1], unit_vec[0]], dtype=np.float64)
        left_point = back_point + ortho_vec * head_width
        right_point = back_point - ortho_vec * head_width
        line_list = [
            [tuple(start_point_array), tuple(tip_point)],
            [tuple(tip_point), tuple(left_point)],
            [tuple(tip_point), tuple(right_point)],
        ]
        return MultiLineString(line_list)

    def _effective_points_array(self) -> np.ndarray:
        """Return effective points array with shape (N, 2)."""
        if self._input_bundle is None:
            raise ValueError("input bundle is missing")
        points_gdf = self._input_bundle["points_gdf"]
        point_array = np.column_stack(
            (points_gdf.geometry.x.to_numpy(), points_gdf.geometry.y.to_numpy())
        )
        mask_array = np.asarray(
            self._input_bundle.get("effective_mask", np.ones(len(points_gdf))),
            dtype=np.bool_,
        )
        if mask_array.shape[0] != point_array.shape[0]:
            raise ValueError("effective mask length mismatch")
        eff_array = point_array[mask_array]
        if eff_array.shape[0] < 2:
            raise ValueError("effective points are insufficient")
        return eff_array

    def _line_intersections_with_box(
        self,
        center_array: np.ndarray,
        axis_array: np.ndarray,
        box_polygon,
        scale_len: float,
    ) -> list[np.ndarray]:
        """Compute line-box intersections for one axis passing box center."""
        line = LineString(
            [
                tuple(center_array - axis_array * scale_len),
                tuple(center_array + axis_array * scale_len),
            ]
        )
        inter = box_polygon.boundary.intersection(line)
        if inter.is_empty:
            raise ValueError("no intersection between axis line and bounding box")
        if inter.geom_type == "Point":
            return [np.asarray([inter.x, inter.y], dtype=np.float64)]
        if inter.geom_type == "MultiPoint":
            return [np.asarray([pt.x, pt.y], dtype=np.float64) for pt in inter.geoms]
        coord_list = list(getattr(inter, "coords", []))
        return [np.asarray([x, y], dtype=np.float64) for x, y in coord_list]

    def _compute_boundary_direction_segment(
        self,
        source_key: str,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute ridge direction segment using effective points and MABR."""
        if self._input_bundle is None:
            raise ValueError("input bundle is missing")
        boundary_axes = self._input_bundle.get("boundary_axes")
        if boundary_axes is None:
            raise ValueError("boundary axes are missing")
        axis_vec = resolve_direction_vector(source_key, boundary_axes=boundary_axes)
        eff_array = self._effective_points_array()
        box_polygon = MultiPoint(
            [tuple(row) for row in eff_array]
        ).minimum_rotated_rectangle
        center_array = np.asarray(box_polygon.centroid.coords[0], dtype=np.float64)
        bbox_min, _, bbox_max, _ = box_polygon.bounds
        scale_len = max(float(bbox_max - bbox_min), 1.0) * 4.0
        point_list = self._line_intersections_with_box(
            center_array,
            axis_vec,
            box_polygon,
            scale_len,
        )
        if len(point_list) < 2:
            raise ValueError("axis line intersection needs at least two points")
        proj_list = [float(np.dot(pt - center_array, axis_vec)) for pt in point_list]
        start_idx = int(np.argmin(proj_list))
        end_idx = int(np.argmax(proj_list))
        return point_list[start_idx], point_list[end_idx]

    def _sync_boundary_direction_layer(self, source_key: str) -> None:
        """Sync ridge direction layer when boundary direction source is selected."""
        if not source_key.startswith("boundary_"):
            return
        try:
            start_pt, end_pt = self._compute_boundary_direction_segment(source_key)
        except Exception:
            self._ridge_direction_source = None
            self._ridge_direction_vector_array = None
            self._ridge_rotation_angle_deg = None
            self._remove_map_layer_with_sync_guard("ridge_direction")
            self._refresh_ridge_ui_state()
            return
        self._set_ridge_direction_state(end_pt - start_pt, source_key)
        crs_value = None
        if self._input_bundle is not None:
            points_gdf = self._input_bundle.get("points_gdf")
            if isinstance(points_gdf, gpd.GeoDataFrame):
                crs_value = points_gdf.crs
        arrow_geom = self._build_ridge_direction_arrow_geometry(start_pt, end_pt)
        ridge_gdf = gpd.GeoDataFrame(
            {"name": ["ridge_direction"]},
            geometry=[arrow_geom],
            crs=crs_value,
        )
        self.map_component.map_canvas.add_vector_layer(
            ridge_gdf,
            "ridge_direction",
            color="#FF7A00",
            width=2,
        )
        if self._ask_apply_rotation():
            self._apply_saved_rotation()

    def _sync_manual_direction_layer(self) -> None:
        """Sync manual ridge direction as vector layer in map and layer tree."""
        if (
            self._manual_start_point_array is None
            or self._manual_end_point_array is None
        ):
            return
        crs_value = None
        if self._input_bundle is not None:
            points_gdf = self._input_bundle.get("points_gdf")
            if isinstance(points_gdf, gpd.GeoDataFrame):
                crs_value = points_gdf.crs
        arrow_geom = self._build_ridge_direction_arrow_geometry(
            self._manual_start_point_array,
            self._manual_end_point_array,
        )
        ridge_gdf = gpd.GeoDataFrame(
            {"name": ["ridge_direction"]},
            geometry=[arrow_geom],
            crs=crs_value,
        )
        self.map_component.map_canvas.add_vector_layer(
            ridge_gdf,
            "ridge_direction",
            color="#FF7A00",
            width=2,
        )

    def _draw_manual_fixed_line(self) -> None:
        """Finalize manual draw by syncing ridge_direction layer."""
        if (
            self._manual_start_point_array is None
            or self._manual_end_point_array is None
            or self._manual_direction_vector_array is None
        ):
            return
        map_canvas = self.map_component.map_canvas
        self._manual_fixed_arrow_item = None
        if self._manual_preview_line_item is not None:
            map_canvas.remove_overlay_item(self._manual_preview_line_item)
            self._manual_preview_line_item = None
        self._sync_manual_direction_layer()

    def _build_ordering_tab(self) -> QWidget:
        """Build Ordering tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()

        self.spin_buffer = DoubleSpinBox()
        self.spin_buffer.setRange(0.01, 1.0)
        self.spin_buffer.setValue(0.5)
        self.spin_buffer.setSingleStep(0.05)
        self.spin_buffer.valueChanged.connect(lambda: self._schedule_update("ordering"))

        self.check_ransac = CheckBox(tr("page.rename.check.ransac"))
        self.check_ransac.stateChanged.connect(
            lambda: self._schedule_update("ordering")
        )

        self.spin_residual = SpinBox()
        self.spin_residual.setRange(1, 100)
        self.spin_residual.setValue(35)
        self.spin_residual.valueChanged.connect(
            lambda: self._schedule_update("ordering")
        )

        self.spin_trials = SpinBox()
        self.spin_trials.setRange(100, 10000)
        self.spin_trials.setValue(2000)
        self.spin_trials.valueChanged.connect(lambda: self._schedule_update("ordering"))

        self.label_ordering_stats = BodyLabel("")
        self.label_ordering_stats.setObjectName("label_ordering_stats")

        bar.addWidget(
            self._build_labeled_widget("page.rename.label.buffer", self.spin_buffer)
        )
        bar.addWidget(self.check_ransac)
        bar.addWidget(
            self._build_labeled_widget("page.rename.label.residual", self.spin_residual)
        )
        bar.addWidget(
            self._build_labeled_widget("page.rename.label.max_trials", self.spin_trials)
        )
        bar.addSeparator()
        bar.addWidget(self.label_ordering_stats)
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)

        # Link RANSAC enable state to numeric inputs
        self.check_ransac.stateChanged.connect(self._update_ransac_ui_state)
        self._set_ordering_stats_text(None)
        self._refresh_ordering_ui_state()

        return tab

    def _update_ransac_ui_state(self):
        enabled = self.check_ransac.isEnabled() and self.check_ransac.isChecked()
        self.spin_residual.setEnabled(enabled)
        self.spin_trials.setEnabled(enabled)

    def _set_ordering_controls_enabled(self, enabled: bool) -> None:
        """Set enabled state for ordering controls by ridge readiness."""
        self.spin_buffer.setEnabled(enabled)
        self.check_ransac.setEnabled(enabled)
        if not enabled:
            self.spin_residual.setEnabled(False)
            self.spin_trials.setEnabled(False)
            return
        self._update_ransac_ui_state()

    def _refresh_ordering_ui_state(self) -> None:
        """Refresh ordering controls based on ridge output readiness."""
        has_points = self._has_points_input()
        has_direction = self._ridge_direction_vector_array is not None
        ridge_peak_payload = self._last_ridge_payload.get("ridge_peaks", {})
        ridge_peaks = np.asarray(ridge_peak_payload.get("peak_x", np.asarray([])))
        has_ridge_peaks = ridge_peaks.ndim == 1 and ridge_peaks.size > 0
        self._set_ordering_controls_enabled(
            has_points and has_direction and has_ridge_peaks
        )

    def _set_ordering_stats_text(self, stats: dict[str, int] | None) -> None:
        """Render ordering summary text as assigned, ignored and total counts."""
        if stats is None:
            assigned_count = 0
            ignored_count = 0
            total_count = 0
        else:
            assigned_count = int(stats.get("assigned_points", 0))
            ignored_count = int(stats.get("ignored_points", 0))
            total_count = int(stats.get("total_points", 0))
        self.label_ordering_stats.setText(
            tr("page.rename.label.ordering_stats").format(
                assigned=assigned_count,
                ignored=ignored_count,
                total=total_count,
            )
        )

    def _build_numbering_tab(self) -> QWidget:
        """Build Numbering tab with Edit tools."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(0, 0, 0, 0)
        bar = self._new_command_bar()

        # Edit Tools (Moved from Seedling Detect)
        self.btn_view = PushButton(tr("page.rename.btn.view"))
        self.btn_view.setCheckable(True)
        self.btn_view.setChecked(True)

        self.btn_add = PushButton(tr("page.rename.btn.add"))
        self.btn_add.setCheckable(True)

        self.btn_move = PushButton(tr("page.rename.btn.move"))
        self.btn_move.setCheckable(True)

        self.btn_delete = PushButton(tr("page.rename.btn.delete"))
        self.btn_delete.setCheckable(True)

        self.btn_undo = PushButton(tr("page.rename.btn.undo"))

        bar.addWidget(self.btn_view)
        bar.addWidget(self.btn_add)
        bar.addWidget(self.btn_move)
        bar.addWidget(self.btn_delete)
        bar.addSeparator()
        bar.addWidget(self.btn_undo)
        bar.addSeparator()

        # Numbering Tools
        self.combo_format = ComboBox()
        self.combo_format.addItems(
            [
                tr("page.rename.combo.rc_plant"),
                tr("page.rename.combo.numeric"),
                tr("page.rename.combo.custom"),
            ]
        )
        self.combo_format.currentIndexChanged.connect(
            lambda: self._schedule_update("numbering")
        )

        bar.addWidget(
            self._build_labeled_widget("page.rename.label.format", self.combo_format)
        )
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)
        return tab

    def set_input_bundle(self, bundle: dict) -> None:
        """Set object-first input bundle from upstream tab.

        Parameters
        ----------
        bundle : dict
            Input payload that follows RenameInputBundle contract.
        """
        try:
            self._validate_input_bundle(bundle)
        except Exception as exc:
            InfoBar.error(
                title=tr("error"),
                content=f"Invalid input bundle: {exc}",
                parent=self,
                duration=4500,
            )
            raise
        self._input_bundle = bundle
        self._dom_layers_cache = list(bundle.get("dom_layers", []))
        points_meta = bundle.get("points_meta", {})
        self._current_points_source = str(points_meta.get("source", "send_next"))
        self._refresh_ridge_ui_state()
        self._render_points_overlay(bundle["points_gdf"])
        self._emit_input_ready()

    def _validate_input_bundle(self, bundle: dict) -> None:
        """Validate required fields and shape alignment for input bundle."""
        required_keys = ["points_gdf", "points_meta", "effective_mask", "dom_layers"]
        missing_keys = [key for key in required_keys if key not in bundle]
        if missing_keys:
            missing_text = ", ".join(missing_keys)
            raise ValueError(f"bundle missing fields: {missing_text}")
        points_gdf = bundle["points_gdf"]
        if not isinstance(points_gdf, gpd.GeoDataFrame):
            raise ValueError("bundle points_gdf must be GeoDataFrame")
        mask_array = np.asarray(bundle["effective_mask"], dtype=np.bool_)
        if mask_array.shape[0] != len(points_gdf):
            raise ValueError("bundle effective_mask length mismatch")

    def _emit_input_ready(self) -> None:
        """Emit input-ready signal when bundle is available."""
        if self._input_bundle is None:
            return
        self.sigInputReady.emit(self._input_bundle)

    def _render_points_overlay(self, points_gdf: gpd.GeoDataFrame) -> None:
        """Render points as a temporary overlay layer in map canvas."""
        xy_array = np.column_stack(
            (points_gdf.geometry.x.to_numpy(), points_gdf.geometry.y.to_numpy())
        )
        if xy_array.size == 0:
            return
        layer_name = "rename_points"
        map_canvas = self.map_component.map_canvas
        self._remove_map_layer_with_sync_guard(layer_name)
        map_canvas.add_point_layer(
            xy_array,
            layer_name,
            size=8,
            fill_color=(255, 59, 48, 180),
            border_color="#FF3B30",
            border_width=1.2,
            z_value=630,
            replace=True,
        )
        map_canvas.zoom_to_layer(layer_name)

    def _build_points_bundle(
        self, points_gdf: gpd.GeoDataFrame, source: str, source_tag: str
    ) -> dict[str, Any]:
        """Build or update current input bundle with normalized points."""
        normalized_gdf, points_meta = normalize_input_points(points_gdf)
        old_bundle = self._input_bundle or {}
        dom_layers = old_bundle.get("dom_layers", self._dom_layers_cache.copy())
        new_bundle = {
            "points_gdf": normalized_gdf,
            "points_meta": {
                "source": source,
                "id_field": points_meta["id_field"],
                "crs_wkt": points_meta["crs_wkt"],
                "source_tag": source_tag,
            },
            "boundary_gdf": old_bundle.get("boundary_gdf"),
            "boundary_axes": old_bundle.get("boundary_axes"),
            "effective_mask": np.ones(len(normalized_gdf), dtype=np.bool_),
            "dom_layers": dom_layers,
        }
        return new_bundle

    @staticmethod
    def _dedupe_layer_name(base_name: str, existing_names: set[str]) -> str:
        """Return unique layer name by suffixing incremental index.

        Parameters
        ----------
        base_name : str
            Preferred layer name.
        existing_names : set[str]
            Existing names in current map and session.

        Returns
        -------
        str
            Unique layer name such as ``name_1``.
        """
        if base_name not in existing_names:
            return base_name
        index = 1
        while f"{base_name}_{index}" in existing_names:
            index += 1
        return f"{base_name}_{index}"

    def _cache_dom_layer(self, layer_name: str, layer_path: str) -> None:
        """Insert DOM layer metadata as top DOM entry in bundle order."""
        self._dom_layers_cache.insert(0, {"name": layer_name, "path": layer_path})
        if self._input_bundle is None:
            return
        self._input_bundle["dom_layers"] = self._dom_layers_cache.copy()

    @staticmethod
    def _format_dom_path_hint(file_path: str) -> str:
        """Build compact path hint text from parent folder name."""
        parent_name = Path(file_path).parent.name
        if not parent_name:
            return ""
        return f" (.../{parent_name}/...)"

    def _build_dom_layer_name(self, file_path: str, existing_names: set[str]) -> str:
        """Build DOM layer name with optional path hint and dedupe suffix."""
        base_name = Path(file_path).stem
        source_name_set = {
            Path(item["path"]).stem
            for item in self._dom_layers_cache
            if item.get("path") and item.get("path") != file_path
        }
        if base_name in source_name_set:
            base_name = f"{base_name}{self._format_dom_path_hint(file_path)}"
        return self._dedupe_layer_name(base_name, existing_names)

    @staticmethod
    def _common_prefix_len(parts_list: list[tuple[str, ...]]) -> int:
        """Return common prefix length for path-parts list."""
        if not parts_list:
            return 0
        index = 0
        min_len = min(len(parts) for parts in parts_list)
        while index < min_len and len({parts[index] for parts in parts_list}) == 1:
            index += 1
        return index

    def _build_name_by_path(
        self, path_list: list[str], existing_names: set[str]
    ) -> dict[str, str]:
        """Build stable display names for DOM paths.

        Notes
        -----
        Same-stem files from different paths will all receive path hints.
        """
        path_by_stem: dict[str, list[str]] = {}
        for file_path in path_list:
            stem = Path(file_path).stem
            path_by_stem.setdefault(stem, []).append(file_path)
        name_by_path: dict[str, str] = {}
        occupied_names = set(existing_names)
        for stem, stem_paths in path_by_stem.items():
            if len(stem_paths) == 1:
                stem_name = self._dedupe_layer_name(stem, occupied_names)
                name_by_path[stem_paths[0]] = stem_name
                occupied_names.add(stem_name)
                continue
            parent_parts = [Path(path).parent.parts for path in stem_paths]
            prefix_len = self._common_prefix_len(parent_parts)
            for path in stem_paths:
                current_parts = Path(path).parent.parts
                hint_part = (
                    current_parts[prefix_len]
                    if prefix_len < len(current_parts)
                    else current_parts[-1]
                )
                base_name = f"{stem} (.../{hint_part}/...)"
                safe_name = self._dedupe_layer_name(base_name, occupied_names)
                name_by_path[path] = safe_name
                occupied_names.add(safe_name)
        return name_by_path

    def _rename_existing_dom_layers(self, name_by_path: dict[str, str]) -> None:
        """Rename already loaded DOM layers to desired names."""
        map_canvas = self.map_component.map_canvas
        for entry in self._dom_layers_cache:
            old_name = entry["name"]
            old_path = entry["path"]
            new_name = name_by_path.get(old_path, old_name)
            if new_name == old_name:
                continue
            if map_canvas.rename_layer(old_name, new_name):
                entry["name"] = new_name
        if self._input_bundle is not None:
            self._input_bundle["dom_layers"] = self._dom_layers_cache.copy()

    def _ask_dom_duplicate_action(self, duplicate_paths: list[str]) -> str | None:
        """Ask user whether duplicate DOM paths should be skipped or renamed."""
        duplicate_names = ", ".join(Path(path).name for path in duplicate_paths)
        msg_box = MessageBox(
            "Duplicate DOM detected",
            f"These DOM files are already loaded: {duplicate_names}",
            self.window(),
        )
        msg_box.yesButton.setText("Skip duplicates")
        msg_box.cancelButton.setText("Load and rename")
        if msg_box.exec():
            return "skip"
        return "rename"

    # --- Event Handlers ---

    def _on_load_shp(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("page.common.load_shp"), "", "Shapefile (*.shp)"
        )
        if not file_path:
            return
        prev_bundle = self._input_bundle
        try:
            points_gdf = load_points_data(file_path)
            new_bundle = self._build_points_bundle(
                points_gdf=points_gdf,
                source="file",
                source_tag=Path(file_path).name,
            )
            self._input_bundle = new_bundle
            self._current_points_source = "file"
            self._refresh_ridge_ui_state()
            self._render_points_overlay(new_bundle["points_gdf"])
            self.sigLoadShp.emit(file_path)
            self._emit_input_ready()
            InfoBar.success(
                title=tr("success"),
                content=f"Loaded points: {Path(file_path).name}",
                parent=self,
                duration=2000,
            )
        except Exception as exc:
            self._input_bundle = prev_bundle
            self._refresh_ridge_ui_state()
            InfoBar.error(
                title=tr("error"),
                content=f"Failed to load points: {exc}",
                parent=self,
                duration=4000,
            )

    def _on_load_boundary(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, tr("page.rename.btn.load_boundary"), "", "Shapefile (*.shp)"
        )
        if not file_path:
            return
        if self._input_bundle is None:
            InfoBar.warning(
                title=tr("warning"),
                content="Load points first before boundary.",
                parent=self,
                duration=2500,
            )
            return
        try:
            boundary_gdf = gpd.read_file(Path(file_path))
            points_gdf = self._input_bundle["points_gdf"]
            points_aligned, boundary_aligned = align_boundary_crs(
                points_gdf, boundary_gdf
            )
            effective_mask = build_effective_mask(points_aligned, boundary_aligned)
            boundary_axes = compute_boundary_axes(boundary_aligned)
            self._input_bundle["points_gdf"] = points_aligned
            self._input_bundle["boundary_gdf"] = boundary_aligned
            self._input_bundle["boundary_axes"] = boundary_axes
            self._input_bundle["effective_mask"] = effective_mask
            self._refresh_ridge_ui_state()
            self.map_component.map_canvas.add_vector_layer(
                boundary_aligned,
                "Boundary",
                color="#FF4040",
                width=2,
            )
            self.sigLoadBoundary.emit(file_path)
            self._emit_input_ready()
            InfoBar.success(
                title=tr("success"),
                content=f"Loaded boundary: {Path(file_path).name}",
                parent=self,
                duration=2000,
            )
        except Exception as exc:
            InfoBar.error(
                title=tr("error"),
                content=f"Failed to load boundary: {exc}",
                parent=self,
                duration=4000,
            )

    def _on_load_dom(self):
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, tr("page.rename.btn.load_dom"), "", "GeoTIFF (*.tif *.tiff)"
        )
        if not file_paths:
            return
        map_canvas = self.map_component.map_canvas
        existing_path_set = {item.get("path", "") for item in self._dom_layers_cache}
        duplicate_path_list = [path for path in file_paths if path in existing_path_set]
        duplicate_action = "rename"
        if duplicate_path_list:
            duplicate_action = self._ask_dom_duplicate_action(duplicate_path_list)
        selected_new_paths = [
            path
            for path in file_paths
            if not (path in duplicate_path_list and duplicate_action == "skip")
        ]
        existing_dom_paths = [item.get("path", "") for item in self._dom_layers_cache]
        target_dom_paths = list(dict.fromkeys(existing_dom_paths + selected_new_paths))
        map_names = set(map_canvas.get_layer_names())
        non_dom_names = map_names - {item["name"] for item in self._dom_layers_cache}
        desired_name_by_path = self._build_name_by_path(target_dom_paths, non_dom_names)
        self._rename_existing_dom_layers(desired_name_by_path)
        existing_names = set(map_canvas.get_layer_names())
        loaded_names: list[str] = []
        loaded_paths: list[str] = []
        failed_files: list[str] = []
        skipped_files: list[str] = []
        for file_path in file_paths:
            if file_path in duplicate_path_list and duplicate_action == "skip":
                skipped_files.append(Path(file_path).name)
                continue
            dom_name = desired_name_by_path.get(file_path, Path(file_path).stem)
            dom_name = self._dedupe_layer_name(dom_name, existing_names)
            existing_names.add(dom_name)
            if not map_canvas.add_raster_layer(file_path, dom_name):
                failed_files.append(Path(file_path).name)
                continue
            loaded_names.append(dom_name)
            loaded_paths.append(file_path)
            self._cache_dom_layer(dom_name, file_path)
        if loaded_names:
            all_dom_names = [item["name"] for item in self._dom_layers_cache]
            map_canvas.ensure_layers_bottom(all_dom_names)
            self.sigLoadDom.emit(loaded_paths)
            self._emit_input_ready()
            InfoBar.success(
                title=tr("success"),
                content=f"Loaded DOM layers: {len(loaded_names)}",
                parent=self,
                duration=2200,
            )
        if skipped_files:
            skipped_text = ", ".join(skipped_files)
            InfoBar.info(
                title=tr("info"),
                content=f"Skipped duplicate DOM: {skipped_text}",
                parent=self,
                duration=3000,
            )
        if failed_files:
            failed_text = ", ".join(failed_files)
            InfoBar.warning(
                title=tr("warning"),
                content=f"Failed DOM: {failed_text}",
                parent=self,
                duration=3500,
            )

    def _schedule_update(self, update_type: str):
        """Schedule a delayed update to avoid spamming calculations."""
        self._pending_update_type = update_type
        self._update_timer.start()

    def _current_ridge_params(self) -> dict[str, Any]:
        """Build current ridge parameter payload from UI state."""
        return {
            "ridge_direction_source": self._ridge_direction_source,
            "ridge_direction_vector": self._ridge_direction_vector_array,
            "rotation_angle_deg": self._ridge_rotation_angle_deg,
            "strength": self.spin_strength.value(),
            "distance": self.spin_distance.value(),
            "height": self.spin_height.value(),
        }

    def _current_ordering_params(self) -> dict[str, Any]:
        """Build current ordering parameter payload from UI state."""
        return {
            "buffer": self.spin_buffer.value(),
            "ransac_enabled": self.check_ransac.isChecked(),
            "residual": self.spin_residual.value(),
            "max_trials": self.spin_trials.value(),
        }

    def _on_parameter_update_timeout(self):
        """Timer finished, emit the update signal."""
        if not self._pending_update_type:
            return

        if self._pending_update_type == "ridge":
            params = self._current_ridge_params()
            self.sigRidgeParamsChanged.emit(params)
            self._run_ridge_diagnostics(params, apply_focus=True)

        elif self._pending_update_type == "ordering":
            params = self._current_ordering_params()
            self.sigOrderingParamsChanged.emit(params)
            if self._is_ordering_tab_active():
                self._run_ordering_diagnostics(params)

        elif self._pending_update_type == "numbering":
            params = {"format_index": self.combo_format.currentIndex()}
            self.sigNumberingParamsChanged.emit(params)

        self._pending_update_type = None

    def _run_ridge_diagnostics(
        self,
        ridge_params: dict[str, Any],
        apply_focus: bool,
    ) -> None:
        """Run ridge diagnostics and dispatch figure/map outputs."""
        if self._input_bundle is None:
            return
        direction_vector = ridge_params.get("ridge_direction_vector")
        if direction_vector is not None:
            self.map_component.show_panel("ridge_figure")
        points_gdf = self._input_bundle.get("points_gdf")
        if not isinstance(points_gdf, gpd.GeoDataFrame):
            return
        self._ridge_figure_panel.set_projected_x_unit(
            projected_x_unit_label(points_gdf.crs)
        )
        try:
            points_array = self._effective_points_array()
        except Exception:
            points_array = np.empty((0, 2), dtype=np.float64)
        ridge_payload = self._ridge_controller.update(
            effective_points_xy=points_array,
            direction_vector=direction_vector,
            strength_ratio=float(ridge_params.get("strength", 0.0)),
            distance=float(ridge_params.get("distance", 1.0)),
            height=float(ridge_params.get("height", 0.0)),
            crs=points_gdf.crs,
        )
        self._last_ridge_payload = ridge_payload
        self._refresh_ordering_ui_state()
        if direction_vector is not None and apply_focus:
            self._focus_ridge_runtime()

    def _run_ordering_diagnostics(self, ordering_params: dict[str, Any]) -> None:
        """Run ordering pipeline and render ridge-colored point layers."""
        if self._input_bundle is None:
            return
        points_gdf = self._input_bundle.get("points_gdf")
        if not isinstance(points_gdf, gpd.GeoDataFrame):
            return
        ridge_peak_payload = self._last_ridge_payload.get("ridge_peaks", {})
        ridge_peaks = np.asarray(ridge_peak_payload.get("peak_x", np.asarray([])))
        effective_mask = np.asarray(
            self._input_bundle.get("effective_mask", np.ones(len(points_gdf))),
            dtype=np.bool_,
        )
        ordering_payload = self._ordering_controller.update(
            points_gdf=points_gdf,
            effective_mask=effective_mask,
            direction_vector=self._ridge_direction_vector_array,
            ridge_peaks=ridge_peaks,
            params=ordering_params,
        )
        self._last_ordering_payload = ordering_payload
        self._input_bundle["ordering_result_gdf"] = ordering_payload[
            "ordering_result_gdf"
        ]
        self._input_bundle["ordering_stats"] = ordering_payload["ordering_stats"]
        self._set_ordering_stats_text(ordering_payload["ordering_stats"])
