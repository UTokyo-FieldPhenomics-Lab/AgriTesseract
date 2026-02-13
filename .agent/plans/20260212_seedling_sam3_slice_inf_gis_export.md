# Seedling SAM3 Slice Inference + GIS Export Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 Seedling_detect 检测页完成可用的 SAM3 文本提示词推理工作流，全图切块推理、以及 GIS 文件导出（`bbox.shp`、`points.shp`）。

**Architecture:** 界面编排集中在 `src/gui/tabs/seedling_detect.py`，核心算法统一放到 `src/utils/seedling_detect/`。地图交互能力扩展在 `src/utils/seedling_detect/preview_controller.py`，全图推理在 `QThread` 后台执行，主线程仅负责 UI 状态、进度条和图层更新。切块结果在 worker 内逐片聚合，结束后统一 NMS 合并并输出矢量层/文件。

**Tech Stack:** PySide6, PySide6-Fluent-Widgets, pyqtgraph, ultralytics (SAM3), numpy, pandas, pyshp, matplotlib(PdfPages), pytest。

---

**Skill refs:** `@superpowers:test-driven-development` `@superpowers:systematic-debugging` `@superpowers:verification-before-completion`

### Task 1: Boundary 选择与切块过滤能力（inside / intersect）

**Files:**
- Modify: `src/gui/tabs/seedling_detect.py:272`
- Modify: `src/utils/seedling_detect/slice.py:46`
- Modify: `src/utils/seedling_detect/preview_controller.py:217`
- Modify: `src/gui/resource/i18n/zh_CN.json:66`
- Modify: `src/gui/resource/i18n/en_US.json:68`
- Modify: `src/gui/resource/i18n/ja_JP.json:68`
- Test: `tests/test_seedling_slice.py`

**Step 0: Add boundary selection button to topbar UI**

代码可以参考或复用@subplot_generate.py#L174-175 @subplot_generate.py#L424-460 

**Step 1: Write the failing test**

```python
def test_filter_slice_windows_keeps_intersect_and_inside() -> None:
    windows = generate_slice_windows(100, 100, 40, 0.0)
    boundary = np.array([[20.0, 20.0], [80.0, 20.0], [80.0, 80.0], [20.0, 80.0]])
    filtered_intersect = filter_windows_by_boundary(
        windows=windows,
        transform=Affine.identity(),
        boundary_xy=boundary,
        mode="intersect",
    )
    filtered_inside = filter_windows_by_boundary(
        windows=windows,
        transform=Affine.identity(),
        boundary_xy=boundary,
        mode="inside",
    )
    assert len(filtered_intersect) >= len(filtered_inside)
    assert len(filtered_inside) > 0
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seedling_slice.py::test_filter_slice_windows_keeps_intersect_and_inside -v`  
Expected: FAIL with `NameError: name 'filter_windows_by_boundary' is not defined`

**Step 3: Write minimal implementation**

```python
def filter_windows_by_boundary(
    windows: list[SliceWindow],
    transform: Affine,
    boundary_xy: np.ndarray | None,
    mode: str,
) -> list[SliceWindow]:
    if boundary_xy is None or len(boundary_xy) < 3:
        return windows
    boundary_poly = Polygon(boundary_xy)
    kept: list[SliceWindow] = []
    for window in windows:
        window_poly = window_to_geo_polygon(window, transform)
        if mode == "inside" and window_poly.within(boundary_poly):
            kept.append(window)
            continue
        if mode == "intersect" and window_poly.intersects(boundary_poly):
            kept.append(window)
    return kept
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seedling_slice.py::test_filter_slice_windows_keeps_intersect_and_inside -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add tests/test_seedling_slice.py src/utils/seedling_detect/slice.py src/gui/tabs/seedling_detect.py src/utils/seedling_detect/preview_controller.py src/gui/resource/i18n/*.json
git commit -m "feat: add boundary-aware slice filtering modes for seedling inference"
```

---

### Task 2: Full-map worker（`qthread.py`）与进度信号

**Files:**
- Modify: `src/utils/seedling_detect/qthread.py`
- Modify: `src/utils/seedling_detect/sam3.py:36`
- Modify: `src/utils/seedling_detect/slice.py:90`
- Modify: `src/utils/seedling_detect/__init__.py:27`
- Test: `tests/test_seedling_preview_worker.py`
- Test: `tests/test_seedling_sam3.py`

**Step 1: Write the failing test**

