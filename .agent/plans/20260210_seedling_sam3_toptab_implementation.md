# Seedling Detect (SAM3 + TopTab) 实施计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 Seedling 检测页完成可用的 SAM3 文本提示词推理工作流，支持 Office 风格 TopTab、预览区快速调参、全图切块推理、点结果 CRUD、结果缓存/回读，以及 GIS 文件导出。

**Architecture:** 界面编排集中在 `seedling_detect.py`，地图交互能力扩展在 `map_canvas.py`，核心算法统一放到 `src/utils/`。推理使用 `QThread` 后台执行，主线程只负责 UI 与图层更新。中间结果落盘为 `results.pth`，可视化导出为 `preview.pdf`，最终输出 `bbox.shp` 与 `mask.shp`。

**Tech Stack:** PySide6, PySide6-Fluent-Widgets, pyqtgraph, ultralytics (SAM3), numpy, pandas, pyshp, matplotlib(PdfPages), pytest。

---

## 一、范围与确认项（已锁定）

1. SHP 点结果 ID 字段使用 `fid`。
2. 预览交互使用 B 模式：鼠标移动显示跟随框，单击锁定。
3. 预览框大小支持 `+/-` 快捷键调整，并与 TopTab 参数双向联动。
4. SAM3 核心算法与流程逻辑放 `src/utils/`。
5. 中间结果目录产物固定为：
   - `results.pth`
   - `preview.pdf`
   - `bbox.shp`
   - `mask.shp`
6. mask 保存策略：像素级 mask 转 polygon 后保存。
7. `preview.pdf` 每页为一个 slice：
   - mask = 0.5 alpha
   - 每个实例颜色不同且鲜亮
   - bbox 与实例颜色一致
   - 中心点红色实心点
   - 附小地图展示当前 slice 在整体位置
8. SAM3 权重路径在设置页配置；不可用时 SAM3 相关按钮全部 disabled，并给出提示。

## 二、文件改动计划

### Task 1: 配置系统与设置页扩展

**Files:**
- Modify: `src/gui/config.py`
- Modify: `src/gui/tabs/settings.py`
- Modify: `src/gui/resource/i18n/zh_CN.json`
- Modify: `src/gui/resource/i18n/en_US.json`
- Modify: `src/gui/resource/i18n/ja_JP.json`

**Steps:**
1. 新增配置项 `sam3WeightPath`（文件路径）。
2. 设置页新增“选择 SAM3 权重文件”卡片并持久化。
3. 增加权重可用性校验函数（文件存在、可读）。
4. 增加文案键值（按钮、提示、状态）。

### Task 2: Seedling TopTab UI 重构

**Files:**
- Modify: `src/gui/tabs/seedling_detect.py`

**Steps:**
1. 将顶部功能区重构为 TopTab：`文件`、`SAM3`、`点结果`。
2. 文件 Tab：DOM 选择与显示。
3. SAM3 Tab：
   - 模型参数（prompt/conf/iou）
   - 预览区参数（preview size）
   - 预览控制（选区、预览推理）
   - 执行控制（slice size/overlap、全图推理）
   - 中间结果控制（保存/读取）
4. 点结果 Tab：View/Add/Move/Delete/Undo + 保存结果。
5. 构建统一按钮状态切换（idle/selecting/running）。

### Task 3: MapCanvas 预览框与点编辑能力

**Files:**
- Modify: `src/gui/components/map_canvas.py`

**Steps:**
1. 新增预览框 overlay 状态（hover/locked/size）。
2. 新增 `+/-` 快捷键尺寸变更信号与接口。
3. 新增预览框锁定点击信号（返回 geo bounds）。
4. 新增点图层显示与命中检测接口。
5. 新增点 CRUD 操作与拖拽移动。

### Task 4: SAM3 核心算法（utils）

**Files:**
- Create: `src/utils/seedling_sam3.py`
- Create: `src/utils/seedling_slice.py`
- Create: `src/utils/seedling_points.py`
- Create: `src/utils/seedling_io.py`
- Create: `src/utils/seedling_cache.py`
- Modify: `src/utils/__init__.py`

**Steps:**
1. `seedling_sam3.py`: SAM3 text prompt 推理封装与统一结果结构。
2. `seedling_slice.py`: 切块窗口、坐标映射、边界过滤、NMS/IoS、全图合并。
3. `seedling_points.py`: 点数据结构、CRUD、撤销命令。
4. `seedling_io.py`: `pandas + pyshp` 导出点/bbox/mask shp 与 prj。
5. `seedling_cache.py`: `results.pth` 读写与 `preview.pdf` 输出。

### Task 5: 后台执行线程

