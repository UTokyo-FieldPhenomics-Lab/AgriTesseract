# Rename IDs 模块 05：按垄归属聚类与 RANSAC（Ordering Tab）实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 Ordering Tab 中将有效点稳定归属到 ridge，输出可追踪的归属结果与可视化着色，为模块06提供可靠的分垄输入。

**Architecture:** 采用“纯算法引擎 + UI 控制器”分层。`ridge_ordering.py` 负责 buffer 归属与可选 RANSAC 过滤；`ridge_ordering_controller.py` 负责参数防抖触发、图层更新和统计回传。Tab 本身只做输入控件与状态绑定。忽略点统一标记为 `ridge_id=-1, is_inlier=False`，不在模块05补号和排序。

**Tech Stack:** PySide6, qfluentwidgets, numpy, pandas, geopandas, scikit-learn(RANSACRegressor), pyqtgraph, pytest。

---

## 设计决策（已锁定）
1. 采用方案 A：算法与 UI 分层实现。
2. 模块05不输出 `order_in_ridge`，垄内排序完全下放到模块06。
3. ignored 点统一保留为 `ridge_id=-1, is_inlier=False`，编号阶段再处理。

## 输入契约（来自模块03/04）
- `points_gdf`：输入点，至少包含 `fid` 与 `geometry`。
- `effective_mask`：有效点布尔掩码。
- `ridge_direction_state`：包含方向向量与方向来源。
- `ridge_peaks`：峰值位置（与模块04一致）。
- `ordering_params`：
  - `buffer: float`
  - `ransac_enabled: bool`
  - `residual: int`
  - `max_trials: int`

## 输出契约（提供给模块06）
- `ordering_result_gdf`（行与 `points_gdf` 一一对应）：
  - `fid: int`
  - `ridge_id: int`（ignored 为 `-1`）
  - `is_inlier: bool`
  - `geometry: Point`
- `ordering_stats`：
  - `total_points`
  - `effective_points`
  - `assigned_points`
  - `ignored_points`
  - `ridge_count`

## 任务分解（可直接执行）

### Task 1：纯算法模块骨架与失败测试

**Files:**
- Create: `src/utils/rename_ids/ridge_ordering.py`
- Modify: `src/utils/rename_ids/__init__.py`
- Test: `tests/rename_ids/test_ridge_ordering_core.py`

**Steps:**
1. 先写失败测试：空输入、单 ridge、多 ridge、ignored 标记规则。
2. 创建算法模块骨架函数：
   - `build_ridge_intervals(...)`
   - `assign_points_to_ridges(...)`
   - `build_ordering_result(...)`
3. 运行单测确认失败原因准确（函数未实现或断言失败）。

**Verify:**
- `uv run pytest tests/rename_ids/test_ridge_ordering_core.py -v`

### Task 2：buffer 归属与 ignored 标记

**Files:**
- Modify: `src/utils/rename_ids/ridge_ordering.py`
- Test: `tests/rename_ids/test_ridge_ordering_core.py`

**Steps:**
1. 实现 ridge intervals：根据 `ridge_peaks` 相邻间距推导每 ridge 带宽边界。
2. 实现点归属：先按 `effective_mask` 过滤(或effective points)，再按投影坐标匹配区间。
3. 未命中区间点直接标记为 ignored（`ridge_id=-1, is_inlier=False`）。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_ridge_ordering_core.py -v`

### Task 3：可选 RANSAC 过滤

当进行距离进行聚类表现不佳时（大部分情况），可以考虑使用 RANSAC 算法进行过滤。

**Files:**
- Modify: `src/utils/rename_ids/ridge_ordering.py`
- Test: `tests/rename_ids/test_ridge_ordering_ransac.py`

**Steps:**
1. 先写失败测试：RANSAC 开关、residual、max_trials 对结果影响。
2. 在每个 ridge 内执行可选 RANSAC：
   - `X = cvt_y`，`y = cvt_x`（沿 reference 的垂线残差思路）。
3. 非内点标记 `is_inlier=False`，但保留 `ridge_id` 归属信息。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_ridge_ordering_ransac.py -v`

### Task 4：Ordering 控制器与地图着色联动

**Files:**
- Create: `src/utils/rename_ids/ridge_ordering_controller.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_ridge_ordering_controller.py`

**Steps:**
1. 先写失败测试：参数更新触发 controller，输出结果层与统计值。
2. 控制器接入 `sigOrderingParamsChanged` 防抖结果。
3. 生成按 ridge_id 稳定色映射图层（输入点层可隐藏）。
4. ignored 点绘制为统一样式（如灰色+描边）。
5. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_ridge_ordering_controller.py -v`

### Task 5：UI 状态、参数禁用与文案

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`
- Modify: `src/gui/resource/i18n/zh_CN.json`
- Modify: `src/gui/resource/i18n/en_US.json`
- Modify: `src/gui/resource/i18n/ja_JP.json`
- Test: `tests/rename_ids/test_ordering_ui_state.py`

