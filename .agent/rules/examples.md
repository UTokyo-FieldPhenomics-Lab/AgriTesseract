---
trigger: always_on
---

1. SAM3 源码: 将 SAM3 源码放入 lib/sam3/ 目录，避免官方 pip 安装导致的 numpy 版本冲突。模型权重文件由用户自行准备。q
2. 在别的项目中实现了相关的功能，位于/dev.notes/文件夹下
  * Tab1 小样地生成: qgis_subplot_plugin/fieldShape.py (QGIS的插件)
  * Tab2 SAM3 推理: sam3_slice/inference_slice.py (仅提供滑动窗口切块，未实现点和box标注以及视频帧追踪功能，sam3的识别功能以这个为准)
  * Tab3 垄聚类: seedling_pos/14_order_by_ridge.py（命令行交互）
  * Tab4 时间切块: seedling_pos/21_slice_time.ipynb （只有切一个的示例，没有批处理）
  * GeoTiff查看器: 02_demo_load_big_geotiff.py
  * 图层管理: 04_demo_layer_manage_drag.py
  * 旋转功能: 06_demo_layer_rotation.py
3. PySide6-Fluent-Widgets的官方案例，位于/dev.notes/fluentwidget_example中，特别的，gallery/app/view中，有大量demo的示例