from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QDialogButtonBox, QCheckBox, QLabel, 
                               QListWidget, QListWidgetItem, QFormLayout, 
                               QLineEdit, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QFileDialog, QMessageBox, 
                               QDialogButtonBox, QPushButton, QComboBox,
                               QTabWidget, QWidget)
from PySide6.QtCore import Qt

import csv
import readfile
import io
import default_values

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

class AlignmentSelectDialog(QDialog):
    def __init__(self, alignments, lan, parent=None):
        super().__init__(parent)
        self.setWindowTitle(lan.get("select_alignment_title", "Select Alignment"))
        self.setMinimumWidth(300)
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel(lan.get("select_alignment_description", "Select the alignment to load:")))
        
        self.listWidget = QListWidget()
        self.listWidget.setSelectionMode(QListWidget.SelectionMode.SingleSelection)
        
        for id, alig_name in enumerate(alignments):
            item = QListWidgetItem(f"{alig_name}")
            item.setData(Qt.ItemDataRole.UserRole, id)
            self.listWidget.addItem(item)
            
        if self.listWidget.count() > 0:
            self.listWidget.setCurrentRow(0)
            
        layout.addWidget(self.listWidget)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)
        
    def get_selected_index(self):
        selected = self.listWidget.selectedItems()
        if selected:
            return selected[0].data(Qt.ItemDataRole.UserRole)
        return 0

class MapSettingsDialog(QDialog):
    def __init__(self, currentEPSG, currentMap, currentDrawMode, currentSpeedProfile, lan, parent=None):
        super().__init__(parent)
        self.lan = lan
        self.setWindowTitle(lan["mapSettings"])

        layout = QVBoxLayout(self)
        formLayout = QFormLayout()

        displayValue = currentEPSG
        self.inputEPSG = QLineEdit(displayValue)
        formLayout.addRow(QLabel(lan["currentEPSG"]), self.inputEPSG)
        
        self.comboMap = QComboBox()
        self.comboMap.addItem(lan.get("mapPositron", "CartoDB Positron"), "positron")
        self.comboMap.addItem(lan.get("mapOSM", "OpenStreetMap"), "osm")
        self.comboMap.addItem(lan.get("mapORM", "OpenRailwayMap"), "orm")
        self.comboMap.addItem(lan.get("mapCUZK", "ČÚZK Ortofoto"), "cuzk")
        index = self.comboMap.findData(currentMap)
        if index >= 0: self.comboMap.setCurrentIndex(index)
        formLayout.addRow(QLabel(lan.get("mapBase", "Map Base:")), self.comboMap)

        self.comboDrawMode = QComboBox()
        self.comboDrawMode.addItem(lan.get("mapDrawSingleColor", "Single Color"), "single")
        self.comboDrawMode.addItem(lan.get("mapDrawByType", "By Element Type"), "type")
        self.comboDrawMode.addItem(lan.get("mapDrawBySpeed", "By Speed Limit"), "speed")
        index = self.comboDrawMode.findData(currentDrawMode)
        if index >= 0: self.comboDrawMode.setCurrentIndex(index)
        formLayout.addRow(QLabel(lan.get("mapDrawMode", "Draw Mode:")), self.comboDrawMode)

        self.labelSpeedProfile = QLabel(lan.get("mapSpeedProfile", "Speed Profile for Map:"))
        self.comboSpeedProfile = QComboBox()
        self.profiles = [("V100", "100"), ("V130", "130"), ("V150", "150"), ("VK", "K")]
        for text, data in self.profiles:
            self.comboSpeedProfile.addItem(text, data)
        index = self.comboSpeedProfile.findData(currentSpeedProfile)
        if index >= 0: self.comboSpeedProfile.setCurrentIndex(index)
        formLayout.addRow(self.labelSpeedProfile, self.comboSpeedProfile)
        
        self.comboDrawMode.currentTextChanged.connect(self.updateSpeedProfileVisibility)
        self.updateSpeedProfileVisibility()

        layout.addLayout(formLayout)
        label = QLabel(lan["EPSGinfo"])
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def updateSpeedProfileVisibility(self):
        is_speed_mode = self.comboDrawMode.currentData() == "speed"
        self.labelSpeedProfile.setVisible(is_speed_mode)
        self.comboSpeedProfile.setVisible(is_speed_mode)

    def getMapSettings(self):
        epsg = self.inputEPSG.text().strip().upper()

        if not epsg.startswith("EPSG:"):
            epsg = f"EPSG:{epsg}"
            
        return epsg, self.comboMap.currentData(), self.comboDrawMode.currentData(), self.comboSpeedProfile.currentData()
        
class HelpDialog(QDialog):
    def __init__(self, lan, parent=None):
        super().__init__(parent)

        self.setWindowTitle(lan["help"])

        layout = QVBoxLayout(self)
        label = QLabel(lan["help_text"])
        layout.addWidget(label)

