# Rename IDs 模块 07：点编辑工具与撤销重做（Numbering Tab）

## 目标
实现点的增删改交互，按钮互斥，支持 Undo/Redo 与快捷键，并在编辑后自动重算归属和编号。

## 交互规则
- `Edit` 作为总开关：
  - 关闭时 Add/Move/Delete 全禁用。
- Add/Move/Delete 为互斥 toggle。
- Undo 普通按钮 + `Ctrl+Z`。
- Redo 新增按钮 + `Ctrl+Y` / `Ctrl+Shift+Z`。

## 编辑行为
- Add：光标变加号，鼠标跟随候选点，左键落点创建。
- Move：
  1. 单点拖移：点随鼠标移动，左键确认，右键或 Esc 取消。
  2. 框选批量移动：交互同上。
- Delete：
  1. 单点删除。
  2. 框选删除。

## 命令栈设计
- `EditCommand` 抽象：`apply()` / `revert()`。
- 子类：`AddPointCommand`、`MovePointCommand`、`DeletePointCommand`。
- 每次命令成功后：触发 Ordering + Numbering 增量重算。

## 输出
- 更新后的点集合。
- 可追溯的 undo/redo 历史。

## 风险与对策
- 批量操作性能：命令内记录索引快照，避免全量复制。
- 交互冲突：编辑模式与方向绘制模式互斥。

## 头脑风暴切入点
- 是否限制一次框选操作最大点数。
- 撤销粒度按“单次鼠标动作”还是“一次完整命令”。
