# Restore GeoPandas and Remove EasyIDP Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Restore the GeoPandas-based shapefile workflow (read `.shp` into `GeoDataFrame`) and fully remove EasyIDP runtime dependency.

**Architecture:** Revert vector data model from `idp.ROI` back to `geopandas.GeoDataFrame` at utility, UI, and map canvas boundaries. Keep current UI behavior, but change internal types and generation logic to GeoPandas/Shapely. Use commit history around `66a32c6`, `f754e71`, and `9e2b4b4` as functional reference, not blind file rollback.

**Tech Stack:** Python 3.12, GeoPandas, Shapely, Rasterio, PySide6, PyQtGraph, pytest (`uv run pytest`), uv lock.

---

### Task 1: Dependency Contract First (TDD for deps)

**Files:**
- Create: `tests/test_dependency_contract.py`
- Modify: `pyproject.toml:9-30`
- Modify: `pyproject.toml:74-75`
- Modify: `uv.lock` (generated)
- Check reference: commit `9e2b4b483c2908a384c4b9d5b615ddb838b909f9`
- Check reference: commit `66a32c6be8b398b8af731a826a42c5c27f5bcec1`

**Step 1: Write the failing test**

```python
from pathlib import Path
import tomllib

def test_runtime_dependencies_contract() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    deps = data["project"]["dependencies"]
    assert any(d.startswith("geopandas") for d in deps)
    assert not any(d.startswith("easyidp") for d in deps)

def test_no_local_easyidp_uv_source() -> None:
    data = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))
    sources = data.get("tool", {}).get("uv", {}).get("sources", {})
    assert "easyidp" not in sources
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_dependency_contract.py -v`  
Expected: FAIL with geopandas missing / easyidp still present.

**Step 3: Write minimal implementation**

- Add `geopandas>=1.1.1` back into `dependencies`.
- Remove `"easyidp"` from `dependencies`.
- Remove `[tool.uv.sources].easyidp`.
- Regenerate lockfile with uv.

Run: `uv lock`

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_dependency_contract.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add pyproject.toml uv.lock tests/test_dependency_contract.py
git commit -m "build(deps): restore geopandas and drop easyidp source"
```

---

### Task 2: Restore GeoDataFrame IO/Generation Utilities

**Files:**
- Modify: `src/utils/subplot_generate/io.py`
- Modify: `src/utils/subplot_generate/__init__.py`
- Create: `tests/test_subplot_geodataframe_io.py`
- Check reference: `66a32c6^:src/core/subplot_generator.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
import geopandas as gpd
import pytest
from shapely.geometry import Polygon

from src.utils.subplot_generate.io import (
    load_boundary_gdf,
    generate_subplots_gdf,
    generate_and_save_gdf,
)

def test_load_boundary_gdf_reads_single_polygon(tmp_path: Path) -> None:
    poly = Polygon([(0,0), (100,0), (100,100), (0,100), (0,0)])
    src = gpd.GeoDataFrame({"id":[1]}, geometry=[poly], crs="EPSG:3857")
    shp = tmp_path / "boundary.shp"
    src.to_file(shp)

    gdf = load_boundary_gdf(shp)
    assert len(gdf) == 1
    assert gdf.geometry.iloc[0].geom_type in {"Polygon", "MultiPolygon"}

