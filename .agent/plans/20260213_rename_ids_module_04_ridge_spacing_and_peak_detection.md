# Rename IDs 模块 04：垄间距估计与峰值检测可视化（Ridge Tab-间距）

## 目标
基于方向向量把有效点投影到垂线，计算密度分布并用峰值确定每条垄中心线。

## 算法流程（参考 `14_order_by_ridge.py`）
1. 过滤有效点（boundary 内）。
2. 将点投影到与垄方向垂直的一维轴。
3. 按 `strength ratio` 做离散分箱统计密度。
4. 用 `find_peaks(distance, height)` 找峰值。
5. 依据峰值 + 方向向量 + 有效点范围生成候选 ridge lines。

## UI 参数
- `strength ratio`
- `distance`
- `height`
- 全部参数变化走防抖后实时刷新。

## 可视化要求
- 顶层叠加层展示：
  - 一维密度曲线
  - 峰值点
  - 每条候选 ridge 实线（高饱和区分色）
- 用户调参后即时重绘。

## 输出
- `ridge_density_profile`
- `ridge_peaks`
- `ridge_lines_gdf`

## 风险与对策
- 峰值过检/漏检：提供参数恢复默认与自动建议范围。
- 点量大时刷新慢：缓存投影结果，仅重算峰值与线层。

## 头脑风暴切入点
- 密度图放在地图叠层还是额外小面板。
- 颜色分配是固定调色板还是按 ridge_id 稳定哈希。
