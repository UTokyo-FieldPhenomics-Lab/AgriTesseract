# Map Canvas & UI Implementation Guide

This document summarizes the technical implementation, development logic, and key considerations for the Map View, Layer Panel (Tree View), and Status Bar components in `AgriTesseract`.

## 1. Map Canvas (`src/gui/components/map_canvas.py`)

The `MapCanvas` is built on top of `pyqtgraph`. It handles raster/vector rendering, coordinate systems, and user interaction.

### Core Mechanisms

*   **Rendering Engine**: Uses `pg.PlotWidget` with a custom `ViewBox` (`CustomViewBox`).
*   **Layer Management**: Layers are stored in `self._layers` (dict) and `self._layer_order` (list). Raster data is managed via `rasterio`.
*   **Lazy Loading**: To handle large GeoTiffs, we use `rasterio`'s windowed reading. Only the currently visible portion of the image is loaded and rendered (`_update_visible_tiles`).

### Zooming & Scaling

*   **Implementation**: `set_zoom(zoom_percent)`
*   **Logic**:
    *   **Base Reference**: Zoom level 100% corresponds to fitting the *first loaded layer's width* to the view.
    *   **Calculation**:
        ```python
        target_width = base_width / (zoom_percent / 100.0)
        ```
    *   **Applied via**: `self._view_box.setRange(rect)`.
    *   **Signal**: `sigZoomChanged` is emitted when the view range changes (debounced in `_on_view_changed`), calculating percentage relative to the base width.

### Rotation

*   **Implementation**: `set_rotation(angle)`
*   **Logic**:
    *   The map content (`self._item_group`) is rotated, *not* the camera (`ViewBox`). This simplifies coordinate handling for the view rect.
    *   **Transform**: `item_group.setRotation(-angle)`. Negative because QGraphicsView clockwise/counter-clockwise conventions implies opposite for "map rotation".
    *   **Critical Fix**: Changing rotation MUST trigger `self._update_timer.start()` to recalculate the visible region. Without this, the raster data won't reload for the new angled view, leading to clipping artifacts.

### Clipping (Visible Region Loading)

*   **Implementation**: `_load_visible_region()`
*   **Coordinate Transformation**:
    *   Since the `item_group` is rotated, the `ViewBox`'s visible rectangle (in screen/view coordinates) does not match the data coordinates directly.
    *   **Inverse Transform**: We transform the `ViewBox` rect using the *inverse* of the rotation to find the corresponding bounding box in the original GeoTiff coordinate space.
        ```python
        transform.rotate(self._rotation_angle)
        bbox = transform.mapRect(view_rect)
        ```
    *   This `bbox` is then converted to a `rasterio.windows.Window` to read the correct data chunks.

### Coordinate Tracking

*   **Implementation**: `pg.SignalProxy` + `_on_mouse_moved`
*   **Reason**: `ViewBox` event overrides can be unreliable for continuous hovering. `SignalProxy` listening to `scene().sigMouseMoved` is more robust.
*   **Mapping**: `self._view_box.mapSceneToView(pos)` converts screen pixels to map coordinates (Projected CRS).

---

## 2. Layer Panel (`src/gui/components/layer_panel.py`)

The Layer Panel manages the stack of map layers using `qfluentwidgets.TreeWidget`.

### UI Structure

*   **Component**: `DraggableTreeWidget` (subclass/alias of `TreeWidget`).
*   **Items**: Each layer is a `QTreeWidgetItem`.
*   **Icons**: Used `qfluentwidgets.FluentIcon` (`IMAGE_EXPORT` for Raster, `TRANSPARENT` for Vector) instead of Emoji prefixes to avoid string parsing issues.

### Functionality

*   **Ordering**:
    *   **Drag & Drop**: Enabled properly on the widget.
    *   **Sync**: When a drop event occurs, the widget updates visual order. We must capture this (or iterate items) to update `MapCanvas`.
    *   **Signal**: `sigLayerOrderChanged` emits the new list of layer names. `MapCanvas` receives this and updates `zValue` of `ImageItems` (higher index = higher Z).

*   **Visibility**:
    *   Checkbox in Tree Item.
    *   **Signal**: `sigLayerVisibilityChanged(layer_name, is_visible)`. Connected to `MapCanvas.set_layer_visibility`.

*   **Context Menus**:
    *   **Background Menu**: Right-click on empty space -> "Add Layer".
    *   **Item Menu**: Right-click on layer -> "Zoom to Layer", "Delete".
    *   **Customization**: Uses `RoundMenu`. `exec` at cursor position (`QCursor.pos()`).

---

## 3. Status Bar (`src/gui/components/status_bar.py`)

The Status Bar provides interactive control using Fluent UI components.

### Layout Strategy

*   **Ratio**: 1:1:1 split for Coordinates, Zoom, and Rotation.
*   **Container**: Uses 3 `QWidget` containers with `QHBoxLayout`.
*   **Expansion**:
    *   `layout.addWidget(container, 1)`: The `1` is the stretch factor, ensuring equal width.
    *   **Input Full Width**: Inside the container, the `DoubleSpinBox` is added with `layout.addWidget(sb, 1)` to automatically fill available space. Fixed widths were removed to prevent truncation.

### Interactive Controls

*   **Components**: `DoubleSpinBox` (Fluent).
*   **Visuals**:
    *   Labels ("Zoom:", "Rotation:") are placed *outside* the SpinBox for cleaner styling.
    *   Prefixes inside SpinBox were removed to avoid clutter.
*   **Bidirectional Synchronization**:
    *   **Map -> StatusBar**: User scrolls/pans map -> `MapCanvas` emits `sigZoomChanged`/`sigRotationChanged` -> `StatusBar` updates SpinBox value (blocking signals temporarily to avoid loop).
    *   **StatusBar -> Map**: User types value -> `StatusBar` emits signal -> `MapCanvas` calls `set_zoom`/`set_rotation`.

### Key Considerations

*   **Signal Loops**: When updating UI from Map signals, block signals on the input widgets (`self.zoom_sb.blockSignals(True)`) to prevent triggering a "user changed value" event back to the map.
*   **Real-time Updates**: Coordinates update on hover via the `MapCanvas` signal connection described in Section 1.
