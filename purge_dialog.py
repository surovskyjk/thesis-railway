# Granular purge dialog: segment manager plus calculation, stops and complete reset scopes
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QGroupBox, QHeaderView,
                               QMessageBox, QPushButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout)

from source_stack import LANDXML_KIND, TTP_KIND


class PurgeDataDialog(QDialog):
    def __init__(self, sourceStack, lan, parent=None):
        super().__init__(parent)
        self.lan = lan
        self.sourceStack = sourceStack
        self.removedSourceIds = set()

        self.setWindowTitle(lan.get("purgeTitle", "Purge Data"))
        self.setMinimumSize(560, 480)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        sourcesGroup = QGroupBox(lan.get("purgeSources", "Loaded segments"))
        sourcesLayout = QVBoxLayout(sourcesGroup)

        self.sourceTree = QTreeWidget()
        self.sourceTree.setColumnCount(2)
        self.sourceTree.setHeaderLabels([lan.get("purgeFileColumn", "File"),
                                         lan.get("purgeChainageRange", "Chainage range")])
        self.sourceTree.header().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.sourceTree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        sourcesLayout.addWidget(self.sourceTree)

        self.btnRemoveSelected = QPushButton(lan.get("purgeRemoveSelected", "Remove selected"))
        self.btnRemoveSelected.clicked.connect(self.removeSelected)
        sourcesLayout.addWidget(self.btnRemoveSelected)
        layout.addWidget(sourcesGroup, 1)

        scopesGroup = QGroupBox(lan.get("purgeScopesGroup", "Additional purge scopes"))
        scopesLayout = QVBoxLayout(scopesGroup)
        self.checkResults = QCheckBox(lan.get("purgeResults", "Calculation results (speed profiles, GPK)"))
        self.checkStops = QCheckBox(lan.get("purgeStops", "Stations / stops"))
        self.checkCompleteReset = QCheckBox(lan.get("purgeCompleteReset", "Complete reset (entire project)"))
        self.checkCompleteReset.toggled.connect(self.onCompleteResetToggled)
        scopesLayout.addWidget(self.checkResults)
        scopesLayout.addWidget(self.checkStops)
        scopesLayout.addWidget(self.checkCompleteReset)
        layout.addWidget(scopesGroup)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                          | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.onAccept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.populateTree()

    # Rebuild the segment tree from the current source stack contents
    def populateTree(self):
        self.sourceTree.clear()

        landXmlRoot = QTreeWidgetItem([self.lan.get("purgeSegmentLandXML", "LandXML"), ""])
        for entry in self.sourceStack.entriesForKind(LANDXML_KIND):
            self.addSourceItem(landXmlRoot, entry)
        self.sourceTree.addTopLevelItem(landXmlRoot)

        ttpRoot = QTreeWidgetItem([self.lan.get("purgeSegmentTTP", "TTP"), ""])
        for entry in self.sourceStack.entriesForKind(TTP_KIND):
            self.addSourceItem(ttpRoot, entry)
        self.sourceTree.addTopLevelItem(ttpRoot)

        self.sourceTree.expandAll()

    # Append one leaf row for a source stack entry, carrying its id for removal
    def addSourceItem(self, parentItem, entry):
        child = QTreeWidgetItem([entry.fileName, f"{entry.stationStart:.3f} - {entry.stationEnd:.3f} km"])
        child.setData(0, Qt.ItemDataRole.UserRole, entry.sourceId)
        parentItem.addChild(child)

    # Mark every selected leaf row for removal and drop it from the tree
    def removeSelected(self):
        for item in self.sourceTree.selectedItems():
            sourceId = item.data(0, Qt.ItemDataRole.UserRole)
            if sourceId is None:
                continue
            self.removedSourceIds.add(sourceId)
            parentItem = item.parent()
            if parentItem is not None:
                parentItem.removeChild(item)

    # A complete reset makes every other scope redundant, disable them while it is checked
    def onCompleteResetToggled(self, isChecked):
        self.sourceTree.setEnabled(not isChecked)
        self.btnRemoveSelected.setEnabled(not isChecked)
        self.checkResults.setEnabled(not isChecked)
        self.checkStops.setEnabled(not isChecked)

    # Confirm before accepting a complete reset, every other scope needs no extra confirmation
    def onAccept(self):
        if self.checkCompleteReset.isChecked():
            answer = QMessageBox.question(
                self, self.lan.get("purgeCompleteReset", "Complete reset"),
                self.lan.get("purgeConfirm", "This clears the entire project. Are you sure?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.accept()

    # Descriptor consumed by MainWindow to actually perform the requested purge
    def getPurgeRequest(self):
        return {
            "removedSourceIds": set(self.removedSourceIds),
            "purgeResults": self.checkResults.isChecked(),
            "purgeStops": self.checkStops.isChecked(),
            "completeReset": self.checkCompleteReset.isChecked(),
        }