**Files:**
- Create: `src/gui/tabs/seedling_worker.py`
- Modify: `src/gui/tabs/seedling_detect.py`

**Steps:**
1. QThread Worker 承载全图推理。
2. 进度、错误、完成信号回传。
3. UI 期间禁用 SAM3 相关触发按钮。

### Task 6: 结果落盘与回读联调

**Files:**
- Modify: `src/gui/tabs/seedling_detect.py`
- Modify: `src/utils/seedling_cache.py`
- Modify: `src/utils/seedling_io.py`

**Steps:**
1. 选择结果目录并保存上述 4 项产物。
2. 从目录读取 `results.pth` 并在地图恢复点与覆盖层。
3. 若 `preview.pdf` 不存在，可按读取数据重建。

### Task 7: 测试与回归

**Files:**
- Create: `tests/test_seedling_slice.py`
- Create: `tests/test_seedling_points.py`
- Create: `tests/test_seedling_io.py`
- Create: `tests/test_seedling_cache.py`

**Steps:**
1. 核心纯函数先测（切块映射、NMS、polygon 转换）。
2. IO 层测试（shp 字段、记录数量、prj 写出）。
3. cache 层测试（pth round-trip，PDF 页数）。
4. 运行：`uv run pytest`。

## 三、数据结构草案

`results.pth`:

```python
{
    "meta": {
        "dom_path": str,
        "crs_wkt": str,
        "sam3_weight_path": str,
        "prompt": str,
        "confidence": float,
        "iou": float,
        "slice_size": int,
        "overlap": float,
        "preview_size": int,
        "created_at": str,
    },
    "slices": [
        {
            "slice_id": int,
            "row": int,
            "col": int,
            "bounds_geo": [xmin, ymin, xmax, ymax],
            "boxes_geo": [[xmin, ymin, xmax, ymax], ...],
            "scores": [float, ...],
            "centers_geo": [[x, y], ...],
            "mask_polygons_geo": [
                [[x, y], [x, y], ...],
                ...
            ],
        },
        ...
    ],
    "merged": {
        "boxes_geo": [[xmin, ymin, xmax, ymax], ...],
        "scores": [float, ...],
        "centers_geo": [[x, y], ...],
        "mask_polygons_geo": [
            [[x, y], [x, y], ...],
            ...
        ],
    },
}
```

## 四、验收标准

1. Seedling 页显示 TopTab，功能分区符合需求。
2. 预览框可 hover 跟随、点击锁定、`+/-` 缩放并与参数联动。
3. SAM3 权重不可用时按钮禁用并有清晰提示。
4. 全图推理在后台线程运行，UI 无卡死。
5. 可保存并回读中间结果目录。
6. 目录内存在 `results.pth`、`preview.pdf`、`bbox.shp`、`mask.shp`。
7. `preview.pdf` 每页渲染符合配色/透明度/小地图要求。
8. 点结果支持增删改查与撤销，导出点 `fid` 字段正确。
9. `uv run pytest` 通过新增测试。

## 五、Todo List（实施跟踪）

- [ ] 增加 `sam3WeightPath` 配置与设置页文件选择卡。
- [ ] Seedling 页重构为 TopTab 并接入状态机。
- [ ] MapCanvas 实现预览框 overlay 与 `+/-` 快捷键。
- [ ] MapCanvas 实现点图层命中、拖拽、删除接口。
- [ ] 新建 `src/utils/seedling_sam3.py`。
- [ ] 新建 `src/utils/seedling_slice.py`。
- [ ] 新建 `src/utils/seedling_points.py`。
- [ ] 新建 `src/utils/seedling_io.py`（pandas + pyshp）。
- [ ] 新建 `src/utils/seedling_cache.py`（pth + PDF）。
- [ ] 新建 `src/gui/tabs/seedling_worker.py`（QThread）。
- [ ] 接通保存/读取中间结果按钮流程。
- [ ] 接通 `bbox.shp`/`mask.shp` 输出。
- [ ] 补充 i18n 文案。
- [ ] 添加并通过 `uv run pytest` 的新增测试。

接下来 Todo List（建议执行顺序）
1. 完成 MapCanvas 点结果 CRUD 可视化与命中编辑（add/move/delete/undo）  
2. 实现 seedling_worker.py（QThread）并接通全图切块推理进度  
3. 接入 SAM3 text prompt + 切块推理主流程（调用 src/utils/seedling_sam3.py / src/utils/seedling_slice.py）  
4. 完成中间结果目录读写：results.pth + preview.pdf  
5. 完成最终产物导出：bbox.shp + mask.shp + 点 fid shp  
6. 补一轮端到端验证（DOM -> 预览 -> 全图 -> 缓存回读 -> shp/pdf）