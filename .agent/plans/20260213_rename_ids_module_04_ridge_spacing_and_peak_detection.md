# Rename IDs 模块 04：垄间距估计、峰值检测与底部诊断面板实施细化

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## 目标
在已确定垄方向后，基于有效点投影计算密度曲线和峰值，实时在底部面板显示曲线，并在地图绘制候选 ridge lines，且每次调参自动执行 focus 与宽度对齐。

## 架构
采用“主地图 + 可扩展底部面板”结构。底部面板由 host 管理，可挂接未来插件（文件夹管理、素材面板等），本模块先实现 `RidgeFigurePanel`（单图：density+peaks）。算法输出由 controller 统一驱动面板和地图联动渲染，避免 UI 逻辑分散。

## 技术栈
PySide6, qfluentwidgets, pyqtgraph, numpy, scipy.signal.find_peaks, geopandas, pytest。

## 参考资料

* `.agent/references/seedling_pos/14_order_by_ridge.py` 中有相关的算法实现，可以参考。

---

## 功能约束（已锁定）
1. `strength ratio / distance / height` 在垄方向未设置时 disabled。
2. 参数变化（防抖）后自动：
   - 打开 bottom panel
   - 重算 ridge diagnostics
   - 执行 focus ridge（旋转+缩放+宽度对齐）
3. `RidgeFigurePanel` 仅绘制 density+peaks。
4. map_canvas 同步绘制 ridge 检测线（平行于 ridge direction和 经过检测的peaks）。
5. 切换到其他 top tab 或其他 nav tab 自动收起 bottom panel。

## 数据契约（模块输出）
- `ridge_density_profile`:
  - `x_bins: np.ndarray[float64]` shape `(M,)`
  - `counts: np.ndarray[int64]` shape `(M,)`
- `ridge_peaks`:
  - `peak_indices: np.ndarray[int64]`
  - `peak_x: np.ndarray[float64]`
  - `peak_heights: np.ndarray[float64]`
- `ridge_lines_gdf`: `GeoDataFrame[LineString]`
- `ridge_runtime_view`:
  - `aligned_x_range: tuple[float, float]`
  - `last_focus_rotation_deg: float`

## 任务分解（可直接执行）

### Task 1：底部面板宿主（可扩展）与布局接入
**Files**
- Modify: `src/gui/components/map_component.py`
- Create: `src/gui/components/bottom_panel.py`
- Test: `tests/bottom_panel/test_panel_host.py`

**Steps**
1. 新增 `BottomPanelHost`（可注册 panel，支持 show/hide/switch）。
2. 在 `MapComponent` 垂直 splitter 插入 `bottom_panel_host` 于 `map_canvas` 与 `status_bar` 之间。
3. 设置初始尺寸比约 `4:1`（map:bottom），status bar 保持固定。
4. 默认收起 host；暴露 `show_panel(name)` / `hide_panel()` API。
5. 支持手动调节高度（但最高和map_canvas一样高1:1）,也支持拖动高度到接近底部的时候自动隐藏（类似与property_panel和layer_panel）
6. 单测验证默认收起、显示切换、面板注册生命周期。

**Verify**
- `uv run pytest tests/bottom_panel/test_panel_host.py -v`

### Task 2：RidgeFigurePanel（单图）实现
**Files**
- Modify: `src/gui/components/bottom_panel.py` (添加一个通用的Figure panel类型)
- Create: `src/gui/tabs/rename_ids.py` (添加RidgeFigurePanel，继承自bottom_panel_figure)
- Test: `tests/bottom_panel/test_figure_panel.py`
- Test: `tests/rename_ids/test_ridge_figure_panel.py`

**Steps**
1. 用 `pyqtgraph.PlotWidget` 实现单图面板。
2. 提供 `set_density_curve(x_bins, counts)` 和 `set_peaks(peak_x, peak_h)`。
3. 实现曲线、峰值 marker、阈值线（可选）绘制刷新。
4. 提供 `clear()` 与 `set_x_range(x_min, x_max)`。
5. 单测验证数据刷新与 xRange 同步。

**Verify**
- `uv run pytest tests/bottom_panel/test_figure_panel.py -v`
- `uv run pytest tests/rename_ids/test_ridge_figure_panel.py -v`

### Task 3：ridge 密度与峰值算法纯函数
**Files**
- Create: `src/utils/rename_ids/ridge_density.py`
- Modify: `src/utils/rename_ids/__init__.py`
- Test: `tests/rename_ids/test_ridge_density.py`

**Refernce**

* `.agent/references/seedling_pos/14_order_by_ridge.py` 中有相关的算法实现，可以参考。

