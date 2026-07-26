# Interactive seven step workflow guide shown as a dockable panel
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QFrame, QLabel, QPushButton, QScrollArea, QSizePolicy,
                               QVBoxLayout, QWidget)

# Ordered identifiers of the workflow steps, used as language dictionary keys
STEP_KEYS = [
    "workflowStep1",
    "workflowStep2",
    "workflowStep3",
    "workflowStep4",
    "workflowStep5",
    "workflowStep6",
    "workflowStep7",
]


class WorkflowStepperWidget(QWidget):
    # Emitted with the zero based index of the step the user clicked
    stepTriggered = Signal(int)

    def __init__(self, lan, parent=None):
        super().__init__(parent)

        self.completedSteps = set()
        self.stepButtons = []
        self.isDark = False

        outerLayout = QVBoxLayout(self)
        outerLayout.setContentsMargins(0, 0, 0, 0)
        outerLayout.setSpacing(0)

        scrollArea = QScrollArea()
        scrollArea.setWidgetResizable(True)
        scrollArea.setFrameShape(QFrame.Shape.NoFrame)

        contentWidget = QWidget()
        self.contentLayout = QVBoxLayout(contentWidget)
        self.contentLayout.setContentsMargins(8, 8, 8, 8)
        self.contentLayout.setSpacing(6)

        self.headerLabel = QLabel(lan.get("workflowTitle", "Workflow"))
        self.headerLabel.setStyleSheet("font-weight: 700; padding-bottom: 4px;")
        self.contentLayout.addWidget(self.headerLabel)

        # Every step stays enabled so any action can be retriggered at any time
        for stepIndex, stepKey in enumerate(STEP_KEYS):
            button = QPushButton(self.buildLabel(stepIndex, lan.get(stepKey, stepKey)))
            button.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
            button.setMinimumHeight(34)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.clicked.connect(lambda checked=False, index=stepIndex: self.stepTriggered.emit(index))
            self.contentLayout.addWidget(button)
            self.stepButtons.append(button)

        self.contentLayout.addStretch(1)
        scrollArea.setWidget(contentWidget)
        outerLayout.addWidget(scrollArea)

        self.applyTheme(False)

    # Compose the visible caption of a step button
    def buildLabel(self, stepIndex, stepText):
        return f"{stepIndex + 1}.  {stepText}"

    # Refresh all captions after a language change
    def updateTexts(self, lan):
        self.headerLabel.setText(lan.get("workflowTitle", "Workflow"))
        for stepIndex, stepKey in enumerate(STEP_KEYS):
            self.stepButtons[stepIndex].setText(
                self.buildLabel(stepIndex, lan.get(stepKey, stepKey)))

    # Mark a step as completed and repaint it in the accent colour
    def markCompleted(self, stepIndex):
        self.completedSteps.add(stepIndex)
        self.restyleButtons()

    # Clear the completed state of a single step
    def markPending(self, stepIndex):
        self.completedSteps.discard(stepIndex)
        self.restyleButtons()

    # Reset every step back to pending, used by the clean actions
    def resetAll(self):
        self.completedSteps.clear()
        self.restyleButtons()

    # Store the active theme and repaint the step buttons
    def applyTheme(self, isDark, tokens=None):
        self.isDark = isDark
        self.tokens = tokens
        self.restyleButtons()

    # Apply the pending or completed stylesheet to each step button
    def restyleButtons(self):
        tokens = getattr(self, "tokens", None)
        if tokens:
            doneBorder = tokens["accentDone"]
            doneBackground = tokens["accentDoneBackground"]
            textColor = tokens["text"]
            idleBorder = tokens["border"]
            idleBackground = tokens["button"]
        else:
            doneBorder = "#2e9e4f"
            doneBackground = "#dff3e4"
            textColor = "#1c1c1c"
            idleBorder = "#c4c4c4"
            idleBackground = "#ececec"

        for stepIndex, button in enumerate(self.stepButtons):
            if stepIndex in self.completedSteps:
                button.setStyleSheet(
                    f"QPushButton {{ text-align: left; padding-left: 10px;"
                    f" border: 2px solid {doneBorder}; border-radius: 4px;"
                    f" background: {doneBackground}; color: {textColor}; font-weight: 600; }}"
                    f"QPushButton:hover {{ border: 2px solid {doneBorder}; }}")
            else:
                button.setStyleSheet(
                    f"QPushButton {{ text-align: left; padding-left: 10px;"
                    f" border: 1px solid {idleBorder}; border-radius: 4px;"
                    f" background: {idleBackground}; color: {textColor}; }}"
                    f"QPushButton:hover {{ border: 1px solid {doneBorder}; }}")
