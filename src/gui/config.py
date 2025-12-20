
from enum import Enum
from PySide6.QtCore import QLocale, QObject, Signal
from qfluentwidgets import (
    QConfig, 
    qconfig, 
    ConfigItem,
    FolderValidator,
    OptionsConfigItem, 
    OptionsValidator, 
    EnumSerializer,
    Theme
)

from loguru import logger
from pathlib import Path
from typing import Dict
import json

from src import __version__

class Language(Enum):
    """Language enumeration."""
    AUTO = "Auto"
    ENGLISH = "en_US"
    CHINESE = "zh_CN"
    JAPANESE = "ja_JP"

class Config(QConfig):
    """
    Configuration for the application.
    """
    
    # Theme Mode: Light, Dark, Auto
    themeMode = OptionsConfigItem(
        "General", "ThemeMode", Theme.AUTO, OptionsValidator(Theme), EnumSerializer(Theme), restart=False
    )
    
    # Language: Auto, English, Chinese, Japanese
    language = OptionsConfigItem(
        "General", "Language", Language.AUTO, OptionsValidator(Language), EnumSerializer(Language), restart=True
    )
    
    # Model Directory
    modelDir = ConfigItem(
        "Model", "ModelDir", "", FolderValidator()
    )


class Translator(QObject):
    """
    Manages application translations.
    """

    def __init__(self):
        super().__init__()
        logger.debug(f"Requested language from config: {cfg.get(cfg.language)}")
        self._current_language = self.get_language(cfg.get(cfg.language))
        logger.info(f"Current language from config: {self._current_language}")
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self):
        """Load all translation files from locales directory."""
        # config.py is in src/gui/, resource is in src/gui/resource/
        locales_dir = Path(__file__).parent / "resource" / "i18n"
        if not locales_dir.exists():
            logger.error(f"Locales directory not found: {locales_dir}")
            return

        for file_path in locales_dir.glob("*.json"):
            lang_code = file_path.stem
            try:
                # Map the language code string to the corresponding Language enum member
                # e.g., 'en_US' -> Language.ENGLISH
                lang = Language(lang_code)
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations[lang] = json.load(f)
                logger.debug(f"Loaded translations for: {lang.name}")
            except Exception as e:
                logger.error(f"Failed to load translation {file_path}: {e}")

    def get_language(self, language: Language) -> Language:
        """Get language code from Language enum."""
        logger.debug(f"Requested language: {language}")
        if language == Language.AUTO:
            # Check system locale
            locale = QLocale.system().name() # e.g., en_US, zh_CN, ja_JP
            if locale.startswith("zh"):
                self._current_language = Language.CHINESE
            elif locale.startswith("ja"):
                self._current_language = Language.JAPANESE
            else:
                self._current_language = Language.ENGLISH
        elif language == Language.CHINESE:
            self._current_language = Language.CHINESE
        elif language == Language.JAPANESE:
            self._current_language = Language.JAPANESE
        else:
            self._current_language = Language.ENGLISH

        return self._current_language

    def set_language(self, language: Language):
        """
        Set the current language.
        
        Parameters
        ----------
        language : Language
            Language code (e.g., 'en', 'zh', 'ja').
        """
        if language == self._current_language:
            return
            
        self._current_language = language
        logger.info(f"Language switched to: {language}")

    def tr(self, key: str) -> str:
        """
        Get translated string for the given key.
        
        If translation is missing for current language, falls back to English,
        then to the key itself.
        """
        # Get dictionary for current language
        lang_dict = self._translations.get(self._current_language, {})
        
        # Try to find key in current language
        result = lang_dict.get(key)
        if result is not None:
            return result
            
        # Fallback to English if not in current language
        if self._current_language != Language.ENGLISH:
            en_dict = self._translations.get(Language.ENGLISH, {})
            result = en_dict.get(key)
            if result is not None:
                return result
                
        # Fallback to key itself
        return key

YEAR = 2025
AUTHOR = "Haozhou Wang"
VERSION = __version__
# HELP_URL = "https://pyqt-fluent-widgets.readthedocs.io"
# FEEDBACK_URL = "https://github.com/zhiyiYo/PyQt-Fluent-Widgets/issues"
# RELEASE_URL = "https://github.com/zhiyiYo/PyQt-Fluent-Widgets/releases/latest"

cfg = Config()
qconfig.load('config.json', cfg)

# Global instance
translator = Translator()

def tr(key: str) -> str:
    """Helper function to translate a key using the global translator."""
    return translator.tr(key)
