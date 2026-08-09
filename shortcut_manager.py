# Loads command definitions, applies keyboard shortcuts and resolves typed commands
import json
from PySide6.QtGui import QKeySequence
from resource_paths import getBundleRoot, getWritableRoot

CONFIG_RELATIVE_PATH = "config/shortcuts.json"
DEFAULT_FLOATING_INPUT_ENABLED = True


class ShortcutManager:
    def __init__(self):
        self.writableConfigPath = getWritableRoot() / CONFIG_RELATIVE_PATH
        self.bundledConfigPath = getBundleRoot() / CONFIG_RELATIVE_PATH
        self.commands = []
        self.floatingInputEnabled = DEFAULT_FLOATING_INPUT_ENABLED
        self.loadCommands()

    # Load the active command list and floating input preference, preferring a saved user copy
    def loadCommands(self):
        sourcePath = self.writableConfigPath if self.writableConfigPath.is_file() else self.bundledConfigPath
        try:
            with open(sourcePath, encoding="utf-8") as fileHandle:
                configData = json.load(fileHandle)
            self.commands = configData.get("commands", [])
            self.floatingInputEnabled = configData.get("floatingCommandInputEnabled",
                                                        DEFAULT_FLOATING_INPUT_ENABLED)
        except (OSError, json.JSONDecodeError):
            self.commands = []
            self.floatingInputEnabled = DEFAULT_FLOATING_INPUT_ENABLED

    # Assign every command's shortcut to its QAction on the given main window
    def applyShortcuts(self, mainWindow):
        for command in self.commands:
            action = getattr(mainWindow, command.get("action", ""), None)
            if action is not None:
                action.setShortcut(QKeySequence(command.get("shortcut", "")))

    # Find the QAction matching a typed alias or command name, case-insensitively
    def resolveAction(self, mainWindow, typedText):
        needle = typedText.strip().lower()
        if not needle:
            return None
        for command in self.commands:
            if needle in (command.get("alias", "").lower(), command.get("commandName", "").lower()):
                return getattr(mainWindow, command.get("action", ""), None)
        return None

    # Resolve and trigger a typed command, returning whether one was found
    def executeTypedCommand(self, mainWindow, typedText):
        action = self.resolveAction(mainWindow, typedText)
        if action is None:
            return False
        action.trigger()
        return True

    # Find the first command whose alias or name starts with the partially typed text, for the HUD hint
    def findBestMatch(self, typedText):
        needle = typedText.strip().lower()
        if not needle:
            return None
        for command in self.commands:
            if command.get("alias", "").lower().startswith(needle):
                return command
        for command in self.commands:
            if command.get("commandName", "").lower().startswith(needle):
                return command
        return None

    # Persist an edited command list and floating input preference to the writable location
    def saveCommands(self, commands, floatingInputEnabled=None):
        self.commands = commands
        if floatingInputEnabled is not None:
            self.floatingInputEnabled = floatingInputEnabled
        self.writableConfigPath.parent.mkdir(parents=True, exist_ok=True)
        configData = {"commands": self.commands, "floatingCommandInputEnabled": self.floatingInputEnabled}
        with open(self.writableConfigPath, "w", encoding="utf-8") as fileHandle:
            json.dump(configData, fileHandle, indent=2, ensure_ascii=False)