class GeometrySettingsDialog(QDialog):
    def __init__(self, settingsData, lan, parent=None):
        super().__init__(parent)
        self.settingsData = settingsData

        self.setWindowTitle(lan["geometrySettings"])
        self.setMinimumSize(600,400)

        layout = QVBoxLayout(self)

        formLayout = QFormLayout()
        current_max_d = self.settingsData.get("maxD", 150.0)
        if isinstance(current_max_d, list):
            current_max_d = current_max_d[0]
            
        self.inputMaxD = QLineEdit(str(current_max_d))
        formLayout.addRow(QLabel(lan.get("max_cant", "Maximum cant D_max [mm]:")), self.inputMaxD)
        
        current_v_init = self.settingsData.get("vInit", [120.0])
        if isinstance(current_v_init, list): current_v_init = current_v_init[0]
        self.inputVInit = QLineEdit(str(current_v_init))
        formLayout.addRow(QLabel(lan.get("vInitLabel", "Initial Speed v_init [km/h]:")), self.inputVInit)

        current_iter_step = self.settingsData.get("iterationStep", 5.0)
        self.inputIterStep = QLineEdit(str(current_iter_step))
        formLayout.addRow(QLabel(lan.get("iterationStepLabel", "Iteration speed reduction step [km/h]:")), self.inputIterStep)

        current_max_iter = self.settingsData.get("maxIterations", 50)
        self.inputMaxIter = QLineEdit(str(current_max_iter))
        formLayout.addRow(QLabel(lan.get("maxIterationsLabel", "Maximum number of iterations [-]:")), self.inputMaxIter)

        layout.addLayout(formLayout)

        labelI = QLabel(lan["cant_def"])
        layout.addWidget(labelI)
        
        # Table for editing settings and thresholds for cant deficiency
        self.tableI = QTableWidget(0, 5)
        self.tableI.setHorizontalHeaderLabels([
            lan["Vbottom"],
            lan["Vtop"],
            lan["I_std"],
            lan["I_lim"],
            lan["I_max"]
        ])

        headerI = self.tableI.horizontalHeader()
        headerI.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableI)

        # Default values for I according to the Czech standard
        defaultCZI = self.settingsData.get("I", default_values.defVal["I"])

        self.populateTable(self.tableI, defaultCZI)

        # Table for editing settings and thresholds for abrupt change of cant deficiency
        labelDI = QLabel(lan["abrupt_cant_def"])
        layout.addWidget(labelDI)

        self.tableDI = QTableWidget(0, 5)
        self.tableDI.setHorizontalHeaderLabels([
            lan["Vbottom"],
            lan["Vtop"],
            lan["dI_std"],
            lan["dI_lim"],
            lan["dI_max"]
        ])

        headerDI = self.tableDI.horizontalHeader()
        headerDI.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableDI)

        # Default values for dI according to the Czech standard
        defaultCZDI = self.settingsData.get("dI", default_values.defVal["dI"])

        self.populateTable(self.tableDI, defaultCZDI)

        # Table for editing settings and thresholds for cant ramp gradient
        labelNlin = QLabel(lan["nLin"])
        layout.addWidget(labelNlin)

        self.tableNlin = QTableWidget(0, 8)
        self.tableNlin.setHorizontalHeaderLabels([
            lan["Vbottom"],
            lan["Vtop"],
            lan["n_n"],
            lan["n_n_abs"],
            lan["n_lim"],
            lan["n_lim_abs"],
            lan["n_min"],
            lan["n_min_abs"]
        ])

        headerNlin = self.tableNlin.horizontalHeader()
        headerNlin.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableNlin)

        # Default values for nLin according to the Czech standard
        defaultCZnLin = self.settingsData.get("nLin", default_values.defVal["nLin"])

        self.populateTable(self.tableNlin, defaultCZnLin)

        # Table for editing settings and thresholds for cant deficiency gradient
        labelNIlin = QLabel(lan["nILin"])
        layout.addWidget(labelNIlin)

        self.tableNIlin = QTableWidget(0, 5)
        self.tableNIlin.setHorizontalHeaderLabels([
            lan["Vbottom"],
            lan["Vtop"],
            lan["nI_n"],
            lan["nI_lim"],
            lan["nI_min"],
        ])

        headerNIlin = self.tableNIlin.horizontalHeader()
        headerNIlin.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableNIlin)

        # Default values for nILin according to the Czech standard
        defaultCZnILin = self.settingsData.get("nILin", default_values.defVal["nILin"])

        self.populateTable(self.tableNIlin, defaultCZnILin)

        toolbarLayoutGeometry = QHBoxLayout()
        
        self.btnImportGeometry = QPushButton(lan["importCSV"])
        self.btnImportGeometry.clicked.connect(self.importGeometryCSV)
        toolbarLayoutGeometry.addWidget(self.btnImportGeometry)
        
        self.btnExportGeometry = QPushButton(lan["exportCSV"])
        self.btnExportGeometry.clicked.connect(self.exportGeometryCSV)
        toolbarLayoutGeometry.addWidget(self.btnExportGeometry)
        
        layout.addLayout(toolbarLayoutGeometry)

        # Buttons for the whole dialog
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def populateTable(self, tableWidget, data):
        tableWidget.setRowCount(len(data))
        for row, rowData in enumerate(data):
            for col, value in enumerate(rowData):
                item = QTableWidgetItem(str(value))
                tableWidget.setItem(row, col, item)

    def importGeometryCSV(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        
        # If cancelled, do nothing
        if not filepath:
            return
        
        # Read file content 
        file_content = readfile.ReadFile().Read(filepath)
        
        if file_content.startswith("Error"):
            err = QMessageBox()
            err.setWindowTitle("Error")
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return
        
        try:
            # Reads CSV file content
            reader = csv.reader(io.StringIO(file_content), delimiter=',')
            # Skips header
            next(reader, None)

            i_data = []
            di_data = []
            nlin_data = []
            nilin_data = []

            for row in reader:
                if not row:
                    continue
                section = row[0]
                if section == "I" and len(row) >= 6:
                    i_data.append(row[1:6])
                elif section == "DI" and len(row) >= 6:
                    di_data.append(row[1:6])
                elif section == "nLin" and len(row) >= 9:
                    nlin_data.append(row[1:9])
                elif section == "nILin" and len(row) >= 6:
                    nilin_data.append(row[1:6])

            if i_data: self.populateTable(self.tableI, i_data)
            if di_data: self.populateTable(self.tableDI, di_data)
            if nlin_data: self.populateTable(self.tableNlin, nlin_data)
            if nilin_data: self.populateTable(self.tableNIlin, nilin_data)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        
    def exportGeometryCSV(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        
        # If cancelled, do nothing
        if not filepath:
            return
        
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                headers = ["Section", "Col1", "Col2", "Col3", "Col4", "Col5", "Col6", "Col7", "Col8"]
                writer.writerow(headers)

                for row in range(self.tableI.rowCount()):
                    rowData = ["I"] + [self.tableI.item(row, col).text() if self.tableI.item(row, col) else "" for col in range(self.tableI.columnCount())]
                    writer.writerow(rowData)

                for row in range(self.tableDI.rowCount()):
                    rowData = ["DI"] + [self.tableDI.item(row, col).text() if self.tableDI.item(row, col) else "" for col in range(self.tableDI.columnCount())]
                    writer.writerow(rowData)

                for row in range(self.tableNlin.rowCount()):
                    rowData = ["nLin"] + [self.tableNlin.item(row, col).text() if self.tableNlin.item(row, col) else "" for col in range(self.tableNlin.columnCount())]
                    writer.writerow(rowData)

                for row in range(self.tableNIlin.rowCount()):
                    rowData = ["nILin"] + [self.tableNIlin.item(row, col).text() if self.tableNIlin.item(row, col) else "" for col in range(self.tableNIlin.columnCount())]
                    writer.writerow(rowData)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        
    def getSettings(self):
        settingsData = {
            "I": [],
            "dI": [],
            "nLin": [],
            "nILin": [],
        }

        try:
            settingsData["maxD"] = float(self.inputMaxD.text())
        except ValueError:
            settingsData["maxD"] = 150.0
            
        try:
            settingsData["vInit"] = [float(self.inputVInit.text())]
        except ValueError:
            settingsData["vInit"] = [120.0]

        try:
            settingsData["iterationStep"] = max(0.1, float(self.inputIterStep.text()))
        except ValueError:
            settingsData["iterationStep"] = 5.0

        try:
            settingsData["maxIterations"] = max(1, int(self.inputMaxIter.text()))
        except ValueError:
            settingsData["maxIterations"] = 50

        # Table I
        for row in range(self.tableI.rowCount()):
            try:
                settingsData["I"].append([
                    float(self.tableI.item(row, 0).text()),
                    float(self.tableI.item(row, 1).text()),
                    float(self.tableI.item(row, 2).text()),
                    float(self.tableI.item(row, 3).text()),
                    float(self.tableI.item(row, 4).text())
                ])

            except(ValueError, AttributeError):
                continue
        
        # Table dI
        for row in range(self.tableDI.rowCount()):
            try:
                settingsData["dI"].append([
                    float(self.tableDI.item(row, 0).text()),
                    float(self.tableDI.item(row, 1).text()),
                    float(self.tableDI.item(row, 2).text()),
                    float(self.tableDI.item(row, 3).text()),
                    float(self.tableDI.item(row, 4).text())
                ])

            except(ValueError, AttributeError):
                continue

        # Table nLin
        for row in range(self.tableNlin.rowCount()):
            try:
                settingsData["nLin"].append([
                    float(self.tableNlin.item(row, 0).text()),
                    float(self.tableNlin.item(row, 1).text()),
                    float(self.tableNlin.item(row, 2).text()),
                    float(self.tableNlin.item(row, 3).text()),
                    float(self.tableNlin.item(row, 4).text()),
                    float(self.tableNlin.item(row, 5).text()),
                    float(self.tableNlin.item(row, 6).text()),
                    float(self.tableNlin.item(row, 7).text())
                ])

            except(ValueError, AttributeError):
                continue
        
        # Table nILin
        for row in range(self.tableNIlin.rowCount()):
            try:
                settingsData["nILin"].append([
                    float(self.tableNIlin.item(row, 0).text()),
                    float(self.tableNIlin.item(row, 1).text()),
                    float(self.tableNIlin.item(row, 2).text()),
                    float(self.tableNIlin.item(row, 3).text()),
                    float(self.tableNIlin.item(row, 4).text()),
                ])

            except(ValueError, AttributeError):
                continue

        return settingsData
    
class DesignApproachDialog(QDialog):
    def __init__(self, settingsData, lan, parent=None):
        super().__init__(parent)
        self.lan = lan
        self.settingsData = settingsData
        
        self.setWindowTitle(lan["designApproach"])

        layout = QVBoxLayout(self)
        labelLimit = QLabel(lan["designApproachLimitDescription"])
        layout.addWidget(labelLimit)

        formLayout = QFormLayout()

        self.designApproach = self.settingsData.get("designApproach", {})
        if isinstance(self.designApproach, str):
            self.designApproach = {
                "I": self.designApproach,
                "dI": self.designApproach,
                "nLin": self.designApproach,
                "nILin": self.designApproach
            }

        self.comboboxes = {}
        parameters = [
            ("I", lan.get("cant_def", "cant deficiency I [mm]")),
            ("dI", lan.get("abrupt_cant_def", "abrupt change of cant deficiency deltaI [mm]")),
            ("nLin", lan.get("nLin", "cant ramp gradient n [-]")),
            ("nILin", lan.get("nILin", "Coefficient of cant deficiency change nI [-]"))
        ]

        for param_key, param_label in parameters:
            cb = QComboBox(self)
            cb.addItems([lan["standard"], lan["limit"], lan["minmax"]])
            
            current_val = self.designApproach.get(param_key, "standard")
            if current_val == "standard":
                cb.setCurrentText(lan["standard"])
            elif current_val == "limit":
                cb.setCurrentText(lan["limit"])
            elif current_val == "minmax":
                cb.setCurrentText(lan["minmax"])
                
            self.comboboxes[param_key] = cb
            formLayout.addRow(QLabel(param_label), cb)
            
        layout.addLayout(formLayout)

        # Buttons for the whole dialog
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def getDesignApproach(self):
        result = {}
        for param_key, cb in self.comboboxes.items():
            selected = cb.currentText()
            if selected == self.lan["standard"]:
                result[param_key] = "standard"
            elif selected == self.lan["limit"]:
                result[param_key] = "limit"
            elif selected == self.lan["minmax"]:
                result[param_key] = "minmax"
            else:
                result[param_key] = "standard"
        return result

class StopsSettingsDialog(QDialog):
    def __init__(self, settingsData, lan, parent=None):
        super().__init__(parent)
        self.settingsData = settingsData
        
        self.setWindowTitle(lan.get("stopsSettings", "Stops Settings"))
        self.setMinimumSize(400, 400)

        layout = QVBoxLayout(self)
        
        formLayout = QFormLayout()
        self.inputDwellTime = QLineEdit(str(self.settingsData.get("defaultDwellTime", 30.0)))
        formLayout.addRow(QLabel(lan.get("defaultDwellTime", "Default Dwell Time [s]:")), self.inputDwellTime)
        layout.addLayout(formLayout)

        labelStops = QLabel(lan.get("trainStops", "Train Stops"))
        layout.addWidget(labelStops)

        self.tableStops = QTableWidget(0, 3)
        self.tableStops.setHorizontalHeaderLabels([
            lan["station"],
            lan.get("dwellTimeTable", "Dwell Time [s]"),
            lan.get("stopName", "Stop Name")
        ])
        headerStops = self.tableStops.horizontalHeader()
        headerStops.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableStops)

        defaultStops = self.settingsData.get("trainStops", [])
        self.populateTable(self.tableStops, defaultStops)

        toolbarLayoutStops = QHBoxLayout()
        
        self.btnAddStop = QPushButton(lan.get("addRow", "Add Row"))
        self.btnAddStop.clicked.connect(self.addStopRow)
        toolbarLayoutStops.addWidget(self.btnAddStop)

        self.btnRemoveStop = QPushButton(lan.get("removeRow", "Remove Row"))
        self.btnRemoveStop.clicked.connect(self.removeStopRow)
        toolbarLayoutStops.addWidget(self.btnRemoveStop)

        self.btnImportStops = QPushButton(lan["importCSV"])
        self.btnImportStops.clicked.connect(lambda: self.importCSV("tableStops"))
        toolbarLayoutStops.addWidget(self.btnImportStops)

        self.btnExportStops = QPushButton(lan["exportCSV"])
        self.btnExportStops.clicked.connect(lambda: self.exportCSV("tableStops"))
        toolbarLayoutStops.addWidget(self.btnExportStops)

        layout.addLayout(toolbarLayoutStops)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def addStopRow(self):
        row = self.tableStops.rowCount()
        self.tableStops.insertRow(row)
        itemStation = QTableWidgetItem("")
        defaultDwell = self.inputDwellTime.text()
        itemDwell = QTableWidgetItem(defaultDwell)
        itemName = QTableWidgetItem("")
        self.tableStops.setItem(row, 0, itemStation)
        self.tableStops.setItem(row, 1, itemDwell)
        self.tableStops.setItem(row, 2, itemName)

    def removeStopRow(self):
        currentRow = self.tableStops.currentRow()
        if currentRow >= 0:
            self.tableStops.removeRow(currentRow)

    def populateTable(self, tableWidget, data):
        tableWidget.setRowCount(len(data))
        for row, rowData in enumerate(data):
            for col, value in enumerate(rowData):
                item = QTableWidgetItem(str(value))
                tableWidget.setItem(row, col, item)

    def importCSV(self, table):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        if not filepath: return
        file_content = readfile.ReadFile().Read(filepath)
        if file_content.startswith("Error"):
            err = QMessageBox(); err.setWindowTitle("Error"); err.setIcon(QMessageBox.Icon.Warning); err.exec(); return
        try:
            reader = csv.reader(io.StringIO(file_content), delimiter=',')
            next(reader, None)
            data_list = list(reader)
            if table == "tableStops": self.populateTable(self.tableStops, data_list)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def exportCSV(self, table):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        if not filepath: return
        try:
            if table == "tableStops":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Station", "Dwell Time", "Name"])
                    for row in range(self.tableStops.rowCount()):
                        writer.writerow([self.tableStops.item(row, col).text() for col in range(self.tableStops.columnCount())])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def getSettings(self):
        settingsData = {"trainStops": []}
        try: settingsData["defaultDwellTime"] = float(self.inputDwellTime.text())
        except ValueError: pass
        for row in range(self.tableStops.rowCount()):
            try: 
                station = float(self.tableStops.item(row, 0).text())
                dwell = float(self.tableStops.item(row, 1).text())
                name_item = self.tableStops.item(row, 2)
                name = name_item.text() if name_item else ""
                settingsData["trainStops"].append([station, dwell, name])
            except (ValueError, AttributeError): 
                continue
        return settingsData

class SpeedSettingsDialog(QDialog):
    def __init__(self, settingsData, lan, parent=None):
        super().__init__(parent)
        self.settingsData = settingsData
        
        self.setWindowTitle(lan.get("speedSettings", "Speed Limits Settings"))
        self.setMinimumSize(400, 400)

        layout = QVBoxLayout(self)
        
        labelSpeeds = QLabel(lan.get("manualSpeedLimits", "Manual Speed Limits"))
        layout.addWidget(labelSpeeds)

        self.tableSpeeds = QTableWidget(0, 2)
        self.tableSpeeds.setHorizontalHeaderLabels([
            lan["station"],
            lan.get("speed_lim", "Speed Limit [km/h]")
        ])
        headerSpeeds = self.tableSpeeds.horizontalHeader()
        headerSpeeds.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableSpeeds)

        defaultSpeeds = self.settingsData.get("manualSpeedLimits", [])
        self.populateTable(self.tableSpeeds, defaultSpeeds)

        toolbarLayoutSpeeds = QHBoxLayout()
        
        self.btnAddSpeed = QPushButton(lan.get("addRow", "Add Row"))
        self.btnAddSpeed.clicked.connect(self.addSpeedRow)
        toolbarLayoutSpeeds.addWidget(self.btnAddSpeed)

        self.btnRemoveSpeed = QPushButton(lan.get("removeRow", "Remove Row"))
        self.btnRemoveSpeed.clicked.connect(self.removeSpeedRow)
        toolbarLayoutSpeeds.addWidget(self.btnRemoveSpeed)

        self.btnImportSpeeds = QPushButton(lan["importCSV"])
        self.btnImportSpeeds.clicked.connect(self.importSpeedsCSV)
        toolbarLayoutSpeeds.addWidget(self.btnImportSpeeds)

        self.btnExportSpeeds = QPushButton(lan["exportCSV"])
        self.btnExportSpeeds.clicked.connect(self.exportSpeedsCSV)
        toolbarLayoutSpeeds.addWidget(self.btnExportSpeeds)

        layout.addLayout(toolbarLayoutSpeeds)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def addSpeedRow(self):
        row = self.tableSpeeds.rowCount()
        self.tableSpeeds.insertRow(row)
        itemStation = QTableWidgetItem("")
        itemSpeed = QTableWidgetItem("")
        self.tableSpeeds.setItem(row, 0, itemStation)
        self.tableSpeeds.setItem(row, 1, itemSpeed)

    def removeSpeedRow(self):
        currentRow = self.tableSpeeds.currentRow()
        if currentRow >= 0:
            self.tableSpeeds.removeRow(currentRow)

    def populateTable(self, tableWidget, data):
        tableWidget.setRowCount(len(data))
        for row, rowData in enumerate(data):
            for col, value in enumerate(rowData):
                item = QTableWidgetItem(str(value))
                tableWidget.setItem(row, col, item)

    def importSpeedsCSV(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        if not filepath: return
        file_content = readfile.ReadFile().Read(filepath)
        if file_content.startswith("Error"):
            err = QMessageBox(); err.setWindowTitle("Error"); err.setIcon(QMessageBox.Icon.Warning); err.exec(); return
        try:
            reader = csv.reader(io.StringIO(file_content), delimiter=',')
            next(reader, None) # Skip header
            data_list = [row[:2] for row in reader] # Take only first two columns
            self.populateTable(self.tableSpeeds, data_list)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def exportSpeedsCSV(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        if not filepath: return
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                writer.writerow(["Station", "Speed"])
                for row in range(self.tableSpeeds.rowCount()):
                    writer.writerow([self.tableSpeeds.item(row, col).text() for col in range(self.tableSpeeds.columnCount())])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def getSettings(self):
        settingsData = {"manualSpeedLimits": []}
        for row in range(self.tableSpeeds.rowCount()):
            try: 
                station = float(self.tableSpeeds.item(row, 0).text())
                speed = float(self.tableSpeeds.item(row, 1).text())
                settingsData["manualSpeedLimits"].append([station, speed])
            except (ValueError, AttributeError): 
                continue
        # Sort by station
        settingsData["manualSpeedLimits"].sort(key=lambda x: x[0])
        return settingsData

class VehicleTab(QWidget):
    def __init__(self, v_data, lan, parent = None):
        super().__init__(parent)
        self.lan = lan
        self.v_data = v_data

        layout = QVBoxLayout(self)
        formLayout = QFormLayout()
        
        self.inputInitialSpeed = QLineEdit(str(self.v_data.get("trainInitialSpeed", 0.0)))
        formLayout.addRow(QLabel(lan.get("trainInitialSpeed", "Initial Speed [km/h]:")), self.inputInitialSpeed)

        self.inputFinalSpeed = QLineEdit(str(self.v_data.get("trainFinalSpeed", 0.0)))
        formLayout.addRow(QLabel(lan.get("trainFinalSpeed", "Final Speed [km/h]:")), self.inputFinalSpeed)

        self.checkReverse = QCheckBox(lan.get("runAgainstStationing", "Run against stationing"))
        self.checkReverse.setChecked(self.v_data.get("runReversed", False))
        formLayout.addRow(self.checkReverse)
        
        self.inputMaxSpeed = QLineEdit(str(self.v_data.get("trainMaxSpeed", 120.0)))
        
        self.comboProfile = QComboBox()
        self.profiles = [
            (lan.get("speed_lim_ttp", "TTP Speed Limits"), ["stationSpeedLimits", "speedLimits"]),
            (lan.get("speed_lim_100", "V100"), ["stationSpeed100", "speedLimits100"]),
            (lan.get("speed_lim_130", "V130"), ["stationSpeed130", "speedLimits130"]),
            (lan.get("speed_lim_150", "V150"), ["stationSpeed150", "speedLimits150"]),
            (lan.get("speed_lim_K", "VK"), ["stationSpeedK", "speedLimitsK"]),
            (lan.get("speed_lim_manual", "Manual Speed Limits"), ["manualSpeedLimits", "manualSpeedLimits"]),
            (lan.get("unlimited", "Unlimited"), ["unlimited", "unlimited"])
        ]
        
        for text, data in self.profiles:
            self.comboProfile.addItem(text, data)
            
        current_profile = self.v_data.get("speedLimitPlot", ["stationSpeed150", "speedLimits150"])
        for i, (text, data) in enumerate(self.profiles):
            if data == current_profile:
                self.comboProfile.setCurrentIndex(i)
                break

        formLayout.addRow(QLabel(lan.get("max_train_speed", "Max Train Speed [km/h]:")), self.inputMaxSpeed)
        
        self.inputBrakeDecel = QLineEdit(str(self.v_data.get("trainBrakeDecel", default_values.defVal.get("trainBrakeDecel", 1.0))))
        formLayout.addRow(QLabel(lan.get("vehicleBrakeDecel", "Braking Deceleration [m/s2]:")), self.inputBrakeDecel)

        formLayout.addRow(QLabel(lan.get("speed_profile", "Speed Profile:")), self.comboProfile)
        
        layout.addLayout(formLayout)

        toolbarLayoutVehicle = QHBoxLayout()
        self.btnImportVehicle = QPushButton(lan.get("importVehicleCSV", "Import full vehicle from CSV"))
        self.btnImportVehicle.clicked.connect(self.importVehicleCSV)
        toolbarLayoutVehicle.addWidget(self.btnImportVehicle)
        
        self.btnExportVehicle = QPushButton(lan.get("exportVehicleCSV", "Export full vehicle to CSV"))
        self.btnExportVehicle.clicked.connect(self.exportVehicleCSV)
        toolbarLayoutVehicle.addWidget(self.btnExportVehicle)
        
        layout.addLayout(toolbarLayoutVehicle)

        labelRes = QLabel(lan["vehicleResistance"])
        layout.addWidget(labelRes)
        
        # Table for editing train resistance coefficients
        self.tableRes = QTableWidget(0, 4)
        self.tableRes.setHorizontalHeaderLabels([
            lan["vehicle"],
            lan["coefA"],
            lan["coefB"],
            lan["coefC"]
        ])

        headerRes = self.tableRes.horizontalHeader()
        headerRes.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableRes)

        # Default values for train resistance coefficients
        defaultRes = self.v_data.get("trainRes", default_values.defVal.get("trainRes", []))

        self.populateTable(self.tableRes, defaultRes)

        labelTrac = QLabel(lan["vehicleTraction"])
        layout.addWidget(labelTrac)

        # Table for editing train traction coefficients
        self.tableTrac = QTableWidget(0, 6)
        self.tableTrac.setHorizontalHeaderLabels([
            lan["vehicle"],
            lan["Vbottom"],
            lan["Vtop"],
            lan["coef_b0"],
            lan["coef_b1"],
            lan["coef_b2"]
        ])

        headerTrac = self.tableTrac.horizontalHeader()
        headerTrac.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableTrac)

        # Default values for vehicle resistance
        defaultTrac = self.v_data.get("trainTrac", default_values.defVal.get("trainTrac", []))

        self.populateTable(self.tableTrac, defaultTrac)

        labelParam = QLabel(lan["vehicleParam"])
        layout.addWidget(labelParam)

        # Table for editing train parameters coefficients
        self.tableParam = QTableWidget(0, 4)
        self.tableParam.setHorizontalHeaderLabels([
            lan["vehicle"],
            lan["rotMass"],
            lan["weight"],
            lan.get("trainLength", "Train Length [m]")
        ])

        headerParam = self.tableParam.horizontalHeader()
        headerParam.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableParam)

        # Default values for train parameters
        defaultParam = self.v_data.get("trainParam", default_values.defVal.get("trainParam", []))
        
        # Ensure older saves have the 4th column (train length) initialized
        for rowData in defaultParam:
            if isinstance(rowData, list) and len(rowData) == 3:
                rowData.append(0.0)

        self.populateTable(self.tableParam, defaultParam)

    def populateTable(self, tableWidget, data):
        tableWidget.setRowCount(len(data))
        for row, rowData in enumerate(data):
            for col, value in enumerate(rowData):
                item = QTableWidgetItem(str(value))
                tableWidget.setItem(row, col, item)

    def importVehicleCSV(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open File", "", "CSV Files (*.csv)")
        if not filepath:
            return
        
        file_content = readfile.ReadFile().Read(filepath)
        if file_content.startswith("Error"):
            err = QMessageBox()
            err.setWindowTitle("Error")
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return
        
        try:
            reader = csv.reader(io.StringIO(file_content), delimiter=',')
            next(reader, None)

            res_data = []
            trac_data = []
            param_data = []

            for row in reader:
                if not row:
                    continue
                section = row[0]
                if section == "Res" and len(row) >= 5:
                    res_data.append(row[1:5])
                elif section == "Trac" and len(row) >= 7:
                    trac_data.append(row[1:7])
                elif section == "Param" and len(row) >= 5:
                    param_data.append(row[1:5])

            if res_data: self.populateTable(self.tableRes, res_data)
            if trac_data: self.populateTable(self.tableTrac, trac_data)
            if param_data: self.populateTable(self.tableParam, param_data)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return

    def exportVehicleCSV(self):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        if not filepath:
            return
        
        try:
            with open(filepath, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)
                headers = ["Section", "Col1", "Col2", "Col3", "Col4", "Col5", "Col6"]
                writer.writerow(headers)

                for row in range(self.tableParam.rowCount()):
                    rowData = ["Param"] + [self.tableParam.item(row, col).text() if self.tableParam.item(row, col) else "" for col in range(self.tableParam.columnCount())]
                    writer.writerow(rowData)

                for row in range(self.tableRes.rowCount()):
                    rowData = ["Res"] + [self.tableRes.item(row, col).text() if self.tableRes.item(row, col) else "" for col in range(self.tableRes.columnCount())]
                    writer.writerow(rowData)
                    
                for row in range(self.tableTrac.rowCount()):
                    rowData = ["Trac"] + [self.tableTrac.item(row, col).text() if self.tableTrac.item(row, col) else "" for col in range(self.tableTrac.columnCount())]
                    writer.writerow(rowData)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
    def getSettings(self):
        settingsData = {
            "trainRes": [],
            "trainTrac": [],
            "trainParam": [],
            "speedLimitPlot": self.comboProfile.currentData(),
            "runReversed": self.checkReverse.isChecked()
        }
        
        try:
            settingsData["trainMaxSpeed"] = float(self.inputMaxSpeed.text())
        except ValueError:
            pass
            
        try:
            settingsData["trainInitialSpeed"] = float(self.inputInitialSpeed.text())
        except ValueError:
            pass

        try:
            settingsData["trainFinalSpeed"] = float(self.inputFinalSpeed.text())
        except ValueError:
            pass

        try:
            settingsData["trainBrakeDecel"] = float(self.inputBrakeDecel.text())
        except ValueError:
            pass

        # Table Train Resistance
        for row in range(self.tableRes.rowCount()):
            try:
                settingsData["trainRes"].append([
                    self.tableRes.item(row, 0).text(),
                    float(self.tableRes.item(row, 1).text()),
                    float(self.tableRes.item(row, 2).text()),
                    float(self.tableRes.item(row, 3).text())
                ])

            except(ValueError, AttributeError):
                continue
        
        # Table Train Traction
        for row in range(self.tableTrac.rowCount()):
            try:
                settingsData["trainTrac"].append([
                    self.tableTrac.item(row, 0).text(),
                    float(self.tableTrac.item(row, 1).text()),
                    float(self.tableTrac.item(row, 2).text()),
                    float(self.tableTrac.item(row, 3).text()),
                    float(self.tableTrac.item(row, 4).text()),
                    float(self.tableTrac.item(row, 5).text())
                ])

            except(ValueError, AttributeError):
                continue

        # Table Train Parameters
        for row in range(self.tableParam.rowCount()):
            try:
                length_item = self.tableParam.item(row, 3)
                settingsData["trainParam"].append([
                    self.tableParam.item(row, 0).text(),
                    float(self.tableParam.item(row, 1).text()),
                    float(self.tableParam.item(row, 2).text()),
                    float(length_item.text()) if length_item and length_item.text() else 0.0
                ])
            except(ValueError, AttributeError):
                continue

        return settingsData

class VehicleSettingsDialog(QDialog):
    def __init__(self, settingsData, lan, parent=None):
        super().__init__(parent)
        self.lan = lan
        self.settingsData = settingsData
        
        self.setWindowTitle(lan["vehicleSettings"])
        self.setMinimumSize(600, 450)

        layout = QVBoxLayout(self)
        
        toolbarLayout = QHBoxLayout()
        self.btnAdd = QPushButton(lan.get("addVehicle", "Add Vehicle"))
        self.btnAdd.clicked.connect(self.addVehicle)
        self.btnRemove = QPushButton(lan.get("removeVehicle", "Remove Vehicle"))
        self.btnRemove.clicked.connect(self.removeVehicle)
        toolbarLayout.addWidget(self.btnAdd)
        toolbarLayout.addWidget(self.btnRemove)
        layout.addLayout(toolbarLayout)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        vehicles = self.settingsData.get("vehicles", [])
        if not vehicles:
            old_v = {
                "trainInitialSpeed": self.settingsData.get("trainInitialSpeed", 0.0),
                "trainFinalSpeed": self.settingsData.get("trainFinalSpeed", 0.0),
                "trainMaxSpeed": self.settingsData.get("trainMaxSpeed", self.settingsData.get("vInit", [120])[0]),
                "trainBrakeDecel": self.settingsData.get("trainBrakeDecel", default_values.defVal.get("trainBrakeDecel", 1.0)),
                "trainRes": self.settingsData.get("trainRes", default_values.defVal.get("trainRes", [])),
                "trainTrac": self.settingsData.get("trainTrac", default_values.defVal.get("trainTrac", [])),
                "trainParam": self.settingsData.get("trainParam", default_values.defVal.get("trainParam", [])),
                "speedLimitPlot": self.settingsData.get("speedLimitPlot", ["stationSpeed150", "speedLimits150"]),
                "runReversed": self.settingsData.get("runReversed", False)
            }
            vehicles.append(old_v)
            
        for v_data in vehicles:
            self.addTab(v_data)
            
        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

    def addTab(self, v_data):
        if self.tabs.count() >= 3: return
        tab = VehicleTab(v_data, self.lan)
        self.tabs.addTab(tab, f'{self.lan.get("vehicle", "Vehicle")} {self.tabs.count() + 1}')
        self.updateButtons()

    def addVehicle(self):
        last_settings = self.tabs.widget(self.tabs.count() - 1).getSettings() if self.tabs.count() > 0 else {}
        self.addTab(last_settings)
        
    def removeVehicle(self):
        if self.tabs.count() > 1:
            self.tabs.removeTab(self.tabs.count() - 1)
        self.updateButtons()
        
    def updateButtons(self):
        self.btnAdd.setEnabled(self.tabs.count() < 3)
        self.btnRemove.setEnabled(self.tabs.count() > 1)
        
    def getSettings(self):
        vehicles = [self.tabs.widget(i).getSettings() for i in range(self.tabs.count())]
        return {"vehicles": vehicles}
