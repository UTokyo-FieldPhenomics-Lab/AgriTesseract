# Rename IDs 模块 06：编号规则引擎（Numbering Tab）实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 基于模块05分垄结果生成稳定且可配置的编号，支持冲突阻断与地图高亮，为保存与 send-next 提供最终 `new_id`。

**Architecture:** 首版采用结构化规则配置，不开放自由模板。排序完全在模块06内完成：先按 `ridge_id` 分组，再按方向向量投影得到垄顺序和垄内顺序。编号由纯函数引擎生成，控制器负责 UI、防抖、冲突检测和地图标注更新。

**Tech Stack:** PySide6, qfluentwidgets, numpy, pandas, geopandas, pyqtgraph, pytest。

---

## 设计决策（已锁定）
1. 首版仅做结构化规则（`ridge_plant`、`continuous`），不做 custom template。
2. 冲突策略：阻断保存和发送，地图高亮冲突点，不自动改号。
3. 排序策略：
   - 先按 `ridge_id` 分组（忽略 `-1`）。
   - 垄序：按垄法向投影排序（支持反向）。
   - 垄内序：按顺垄向量投影排序（支持反向）。
4. 模块05不产出排序字段，模块06全权负责排序与编号。

## 前置依赖
- 需先完成模块08A（点ID文本层与冲突高亮层），否则 Numbering 可视化与冲突定位不可用。

## UI 控件最小集合（首版）

### 分组 A：模式选择
- `Numbering Mode`：`Ridge + Plant` / `Continuous`

### 分组 B：Ridge 规则（当 mode = Ridge + Plant）
- `Ridge Direction`：`Left -> Right` / `Right -> Left`
- `Ridge Sequence`：`Numeric` / `Alpha`
- `Ridge Offset`：整数输入（>= 0）
- `Ridge Prefix`：文本输入
- `Ridge Suffix`：文本输入

### 分组 C：Plant 规则（当 mode = Ridge + Plant）
- `Plant Direction`：`Along Ridge` / `Against Ridge`
- `Plant Sequence`：`Numeric` / `Alpha`
- `Plant Offset`：整数输入（>= 0）
- `Plant Prefix`：文本输入
- `Plant Suffix`：文本输入

### 分组 D：Continuous 规则（当 mode = Continuous）
- `Start Number`：整数输入（>= 1）
- `Global Prefix`：文本输入
- `Global Suffix`：文本输入

### 分组 E：状态与动作
- `Conflict Summary`（只读标签）
- `Apply Numbering`（触发计算，保留防抖自动刷新）
- `Save` / `Send to Next`：冲突时自动禁用

## 输入契约（来自模块03/05）
- `points_gdf`：原始点与几何。
- `ordering_result_gdf`：至少含 `fid`、`ridge_id`、`is_inlier`、`geometry`。
- `ridge_direction_state`：方向向量与角度。

## 输出契约
- `numbering_result_gdf`（与 points 对齐）：
  - `fid: int`
  - `ridge_id: int`
  - `is_inlier: bool`
  - `ridge_rank: int`（无效点为 `-1`）
  - `plant_rank: int`（无效点为 `-1`）
  - `new_id: str`
  - `ridge_label: str`
  - `plant_label: str`
  - `id_conflict: bool`
- `numbering_stats`：
  - `total_points`
  - `numbered_points`
  - `ignored_points`
  - `conflict_count`

## 任务分解（可直接执行）

### Task 1：编号规则数据结构与失败测试

**Files:**
- Create: `src/utils/rename_ids/numbering_rules.py`
- Modify: `src/utils/rename_ids/__init__.py`
- Test: `tests/rename_ids/test_numbering_rules.py`

**Steps:**
1. 先写失败测试：
   - Numeric/Alpha 序列（含 A..Z..AA）。
   - prefix/suffix 与 offset 组合。
2. 定义首版规则结构：
   - `NumberingConfig`
   - `RidgeRule`
   - `PlantRule`
   - `ContinuousRule`
