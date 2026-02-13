# Rename IDs 模块 08：Map Canvas 渲染、图层切换与 ID 标注

## 目标
把流程中的可视化层（输入点、ridge、聚类结果、编辑态、文本标注）统一管理，保证交互清晰。

## 图层体系建议
- `dom_background_layers`（始终底层）
- `input_points_layer`
- `effective_points_layer`（可选）
- `ridge_preview_layer`
- `ordering_colored_layer`
- `editing_overlay_layer`
- `id_label_layer`

## Tab 联动显示策略
- File：重点显示输入层 + boundary + DOM。
- Ridge：重点显示 ridge 预览层。
- Ordering：重点显示聚类着色层，弱化输入层。
- Numbering：显示最终点 + 文本 ID。

## ID 字段显示
- 支持选择属性列作为标签字段。
- 默认 `FID`。
- 标签紧邻点显示，支持碰撞策略（后续可优化）。

## 关键实现点
- 统一图层管理器接口：`show/hide/reorder/update_data`。
- 文本标注单独 layer，避免和点图层混渲染造成性能问题。
- 颜色与 ridge_id 的映射全流程稳定。

## 风险与对策
- 标签过多导致卡顿：缩放阈值显示或采样显示。
- 图层频繁刷新闪烁：增量更新、双缓冲或批量提交。

## 头脑风暴切入点
- 继续沿用现有 map_canvas 能力，还是抽独立 `rename_canvas_controller`。
- 标签渲染是否支持描边和缩放自适应字号。
