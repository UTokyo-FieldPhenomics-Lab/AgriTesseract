# 20260211 Seedling Code Refactoring

## Overview
Refactored seedling detection and subplot generation code from flat layout into organized submodules, extracted preview-specific logic from `map_canvas.py`.

## Changes

### New Submodule: `src/utils/seedling_detect/`
| File | Source | Notes |
|---|---|---|
| `__init__.py` | NEW | Re-exports all public API |
| `cache.py` | `seedling_cache.py` | No content change |
| `io.py` | `seedling_io.py` | No content change |
| `points.py` | `seedling_points.py` | No content change |
| `preview.py` | `seedling_preview.py` | Added `polygon_px_to_geo()` from worker |
| `preview_controller.py` | NEW | Extracted from `map_canvas.py` preview logic |
| `qthread.py` | `gui/tabs/seedling_preview_worker.py` | Renamed, `_polygon_px_to_geo` moved to `preview.py` |
| `sam3.py` | `seedling_sam3.py` | No content change |
| `slice.py` | `seedling_slice.py` | No content change |

### New Submodule: `src/utils/subplot_generate/`
| File | Source |
|---|---|
| `__init__.py` | NEW |
| `io.py` | `gui/tabs/subplot_easyidp.py` |

### Modified Files
- **`map_canvas.py`**: Removed all preview-specific code (signals, state, constants, box item, methods). Added generic `add_overlay_item()`/`remove_overlay_item()` API, `_key_handlers`, `_hover_handlers`, `_click_handlers` delegation lists. Restored generic event handlers.
- **`seedling_detect.py` (tab)**: Import from `seedling_detect.qthread` + `preview_controller`. Creates `SeedlingPreviewController` and registers its handlers with map_canvas. All preview method calls go through `self._preview_ctrl`.
- **`utils/__init__.py`**: Updated all import paths to submodules
- **`gui/tabs/subplot_generate.py`**: Import from `subplot_generate.io`
- **8 test files**: Updated import paths

### Deleted Files
- `src/utils/seedling_cache.py`, `seedling_io.py`, `seedling_points.py`, `seedling_preview.py`, `seedling_sam3.py`, `seedling_slice.py`
- `src/gui/tabs/seedling_preview_worker.py`, `subplot_easyidp.py`

### Bug Fixes
- `test_seedling_sam3.py`: Fixed pre-existing function name mismatch (`_extract_polygons_px` → `_extract_polygons_from_mask_xy`)

## Test Results
```
21 passed in 2.47s
```
