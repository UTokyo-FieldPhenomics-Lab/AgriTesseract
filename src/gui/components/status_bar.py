
from PySide6.QtWidgets import QStatusBar, QLabel, QWidget
from src.gui.i18n import tr

class StatusBar(QStatusBar):
    """
    Custom Status Bar with Coordinate, Zoom, and Rotation labels.
    """
    def __init__(self, parent: QWidget = None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self):
        # Coordinate label
        self.coord_label = QLabel(tr("status.coord").format(x=0.0, y=0.0))
        self.coord_label.setMinimumWidth(200)
        self.addWidget(self.coord_label)

        self.addWidget(QLabel("|"))

        # Zoom label
        self.zoom_label = QLabel(tr("status.zoom").format(zoom=100))
        self.zoom_label.setMinimumWidth(100)
        self.addWidget(self.zoom_label)

        self.addWidget(QLabel("|"))

        # Rotation label
        self.rotation_label = QLabel(tr("status.rotation").format(angle=0.0))
        self.rotation_label.setMinimumWidth(120)
        self.addWidget(self.rotation_label)

        # Stretch to push permanent widget to end
        self.addWidget(QLabel(""), 1)

        # Status message
        self.status_message = QLabel(tr("status.ready"))
        self.addPermanentWidget(self.status_message)

    def update_coordinates(self, x: float, y: float) -> None:
        self.coord_label.setText(tr("status.coord").format(x=x, y=y))

    def update_zoom(self, zoom_level: float) -> None:
        self.zoom_label.setText(tr("status.zoom").format(zoom=zoom_level))

    def update_rotation(self, angle: float) -> None:
        self.rotation_label.setText(tr("status.rotation").format(angle=angle))

    def set_message(self, message: str) -> None:
        self.status_message.setText(message)
