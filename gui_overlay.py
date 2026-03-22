from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QCheckBox, QLabel, QListWidget, QListWidgetItem, QFormLayout, QLineEdit
from PySide6.QtCore import Qt


class TTPSelectSectionDialog(QDialog):
    def __init__(self, sections, HasLandXML, lan, parent=None):
        super().__init__(parent)

        # Set up the dialog layout
        self.setWindowTitle(lan["select_sections_for_ttp_title"])
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        layout = QVBoxLayout()

        # Load all checkbox
        self.loadAllCheckBox = QCheckBox(lan["load_all"])
        self.loadAllCheckBox.setChecked(False)
        self.loadAllCheckBox.toggled.connect(self.toggleListWidget)
        layout.addWidget(self.loadAllCheckBox)

        # Sections selector - list widget
        layout.addWidget(QLabel(lan["select_sections_for_ttp_description"]))
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QListWidget.SelectionMode.MultiSelection)

        # Populate the list widget with sections
        for id, section in enumerate(sections):
            item = QListWidgetItem(section)
            item.setData(Qt.ItemDataRole.UserRole, id)
            self.listWidget.addItem(item)
        layout.addWidget(self.listWidget)
        
        # Crop the sections if LandXML data is available and successfully loaded
        self.LandXMLCheckBox = QCheckBox(lan["crop_to_landxml"])
        if not HasLandXML:
            self.LandXMLCheckBox.setEnabled(False)
            self.LandXMLCheckBox.setChecked(False)
        layout.addWidget(self.LandXMLCheckBox)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def toggleListWidget(self, checked):
        self.listWidget.setEnabled(not checked)

    def get_selected_section(self):
        selected = self.listWidget.selectedItems()
        selectedIds = [item.data(Qt.ItemDataRole.UserRole) for item in selected]
        
        return selectedIds, self.LandXMLCheckBox.isChecked(), self.loadAllCheckBox.isChecked()


class MapSettingsDialog(QDialog):
    def __init__(self, currentEPSG, lan, parent=None):
        super().__init__(parent)

        self.setWindowTitle(lan["mapSettings"])

        layout = QVBoxLayout(self)
        formLayout = QFormLayout()

        displayValue = currentEPSG
        self.inputEPSG = QLineEdit(displayValue)

        formLayout.addRow(QLabel(lan["currentEPSG"]), self.inputEPSG)
        layout.addLayout(formLayout)

        label = QLabel(lan["EPSGinfo"])
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def getEPSG(self):

        epsg = self.inputEPSG.text().strip().upper()

        if not epsg.startswith("EPSG:"):
            return f"EPSG:{epsg}"
        else:
            return epsg