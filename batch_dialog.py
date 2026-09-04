# Modal dialog for configuring and launching a batch of track variants
import copy
import csv
import io
from pathlib import Path

from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QTabWidget, QWidget,
                                QLabel, QLineEdit, QComboBox, QCheckBox, QPushButton, QListWidget,
                                QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox,
                                QDialogButtonBox)

import batch_config
import geometry_engine
import readfile

# Default export formats offered on the Output tab, key -> initially checked
DEFAULT_EXPORT_FORMATS = (("txt", True), ("csv", True), ("md", False),
                           ("pdf", True), ("tex", False), ("png", True), ("svg", False))


class BatchProcessingDialog(QDialog):
    def __init__(self, settingsData, batchConfigStore, lan, parent=None):
        super().__init__(parent)
        self.settingsData = settingsData
        self.batchConfigStore = batchConfigStore
        self.lan = lan or {}
        self.trackSources = []
        self.stopsProfiles = []
        self.finalConfigData = None
        self.isFullyBuilt = False

        self.setWindowTitle(self.lan.get("batchTitle", "Batch Processing"))
        self.setMinimumSize(720, 560)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        nameLayout = QFormLayout()
        self.configNameInput = QLineEdit()
        nameLayout.addRow(QLabel(self.lan.get("batchConfigName", "Configuration name")), self.configNameInput)
        layout.addLayout(nameLayout)

        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.buildTrackSourcesTab()
        self.buildStopsProfilesTab()
        self.buildDesignApproachesTab()
        self.buildSensitivityTab()
        self.buildOptimizationTab()
        self.buildOutputTab()

        previewLayout = QHBoxLayout()
        self.variantPreviewLabel = QLabel()
        previewLayout.addWidget(self.variantPreviewLabel, 1)
        self.savePresetButton = QPushButton(self.lan.get("batchSavePreset", "Save preset..."))
        self.savePresetButton.clicked.connect(self.savePresetFile)
        previewLayout.addWidget(self.savePresetButton)
        self.loadPresetButton = QPushButton(self.lan.get("batchLoadPreset", "Load preset..."))
        self.loadPresetButton.clicked.connect(self.loadPresetFile)
        previewLayout.addWidget(self.loadPresetButton)
        layout.addLayout(previewLayout)

        self.buttonBox = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.buttonBox.button(QDialogButtonBox.StandardButton.Ok).setText(self.lan.get("batchRun", "Run"))
        self.buttonBox.accepted.connect(self.onAccept)
        self.buttonBox.rejected.connect(self.reject)
        layout.addWidget(self.buttonBox)

        self.isFullyBuilt = True
        self.refreshVariantPreview()

    # --- Track sources tab ------------------------------------------------

    def buildTrackSourcesTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.trackSourceList = QListWidget()
        layout.addWidget(self.trackSourceList, 1)

        buttonsRow = QHBoxLayout()
        self.addTrackFilesButton = QPushButton(self.lan.get("batchAddFiles", "Add files..."))
        self.addTrackFilesButton.clicked.connect(self.addTrackFiles)
        buttonsRow.addWidget(self.addTrackFilesButton)
        self.removeTrackFileButton = QPushButton(self.lan.get("batchRemoveFile", "Remove"))
        self.removeTrackFileButton.clicked.connect(self.removeTrackFile)
        buttonsRow.addWidget(self.removeTrackFileButton)
        self.moveTrackFileUpButton = QPushButton(self.lan.get("batchMoveUp", "Move up"))
        self.moveTrackFileUpButton.clicked.connect(self.moveTrackFileUp)
        buttonsRow.addWidget(self.moveTrackFileUpButton)
        self.moveTrackFileDownButton = QPushButton(self.lan.get("batchMoveDown", "Move down"))
        self.moveTrackFileDownButton.clicked.connect(self.moveTrackFileDown)
        buttonsRow.addWidget(self.moveTrackFileDownButton)
        layout.addLayout(buttonsRow)

        formLayout = QFormLayout()
        self.epsgInput = QLineEdit("EPSG:5514")
        formLayout.addRow(QLabel(self.lan.get("batchEpsg", "Coordinate system")), self.epsgInput)
        self.chainageModeCombo = QComboBox()
        self.chainageModeCombo.addItem(self.lan.get("batchChainageSequential", "Sequential (rebased)"), "sequential")
        self.chainageModeCombo.addItem(self.lan.get("batchChainageAsImported", "As imported"), "asImported")
        formLayout.addRow(QLabel(self.lan.get("batchChainageMode", "Chainage mode")), self.chainageModeCombo)
        layout.addLayout(formLayout)

        self.tabs.addTab(tab, self.lan.get("batchTabTrackSources", "Track sources"))

    def addTrackFiles(self):
        filePaths, _ = QFileDialog.getOpenFileNames(
            self, self.lan.get("batchAddFiles", "Add files..."), "", "LandXML (*.xml)")
        for filePath in filePaths:
            self.trackSources.append({"filePath": filePath, "fileName": Path(filePath).name, "alignmentIndex": 0})
        self.refreshTrackSourceList()
        self.refreshVariantPreview()

    def removeTrackFile(self):
        row = self.trackSourceList.currentRow()
        if row >= 0:
            del self.trackSources[row]
            self.refreshTrackSourceList()
        self.refreshVariantPreview()

    def moveTrackFileUp(self):
        row = self.trackSourceList.currentRow()
        if row > 0:
            self.trackSources[row - 1], self.trackSources[row] = self.trackSources[row], self.trackSources[row - 1]
            self.refreshTrackSourceList()
            self.trackSourceList.setCurrentRow(row - 1)

    def moveTrackFileDown(self):
        row = self.trackSourceList.currentRow()
        if 0 <= row < len(self.trackSources) - 1:
            self.trackSources[row + 1], self.trackSources[row] = self.trackSources[row], self.trackSources[row + 1]
            self.refreshTrackSourceList()
            self.trackSourceList.setCurrentRow(row + 1)

    def refreshTrackSourceList(self):
        self.trackSourceList.clear()
        for source in self.trackSources:
            self.trackSourceList.addItem(source["fileName"])

    # --- Stopping patterns tab ---------------------------------------------

    def buildStopsProfilesTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.stopsProfileList = QListWidget()
        layout.addWidget(self.stopsProfileList, 1)

        buttonsRow = QHBoxLayout()
        self.addStopsProfileButton = QPushButton(self.lan.get("batchAddStopsProfile", "Add stopping pattern..."))
        self.addStopsProfileButton.clicked.connect(self.addStopsProfile)
        buttonsRow.addWidget(self.addStopsProfileButton)
        self.removeStopsProfileButton = QPushButton(self.lan.get("batchRemoveStopsProfile", "Remove"))
        self.removeStopsProfileButton.clicked.connect(self.removeStopsProfile)
        buttonsRow.addWidget(self.removeStopsProfileButton)
        layout.addLayout(buttonsRow)

        self.tabs.addTab(tab, self.lan.get("batchTabStopsProfiles", "Stopping patterns"))

    # Several patterns are usually compared in one batch, so the picker takes them all at once
    def addStopsProfile(self):
        filePaths, _ = QFileDialog.getOpenFileNames(
            self, self.lan.get("batchAddStopsProfile", "Add stopping pattern..."), "", "CSV Files (*.csv)")
        if not filePaths:
            return

        problems = []
        for filePath in filePaths:
            fileContent = readfile.ReadFile().Read(filePath)
            if not fileContent or fileContent.startswith("Error"):
                problems.append(f"{Path(filePath).name}: {fileContent or ''}".strip())
                continue

            trainStops = self.parseStopsCsv(fileContent)
            if not trainStops:
                problems.append(f"{Path(filePath).name}: "
                                f"{self.lan.get('batchStopsFileEmpty', 'no usable stop rows')}")
                continue

            profileId = f"profile{len(self.stopsProfiles) + 1}"
            self.stopsProfiles.append({"stopsProfileId": profileId, "label": Path(filePath).stem,
                                       "fileName": Path(filePath).name, "trainStops": trainStops})

        self.refreshStopsProfileList()
        self.refreshVariantPreview()

        # One dialog for the whole selection, a single bad file never hides the ones that worked
        if problems:
            QMessageBox.warning(self, self.lan.get("error", "Error"),
                                self.lan.get("batchStopsImportProblems",
                                             "Some stopping patterns could not be imported:")
                                + "\n" + "\n".join(problems))

    # Same contract as StopsSettingsDialog.importCSV: skip one header row, positional [km, dwell, name]
    def parseStopsCsv(self, fileContent):
        trainStops = []
        reader = csv.reader(io.StringIO(fileContent), delimiter=',')
        next(reader, None)
        for row in reader:
            try:
                stationKm = float(row[0])
                dwell = float(row[1])
                name = str(row[2]) if len(row) > 2 else ""
                trainStops.append([stationKm, dwell, name])
            except (IndexError, ValueError):
                continue
        return trainStops

    def removeStopsProfile(self):
        row = self.stopsProfileList.currentRow()
        if row >= 0:
            del self.stopsProfiles[row]
            self.refreshStopsProfileList()
        self.refreshVariantPreview()

    def refreshStopsProfileList(self):
        self.stopsProfileList.clear()
        for profile in self.stopsProfiles:
            self.stopsProfileList.addItem(f"{profile.get('label', '')} ({len(profile.get('trainStops', []))} stops)")

    # --- Design approaches tab ---------------------------------------------

    def buildDesignApproachesTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.approachTable = QTableWidget(0, 5)
        self.approachTable.setHorizontalHeaderLabels([
            self.lan.get("batchApproachLabel", "Label"),
            self.lan.get("cant_def", "I"), self.lan.get("abrupt_cant_def", "dI"),
            self.lan.get("nLin", "nLin"), self.lan.get("nILin", "nILin"),
        ])
        self.approachTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.approachTable, 1)

        buttonsRow = QHBoxLayout()
        self.addApproachButton = QPushButton(self.lan.get("addRow", "Add Row"))
        self.addApproachButton.clicked.connect(lambda: self.addApproachRow())
        buttonsRow.addWidget(self.addApproachButton)
        self.removeApproachButton = QPushButton(self.lan.get("removeRow", "Remove Row"))
        self.removeApproachButton.clicked.connect(self.removeApproachRow)
        buttonsRow.addWidget(self.removeApproachButton)
        layout.addLayout(buttonsRow)

        self.tabs.addTab(tab, self.lan.get("batchTabApproaches", "Design approaches"))

        # Seeded with three representative combinations, all editable and removable
        self.addApproachRow("CSN standard", "standard", "standard", "standard", "standard")
        self.addApproachRow("CSN limit", "limit", "limit", "limit", "limit")
        self.addApproachRow("Marginal I", "minmax", "limit", "limit", "limit")

    def buildApproachLevelCombo(self, currentLevel):
        combo = QComboBox()
        for levelKey in batch_config.APPROACH_LEVELS:
            combo.addItem(self.lan.get(levelKey, levelKey), levelKey)
        index = combo.findData(currentLevel)
        combo.setCurrentIndex(max(0, index))
        combo.currentIndexChanged.connect(self.refreshVariantPreview)
        return combo

    def addApproachRow(self, label="", iLevel="standard", dILevel="standard", nLinLevel="standard", nILinLevel="standard"):
        row = self.approachTable.rowCount()
        self.approachTable.insertRow(row)
        self.approachTable.setItem(row, 0, QTableWidgetItem(label or f"Approach {row + 1}"))
        for col, level in zip((1, 2, 3, 4), (iLevel, dILevel, nLinLevel, nILinLevel)):
            self.approachTable.setCellWidget(row, col, self.buildApproachLevelCombo(level))
        self.refreshVariantPreview()

    def removeApproachRow(self):
        row = self.approachTable.currentRow()
        if row >= 0:
            self.approachTable.removeRow(row)
        self.refreshVariantPreview()

    def collectDesignApproaches(self):
        approaches = []
        for row in range(self.approachTable.rowCount()):
            labelItem = self.approachTable.item(row, 0)
            label = labelItem.text() if labelItem else f"Approach {row + 1}"
            approach = {}
            for col, paramKey in zip((1, 2, 3, 4), batch_config.APPROACH_PARAMETERS):
                combo = self.approachTable.cellWidget(row, col)
                approach[paramKey] = combo.currentData() if combo else "standard"
            approaches.append({"approachId": f"a{row + 1}", "label": label, "approach": approach})
        return approaches

    # --- Optimization tab ----------------------------------------------------

    def buildOptimizationTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.includeBaselineCheck = QCheckBox(self.lan.get("batchIncludeBaseline", "Include baseline scenario (no optimization)"))
        self.includeBaselineCheck.setChecked(True)
        self.includeBaselineCheck.stateChanged.connect(self.refreshVariantPreview)
        layout.addWidget(self.includeBaselineCheck)

        self.scenarioTable = QTableWidget(0, 6)
        self.scenarioTable.setHorizontalHeaderLabels([
            self.lan.get("batchScenarioLabel", "Label"),
            self.lan.get("optPatternLcl", "Line-Curve-Line"),
            self.lan.get("optPatternLscsl", "Line-Spiral-Curve-Spiral-Line"),
            self.lan.get("batchScenarioDMax", "d_max [m]"), self.lan.get("batchScenarioLMin", "L_min [m]"),
            self.lan.get("batchScenarioLkMax", "L_k,max [m]"),
        ])
        self.scenarioTable.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.scenarioTable, 1)

        buttonsRow = QHBoxLayout()
        self.addScenarioButton = QPushButton(self.lan.get("batchAddScenario", "Add scenario"))
        self.addScenarioButton.clicked.connect(lambda: self.addOptimizationScenarioRow())
        buttonsRow.addWidget(self.addScenarioButton)
        self.removeScenarioButton = QPushButton(self.lan.get("batchRemoveScenario", "Remove"))
        self.removeScenarioButton.clicked.connect(self.removeOptimizationScenarioRow)
        buttonsRow.addWidget(self.removeScenarioButton)
        layout.addLayout(buttonsRow)

        self.tabs.addTab(tab, self.lan.get("batchTabOptimization", "Optimization"))

    def buildOptModeCombo(self, allowedModes, currentMode):
        combo = QComboBox()
        combo.addItem(self.lan.get("optModeNone", "Do not optimize"), geometry_engine.OPTIMIZATION_MODE_NONE)
        modeLabelKeys = {
            geometry_engine.OPTIMIZATION_MODE_SHIFT_AND_EXTEND: "optModeShiftAndExtend",
            geometry_engine.OPTIMIZATION_MODE_EXTEND_SPIRALS: "optModeExtendSpirals",
            geometry_engine.OPTIMIZATION_MODE_SHIFT_ARC: "optModeShiftArc",
            geometry_engine.OPTIMIZATION_MODE_INVERTED_SHIFT: "optModeInvertedShift",
        }
        for mode in allowedModes:
            combo.addItem(self.lan.get(modeLabelKeys[mode], mode), mode)
        index = combo.findData(currentMode)
        combo.setCurrentIndex(max(0, index))
        combo.currentIndexChanged.connect(self.refreshVariantPreview)
        return combo

    def addOptimizationScenarioRow(self, label="", modeLcl=geometry_engine.OPTIMIZATION_MODE_NONE,
                                   modeLscsl=geometry_engine.OPTIMIZATION_MODE_SHIFT_AND_EXTEND,
                                   dMaxM=0.5, lMinM=25.0, lkMaxM=geometry_engine.DEFAULT_LK_MAX_M):
        row = self.scenarioTable.rowCount()
        self.scenarioTable.insertRow(row)
        self.scenarioTable.setItem(row, 0, QTableWidgetItem(label or f"d_max={dMaxM}"))
        self.scenarioTable.setCellWidget(row, 1, self.buildOptModeCombo(geometry_engine.LCL_OPTIMIZATION_MODES, modeLcl))
        self.scenarioTable.setCellWidget(row, 2, self.buildOptModeCombo(geometry_engine.OPTIMIZATION_MODES, modeLscsl))
        dMaxInput = QLineEdit(str(dMaxM))
        dMaxInput.textChanged.connect(self.refreshVariantPreview)
        self.scenarioTable.setCellWidget(row, 3, dMaxInput)
        lMinInput = QLineEdit(str(lMinM))
        lMinInput.textChanged.connect(self.refreshVariantPreview)
        self.scenarioTable.setCellWidget(row, 4, lMinInput)
        lkMaxInput = QLineEdit(str(lkMaxM))
        lkMaxInput.textChanged.connect(self.refreshVariantPreview)
        self.scenarioTable.setCellWidget(row, 5, lkMaxInput)
        self.refreshVariantPreview()

    def removeOptimizationScenarioRow(self):
        row = self.scenarioTable.currentRow()
        if row >= 0:
            self.scenarioTable.removeRow(row)
        self.refreshVariantPreview()

    def collectOptimizationScenarios(self):
        scenarios = []
        for row in range(self.scenarioTable.rowCount()):
            labelItem = self.scenarioTable.item(row, 0)
            label = labelItem.text() if labelItem else f"Scenario {row + 1}"
            modeLclCombo = self.scenarioTable.cellWidget(row, 1)
            modeLscslCombo = self.scenarioTable.cellWidget(row, 2)
            dMaxInput = self.scenarioTable.cellWidget(row, 3)
            lMinInput = self.scenarioTable.cellWidget(row, 4)
            lkMaxInput = self.scenarioTable.cellWidget(row, 5)
            try:
                dMaxM = float(dMaxInput.text())
                lMinM = float(lMinInput.text())
                lkMaxM = float(lkMaxInput.text())
            except ValueError:
                dMaxM, lMinM, lkMaxM = 0.0, 0.0, 0.0
            scenarios.append({
                "scenarioId": f"opt{row + 1}", "label": label, "isEnabled": True,
                "dMaxM": dMaxM, "lMinM": lMinM, "lkMaxM": lkMaxM,
                "modeLcl": modeLclCombo.currentData() if modeLclCombo else geometry_engine.OPTIMIZATION_MODE_NONE,
                "modeLscsl": modeLscslCombo.currentData() if modeLscslCombo else geometry_engine.OPTIMIZATION_MODE_NONE,
            })
        return scenarios

    # --- Sensitivity tab -----------------------------------------------------

    def buildSensitivityTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        self.sweepEnabledCheck = QCheckBox(self.lan.get("batchSweepEnabled", "Enable sensitivity sweep"))
        self.sweepEnabledCheck.stateChanged.connect(self.onSweepToggled)
        layout.addWidget(self.sweepEnabledCheck)

        formLayout = QFormLayout()
        self.sweepParamCombo = QComboBox()
        for paramKey, config in batch_config.SWEEP_PARAMETERS.items():
            self.sweepParamCombo.addItem(self.lan.get(config["labelKey"], paramKey), paramKey)
        self.sweepParamCombo.currentIndexChanged.connect(self.refreshVariantPreview)
        formLayout.addRow(QLabel(self.lan.get("batchSweepParam", "Parameter")), self.sweepParamCombo)

        self.sweepMinInput = QLineEdit("0")
        self.sweepMaxInput = QLineEdit("0")
        self.sweepStepInput = QLineEdit("1")
        for inputField, rowKey, fallback in ((self.sweepMinInput, "batchSweepMin", "Min"),
                                              (self.sweepMaxInput, "batchSweepMax", "Max"),
                                              (self.sweepStepInput, "batchSweepStep", "Step")):
            inputField.textChanged.connect(self.refreshVariantPreview)
            formLayout.addRow(QLabel(self.lan.get(rowKey, fallback)), inputField)
        layout.addLayout(formLayout)
        layout.addStretch(1)

        self.tabs.addTab(tab, self.lan.get("batchTabSensitivity", "Sensitivity"))
        self.onSweepToggled(0)

    def onSweepToggled(self, state):
        isEnabled = self.sweepEnabledCheck.isChecked()
        self.sweepParamCombo.setEnabled(isEnabled)
        self.sweepMinInput.setEnabled(isEnabled)
        self.sweepMaxInput.setEnabled(isEnabled)
        self.sweepStepInput.setEnabled(isEnabled)
        self.refreshVariantPreview()

    def collectSweepConfig(self):
        isEnabled = self.sweepEnabledCheck.isChecked()
        try:
            minValue = float(self.sweepMinInput.text())
            maxValue = float(self.sweepMaxInput.text())
            stepValue = float(self.sweepStepInput.text())
        except ValueError:
            minValue = maxValue = stepValue = 0.0
            isEnabled = False
        return {"isEnabled": isEnabled, "paramKey": self.sweepParamCombo.currentData(),
                "minValue": minValue, "maxValue": maxValue, "stepValue": stepValue}

    # --- Output tab ------------------------------------------------------------

    def buildOutputTab(self):
        tab = QWidget()
        layout = QVBoxLayout(tab)

        formLayout = QFormLayout()
        self.calculationModeCombo = QComboBox()
        self.calculationModeCombo.addItem(self.lan.get("batchModeDesign", "Design"), "design")
        self.calculationModeCombo.addItem(self.lan.get("batchModeAsBuilt", "As built"), "asBuilt")
        formLayout.addRow(QLabel(self.lan.get("batchCalculationMode", "Calculation mode")), self.calculationModeCombo)

        self.designProfileCombo = QComboBox()
        for profileKey in ("I100", "I130", "I150", "K"):
            self.designProfileCombo.addItem(profileKey, profileKey)
        self.designProfileCombo.setCurrentIndex(self.designProfileCombo.findData("I150"))
        formLayout.addRow(QLabel(self.lan.get("batchDesignProfile", "Design profile")), self.designProfileCombo)
        layout.addLayout(formLayout)

        self.runVehiclesCheck = QCheckBox(self.lan.get("batchRunVehicles", "Run vehicle simulation for every variant"))
        self.runVehiclesCheck.setChecked(True)
        layout.addWidget(self.runVehiclesCheck)

        layout.addWidget(QLabel(self.lan.get("exportFormats", "Export formats")))
        self.formatChecks = {}
        for formatKey, defaultChecked in DEFAULT_EXPORT_FORMATS:
            check = QCheckBox(self.lan.get(f"format{formatKey.capitalize()}", formatKey.upper()))
            check.setChecked(defaultChecked)
            self.formatChecks[formatKey] = check
            layout.addWidget(check)
        layout.addStretch(1)

        self.tabs.addTab(tab, self.lan.get("batchTabOutput", "Output"))

    # --- Cross-tab config assembly ------------------------------------------

    def collectConfigData(self):
        configData = self.batchConfigStore.defaultConfig()
        configData["configName"] = self.configNameInput.text()
        configData["epsgInput"] = self.epsgInput.text().strip() or "EPSG:5514"
        configData["trackSources"] = list(self.trackSources)
        configData["chainageMode"] = self.chainageModeCombo.currentData()
        configData["startChainageKm"] = 0.0
        configData["stopsProfiles"] = list(self.stopsProfiles)
        configData["designApproaches"] = self.collectDesignApproaches()
        configData["sweep"] = self.collectSweepConfig()
        configData["optimizationScenarios"] = self.collectOptimizationScenarios()
        configData["includeBaselineScenario"] = self.includeBaselineCheck.isChecked()
        configData["calculationMode"] = self.calculationModeCombo.currentData()
        configData["designProfile"] = self.designProfileCombo.currentData()
        configData["runVehicles"] = self.runVehiclesCheck.isChecked()
        configData["baseSettings"] = copy.deepcopy(self.settingsData)
        configData["exportFormats"] = {key: check.isChecked() for key, check in self.formatChecks.items()}
        return configData

    # Toggle the themed error styling on the variant preview label
    def setPreviewError(self, isError):
        self.variantPreviewLabel.setProperty("errorState", isError)
        self.variantPreviewLabel.style().unpolish(self.variantPreviewLabel)
        self.variantPreviewLabel.style().polish(self.variantPreviewLabel)

    def refreshVariantPreview(self, *args):
        if not self.isFullyBuilt:
            return
        configData = self.collectConfigData()
        problems = self.batchConfigStore.validateConfig(configData)
        if problems:
            self.variantPreviewLabel.setText("; ".join(self.lan.get(code, code) for code in problems))
            self.setPreviewError(True)
            return
        try:
            variantCount = len(batch_config.expandVariantSpecs(configData))
            previewText = self.lan.get("batchVariantPreview", "{count} variants will be executed")
            self.variantPreviewLabel.setText(previewText.format(count=variantCount))
            self.setPreviewError(False)
        except ValueError as exc:
            self.variantPreviewLabel.setText(str(exc))
            self.setPreviewError(True)

    def onAccept(self):
        configData = self.collectConfigData()
        problems = self.batchConfigStore.validateConfig(configData)
        if problems:
            QMessageBox.warning(self, self.lan.get("error", "Error"),
                                "\n".join(self.lan.get(code, code) for code in problems))
            return
        self.finalConfigData = configData
        self.accept()

    def getBatchConfig(self):
        return self.finalConfigData

    # --- Preset persistence --------------------------------------------------

    def savePresetFile(self):
        filePath, _ = QFileDialog.getSaveFileName(
            self, self.lan.get("batchSavePreset", "Save preset..."), "", "JSON Files (*.json)")
        if not filePath:
            return
        try:
            self.batchConfigStore.saveConfig(filePath, self.collectConfigData())
        except OSError as exc:
            QMessageBox.critical(self, self.lan.get("error", "Error"), str(exc))

    def loadPresetFile(self):
        filePath, _ = QFileDialog.getOpenFileName(
            self, self.lan.get("batchLoadPreset", "Load preset..."), "", "JSON Files (*.json)")
        if not filePath:
            return
        try:
            configData = self.batchConfigStore.loadConfig(filePath)
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, self.lan.get("error", "Error"), str(exc))
            return
        self.applyConfigData(configData)

    def applyConfigData(self, configData):
        self.configNameInput.setText(configData.get("configName", ""))

        self.trackSources = list(configData.get("trackSources", []))
        self.refreshTrackSourceList()
        self.epsgInput.setText(configData.get("epsgInput", "EPSG:5514"))
        chainageIndex = self.chainageModeCombo.findData(configData.get("chainageMode", "sequential"))
        self.chainageModeCombo.setCurrentIndex(max(0, chainageIndex))

        self.stopsProfiles = list(configData.get("stopsProfiles", []))
        self.refreshStopsProfileList()

        self.approachTable.setRowCount(0)
        for approach in configData.get("designApproaches", []):
            levels = approach.get("approach", {})
            self.addApproachRow(approach.get("label", ""), levels.get("I", "standard"), levels.get("dI", "standard"),
                                levels.get("nLin", "standard"), levels.get("nILin", "standard"))

        self.scenarioTable.setRowCount(0)
        for scenario in configData.get("optimizationScenarios", []):
            self.addOptimizationScenarioRow(scenario.get("label", ""),
                                            scenario.get("modeLcl", geometry_engine.OPTIMIZATION_MODE_NONE),
                                            scenario.get("modeLscsl", geometry_engine.OPTIMIZATION_MODE_SHIFT_AND_EXTEND),
                                            scenario.get("dMaxM", 0.5), scenario.get("lMinM", 25.0),
                                            scenario.get("lkMaxM", geometry_engine.DEFAULT_LK_MAX_M))
        self.includeBaselineCheck.setChecked(bool(configData.get("includeBaselineScenario", True)))

        sweep = configData.get("sweep", {})
        self.sweepEnabledCheck.setChecked(bool(sweep.get("isEnabled", False)))
        paramIndex = self.sweepParamCombo.findData(sweep.get("paramKey", ""))
        if paramIndex >= 0:
            self.sweepParamCombo.setCurrentIndex(paramIndex)
        self.sweepMinInput.setText(str(sweep.get("minValue", 0.0)))
        self.sweepMaxInput.setText(str(sweep.get("maxValue", 0.0)))
        self.sweepStepInput.setText(str(sweep.get("stepValue", 1.0)))

        self.calculationModeCombo.setCurrentIndex(max(0, self.calculationModeCombo.findData(
            configData.get("calculationMode", "design"))))
        self.designProfileCombo.setCurrentIndex(max(0, self.designProfileCombo.findData(
            configData.get("designProfile", "I150"))))
        self.runVehiclesCheck.setChecked(bool(configData.get("runVehicles", True)))

        exportFormats = configData.get("exportFormats", {})
        for key, check in self.formatChecks.items():
            check.setChecked(bool(exportFormats.get(key, check.isChecked())))

        self.refreshVariantPreview()
