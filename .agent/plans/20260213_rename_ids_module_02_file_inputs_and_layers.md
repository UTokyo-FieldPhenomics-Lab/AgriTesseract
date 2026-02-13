# Rename IDs 模块 02：文件输入与图层管理（File Tab）

## 目标
实现 `Load Shp`、`Load Boundary`、`Load DOM` 的统一加载逻辑，并确保 map/layer tree 呈现规则稳定。

## 功能范围
- 点 shp 加载：
  - 支持手动加载。
  - 支持接收上一 Tab send-to-next 数据。
  - 二者标准化为同一内部数据结构（字段、CRS、几何类型一致）。
- boundary 加载（可选）：
  - 生成有效点 mask（boundary 内点才参与后续）。
  - 计算最小面积外接矩形，提供轴向候选。
- 多 DOM 加载：
  - 支持多选 tif/tiff。
  - DOM 图层在 file tree 始终置底。

## 输入/输出
- 输入：shp/boundary/DOM 文件路径或上一流程传入数据对象。
- 输出：
  - 标准化 `input_points_gdf`
  - `boundary_gdf` 与 `boundary_obb_axes`
  - 排序后的 `dom_layers`

## 关键实现点
- 增加 `normalize_input_points()` 统一列名与 ID 基础字段（默认 FID）。
- 坐标系检查：boundary/DOM 与 points 不一致时给出转换或阻断提示。
- 图层优先级：编辑层 > 结果层 > 输入点层 > DOM 背景层。

## 风险与对策
- 来自上一 Tab 的字段不完整：需要兜底补列并记录来源。
- 大体量 DOM 导致卡顿：使用延迟加载和缩略显示策略。

## 头脑风暴切入点
- 数据标准化放在 Tab 内还是抽 `src/utils/rename_io.py`。
- “置底”是每次加载重排还是维护层级索引。
