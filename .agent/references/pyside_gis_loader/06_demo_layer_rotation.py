import sys
import pyqtgraph as pg
from PySide6 import QtGui, QtCore, QtWidgets
import numpy as np
from loguru import logger

pg.setConfigOption('antialias', True)
pg.setConfigOption('background', 'w')
pg.setConfigOption('foreground', 'k')


class CustomRotatingViewBox(pg.ViewBox):
    """
    一个自定义的 ViewBox。
    增加了 sigClicked 信号，以便在非 PanMode 下处理点击事件。
    """
    
    sigClicked = QtCore.Signal(object) 
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setMouseMode(pg.ViewBox.PanMode) 

    def set_rotation(self, angle):
        pass

    def mouseDragEvent(self, ev):
        if self.state['mouseMode'] == pg.ViewBox.PanMode:
            ev.accept()
            p_now = self.mapToView(ev.pos())
            p_last = self.mapToView(ev.lastPos())
            map_delta = p_now - p_last
            if map_delta == QtCore.QPointF(0, 0):
                return
            current_rect = self.viewRect()
            new_center = current_rect.center() - map_delta
            current_rect.moveCenter(new_center)
            self.setRange(current_rect, padding=0)
        else:
            ev.ignore()
            super().mouseDragEvent(ev)

    def mouseClickEvent(self, ev):
        """
        覆盖 mouseClickEvent，无论当前模式如何，
        都发出 sigClicked 信号。
        """
        if ev.button() == QtCore.Qt.MouseButton.LeftButton:
            self.sigClicked.emit(ev)
            ev.accept()
        else:
            super().mouseClickEvent(ev)


