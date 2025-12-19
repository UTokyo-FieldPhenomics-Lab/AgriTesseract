"""
Translation manager for EasyPlantFieldID.
"""

import json
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal

from loguru import logger


class Translator(QObject):
    """
    Manages application translations.
    """
    
    sigLanguageChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._current_language = "en"
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_translations()

    def _load_translations(self):
        """Load all translation files from locales directory."""
        locales_dir = Path(__file__).parent / "locales"
        if not locales_dir.exists():
            logger.error(f"Locales directory not found: {locales_dir}")
            return

        for file_path in locales_dir.glob("*.json"):
            lang_code = file_path.stem
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self._translations[lang_code] = json.load(f)
                logger.debug(f"Loaded translations for: {lang_code}")
            except Exception as e:
                logger.error(f"Failed to load translation {file_path}: {e}")

    def set_language(self, language: str):
        """
        Set the current language.
        
        Parameters
        ----------
        language : str
            Language code (e.g., 'en', 'zh', 'ja').
        """
        if language == self._current_language:
            return
            
        if language not in self._translations and language != "en":
            logger.warning(f"Language {language} not found, falling back to en")
            
        self._current_language = language
        self.sigLanguageChanged.emit(language)
        logger.info(f"Language switched to: {language}")

    def get_language(self) -> str:
        """Get current language code."""
        return self._current_language

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
        if self._current_language != "en":
            en_dict = self._translations.get("en", {})
            result = en_dict.get(key)
            if result is not None:
                return result
                
        # Fallback to key itself
        return key


# Global instance
_translator = Translator()

def tr(key: str) -> str:
    """Helper function to translate a key using the global translator."""
    return _translator.tr(key)

def set_language(language: str):
    """Helper to set global language."""
    _translator.set_language(language)
