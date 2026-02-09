import sys
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QLabel,
    QListWidgetItem
)
from PySide6.QtCore import QRectF, Qt

# 确保 pyqtgraph 在 PySide6 模式下运行
pg.setConfigOption('leftButtonPan', False) # 可选：禁用左键平移，以便进行框选

class LayerManagerDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo 3 - PyQtGraph 图层管理器")
        self.setGeometry(150, 150, 1000, 700)

        # --- 核心数据结构 ---
        # self.layer_registry 
        # 键 (Key) = 图层名称 (str)
        # 值 (Value) = PyQtGraph 的 GraphicsItem 对象
        self.layer_registry = {}
        
        # 用于生成唯一图层名称的计数器
        self.layer_counter = 0

        # --- 主布局 ---
        central_widget = QWidget()
        main_layout = QHBoxLayout(central_widget) # 水平布局
        self.setCentralWidget(central_widget)

        # 1. 左侧：控制面板
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)
        control_panel.setMaximumWidth(250) # 限制控制面板宽度

        # 2. 右侧：PyQtGraph 绘图区
        self.plot_widget = pg.PlotWidget()
        self.setup_plot()

        # --- 填充控制面板 ---
        
        # "添加" 按钮
        control_layout.addWidget(QLabel("添加新图层:"))
        btn_add_points = QPushButton("添加随机点 (Points)")
        btn_add_image = QPushButton("添加随机图像 (Image)")
        btn_add_line = QPushButton("添加随机线条 (Line)")
        
        control_layout.addWidget(btn_add_points)
        control_layout.addWidget(btn_add_image)
        control_layout.addWidget(btn_add_line)
        
        # 图层列表
        control_layout.addWidget(QLabel("图层列表:"))
        self.layer_list_widget = QListWidget()
        control_layout.addWidget(self.layer_list_widget)

        # "管理" 按钮
        control_layout.addWidget(QLabel("管理选中图层:"))
        self.toggle_button = QPushButton("切换可见性 (Show/Hide)")
        self.delete_button = QPushButton("删除图层 (Delete)")
        
        # 默认禁用，直到有图层被选中
        self.toggle_button.setEnabled(False)
        self.delete_button.setEnabled(False)
        
        control_layout.addWidget(self.toggle_button)
        control_layout.addWidget(self.delete_button)
        
        # 将控制面板和绘图区添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.plot_widget)
        
        # --- 信号连接 ---
        btn_add_points.clicked.connect(self.add_points_layer)
        btn_add_image.clicked.connect(self.add_image_layer)
        btn_add_line.clicked.connect(self.add_line_layer)
        
        # 当在 QListWidget 中选择的项目变化时
        self.layer_list_widget.currentItemChanged.connect(self.on_layer_selected)
        
        # 管理按钮
        self.toggle_button.clicked.connect(self.toggle_layer_visibility)
        self.delete_button.clicked.connect(self.delete_layer)

    def setup_plot(self):
        """初始化 PlotWidget"""
        self.plot_widget.setBackground('w') # 白色背景
        self.plot_widget.setAspectLocked(True) # 锁定长宽比
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Y 坐标')
        self.plot_widget.setLabel('bottom', 'X 坐标')
        # 设置一个初始的可见范围
        self.plot_widget.setRange(xRange=[0, 100], yRange=[0, 100])

    # --- 图层添加方法 ---

    def add_points_layer(self):
        """添加一个随机散点图层"""
        x = np.random.rand(50) * 100
        y = np.random.rand(50) * 100
        # 随机选择颜色
        color = np.random.choice(['r', 'g', 'b', 'c', 'm', 'y'])
        
        item = pg.ScatterPlotItem(
            x=x, y=y, 
            pen=None, 
            brush=pg.mkBrush(color), 
            size=8
        )
        item.setZValue(10) # Z值设为10 (在顶层)
        
        layer_name = f"Points Layer {self.layer_counter}"
        self.register_layer(item, layer_name)

    def add_image_layer(self):
        """添加一个随机图像图层"""
        # 生成一个 50x50 的随机噪声图像
        img_data = np.random.normal(size=(50, 50))
        
        item = pg.ImageItem(img_data)
        item.setZValue(-100) # Z值设为-100 (在最底层)
        
        # 随机放置在 (0, 100) 范围内
        x = np.random.rand() * 50
        y = np.random.rand() * 50
        width = 50
        height = 50
        item.setRect(QRectF(x, y, width, height))
        
        # 为其应用一个颜色查找表 (colormap)
        item.setLookupTable(pg.colormap.get('viridis').getLookupTable())
        
        layer_name = f"Image Layer {self.layer_counter}"
        self.register_layer(item, layer_name)

    def add_line_layer(self):
        """添加一个随机线条图层"""
        x_data = np.linspace(0, 100, 20) # 0到100
        y_data = np.random.rand(20) * 100 # 随机 Y
        color = np.random.choice(['r', 'g', 'b', 'c', 'm', 'y'])

        item = pg.PlotDataItem(x=x_data, y=y_data, pen=pg.mkPen(color, width=2))
        item.setZValue(5) # Z值设为5 (在点和图像之间)
        
        layer_name = f"Line Layer {self.layer_counter}"
        self.register_layer(item, layer_name)

    # --- 核心管理逻辑 ---

    def register_layer(self, item: pg.GraphicsObject, name: str):
        """
        核心函数：将一个新图层注册到系统
        """
        self.layer_counter += 1
        
        # 1. 添加到 PlotWidget (使其可见)
        self.plot_widget.addItem(item)
        
        # 2. 添加到 Python 字典 (用于逻辑跟踪)
        self.layer_registry[name] = item
        
        # 3. 添加到 UI 列表 (QListWidget)
        list_item = QListWidgetItem(name)
        self.layer_list_widget.addItem(list_item)
        
        # 4. 自动选中新添加的图层
        self.layer_list_widget.setCurrentItem(list_item)
        print(f"图层已注册: {name}")

    def on_layer_selected(self, current_item: QListWidgetItem, previous_item: QListWidgetItem):
        """当 QListWidget 中的选择变化时触发"""
        if current_item:
            self.toggle_button.setEnabled(True)
            self.delete_button.setEnabled(True)
        else:
            self.toggle_button.setEnabled(False)
            self.delete_button.setEnabled(False)

    def toggle_layer_visibility(self):
        """切换选中图层的可见性"""
        current_item_widget = self.layer_list_widget.currentItem()
        if not current_item_widget:
            return
        
        # QListWidget 中的文本可能带有 [Hidden] 标记
        layer_name_text = current_item_widget.text()
        # 基础名称是我们在字典中的 Key
        base_name = layer_name_text.replace(" [Hidden]", "")
        
        item = self.layer_registry.get(base_name)
        if not item:
            print(f"错误: 在注册表中找不到 {base_name}")
            return

        if item.isVisible():
            item.hide()
            current_item_widget.setText(f"{base_name} [Hidden]")
            current_item_widget.setForeground(Qt.gray) # 设置为灰色
        else:
            item.show()
            current_item_widget.setText(base_name)
            current_item_widget.setForeground(Qt.black) # 恢复为黑色

    def delete_layer(self):
        """删除选中的图层"""
        current_item_widget = self.layer_list_widget.currentItem()
        if not current_item_widget:
            return

        # 1. 从 QListWidget 中获取当前行号
        current_row = self.layer_list_widget.row(current_item_widget)
        
        # 2. 从 QListWidget 中移除
        list_item = self.layer_list_widget.takeItem(current_row)
        
        layer_name_text = list_item.text()
        base_name = layer_name_text.replace(" [Hidden]", "")
        
        # 3. 从注册表 (dict) 中查找并移除
        if base_name in self.layer_registry:
            item = self.layer_registry[base_name]
            
            # 4. 从 PlotWidget 中移除
            self.plot_widget.removeItem(item)
            
            # 5. 从字典中删除
            del self.layer_registry[base_name]
            print(f"图层已删除: {base_name}")
        else:
            print(f"错误: 尝试删除一个不存在的图层 {base_name}")


# --- 程序入口 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LayerManagerDemo()
    window.show()
    sys.exit(app.exec())