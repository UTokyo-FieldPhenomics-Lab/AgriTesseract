
import sys
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from loguru import logger
from qfluentwidgets import (
    FluentWindow, 
    NavigationItemPosition, 
    FluentIcon as FIF,
    SplashScreen,
    setTheme,
    Theme
)

from src.gui.config import cfg, tr
from src.gui.interfaces.subplot_interface import SubplotInterface
from src.gui.interfaces.seedling_interface import SeedlingInterface
from src.gui.interfaces.rename_interface import RenameInterface
from src.gui.interfaces.timeseries_interface import TimeSeriesInterface
from src.gui.interfaces.annotate_interface import AnnotateInterface
from src.gui.interfaces.settings_interface import SettingsInterface

class MainWindow(FluentWindow):
    """
    Main Window using Fluent Design.
    """

    def __init__(self):
        super().__init__()

        # Create interfaces
        self.subplot_interface = SubplotInterface(self)
        self.seedling_interface = SeedlingInterface(self)
        self.rename_interface = RenameInterface(self)
        self.timeseries_interface = TimeSeriesInterface(self)
        self.annotate_interface = AnnotateInterface(self)
        self.settings_interface = SettingsInterface(self)

        # Set object names for FluentWindow navigation
        self.subplot_interface.setObjectName("subplot_interface")
        self.seedling_interface.setObjectName("seedling_interface")
        self.rename_interface.setObjectName("rename_interface")
        self.timeseries_interface.setObjectName("timeseries_interface")
        self.annotate_interface.setObjectName("annotate_interface")
        self.settings_interface.setObjectName("settings_interface")

        self.init_navigation()
        self.init_window()
        
        logger.info("MainWindow initialized successfully")

    def init_navigation(self):
        # Add interfaces to navigation
        self.addSubInterface(self.subplot_interface, FIF.TILES, tr("nav.subplot"))
        self.addSubInterface(self.seedling_interface, FIF.LEAF, tr("nav.seedling"))
        self.addSubInterface(self.rename_interface, FIF.EDIT, tr("nav.rename"))
        self.addSubInterface(self.timeseries_interface, FIF.HISTORY, tr("nav.timeseries"))
        self.addSubInterface(self.annotate_interface, FIF.PENCIL_INK, tr("nav.annotate"))
        
        self.navigationInterface.addSeparator()

        # add custom widget to bottom
        self.addSubInterface(
            self.settings_interface, 
            FIF.SETTING, 
            tr("nav.settings"), 
            NavigationItemPosition.BOTTOM
        )

        # NOTE: enable acrylic effect
        self.navigationInterface.setAcrylicEnabled(True)

        # disable pop animation
        # self.stackedWidget.setAnimationEnabled(False)

    def init_window(self):
        self.resize(1200, 800)

        # Set window icon if available
        self.setWindowIcon(QIcon(":/qfluentwidgets/images/logo.png"))

        self.setWindowTitle(tr("app.title"))

        # Apply Theme
        setTheme(cfg.get(cfg.themeMode))
        
        # Center window
        desktop = QApplication.primaryScreen().availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)

        # set the minimum window width that allows the navigation panel to be expanded
        self.navigationInterface.setMinimumExpandWidth(600)
        self.navigationInterface.setExpandWidth(200)
        # self.navigationInterface.expand(useAni=False)

    def closeEvent(self, event):
        logger.info("MainWindow closing")
        # Cleanup interfaces
        for interface in [self.subplot_interface, self.seedling_interface, 
                          self.rename_interface, self.timeseries_interface, 
                          self.annotate_interface]:
            if hasattr(interface, 'map_component'):
                interface.map_component.cleanup()
        super().closeEvent(event)
        
