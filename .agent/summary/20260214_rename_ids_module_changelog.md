# Rename IDs Module Changelog (2026-02-14)

## Scope

- This changelog consolidates Rename IDs module updates across Module 02 and Module 03.
- It also records user-reported UI/interaction fixes delivered during implementation.

## Module 02 (File Inputs and Layers)

### Commit Breakdown

1. `e5cb15b` feat(task1): add RenameTab input bundle contract and state
   - Added file-tab input bundle contract and session state fields in `RenameTab`.
   - Added input-ready signaling and updated file-tab i18n labels.

2. `f8d7ab6` feat(task2): add point IO normalization utilities
   - Added `src/utils/rename_ids/io.py` for point loading and normalization.
   - Added tests: `tests/rename_ids/test_io.py`.

3. `91806ba` feat(task3): add boundary mask and axis preprocessing
   - Added `src/utils/rename_ids/boundary.py` for CRS alignment, effective mask, and OBB axes.
   - Added tests: `tests/rename_ids/test_boundary.py`.

4. `40948bc` feat(task4): stabilize DOM multi-load ordering across map and tree
   - Added deterministic DOM bottom-group ordering and layer-order sync between map canvas and layer tree.
   - Added duplicate/same-name DOM handling base behavior and related tests.
   - Added tests: `tests/rename_ids/test_dom_loading.py`, `tests/test_map_canvas_layer_order.py`.

5. `9e93924` feat(task5): add object-first send-to-next handoff
   - Added object-first bundle handoff from Seedling tab to Rename tab, with legacy shapefile fallback.
   - Added tests: `tests/test_tab_handoff.py`.

## Module 03 (Ridge Direction Selection and Interaction)

### Commit Breakdown

1. `189d21a` feat(task3): add ridge direction sources and manual draw flow
   - Added ridge direction utility module and source mapping (`boundary_x/y/-x/-y`, `manual_draw`).
   - Added ridge tab direction source UI foundation and manual two-click flow.

2. `b7e1a1e` fix(task3): remove overlay arrow and clear boundary ridge on manual
   - Removed extra map-only arrow overlay after manual draw completion.
   - Fixed boundary-to-manual switch cleanup for stale ridge-direction layer artifacts.

3. `0dfcb28` feat(task4): add ridge rotation confirm dialog and focus action
   - Added Fluent `MessageBox` confirmation (mask dialog style) before applying rotation.
   - Added `focus ridge` action to apply saved ridge-follow rotation angle on demand.

4. `57eb457` fix(task4): correct ridge rotation angle sign
   - Corrected rotation angle sign convention to match `MapCanvas.set_rotation` behavior.
   - Added regression assertions for sign-sensitive rotation behavior.

5. `a40d393` feat(task5): enforce mode exclusion and ridge payload contract
   - Enforced manual-draw mode exclusion with numbering edit tools (`add/move/delete`).
   - Migrated ridge payload from `direction_index` to semantic contract:
     - `ridge_direction_source`
     - `ridge_direction_vector`
     - `rotation_angle_deg`

6. `c77be92` fix(task5): use toggle ridge button and restore manual reactivation
   - Switched "set ridge direction" to Fluent toggle interaction with accent active state.
   - Fixed manual mode lifecycle so it exits after confirmation and can be reactivated reliably.

7. `7d3dc49` feat(task6): sync ridge state with layer deletions
   - Added layer-removal-driven state sync:
     - deleting `Boundary` reverts direction options to manual-only and clears boundary-derived ridge state
     - deleting `rename_points` disables ridge controls and clears dependent runtime state
   - Added guarded internal layer removal to avoid false-positive sync loops.

## User-Requested Manual Fixes Included

1. DOM load no-op bug fix and tree/map ordering consistency fixes.
2. Duplicate DOM UX upgrades:
   - Fluent dialog interaction
   - same-filename/different-path rename strategy with path hints.
3. Ridge-direction rendering and interaction refinements:
   - moved to `MultiLineString` arrow representation (shaft + inverted-V head)
   - removed stale overlays and stale boundary arrow artifacts on mode switches.
4. Ridge rotation UX refinements:
   - confirm-before-rotate
   - focus-ridge reapply
   - corrected sign direction (`-92.82` style expected behavior).
5. Manual draw workflow refinements:
   - toggle accent state while active
   - deactivation after two-click confirmation
   - reliable reactivation on subsequent toggles.

## Verification Snapshot

- Rename IDs regression: `uv run pytest tests/rename_ids -v` -> `31 passed`
- Full project regression: `uv run pytest` -> `75 passed`
