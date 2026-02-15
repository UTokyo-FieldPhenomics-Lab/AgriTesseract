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

## Module 04 (2026-02-15)

### Scope

Completed plan file:

- `.agent/plans/20260213_rename_ids_module_04_ridge_spacing_and_peak_detection.md`

Key delivered capability:

- Ridge spacing and peak detection diagnostics panel in Rename IDs.
- Bottom diagnostics panel host + show/hide/collapse behavior.
- Ridge density profile + peak detection + detected ridge line overlay.
- Focus-ridge workflow with fit-axis and synchronized panel refresh.

### Commit Timeline and Functional Meaning

- `6d7baab` feat(task1-3): add bottom panel host and ridge diagnostics foundations
  - Added bottom host container and `MapComponent` vertical layout integration.
  - Added `BottomPanelFigure`/`RidgeFigurePanel` and core ridge density utility functions.
- `4a628f5` fix(task1): keep bottom panel draggable when collapsed
  - Fixed collapsed-state drag-out behavior by preserving minimal collapsible height.
- `b4b28bf` feat(task4): wire ridge diagnostics to panel and map overlay
  - Connected ridge parameter updates to diagnostics controller and map overlay refresh.
- `683dcd9` fix(task4): align ridge plot theme and preserve density valleys
  - Theme-aware plot colors for light/dark and contiguous histogram bins with zero valleys.
- `9ddf96b` fix(task4): refine ridge labels, flyouts, and chart layout
  - i18n label refinements, click-trigger flyout help text, compact chart titles/labels.
- `129efa5` fix(task5): preserve fit aspect and sync rotated hover preview
  - Fit width/height keeps map aspect ratio; hover coordinate transform unified with click path.
- `d9f2fe6` fix(task6): restore ridge panel state and synchronize focus refresh
  - Restored bottom panel content after collapse/return and synchronized focus with panel x/y range updates.

## User-Requested Manual Fixes Included

### Module 02

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

### Module 04

1. No visible trigger for bottom panel show/hide in UI

- Cause: wiring stage incomplete before controller integration.
- Fix: hooked diagnostics pipeline into ridge update flow; panel auto-shows when direction is valid.

2. Bottom panel could not be dragged back from collapsed state

- Cause: panel content stack was fully hidden with no restore path.
- Fix: kept collapsible host height; added content restoration when splitter is dragged up.

3. Plot background black did not match light mode / dark mode mismatch

- Cause: fixed plot colors were used.
- Fix: applied theme-aware palette bound to app theme changes.

4. Ridge density looked like a nearly flat line and parameter changes had weak effect

- Cause: histogram built only on occupied bins, losing valleys between ridges.
- Fix: switched to contiguous bin construction with zero-count valleys.

5. Parameter names unclear (`strength`, `distance`, `height`)

- Fix: updated i18n labels to user-facing terms:
  - `Density Bin Width`
  - `Min Peak Spacing`
  - `Peak Count Threshold`
- `distance` semantics updated to float meters and converted to peak-bin distance internally.

6. Teaching tip interaction style and chart compactness adjustments requested

- Fix: replaced hover teaching tip with click-triggered simple flyout.
- Fix: removed bottom x-label text and reduced title size for more y-axis plotting area.

7. Fit width/height should not distort view geometry

- Cause: independent axis setting behavior led to apparent distortion.
- Fix: fit-axis methods now maintain current x:y view ratio and scale counterpart axis accordingly.

8. Manual ridge preview did not follow mouse when map rotation was non-zero

- Cause: hover path used different coordinate transform than click path.
- Fix: hover uses the same item-space transform chain as click handling.

9. After auto-hide, returning to ridge did not automatically restore panel

- Fix: on returning to ridge tab with valid direction, diagnostics rerun and panel restored.

10. After dragging panel up from bottom, only gray background appeared (plot missing)

- Fix: added explicit panel-content restore API and splitter-move restoration hook.

11. Focus ridge should synchronize bottom panel and y-range to min-max

- Fix: focus action now also reruns diagnostics for panel sync.
- Fix: controller now computes y-range from data/peaks/threshold min-max with padding.

## Verification Snapshot

- `uv run pytest tests/rename_ids -v` -> `58 passed`
- `uv run pytest` -> `112 passed`

Additional targeted suites were also used during TDD red-green cycles for:

- bottom panel collapse/restore behavior
- map canvas fit-axis behavior
- rotated hover coordinate consistency
- ridge focus and panel visibility rules