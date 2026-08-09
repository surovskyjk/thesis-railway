# Frameless floating HUD widget for AutoCAD-style command entry near the cursor
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QFrame, QLabel, QLineEdit, QVBoxLayout


class FloatingCommandInput(QFrame):
    commandSubmitted = Signal(str)
    inputCancelled = Signal()

    def __init__(self, shortcutManager, parent=None):
        super().__init__(parent, Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
                          | Qt.WindowType.WindowStaysOnTopHint)
        self.shortcutManager = shortcutManager
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setStyleSheet("FloatingCommandInput { background: palette(window);"
                           " border: 1px solid palette(mid); border-radius: 4px; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(2)

        self.inputField = QLineEdit()
        self.inputField.setMinimumWidth(140)
        self.inputField.textChanged.connect(self.onTextChanged)
        self.inputField.installEventFilter(self)
        layout.addWidget(self.inputField)

        self.hintLabel = QLabel()
        self.hintLabel.setStyleSheet("color: palette(mid); font-size: 10px;")
        layout.addWidget(self.hintLabel)

    # Show the HUD at the given global position and seed it with the first typed character
    def openAt(self, globalPosition, initialText):
        self.move(globalPosition)
        self.hintLabel.clear()
        self.inputField.setText(initialText)
        self.show()
        self.raise_()
        self.inputField.setFocus(Qt.FocusReason.PopupFocusReason)
        self.inputField.end(False)

    # Refresh the ghost hint label with the top autocomplete match for the typed text
    def onTextChanged(self, typedText):
        bestMatch = self.shortcutManager.findBestMatch(typedText)
        if bestMatch is None:
            self.hintLabel.clear()
        else:
            self.hintLabel.setText(f'{bestMatch.get("commandName", "")} ({bestMatch.get("alias", "")})')

    # Catch Enter to submit, Escape to cancel, and losing focus to dismiss the HUD
    def eventFilter(self, watched, event):
        if watched is self.inputField:
            if event.type() == QEvent.Type.KeyPress:
                if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                    self.commandSubmitted.emit(self.inputField.text())
                    self.hide()
                    return True
                if event.key() == Qt.Key.Key_Escape:
                    self.inputCancelled.emit()
                    self.hide()
                    return True
            if event.type() == QEvent.Type.FocusOut:
                self.hide()
        return super().eventFilter(watched, event)
