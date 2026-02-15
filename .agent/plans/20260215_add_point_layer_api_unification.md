# MapCanvas add_point_layer API Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 `MapCanvas` 中新增统一的点图层 API `add_point_layer`，并将项目中所有点图层渲染改为调用该 API，同时兼容已有视觉样式与图层行为。

**Architecture:** 在 `MapCanvas` 里实现点数据归一化、样式解析与图层注册，业务层（tabs/controller）只提供点数据和样式参数，不再直接写 `_layers/_layer_order`。样式支持 `color`（同设填充与边框）以及 `fill_color`/`border_color` 精细覆盖；若显式指定 `fill_color` 或 `border_color`，则使用显式值覆盖 `color` 对应通道。

**Tech Stack:** Python, PySide6, PyQtGraph, NumPy, GeoPandas, pytest, uv

---

### Task 1: Add point-layer API in MapCanvas

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/map_canvas/test_point_layer_api.py`

**Step 1: Write the failing tests for new API surface**

```python
def test_add_point_layer_with_color_sets_fill_and_border(qtbot):
    canvas = MapCanvas()
    ok = canvas.add_point_layer(
        np.asarray([[1.0, 2.0], [3.0, 4.0]], dtype=float),
        "pts",
        color="#FFAA00",
    )
    assert ok is True
    assert "pts" in canvas._layers


def test_add_point_layer_explicit_fill_or_border_overrides_color(qtbot):
    canvas = MapCanvas()
    ok = canvas.add_point_layer(
        np.asarray([[1.0, 2.0]], dtype=float),
        "pts",
        color="#FFAA00",
        fill_color="#00FF00",
        border_color="#0000FF",
    )
    assert ok is True


def test_add_point_layer_replaces_existing_layer_without_duplicate_order(qtbot):
    canvas = MapCanvas()
    canvas.add_point_layer(np.asarray([[0.0, 0.0]], dtype=float), "pts")
    canvas.add_point_layer(np.asarray([[1.0, 1.0]], dtype=float), "pts")
    assert canvas._layer_order.count("pts") == 1
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/map_canvas/test_point_layer_api.py -v`

Expected: FAIL with missing `add_point_layer` or behavior mismatch.

**Step 3: Implement minimal add_point_layer contract**

Implementation notes:
- 新增 `add_point_layer(...) -> bool`，推荐签名：

```python
def add_point_layer(
    self,
    data: Any,
    layer_name: str,
    *,
    symbol: str = "o",
    size: float = 8.0,
    color: Any | None = None,
    fill_color: Any | None = None,
    border_color: Any | None = None,
    border_width: float = 1.2,
    z_value: float = 620.0,
    replace: bool = True,
    zoom_on_add: bool = False,
) -> bool:
    ...
```

- 新增小函数（单一职责，单函数 < 50 行）：
  - `_normalize_point_array(data: Any) -> np.ndarray`
  - `_resolve_point_style(color, fill_color, border_color, border_width) -> tuple[Any, Any]`
  - `_calc_bounds_from_points(points_xy: np.ndarray) -> LayerBounds | None`
- 样式优先级规则：
  - 若 `fill_color` 未给：使用 `color` 作为 fill
  - 若 `border_color` 未给：使用 `color` 作为 border
  - 若 `fill_color` 或 `border_color` 任一给定：对应通道使用显式值（即“单独绘制”）
  - 若三者都未给：使用现有默认橙色方案（保持历史视觉）
- 统一完成图层注册：remove(when replace) → add item → `_layers`/`_layer_order` → `sigLayerAdded`。

**Step 4: Run tests to verify pass**

Run: `uv run pytest tests/map_canvas/test_point_layer_api.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/gui/components/map_canvas.py tests/map_canvas/test_point_layer_api.py
git commit -m "feat: add map canvas point-layer api with color override support"
```

### Task 2: Migrate Rename tab point rendering to add_point_layer

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_ridge_state_sync_with_layer_deletion.py`

**Step 1: Write/adjust failing test for rename_points path**

```python
def test_render_points_overlay_registers_rename_points_layer(qtbot):
    tab = RenameTab()
    # prepare points_gdf with at least 1 point
    tab._render_points_overlay(points_gdf)
    assert "rename_points" in tab.map_component.map_canvas._layers
```

**Step 2: Run targeted test and observe failure (if any)**

Run: `uv run pytest tests/rename_ids/test_ridge_state_sync_with_layer_deletion.py -v`

**Step 3: Replace manual ScatterPlotItem registration**