**Steps:**
1. 先写失败测试：无 ridge 结果时 Ordering 参数 disabled。
2. 保留并完善 `check_ransac` 对 residual/max_trials 的启禁联动。
3. 增加统计提示：assigned/ignored/total。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_ordering_ui_state.py -v`

### Task 6：端到端回归

**Files:**
- Test: `tests/rename_ids/test_ordering_end_to_end.py`

**Steps:**
1. 构造小样本：含边界外点、buffer 临界点、明显离群点。
2. 跑“方向已定 -> ridge peaks 已定 -> ordering”完整流。
3. 断言输出契约字段齐全、统计一致、ignored 规则正确。
4. 全量回归。

**Verify:**
- `uv run pytest tests/rename_ids -v`
- `uv run pytest`

## 风险与对策
- **RANSAC 参数敏感**：保留默认值与“一键恢复默认”。
- **多 ridge 色彩混淆**：使用稳定哈希色盘，跨刷新不变。
- **大点量性能压力**：缓存投影坐标，参数更新只重跑必要步骤。
- **方向状态变化导致分配抖动**：在 controller 中监听方向变更并强制重算归属。

## 验收标准
1. Ordering 参数变更可实时更新归属与颜色结果。
2. ignored 点稳定标记为 `ridge_id=-1, is_inlier=False`。
3. 输出字段仅包含分垄归属（`ridge_id`、`is_inlier`），不包含排序字段。
4. RANSAC 开关与参数启禁状态正确。
5. Ordering 输出可直接被模块06消费，无需额外清洗。

---

## 补充任务（UI 触发时机与单图层着色）

### Task 7：仅在 Ordering Tab 可见时执行 ordering 计算

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_ordering_ui_state.py`

**Steps:**
1. 在 `RenameTab` 增加“当前是否处于 Ordering 顶部 tab”的判断逻辑。
2. Ridge 参数更新流程只刷新 ridge payload 与 ordering UI 可用态，不触发 ordering 计算。
3. 仅当当前 tab 为 Ordering 时，Ordering 参数更新才触发计算。
4. 从其他 tab 切到 Ordering tab 时执行一次 ordering 首算（若前置条件满足）。
5. 补充测试：在 Ridge tab 调参不应产生 ordering 结果图层；切换到 Ordering tab 后再产生。

**Verify:**
- `uv run pytest tests/rename_ids/test_ordering_ui_state.py -v`

### Task 8：MapCanvas 点图层支持按点颜色列表渲染

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/map_canvas/test_point_layer_api.py`

**Steps:**
1. 为 `add_point_layer`： `color`, `fill_color` 与 `border_color`允许 单个颜色输入 和 长度应与点数一致的颜色列表。
2. 保持原有单色参数 `color/fill_color/border_color` 完全兼容。
3. 当提供颜色列表时，采用按点样式渲染单一 `ScatterPlotItem`（单图层）。
4. 补充测试：按点颜色列表生效、长度不匹配报错、旧接口行为不变。

**Verify:**
- `uv run pytest tests/map_canvas/test_point_layer_api.py -v`

### Task 9：Ordering 结果改为单图层 `ordering_points`

**Files:**
- Modify: `src/utils/rename_ids/ridge_ordering_controller.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_ridge_ordering_controller.py`

**Steps:**
1. 将 `RidgeOrderingController` 的多图层输出（`ordering_ridge_{n}`）改为单图层输出 `ordering_points`。
2. 基于 `ridge_id` 构建稳定颜色映射，ignored 点去除fill color, border color使用灰色。
3. 调用扩展后的 `add_point_layer` 传入按点颜色列表，保持单图层但多颜色显示。
4. 更新测试断言为单图层命名与单图层多颜色行为。

**Verify:**
- `uv run pytest tests/rename_ids/test_ridge_ordering_controller.py -v`

### Task 10：补充回归验证

**Files:**
- Test: `tests/rename_ids/test_ordering_end_to_end.py`

**Steps:**
1. 更新端到端测试，断言 `ordering_points` 存在且契约字段完整。
2. 断言 ignored 规则稳定：`ridge_id=-1` 且 `is_inlier=False`。
3. 运行 rename_ids 全量回归与项目全量回归。

**Verify:**
- `uv run pytest tests/rename_ids -v`
- `uv run pytest`
