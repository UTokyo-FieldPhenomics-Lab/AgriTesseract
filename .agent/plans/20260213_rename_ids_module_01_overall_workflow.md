# Rename IDs 模块 01：总体流程与状态编排

## 目标
把 `src/gui/tabs/rename_ids.py` 的四个 TopTab（File/Ridge/Ordering/Numbering）串成一条可重复、可回滚、可导出的完整业务链路。

## 业务流程（全局）
1. 载入输入点（来自按钮加载或上一 Tab 的 send-to-next）。
2. 可选加载 boundary 与 DOM。
3. 在 Ridge 阶段确定垄方向与垄间距，生成候选 ridge lines。
4. 在 Ordering 阶段按 ridge 聚类点归属，得到每点 ridge membership。
5. 前置 map_canvas 能力（08A）：补齐点ID文本层和冲突高亮层。
6. 在 Numbering 阶段按规则生成 ID，支持编辑点并实时重算归属/编号。
7. 保存 shapefile 或发送到下一 Tab。

## 统一状态模型
- `RenameSessionState`:
  - `input_points_gdf`
  - `boundary_gdf | None`
  - `dom_layers[list]`
  - `effective_points_mask`
  - `ridge_direction_vector`
  - `ridge_peaks` / `ridge_lines_gdf`
  - `ordering_result`（每点 ridge_id / inlier / score）
  - `numbering_config`
  - `final_points_gdf`
- 所有 TopTab 只改自己负责的子状态，主状态集中在单一 Controller 中维护。

## 关键设计决策
- 任何参数变化都走防抖（已有 800ms timer 可复用）。
- 使用分阶段缓存，避免每次都从头跑完整流程。
- 编辑（增删改）后触发局部重算：Ordering + Numbering。

## 验收标准
- 从加载到保存可一条链路跑通。
- 任意阶段参数改动后 UI 与地图渲染一致更新。
- 可恢复/回滚（Undo/Redo）且不破坏状态一致性。

## 头脑风暴切入点
- 是否引入显式状态机（Idle/Loaded/RidgeReady/Ordered/Numbered）来限制非法操作。
- 大数据量下是全量重算还是分区增量重算。
