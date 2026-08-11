# Modal progress dialog shown while a batch of variants runs and while the archive is packaged
from PySide6.QtCore import Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPlainTextEdit, QDialogButtonBox


class BatchProgressDialog(QDialog):
    cancelRequested = Signal()

    def __init__(self, lan, parent=None):
        super().__init__(parent)
        self.lan = lan or {}
        self.isFinished = False

        self.setWindowTitle(self.lan.get("batchProgressTitle", "Batch processing"))
        self.setMinimumSize(480, 320)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        self.phaseLabel = QLabel(self.lan.get("batchProgressGeometry", "Calculating variants..."))
        layout.addWidget(self.phaseLabel)

        self.progressBar = QProgressBar()
        self.progressBar.setMinimum(0)
        self.progressBar.setValue(0)
        layout.addWidget(self.progressBar)

        self.logView = QPlainTextEdit()
        self.logView.setReadOnly(True)
        layout.addWidget(self.logView, 1)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.cancelButton = self.buttonBox.button(QDialogButtonBox.StandardButton.Cancel)
        self.cancelButton.clicked.connect(self.onCancelClicked)
        layout.addWidget(self.buttonBox)

    # Switch the caption above the progress bar, used to move from calculating to packaging
    def setPhase(self, phaseText):
        self.phaseLabel.setText(phaseText)

    # Reset the bar to run from zero to the given number of variants
    def setVariantCount(self, count):
        self.progressBar.setMaximum(max(count, 1))
        self.progressBar.setValue(0)

    # Advance the bar and log one completed variant
    def advance(self, index, label):
        self.progressBar.setValue(index + 1)
        self.appendLog(f"[{index + 1}/{self.progressBar.maximum()}] {label}")

    # Append one line to the running log without clearing prior entries
    def appendLog(self, text):
        self.logView.appendPlainText(text)

    # Switch the dialog into its terminal state, Cancel becomes Close
    def finish(self, summaryText):
        self.isFinished = True
        self.phaseLabel.setText(summaryText)
        self.progressBar.setValue(self.progressBar.maximum())
        self.cancelButton.setText(self.lan.get("dialogClose", "Close"))
        self.cancelButton.clicked.disconnect(self.onCancelClicked)
        self.cancelButton.clicked.connect(self.accept)

    # The engines cannot be interrupted mid-variant, so make that limitation visible immediately
    def onCancelClicked(self):
        self.cancelButton.setEnabled(False)
        self.cancelButton.setText(self.lan.get("batchCancelling", "Finishing current variant..."))
        self.cancelRequested.emit()

    # Treat the window's own close button the same as pressing Cancel while a batch is still running
    def closeEvent(self, event):
        if not self.isFinished:
            self.cancelRequested.emit()
        super().closeEvent(event)
