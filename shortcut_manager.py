# Loads command definitions, applies keyboard shortcuts and resolves typed commands
import json
from PySide6.QtGui import QKeySequence
from resource_paths import getBundleRoot, getWritableRoot

CONFIG_RELATIVE_PATH = "config/shortcuts.json"


class ShortcutManager:
    def __init__(self):
        self.writableConfigPath = getWritableRoot() / CONFIG_RELATIVE_PATH
        self.bundledConfigPath = getBundleRoot() / CONFIG_RELATIVE_PATH
        self.commands = []
        self.loadCommands()

    # Load the active command list, preferring a previously saved user copy over the bundled default
    def loadCommands(self):
        sourcePath = self.writableConfigPath if self.writableConfigPath.is_file() else self.bundledConfigPath
        try:
            with open(sourcePath, encoding="utf-8") as fileHandle:
                self.commands = json.load(fileHandle).get("commands", [])
        except (OSError, json.JSONDecodeError):
            self.commands = []

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

    # Persist an edited command list to the writable location, creating the folder if needed
    def saveCommands(self, commands):
        self.commands = commands
        self.writableConfigPath.parent.mkdir(parents=True, exist_ok=True)
        with open(self.writableConfigPath, "w", encoding="utf-8") as fileHandle:
            json.dump({"commands": self.commands}, fileHandle, indent=2, ensure_ascii=False)
