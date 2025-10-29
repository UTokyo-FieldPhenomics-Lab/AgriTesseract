import sys
import pyqtgraph as pg
from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np

# 确保在 Qt Application 实例化之前设置这些选项
# 使用抗锯齿，使旋转的线条和文字看起来更平滑
pg.setConfigOption('antialias', True)
# 设置浅色背景和深色前景
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class GlobalRotationDemo(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQtGraph 全局旋转 Demo')
        self.setGeometry(100, 100, 800, 700)
        
        # --- 1. 创建主布局 ---
        self.main_layout = QtWidgets.QVBoxLayout(self)
        
        # --- 2. 创建 PlotWidget ---
        self.pw = pg.PlotWidget()
        
        # !!! 关键：设置旋转的锚点为视图中心
        # 否则，它将围绕 (0,0) 点（左上角）旋转
        self.pw.setTransformationAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.pw.setResizeAnchor(QtWidgets.QGraphicsView.ViewportAnchor.AnchorViewCenter)
        
        self.main_layout.addWidget(self.pw)
        
        # --- 3. 添加绘图内容 ---
        self.add_plot_items()
        
        # --- 4. 创建控制面板 ---
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_widget)
        
        control_layout.addWidget(QtWidgets.QLabel("全局旋转角度:"))
        
        # QDoubleSpinBox 完美符合您的所有要求：
        # - 显示当前角度
        # - 允许直接输入（按 Enter 或失去焦点时生效）
        # - 自带上下调整按钮
        self.angle_spinbox = QtWidgets.QDoubleSpinBox()
        self.angle_spinbox.setRange(-360.0, 360.0) # 允许旋转范围
        self.angle_spinbox.setValue(0.0)           # 默认初始 0.0°
        self.angle_spinbox.setSingleStep(1.0)      # 步长为 1°
        self.angle_spinbox.setSuffix(" °")         # 单位
        self.angle_spinbox.setKeyboardTracking(False) # 仅在按 Enter 或失去焦点时应用
        
        control_layout.addWidget(self.angle_spinbox)
        control_layout.addStretch() # 推动控件到左侧
        
        self.main_layout.addWidget(control_widget)
        
        # --- 5. 连接信号 ---
        self.angle_spinbox.valueChanged.connect(self.apply_rotation)
        
        # --- 6. 应用初始旋转 (0.0°) ---
        self.apply_rotation()

    def add_plot_items(self):
        # --- a. 添加随机 Raster 图层 ---
        # 生成一些有结构的随机数据
        img_data = np.random.normal(size=(200, 100))
        img_data[20:80, 20:80] += 3.0 # 添加一个方块
        img_data = pg.gaussianFilter(img_data, (5, 5)) # 应用高斯模糊
        
        self.raster_item = pg.ImageItem(img_data)
        # 设置图像在坐标系中的位置和大小
        self.raster_item.setRect(QtCore.QRectF(0, 0, 100, 50))
        self.pw.addItem(self.raster_item)
        
        # --- b. 添加随机 Point 图层 ---
        n = 100
        x = np.random.uniform(0, 100, n)
        y = np.random.uniform(0, 50, n)
        sizes = np.random.uniform(5, 15, n)
        brushes = [pg.mkBrush(r, g, b, 150) for r, g, b in np.random.randint(0, 255, (n, 3))]
        
        self.points_item = pg.ScatterPlotItem(x, y, size=sizes, brush=brushes, pen=None)
        self.pw.addItem(self.points_item)
        
        # 设置初始视图范围
        self.pw.setRange(xRange=(-20, 120), yRange=(-20, 70))
        # 启用自动缩放，但保持长宽比
        self.pw.getViewBox().setAspectLocked(True)

    def apply_rotation(self):
        """
        获取 SpinBox 的值并将其应用为 PlotWidget 的变换
        """
        angle = self.angle_spinbox.value()
        
        # 创建一个新的 2D 变换矩阵
        transform = QtGui.QTransform()
        
        # 应用旋转（以度为单位）
        transform.rotate(angle)
        
        # 将此变换设置给 QGraphicsView (PlotWidget)
        self.pw.setTransform(transform)


if __name__ == '__main__':
    # 1. 创建 QApplication
    app = QtWidgets.QApplication(sys.argv)
    
    # 2. 创建并显示窗口
    demo = GlobalRotationDemo()
    demo.show()
    
    # 3. 运行事件循环
    sys.exit(app.exec())