```python
def test_seedling_inference_worker_emits_progress_and_finished(qtbot) -> None:
    payload = SeedlingInferenceInput(
        dom_path="tests/data/demo.tif",
        weight_path="fake.pt",
        prompt="plants",
        conf=0.25,
        iou=0.45,
        slice_size=640,
        overlap_ratio=0.2,
    )
    worker = SeedlingInferenceWorker(payload, predictor_factory=FakePredictorFactory())
    progress_values = []
    worker.sigProgress.connect(progress_values.append)
    worker.run()
    assert progress_values[0] == 0
    assert progress_values[-1] == 100
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seedling_preview_worker.py::test_seedling_inference_worker_emits_progress_and_finished -v`  
Expected: FAIL with `ImportError` or `NameError` for `SeedlingInferenceWorker`

**Step 3: Write minimal implementation**

```python
class SeedlingInferenceWorker(QObject):
    sigProgress = Signal(int)
    sigFinished = Signal(dict)
    sigFailed = Signal(str)
    sigCancelled = Signal()

    @Slot()
    def run(self) -> None:
        self.sigProgress.emit(0)
        # iterate windows -> run SAM3 -> collect boxes/polygons/scores
        # emit int(progress) each loop
        self.sigProgress.emit(100)
        self.sigFinished.emit(result_payload)
```

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seedling_preview_worker.py::test_seedling_inference_worker_emits_progress_and_finished -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/seedling_detect/seedling_worker.py src/utils/seedling_detect/sam3.py src/utils/seedling_detect/slice.py src/utils/seedling_detect/__init__.py tests/test_seedling_preview_worker.py tests/test_seedling_sam3.py
git commit -m "feat: add background full-map SAM3 worker with progress signals"
```

---

### Task 3: SeedlingTab 接通全图推理启动/停止与状态栏进度

**Files:**
- Modify: `src/gui/tabs/seedling_detect.py:534`
- Modify: `src/gui/components/status_bar.py:208` (only if clamping/helper needed)
- Test: `tests/test_seedling_tab_layout.py`
- Test: `tests/test_seedling_preview_worker.py` (UI signal wiring case)

**Step 1: Write the failing test**

```python
def test_start_inference_updates_status_progress(seedling_tab, qtbot) -> None:
    seedling_tab._on_full_inference_progress(35)
    assert seedling_tab.map_component.status_bar.progress_bar.value() == 35
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seedling_tab_layout.py::test_start_inference_updates_status_progress -v`  
Expected: FAIL with missing slot `_on_full_inference_progress`

**Step 3: Write minimal implementation**

```python
@Slot(int)
def _on_full_inference_progress(self, percent: int) -> None:
    self.map_component.status_bar.set_progress(max(0, min(100, int(percent))))
```

同时接通：
- `btn_start_inference` -> `_on_full_inference_clicked`
- 创建线程与 worker，连接 `sigProgress/sigFinished/sigFailed/sigCancelled`
- 运行时按钮文本切换为停止；结束后恢复

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seedling_tab_layout.py::test_start_inference_updates_status_progress -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/gui/tabs/seedling_detect.py tests/test_seedling_tab_layout.py
git commit -m "feat: wire full inference thread lifecycle and live status progress"
```

---

### Task 4: 推理结果 NMS 合并 + 地图图层渲染（`result_bbox` / `result_points`）

**Files:**
- Modify: `src/utils/seedling_detect/slice.py:90`
- Modify: `src/utils/seedling_detect/preview_controller.py:35`
- Modify: `src/gui/tabs/seedling_detect.py:484`
- Test: `tests/test_seedling_slice.py`
- Test: `tests/test_seedling_preview.py`

**Step 1: Write the failing test**

```python
def test_nms_boxes_merges_overlaps_and_keeps_high_score() -> None:
    boxes = np.array([[0, 0, 10, 10], [1, 1, 11, 11], [30, 30, 40, 40]], dtype=float)
    scores = np.array([0.7, 0.9, 0.8], dtype=float)
    keep = nms_boxes_xyxy(boxes, scores, iou_threshold=0.5)
    assert keep == [1, 2]
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seedling_slice.py::test_nms_boxes_merges_overlaps_and_keeps_high_score -v`  
Expected: FAIL with `NameError: nms_boxes_xyxy`

**Step 3: Write minimal implementation**

```python
def nms_boxes_xyxy(boxes_xyxy: np.ndarray, scores: np.ndarray, iou_threshold: float) -> list[int]:
    if boxes_xyxy.size == 0:
        return []
    order = np.argsort(-scores)
    keep: list[int] = []
    while order.size:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            return keep
        iou = pairwise_iou_xyxy(boxes_xyxy[i], boxes_xyxy[order[1:]])
        order = order[1:][iou <= iou_threshold]
    return keep
```

