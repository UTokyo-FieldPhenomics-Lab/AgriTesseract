# Fix Preview Region Visibility

## Background
The user reported that the "Preview Regions" layer (interactive picking box) occasionally reappeared when switching away from the "SAM3 Preview" tab in `gui/tabs/seedling_detect.py`. 
Although `set_preview_layers_visibility(False)` was called on tab switch, the interactive handlers (`hover`) in `preview_controller.py` were still active if "Pick Preview" mode was enabled, leading to the layer being re-shown.

## Changes

### `src/utils/seedling_detect/preview_controller.py`

1.  **Added Visibility State**: Introduced `self._layers_visible` boolean flag to track whether the preview layers should be visible.
2.  **Updated Visibility Setter**: Modified `set_preview_layers_visibility` to update the `_layers_visible` flag.
3.  **Guarded Interaction Handlers**: Updated `handle_coordinate_hover`, `handle_click`, `handle_key_press`, and `_update_preview_overlay` to check `_layers_visible`. If false, these methods return early (or force hide the overlay), preventing unwanted interactions and visual updates when the tab is not active.

## Verification
- Verified that `_on_tab_changed` in `seedling_detect.py` correctly calls `set_preview_layers_visibility` with the appropriate boolean based on the active tab.
- Verified that the new checks in `preview_controller.py` prevent the preview box from being shown or updated when `_layers_visible` is false.
