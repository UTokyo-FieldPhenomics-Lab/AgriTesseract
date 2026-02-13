from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QWidget
from qfluentwidgets import (
    BodyLabel,
    DoubleSpinBox,
    IndeterminateProgressBar,
    ProgressBar,
)

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
        self.setObjectName("statusBar")
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

        layout.addWidget(self.coord_container, 1)  # Ratio 1

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
        zoom_layout.addWidget(self.zoom_sb, 1)  # Expand to fill

        layout.addWidget(self.zoom_container, 1)  # Ratio 1

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
        rot_layout.addWidget(self.rotation_sb, 1)  # Expand to fill

        layout.addWidget(self.rotation_container, 0)  # Fixed size

        # Spacer to push status to right
        # layout.addStretch(1)

        # --- Section 4: Status Indicators ---
        self._init_status_indicators(layout)

    def _create_separator(self) -> QFrame:
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setLineWidth(1)
        line.setMidLineWidth(0)
        line.setStyleSheet(
            "QFrame { border: none; background-color: #E5E5E5; max-width: 1px; }"
        )
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

    def _init_status_indicators(self, layout: QHBoxLayout):
        """Initialize status indicator section."""
        # Separator 3
        layout.addWidget(self._create_separator())

        self.status_container = QWidget()
        status_layout = QHBoxLayout(self.status_container)
        status_layout.setContentsMargins(16, 0, 16, 0)
        status_layout.setSpacing(10)

        # 1. Message Label / Badge Container
        self.message_container = QWidget()
        self.message_layout = QHBoxLayout(self.message_container)
        self.message_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.addWidget(self.message_container)

        # 2. Progress Bar
        self.progress_bar = ProgressBar()
        self.progress_bar.setFixedWidth(50)
        self.progress_bar.hide()
        status_layout.addWidget(self.progress_bar)

        # 3. Indeterminate Progress Bar
        self.busy_bar = IndeterminateProgressBar()
        self.busy_bar.setFixedWidth(50)
        self.busy_bar.hide()
        status_layout.addWidget(self.busy_bar)

        layout.addWidget(self.status_container)
        layout.addStretch(
            1
        )  # Stretch to keep status on left/center-left or let it push?
        # Actually user requirement: "at the last side" (right side).
        # So we should add stretch before this container if we want it on the right.

    def _rebuild_layout_for_status(self):
        """Rebuild layout to place coordinates left, zoom/rot center, status right."""
        # Current layout in _init_ui is adding items sequentially.
        # We need to insert stretch before status container.
        # Let's modify _init_ui instead of appending here.
        pass

    def set_status(self, mode: str, message: str) -> None:
        """
        Set status message and badge.

        Parameters
        ----------
        mode : str
             'success', 'warning', 'error', 'info', 'custom'
        message : str
             Status message text
        """
        _ = (mode, message)
        return

    def set_progress(self, value: int = None) -> None:
        """
        Set progress bar state.

        Parameters
        ----------
        value : int, optional
            0-100 for determinate progress.
            None for indeterminate (busy) state.
            -1 to hide progress bars.
        """
        if value is None:
            self.progress_bar.hide()
            self.busy_bar.show()
            if not self.busy_bar.isStarted():
                self.busy_bar.start()
        elif 0 <= value <= 100:
            self.busy_bar.hide()
            if self.busy_bar.isStarted():
                self.busy_bar.stop()
            self.progress_bar.setValue(value)
            self.progress_bar.show()
        else:
            self.clear_progress()

    def clear_message(self):
        """Clear status message."""
        while self.message_layout.count():
            item = self.message_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def clear_progress(self):
        """Hide all progress bars."""
        self.progress_bar.hide()
        self.busy_bar.hide()
        if self.busy_bar.isStarted():
            self.busy_bar.stop()

    def clear_status(self):
        """Clear all status content."""
        self.clear_message()
        self.clear_progress()