3. 实现 label 生成纯函数。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_rules.py -v`

### Task 2：排序引擎（模块06内完成）

**Files:**
- Create: `src/utils/rename_ids/numbering_sort.py`
- Test: `tests/rename_ids/test_numbering_sort.py`

**Steps:**
1. 先写失败测试：
   - ridge 顺序反转。
   - plant 顺序反转。
   - ignored 点保留 `-1`。
2. 实现几何投影排序：
   - 垄序按法向投影。
   - 垄内序按顺垄投影。
3. 输出 `ridge_rank` 和 `plant_rank`。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_sort.py -v`

### Task 3：编号引擎（模式与组装）

**Files:**
- Create: `src/utils/rename_ids/numbering_engine.py`
- Test: `tests/rename_ids/test_numbering_engine.py`

**Steps:**
1. 先写失败测试：
   - `ridge_plant` 模式输出 `ridge_label`、`plant_label`、`new_id`。
   - `continuous` 模式全局递增。
2. 实现 `build_numbering_result(...)`：
   - 使用 Task2 排序结果。
   - 生成新 ID。
3. 保证 ignored 点不参与编号。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_engine.py -v`

### Task 4：冲突检测与阻断策略

**Files:**
- Modify: `src/utils/rename_ids/numbering_engine.py`
- Create: `src/utils/rename_ids/numbering_conflict.py`
- Test: `tests/rename_ids/test_numbering_conflict.py`

**Steps:**
1. 先写失败测试：重复 `new_id` 检测和冲突点索引输出。
2. 实现 `detect_id_conflicts(...)`。
3. 给结果添加 `id_conflict` 字段。
4. 输出冲突统计供 UI 使用。
5. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_conflict.py -v`

### Task 5：Numbering 控制器与地图高亮

**Files:**
- Create: `src/utils/rename_ids/numbering_controller.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_numbering_controller.py`

**Steps:**
1. 先写失败测试：参数变化触发重算并更新结果层。
2. 控制器接入 Numbering UI 参数与防抖更新。
3. 地图显示 `new_id` 文本与冲突点高亮层。
4. 计算并显示 `numbering_stats`。
5. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_controller.py -v`

### Task 6：UI 最小控件接入与状态禁用

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`
- Modify: `src/gui/resource/i18n/zh_CN.json`
- Modify: `src/gui/resource/i18n/en_US.json`
- Modify: `src/gui/resource/i18n/ja_JP.json`
- Test: `tests/rename_ids/test_numbering_ui_state.py`

**Steps:**
1. 先写失败测试：
   - mode 切换时分组控件启禁正确。
   - ordering 结果缺失时全部禁用。
2. 按“最小集合”补齐控件和文案。
3. 接入冲突提示标签与按钮禁用逻辑。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_ui_state.py -v`

### Task 7：保存/发送阻断联动

**Files:**
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_numbering_save_send_guard.py`

**Steps:**
1. 先写失败测试：冲突存在时 Save/Send 禁用。
2. 无冲突时允许保存与发送。
3. 错误提示包含冲突数量与示例 ID。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/rename_ids/test_numbering_save_send_guard.py -v`

### Task 8：端到端回归

**Files:**
- Test: `tests/rename_ids/test_numbering_end_to_end.py`

**Steps:**
1. 构造包含 ignored 点、冲突场景、方向反转场景的样本。
2. 跑“ordering -> numbering -> conflict guard”完整流。
3. 断言输出契约字段完整、冲突阻断生效。
4. 全量回归。

**Verify:**
- `uv run pytest tests/rename_ids -v`
- `uv run pytest`

## 风险与对策
- **规则复杂度上升**：首版坚守结构化规则，模板延期。
- **冲突过多影响体验**：提供冲突统计和地图高亮定位。
- **方向反转导致编号跳变**：排序和编号统一走单一引擎重算。
- **文本标注性能压力**：按缩放阈值显示或批量刷新。

## 验收标准
1. Numbering Tab 可在 `ridge_plant` 与 `continuous` 间切换并正确编号。
2. 排序不依赖模块05，模块06内部可稳定重建顺序。
3. 冲突时保存/发送被阻断，且冲突点在地图高亮。
4. ignored 点不参与编号，但保留在结果中。
5. 新增测试全部通过，模块05->06 数据链路可直接联动。
