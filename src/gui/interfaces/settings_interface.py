
from pathlib import Path
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFileDialog
from PySide6.QtCore import Qt, QSettings, Signal
from loguru import logger
from qfluentwidgets import (
    ScrollArea, 
    SettingCardGroup, 
    PushSettingCard, 
    ComboBoxSettingCard,
    ExpandLayout,
    InfoBar,
    InfoBarPosition,
    SettingCard,
    ComboBox
)
from qfluentwidgets import FluentIcon as FIF

from src.gui.i18n import tr, Translator

class LanguageSettingCard(SettingCard):
    """ Language setting card with ComboBox """
    def __init__(self, icon, title, content, texts, parent=None):
        super().__init__(icon, title, content, parent)
        self.comboBox = ComboBox(self)
        self.comboBox.addItems(texts)
        self.hBoxLayout.addWidget(self.comboBox, 0, Qt.AlignmentFlag.AlignRight)
        self.hBoxLayout.addSpacing(16)

class SettingsInterface(ScrollArea):
    """
    Settings Interface.
    """
    def __init__(self, translator: Translator, parent=None):
        super().__init__(parent)
        self.translator = translator
        self.settings = QSettings("UTokyo-FieldPhenomics-Lab", "EasyPlantFieldID")
        
        self.scrollWidget = QWidget()
        self.expandLayout = ExpandLayout(self.scrollWidget)
        
        self.setWidget(self.scrollWidget)
        self.setWidgetResizable(True)
        
        self._init_ui()
        self._load_settings()

    def _init_ui(self):
        """Initialize UI controls."""
        
        # --- Settings Header ---
        self.settingLabel = QLabel(tr("nav.settings"), self)
        self.settingLabel.setStyleSheet("font-size: 24px; font-weight: bold;")
        
        # --- General Group ---
        self.generalGroup = SettingCardGroup(tr("settings.group.general"), self.scrollWidget)
        
        # Language Selection
        self.languageCard = LanguageSettingCard(
            FIF.LANGUAGE,
            tr("settings.label.language"),
            tr("settings.desc.language"),
            texts=["English", "中文", "日本語"],
            parent=self.generalGroup
        )
        self.languageCard.comboBox.setCurrentIndex(0)
        self.languageCard.comboBox.currentTextChanged.connect(self._on_language_changed)
        
        self.generalGroup.addSettingCard(self.languageCard)
        
        # --- Model Configuration Group ---
        self.modelGroup = SettingCardGroup(tr("settings.group.model"), self.scrollWidget)
        
        self.modelDirCard = PushSettingCard(
            tr("settings.btn.browse"),
            FIF.FOLDER,
            tr("settings.label.model_dir"),
            "...", # Placeholder for content
            self.modelGroup
        )
        self.modelDirCard.clicked.connect(self._browse_model_dir)
        
        self.modelGroup.addSettingCard(self.modelDirCard)

        # --- Add Groups to Layout ---
        self.expandLayout.setSpacing(28)
        self.expandLayout.setContentsMargins(60, 60, 60, 60)
        self.expandLayout.addWidget(self.settingLabel)
        self.expandLayout.addWidget(self.generalGroup)
        self.expandLayout.addWidget(self.modelGroup)

    def _load_settings(self):
        """Load settings from QSettings."""
        # Load Language
        current_lang = self.settings.value("language", "en")
        
        # Map code to text index
        lang_map = {
            "en": 0, # English
            "zh": 1, # Chinese
            "ja": 2  # Japanese
        }
        index = lang_map.get(current_lang, 0)
        self.languageCard.comboBox.setCurrentIndex(index)
        
        # Load Model Dir
        model_dir = self.settings.value("model_dir", "")
        if model_dir:
            self.modelDirCard.setContent(str(model_dir))
        else:
            self.modelDirCard.setContent(tr("settings.placeholder.no_dir"))

    def _browse_model_dir(self):
        """Open file dialog to select model directory."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            tr("settings.btn.browse"),
            self.modelDirCard.contentLabel.text()
        )
        if directory:
            self.modelDirCard.setContent(directory)
            self.settings.setValue("model_dir", directory)
            logger.info(f"Model directory saved: {directory}")

    def _on_language_changed(self, text: str):
        """Handle language change."""
        lang_map = {
            "English": "en",
            "中文": "zh",
            "日本語": "ja"
        }
        lang_code = lang_map.get(text, "en")
        
        # Only update if changed
        current_saved = self.settings.value("language", "en")
        if lang_code != current_saved:
            self.settings.setValue("language", lang_code)
            logger.info(f"Language setting changed to {lang_code}. Restart required.")
            
            InfoBar.warning(
                title=tr("settings.msg.restart_title"),
                content=tr("settings.msg.restart"),
                orient=Qt.Orientation.Horizontal,
                isClosable=True,
                position=InfoBarPosition.TOP_RIGHT, # Need to import InfoBarPosition
                duration=5000,
                parent=self
            )
