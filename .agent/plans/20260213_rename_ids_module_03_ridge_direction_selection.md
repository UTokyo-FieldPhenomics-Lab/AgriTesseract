# Rename IDs 模块 03：垄方向选择与画布交互（Ridge Tab-方向）

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

## 目标
替换现有 `Auto | X-axis | Y-axis` 为业务导向的方向来源体系，支持手动画两点定义方向，并在“用户确认后”才应用视图旋转。

## 架构决策（已确认）

### 决策 1：入口交互（方案 A，已定）
- Ridge 方向下拉固定提供 5 个选项：
  - `boundary x`
  - `boundary y`
  - `boundary -x`
  - `boundary -y`
  - `manual draw`
- 提供“设置垄方向”按钮：
  - 点击后自动把下拉切换到 `manual draw`。
  - 进入两点绘制模式。
- 当用户从 `manual draw` 切换到任一 `boundary *` 选项时，必须执行清理：
  - 清除手动点缓存（首点/末点）。
  - 清除手动画线 overlay 与动态预览线。
  - 清除 manual 方向向量及相关状态变量。

### 决策 2：旋转作用域（方案 A，已定）
- 默认仅记录：
  - `ridge_direction_vector`
  - `rotation_angle_deg`
  - `ridge_direction_source`
- 方向计算完成后弹出 Fluent 风格 MessageBox（with mask）：
  - 提示是否立即应用旋转来 follow 垄方向。
  - 用户确认后才调用 `set_rotation(angle)`。
  - 用户取消则仅保留向量与角度，不旋转视图。
- Top Tab 增加 `focus ridge` 按钮：
  - 点击后对当前已存储角度执行旋转应用。

## 方向来源设计细则
- 无 boundary：
  - 下拉仅可用 `manual_draw`（其余 boundary 选项禁用或隐藏，按现有 UI 一致性择一）。
- 有 boundary：
  - boundary 四个方向选项都可用；`manual_draw` 同时可用。
- boundary 方向向量定义：
  - `boundary_x` 使用 boundary 主轴 x。
  - `boundary_y` 使用 boundary 主轴 y。
  - `boundary_-x` 为 `-1 * boundary_x`。
  - `boundary_-y` 为 `-1 * boundary_y`。

## 手动两点交互（manual_draw）
1. 点击“设置垄方向”进入模式，并自动切换下拉到 `manual_draw`。
2. 首次左键记录起点 `p0`。
3. 鼠标移动显示 `p0 -> p_current` 动态线段预览。
4. 第二次左键记录终点 `p1`，计算并归一化方向向量 `v = normalize(p1 - p0)`。
5. 覆盖上一次 manual 结果（允许重复设置）。
6. 若向量长度接近 0，给出提示并保持待重试状态。

## 与地图旋转联动
- 方向确定后总是先计算 `rotation_angle_deg`（使垄向量对齐到逻辑 +Y）。
- 不自动旋转地图；旋转是用户确认后的显式动作。
- 旋转仅影响map_canvas的显示，不影响和修改后续算法投影坐标，均使用原始地理坐标。

## 输出契约
- `ridge_direction_vector: np.ndarray(shape=(2,), dtype=float64)`
- `rotation_angle_deg: float`
- `ridge_direction_source: str`，取值：
  - `boundary_x`
  - `boundary_y`
  - `boundary_-x`
  - `boundary_-y`
  - `manual_draw`

## 任务分解（可直接执行）

### Task 1：方向来源与旋转角计算工具
**Files**
- Create: `src/utils/rename_ids/ridge_direction.py`
- Modify: `src/utils/rename_ids/__init__.py`
- Test: `tests/rename_ids/test_ridge_direction.py`

**Steps**
1. 先写失败测试：覆盖 boundary 正反向、manual 两点、零长度向量异常。
2. 实现最小函数：向量归一化、source 解析、角度计算。
3. 运行测试并通过。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_direction.py -v`

### Task 2：Ridge Tab 方向入口 UI 重构
**Files**
- Modify: `src/gui/tabs/rename_ids.py`
- Modify: `src/gui/resource/i18n/en_US.json`
- Modify: `src/gui/resource/i18n/zh_CN.json`
- Modify: `src/gui/resource/i18n/ja_JP.json`
- Test: `tests/rename_ids/test_ridge_tab_direction_ui.py`

**Steps**
1. 先写失败测试：下拉包含 5 项，按钮点击后切到 `manual_draw`。
2. 替换旧 `Auto/X/Y` 文案与索引语义。
3. 增加“设置垄方向”和“focus ridge”按钮。
4. 运行测试并通过。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_tab_direction_ui.py -v`

### Task 3：manual_draw 状态机与清理规则
**Files**
- Modify: `src/gui/tabs/rename_ids.py`
- Modify: `src/gui/components/map_canvas.py`（如需补充 handler 注册 API）
- Test: `tests/rename_ids/test_ridge_manual_draw_interaction.py`

**Steps**
1. 先写失败测试：首点、动态预览、次点成向量、重复覆盖。
2. 实现状态变量与 overlay 生命周期。
3. 实现“manual -> boundary_*”时的清理逻辑。
4. 运行测试并通过。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_manual_draw_interaction.py -v`

### Task 4：旋转确认弹窗与 focus ridge 动作
**Files**
- Modify: `src/gui/tabs/rename_ids.py`
- Reference: `.agent/references/fluentwidget_example/gallery/app/view/dialog_interface.py`
- Test: `tests/rename_ids/test_ridge_rotation_confirm_flow.py`

**Steps**
1. 先写失败测试：方向计算后弹窗，确认才旋转，取消不旋转。
2. 按 Fluent 风格实现 MessageBox with mask。
3. 实现 `focus ridge` 按钮触发 `set_rotation(saved_angle)`。
4. 运行测试并通过。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_rotation_confirm_flow.py -v`

### Task 5：模式互斥与参数信号输出契约
**Files**
- Modify: `src/gui/tabs/rename_ids.py`
- Test: `tests/rename_ids/test_ridge_mode_exclusion_and_payload.py`

**Steps**
1. 先写失败测试：方向绘制模式与 add/move/delete 互斥。
2. 输出 payload 改为 source/vector/angle 语义，不再依赖旧 `direction_index`。
3. 运行测试并通过。

**Verify**
- `uv run pytest tests/rename_ids/test_ridge_mode_exclusion_and_payload.py -v`

### Task 6：回归验证
**Files**
- Test: `tests/rename_ids/test_dom_loading.py`
- Test: `tests/rename_ids/test_boundary.py`
- Test: `tests/test_tab_handoff.py`

**Steps**
1. 运行 rename_ids 相关测试。
2. 运行全量 pytest，确保无回归。

**Verify**
- `uv run pytest tests/rename_ids -v`
- `uv run pytest`

## 风险与对策
- 用户频繁切换 source 导致状态脏：统一通过 guard clause 清理 manual 状态。
- 旋转确认打断操作节奏：仅在方向更新后弹一次，后续可由 `focus ridge` 主动触发。
- boundary 不存在时误用 boundary source：UI 层禁用并在逻辑层二次校验。
