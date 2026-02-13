# Rename IDs 模块 03：垄方向选择与画布交互（Ridge Tab-方向）

## 目标
替换现有 `Auto | X-axis | Y-axis` 为更贴合业务的方向来源体系，并支持手动画两点定义方向。

## 方向来源设计
- 无 boundary：
  - 仅提供手动两点方向。
- 有 boundary：
  - 提供 `Boundary X Axis`、`Boundary Y Axis`。
  - 同时保留手动两点方向。

## 手动两点交互
1. 启动“设置垄方向”模式。
2. 左键首点确定起点。
3. 鼠标移动时显示动态连线预览。
4. 左键第二次确定终点，得到方向向量。
5. 支持重复设置并覆盖前值。

## 与地图旋转联动
- 方向确定后计算旋转角，使垄向量对齐到屏幕/逻辑坐标的 +Y 方向。
- 旋转只影响显示坐标与后续投影坐标，不修改原始地理坐标。

## 输出
- `ridge_direction_vector`
- `rotation_angle_deg`
- `ridge_direction_source`（boundary_x / boundary_y / manual_points）

## 关键实现点
- map_canvas 需新增临时线段 overlay 与拾取状态。
- 需要模式互斥：方向绘制模式不能与 add/move/delete 同时开启。

## 头脑风暴切入点
- 方向模式入口做成按钮还是下拉+按钮组合。
- 旋转是全局视图旋转还是仅算法坐标旋转。
