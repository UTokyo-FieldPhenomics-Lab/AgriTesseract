# Rename IDs 模块 05：按垄归属聚类与 RANSAC（Ordering Tab）

## 目标
把点归属到各 ridge，并用 buffer + 可选 RANSAC 控制鲁棒性，实时反馈颜色与归属结果。

## 算法流程
1. 用 ridge peaks 计算相邻 ridge 间距并推导每 ridge 作用带。
2. 按 `buffer` 选出每 ridge 候选点。
3. 若启用 RANSAC：
   - 过滤离群点（参数：`residual`, `max_trials`）。
4. 生成每点 `ridge_id`、`inlier` 标记。

## UI 行为
- 参数变化防抖后实时重算。
- 在 Ordering Tab 激活时：
  - 可隐藏原始 input points 层。
  - 显示按 ridge 着色的结果层。

## 输出
- `ordering_result_df/gdf`：
  - `point_id`
  - `ridge_id`
  - `is_inlier`
  - `order_in_ridge`（可选）

## 关键实现点
- `check_ransac` 勾选控制参数输入启用状态（已有基础）。
- 颜色映射保持跨 Tab 稳定，避免用户视觉混乱。

## 风险与对策
- RANSAC 参数敏感：给出推荐默认值 + 一键恢复。
- 边缘点不稳定：保留“忽略点”统计并明确显示数量。

## 头脑风暴切入点
- 是否支持每条 ridge 独立参数（进阶模式）。
- ignored 点后续编号策略（跳过/连续补号/保留 -1）。
