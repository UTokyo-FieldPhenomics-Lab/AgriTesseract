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
    QTreeWidget,      
    QTreeWidgetItem,  
    QMenu,            
    QDialog,          
    QLabel,
    QMessageBox,
    QAbstractItemView 
)
from PySide6.QtGui import QAction, QColor, QDragEnterEvent, QDropEvent, QDragMoveEvent
from PySide6.QtCore import QRectF, Qt, QPoint, Signal

# 确保 pyqtgraph 在 PySide6 模式下运行
# pg.setConfigOption('leftButtonPan', False) 

# -----------------------------------------------------------------
# 自定义 QTreeWidget 子类
# -----------------------------------------------------------------
# 1. 创建一个 QTreeWidget 的子类
class CustomDropTreeWidget(QTreeWidget):
    
    # 2. (推荐) 创建一个自定义信号，这是Qt的最佳实践
    #    你可以在拖放完成后发射这个信号。
    itemSuccessfullyDropped = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # 3. 在 __init__ 中设置拖放属性
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        # 4. (推荐) 连接你自定义的信号到一个槽函数
        # self.itemSuccessfullyDropped.connect(self.on_item_dropped)

    def on_item_dropped(self):
        # 8. 这是信号触发时调用的函数
        print("dragged")

    # 5. 重写 dragEnterEvent
    def dragEnterEvent(self, event: QDragEnterEvent):
        # 我们必须 'accept' 这个事件，否则 dropEvent 永远不会被触发
        # acceptProposedAction() 会自动处理来自 InternalMove 的数据
        # event.acceptProposedAction()
        super().dragEnterEvent(event)

    # 6. 重写 dragMoveEvent
    def dragMoveEvent(self, event: QDragMoveEvent):
        # 同样，在移动时也要 'accept'
        # event.acceptProposedAction()
        super().dragMoveEvent(event)

    # 7. 重写 dropEvent
    def dropEvent(self, event: QDropEvent):
        # 关键步骤：首先调用父类的 dropEvent
        # 这将执行实际的 "InternalMove" 操作
        super().dropEvent(event)
        
        # 检查拖放是否真的被接受并完成（例如，你没有拖放到一个无效的位置）
        # event.isAccepted() 在 super().dropEvent() 后会是 True
        if event.isAccepted():
            # 现在，父类的操作已完成，执行我们的自定义操作
            # 你可以直接在这里打印：
            # print("dragged")
            
            # 或者（更好的做法）发射我们的自定义信号：
            self.itemSuccessfullyDropped.emit()

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
        # self.layer_tree_widget = QTreeWidget()
        self.layer_tree_widget = CustomDropTreeWidget()
        self.layer_tree_widget.setHeaderLabels(["(Layers)"])

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
        # [FIX 2] 连接到我们的自定义信号
        # self.layer_tree_widget.orderChanged.connect(self.update_z_order)
        self.layer_tree_widget.itemSuccessfullyDropped.connect(self.update_z_order)

        # [特性 2] Checkbox/重命名 状态改变信号
        self.layer_tree_widget.itemChanged.connect(self.handle_item_changed)
        
        # [特性 3] 右键菜单信号
        self.layer_tree_widget.customContextMenuRequested.connect(self.open_context_menu)

        # [新特性 1] 双击重命名
        self.layer_tree_widget.itemDoubleClicked.connect(self.start_rename_from_doubleclick)


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
        self.register_layer(item, layer_name)

    def add_image_layer(self):
        img_data = np.random.normal(size=(50, 50))
        item = pg.ImageItem(img_data)
        x, y = np.random.rand(2) * 50
        item.setRect(QRectF(x, y, 50, 50))
        item.setLookupTable(pg.colormap.get('viridis').getLookupTable())
        
        layer_name = f"Image Layer {self.layer_counter}"
        self.register_layer(item, layer_name)

    def add_line_layer(self):
        x = np.linspace(0, 100, 20) 
        y = np.random.rand(20) * 100
        color = np.random.choice(['r', 'g', 'b', 'c', 'm', 'y'])
        item = pg.PlotDataItem(x=x, y=y, pen=pg.mkPen(color, width=2))
        
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
        # 我们存储一个元组: (pyqtgraph_item, z_base)
        self.layer_registry[name] = item
        
        # --- [升级] UI 列表 (QTreeWidget) ---
        
        # 在操作 QTreeWidget 时暂时阻塞信号
        # 否则 'itemChanged' 会在我们设置 Checkbox 时触发
        self.layer_tree_widget.blockSignals(True)
        
        list_item = QTreeWidgetItem([name])

        base_flags = Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEditable |Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        
        # [特性 2] 添加 Checkbox 并默认勾选
        # list_item.setFlags(
        #     list_item.flags() | 
        #     Qt.ItemFlag.ItemIsUserCheckable | 
        #     Qt.ItemFlag.ItemIsEditable |
        #     Qt.ItemFlag.ItemIsDragEnabled
        # )
        list_item.setFlags(base_flags | Qt.ItemFlag.ItemIsDragEnabled)
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
            if layer_name in self.layer_registry: # 注册表中只存储了 item
                pyqt_item = self.layer_registry[layer_name]
                
                # 3. 计算新的 Z 值
                # 列表顶部的项目 (i=0) 应该有最高的 Z 值 (例如 100)
                # 列表底部的项目 (i=count-1) 应该有最低的 Z 值 (例如 1)
                new_z = count - i 
                
                pyqt_item.setZValue(new_z)
                print(f"图层 '{layer_name}' Z-Value 设置为: {new_z}")

    def process_rename(self, item_widget: QTreeWidgetItem, old_name: str, new_name: str):
        """
        [新特性 1] 处理重命名逻辑
        """
        # 1. 检查新名称是否已存在
        if new_name in self.layer_registry:
            QMessageBox.warning(self, "重命名失败", f"名称 '{new_name}' 已存在。")
            # 阻止信号, 将文本改回旧名称
            self.layer_tree_widget.blockSignals(True)
            item_widget.setText(0, old_name)
            self.layer_tree_widget.blockSignals(False)
            return
            
        # 2. 更新注册表 (用新键替换旧键)
        self.layer_registry[new_name] = self.layer_registry.pop(old_name)
        print(f"图层已重命名: '{old_name}' -> '{new_name}'")

    def handle_item_changed(self, item_widget: QTreeWidgetItem, column: int):
        """
        处理 *所有* item 变化 (Checkbox 和 重命名)
        """
        if column != 0: 
            return

        # [新特性 1] 检查这是否是一个重命名事件
        if hasattr(self, 'old_rename_key'):
            old_name = self.old_rename_key
            new_name = item_widget.text(0)
            del self.old_rename_key # 清除标志
            
            if old_name != new_name:
                self.process_rename(item_widget, old_name, new_name)
        
        # [特性 2] 否则, 假定这是一个 Checkbox 事件
        else:
            self.process_visibility_change(item_widget)

    def process_visibility_change(self, item_widget: QTreeWidgetItem):
        """
        [特性 2] Checkbox 可见性
        当 Checkbox 状态改变时触发
        """           
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

    # --- [新特性] 重命名辅助函数 ---
    def start_rename_from_doubleclick(self, item_widget: QTreeWidgetItem, column: int):
        """由双击触发"""
        if column == 0:
            self.start_rename_item(item_widget)
            
    def start_rename_from_menu(self, item_widget: QTreeWidgetItem):
        """由右键菜单触发"""
        self.start_rename_item(item_widget)

    def start_rename_item(self, item_widget: QTreeWidgetItem):
        """
        [新特性 1] 重命名的入口点
        """
        # 1. 存储旧名称, 以便 itemChanged 信号知道这是一个重命名
        self.old_rename_key = item_widget.text(0)
        
        # 2. 告诉 QTreeWidget 进入编辑模式
        self.layer_tree_widget.editItem(item_widget, 0)

    def delete_layer(self, item_widget: QTreeWidgetItem):
        """
        [特性 3] 删除操作
        """
        layer_name = item_widget.text(0)
        
        if layer_name in self.layer_registry:
            # 1. 从 PlotWidget 中移除
            pyqt_item = self.layer_registry[layer_name]
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