Implementation notes:
- 在 `_render_points_overlay()` 里改为调用 `map_canvas.add_point_layer(...)`。
- 使用新视觉：红色边框+半透明红色填充、`size=8`、`z_value=630`。
- 保持 `zoom_to_layer("rename_points")` 行为不变。

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/rename_ids/test_ridge_state_sync_with_layer_deletion.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/gui/tabs/rename_ids.py tests/rename_ids/test_ridge_state_sync_with_layer_deletion.py
git commit -m "refactor: use add_point_layer for rename points overlay"
```

### Task 3: Migrate Seedling tab fallback result_points rendering

**Files:**
- Modify: `src/gui/tabs/seedling_detect.py`
- Test: `tests/seedling_detection/test_tab_handoff.py`

**Step 1: Add/adjust failing test for fallback layer registration**

```python
def test_copy_points_overlay_to_rename_tab_uses_layer_registry():
    # prepare seedling tab with merged points
    # prepare rename tab stub with real map_canvas
    seedling_tab._copy_points_overlay_to_rename_tab(rename_tab)
    assert "result_points" in rename_tab.map_component.map_canvas._layers
```

**Step 2: Run targeted test and verify failure (if any)**

Run: `uv run pytest tests/seedling_detection/test_tab_handoff.py -v`

**Step 3: Replace manual scatter + private registry writes**

Implementation notes:
- 在 `_copy_points_overlay_to_rename_tab()` 改为 `map_canvas.add_point_layer(...)`。
- 使用新视觉：红色边框+半透明红色填充、`size=8`、`z_value=630`、layer name `result_points`。（和前面的rename_ids的rename_points保持一致）

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/seedling_detection/test_tab_handoff.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/gui/tabs/seedling_detect.py tests/seedling_detection/test_tab_handoff.py
git commit -m "refactor: route seedling fallback points through add_point_layer"
```

### Task 4: Migrate PreviewController result point layer

**Files:**
- Modify: `src/utils/seedling_detect/preview_controller.py`
- Test: `tests/seedling_detection/test_preview.py`

**Step 1: Add failing test for result point rendering registration**

```python
def test_show_result_points_layer_registers_result_points(qtbot):
    # setup controller with map canvas
    controller._show_result_points_layer(np.asarray([[1.0, 2.0]], dtype=float))
    assert RESULT_POINTS_LAYER_NAME in controller._canvas._layers
```

**Step 2: Run targeted test and verify failure**

Run: `uv run pytest tests/seedling_detection/test_preview.py -v`

**Step 3: Replace direct scatter construction with add_point_layer**

Implementation notes:
- `_show_result_points_layer()` 改为调用 `self._canvas.add_point_layer(...)`。
- 保持视觉参数与 layer 名 `RESULT_POINTS_LAYER_NAME`。
- 保持清理逻辑与 `clear_inference_result_layers()` 一致。

**Step 4: Run test to verify pass**

Run: `uv run pytest tests/seedling_detection/test_preview.py -v`

Expected: PASS.

**Step 5: Commit**

```bash
git add src/utils/seedling_detect/preview_controller.py tests/seedling_detection/test_preview.py
git commit -m "refactor: use add_point_layer in preview result points"
```

### Task 5: Full regression and API compatibility checks

**Files:**
- Test: `tests/map_canvas/`
- Test: `tests/rename_ids/`
- Test: `tests/seedling_detection/`

**Step 1: Run focused suites for touched modules**

Run: `uv run pytest tests/map_canvas tests/rename_ids tests/seedling_detection -v`

Expected: PASS.

**Step 2: Run full test suite**

Run: `uv run pytest`

Expected: PASS or only known unrelated failures.

**Step 3: Manual behavior checklist**

- 打开 seedling tab 推理结果并发送到 rename，确认 `rename_points/result_points` 可在图层面板显示、开关可见性、删除后状态同步。
- 验证 `zoom_to_layer()` 对点图层生效。
- 验证颜色覆盖规则：
  - 仅 `color`：fill+border 同色
  - `color + fill_color`：fill 使用 fill_color，border 使用 color
  - `color + border_color`：border 使用 border_color，fill 使用 color
  - 三者都给：fill/border 使用显式颜色

**Step 4: Final commit**

```bash
git add src/gui/components/map_canvas.py src/gui/tabs/rename_ids.py src/gui/tabs/seedling_detect.py src/utils/seedling_detect/preview_controller.py tests/map_canvas/test_point_layer_api.py tests/rename_ids tests/seedling_detection
git commit -m "refactor: unify point rendering with add_point_layer across app"
```
