# Rename IDs 模块 08A：Map Canvas 前置增强（05->06 之间）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在进入模块06编号前补齐 map_canvas 最小能力：点ID文本标注、冲突高亮、图层显隐/刷新接口，保证 Numbering 可完整可视化落地。

**Architecture:** 08A 只实现“编号必需能力”，避免把完整图层系统一次做重。以 `MapCanvas` 通用 API + `rename_ids.py` 调用为主，不引入新的大型渲染框架。文本标注采用独立 overlay layer，样式固定黑字白描边，支持批量刷新。

**Tech Stack:** PySide6, pyqtgraph, qfluentwidgets, geopandas, numpy, pytest。

---

## 范围（前置最小集）
1. 点图层文本标注（按字段显示）。
2. 文本样式：黑色文字 + 白色描边。
3. 文本层 API：创建、更新、清空、显隐。
4. 冲突点高亮层 API（模块06冲突阻断使用）。
5. Numbering Tab 切换时标签层显示策略。

## 不在 08A 范围
- 不做复杂标签避让算法。
- 不做完整多面板图层体系重构。
- 不做高级性能优化（仅做必要阈值控制）。

## 任务分解（可直接执行）

### Task 1：文本标注图层数据模型与失败测试

**Files:**
- Create: `src/utils/rename_ids/label_style.py`
- Test: `tests/rename_ids/test_label_style.py`

**Steps:**
1. 先写失败测试：默认样式、黑字白描边参数校验。
2. 定义 `LabelStyle` 数据结构（颜色、描边、字号、偏移）。
3. 实现默认样式工厂函数。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_label_style.py -v`

### Task 2：MapCanvas 文本标注 API

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/gui/test_map_canvas_text_labels.py`

**Steps:**
1. 先写失败测试：添加、更新、清空、显隐文本层。
2. 新增通用接口（命名可调整但语义固定）：
   - `set_point_labels(layer_name, xy_array, text_list, style)`
   - `clear_point_labels(layer_name)`
   - `set_layer_visibility(layer_name, visible)`（复用现有）
3. 文本渲染为黑字白描边（QGraphicsTextItem + 描边效果或双层文本实现）。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/gui/test_map_canvas_text_labels.py -v`

### Task 3：冲突点高亮层 API

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/gui/test_map_canvas_conflict_overlay.py`

**Steps:**
1. 先写失败测试：冲突点层可创建/刷新/清空。
2. 新增冲突层 helper（如红圈或黄底强调，统一层名）。
3. 保证与普通点层并存，不覆盖底层数据。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/gui/test_map_canvas_conflict_overlay.py -v`

### Task 4：rename_ids 与 Numbering 显示联动

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_numbering_label_visibility.py`

**Steps:**
1. 先写失败测试：切到 Numbering 时显示标签层，离开时隐藏或收敛显示。
2. 将“显示字段”默认设为 `fid`，后续由模块06切换到 `new_id`。
3. 接入冲突高亮层显示开关。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_label_visibility.py -v`

### Task 5：轻量性能保护与回归

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/gui/test_map_canvas_label_perf_guard.py`

**Steps:**
1. 增加最小性能阈值策略（例如缩放过小时隐藏标签）。
2. 增加批量更新路径，减少单点反复重绘。
3. 跑局部与全量回归。

**Verify:**
- `uv run pytest tests/gui/test_map_canvas_label_perf_guard.py -v`
- `uv run pytest tests/rename_ids -v`

## 验收标准
1. MapCanvas 能按字段显示点标签，样式为黑字白描边。
2. Numbering 前置流程可见 `fid` 标签，编号后可切换 `new_id`。
3. 冲突点可单独高亮并可清除。
4. 这些能力不依赖模块06逻辑即可独立运行。
