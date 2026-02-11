# Preview Controller Fixes

## 1. Fix: Preview Size Adjustment & Keyboard Focus
The `+`, `-`, and `Esc` keys were not working because `MapCanvas` did not have keyboard focus when hovering.
- **`src/gui/components/map_canvas.py`**:
  - Implemented `eventFilter` on both `_plot_widget` and `_plot_widget.viewport()` to intercept keys.
  - Added `self.setFocusProxy(self._plot_widget)` to ensure `MapCanvas` forwards focus correctly.
  - Added logging for debugging.

- **`src/gui/tabs/seedling_detect.py`**:
  - Added `self.map_component.map_canvas.setFocus()` inside `_on_pick_preview_toggled` to force focus immediately when entering preview mode.

## 2. Feature: Exit Preview Mode with Escape Key
Implemented `Esc` to stop picking preview.
- **`src/utils/seedling_detect/preview_controller.py`**:
  - Logic added to handle `Esc` and emit `sigRequestPreviewModeStop`.

## 3. Logging Fix
- **`launch.py`**:
  - Fixed logging override issue caused by `easyidp`.

Confimed working: Keys +/-, Esc work correctly after clicking "Pick Preview" button, even before clicking on the canvas.
