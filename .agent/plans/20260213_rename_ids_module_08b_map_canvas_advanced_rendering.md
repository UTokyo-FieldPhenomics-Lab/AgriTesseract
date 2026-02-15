# Rename IDs 模块 08B：Map Canvas 进阶渲染与图层管理

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在08A最小能力之上，补齐长期可扩展的图层管理与渲染策略，支撑模块07编辑和模块09导出前检查的复杂可视化需求。

**Architecture:** 08B 聚焦“体系化能力”：图层分组、批量更新、显示策略和可扩展底部面板协同。保持对现有 `MapCanvas` API 向后兼容，新增能力优先以 helper/controller 方式接入。

**Tech Stack:** PySide6, pyqtgraph, qfluentwidgets, geopandas, numpy, pytest。

---

## 范围
1. 图层语义分组（input/ordering/numbering/editing/background）。
2. 图层切换模板（按 TopTab 自动切换可见性）。
3. 标签渲染增强（可选避让、字号缩放）。
4. 批量图层更新接口，减少闪烁。
5. 底部面板与地图联动策略通用化。

## 任务分解（可直接执行）

### Task 1：图层分组与可见性模板

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/gui/test_layer_visibility_profiles.py`

**Steps:**
1. 定义图层分组元数据。
2. 提供 `apply_visibility_profile(profile_name)`。
3. 在 TopTab 切换时应用 profile。
4. 运行测试并通过。

**Verify:**
- `uv run pytest tests/gui/test_layer_visibility_profiles.py -v`

### Task 2：标签增强与可读性策略

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/gui/test_label_render_enhancement.py`

**Steps:**
1. 增加缩放自适应字号。
2. 增加简易碰撞规避（可选开关）。
3. 运行测试并通过。

**Verify:**
- `uv run pytest tests/gui/test_label_render_enhancement.py -v`

### Task 3：批量更新与防闪烁

**Files:**
- Modify: `src/gui/components/map_canvas.py`
- Test: `tests/gui/test_map_canvas_batch_update.py`

**Steps:**
1. 提供批量更新上下文（暂停重绘 -> 批量提交）。
2. 合并多次 layer refresh。
3. 运行测试并通过。

**Verify:**
- `uv run pytest tests/gui/test_map_canvas_batch_update.py -v`

### Task 4：底部面板联动通用化

**Files:**
- Modify: `src/gui/components/bottom_panel_host.py`
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/gui/test_bottom_panel_profiles.py`

**Steps:**
1. 定义不同模块的 panel profile。
2. 支持 tab/nav 切换时自动开关与回收。
3. 运行测试并通过。

**Verify:**
- `uv run pytest tests/gui/test_bottom_panel_profiles.py -v`

## 验收标准
1. TopTab 切换可一键应用图层显示模板。
2. 大量标签场景下可读性和流畅度提升。
3. 批量更新减少图层闪烁。
4. 08A 与 08B 接口兼容，不破坏模块06功能。
