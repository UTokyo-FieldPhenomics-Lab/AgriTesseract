
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QFileDialog,
    QMessageBox,
)
from PySide6.QtCore import Qt, QSettings
from loguru import logger
from qfluentwidgets import PushButton, LineEdit, ComboBox, PrimaryPushButton

from src.gui.pages.base_page import BasePage, PageGroup
from src.gui.i18n import tr, set_language, Translator

class SettingsPage(BasePage):
    """
    Settings page for application configuration.
    """

    def __init__(self, translator: Translator, parent=None):
        self.translator = translator
        super().__init__(parent)
        self._init_controls()
        self._load_settings()

    def _init_controls(self) -> None:
        """Initialize settings controls."""
        
        # --- General Group ---
        general_group = PageGroup(tr("settings.group.general"))
        
        # Language Selection
        general_group.add_widget(QLabel(tr("settings.label.language")))
        self.combo_language = ComboBox()
        self.combo_language.addItems(["English (en)", "Chinese (zh)", "Japanese (ja)"])
        # Map nice names back to codes
        self.lang_map = {
            "English (en)": "en",
            "Chinese (zh)": "zh",
            "Japanese (ja)": "ja"
        }
        # Invert map for setting index
        self.code_map = {v: k for k, v in self.lang_map.items()}
        
        self.combo_language.currentTextChanged.connect(self._on_language_changed)
        general_group.add_widget(self.combo_language)
        
        # Restart warning label
        self.label_restart = QLabel(tr("settings.msg.restart"))
        self.label_restart.setStyleSheet("color: #ffa500; font-style: italic;")
        self.label_restart.setVisible(False)
        general_group.add_widget(self.label_restart)

        self.add_group(general_group)

        # --- Model Configuration Group ---
        model_group = PageGroup(tr("settings.group.model"))
        
        model_group.add_widget(QLabel(tr("settings.label.model_dir")))
        
        dir_layout_widget = QWidget()
        dir_layout = QVBoxLayout(dir_layout_widget)
        dir_layout.setContentsMargins(0,0,0,0)
        
        self.edit_model_dir = LineEdit()
        self.edit_model_dir.setPlaceholderText("path/to/models")
        self.edit_model_dir.textChanged.connect(self._save_settings) # Auto-save on change? Or explicit save?
        # Let's save on focus out or special button, but textChanged is easiest for now if using QSettings
        
        self.btn_browse_model = PushButton(tr("settings.btn.browse"))
        self.btn_browse_model.clicked.connect(self._browse_model_dir)
        
        model_group.add_widget(self.edit_model_dir)
        model_group.add_widget(self.btn_browse_model)

        self.add_group(model_group)
        
        # Add stretch to push content up
        self._layout.addStretch(1)

    def _load_settings(self):
        """Load settings from QSettings."""
        self.settings = QSettings("UTokyo-FieldPhenomics-Lab", "EasyPlantFieldID")
        
        # Load Language
        current_lang = self.settings.value("language", "en")
        
        # If the translator has a different language (e.g. from main.py init), sync it
        # Actually main.py should load this setting. 
        # But here we set the combo box.
        
        display_text = self.code_map.get(current_lang, "English (en)")
        self.combo_language.setCurrentText(display_text)
        
        # Load Model Dir
        model_dir = self.settings.value("model_dir", "")
        self.edit_model_dir.setText(str(model_dir))

    def _save_settings(self):
        """Save current settings."""
        # Save Model Dir
        self.settings.setValue("model_dir", self.edit_model_dir.text())
        logger.info("Settings saved")

    def _browse_model_dir(self):
        """Open file dialog to select model directory."""
        directory = QFileDialog.getExistingDirectory(
            self, 
            tr("settings.btn.browse"),
            self.edit_model_dir.text()
        )
        if directory:
            self.edit_model_dir.setText(directory)
            self._save_settings()

    def _on_language_changed(self, text: str):
        """Handle language change."""
        lang_code = self.lang_map.get(text, "en")
        
        # Save to settings
        self.settings.setValue("language", lang_code)
        
        # Show restart warning
        self.label_restart.setVisible(True)
        
        logger.info(f"Language setting changed to {lang_code}. Restart required.")
