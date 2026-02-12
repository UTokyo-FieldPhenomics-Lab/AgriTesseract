# Refactor Rename IDs Topbar Summary

**Date**: 2026-02-12
**Task**: Refactor `rename_ids.py` topbar and move points editing tools.

## Key Changes

### 1. Refactored `src/gui/tabs/rename_ids.py`
- **New UI Structure**: Replaced the old vertical grouped layout with a horizontal `SegmentedWidget` navigation bar.
- **Implemented Top Tabs**:
    - **File**: 
        - Existing `Load SHP`.
        - **New**: `Load Boundary SHP` (to assist ridge direction).
        - **New**: `Load DOM` (for reference layers).
    - **Ridge**: 
        - Implemented parameters from `14_order_by_ridge.py`: Direction, Strength, Distance, Height.
        - Added reactive updates with debounce (signals: `sigRidgeParamsChanged`).
    - **Ordering**:
        - Implemented parameters: Buffer, RANSAC (toggle), Residual, Max Trials.
        - Added reactive updates with debounce (signals: `sigOrderingParamsChanged`).
    - **Numbering**:
        - **Moved Point Editing Tools**: View, Add, Move, Delete, Undo buttons moved from `seedling_detect.py`.
        - Renaming format selection.
        - Reactive updates (signals: `sigNumberingParamsChanged`).

### 2. Updated `src/gui/tabs/seedling_detect.py`
- **Removed Points Tab**: Deleted the redundant "Points" tab and its associated build methods.
- **Updated Slice Inference Tab**:
    - Added **Save SHP** button.
    - Removed **Save/Load Cache** buttons as requested.
- **Bug Fixes**: Resolved `AttributeError` issues by ensuring UI components (`spin_overlap`, `btn_start_inference`) are initialized before adding to layout.

### 3. Localization Updates
- Updated `src/gui/resource/i18n/zh_CN.json`, `en_US.json`, and `ja_JP.json`.
- Added new keys for:
    - Tab names (Ridge, Ordering).
    - New button labels (Load Boundary, Load DOM).
    - New parameter labels (Distance, Height, Buffer, RANSAC, Residual, Max Trials).

## Technical Details
- **Reactive Controls**: Implemented a `QTimer` based debounce mechanism in `RenameTab` to prevent excessive signal emission when adjusting spinboxes/comboboxes.
- **Code Cleanup**: Removed duplicate code in `seedling_detect.py`.

## Verification
- Verified application startup with `uv run launch.py`.
- Confirmed correct UI layout and presence of new controls.
