# Rename IDs Module 02 Changelog (2026-02-14)

## Commit Breakdown (Task 1-5)

1. `e5cb15b` feat(task1): add RenameTab input bundle contract and state  
   - Introduced file-tab input bundle contract and session state fields in `RenameTab`.
   - Added input-ready signaling and updated file-tab i18n labels.

2. `f8d7ab6` feat(task2): add point IO normalization utilities  
   - Added `src/utils/rename_ids/io.py` for point loading/normalization.
   - Added tests: `tests/rename_ids/test_io.py`.

3. `91806ba` feat(task3): add boundary mask and axis preprocessing  
   - Added `src/utils/rename_ids/boundary.py` for CRS alignment, effective mask, and OBB axes.
   - Added tests: `tests/rename_ids/test_boundary.py`.

4. `40948bc` feat(task4): stabilize DOM multi-load ordering across map and tree  
   - Added deterministic DOM bottom-group ordering and layer order sync between map canvas and layer tree.
   - Added DOM duplicate/same-name handling base behavior and related tests.
   - Added tests: `tests/rename_ids/test_dom_loading.py`, `tests/test_map_canvas_layer_order.py`.

5. `9e93924` feat(task5): add object-first send-to-next handoff  
   - Added object-first bundle handoff from Seedling tab to Rename tab, with legacy shapefile fallback.
   - Added tests: `tests/test_tab_handoff.py`.

## User-Requested Manual Fixes Included

1. **DOM load no-op fix**  
   - Fixed issue where single/multi DOM selection in Rename tab did not actually add raster layers.

2. **Layer tree order consistency**  
   - Fixed mismatch where file tree order differed from map canvas layer order.
   - Added explicit order synchronization API/signals to keep both views consistent.

3. **Duplicate DOM interaction and naming behavior**  
   - Added duplicate-path confirmation flow: skip duplicates or load+rename.
   - Upgraded dialog to Fluent `MessageBox` style (mask dialog), aligned with UI system.
   - For same filename with different paths, apply path-hint naming and rename both existing/new entries (not only new one).

4. **DOM internal stack ordering refinement**  
   - Ensured newly added DOM appears above previous DOM layers while DOM group remains below vector layers.

## Test Status

- Full suite passed after split and fixes: `uv run pytest` -> `54 passed`.
