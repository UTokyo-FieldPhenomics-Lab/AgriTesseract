# Replace Seedling InfoBar with StateToolTip

## User Request
Replace the one-time `InfoBar` notification during preview inference (`src/gui/tabs/seedling_detect.py`) with a persistent `StateToolTip` that shows "Running..." and updates to "Finished!" on success, similar to the `status_info_interface.py` example.

## Changes

### `src/gui/tabs/seedling_detect.py`

1.  **Imported `StateToolTip`** from `qfluentwidgets`.
2.  **Added `self.stateTooltip`** initialization in `__init__`.
3.  **Modified `_set_preview_running_ui`**:
    -   Instead of showing an ephemeral `InfoBar.info`, it now creates and shows a `StateToolTip`.
    -   Used `tr("info")` as title and `tr("page.seedling.msg.preview_running")` as content.
    -   Positioned the tooltip using `getSuitablePos()`.
    -   Added cleanup logic to close the tooltip if it wasn't handled by a success state (i.e., on failure or cancellation).
4.  **Modified `_on_preview_inference_finished`**:
    -   Updates the `StateToolTip` to show a success message (`tr("page.seedling.msg.preview_finished") + " 😆"`) and sets its state to `True` (done), which triggers its completion animation.

## Verification
-   The `StateToolTip` lifecycle is managed: created on start, updated on success, closed on failure/cancellation.
-   Used positional arguments for `StateToolTip` constructor to match the reference implementation and avoid verify keyword argument issues.
