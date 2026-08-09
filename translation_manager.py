# Discovers and lazily loads translation JSON files, replacing the old hardcoded lang.py
import json
from resource_paths import getBundleRoot

TRANSLATIONS_DIRECTORY = "translations"
DISPLAY_NAME_KEY = "_languageDisplayName"
FALLBACK_LANGUAGE_CODE = "en"


class TranslationManager:
    def __init__(self):
        self.cache = {}
        self.translationsRoot = getBundleRoot() / TRANSLATIONS_DIRECTORY

    # Every language code discoverable on disk right now, no hardcoded language list
    def discoverLanguageCodes(self):
        if not self.translationsRoot.is_dir():
            return []
        return sorted(path.stem for path in self.translationsRoot.glob("*.json"))

    # Every currently discoverable language code, used for session-restore validation
    def availableLanguageCodes(self):
        return self.discoverLanguageCodes()

    # (langCode, displayName) pairs used to build the language switcher
    def availableLanguages(self):
        languages = []
        for langCode in self.discoverLanguageCodes():
            languageDict = self.getLanguage(langCode)
            displayName = languageDict.get(DISPLAY_NAME_KEY, langCode.upper())
            languages.append((langCode, displayName))
        return languages

    # Read one languageCode.json file, returning {} on any I/O or parse failure
    def loadLanguageFile(self, langCode):
        filePath = self.translationsRoot / f"{langCode}.json"
        try:
            with open(filePath, encoding="utf-8") as fileHandle:
                return json.load(fileHandle)
        except (OSError, json.JSONDecodeError):
            return {}

    # Return the flat dict for a language, caching it and falling back to English if missing
    def getLanguage(self, langCode):
        if langCode not in self.cache:
            self.cache[langCode] = self.loadLanguageFile(langCode)
        languageDict = self.cache[langCode]
        if not languageDict and langCode != FALLBACK_LANGUAGE_CODE:
            return self.getLanguage(FALLBACK_LANGUAGE_CODE)
        return languageDict