class BoundlessRotationDemo(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQtGraph - QGIS 逻辑与像素高亮 Demo')
        self.setGeometry(100, 100, 800, 800)
        
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
        
        # --- 5. 创建像素高亮矩形框 ---
        self.pixel_highlighter = QtWidgets.QGraphicsRectItem()
        self.pixel_highlighter.setPen(pg.mkPen(None))
        self.pixel_highlighter.setBrush(pg.mkBrush(255, 0, 0, 100))
        
        self.item_group.addItem(self.pixel_highlighter)
        self.pixel_highlighter.hide()
        self.pixel_highlighter.setZValue(100) 

        
        # --- 6. 创建控制面板 (旋转角度) ---
        rotation_widget = QtWidgets.QWidget()
        rotation_layout = QtWidgets.QHBoxLayout(rotation_widget)
        rotation_layout.addWidget(QtWidgets.QLabel("Item 旋转角度:"))
        self.angle_spinbox = QtWidgets.QDoubleSpinBox()
        self.angle_spinbox.setRange(-360.0, 360.0)
        self.angle_spinbox.setValue(0.0)
        self.angle_spinbox.setSingleStep(1.0)
        self.angle_spinbox.setSuffix(" °")
        self.angle_spinbox.setKeyboardTracking(False) 
        rotation_layout.addWidget(self.angle_spinbox)
        rotation_layout.addStretch()
        self.main_layout.addWidget(rotation_widget)
        
        # --- 7. 创建工具栏 (模式切换) ---
        toolbar = QtWidgets.QWidget()
        toolbar_layout = QtWidgets.QHBoxLayout(toolbar)
        toolbar_layout.setContentsMargins(0, 0, 0, 0)

        self.btn_pan = QtWidgets.QToolButton()
        self.btn_pan.setText("正常查看模式")
        self.btn_pan.setCheckable(True)

        self.btn_pick = QtWidgets.QToolButton()
        self.btn_pick.setText("选点模式")
        self.btn_pick.setCheckable(True)

        self.mode_button_group = QtWidgets.QButtonGroup(self)
        self.mode_button_group.addButton(self.btn_pan)
        self.mode_button_group.addButton(self.btn_pick)

        toolbar_layout.addWidget(self.btn_pan)
        toolbar_layout.addWidget(self.btn_pick)
        toolbar_layout.addStretch()
        self.main_layout.addWidget(toolbar)
        
        # --- 8. 连接信号 ---
        self.angle_spinbox.valueChanged.connect(self.apply_rotation_to_items)
        self.btn_pan.toggled.connect(self.on_mode_changed)
        self.btn_pick.toggled.connect(self.on_mode_changed)
        self.view_box.sigClicked.connect(self.on_canvas_clicked)
        
        # --- 9. 设置初始状态 ---
        self.apply_rotation_to_items()
        self.btn_pan.setChecked(True)
        self.on_mode_changed() 

    def add_plot_items(self):
        # --- a. Raster ---
        img_data = np.random.normal(size=(200, 100))
        img_data[20:80, 20:80] += 3.0
        img_data = pg.gaussianFilter(img_data, (5, 5))
        
        self.image_data = img_data 
        self.raster_item = pg.ImageItem(self.image_data)
        
        self.raster_item.setRect(QtCore.QRectF(0, 0, 100, 50))
        self.item_group.addItem(self.raster_item)

        self.raster_item.setZValue(0) 
        
        # --- b. Points (被注释掉了，没问题) ---
        # ...
        
        # ======================================================
        # ### 修复 1：恢复 setRange 和 setAspectLocked ###
        # ======================================================
        # 这将修复视觉失真
        self.view_box.setRange(xRange=(-20, 120), yRange=(-20, 70)) 
        self.view_box.setAspectLocked(True)
        # ======================================================

    def apply_rotation_to_items(self):
        angle = self.angle_spinbox.value()
        self.item_group.setRotation(-angle)

    def on_mode_changed(self):
        """
        当工具栏按钮被点击时调用，用于切换模式。
        """
        if self.btn_pan.isChecked():
            self.view_box.setMouseMode(pg.ViewBox.PanMode)
            self.pw.setCursor(QtCore.Qt.CursorShape.OpenHandCursor)
            self.pixel_highlighter.hide()
            
        elif self.btn_pick.isChecked():
            self.view_box.setMouseMode(pg.ViewBox.RectMode)
            self.pw.setCursor(QtCore.Qt.CursorShape.CrossCursor)

    def on_canvas_clicked(self, ev):
        """
        当 ViewBox 被点击时调用 (由 sigClicked 信号触发)
        """
        if not self.btn_pick.isChecked():
            return 

        # --- 坐标转换链 ---
        p_view = self.view_box.mapToView(ev.pos())
        p_item_world = self.item_group.mapFromParent(p_view)
        p_raster_local = self.raster_item.mapFromParent(p_item_world)
        
        # ======================================================
        # ### 修复 2：恢复使用 dataTransform() ###
        # 这是从像素索引 -> 局部坐标的正确变换
        # ======================================================
        img_transform = self.raster_item.dataTransform()
        inv_transform, invertible = img_transform.inverted()
        # ======================================================

        if not invertible:
            logger.warning("变换不可逆")
            self.pixel_highlighter.hide()
            return

        p_pixel_index = inv_transform.map(p_raster_local)
        
        row = int(np.floor(p_pixel_index.y()))
        col = int(np.floor(p_pixel_index.x()))
        
        value_str = "图像边界之外"
        
        if (0 <= row < self.image_data.shape[0]) and (0 <= col < self.image_data.shape[1]):
            # --- 提取值 ---
            value = self.image_data[row, col]
            value_str = f"{value:.4f}"
            
            # --- 更新高亮框 ---
            p_top_left_pixel = QtCore.QPointF(col, row)
            p_bottom_right_pixel = QtCore.QPointF(col + 1, row + 1)
            
            p_top_left_local = img_transform.map(p_top_left_pixel)
            p_bottom_right_local = img_transform.map(p_bottom_right_pixel)
            
            pixel_rect_local = QtCore.QRectF(p_top_left_local, p_bottom_right_local)
            
            # 将局部矩形映射到父级（ItemGroup）坐标系
            pixel_rect_world = self.raster_item.mapRectToParent(pixel_rect_local)
            
            self.pixel_highlighter.setRect(pixel_rect_world)
            self.pixel_highlighter.show()
            
        else:
            self.pixel_highlighter.hide()

        
        # --- 显示信息框 ---
        info_text = f"""
<b>📍 点信息</b><br>
--------------------------<br>
<b>世界坐标 (X, Y):</b><br>
({p_item_world.x():.2f}, {p_item_world.y():.2f})<br>
<br>
<b>光栅像素 (Col, Row):</b><br>
({col}, {row})<br>
<br>
<b>像素值:</b><br>
{value_str}
"""
        logger.debug(info_text)
        QtWidgets.QMessageBox.information(self, "点信息", info_text)


if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    demo = BoundlessRotationDemo()
    demo.show()
    sys.exit(app.exec())