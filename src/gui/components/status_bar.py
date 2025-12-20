from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QWidget
from PySide6.QtCore import Signal, Qt
from qfluentwidgets import DoubleSpinBox, BodyLabel

from src.gui.config import tr

class StatusBar(QFrame):
    """
    Custom Status Bar with Coordinate display and interactive Zoom/Rotation controls.
    """
    
    sigZoomChanged = Signal(float)
    sigRotationChanged = Signal(float)

    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._init_ui()
        self._connect_signals()

    def _init_ui(self):
        self.setObjectName('statusBar')
        self.setFixedHeight(40)
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Section 1: Coordinates ---
        self.coord_container = QWidget()
        coord_layout = QHBoxLayout(self.coord_container)
        coord_layout.setContentsMargins(16, 0, 16, 0)
        
        self.coord_label = BodyLabel(tr("status.coord").format(x=0.0, y=0.0))
        coord_layout.addWidget(self.coord_label, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.coord_container, 1) # Ratio 1

        # Separator 1
        layout.addWidget(self._create_separator())

        # --- Section 2: Zoom ---
        self.zoom_container = QWidget()
        zoom_layout = QHBoxLayout(self.zoom_container)
        zoom_layout.setContentsMargins(16, 0, 16, 0)
        zoom_layout.setSpacing(10)
        
        # Label outside
        self.zoom_label = BodyLabel(tr("status.zoom_prefix").strip()) 
        
        self.zoom_sb = DoubleSpinBox()
        self.zoom_sb.setRange(1, 50000)
        self.zoom_sb.setSuffix("%")
        # Ensure no prefix in the box itself
        self.zoom_sb.setPrefix("") 
        self.zoom_sb.setValue(100)
        self.zoom_sb.setSingleStep(10)
        self.zoom_sb.setDecimals(0)
        
        # Layout
        zoom_layout.addWidget(self.zoom_label)
        zoom_layout.addWidget(self.zoom_sb, 1) # Expand to fill
        
        layout.addWidget(self.zoom_container, 1) # Ratio 1

        # Separator 2
        layout.addWidget(self._create_separator())

        # --- Section 3: Rotation ---
        self.rotation_container = QWidget()
        rot_layout = QHBoxLayout(self.rotation_container)
        rot_layout.setContentsMargins(16, 0, 16, 0)
        rot_layout.setSpacing(10)
        
        self.rotation_label = BodyLabel(tr("status.rotation_prefix").strip())
        
        self.rotation_sb = DoubleSpinBox()
        self.rotation_sb.setRange(-360, 360) 
        self.rotation_sb.setSuffix("°")
        self.rotation_sb.setPrefix("")
        self.rotation_sb.setValue(0.00)
        self.rotation_sb.setSingleStep(1.0)
        self.rotation_sb.setDecimals(2)
        
        # Layout
        rot_layout.addWidget(self.rotation_label)
        rot_layout.addWidget(self.rotation_sb, 1) # Expand to fill
        
        layout.addWidget(self.rotation_container, 1) # Ratio 1
        
        # ready status is removed as requested.

    def _create_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setLineWidth(1)
        line.setMidLineWidth(0)
        line.setStyleSheet("QFrame { border: none; background-color: #E5E5E5; max-width: 1px; }") 
        # Note: Colors should dynamic in real app, but this mimics simple separator
        line.setFixedHeight(24)
        return line

    def _connect_signals(self):
        # Value changed -> Emit signal
        self.zoom_sb.valueChanged.connect(self._on_zoom_changed)
        self.rotation_sb.valueChanged.connect(self._on_rotation_changed)

    def _on_zoom_changed(self, value: float):
        self.sigZoomChanged.emit(value)

    def _on_rotation_changed(self, value: float):
        self.sigRotationChanged.emit(value)

    def update_coordinates(self, x: float, y: float) -> None:
        self.coord_label.setText(tr("status.coord").format(x=x, y=y))

    def update_zoom(self, zoom_level: float) -> None:
        # Block signals to prevent loop: Map -> StatusBar -> Map -> ...
        if self.zoom_sb.value() != zoom_level:
            self.zoom_sb.blockSignals(True)
            self.zoom_sb.setValue(zoom_level)
            self.zoom_sb.blockSignals(False)

    def update_rotation(self, angle: float) -> None:
        # Normalize angle for display if needed? Map might send 0-360 or -180-180.
        # Spinbox handles range.
        if abs(self.rotation_sb.value() - angle) > 0.01:
            self.rotation_sb.blockSignals(True)
            self.rotation_sb.setValue(angle)
            self.rotation_sb.blockSignals(False)
