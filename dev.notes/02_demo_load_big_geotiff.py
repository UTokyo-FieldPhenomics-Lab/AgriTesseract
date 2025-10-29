import sys
import rasterio
import rasterio.enums
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QWidget,
    QPushButton,
    QFileDialog,
    QMessageBox
)
from PySide6.QtCore import QTimer, QRectF

from loguru import logger

class LargeTiffViewer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 + PyQtGraph - 大型GeoTIFF查看器")
        self.setGeometry(100, 100, 900, 700)

        # 核心组件
        self.load_button = QPushButton("加载大型 GeoTIFF")
        self.plot_widget = pg.PlotWidget()
        self.image_item = pg.ImageItem() # 我们将动态更新这个 Item

        # --- 布局 ---
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.load_button)
        layout.addWidget(self.plot_widget)
        self.setCentralWidget(central_widget)

        # --- 内部状态 ---
        self.dataset = None  # 用于保存 rasterio 的文件句柄
        
        # 关键: 用于"防抖"的QTimer
        # 防止在平移时触发100次更新，只在用户停止操作150ms后更新
        self.update_timer = QTimer()
        self.update_timer.setSingleShot(True)
        self.update_timer.setInterval(150) # 150毫秒延迟
        self.update_timer.timeout.connect(self.update_image_display)

        # --- 初始化 Plot ---
        self.setup_plot()

        # --- 信号连接 ---
        self.load_button.clicked.connect(self.load_file)
        # 关键: 连接视图变化信号到我们的"防抖"计时器
        self.plot_widget.sigRangeChanged.connect(self.on_view_changed)

    def setup_plot(self):
        self.plot_widget.setBackground('w')
        self.plot_widget.setLabel('left', 'Y 坐标')
        self.plot_widget.setLabel('bottom', 'X 坐标')
        self.plot_widget.setAspectLocked(True) # 锁定长宽比，对地图至关重要
        self.plot_widget.addItem(self.image_item)

    def load_file(self):
        """
        打开文件对话框并"打开"GeoTIFF (不读取数据)
        """
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择一个 GeoTIFF 文件",
            "",
            "GeoTIFF (*.tif *.tiff)"
        )

        if not filepath:
            return

        try:
            # 如果已打开一个文件，先关闭它
            if self.dataset:
                self.dataset.close()

            # 1. "打开" 文件，这只读取元数据，不读取像素数据
            self.dataset = rasterio.open(filepath)
            logger.info(f"=> loading geotiff: {filepath}")
            
            # 2. 获取地理边界
            bounds = self.dataset.bounds

            # 3. [修正] 手动计算宽度和高度
            width = bounds.right - bounds.left
            height = bounds.top - bounds.bottom

            logger.debug(f"   geotiff bounds info: {bounds} | top: {bounds.top} | left: {bounds.left} | width: {width} | height: {height} ")

            # 4. 设置 ImageItem 的地理位置
            # QRectF(left, top, width, height)
            # 在 PyQtGraph 的 Y-Up 坐标系中, (left, bottom) 是左下角
            self.image_rect = QRectF(
                bounds.left, 
                bounds.bottom, 
                width, 
                height
            )
            # self.image_item.setRect(self.image_rect) # 暂时不设置，在update中设置

            # 4. 立即将视图缩放到图像的完整范围
            logger.debug(f"set view to image bounds: {self.image_rect}")
            self.plot_widget.setRange(self.image_rect)
            
            # 5. 手动触发第一次图像加载
            self.update_image_display()

        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"无法打开 GeoTIFF 文件:\n{str(e)}")
            self.dataset = None

    def on_view_changed(self):
        """
        当视图(平移/缩放)发生变化时，这个函数会被*频繁*调用。
        我们不在这里做实际工作，而是(重新)启动计时器。
        """
        self.update_timer.start()

    def update_image_display(self):
        """
        这是实际的 I/O 工作函数。只在用户停止操作 150ms 后执行。
        """
        logger.info(":: update image display activated")
        if not self.dataset:
            return

        # 1. 获取 PyQtGraph 当前可见的矩形区域 (地理坐标)
        logger.info(f"=> get visiable rect")
        view_rect = self.plot_widget.getViewBox().viewRect()

        geo_left = view_rect.left()
        geo_right = view_rect.right()
        geo_top = view_rect.top()
        geo_bottom = view_rect.bottom()

        geo_width = geo_right - geo_left
        geo_height = geo_top - geo_bottom
        
        img_rect = QRectF(
            geo_left, 
            geo_bottom, 
            geo_width, 
            geo_height
        )

        logger.debug(f"   view_rect: {view_rect} | geo_left: {geo_left} | geo_right: {geo_right} | geo_top: {geo_top} | geo_bottom: {geo_bottom}")

        try:
            # 2. 将地理坐标转换为 rasterio 的 "窗口" (像素坐标)
            logger.debug(f"   set geo_coord to rasterio window pixel_coord: left={geo_left}, bottom={geo_bottom}, right={geo_right}, top={geo_top}")
            # (left, top, right, bottom)
            window = self.dataset.window(geo_left, geo_top, geo_right, geo_bottom)
        except rasterio.errors.WindowError:
            # 如果视图完全在图像之外，清空图像
            logger.warning("   viewport outside image bounds, clear image")
            self.image_item.clear()
            return
            
        # 3. 确定降采样的目标分辨率
        # 我们不希望读取比屏幕像素更多的像素
        # 获取视图框的像素大小
        view_px_width = int(self.plot_widget.getViewBox().width())
        view_px_height = int(self.plot_widget.getViewBox().height())

        logger.info(f"=> Decide the downsample pixels to height={view_px_height}, width={view_px_width} -> target_shape")
        target_shape = (view_px_height, view_px_width)

        if view_px_width <= 0 or view_px_height <= 0:
            logger.warning("   viewport too small, clear image not load")
            return # 视图太小，不加载

        # 确保目标形状至少是 (1, 1)
        target_shape = (max(1, target_shape[0]), max(1, target_shape[1]))
        logger.debug(f"   corrected target shape: {target_shape}")

        # 4. [核心] 从磁盘读取数据
        # - indexes: 读取哪些波段 (这里我们假定RGB)
        # - window: 只读取这个窗口
        # - out_shape: 立即降采样到这个形状
        # - resampling: 降采样算法
        logger.info("=> Loading data from geotiff")
        
        # 选择波段 (RGB 或 灰度)
        if self.dataset.count >= 3:
            indexes = (1, 2, 3) # 读取 R, G, B
        else:
            indexes = 1 # 读取单波段
            
        try:
            logger.debug(f"   reading geotiff with indexes: {indexes} | window: {window}, out_shape: {target_shape}")
            data = self.dataset.read(
                indexes=indexes,
                window=window,
                out_shape=target_shape,
                resampling=rasterio.enums.Resampling.bilinear,
                boundless=True # Allow reading beyond file boundaries
            )
            logger.debug(f"   obtained data with shape{data.shape} and with value range ({data.min()}, {data.max()})")
        except Exception as e:
            logger.error(f"Rasterio 读取错误: {e}")
            return

        # 5. 格式化数据以供 PyQtGraph 显示
        logger.info("=> Transposing data for PyQtGraph display")
        if data.ndim == 3:
            # rasterio 读取为 (bands, height, width)
            # pyqtgraph 需要 (height, width) 或 (height, width, bands)
            # (B, H, W) -> (H, W, B)
            data = data.transpose((1, 2, 0))
            logger.debug(f"   transposed data to shape{data.shape} and with value range ({data.min()}, {data.max()})")
            

        # 6. 更新 ImageItem
        logger.info("=> Updating ImageItem")
        
        # 首先清除旧图像，防止在数据类型更改时出错
        self.image_item.clear()
        self.image_item.setImage(data)

        # 7. [重要 - 修正] 设置新加载图像的地理边界
        # 我们必须告诉 ImageItem，这个 (可能很小的) NumPy 数组
        # 对应于磁盘上的哪个地理矩形。
        logger.info("=> Updating image rect")
        win_bounds = self.dataset.window_bounds(window)
        logger.debug(f"   window_bounds: {win_bounds} with type: {type(win_bounds)}")
        
       # [修正] 手动计算宽度和高度 (使用索引访问)
        # win_bounds 是 (left, top, right, bottom)
        # geo_left = win_bounds[0]
        # geo_top = win_bounds[1]
        # geo_right = win_bounds[2]
        # geo_bottom = win_bounds[3]

        # win_width = geo_right - geo_left
        # win_height = geo_top - geo_bottom
        
        # img_rect = QRectF(
        #     geo_left, 
        #     geo_bottom, 
        #     win_width, 
        #     win_height
        # )

        self.image_item.setRect(img_rect)

    def closeEvent(self, event):
        """
        在关闭窗口时，确保释放文件句柄
        """
        if self.dataset:
            self.dataset.close()
        super().closeEvent(event)


# --- 程序入口 ---
if __name__ == "__main__":
    # 启用 PyQtGraph 的图像自动降采样
    pg.setConfigOptions(imageAxisOrder='row-major') # (H, W) 顺序

    app = QApplication(sys.argv)
    window = LargeTiffViewer()
    window.show()
    sys.exit(app.exec())