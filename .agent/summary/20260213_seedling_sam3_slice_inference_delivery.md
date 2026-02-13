# Seedling SAM3 Slice Inference Delivery Summary (2026-02-13)

## Scope

This delivery completed the Seedling SAM3 full-map slice inference workflow, post-processing controls, visualization layers, and GIS export/send-next flow.

- Base branch: `master`
- Feature branch used: `feat/seedling-sam3-slice-inf-gis-export`
- Integration mode: fast-forward merge (commit history preserved)

## Commit Timeline (Preserved)

1. `f1e32f9` feat: add boundary-aware slice filtering modes for seedling inference
2. `36abc66` feat: add background full-map SAM3 worker with progress signals
3. `a96ff84` feat: wire full inference thread lifecycle and live status progress
4. `acd7190` fix(inference): reuse SAM3 predictor across slice loop
5. `0900abc` feat: merge slice detections via NMS and render result bbox/points layers
6. `ed770d1` feat: add toggleable boundary and overlay pruning for slice results
7. `cd1c92e` feat: export bbox and center points shapefiles from merged results
8. `311973e` feat: move boundary loader and export polygon/send-next workflow
9. `3266729` feat: render vivid result polygon layer for full inference
10. `becd706` feat: refine save/send workflow with prefix export and layer sync

## Key Functional Outcomes

### 1) Full-map SAM3 inference pipeline

- Added background full-map inference worker in `src/utils/seedling_detect/qthread.py`.
- Implemented progress signal wiring and UI status updates in `src/gui/tabs/seedling_detect.py`.
- Fixed repeated model initialization by reusing a single predictor instance during slice loops.

### 2) Slice post-processing and filtering

- Added boundary-aware slice filtering (`inside` / `intersect`).
- Added global IoU NMS merge and IoS-based overlay suppression.
- Added boundary-touch box pruning (except global image edges) with user toggles.

### 3) Visualization layers in map canvas

- Added result layers:
  - `result_bbox`
  - `result_points`
  - `result_polygon` (vivid per-instance colors)
- All result layers now refresh together based on:
  - `rm boundary`
  - `rm overlay`
  - `iou_tresh`
  - `ios_tresh`

### 4) Export and downstream handoff

- Save workflow now uses path prefix selection (not folder-only).
- Export naming now follows:
  - `<prefix>_bbox.shp`
  - `<prefix>_points.shp`
  - `<prefix>_polygon.shp`
- `send to next` now:
  - loads exported points into Rename IDs flow,
  - copies `result_points` overlay into target map canvas,
  - switches tab and performs `zoom_to_layer("result_points")`.

### 5) UI and copy updates

- Moved `Load Boundary SHP` to File top-tab row next to DOM path info.
- Updated i18n strings in:
  - `src/gui/resource/i18n/zh_CN.json`
  - `src/gui/resource/i18n/en_US.json`
  - `src/gui/resource/i18n/ja_JP.json`

## Code/Test Footprint

- Files changed: 16
- Net diff: `1713 insertions`, `127 deletions`

Primary modules touched:

- `src/gui/tabs/seedling_detect.py`
- `src/utils/seedling_detect/slice.py`
- `src/utils/seedling_detect/qthread.py`
- `src/utils/seedling_detect/sam3.py`
- `src/utils/seedling_detect/preview_controller.py`
- `src/utils/seedling_detect/io.py`

Tests expanded:

- `tests/test_seedling_slice.py`
- `tests/test_seedling_preview_worker.py`
- `tests/test_seedling_sam3.py`
- `tests/test_seedling_io.py`
- `tests/test_seedling_preview.py`
- `tests/test_seedling_tab_layout.py`

## Verification

Final full-suite verification command:

```bash
uv run pytest -q
```

Result:

- `32 passed`

## Branch/Worktree Finalization

- Feature worktree removed:
  - `.worktrees/seedling-sam3-slice-inf-gis-export`
- Feature branch deleted locally:
  - `feat/seedling-sam3-slice-inf-gis-export`
- `master` now contains the full commit history above (no squash).
