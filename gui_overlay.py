from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, 
                               QDialogButtonBox, QCheckBox, QLabel, 
                               QListWidget, QListWidgetItem, QFormLayout, 
                               QLineEdit, QTableWidget, QTableWidgetItem, 
                               QHeaderView, QFileDialog, QMessageBox, 
                               QDialogButtonBox, QPushButton, QComboBox)
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

class MapSettingsDialog(QDialog):
    def __init__(self, currentEPSG, currentMap, lan, parent=None):
        super().__init__(parent)

        self.setWindowTitle(lan["mapSettings"])

        layout = QVBoxLayout(self)
        formLayout = QFormLayout()

        displayValue = currentEPSG
        self.inputEPSG = QLineEdit(displayValue)

        formLayout.addRow(QLabel(lan["currentEPSG"]), self.inputEPSG)
        layout.addLayout(formLayout)
        
        self.comboMap = QComboBox()
        self.comboMap.addItem(lan.get("mapPositron", "CartoDB Positron"), "positron")
        self.comboMap.addItem(lan.get("mapOSM", "OpenStreetMap"), "osm")
        self.comboMap.addItem(lan.get("mapORM", "OpenRailwayMap"), "orm")
        self.comboMap.addItem(lan.get("mapCUZK", "ČÚZK Ortofoto"), "cuzk")
        
        index = self.comboMap.findData(currentMap)
        if index >= 0:
            self.comboMap.setCurrentIndex(index)
            
        formLayout.addRow(QLabel(lan.get("mapBase", "Map Base:")), self.comboMap)

        label = QLabel(lan["EPSGinfo"])
        layout.addWidget(label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
    def getMapSettings(self):

        epsg = self.inputEPSG.text().strip().upper()

        if not epsg.startswith("EPSG:"):
            epsg = f"EPSG:{epsg}"
            
        return epsg, self.comboMap.currentData()
        
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

        toolbarLayoutI = QHBoxLayout()

        self.btnImportI = QPushButton(lan["importCSV"])
        self.btnImportI.clicked.connect(lambda: self.importCSV("tableI"))
        toolbarLayoutI.addWidget(self.btnImportI)

        self.btnExportI = QPushButton(lan["exportCSV"])
        self.btnExportI.clicked.connect(lambda: self.exportCSV("tableI"))
        toolbarLayoutI.addWidget(self.btnExportI)

        layout.addLayout(toolbarLayoutI)

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

        toolbarLayoutDI = QHBoxLayout()

        self.btnImportDI = QPushButton(lan["importCSV"])
        self.btnImportDI.clicked.connect(lambda: self.importCSV("tableDI"))
        toolbarLayoutDI.addWidget(self.btnImportDI)

        self.btnExportDI = QPushButton(lan["exportCSV"])
        self.btnExportDI.clicked.connect(lambda: self.exportCSV("tableDI"))
        toolbarLayoutDI.addWidget(self.btnExportDI)

        layout.addLayout(toolbarLayoutDI)

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

        toolbarLayoutNlin = QHBoxLayout()

        self.btnImportNlin = QPushButton(lan["importCSV"])
        self.btnImportNlin.clicked.connect(lambda: self.importCSV("tableNlin"))
        toolbarLayoutNlin.addWidget(self.btnImportNlin)

        self.btnExportNlin = QPushButton(lan["exportCSV"])
        self.btnExportNlin.clicked.connect(lambda: self.exportCSV("tableNlin"))
        toolbarLayoutNlin.addWidget(self.btnExportNlin)

        layout.addLayout(toolbarLayoutNlin)

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

        toolbarLayoutNIlin = QHBoxLayout()

        self.btnImportNIlin = QPushButton(lan["importCSV"])
        self.btnImportNIlin.clicked.connect(lambda: self.importCSV("tableNIlin"))
        toolbarLayoutNIlin.addWidget(self.btnImportNIlin)

        self.btnExportNIlin = QPushButton(lan["exportCSV"])
        self.btnExportNIlin.clicked.connect(lambda: self.exportCSV("tableNIlin"))
        toolbarLayoutNIlin.addWidget(self.btnExportNIlin)

        layout.addLayout(toolbarLayoutNIlin)

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

    def importCSV(self, table):
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

            if table == "tableI":
                self.populateTable(self.tableI, reader)

            elif table == "tableDI":
                self.populateTable(self.tableDI, reader)

            elif table == "tableNlin":
                self.populateTable(self.tableNlin, reader)

            elif table == "tableNIlin":
                self.populateTable(self.tableNIlin, reader)
            
            else:
                raise ValueError
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        
    def exportCSV(self, table):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        
        # If cancelled, do nothing
        if not filepath:
            return
        
        try:
            if table == "tableI":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vbottom", "Vtop", "I_std", "I_lim", "I_max"]
                    writer.writerow(headers)

                    for row in range(self.tableI.rowCount()):
                        rowData = [self.tableI.item(row, col).text() for col in range(self.tableI.columnCount())]
                        writer.writerow(rowData)

            elif table == "tableDI":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vbottom", "Vtop", "dI_std", "dI_lim", "dI_max"]
                    writer.writerow(headers)

                    for row in range(self.tableDI.rowCount()):
                        rowData = [self.tableDI.item(row, col).text() for col in range(self.tableDI.columnCount())]
                        writer.writerow(rowData)

            elif table == "tableNlin":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vbottom", "Vtop", "n_n", "n_n_abs", "n_lim", "n_lim_abs", "n_min", "n_min_abs"]
                    writer.writerow(headers)

                    for row in range(self.tableNlin.rowCount()):
                        rowData = [self.tableNlin.item(row, col).text() for col in range(self.tableNlin.columnCount())]
                        writer.writerow(rowData)

            elif table == "tableNIlin":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vbottom", "Vtop", "nI_n", "nI_lim", "nI_min"]
                    writer.writerow(headers)

                    for row in range(self.tableNIlin.rowCount()):
                        rowData = [self.tableNIlin.item(row, col).text() for col in range(self.tableNIlin.columnCount())]
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

        self.tableStops = QTableWidget(0, 2)
        self.tableStops.setHorizontalHeaderLabels([
            lan["station"],
            lan.get("dwellTimeTable", "Dwell Time [s]")
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
        self.tableStops.setItem(row, 0, itemStation)
        self.tableStops.setItem(row, 1, itemDwell)

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
            if table == "tableStops": self.populateTable(self.tableStops, reader)
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def exportCSV(self, table):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        if not filepath: return
        try:
            if table == "tableStops":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    writer.writerow(["Station", "Dwell Time"])
                    for row in range(self.tableStops.rowCount()):
                        writer.writerow([self.tableStops.item(row, col).text() for col in range(self.tableStops.columnCount())])
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            
    def getSettings(self):
        settingsData = {"trainStops": []}
        try: settingsData["defaultDwellTime"] = float(self.inputDwellTime.text())
        except ValueError: pass
        for row in range(self.tableStops.rowCount()):
            try: settingsData["trainStops"].append([float(self.tableStops.item(row, 0).text()), float(self.tableStops.item(row, 1).text())])
            except (ValueError, AttributeError): continue
        return settingsData

class VehicleSettingsDialog(QDialog):
    def __init__(self, settingsData, lan, parent = None):
        super().__init__(parent)
        self.lan = lan
        self.settingsData = settingsData
        
        self.setWindowTitle(lan["vehicleSettings"])
        self.setMinimumSize(600,400)

        layout = QVBoxLayout(self)
        
        formLayout = QFormLayout()
        
        self.inputInitialSpeed = QLineEdit(str(self.settingsData.get("trainInitialSpeed", 0.0)))
        formLayout.addRow(QLabel(lan.get("trainInitialSpeed", "Initial Speed [km/h]:")), self.inputInitialSpeed)

        self.inputFinalSpeed = QLineEdit(str(self.settingsData.get("trainFinalSpeed", 0.0)))
        formLayout.addRow(QLabel(lan.get("trainFinalSpeed", "Final Speed [km/h]:")), self.inputFinalSpeed)
        
        self.inputMaxSpeed = QLineEdit(str(self.settingsData.get("trainMaxSpeed", self.settingsData.get("vInit", [120])[0])))
        
        self.comboProfile = QComboBox()
        self.profiles = [
            (lan.get("speed_lim_ttp", "TTP Speed Limits"), ["stationSpeedLimits", "speedLimits"]),
            (lan.get("speed_lim_100", "V100"), ["stationSpeed100", "speedLimits100"]),
            (lan.get("speed_lim_130", "V130"), ["stationSpeed130", "speedLimits130"]),
            (lan.get("speed_lim_150", "V150"), ["stationSpeed150", "speedLimits150"]),
            (lan.get("speed_lim_K", "VK"), ["stationSpeedK", "speedLimitsK"]),
            (lan.get("unlimited", "Unlimited"), ["unlimited", "unlimited"])
        ]
        
        for text, data in self.profiles:
            self.comboProfile.addItem(text, data)
            
        current_profile = self.settingsData.get("speedLimitPlot", ["stationSpeed150", "speedLimits150"])
        for i, (text, data) in enumerate(self.profiles):
            if data == current_profile:
                self.comboProfile.setCurrentIndex(i)
                break

        formLayout.addRow(QLabel(lan.get("max_train_speed", "Max Train Speed [km/h]:")), self.inputMaxSpeed)
        
        self.inputBrakeMech = QLineEdit(str(self.settingsData.get("trainBrakeMech", default_values.defVal.get("trainBrakeMech", 150.0))))
        formLayout.addRow(QLabel(lan.get("vehicleBrakeMech", "Mechanical Braking [kN]:")), self.inputBrakeMech)
        formLayout.addRow(QLabel(lan.get("speed_profile", "Speed Profile:")), self.comboProfile)
        
        layout.addLayout(formLayout)

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
        defaultRes = self.settingsData.get("trainRes", default_values.defVal.get("trainRes", []))

        self.populateTable(self.tableRes, defaultRes)

        toolbarLayoutRes = QHBoxLayout()

        self.btnImportRes = QPushButton(lan["importCSV"])
        self.btnImportRes.clicked.connect(lambda: self.importCSV("tableRes"))
        toolbarLayoutRes.addWidget(self.btnImportRes)

        self.btnExportRes = QPushButton(lan["exportCSV"])
        self.btnExportRes.clicked.connect(lambda: self.exportCSV("tableRes"))
        toolbarLayoutRes.addWidget(self.btnExportRes)

        layout.addLayout(toolbarLayoutRes)

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
        defaultTrac = self.settingsData.get("trainTrac", default_values.defVal.get("trainTrac", []))

        self.populateTable(self.tableTrac, defaultTrac)

        toolbarLayoutTrac = QHBoxLayout()

        self.btnImportTrac = QPushButton(lan["importCSV"])
        self.btnImportTrac.clicked.connect(lambda: self.importCSV("tableTrac"))
        toolbarLayoutTrac.addWidget(self.btnImportTrac)

        self.btnExportTrac = QPushButton(lan["exportCSV"])
        self.btnExportTrac.clicked.connect(lambda: self.exportCSV("tableTrac"))
        toolbarLayoutTrac.addWidget(self.btnExportTrac)

        layout.addLayout(toolbarLayoutTrac)

        labelBrake = QLabel(lan.get("vehicleBrakeDyn", "Vehicle Dynamic Braking"))
        layout.addWidget(labelBrake)

        # Table for editing dynamic brake coefficients
        self.tableBrake = QTableWidget(0, 6)
        self.tableBrake.setHorizontalHeaderLabels([
            lan["vehicle"],
            lan["Vbottom"],
            lan["Vtop"],
            lan["coef_b0"],
            lan["coef_b1"],
            lan["coef_b2"]
        ])
        headerBrake = self.tableBrake.horizontalHeader()
        headerBrake.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableBrake)

        defaultBrake = self.settingsData.get("trainBrake", default_values.defVal.get("trainBrake", []))
        self.populateTable(self.tableBrake, defaultBrake)

        toolbarLayoutBrake = QHBoxLayout()
        self.btnImportBrake = QPushButton(lan["importCSV"])
        self.btnImportBrake.clicked.connect(lambda: self.importCSV("tableBrake"))
        toolbarLayoutBrake.addWidget(self.btnImportBrake)
        self.btnExportBrake = QPushButton(lan["exportCSV"])
        self.btnExportBrake.clicked.connect(lambda: self.exportCSV("tableBrake"))
        toolbarLayoutBrake.addWidget(self.btnExportBrake)
        layout.addLayout(toolbarLayoutBrake)

        labelParam = QLabel(lan["vehicleParam"])
        layout.addWidget(labelParam)

        # Table for editing train parameters coefficients
        self.tableParam = QTableWidget(0, 3)
        self.tableParam.setHorizontalHeaderLabels([
            lan["vehicle"],
            lan["rotMass"],
            lan["weight"]
        ])

        headerParam = self.tableParam.horizontalHeader()
        headerParam.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.tableParam)

        # Default values for train parameters
        defaultParam = self.settingsData.get("trainParam", default_values.defVal.get("trainParam", []))

        self.populateTable(self.tableParam, defaultParam)

        toolbarLayoutParam = QHBoxLayout()

        self.btnImportParam = QPushButton(lan["importCSV"])
        self.btnImportParam.clicked.connect(lambda: self.importCSV("tableParam"))
        toolbarLayoutParam.addWidget(self.btnImportParam)

        self.btnExportParam = QPushButton(lan["exportCSV"])
        self.btnExportParam.clicked.connect(lambda: self.exportCSV("tableParam"))
        toolbarLayoutParam.addWidget(self.btnExportParam)

        layout.addLayout(toolbarLayoutParam)

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

    def importCSV(self, table):
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

            if table == "tableRes":
                self.populateTable(self.tableRes, reader)
            
            elif table == "tableTrac":
                self.populateTable(self.tableTrac, reader)

            elif table == "tableBrake":
                self.populateTable(self.tableBrake, reader)

            elif table == "tableParam":
                self.populateTable(self.tableParam, reader)

            else:
                raise ValueError
            
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        
    def exportCSV(self, table):
        filepath, _ = QFileDialog.getSaveFileName(self, "Save File", "", "CSV Files (*.csv)")
        
        # If cancelled, do nothing
        if not filepath:
            return
        
        try:
            if table == "tableRes":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vehicle", "A", "B", "C"]
                    writer.writerow(headers)

                    for row in range(self.tableRes.rowCount()):
                        rowData = [self.tableRes.item(row, col).text() for col in range(self.tableRes.columnCount())]
                        writer.writerow(rowData)

            elif table == "tableTrac":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vehicle", "Speed from", "Speed to", "Coefficient b_0", "Coefficient b_1", "Coefficient b_2"]
                    writer.writerow(headers)

                    for row in range(self.tableTrac.rowCount()):
                        rowData = [self.tableTrac.item(row, col).text() for col in range(self.tableTrac.columnCount())]
                        writer.writerow(rowData)

            elif table == "tableBrake":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vehicle", "Speed from", "Speed to", "Coefficient b_0", "Coefficient b_1", "Coefficient b_2"]
                    writer.writerow(headers)
                    for row in range(self.tableBrake.rowCount()):
                        rowData = [self.tableBrake.item(row, col).text() for col in range(self.tableBrake.columnCount())]
                        writer.writerow(rowData)

            elif table == "tableParam":
                with open(filepath, "w", newline="") as file:
                    writer = csv.writer(file)
                    headers = ["Vehicle", "Coefficient of Rotating Mass", "Weight (Tonnes)"]
                    writer.writerow(headers)

                    for row in range(self.tableParam.rowCount()):
                        rowData = [self.tableParam.item(row, col).text() for col in range(self.tableParam.columnCount())]
                        writer.writerow(rowData)

        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))
            return
        
    def getSettings(self):
        settingsData = {
            "trainRes": [],
            "trainTrac": [],
            "trainBrake": [],
            "trainParam": [],
            "speedLimitPlot": self.comboProfile.currentData()
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
            settingsData["trainBrakeMech"] = float(self.inputBrakeMech.text())
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

        # Table Dynamic Brake
        for row in range(self.tableBrake.rowCount()):
            try:
                settingsData["trainBrake"].append([
                    self.tableBrake.item(row, 0).text(),
                    float(self.tableBrake.item(row, 1).text()),
                    float(self.tableBrake.item(row, 2).text()),
                    float(self.tableBrake.item(row, 3).text()),
                    float(self.tableBrake.item(row, 4).text()),
                    float(self.tableBrake.item(row, 5).text())
                ])
            except(ValueError, AttributeError):
                continue

        # Table Train Parameters
        for row in range(self.tableParam.rowCount()):
            try:
                settingsData["trainParam"].append([
                    self.tableParam.item(row, 0).text(),
                    float(self.tableParam.item(row, 1).text()),
                    float(self.tableParam.item(row, 2).text())
                ])

            except(ValueError, AttributeError):
                continue

        return settingsData
