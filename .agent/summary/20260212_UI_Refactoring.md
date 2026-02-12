# 2026-02-12 UI Refactoring: Subplot & Main Interface

## Summary
Refactored the Subplot Generation tab to use a modern "Segmented Control" top bar, migrated controls from the right sidebar, and globally disabled the right sidebar to clean up the interface. Enhanced the Map Canvas with a context menu and the Status Bar with status indicators.

## Changes
### UI / UX
- **Global**: Disabled `PropertyPanel` (Right Sidebar) for all tabs in `BaseInterface`.
- **Subplot Tab**:
    - Replaced side panel controls with Top Bar navigation (`SegmentedWidget`).
    - Organized controls into **File**, **Layout**, **Numbering**, **Output** tabs.
    - Removed "Preview" checkbox (auto-enabled).
- **Map Canvas**:
    - Added Context Menu with **Focus** (Zoom to Fit) and **Rotate** actions.
    - Fixed initialization order for rotation/item groups.
- **Status Bar**:
    - Added `InfoBadge` support for status messages.
    - Added `ProgressBar` and `IndeterminateProgressBar` for heavy operations.

### Code
- `src/gui/tabs/subplot_generate.py`: Complete rewrite of UI setup to use `qfluentwidgets` components directly.
- `src/gui/components/map_canvas.py`: Added `_show_context_menu` and fixed `_init_ui` logic.
- `src/gui/components/status_bar.py`: Implemented `set_status` and `set_progress` methods.
- `src/gui/components/base_interface.py`: Hidden `property_panel` by default.

## Verification
- **Launch**: Verified application starts without errors.
- **Tab Switching**: Verified switching between top bar tabs works correctly.
- **Functionality**:
    - Loading Image/Boundary works (Status Bar updates).
    - Subplot Preview updates on parameter change.
    - Context Menu "Focus" and "Rotate" work.
    - "Save SHP" triggers generation and status updates.
