# Rename IDs 模块 02：文件输入与图层管理（File Tab）实施细化

## Goal
统一 `Load Shp` / `Load Boundary` / `Load DOM` 与上一 Tab send-to-next 入口，确保进入 Ridge 前数据结构一致、图层顺序稳定。

## Architecture
File Tab 只负责输入装配与渲染触发，不直接写业务算法。通过 `RenameInputBundle`（object-first）作为模块出口，把点、边界、DOM、有效点掩码和边界轴向统一交给后续 Ridge/Ordering。`rename_ids.py` 作为UI协调层，`src/utils/rename_ids/io.py` 和 `src/utils/rename_ids/boundary.py` 承担纯逻辑和可测试函数。

## Tech Stack
PySide6, qfluentwidgets, geopandas, shapely, numpy, rasterio, pyqtgraph, pytest。

---

## Data Contract（已锁定：object-first）

### RenameInputBundle
- `points_gdf`: `gpd.GeoDataFrame`，几何类型必须是 `Point`。
- `points_meta`: `dict[str, object]`
  - `source`: `"file" | "send_next"`
  - `id_field`: `str`
  - `crs_wkt`: `str | None`
  - `source_tag`: `str`（如文件名或上游模块名）
- `boundary_gdf`: `gpd.GeoDataFrame | None`（Polygon/MultiPolygon）。
- `boundary_axes`: `dict[str, np.ndarray] | None`
  - `x_axis`: `np.ndarray[float64]` shape `(2,)`
  - `y_axis`: `np.ndarray[float64]` shape `(2,)`
- `effective_mask`: `np.ndarray[bool_]` shape `(N,)`，与 `points_gdf` 行严格对齐。
- `dom_layers`: `list[dict[str, str]]`
  - 每项 `{"name": str, "path": str}`，顺序即显示顺序（top -> bottom）。

## 模块范围
1. 点输入标准化（file/send-next 共路径）。
2. boundary 可选加载、有效点计算、最小外接矩形轴向提取。
3. DOM 多图层加载与强制置底。
4. 输入错误反馈（InfoBar）与阻断策略。

## 文件改动计划

### Task 1: 输入数据契约与会话缓存

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`

**Steps:**
1. 在 `RenameTab` 增加 `_input_bundle: dict | None` 和 `_current_points_source`。
2. 新增 `set_input_bundle(bundle: dict) -> None`，作为 object-first 主入口。
3. `sigLoadShp` 保留路径入口，但内部最终也组装为 bundle。
4. 新增 `_emit_input_ready()`（若需要）供后续模块监听。

### Task 2: 点数据读取与标准化

**Files:**
- Create: `src/utils/rename_ids/io.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/test_rename_io.py`

**Steps:**
1. 在 `rename_ids/io.py` 增加 `load_points_data(source: str | dict) -> gpd.GeoDataFrame`。
2. 实现 `normalize_input_points(gdf: gpd.GeoDataFrame) -> tuple[gpd.GeoDataFrame, dict]`：
   - 校验几何全为 Point。
   - 统一生成 `fid`（若缺失）。
   - 统一必要字段（最少：`fid`, `geometry`）。
3. 在 `rename_ids.py` 的 `_on_load_shp()` 调用上述函数并更新 `_input_bundle`。
4. 单测覆盖：
   - 缺少 fid 自动补齐。
   - 非 Point 几何触发异常。
   - CRS 缺失时 `crs_wkt` 为 `None`。

### Task 3: boundary 处理与有效点掩码

**Files:**
- Create: `src/utils/rename_ids/boundary.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/test_rename_boundary.py`

**Steps:**
1. 实现 `align_boundary_crs(points_gdf, boundary_gdf) -> tuple[gpd.GeoDataFrame, gpd.GeoDataFrame]`。
2. 实现 `build_effective_mask(points_gdf, boundary_gdf) -> np.ndarray`。
3. 实现 `compute_boundary_axes(boundary_gdf) -> dict[str, np.ndarray]`：
   - 基于最小面积外接矩形计算 x/y 轴单位向量。
4. `rename_ids.py` 的 `_on_load_boundary()` 更新 `boundary_gdf`、`boundary_axes`、`effective_mask`。
5. 单测覆盖：
   - CRS 对齐成功路径。
   - 点在边界内外掩码正确。
   - 非法 boundary（空/无效）抛出明确错误。

### Task 4: DOM 多文件加载与置底规则

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/test_map_canvas_layer_order.py`（或现有组件测试文件）

**Steps:**
1. `rename_ids.py` 的 `_on_load_dom()` 支持多文件批量加载并写入 `dom_layers`。
2. `map_canvas.py` 增加 `ensure_layers_bottom(layer_names: list[str]) -> None`。
3. 每次新增 DOM 后调用置底函数，保证 DOM 类型永远位于 layer tree 最底部，但新增的DOM应该在同类型DOM的最上层。
4. 命名冲突自动去重（`name`, `name_1`, `name_2`）。
5. 单测覆盖：
   - 混合矢量和栅格层时 DOM 位于末尾。
   - 重复加载同名 DOM 不覆盖已有层。

### Task 5: send-to-next object-first 对接

**Files:**
- Modify: `src/gui/tabs/seedling_detect.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/test_tab_handoff.py`

**Steps:**
1. 在 `seedling_detect.py` 新增组装 `RenameInputBundle` 的函数。
2. `_on_send_to_next_clicked()` 优先调用 `rename_tab.set_input_bundle(bundle)`。
3. 兼容回退：若对象传递失败，再使用 `sigLoadShp.emit(path)`。
4. 单测覆盖：
   - object-first 正常传递。
   - 回退路径仍可工作。

## 交互与错误处理规则
- 点加载失败：InfoBar.error + 不污染当前 `_input_bundle`。
- boundary 与 points CRS 无法对齐：InfoBar.warning + 提示是否要转换为Point一致的CRS，如果用户选择了否，则阻断 boundary 生效。如果选择了是，则自动转换boundary的CRS。
- DOM 某个文件失败：记录失败列表，其他成功项继续加载。
- DOM 的CRS和Points不一致：InfoBar.warning + 提示是否要转换为Point一致的CRS，如果用户选择了否，则阻断 DOM 生效。如果选择了是，则自动转换DOM的CRS。
- send-to-next bundle 不完整：给出缺失字段名并拒绝接收。

## 验收标准
1. 文件加载和 send-to-next 最终得到一致的 `RenameInputBundle`。
2. boundary 加载后 `effective_mask` 与可视化有效点一致。
3. 加载多个 DOM 后 layer panel 底部始终是 DOM 组，且DOM组内DOM按加载顺序排列。
4. Ridge Tab 可直接读取 `boundary_axes`，无需再解析 boundary。
5. `uv run pytest tests/test_rename_io.py tests/test_rename_boundary.py` 通过。

## 依赖与下一模块接口
- 向模块 03 输出：`boundary_axes`、`effective_mask`、`effective_points_gdf`(if have, those points inside the boundary)。
- 模块 03 不应再次处理文件与 CRS，仅消费 bundle。

## 非目标（本模块不做）
- 不实现 ridge 峰值检测。
- 不实现 RANSAC 聚类。
- 不实现编号规则。
