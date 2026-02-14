"""
ID Renaming Page with SegmentedWidget top tabs.
"""

from typing import Any, Optional
from pathlib import Path

import geopandas as gpd
import numpy as np
import pyqtgraph as pg

from PySide6.QtCore import Qt, Slot, Signal, QTimer
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
    PrimaryPushButton,
    ComboBox,
    SpinBox,
    DoubleSpinBox,
    BodyLabel,
    CheckBox,
    InfoBar,
    MessageBox,
    qrouter,
)

from src.gui.components.base_interface import TabInterface
from src.gui.components.map_canvas import LayerBounds
from src.gui.config import tr
from src.utils.rename_ids.boundary import (
    align_boundary_crs,
    build_effective_mask,
    compute_boundary_axes,
)
from src.utils.rename_ids.io import load_points_data, normalize_input_points


def rename_top_tab_keys() -> tuple[str, ...]:
    """Return ordered i18n keys for rename top tabs."""
    return (
        "page.rename.tab.file",
        "page.rename.tab.ridge",
        "page.rename.tab.ordering",
        "page.rename.tab.numbering",
    )


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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._input_bundle: dict[str, Any] | None = None
        self._current_points_source: str = ""
        self._dom_layers_cache: list[dict[str, str]] = []

        # Debounce timer for reactive updates
        self._update_timer = QTimer(self)
        self._update_timer.setSingleShot(True)
        self._update_timer.setInterval(800)  # 800ms delay
        self._update_timer.timeout.connect(self._on_parameter_update_timeout)

        # Track which type of parameter changed
        self._pending_update_type: Optional[str] = None

        self._init_controls()

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
        self.nav.setCurrentItem(widget.objectName())
        qrouter.push(self.stacked_widget, widget.objectName())

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
        layout.addWidget(BodyLabel(tr(label_key)))
        layout.addWidget(widget)
        return wrapper

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
        self.combo_direction.addItems(
            [
                tr("page.rename.combo.auto"),
                tr("page.rename.combo.x"),
                tr("page.rename.combo.y"),
            ]
        )
        self.combo_direction.currentIndexChanged.connect(
            lambda: self._schedule_update("ridge")
        )

        self.spin_strength = SpinBox()
        self.spin_strength.setRange(1, 100)
        self.spin_strength.setValue(10)
        self.spin_strength.valueChanged.connect(lambda: self._schedule_update("ridge"))

        self.spin_distance = SpinBox()
        self.spin_distance.setRange(1, 50)
        self.spin_distance.setValue(3)
        self.spin_distance.valueChanged.connect(lambda: self._schedule_update("ridge"))

        self.spin_height = SpinBox()
        self.spin_height.setRange(1, 200)
        self.spin_height.setValue(20)
        self.spin_height.valueChanged.connect(lambda: self._schedule_update("ridge"))

        bar.addWidget(
            self._build_labeled_widget(
                "page.rename.label.direction", self.combo_direction
            )
        )
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
        bar.addWidget(self._bar_spacer())
        layout.addWidget(bar)

        # Link RANSAC enable state to numeric inputs
        self.check_ransac.stateChanged.connect(self._update_ransac_ui_state)
        self._update_ransac_ui_state()

        return tab

    def _update_ransac_ui_state(self):
        enabled = self.check_ransac.isChecked()
        self.spin_residual.setEnabled(enabled)
        self.spin_trials.setEnabled(enabled)

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
        map_canvas.remove_layer(layer_name)
        scatter_item = pg.ScatterPlotItem(
            x=xy_array[:, 0],
            y=xy_array[:, 1],
            symbol="o",
            size=7,
            pen=pg.mkPen(color="#3B82F6", width=1.0),
            brush=pg.mkBrush(59, 130, 246, 160),
        )
        scatter_item.setZValue(620)
        map_canvas.add_overlay_item(scatter_item)
        x_min = float(np.min(xy_array[:, 0]))
        y_min = float(np.min(xy_array[:, 1]))
        x_max = float(np.max(xy_array[:, 0]))
        y_max = float(np.max(xy_array[:, 1]))
        map_canvas._layers[layer_name] = {
            "item": scatter_item,
            "visible": True,
            "bounds": LayerBounds(x_min, y_min, x_max, y_max),
        }
        map_canvas._layer_order.append(layer_name)
        map_canvas.sigLayerAdded.emit(layer_name, "Vector")
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

    def _on_parameter_update_timeout(self):
        """Timer finished, emit the update signal."""
        if not self._pending_update_type:
            return

        if self._pending_update_type == "ridge":
            params = {
                "direction_index": self.combo_direction.currentIndex(),
                "strength": self.spin_strength.value(),
                "distance": self.spin_distance.value(),
                "height": self.spin_height.value(),
            }
            self.sigRidgeParamsChanged.emit(params)

        elif self._pending_update_type == "ordering":
            params = {
                "buffer": self.spin_buffer.value(),
                "ransac_enabled": self.check_ransac.isChecked(),
                "residual": self.spin_residual.value(),
                "max_trials": self.spin_trials.value(),
            }
            self.sigOrderingParamsChanged.emit(params)

        elif self._pending_update_type == "numbering":
            params = {"format_index": self.combo_format.currentIndex()}
            self.sigNumberingParamsChanged.emit(params)

        self._pending_update_type = None