def test_generate_and_save_gdf_writes_shapefile(tmp_path: Path) -> None:
    poly = Polygon([(0,0), (100,0), (100,100), (0,100), (0,0)])
    gdf = gpd.GeoDataFrame({"id":[1]}, geometry=[poly], crs="EPSG:3857")
    out = tmp_path / "subplots.shp"

    result = generate_and_save_gdf(
        boundary_gdf=gdf, mode_index=0, rows=2, cols=2,
        width=2.0, height=2.0, x_spacing=0.0, y_spacing=0.0,
        keep_mode="all", output_path=out,
    )
    assert len(result) == 4
    assert out.exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_subplot_geodataframe_io.py -v`  
Expected: FAIL with missing `load_boundary_gdf` / `generate_and_save_gdf`.

**Step 3: Write minimal implementation**

- In `io.py`, implement GeoPandas-first APIs:
  - `load_boundary_gdf(shp_path) -> gpd.GeoDataFrame`
  - `generate_subplots_gdf(...) -> gpd.GeoDataFrame` (MAR + grid logic)
  - `generate_and_save_gdf(...) -> gpd.GeoDataFrame` (`to_file`)
  - `calculate_optimal_rotation(boundary_gdf) -> float | None`
- Keep function responsibility single-purpose and short; extract helpers for:
  - MAR axis resolution
  - cell size calculation
  - polygon generation loop
- Remove `easyidp` import entirely.
- Update `__init__.py` exports to new function names.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_subplot_geodataframe_io.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/utils/subplot_generate/io.py src/utils/subplot_generate/__init__.py tests/test_subplot_geodataframe_io.py
git commit -m "feat(subplot): restore geopandas geodataframe generation utilities"
```

---

### Task 3: Revert Map Canvas Vector Path to GeoDataFrame

**Files:**
- Modify: `src/gui/components/map_canvas.py:43-60`
- Modify: `src/gui/components/map_canvas.py:445-590`
- Create: `tests/test_map_canvas_vector_geopandas.py`
- Check reference: `66a32c6^:src/gui/components/map_canvas.py`

**Step 1: Write the failing test**

```python
import geopandas as gpd
from shapely.geometry import Polygon

from src.gui.components.map_canvas import MapCanvas

def test_add_vector_layer_accepts_geodataframe(qtbot) -> None:
    canvas = MapCanvas()
    qtbot.addWidget(canvas)
    gdf = gpd.GeoDataFrame(
        {"id": [1]},
        geometry=[Polygon([(0,0), (1,0), (1,1), (0,1), (0,0)])],
        crs="EPSG:3857",
    )
    assert canvas.add_vector_layer(gdf, "Boundary")
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_map_canvas_vector_geopandas.py -v`  
Expected: FAIL because current path expects ROI/easyidp.

**Step 3: Write minimal implementation**

- Replace EasyIDP import guard with GeoPandas import guard.
- Implement vector normalization:
  - `str/Path -> gpd.read_file(path)`
  - `GeoDataFrame -> use directly`
- Convert geometry to plotting arrays for `Polygon` and `MultiPolygon`.
- Compute bounds from `gdf.total_bounds`.
- Remove EasyIDP-specific logging and class checks.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_map_canvas_vector_geopandas.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/gui/components/map_canvas.py tests/test_map_canvas_vector_geopandas.py
git commit -m "refactor(map): switch vector layer ingestion back to geopandas"
```

---

### Task 4: Update GUI Tabs from ROI model to GeoDataFrame model

**Files:**
- Modify: `src/gui/tabs/subplot_generate.py`
- Modify: `src/gui/tabs/seedling_detect.py`
- Modify: `src/utils/subplot_generate/__init__.py` (if imports still old names)

**Step 1: Write the failing test**

```python
def test_seedling_tab_load_boundary_uses_geodataframe(...):
    # existing fixture style in repo
    # assert loaded boundary object is GeoDataFrame-compatible and
    # boundary render call still succeeds
    ...
```

(Use existing tab layout test style; add focused test only for boundary loading path.)

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seedling_tab_layout.py -v`  
Expected: FAIL after utility API rename/type shift.

**Step 3: Write minimal implementation**

- `subplot_generate.py`
  - replace `boundary_roi` / `last_preview_roi` with `boundary_gdf` / `last_preview_gdf`.
  - switch imports/calls:
    - `load_boundary_gdf`
    - `generate_subplots_gdf`
    - `generate_and_save_gdf`
    - `calculate_optimal_rotation(boundary_gdf)`
