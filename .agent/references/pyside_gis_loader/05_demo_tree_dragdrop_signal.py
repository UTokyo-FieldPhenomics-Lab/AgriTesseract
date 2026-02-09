import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, 
    QAbstractItemView, QStyle
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QDragMoveEvent

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
        self.itemSuccessfullyDropped.connect(self.on_item_dropped)

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


# --- 主窗口设置 (使用上面的 CustomDropTreeWidget) ---

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("重写 DropEvent 的 QTreeWidget")
        self.setGeometry(300, 300, 400, 300)

        # A. 使用我们的自定义子类
        self.tree = CustomDropTreeWidget()
        # self.tree = QTreeWidget()
        self.tree.setHeaderLabel("文件系统")
        
        # B. 填充项目 (与上个示例相同)
        self.populate_tree()

        layout = QVBoxLayout()
        layout.addWidget(self.tree)
        self.setLayout(layout)

    def populate_tree(self):
        folder_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon)
        file_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

        base_flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

        # --- 文件夹 (Droppable) ---
        folder1 = QTreeWidgetItem(self.tree, ["文件夹 A"])
        folder1.setIcon(0, folder_icon)
        folder1.setFlags(base_flags | Qt.ItemFlag.ItemIsDropEnabled)

        folder2 = QTreeWidgetItem(self.tree, ["文件夹 B"])
        folder2.setIcon(0, folder_icon)
        folder2.setFlags(base_flags | Qt.ItemFlag.ItemIsDropEnabled)

        # --- 文件 (Draggable) ---
        file_a = QTreeWidgetItem(self.tree, ["文件 1.txt"])
        file_a.setIcon(0, file_icon)
        file_a.setFlags(base_flags | Qt.ItemFlag.ItemIsDragEnabled)

        file_b = QTreeWidgetItem(self.tree, ["文件 2.py"])
        file_b.setIcon(0, file_icon)
        # 文件：可以被拖拽 (Drag)，但不能被放置 (Drop)
        file_b.setFlags(base_flags | Qt.ItemFlag.ItemIsDragEnabled)

        file_c = QTreeWidgetItem(folder1, ["文件 3.md"])
        file_c.setIcon(0, file_icon)
        file_c.setFlags(base_flags | Qt.ItemFlag.ItemIsDragEnabled)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())