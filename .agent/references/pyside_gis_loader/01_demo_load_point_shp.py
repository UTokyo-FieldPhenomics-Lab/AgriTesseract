import sys
import geopandas
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
from PySide6.QtCore import Qt

class MapWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PySide6 + PyQtGraph SHP 加载器")
        self.setGeometry(100, 100, 800, 600)

        # --- 核心组件 ---
        
        # 1. PyQtGraph 的绘图控件
        self.plot_widget = pg.PlotWidget()
        
        # 2. “加载”按钮
        self.load_button = QPushButton("加载 Point SHP 文件")
        self.load_button.clicked.connect(self.load_shp_file)

        # --- 布局 ---
        central_widget = QWidget()
        layout = QVBoxLayout(central_widget)
        layout.addWidget(self.load_button)
        layout.addWidget(self.plot_widget) # 绘图控件在下
        
        self.setCentralWidget(central_widget)

        # --- 初始化绘图控件 ---
        self.setup_plot()

    def setup_plot(self):
        # 设置背景为白色（默认为黑色）
        self.plot_widget.setBackground('w')
        
        # 关键：锁定长宽比
        # 这确保了地图不会因为窗口缩放而变形
        self.plot_widget.setAspectLocked(True)

        # 添加网格线，使其看起来更像地图
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Y 坐标 / 纬度')
        self.plot_widget.setLabel('bottom', 'X 坐标 / 经度')

    def load_shp_file(self):
        """
        打开文件对话框并加载 SHP 文件
        """
        # 打开文件对话框，过滤器只显示 .shp 文件
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "选择一个 Point Shapefile",
            "",  # 默认目录
            "Shapefiles (*.shp)"
        )

        # 如果用户取消了选择，则 filepath 为空
        if not filepath:
            return

        # 调用绘图函数
        self.plot_shp(filepath)

    def plot_shp(self, filepath):
        """
        使用 GeoPandas 读取 SHP 并在 PyQtGraph 上绘图
        """
        try:
            # 1. 使用 GeoPandas 读取文件
            gdf = geopandas.read_file(filepath)

            # 2. 检查是否为 Point 类型
            if gdf.geom_type.empty or not (gdf.geom_type == 'Point').all():
                QMessageBox.warning(self, "加载失败", "该文件不是纯粹的 Point SHP 文件。")
                return

            # 3. 提取 X 和 Y 坐标
            # GeoPandas 提供了 .x 和 .y 属性来直接访问 Point 的坐标
            x_coords = gdf.geometry.x
            y_coords = gdf.geometry.y

            # 4. 在 PyQtGraph 中绘图
            
            # 首先清除之前的绘图内容
            self.plot_widget.clear()

            # 创建一个散点图项 (ScatterPlotItem)
            # 我们使用红色(r)的圆圈(o)
            scatter = pg.ScatterPlotItem(
                x=x_coords,
                y=y_coords,
                pen=None,  # 不绘制边框
                brush=pg.mkBrush(color='r', width=0), # 填充红色
                size=5,    # 点的大小
            )
            
            # 将散点图添加到绘图控件中
            self.plot_widget.addItem(scatter)
            
            # (可选) 自动缩放到数据显示的范围
            self.plot_widget.autoRange()

        except Exception as e:
            QMessageBox.critical(self, "加载错误", f"加载或解析SHP文件时出错:\n{str(e)}")


# --- 程序入口 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MapWindow()
    window.show()
    sys.exit(app.exec())