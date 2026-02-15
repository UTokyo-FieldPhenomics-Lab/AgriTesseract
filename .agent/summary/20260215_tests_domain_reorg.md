# Tests Domain Reorganization Summary

## Background

Reorganized the `tests` directory from a mostly flat layout into first-level
functional domains, aligned with current product feature areas.

Target domains:

- `tests/rename_ids/`
- `tests/subplot_generate/`
- `tests/seedling_detection/`
- `tests/map_canvas/`

This change improves test discoverability and keeps each feature's tests grouped
in one place.

## Key Changes

### 1) File migration and renaming

- Moved map canvas tests into `tests/map_canvas/`.
- Moved subplot tests into `tests/subplot_generate/`.
- Moved seedling tests into `tests/seedling_detection/`.
- Kept existing `tests/rename_ids/` tests in place.
- Renamed files inside domain folders to remove repeated prefixes, for example:
  - `test_seedling_io.py` -> `test_io.py`
  - `test_subplot_generator.py` -> `test_generator.py`
  - `test_map_canvas_layer_order.py` -> `test_layer_order.py`

### 2) Dependency contract test placement

- Moved dependency contract test to subplot domain:
  - `tests/subplot_generate/test_dependency_contract.py`

Reason: this contract validates the subplot-side dependency migration away from
EasyIDP and toward GeoTIFF/GeoPandas-based flow.

### 3) Pytest import/bootstrap stabilization after reorganization

After moving tests into nested folders, collection initially failed due to:

- `ModuleNotFoundError: No module named 'src'` in nested test packages.
- Test module basename collision (`test_io.py`) across domains.

Fixes:

- Added shared `tests/conftest.py` to append repository root to `sys.path`.
- Added package markers:
  - `tests/map_canvas/__init__.py`
  - `tests/seedling_detection/__init__.py`
  - `tests/subplot_generate/__init__.py`
  - `tests/rename_ids/__init__.py`

## Verification

Executed full test suite:

```bash
uv run pytest
```

Result:

- `76 passed in 6.46s`

All tests collect and pass under the new domain-based structure.