- `seedling_detect.py`
  - replace `_boundary_roi` with `_boundary_gdf`.
  - `_get_boundary_xy()` use `self._boundary_gdf.geometry.iloc[0].exterior.coords`.
  - use `load_boundary_gdf(file_path)` and pass gdf to canvas.
- Keep UI behavior unchanged.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seedling_tab_layout.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add src/gui/tabs/subplot_generate.py src/gui/tabs/seedling_detect.py src/utils/subplot_generate/__init__.py tests/test_seedling_tab_layout.py
git commit -m "refactor(gui): migrate boundary flow from ROI to geodataframe"
```

---

### Task 5: Remove EasyIDP tests and restore GeoPandas subplot tests

**Files:**
- Delete: `tests/test_subplot_easyidp.py`
- Create/Modify: `tests/test_subplot_generator.py` (restore GeoPandas assertions)
- Optional Modify: `tests/test_subplot_geodataframe_io.py` (merge if duplicated)
- Check reference: `f754e71` deletion target + `66a32c6^:tests/test_subplot_generator.py`

**Step 1: Write the failing test**

Restore focused tests:
- load boundary from `.shp` returns one-row gdf
- 2x2 generation returns 4 polygons
- spacing math (e.g., 100m field, 2x2, 10m spacing => 45m cell width/height)
- output shapefile can be re-read by GeoPandas

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_subplot_generator.py -v`  
Expected: FAIL until geopandas code path is complete.

**Step 3: Write minimal implementation**

- finalize helper behavior for row/col and spacing dimensions.
- ensure CRS preserved during output.
- ensure save path normalization to `.shp`.

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_subplot_generator.py -v`  
Expected: PASS.

**Step 5: Commit**

```bash
git add tests/test_subplot_generator.py tests/test_subplot_geodataframe_io.py
git rm tests/test_subplot_easyidp.py
git commit -m "test(subplot): replace easyidp tests with geopandas coverage"
```

---

### Task 6: Full Verification, Regression Gate, and Handoff

**Files:**
- Modify (if needed): any failing file from previous tasks
- Optional docs note: `.agent/summary/20260213_geopandas_restore.md` (if team expects summary)

**Step 1: Run focused suite first**

Run:
- `uv run pytest tests/test_dependency_contract.py -v`
- `uv run pytest tests/test_subplot_generator.py -v`
- `uv run pytest tests/test_seedling_tab_layout.py -v`
- `uv run pytest tests/test_map_canvas_vector_geopandas.py -v`

Expected: all PASS.

**Step 2: Run full suite**

Run: `uv run pytest`  
Expected: full PASS, no easyidp import errors.

**Step 3: Static sanity check**

Run:
- `uv run ruff check src tests`
- `uv run black --check src tests`

Expected: no lint/format errors.

**Step 4: Final commit**

```bash
git add -A
git commit -m "refactor(gis): restore geopandas shapefile workflow and remove easyidp dependency"
```

**Step 5: Implementation handoff note**

- Include changed APIs and migration note:
  - `load_boundary_roi` -> `load_boundary_gdf`
  - `generate_subplots_roi` -> `generate_subplots_gdf`
  - `generate_and_save` -> `generate_and_save_gdf` (or keep alias if retained)

---

## Risk Controls

- If geometry behavior diverges from pre-`66a32c6` expectations, use `@superpowers/systematic-debugging` before changing math.
- If task execution will be parallelized, use `@superpowers/subagent-driven-development`.
- Keep commits small and reversible (one task = one commit).
- Do not re-introduce `src/core/` unless there is clear net benefit (YAGNI).

## Command Quicklist

```bash
uv run pytest tests/test_dependency_contract.py -v
uv run pytest tests/test_subplot_geodataframe_io.py -v
uv run pytest tests/test_map_canvas_vector_geopandas.py -v
uv run pytest tests/test_seedling_tab_layout.py -v
uv run pytest tests/test_subplot_generator.py -v
uv run pytest
uv run ruff check src tests
uv run black --check src tests
```
