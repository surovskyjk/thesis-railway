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

    # Read one shortcuts.json file, returning an empty command list on any read failure
    def readConfigFile(self, configPath):
        try:
            with open(configPath, encoding="utf-8") as fileHandle:
                return json.load(fileHandle)
        except (OSError, json.JSONDecodeError):
            return {}

    # Load the active command list and floating input preference, preferring a saved user copy
    def loadCommands(self):
        sourcePath = self.writableConfigPath if self.writableConfigPath.is_file() else self.bundledConfigPath
        configData = self.readConfigFile(sourcePath)
        self.commands = configData.get("commands", [])
        self.floatingInputEnabled = configData.get("floatingCommandInputEnabled",
                                                    DEFAULT_FLOATING_INPUT_ENABLED)

        # A saved user copy predating a new built-in command would otherwise hide it forever
        if sourcePath == self.writableConfigPath:
            knownNames = {command.get("commandName", "") for command in self.commands}
            bundledCommands = self.readConfigFile(self.bundledConfigPath).get("commands", [])
            for command in bundledCommands:
                if command.get("commandName", "") not in knownNames:
                    self.commands.append(command)

    # Assign every command's shortcut to its QAction on the given main window
    def applyShortcuts(self, mainWindow):
        boundActionNames = {command.get("action", "") for command in self.commands
                            if command.get("shortcut", "")}
        for command in self.commands:
            actionName = command.get("action", "")
            action = getattr(mainWindow, actionName, None)
            if action is None:
                continue
            shortcut = command.get("shortcut", "")
            # An alias only entry must never wipe a binding another entry gives the same action
            if not shortcut and actionName in boundActionNames:
                continue
            action.setShortcut(QKeySequence(shortcut))

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