**Steps**
1. 实现 `project_points_to_perp_axis(points_xy, direction_vec)`。
2. 实现 `build_density_histogram(projected_x, strength_ratio)`。
3. 实现 `detect_ridge_peaks(counts, distance, height)`。
4. 实现 `build_ridge_lines_from_peaks(...)` 输出 line geometry。
5. 单测覆盖：空输入、单峰、多峰、参数边界、异常参数。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_density.py -v`

### Task 4：Ridge diagnostics controller（面板+地图联动）
**Files**
- Create: `src/utils/rename_ids/ridge_detection_controller.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_ridge_detection_controller.py`

**Steps**
1. 新建 controller，输入：effective_points(and its bbox)、direction_state(direction vectors)、ridge params (control parameters for peak detection)。
2. 输出 density/peaks/ridge_lines，并分发到 figure panel 和 map overlay。
3. 地图绘制 ridge lines（鲜艳区分色，固定层名如 `ridge_detected_lines`）。
4. 参数变化只增量重绘（先 clear 旧层再注册新层）。
5. 单测验证 payload 与层更新次数。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_detection_controller.py -v`

### Task 5：focus ridge（旋转 + Fit to X）与通用视图适配 API

**Files**
- Modify: `src/gui/components/map_canvas.py`
- Modify: `src/gui/components/layer_panel.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/gui/test_map_canvas_fit_axis.py`
- Test: `tests/gui/test_layer_panel_fit_actions.py`
- Test: `tests/rename_ids/test_ridge_focus.py`

**Steps**
1. 在 `map_canvas.py` 增加通用 API：
   - `fit_layer_to_x(layer_name: str, padding: float = 0.05) -> bool`
   - `fit_layer_to_y(layer_name: str, padding: float = 0.05) -> bool`
2. API 逻辑：
   - 读取目标图层 bounds；
   - 在当前 rotation 视图下，仅调整一个轴向的可视范围（x 或 y）；
   - 保持另一轴范围不变；
   - 图层不存在或 bounds 无效时返回 `False`。
3. 在 `layer_panel.py` 的右键菜单增加两个动作：
   - `Fit Width`（icon: `CareDownSolid`，对应 x 方向适配）
   - `Fit Height`（icon: `CareRightSolid`，对应 y 方向适配）
   - 触发后调用 map_canvas 对应 API。
4. 将 focus ridge 主流程改为两步：
   - `map_canvas.set_rotation(saved_angle)`
   - `map_canvas.fit_layer_to_x(points_layer_name, padding=...)`
5. ridge 参数每次防抖更新后，重复执行上述 focus ridge 两步
6. 确保地图宽度与底部 density 曲线语义对齐(x轴方向, 附上padding=0.05)。
7. 单测覆盖：
   - `fit_layer_to_x/y` 成功与失败分支；
   - 右键动作触发链路；
   - ridge 参数更新必触发 `rotation + fit_layer_to_x`。

**Verify**
- `uv run pytest tests/gui/test_map_canvas_fit_axis.py -v`
- `uv run pytest tests/gui/test_layer_panel_fit_actions.py -v`
- `uv run pytest tests/rename_ids/test_ridge_focus.py -v`

### Task 6：参数启用状态与自动展开/自动收起
**Files**
- Modify: `src/gui/tabs/rename_ids.py`
- Modify: `src/gui/main_window.py`（如需监听 nav 切换）
- Test: `tests/rename_ids/test_ridge_panel_visibility_rules.py`

**Steps**
1. 方向无效时 disable 三个 ridge 参数输入。
2. 方向有效 + 参数变更后自动展开 bottom panel。
3. top tab 退出 Ridge 或 nav 切换时自动收起 bottom panel。
4. 防抖触发后只执行一次刷新，避免抖动重绘。
5. 单测覆盖切换规则。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_panel_visibility_rules.py -v`

### Task 7：回归与性能基线
**Files**
- Test: `tests/rename_ids/test_ridge_end_to_end.py`

**Steps**
1. 跑 Ridge 相关测试集。
2. 跑全量 pytest。
3. 记录中等点数（如 5k~20k）参数调节响应时间基线。

**Verify**
- `uv run pytest tests/rename_ids -v`
- `uv run pytest`

## 验收标准
1. 方向未设置时，ridge 参数不可编辑。
2. 参数变化后，自动弹出底部面板并更新 density+peaks。
3. map_canvas 实时显示 ridge 平行线，与峰值结果一致。
4. 每次调参都执行 focus ridge 与宽度对齐。
5. 切 tab 或切 nav 后底部面板自动收起。
6. 所有新增测试通过。
