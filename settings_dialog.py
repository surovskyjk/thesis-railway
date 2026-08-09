# Dialog for viewing and editing command names, aliases, keyboard shortcuts and the floating HUD toggle
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                               QHeaderView, QDialogButtonBox, QMessageBox, QKeySequenceEdit,
                               QCheckBox)

COLUMN_COMMAND = 0
COLUMN_ALIAS = 1
COLUMN_SHORTCUT = 2


class ShortcutSettingsDialog(QDialog):
    def __init__(self, commands, floatingInputEnabled, lan, parent=None):
        super().__init__(parent)
        self.lan = lan
        self.setWindowTitle(lan.get("shortcutSettings", "Shortcuts"))
        self.setMinimumSize(520, 400)

        layout = QVBoxLayout(self)

        self.table = QTableWidget(len(commands), 3)
        self.table.setHorizontalHeaderLabels([
            lan.get("shortcutCommand", "Command"),
            lan.get("shortcutAlias", "Alias"),
            lan.get("shortcutKey", "Shortcut"),
        ])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.populateTable(commands)
        layout.addWidget(self.table)

        self.floatingInputCheckBox = QCheckBox(
            lan.get("floatingInputToggle", "Enable Dynamic Floating Command Input (AutoCAD Style)"))
        self.floatingInputCheckBox.setChecked(floatingInputEnabled)
        layout.addWidget(self.floatingInputCheckBox)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.validateAndAccept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    # Fill the table with one row per command, the command name column stays read only
    def populateTable(self, commands):
        for row, command in enumerate(commands):
            nameItem = QTableWidgetItem(command.get("commandName", ""))
            nameItem.setFlags(nameItem.flags() & ~Qt.ItemFlag.ItemIsEditable)
            nameItem.setData(Qt.ItemDataRole.UserRole, command.get("action", ""))
            self.table.setItem(row, COLUMN_COMMAND, nameItem)
            self.table.setItem(row, COLUMN_ALIAS, QTableWidgetItem(command.get("alias", "")))
            keyEditor = QKeySequenceEdit(QKeySequence(command.get("shortcut", "")))
            self.table.setCellWidget(row, COLUMN_SHORTCUT, keyEditor)

    # Reject silently-conflicting edits before accepting, otherwise close the dialog
    def validateAndAccept(self):
        commands = self.getCommands()
        aliases = [command["alias"].lower() for command in commands if command["alias"]]
        shortcuts = [command["shortcut"] for command in commands if command["shortcut"]]

        if len(aliases) != len(set(aliases)):
            QMessageBox.warning(self, self.lan.get("error", "Error"),
                                self.lan.get("shortcutDuplicateAlias", "Duplicate alias found."))
            return
        if len(shortcuts) != len(set(shortcuts)):
            QMessageBox.warning(self, self.lan.get("error", "Error"),
                                self.lan.get("shortcutDuplicateKey", "Duplicate shortcut found."))
            return
        self.accept()

    # Read the edited command list back out of the table
    def getCommands(self):
        commands = []
        for row in range(self.table.rowCount()):
            nameItem = self.table.item(row, COLUMN_COMMAND)
            aliasItem = self.table.item(row, COLUMN_ALIAS)
            keyEditor = self.table.cellWidget(row, COLUMN_SHORTCUT)
            commands.append({
                "commandName": nameItem.text(),
                "action": nameItem.data(Qt.ItemDataRole.UserRole),
                "alias": aliasItem.text().strip(),
                "shortcut": keyEditor.keySequence().toString(),
            })
        return commands

    # Whether the floating HUD command input checkbox is checked
    def isFloatingInputEnabled(self):
        return self.floatingInputCheckBox.isChecked()
