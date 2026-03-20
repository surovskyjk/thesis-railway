from PySide6.QtWidgets import QDialog, QVBoxLayout, QDialogButtonBox, QCheckBox, QLabel, QComboBox, QFormLayout, QLineEdit

class TTPSelectSectionDialog(QDialog):
    def __init__(self, sections, HasLandXML, lan, parent=None):
        super().__init__(parent)

        # Set up the dialog layout
        self.setWindowTitle(lan["select_sections_for_ttp_title"])
        self.setMinimumWidth(400)
        self.setMinimumHeight(300)
        layout = QVBoxLayout()
        layout.addWidget(QLabel(lan["select_sections_for_ttp_description"]))
        self.combobox = QComboBox()

        # Populate the combo box with sections
        for id, section in enumerate(sections):
            self.combobox.addItem(section, userData=id)
        layout.addWidget(self.combobox)
        
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

    def get_selected_section(self):
        return self.combobox.currentData(), self.LandXMLCheckBox.isChecked()

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