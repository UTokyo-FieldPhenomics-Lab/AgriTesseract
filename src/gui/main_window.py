
import sys
from typing import Optional

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer

from loguru import logger

from qfluentwidgets import (
    FluentWindow, 
    NavigationItemPosition, 
    FluentIcon as FIF,
    SplashScreen,
    setTheme,
    Theme,
    isDarkTheme
)

from src.gui.config import cfg, tr
from src.gui.tabs.subplot_generate import SubplotTab
from src.gui.tabs.seedling_detect import SeedlingTab
from src.gui.tabs.rename_ids import RenameTab
from src.gui.tabs.timeseries_crop import TimeSeriesTab
from src.gui.tabs.active_annotate import ActiveAnnotateTab
from src.gui.tabs.settings import SettingsTab

class MainWindow(FluentWindow):
    """
    Main Window using Fluent Design.
    """

    def __init__(self):
        super().__init__()

        # Create interfaces
        self.subplot_tab = SubplotTab(self)
        self.seedling_tab = SeedlingTab(self)
        self.rename_tab = RenameTab(self)
        self.timeseries_tab = TimeSeriesTab(self)
        self.annotate_tab = ActiveAnnotateTab(self)
        self.settings_tab = SettingsTab(self)

        # Set object names for FluentWindow navigation
        self.subplot_tab.setObjectName("subplot_tab")
        self.seedling_tab.setObjectName("seedling_tab")
        self.rename_tab.setObjectName("rename_tab")
        self.timeseries_tab.setObjectName("timeseries_tab")
        self.annotate_tab.setObjectName("annotate_tab")
        self.settings_tab.setObjectName("settings_tab")

        self.init_navigation()
        self.init_window()
        
        logger.info("MainWindow initialized successfully")

    def init_navigation(self):
        # Add interfaces to navigation
        self.addSubInterface(self.subplot_tab, FIF.TILES, tr("nav.subplot"))
        self.addSubInterface(self.seedling_tab, FIF.LEAF, tr("nav.seedling"))
        self.addSubInterface(self.rename_tab, FIF.EDIT, tr("nav.rename"))
        self.addSubInterface(self.timeseries_tab, FIF.HISTORY, tr("nav.timeseries"))
        self.addSubInterface(self.annotate_tab, FIF.PENCIL_INK, tr("nav.annotate"))
        
        self.navigationInterface.addSeparator()

        # add custom widget to bottom
        self.addSubInterface(
            self.settings_tab, 
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

        self.navigationInterface.setMinimumExpandWidth(600)
        self.navigationInterface.setExpandWidth(200)
        # self.navigationInterface.expand(useAni=False)

        self.setMicaEffectEnabled(cfg.get(cfg.micaEnabled))

    def _onThemeChangedFinished(self):
        super()._onThemeChangedFinished()
        # retry
        if self.isMicaEffectEnabled():
            QTimer.singleShot(100, lambda: self.windowEffect.setMicaEffect(self.winId(), isDarkTheme()))

    def closeEvent(self, event):
        logger.info("MainWindow closing")
        # Cleanup interfaces
        for interface in [self.subplot_tab, self.seedling_tab, 
                          self.rename_tab, self.timeseries_tab, 
                          self.annotate_tab]:
            if hasattr(interface, 'map_component'):
                interface.map_component.cleanup()
        super().closeEvent(event)
        
