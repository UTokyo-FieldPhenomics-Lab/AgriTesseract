# Rename IDs 模块 09：保存输出与发送下一步

## 目标
完成最终结果落盘与跨 Tab 传递，保证“boundary 外点不保存”的业务约束。

## 功能范围
- Save SHP：
  - 输出点几何与新 ID 字段。
  - 仅保存有效点（boundary 内）。
  - 保留必要原始字段与新增字段。
- Send to Next：
  - 发送统一数据结构到下一 Tab。
  - 与 `Load Shp` 路径加载后的内部结构保持一致。

## 输出字段建议
- `orig_id`
- `new_id`
- `ridge_id`
- `plant_order`
- `is_inlier`

## 关键实现点
- 导出前执行最终校验：
  - CRS 存在且一致。
  - `new_id` 不为空。
  - 几何类型均为 Point。
- 若存在 ignored/outside 点，保存日志或弹窗提示统计。

## 验收标准
- 保存文件可被 QGIS 正常读取，字段完整。
- send-to-next 接收端无需额外适配即可直接消费。
- boundary 外点不出现在导出结果中。

## 头脑风暴切入点
- 是否同时导出“完整集（含无效点）”与“有效集”两个文件。
- send-to-next 传路径还是传内存对象（性能 vs 解耦）。
