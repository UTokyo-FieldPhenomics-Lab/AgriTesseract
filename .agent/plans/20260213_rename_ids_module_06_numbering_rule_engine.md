# Rename IDs 模块 06：编号规则引擎（Numbering Tab）

## 目标
重构现有 format 选择，提供可组合、可扩展的 ID 生成规则系统。

## 规则能力
- 垄编号维度：
  - 方向：左到右 / 右到左（基于旋转后坐标）。
  - 序列：数字或字母（A..Z..AA..AB）。
  - offset：起始偏移。
  - prefix/suffix。
- 垄内植株编号维度：
  - 方向：顺垄向量 / 反垄向量。
  - 序列：数字或字母。
  - offset + prefix/suffix。
- 连续编号模式：
  - 按“垄顺序 + 垄内顺序”全局 1..N。

## 建议数据结构
- `NumberingConfig`:
  - `mode`（ridge_plant / continuous / custom_template）
  - `ridge_rule`（dir, seq_type, offset, prefix, suffix）
  - `plant_rule`（dir, seq_type, offset, prefix, suffix）
  - `template`（可选，后续扩展）

## 输出
- 每点最终字段：
  - `new_id`
  - `ridge_label`
  - `plant_label`

## 关键实现点
- 编号函数纯函数化，输入排序后的点集 + config，输出稳定可测试。
- i18n 文案与 UI 控件分组要清晰（基础模式与高级模式）。

## 头脑风暴切入点
- “custom”模式采用模板语法（如 `{ridge}{plant}`）还是 GUI 拼装器。
- 编号冲突检测与高亮提示策略。
