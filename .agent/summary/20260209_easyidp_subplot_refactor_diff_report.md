# EasyIDP Subplot Refactor: Plan vs Implementation Diff Report

## Scope

- Plan reference: `.agent/plans/20260209_easyidp_subplot_refactor_design.md`
- Implementation scope: current `EasyPlantFieldID` repository only
- Related commits:
  - `f754e71` feat(subplot): migrate subplot flow to EasyIDP ROI
  - `66a32c6` refactor(core): drop geopandas core path and use ROI layers
  - `43829ad` docs(agent): add easyidp subplot refactor design note

## Alignment Summary

Overall status: **Mostly aligned**.

- Core objective (remove local subplot core and switch to EasyIDP-native ROI flow) is completed.
- UI parameter model (grid/size + keep) is completed.
- MapCanvas vector path migration (ROI + shp path, no GeoDataFrame) is completed.
- Runtime dependency cleanup (`geopandas` removal) is completed.
- Verification exists, but coverage differs from the original plan in one key area (MapCanvas automated tests).

## Detailed Diff (Planned vs Implemented)

### 1) Architecture and Runtime Path

- **Planned**: GUI calls `easyidp.geotools.generate_subplots()` directly; `idp.ROI` as canonical model.
- **Implemented**:
  - Added `src/gui/tabs/subplot_easyidp.py` as EasyIDP helper layer.
  - `src/gui/tabs/subplot_generate.py` now uses EasyIDP helper functions and ROI objects.
  - `src/core/subplot_generator.py` and `src/core/__init__.py` removed.
- **Result**: aligned.

### 2) Save Flow

- **Planned**: save via `ROI.save()`.
- **Implemented**:
  - Save path uses `ROI.save(..., name_field="id")`.
  - Added normalization for missing extension so output is enforced to `.shp`.
- **Result**: aligned, with an extra robustness fix beyond plan.

### 3) UI Parameters

- **Planned**: support grid/size dual mode and add `keep` (`all/touch/inside`).
- **Implemented**:
  - `src/gui/components/property_panel.py` adds Keep dropdown and signal wiring.
  - i18n keys added in `src/gui/resource/i18n/en_US.json`, `src/gui/resource/i18n/zh_CN.json`, `src/gui/resource/i18n/ja_JP.json`.
  - Mode-dependent kwargs mapping implemented in helper logic.
- **Result**: aligned.

### 4) MapCanvas Refactor

- **Planned**: `add_vector_layer()` accepts ROI or shp path; parse ROI coords directly; no GeoDataFrame.
- **Implemented**:
  - `src/gui/components/map_canvas.py` now normalizes input to ROI (`idp.ROI` or path).
  - Vector rendering uses flattened `numpy` arrays with `NaN` separators.
  - Bound calculation replaced with internal bounds container.
  - GeoPandas path removed.
- **Result**: aligned.

### 5) Dependency Cleanup

- **Planned**: remove runtime `geopandas` after migration.
- **Implemented**:
  - Removed `geopandas` from `pyproject.toml`.
  - `uv.lock` updated accordingly.
- **Result**: aligned.

### 6) Testing and Verification

- **Planned**:
  1. parameter mapping tests,
  2. ROI output contract tests,
  3. MapCanvas ROI/path tests,
  4. manual GUI verification.
- **Implemented**:
  - Added `tests/test_subplot_easyidp.py` with:
    - grid/size param mapping tests,
    - generate+save test,
    - missing extension normalization test.
  - Removed legacy `tests/test_subplot_generator.py`.
  - Project test command passed (`uv run pytest`).
- **Gap**:
  - No dedicated automated MapCanvas test file was added for ROI/path vector loading.
- **Result**: partially aligned.

## Post-Plan Findings and Fixes

During manual GUI validation, two issues surfaced and were handled:

1. Missing `.shp` extension caused `ROI.save()` failure.
   - Fixed in current repo via output-path normalization in `src/gui/tabs/subplot_easyidp.py`.

2. `.prj` format compatibility in QGIS (WKT2 vs WKT1).
   - Root cause identified in EasyIDP writer behavior.
   - Addressed in sibling repo `../EasyIDP` by adding `wkt_version` control in save/write functions and tests.
   - This fix is **external dependency work**, not a direct code change inside this repo.

## Unplanned/Out-of-Scope Workspace Changes

These are present in workspace status but not part of the refactor design execution itself:

- `.gitignore` modified (test output ignore rule)
- `tests/files` untracked dataset/model artifacts

## Final Assessment

- Design intent was implemented successfully for the core migration path.
- Main remaining technical debt against the original plan: add automated MapCanvas ROI/path tests.
- Operationally, the workflow is now EasyIDP-native end-to-end in this repo.

## Suggested Follow-up (Optional)

1. Add `tests/test_map_canvas_vector_roi.py` covering ROI object and shp path loading.
2. Optionally expose `wkt_version` in GUI export settings (if users need explicit WKT2 export).
3. Add a short developer note linking EasyIDP `wkt_version` behavior for GIS compatibility.
