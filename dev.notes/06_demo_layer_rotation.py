import sys
import pyqtgraph as pg
from PySide6 import QtWidgets, QtCore, QtGui
import numpy as np

pg.setConfigOption('antialias', True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class CustomRotatingViewBox(pg.ViewBox):
    """
    一个自定义的 ViewBox，它知道当前的旋转角度，
    并重写 mouseDragEvent 以正确处理平移。
    
    此版本使用 QGIS 逻辑（最终修正版）：
    1. 计算鼠标拖动对应的 *未旋转* 的数据向量 (map_delta)
    2. 更新视图中心点：new_center = old_center - map_delta
    3. ItemGroup 负责处理旋转渲染
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 注意：我们不再需要 self.current_angle
        # self.current_angle = 0.0 
        self.setMouseMode(pg.ViewBox.PanMode) 

    def set_rotation(self, angle):
        # ViewBox 不再需要知道旋转角度
        pass

    def mouseDragEvent(self, ev):
        if self.state['mouseMode'] == pg.ViewBox.PanMode:
            ev.accept()
            
            # 1. 计算鼠标在数据坐标系中的等效移动向量 (未旋转)
            #    mapToView 会处理 Y 轴反转
            p_now = self.mapToView(ev.pos())
            p_last = self.mapToView(ev.lastPos())
            
            map_delta = p_now - p_last
            
            if map_delta == QtCore.QPointF(0, 0):
                return

            # ======================================================
            # ### 关键修复：应用 QGIS 逻辑 (最终版) ###
            # ======================================================
            
            # 1. 获取当前的视图矩形 (ViewBox 的状态)
            current_rect = self.viewRect()
            
            # 2. 计算新的中心点
            #    我们使用 "old_center - map_delta" 来实现“自然拖动”
            new_center = current_rect.center() - map_delta
            
            # 3. 将视图矩形移动到新的中心
            current_rect.moveCenter(new_center)
            
            # 4. 将 ViewBox 设置为这个新的矩形状态
            self.setRange(current_rect, padding=0)

            # ======================================================
            # ### 修复结束 ###
            # ======================================================
        
        else:
            super().mouseDragEvent(ev)


class BoundlessRotationDemo(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQtGraph 真正无界旋转 (QGIS 逻辑) Demo')
        self.setGeometry(100, 100, 800, 700)
        
        # --- 1. 创建自定义 ViewBox 和 PlotWidget ---
        self.view_box = CustomRotatingViewBox()
        self.pw = pg.PlotWidget(viewBox=self.view_box)
        
        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.pw)

        # --- 2. 配置 PlotItem 和 ViewBox ---
        plot_item = self.pw.getPlotItem()
        plot_item.hideAxis('left')
        plot_item.hideAxis('bottom')
        plot_item.hideButtons()
        
        plot_item.setClipToView(False) 

        self.view_box.setContentsMargins(0, 0, 0, 0)
        self.view_box.setBorder(None)
        
        # --- 3. 创建一个 ItemGroup 来容纳所有
        self.item_group = pg.ItemGroup()
        self.view_box.addItem(self.item_group)
        
        self.rotation_center = pg.Point(50, 25)
        self.item_group.setTransformOriginPoint(self.rotation_center)

        # --- 4. 添加绘图内容到 ItemGroup ---
        self.add_plot_items()
        
        # --- 5. 创建控制面板 (相同) ---
        control_widget = QtWidgets.QWidget()
        control_layout = QtWidgets.QHBoxLayout(control_widget)
        control_layout.addWidget(QtWidgets.QLabel("Item 旋转角度:"))
        self.angle_spinbox = QtWidgets.QDoubleSpinBox()
        self.angle_spinbox.setRange(-360.0, 360.0)
        self.angle_spinbox.setValue(0.0)
        self.angle_spinbox.setSingleStep(1.0)
        self.angle_spinbox.setSuffix(" °")
        self.angle_spinbox.setKeyboardTracking(False) 
        control_layout.addWidget(self.angle_spinbox)
        control_layout.addStretch()
        self.main_layout.addWidget(control_widget)
        
        # --- 6. 连接信号 ---
        self.angle_spinbox.valueChanged.connect(self.apply_rotation_to_items)
        
        # --- 7. 应用初始旋转 (0.0°) ---
        self.apply_rotation_to_items()

    def add_plot_items(self):
        # --- a. Raster ---
        img_data = np.random.normal(size=(200, 100))
        img_data[20:80, 20:80] += 3.0
        img_data = pg.gaussianFilter(img_data, (5, 5))
        
        self.raster_item = pg.ImageItem(img_data)
        self.raster_item.setRect(QtCore.QRectF(0, 0, 100, 50))
        self.item_group.addItem(self.raster_item)
        
        # --- b. Points ---
        n = 100
        x = np.random.uniform(0, 100, n)
        y = np.random.uniform(0, 50, n)
        sizes = np.random.uniform(5, 15, n)
        brushes = [pg.mkBrush(r, g, b, 150) for r, g, b in np.random.randint(0, 255, (n, 3))]
        
        self.points_item = pg.ScatterPlotItem(x, y, size=sizes, brush=brushes, pen=None)
        self.item_group.addItem(self.points_item)
        
        self.view_box.setRange(xRange=(-20, 120), yRange=(-20, 70)) 
        self.view_box.setAspectLocked(True)

    def apply_rotation_to_items(self):
        angle = self.angle_spinbox.value()
        
        # 只旋转 ItemGroup
        # 将传入的角度反转，使其从逆时针变为顺时针
        # PyQtGraph/Qt 默认为逆时针为正
        # QGIS 等通常以顺时针为正
        self.item_group.setRotation(-angle)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    demo = BoundlessRotationDemo()
    demo.show()
    sys.exit(app.exec())