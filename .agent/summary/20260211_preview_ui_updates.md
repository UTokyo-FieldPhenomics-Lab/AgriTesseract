# Preview UI Updates

## 1. Disable Buttons when No DOM Loaded
- **`src/gui/tabs/seedling_detect.py`**:
    - Renamed `_apply_weight_availability` to `_update_button_states`.
    - Added check for `self._dom_path`.
    - Buttons now require both "weights exist" AND "DOM loaded" (where applicable).

## 2. Auto-Hide Preview Layers on Tab Switch
- **`src/utils/seedling_detect/preview_controller.py`**:
    - `set_preview_layers_visibility` toggles visibility on `MapCanvas` side.
- **`src/gui/tabs/seedling_detect.py`**:
    - Calls controller's visibility toggle on tab change.

## 3. Sync Layer Panel Visibility
- **`src/gui/components/map_canvas.py`**:
    - Added `sigLayerVisibilityChanged(str, bool)`.
    - Emitting this signal in `set_layer_visibility`.
- **`src/gui/components/map_component.py`**:
    - Connected `MapCanvas.sigLayerVisibilityChanged` -> `LayerPanel.set_layer_visibility`.

Confirmed behavior:
- Buttons disabled until DOM+Weights are ready.
- Preview layers hide/unhide when switching tabs.
- Layer Panel checkboxes (file tree) update automatically when preview layers are programmatically hidden/shown on tab switch.