并在 UI 完成：
- `sigFinished` 后构建 `bbox_df` 与 `points_df`
- 使用 `preview_controller` 新增方法绘制 `infer_bbox`（polygon）与 `infer_points`（scatter）
- 图层名固定：`infer_bbox`、`infer_points`

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seedling_slice.py::test_nms_boxes_merges_overlaps_and_keeps_high_score -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/seedling_detect/slice.py src/utils/seedling_detect/preview_controller.py src/gui/tabs/seedling_detect.py tests/test_seedling_slice.py tests/test_seedling_preview.py
git commit -m "feat: merge slice detections via NMS and render infer bbox/points layers"
```

---

### Task 5: 最终产物导出（`bbox.shp` + `points.shp` with fid）

**Files:**
- Modify: `src/gui/tabs/seedling_detect.py:272`
- Modify: `src/utils/seedling_detect/io.py:38`
- Test: `tests/test_seedling_io.py`

**Step 1: Write the failing test**

```python
def test_export_inference_outputs_writes_three_shapefiles(tmp_path: Path) -> None:
    export_inference_outputs(
        out_dir=tmp_path,
        bbox_df=make_bbox_df(),
        mask_df=make_mask_df(),
        points_df=make_points_df(),
        crs_wkt=None,
    )
    assert (tmp_path / "bbox.shp").exists()
    assert (tmp_path / "points.shp").exists()
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seedling_io.py::test_export_inference_outputs_writes_three_shapefiles -v`  
Expected: FAIL with `NameError: export_inference_outputs`

**Step 3: Write minimal implementation**

```python
def export_inference_outputs(
    out_dir: str | Path,
    bbox_df: pd.DataFrame,
    mask_df: pd.DataFrame,
    points_df: pd.DataFrame,
    crs_wkt: str | None,
) -> None:
    target_dir = Path(out_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    save_bbox_shp(bbox_df, target_dir / "bbox.shp", crs_wkt)
    save_mask_polygon_shp(mask_df, target_dir / "mask.shp", crs_wkt)
    save_point_shp(points_df, target_dir / "points.shp", crs_wkt)
```

同时 UI：
- `btn_save_shp` 触发目录选择
- 若无推理结果，InfoBar warning 并 return guard clause
- 导出成功后提示文件数与目录

**Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_seedling_io.py::test_export_inference_outputs_writes_three_shapefiles -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/utils/seedling_detect/io.py src/gui/tabs/seedling_detect.py tests/test_seedling_io.py
git commit -m "feat: export bbox mask and center points shapefiles from inference results"
```

---

### Task 6: 回归测试与验收清单

**Files:**
- Modify: `tests/test_seedling_slice.py`
- Modify: `tests/test_seedling_preview_worker.py`
- Modify: `tests/test_seedling_io.py`
- Modify: `tests/test_seedling_tab_layout.py`
- Optional docs: `README.md` (seedling workflow section)

**Step 1: Write the failing integration-style test**

```python
def test_full_inference_result_schema_is_export_ready() -> None:
    result = build_fake_full_inference_result()
    assert {"bbox_df", "mask_df", "points_df"} <= set(result.keys())
```

**Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_seedling_preview_worker.py::test_full_inference_result_schema_is_export_ready -v`  
Expected: FAIL due missing keys/schema mismatch

**Step 3: Write minimal implementation**

```python
result_payload = {
    "bbox_df": bbox_df,
    "mask_df": mask_df,
    "points_df": points_df,
    "meta": meta_dict,
}
```

**Step 4: Run tests to verify all pass**

Run: `uv run pytest tests/test_seedling_slice.py tests/test_seedling_preview_worker.py tests/test_seedling_io.py tests/test_seedling_tab_layout.py -v`  
Expected: PASS for all selected modules

Run: `uv run pytest -v`  
Expected: PASS (full suite)

**Step 5: Commit**

```bash
git add tests src/gui/tabs/seedling_detect.py src/utils/seedling_detect/*.py README.md
git commit -m "test: cover boundary filtering worker progress nms merge and shp export workflow"
```

---

## Done Criteria

- Boundary 按钮与可选过滤模式可用：无 boundary 时全图切块，有 boundary 时按 `intersect/inside` 过滤。
- 全图推理通过 `QThread` 后台执行，状态栏进度实时 0-100 更新。
- 推理结束后进行全局 NMS 合并，地图上生成 `infer_bbox` 与 `infer_points` 图层。
- 可导出 `bbox.shp`、`points.shp`（`points` 包含 `fid` 字段）。
- `uv run pytest` 通过。
