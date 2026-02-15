# 2026-02-15 Ordering Tab Single-Layer Follow-ups

## 背景
- 目标：完成 Rename IDs 模块 05 的 Ordering 归属流程，并根据手动 UI 反馈完成性能与交互修正。
- 范围：算法归属、RANSAC、UI 触发时机、单图层多颜色渲染、图层可见性与排序一致性。

## 本次提交记录（按时间顺序）
- `f88e16c` `test(rename_ids): add ridge ordering core failing specs`
  - 新增 ordering 核心失败用例，锁定空输入、单垄、多垄、ignored 规则。
- `0d06c60` `feat(rename_ids): implement buffer-based ridge assignment`
  - 实现基于 buffer 的垄归属与 ignored 标记（`ridge_id=-1`, `is_inlier=False`）。
- `09aca92` `feat(rename_ids): add optional per-ridge ransac filtering`
  - 增加可选按垄 RANSAC 过滤，仅更新 `is_inlier`，保留 `ridge_id`。
- `9b9cbe1` `feat(rename_ids): wire ordering controller with ridge color layers`
  - 打通 Ordering 控制器与 UI/地图联动，完成结果回写与图层渲染链路。
- `382137b` `feat(rename_ids): gate ordering UI by ridge readiness`
  - 按 ridge readiness 启用/禁用 Ordering 参数，并增加统计文案显示。
- `68d72a0` `test(rename_ids): add ordering end-to-end contract regression`
  - 增加端到端回归，校验输出契约与统计一致性。
- `dccf96b` `perf(rename_ids): defer ordering run until ordering tab active`
  - 性能优化：仅在 Ordering top tab 激活时执行 ordering，Ridge tab 不触发。
- `7e4e9f4` `feat(map_canvas): support per-point colors in one point layer`
  - `add_point_layer` 支持按点颜色列表，实现单图层多颜色点渲染。
- `6ddb45f` `feat(rename_ids): render ordering result as single colored layer`
  - Ordering 输出改为单图层 `ordering_points`，按 `ridge_id` 着色，ignored 特殊样式。
- `8b5832a` `fix(map_canvas): treat rgba tuple as scalar point color`
  - 修复 RGBA tuple 被误判为颜色列表导致长度校验报错的问题。
- `bf4fed1` `fix(rename_ids): sync ordering visibility and layer order per tab`
  - 修复 tab 切换时图层显示与排序：Ridge/Ordering 场景各自稳定。
- `acb0f08` `test(rename_ids): assert ordering_points in end-to-end flow`
  - 端到端补充断言：必须存在 `ordering_points` 图层。

## 用户手动反馈与对应修复

### 1) Ridge tab 内不应自动执行 Ordering
- 反馈：在 Ridge tab 操作会提前触发 Ordering 计算并更新图层，带来额外开销。
- 修复：`dccf96b`
- 结果：仅在 Ordering top tab 可见时运行 Ordering；切入 Ordering 时触发首算。

### 2) Ordering 结果应为单图层而非 `ordering_ridge_{n}` 多图层
- 反馈：希望一个图层承载不同颜色点，便于图层管理。
- 修复：`7e4e9f4` + `6ddb45f`
- 结果：输出单图层 `ordering_points`，颜色按点应用（`ridge_id` 映射）；ignored 单独样式。

### 3) 加载点图层报错：`Per-point color list length must match point count`
- 反馈：日志报错，影响点图层加载。
- 根因：RGBA tuple 被误识别为 per-point 颜色序列。
- 修复：`8b5832a`
- 结果：RGB/RGBA tuple 视为单色输入，列表仅用于真正的逐点着色。

### 4) Ordering/Ridge tab 切换时图层可见性与顺序要稳定
- 反馈：
  - 切回 Ridge 时应隐藏 `ordering_points`，显示 `rename_points`。
  - 两个 tab 场景下图层顺序应按预期，不因切换而漂移。
- 修复：`bf4fed1`
- 结果：按 tab 同步关键图层可见性；按场景应用稳定优先级排序。

## 计划文件更新说明
- 用户手动更新执行计划文件：
  - `.agent/plans/20260213_rename_ids_module_05_ordering_ransac_clustering.md`
- 本次日志将该手动反馈驱动的增量任务与对应提交做了可追溯对齐。

## 回归验证（最终）
- `uv run pytest tests/rename_ids/test_ordering_end_to_end.py -v` 通过
- `uv run pytest tests/rename_ids -v` 75 passed
- `uv run pytest` 137 passed
