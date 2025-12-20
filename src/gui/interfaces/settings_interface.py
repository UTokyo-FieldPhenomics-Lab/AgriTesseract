
from pathlib import Path
from PySide6.QtWidgets import QWidget, QLabel, QFileDialog
from PySide6.QtCore import Qt
from qfluentwidgets import (
    ScrollArea, 
    SettingCardGroup, 
    PushSettingCard, 
    OptionsSettingCard,
    ExpandLayout,
    InfoBar,
    InfoBarPosition,
    Theme,
    setTheme,
    setThemeColor
)
from qfluentwidgets import FluentIcon as FIF

from src.gui.config import cfg, Language, tr, translator

class SettingsInterface(ScrollArea):
    """
    Settings Interface.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        self.setObjectName('settingsInterface')
        
        self._init_ui()
        self._load_settings()
        self._connect_signals()

    def _init_ui(self):
        """Initialize UI controls."""
        
        # --- Settings Header ---
        self.settingLabel = QLabel(tr("nav.settings"), self)
        self.settingLabel.setObjectName('settingLabel')
        
        # --- General Group ---
        self.generalGroup = SettingCardGroup(tr("settings.group.general"), self.scrollWidget)
        
        # Theme Selection
        self.themeCard = OptionsSettingCard(
            cfg.themeMode,
            FIF.BRUSH,
            tr("settings.label.theme"),
            tr("settings.desc.theme"),
            texts=[
                tr("settings.theme.light"),
                tr("settings.theme.dark"),
                tr("settings.theme.auto"),
            ],
            parent=self.generalGroup
        )
        
        # Language Selection
        self.languageCard = OptionsSettingCard(
            cfg.language,
            FIF.LANGUAGE,
            tr("settings.label.language"),
            tr("settings.desc.language"),
            texts=[
                tr("settings.lang.auto"),
                tr("settings.lang.en"),
                tr("settings.lang.zh"),
                tr("settings.lang.ja")
            ],
            parent=self.generalGroup
        )
        
        self.generalGroup.addSettingCard(self.themeCard)
        self.generalGroup.addSettingCard(self.languageCard)
        
        # --- Model Configuration Group ---
        self.modelGroup = SettingCardGroup(tr("settings.group.model"), self.scrollWidget)
        
        self.modelDirCard = PushSettingCard(
            tr("settings.btn.browse"),
            FIF.FOLDER,
            tr("settings.label.model_dir"),
            cfg.modelDir.value,
            self.modelGroup
        )
        
        self.modelGroup.addSettingCard(self.modelDirCard)

        # --- Add Groups to Layout ---
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(60, 60, 60, 60)
        self.expandLayout.addWidget(self.settingLabel)
        self.expandLayout.addWidget(self.generalGroup)
        self.expandLayout.addWidget(self.modelGroup)

    def _load_settings(self):
        """Load settings (handled by QConfig binding automatically for some widgets, but some manual sync needed)."""
        # Set initial content for model dir
        if not cfg.modelDir.value:
            self.modelDirCard.setContent(tr("settings.placeholder.no_dir"))
        else:
            self.modelDirCard.setContent(cfg.modelDir.value)

    def _connect_signals(self):
        """Connect signals."""
        self.modelDirCard.clicked.connect(self._browse_model_dir)
        cfg.themeChanged.connect(self.setQss)
        cfg.language.valueChanged.connect(self.setLanguage)

    def _browse_model_dir(self):
        """Open file dialog to select model directory."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            tr("settings.btn.browse"),
            self.modelDirCard.contentLabel.text() if self.modelDirCard.contentLabel.text() != "..." else ""
        )
        if directory:
            self.modelDirCard.setContent(directory)
            cfg.set(cfg.modelDir, directory)

    def _on_restart_needed(self):
        """Show restart warning."""
        InfoBar.warning(
            title=tr("settings.msg.restart_title"),
            content=tr("settings.msg.restart"),
            orient=Qt.Orientation.Horizontal,
            isClosable=True,
            position=InfoBarPosition.TOP_RIGHT,
            duration=5000,
            parent=self
        )

    def setQss(self):
        """Apply QSS."""
        theme = cfg.themeMode.value
        if theme == Theme.AUTO:
            import darkdetect
            theme_name = "dark" if darkdetect.isDark() else "light"
        else:
            theme_name = theme.value.lower()
            
        qss_path = Path(__file__).parent.parent / "resource" / "qss" / theme_name / "setting_interface.qss"
        if qss_path.exists():
            with open(qss_path, encoding='utf-8') as f:
                self.setStyleSheet(f.read())

    def setLanguage(self, language: Language):
        """Set language."""
        translator.set_language(language)
        self._on_restart_needed()
