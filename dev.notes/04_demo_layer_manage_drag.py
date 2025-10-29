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
    QTreeWidget,      # <--- 新增
    QTreeWidgetItem,  # <--- 新增
    QMenu,            # <--- 新增
    QDialog,          # <--- 新增
    QLabel,
    QAbstractItemView # <--- 新增
)
from PySide6.QtGui import QAction, QColor # <--- 新增
from PySide6.QtCore import QRectF, Qt, QPoint

# 确保 pyqtgraph 在 PySide6 模式下运行
pg.setConfigOption('leftButtonPan', False) 

# Z-Value 常量
# 我们给不同类型的图层设置一个 "基础" Z 值
# 这样点(Z=100)总是绘制在线(Z=50)之上，图像(Z=0)总是在最下面
# 拖拽排序将在这个基础值之上增加一个小的偏移量
Z_BASE_IMAGE = 0
Z_BASE_LINE = 50
Z_BASE_POINT = 100

class LayerManagerDemo(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Demo 3 (升级版) - QGIS 风格图层管理器")
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
        control_panel.setMaximumWidth(300) # 限制控制面板宽度

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
        
        # [升级] 图层列表
        control_layout.addWidget(QLabel("图层列表 (可拖拽排序):"))
        self.layer_tree_widget = QTreeWidget()
        self.layer_tree_widget.setHeaderLabels(["图层 (Layers)"])
        
        # [特性 1] 启用拖拽
        self.layer_tree_widget.setDragEnabled(True)
        self.layer_tree_widget.setAcceptDrops(True)
        self.layer_tree_widget.setDropIndicatorShown(True)
        # 仅在内部移动
        self.layer_tree_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)

        # [特性 3] 启用右键菜单
        self.layer_tree_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        control_layout.addWidget(self.layer_tree_widget)
        
        # 将控制面板和绘图区添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(self.plot_widget)
        
        # --- 信号连接 ---
        btn_add_points.clicked.connect(self.add_points_layer)
        btn_add_image.clicked.connect(self.add_image_layer)
        btn_add_line.clicked.connect(self.add_line_layer)
        
        # [特性 1] 拖拽完成信号
        # 当拖拽操作完成, QTreeWidget 的 model 会发出 'rowsMoved' 信号
        self.layer_tree_widget.model().rowsMoved.connect(self.update_z_order)

        # [特性 2] Checkbox 状态改变信号
        self.layer_tree_widget.itemChanged.connect(self.handle_item_changed)
        
        # [特性 3] 右键菜单信号
        self.layer_tree_widget.customContextMenuRequested.connect(self.open_context_menu)


    def setup_plot(self):
        """初始化 PlotWidget"""
        self.plot_widget.setBackground('w') 
        self.plot_widget.setAspectLocked(True) 
        self.plot_widget.showGrid(x=True, y=True, alpha=0.3)
        self.plot_widget.setLabel('left', 'Y 坐标')
        self.plot_widget.setLabel('bottom', 'X 坐标')
        self.plot_widget.setRange(xRange=[0, 100], yRange=[0, 100])

    # --- 图层添加方法 ---

    def add_points_layer(self):
        x = np.random.rand(50) * 100
        y = np.random.rand(50) * 100
        color = np.random.choice(['r', 'g', 'b', 'c', 'm', 'y'])
        item = pg.ScatterPlotItem(x=x, y=y, pen=None, brush=pg.mkBrush(color), size=8)
        
        layer_name = f"Points Layer {self.layer_counter}"
        
        # 注册图层，并传入 "z_base"
        self.register_layer(item, layer_name, Z_BASE_POINT)

    def add_image_layer(self):
        img_data = np.random.normal(size=(50, 50))
        item = pg.ImageItem(img_data)
        x, y = np.random.rand(2) * 50
        item.setRect(QRectF(x, y, 50, 50))
        item.setLookupTable(pg.colormap.get('viridis').getLookupTable())
        
        layer_name = f"Image Layer {self.layer_counter}"
        self.register_layer(item, layer_name, Z_BASE_IMAGE)

    def add_line_layer(self):
        x = np.linspace(0, 100, 20) 
        y = np.random.rand(20) * 100
        color = np.random.choice(['r', 'g', 'b', 'c', 'm', 'y'])
        item = pg.PlotDataItem(x=x, y=y, pen=pg.mkPen(color, width=2))
        
        layer_name = f"Line Layer {self.layer_counter}"
        self.register_layer(item, layer_name, Z_BASE_LINE)

    # --- 核心管理逻辑 ---

    def register_layer(self, item: pg.GraphicsObject, name: str, z_base: int):
        """
        核心函数：将一个新图层注册到系统
        """
        self.layer_counter += 1
        
        # 1. 添加到 PlotWidget (使其可见)
        self.plot_widget.addItem(item)
        
        # 2. 添加到 Python 字典 (用于逻辑跟踪)
        # 我们存储一个元组: (pyqtgraph_item, z_base)
        self.layer_registry[name] = (item, z_base)
        
        # --- [升级] UI 列表 (QTreeWidget) ---
        
        # 在操作 QTreeWidget 时暂时阻塞信号
        # 否则 'itemChanged' 会在我们设置 Checkbox 时触发
        self.layer_tree_widget.blockSignals(True)
        
        list_item = QTreeWidgetItem([name])
        
        # [特性 2] 添加 Checkbox 并默认勾选
        list_item.setFlags(list_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        list_item.setCheckState(0, Qt.CheckState.Checked)

        # 新图层总是插在最顶部 (index 0)
        self.layer_tree_widget.insertTopLevelItem(0, list_item)
        
        # 自动选中新添加的图层
        self.layer_tree_widget.setCurrentItem(list_item)
        
        # 恢复信号
        self.layer_tree_widget.blockSignals(False)
        
        print(f"图层已注册: {name}")
        
        # 3. [升级] 注册后，立即更新所有Z值
        self.update_z_order()

    def update_z_order(self):
        """
        [特性 1] 拖拽排序的核心
        遍历 QTreeWidget, 根据其*显示顺序*重新计算 Z 值
        """
        print("--- 正在更新 Z 轴顺序 ---")
        
        # 列表中的总项目数
        count = self.layer_tree_widget.topLevelItemCount()
        
        for i in range(count):
            # 1. 从 QTreeWidget 获取项目
            # i=0 是列表中的*最顶部*
            item_widget = self.layer_tree_widget.topLevelItem(i)
            layer_name = item_widget.text(0)
            
            # 2. 从注册表中获取 pyqt_item
            if layer_name in self.layer_registry:
                pyqt_item, z_base = self.layer_registry[layer_name]
                
                # 3. 计算新的 Z 值
                # 列表顶部的项目 (i=0) 应该有最高的 Z 值
                # 列表底部的项目 (i=count-1) 应该有最低的 Z 值
                # 我们使用 z_base 来确保点总是在线之上
                new_z = z_base + (count - i)
                
                pyqt_item.setZValue(new_z)
                print(f"图层 '{layer_name}' Z-Value 设置为: {new_z}")

    def handle_item_changed(self, item_widget: QTreeWidgetItem, column: int):
        """
        [特性 2] Checkbox 可见性
        当 Checkbox 状态改变时触发
        """
        if column != 0:
            return # 我们只关心第一列
            
        layer_name = item_widget.text(0)
        pyqt_item, _ = self.layer_registry.get(layer_name, (None, 0))
        
        if pyqt_item:
            if item_widget.checkState(0) == Qt.CheckState.Checked:
                pyqt_item.show()
                print(f"图层 '{layer_name}' 已显示")
            else:
                pyqt_item.hide()
                print(f"图层 '{layer_name}' 已隐藏")

    def open_context_menu(self, position: QPoint):
        """
        [特性 3] 右键菜单
        """
        # 1. 获取在 'position' 位置的 Item
        item_widget = self.layer_tree_widget.itemAt(position)
        
        if not item_widget:
            return # 如果右键点击的是空白区域，则不显示菜单

        # 2. 创建菜单
        context_menu = QMenu(self)
        
        # --- 创建 Actions ---
        delete_action = QAction("删除 (Delete Layer)", self)
        props_action = QAction("属性 (Properties)", self)
        
        # --- 连接 Actions ---
        # 我们使用 lambda 来传递 item_widget
        delete_action.triggered.connect(lambda: self.delete_layer(item_widget))
        props_action.triggered.connect(lambda: self.show_properties(item_widget))
        
        # --- 添加到菜单 ---
        context_menu.addAction(delete_action)
        context_menu.addAction(props_action)
        
        # 3. 显示菜单
        # mapToGlobal 将小部件的本地坐标转换为屏幕的全局坐标
        context_menu.exec(self.layer_tree_widget.mapToGlobal(position))

    def delete_layer(self, item_widget: QTreeWidgetItem):
        """
        [特性 3] 删除操作
        """
        layer_name = item_widget.text(0)
        
        if layer_name in self.layer_registry:
            # 1. 从 PlotWidget 中移除
            pyqt_item, _ = self.layer_registry[layer_name]
            self.plot_widget.removeItem(pyqt_item)
            
            # 2. 从注册表 (dict) 中删除
            del self.layer_registry[layer_name]
            
            # 3. 从 QTreeWidget 中移除
            # (获取根并移除其子项)
            root = self.layer_tree_widget.invisibleRootItem()
            root.removeChild(item_widget)
            
            print(f"图层已删除: {layer_name}")
            
            # 4. (可选) 删除后更新 Z 轴
            self.update_z_order()
        
    def show_properties(self, item_widget: QTreeWidgetItem):
        """
        [特性 3] 属性操作 (显示一个空对话框)
        """
        layer_name = item_widget.text(0)
        
        # 创建一个简单的模态对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"'{layer_name}' 的属性")
        dialog.setLayout(QVBoxLayout())
        dialog.layout().addWidget(QLabel(f"这里是 {layer_name} 的属性面板。\n(这是一个占位符)"))
        dialog.setMinimumWidth(300)
        dialog.setMinimumHeight(200)
        
        # .exec() 会阻塞，直到对话框关闭
        dialog.exec()


# --- 程序入口 ---
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LayerManagerDemo()
    window.show()
    sys.exit(app.exec())