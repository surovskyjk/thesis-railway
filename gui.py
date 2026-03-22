# PySide6 imports
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QTabWidget, QApplication, QMainWindow, QPushButton, QWidget,
                                QHBoxLayout, QVBoxLayout, QLabel, QPlainTextEdit, QFileDialog, 
                                QSplitter, QMessageBox, QStyle, QToolBar)
from PySide6.QtGui import QAction, QIcon

# pyqtgraph imports
import pyqtgraph as pg

# Matplotlib imports for Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

# numpy import for data handling
import numpy as np

# Local imports

import lang
import readfile
import gui_overlay
from map_viewer import MapWidget


class MplCanvas(FigureCanvas):
    # Canvas widget for Matplotlib plots
    def __init__(self, parent=None, width=5, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        
        self.ax_speed = self.fig.add_subplot(211)

        self.ax_cant = self.fig.add_subplot(212, sharex=self.ax_speed)

        self.ax_curvature = self.ax_cant.twinx()

        super().__init__(self.fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window settings

        self.resize(QSize(1000, 800))
        self.current_language = "en"
        lan = lang.DIC[self.current_language]
        self.setWindowTitle(lan["app_title"])

        # Other default settings
        self.epsgInput = "EPSG:5514"

        # Empty dictionaries for data to be loaded and plotted

        self.dataStorage = {}
        self.plotCantData = {}
        self.plotCurvatureData = {}
        self.plotSpeedData = {}

        # Layouts - main grid

        # layoutH = QHBoxLayout()
        # layoutV = QVBoxLayout()
        # layoutPlots = QVBoxLayout()
        layoutTabsXML = QTabWidget()
        self.layoutTabsPlots = QTabWidget()

        # Central widget - Main Splitter

        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.addWidget(layoutTabsXML)
        self.main_splitter.addWidget(self.layoutTabsPlots)
        self.setCentralWidget(self.main_splitter)

        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 2)

        # Menu bar
        main_menu = self.menuBar()
        self.fileMenu = main_menu.addMenu(lan["file"])
        self.cleanMenu = main_menu.addMenu(lan["clean"])
        self.settingsMenu = main_menu.addMenu(lan["settings"])
        self.viewMenu = main_menu.addMenu(lan["view"])
        self.exitMenu = main_menu.addMenu(lan["exit"])
        self.helpMenu = main_menu.addMenu(lan["help"])

        # Submenu - File
        openFileAction = QAction(lan["open_file"], self)
        self.fileMenu.addAction(openFileAction)
        openFileAction.triggered.connect(self.openFile)

        autodetect_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon)
        autodetectXMLAction = QAction(autodetect_icon, lan["autodetect"], self)
        self.fileMenu.addAction(autodetectXMLAction)
        autodetectXMLAction.setStatusTip(lan["autodetect_tip"])
        autodetectXMLAction.setShortcut("Ctrl+O")
        autodetectXMLAction.triggered.connect(self.openAutodetectXML)

        openParseLandXMLAction = QAction(lan["open_parse_landxml"], self)
        self.fileMenu.addAction(openParseLandXMLAction)
        openParseLandXMLAction.triggered.connect(self.openLandXML)

        openParseXMLTTPAction = QAction(lan["open_parse_xmlttp"], self)      
        self.fileMenu.addAction(openParseXMLTTPAction)
        self.fileMenu.addSeparator()
        openParseXMLTTPAction.triggered.connect(self.openXMLTTP)
        
        # Submenu - Clean
        cleanTTPDataAction = QAction(lan["cleanTTP"], self)
        self.cleanMenu.addAction(cleanTTPDataAction)
        cleanTTPDataAction.triggered.connect(self.cleanTTPData)

        cleanLandXMLDataAction = QAction(lan["cleanLandXML"], self)
        self.cleanMenu.addAction(cleanLandXMLDataAction)
        cleanLandXMLDataAction.triggered.connect(self.cleanLandXMLData)

        cleanDataAction = QAction(lan["cleanAll"], self)
        self.cleanMenu.addAction(cleanDataAction)
        cleanDataAction.triggered.connect(self.cleanData)

        # Submenu - Settings
        self.languageMenu = self.settingsMenu.addMenu(lan["language"])
        self.settingsMenu.addSeparator()
        

        # Sub-submenu - Languages
        langCZAction = QAction("Čeština", self)
        self.languageMenu.addAction(langCZAction)
        langCZAction.triggered.connect(lambda: self.change_language("cz"))

        langENAction = QAction("English", self)
        self.languageMenu.addAction(langENAction)
        langENAction.triggered.connect(lambda: self.change_language("en"))

        langDEAction = QAction("Deutsch", self)
        self.languageMenu.addAction(langDEAction)
        langDEAction.triggered.connect(lambda: self.change_language("de"))

        # Sub-submenu - Map settings
        mapSettingsAction = QAction(lan["mapSettings"], self)
        self.settingsMenu.addAction(mapSettingsAction)
        mapSettingsAction.triggered.connect(self.openMapSettings)

        # Submenu - View
        self.toggleCantAction = QAction(lan["cant"], self)
        self.toggleCantAction.setCheckable(True)
        self.toggleCantAction.setChecked(True)
        self.toggleCantAction.triggered.connect(self.toggleCantVisibility)
        self.viewMenu.addAction(self.toggleCantAction)

        self.toggleCantPossibleAction = QAction(lan["cant_possible"], self)
        self.toggleCantPossibleAction.setCheckable(True)
        self.toggleCantPossibleAction.setChecked(True)
        self.toggleCantPossibleAction.triggered.connect(self.toggleCantPossibleVisibility)
        self.viewMenu.addAction(self.toggleCantPossibleAction)

        self.toggleCantDefPossibleAction = QAction(lan["cant_def_possible"], self)
        self.toggleCantDefPossibleAction.setCheckable(True)
        self.toggleCantDefPossibleAction.setChecked(True)
        self.toggleCantDefPossibleAction.triggered.connect(self.toggleCantDefPossibleVisibility)
        self.viewMenu.addAction(self.toggleCantDefPossibleAction)

        self.toggleCantPlusCantDefPossibleAction = QAction(lan["cant_plus_cant_def_possible"], self)
        self.toggleCantPlusCantDefPossibleAction.setCheckable(True)
        self.toggleCantPlusCantDefPossibleAction.setChecked(True)
        self.toggleCantPlusCantDefPossibleAction.triggered.connect(self.toggleCantPlusCantDefPossibleVisibility)
        self.viewMenu.addAction(self.toggleCantPlusCantDefPossibleAction)
        
        self.toggleCurvatureAction = QAction(lan["curvature"], self)
        self.toggleCurvatureAction.setCheckable(True)
        self.toggleCurvatureAction.setChecked(True)
        self.toggleCurvatureAction.triggered.connect(self.toggleCurvatureVisibility)
        self.viewMenu.addAction(self.toggleCurvatureAction)

        self.toggleCurvatureNewAction = QAction(lan["curvature_new"], self)
        self.toggleCurvatureNewAction.setCheckable(True)
        self.toggleCurvatureNewAction.setChecked(True)
        self.toggleCurvatureNewAction.triggered.connect(self.toggleCurvatureNewVisibility)
        self.viewMenu.addAction(self.toggleCurvatureNewAction)

        self.viewMenu.addSeparator()

        self.toggleSpeedAction = QAction(lan["speed_lim"], self)
        self.toggleSpeedAction.setCheckable(True)
        self.toggleSpeedAction.setChecked(True)
        self.toggleSpeedAction.triggered.connect(self.toggleSpeedVisibility)
        self.viewMenu.addAction(self.toggleSpeedAction)

        self.toggleSpeed100Action = QAction(lan["speed_lim_100"], self)
        self.toggleSpeed100Action.setCheckable(True)
        self.toggleSpeed100Action.setChecked(True)
        self.toggleSpeed100Action.triggered.connect(self.toggleSpeed100Visibility)
        self.viewMenu.addAction(self.toggleSpeed100Action)

        self.toggleSpeed130Action = QAction(lan["speed_lim_130"], self)
        self.toggleSpeed130Action.setCheckable(True)
        self.toggleSpeed130Action.setChecked(True)
        self.toggleSpeed130Action.triggered.connect(self.toggleSpeed130Visibility)
        self.viewMenu.addAction(self.toggleSpeed130Action)

        self.toggleSpeed150Action = QAction(lan["speed_lim_150"], self)
        self.toggleSpeed150Action.setCheckable(True)
        self.toggleSpeed150Action.setChecked(True)
        self.toggleSpeed150Action.triggered.connect(self.toggleSpeed150Visibility)
        self.viewMenu.addAction(self.toggleSpeed150Action)

        self.toggleSpeedKAction = QAction(lan["speed_lim_K"], self)
        self.toggleSpeedKAction.setCheckable(True)
        self.toggleSpeedKAction.setChecked(True)
        self.toggleSpeedKAction.triggered.connect(self.toggleSpeedKVisibility)
        self.viewMenu.addAction(self.toggleSpeedKAction)

        # Submenu - Exit
        exitAction = QAction(lan["exit"], self)
        self.exitMenu.addAction(exitAction)
        exitAction.triggered.connect(self.close)
        
        # Submenus - Help


        # Create toolbar for the most common actions
        toolbar = self.addToolBar(lan["toolbar"])
        toolbar.addAction(autodetectXMLAction)

        # Widgets for XML parsing tabs
        # Raw data
        self.textboxRawLandXML = QPlainTextEdit()
        self.textboxRawTTP = QPlainTextEdit()
        self.textboxRawLandXML.setReadOnly(True)
        self.textboxRawTTP.setReadOnly(True)

        # Parsed data tables
        self.tableTTP = pg.TableWidget(sortable = False)
        self.tableLandXML = pg.TableWidget(sortable = False)

        # Layout and containers for XML tabs
        layoutXMLTTP_container = QWidget()
        layoutXMLLand_container = QWidget()
                
        layoutXMLTTP = QVBoxLayout(layoutXMLTTP_container)
        layoutXMLTTP.setContentsMargins(0,0,0,0)
        layoutXMLTTP.setSpacing(0)
        layoutXMLLand = QVBoxLayout(layoutXMLLand_container)
        layoutXMLLand.setContentsMargins(0,0,0,0)
        layoutXMLLand.setSpacing(0)

        splitterXMLTTP = QSplitter(Qt.Orientation.Vertical)
        splitterXMLLand = QSplitter(Qt.Orientation.Vertical)
        
        layoutXMLTTPRaw_container = QWidget()
        layoutXMLTTPRaw = QVBoxLayout(layoutXMLTTPRaw_container)
        layoutXMLTTPRaw.setContentsMargins(0,0,0,0)
        layoutXMLTTPRaw.setSpacing(0)
        layoutXMLLandRaw_container = QWidget()
        layoutXMLLandRaw = QVBoxLayout(layoutXMLLandRaw_container)
        layoutXMLLandRaw.setContentsMargins(0,0,0,0)
        layoutXMLLandRaw.setSpacing(0)
        layoutXMLTTPParsed_container =QWidget()
        layoutXMLTTPParsed = QVBoxLayout(layoutXMLTTPParsed_container)
        layoutXMLTTPParsed.setContentsMargins(0,0,0,0)
        layoutXMLTTPParsed.setSpacing(0)    
        layoutXMLLandParsed_container = QWidget()
        layoutXMLLandParsed = QVBoxLayout(layoutXMLLandParsed_container)
        layoutXMLLandParsed.setContentsMargins(0,0,0,0)
        layoutXMLLandParsed.setSpacing(0)

        self.labelXMLTTPRaw = QLabel(lan["raw_data"])
        self.labelXMLTTPParsed = QLabel(lan["parsed_data"])
        self.labelLandXMLRaw = QLabel(lan["raw_data"])
        self.labelLandXMLParsed = QLabel(lan["parsed_data"])

        layoutXMLTTPRaw.addWidget(self.labelXMLTTPRaw, stretch=0)
        layoutXMLTTPRaw.addWidget(self.textboxRawTTP, stretch=1)
        layoutXMLTTPParsed.addWidget(self.labelXMLTTPParsed, stretch=0)
        layoutXMLTTPParsed.addWidget(self.tableTTP, stretch=1)
    
        layoutXMLLandRaw.addWidget(self.labelLandXMLRaw, stretch=0)
        layoutXMLLandRaw.addWidget(self.textboxRawLandXML, stretch=1)
        layoutXMLLandParsed.addWidget(self.labelLandXMLParsed, stretch=0)
        layoutXMLLandParsed.addWidget(self.tableLandXML, stretch=1)
        

        splitterXMLTTP.addWidget(layoutXMLTTPRaw_container)
        splitterXMLTTP.addWidget(layoutXMLTTPParsed_container)
        splitterXMLLand.addWidget(layoutXMLLandRaw_container)
        splitterXMLLand.addWidget(layoutXMLLandParsed_container)

        layoutXMLTTP.addWidget(splitterXMLTTP)
        layoutXMLLand.addWidget(splitterXMLLand)

        # Tabs for XML parsing
        layoutTabsXML.setTabPosition(QTabWidget.TabPosition.West)
        layoutTabsXML.addTab(layoutXMLLand_container, "LandXML")
        layoutTabsXML.addTab(layoutXMLTTP_container, "XML TTP")

        # Plot tabs (plots and map)
        self.layoutTabsPlots_container = QWidget()
        layoutPlots = QVBoxLayout(self.layoutTabsPlots_container)
        layoutPlots.setContentsMargins(0,0,0,0)
        layoutPlots.setSpacing(0)
        self.layoutTabsPlotsMap_container = QWidget()
        layoutPlotsMap = QVBoxLayout(self.layoutTabsPlotsMap_container)
        layoutPlotsMap.setContentsMargins(0,0,0,0)
        layoutPlotsMap.setSpacing(0)

        # Matplotlib canvas - add widget for plots
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layoutPlots.addWidget(self.canvas, stretch=3)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layoutPlots.addWidget(self.toolbar)

        # Map - add widget for maps
        self.mapWidget = MapWidget(self)
        layoutPlotsMap.addWidget(self.mapWidget)

        # Tabs for plots
        self.layoutTabsPlots.setTabPosition(QTabWidget.TabPosition.East)
        self.layoutTabsPlots.addTab(self.layoutTabsPlots_container, lan["plots"])
        
        # Tab for map
        self.layoutTabsPlots.addTab(self.layoutTabsPlotsMap_container,lan["map"])

        # Change language function
    def change_language(self, lang_code):
        self.current_language = lang_code
        self.update_texts()

    def update_texts(self):
        lan = lang.DIC[self.current_language]

        # Update menu texts
        self.setWindowTitle(lan["app_title"])
        self.fileMenu.setTitle(lan["file"])
        self.settingsMenu.setTitle(lan["settings"])
        self.languageMenu.setTitle(lan["language"])
        self.viewMenu.setTitle(lan["view"])
        self.cleanMenu.setTitle(lan["clean"])
        self.exitMenu.setTitle(lan["exit"])
        self.helpMenu.setTitle(lan["help"])

        self.fileMenu.actions()[0].setText(lan["open_file"])
        self.fileMenu.actions()[1].setText(lan["autodetect"])
        self.fileMenu.actions()[2].setText(lan["open_parse_landxml"])
        self.fileMenu.actions()[3].setText(lan["open_parse_xmlttp"])

        self.settingsMenu.actions()[2].setText(lan["mapSettings"])

        self.viewMenu.actions()[0].setText(lan["cant"])
        self.viewMenu.actions()[1].setText(lan["cant_possible"])
        self.viewMenu.actions()[2].setText(lan["cant_def_possible"])
        self.viewMenu.actions()[3].setText(lan["cant_plus_cant_def_possible"])
        self.viewMenu.actions()[4].setText(lan["curvature"])
        self.viewMenu.actions()[5].setText(lan["curvature_new"])
        self.viewMenu.actions()[7].setText(lan["speed_lim"])
        self.viewMenu.actions()[8].setText(lan["speed_lim_100"])
        self.viewMenu.actions()[9].setText(lan["speed_lim_130"])
        self.viewMenu.actions()[10].setText(lan["speed_lim_150"])
        self.viewMenu.actions()[11].setText(lan["speed_lim_K"])


        # Update labels
        self.labelXMLTTPRaw.setText(lan["raw_data"])
        self.labelXMLTTPParsed.setText(lan["parsed_data"])
        self.labelLandXMLRaw.setText(lan["raw_data"])
        self.labelLandXMLParsed.setText(lan["parsed_data"])

        # Update matplotlib canvas

        self.canvas.ax_speed.set_xlabel(lan["station"])
        self.canvas.ax_speed.set_ylabel(lan["speed_lim"])
        self.canvas.ax_speed.set_title(f'{lan["speed_lim"]} vs {lan["station"]}')
        
        self.canvas.ax_cant.set_xlabel(lan["station"])
        self.canvas.ax_cant.set_ylabel(lan["cant"])
        self.canvas.ax_cant.set_title(f'{lan["cant"]} vs {lan["station"]}', loc = 'left')

        self.canvas.ax_curvature.set_xlabel(lan["station"])
        self.canvas.ax_curvature.set_ylabel(lan["curvature"])
        self.canvas.ax_curvature.set_title(f'{lan["curvature"]} vs {lan["station"]}', loc ='right')


        # Update legends
        if self.canvas.ax_speed.lines:
            self.canvas.ax_speed.lines[0].set_label(lan["speed_lim"])
            self.canvas.ax_speed.legend()

        if self.canvas.ax_cant.lines:
            self.canvas.ax_cant.lines[0].set_label(lan["cant"])
            self.canvas.ax_cant.legend(loc = 'upper left')

        if self.canvas.ax_curvature.lines:
            self.canvas.ax_curvature.lines[0].set_label(lan["curvature"])
            self.canvas.ax_curvature.legend(loc = 'upper right')

        self.canvas.draw()


    def getFileContent(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt);;XML Files (*.xml)")
        
        # If cancelled, do nothing
        
        if not filepath:
            return
        
        # Read file content

        file_content = readfile.ReadFile().Read(filepath)
        return file_content
    
    def openFile(self):
        file_content = self.getFileContent()
        if file_content is not None:
            self.textboxRawLandXML.setPlainText(file_content)

    def openAutodetectXML(self):
        file_content = self.getFileContent()
        if file_content is None:
            return
        
        xml_type = readfile.ReadFile().XMLType(file_content)
        if xml_type == 1:
            self.parseLandXML(file_content)
        elif xml_type == 2:
            self.parseXMLTTP(file_content)
        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["unknown_xml_type"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def openLandXML(self):
        file_content = self.getFileContent()
        self.parseLandXML(file_content)

    def openXMLTTP(self):
        file_content = self.getFileContent()
        self.parseXMLTTP(file_content)

    def parseLandXML(self, file_content):
        #file_content = self.getFileContent()
        if file_content is not None:
            self.textboxRawLandXML.setPlainText(file_content)
            LandXMLData = readfile.ReadFile().ParseLandXML(file_content, self.epsgInput)
            self.updateTableLandXML(LandXMLData)
            self.dataStorage["stationHorizontal"] = LandXMLData["stationHorizontal"]
            self.dataStorage["stationCant"] = LandXMLData["stationCant"]
            self.dataStorage["cant"] = LandXMLData["cant"]
            self.dataStorage["curvature"] = LandXMLData["curvature"]
            self.plotCant()
            self.plotCurvature()

            alignment = LandXMLData["alignmentCoordinates"]
            self.mapWidget.drawAlignment(alignment)

        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["no_file"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def parseXMLTTP(self, file_content):
        #file_content = self.getFileContent()
        if file_content is not None:
            self.textboxRawTTP.setPlainText(file_content)
            XMLTTPData = readfile.ReadFile().ParseXMLTTP(file_content)

            lan = lang.DIC[self.current_language]

            self.dataStorage["stationSpeedLimits"] = XMLTTPData["stationSpeedLimits"]
            self.dataStorage["speedLimits"] = XMLTTPData["speedLimits"]

            validStationSpeedLimits = (self.dataStorage["speedLimits"] != 0) & ~np.isnan(self.dataStorage["speedLimits"])
            
            self.dataStorage["stationSpeedLimits"] = self.dataStorage["stationSpeedLimits"][validStationSpeedLimits]
            self.dataStorage["speedLimits"] = self.dataStorage["speedLimits"][validStationSpeedLimits]

            sections = self.TTPSections(self.dataStorage["stationSpeedLimits"])

            if len(sections) > 0:
                sectionsInfo = []

                # Create a list of section descriptions for the dialog
                for i, section in enumerate(sections):
                    sectionsInfo.append(f"{lan['station']} {section['stationStart']:.6f} km - {section['stationEnd']:.6f} km")

                # LandXML data availability check for cropping option in TTP sections dialog
                HasLandXML = "stationHorizontal" in self.dataStorage and len(self.dataStorage["stationHorizontal"]) > 0

                # Show the section selection dialog
                dialog = gui_overlay.TTPSelectSectionDialog(sectionsInfo, HasLandXML, lan, self)
                if dialog.exec():
                    selectedSectionIDs, cropToLandXML, loadAll = dialog.get_selected_section()
                else:
                    return  # User cancelled the dialog, do nothing
            
            else:
                selectedSectionIDs = []
                HasLandXML = False
                cropToLandXML = False
                loadAll = True

            # Extract data from central storage
            stationsRaw = np.array(self.dataStorage["stationSpeedLimits"])
            speedLimitsRaw = np.array(self.dataStorage["speedLimits"])

            # Crop to LandXML data range if option is selected and LandXML data is available
            if not loadAll:
                if not selectedSectionIDs:
                    return

                tempStations = []
                tempSpeedLimits = []

                for sectionID in sorted(selectedSectionIDs):
                    currentSection = sections[sectionID]
                    startID = currentSection["startID"]
                    endID = currentSection["endID"]+1

                    tempStations.append(stationsRaw[startID:endID])
                    tempSpeedLimits.append(speedLimitsRaw[startID:endID])

                stationsRaw = np.concatenate(tempStations)
                speedLimitsRaw = np.concatenate(tempSpeedLimits)

            if cropToLandXML and HasLandXML:
                LandXMLMin = np.nanmin(self.dataStorage["stationHorizontal"])
                LandXMLMax = np.nanmax(self.dataStorage["stationHorizontal"])

                if np.isnan(LandXMLMin) or np.isnan(LandXMLMax):
                    stations = stationsRaw
                    speedLimits = speedLimitsRaw
                else:

                    beforeMinMask = stationsRaw <= LandXMLMin
                    if np.any(beforeMinMask):
                        lastBefore = np.where(beforeMinMask)[0][-1]
                        speedLimitAtMin = speedLimitsRaw[lastBefore]
                    else:
                        speedLimitAtMin = speedLimitsRaw[0] if len(speedLimitsRaw) > 0 else 0
                    
                    validMask = (stationsRaw > LandXMLMin) & (stationsRaw < LandXMLMax)

                    stationsInside = stationsRaw[validMask]
                    speedLimitsInside = speedLimitsRaw[validMask]

                    stationsCropped = [LandXMLMin]
                    speedLimitsCropped = [speedLimitAtMin]
                    
                    stationsCropped.extend(stationsInside.tolist())
                    speedLimitsCropped.extend(speedLimitsInside.tolist())
                    
                    if stationsCropped[-1] < LandXMLMax:
                        stationsCropped.append(LandXMLMax)
                        speedLimitsCropped.append(speedLimitsCropped[-1])

                    stations = np.array(stationsCropped, dtype = float)
                    speedLimits = np.array(speedLimitsCropped, dtype = float)
            
            else:
                stations = stationsRaw
                speedLimits = speedLimitsRaw

            self.dataStorage["stationSpeedLimits"] = stations
            self.dataStorage["speedLimits"] = speedLimits

            TTPData = {
                "stationSpeedLimits": stations,
                "speedLimits": speedLimits
            }

            self.tableTTP.setData(TTPData)
            self.plotSpeedLimits()
        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["no_file"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def plotCant(self):
        lan = lang.DIC[self.current_language]

        self.canvas.ax_cant.clear()
        self.plotCantData.clear()

        stationCant = self.dataStorage.get("stationCant")
        stationCantPossible = self.dataStorage.get("stationCantPossible")

        if (stationCant is None or len(stationCant) == 0) and (stationCantPossible is None or len(stationCantPossible) == 0):
            self.canvas.draw()
            return

        cant = self.dataStorage.get("cant")
        if (cant is not None and len(cant)>0) and (stationCant is not None and len(stationCant)>0):
            line, = self.canvas.ax_cant.plot(stationCant, cant, marker='o', linestyle='-', color='tab:blue', label=lan["cant"])
            self.plotCantData["cant"] = line
            line.set_visible(self.toggleCantAction.isChecked())

        cantPossible = self.dataStorage.get("cantPossible")
        if (cantPossible is not None and len(cantPossible)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvas.ax_cant.plot(stationCantPossible, cantPossible, marker='o', linestyle='-', color='tab:orange', label=lan["cant_possible"])
            self.plotCantData["cantPossible"] = line
            line.set_visible(self.toggleCantPossibleAction.isChecked())

        cantDefPossible = self.dataStorage.get("cantDefPossible")
        if (cantDefPossible is not None and len(cantDefPossible)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvas.ax_cant.plot(stationCantPossible, cantDefPossible, marker='o', linestyle='-', color='tab:green', label=lan["cant_def_possible"])
            self.plotCantData["cantDefPossible"] = line
            line.set_visible(self.toggleCantDefPossibleAction.isChecked())

        cantPlusCantDefPossible = self.dataStorage.get("cantPlusCantDefPossible")
        if (cantPlusCantDefPossible is not None and len(cantPlusCantDefPossible)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvas.ax_cant.plot(stationCantPossible, cantPlusCantDefPossible, marker='o', linestyle='-', color='tab:red', label=lan["cant_plus_cant_def_possible"])
            self.plotCantData["cantPlusCantDefPossible"] = line
            line.set_visible(self.toggleCantPlusCantDefPossibleAction.isChecked())

        self.canvas.ax_cant.grid(True)
        self.canvas.ax_cant.autoscale(enable=True, axis='x', tight=True)
        self.canvas.ax_cant.set_xlabel(lan["station"])
        self.canvas.ax_cant.set_ylabel(lan["cant"])
        self.canvas.ax_cant.set_title(f'{lan["cant"]} vs {lan["station"]}', loc = 'left')
        self.canvas.ax_cant.tick_params(axis='y', labelcolor='tab:blue')
        if self.canvas.ax_cant.lines:
            self.canvas.ax_cant.legend(loc = 'upper left')
        self.canvas.draw()

    def plotCurvature(self):
        lan = lang.DIC[self.current_language]

        self.canvas.ax_curvature.clear()
        self.plotCurvatureData.clear()

        # Initial check to avoid plotting data without station available
        stationHorizontal = self.dataStorage.get("stationHorizontal")
        stationHorizontalNew = self.dataStorage.get("stationHorizontalNew")
        if (stationHorizontal is None or len(stationHorizontal) == 0) and (stationHorizontalNew is None or len(stationHorizontalNew) == 0):
            self.canvas.draw()
            return  # No data to plot
        
        def fractionFormatter(x, pos = None):
            if np.isclose(x, 0, atol=1e-6):
                return "0"
            else:
                return f"1/{int(round(1/x))}"

        curvature = self.dataStorage.get("curvature")
        if (curvature is not None and len(curvature) > 0) and (stationHorizontal is not None and len(stationHorizontal) > 0):
            line, = self.canvas.ax_curvature.plot(stationHorizontal, curvature, marker='o', linestyle='-', color='tab:orange', label=lan["curvature"])
            self.plotCurvatureData["curvature"] = line
            line.set_visible(self.toggleCurvatureAction.isChecked())

        curvatureNew = self.dataStorage.get("curvatureNew")
        if (curvatureNew is not None and len(curvatureNew) > 0) and (stationHorizontalNew is not None and len(stationHorizontalNew) > 0):
            line, = self.canvas.ax_curvature.plot(stationHorizontalNew, curvatureNew, marker='o', linestyle='-', color='tab:green', label=lan["curvature"])
            self.plotCurvatureData["curvatureNew"] = line
            line.set_visible(self.toggleCurvatureNewAction.isChecked())
        
        self.canvas.ax_curvature.yaxis.set_label_position("right")
        self.canvas.ax_curvature.yaxis.tick_right()
        self.canvas.ax_curvature.grid(True)
        self.canvas.ax_curvature.autoscale(enable=True, axis='x', tight=True)
        self.canvas.ax_curvature.set_xlabel(lan["station"])
        self.canvas.ax_curvature.set_ylabel(lan["curvature"])
        self.canvas.ax_curvature.set_title(f'{lan["curvature"]} vs {lan["station"]}', loc ='right')
        self.canvas.ax_curvature.tick_params(axis='y', labelcolor='tab:orange')
        self.canvas.ax_curvature.yaxis.set_major_formatter(FuncFormatter(fractionFormatter))
        self.canvas.ax_curvature.legend(loc = 'upper right')
        self.canvas.draw()

    def plotSpeedLimits(self):
        lan = lang.DIC[self.current_language]

        self.canvas.ax_speed.clear()


        stationSpeedLimits = self.dataStorage.get("stationSpeedLimits")
        stationSpeed100 = self.dataStorage.get("stationSpeed100")
        stationSpeed130 = self.dataStorage.get("stationSpeed130")
        stationSpeed150 = self.dataStorage.get("stationSpeed150")
        stationSpeedK = self.dataStorage.get("stationSpeedK")

        if (stationSpeedLimits is None or len(stationSpeedLimits) == 0) and (stationSpeed100 is None or len(stationSpeed100) == 0) and (stationSpeed130 is None or len(stationSpeed130) == 0) and (stationSpeed150 is None or len(stationSpeed150) == 0) and (stationSpeedK is None or len(stationSpeedK) == 0):
            self.canvas.draw()
            return  # No data to plot
        
        speedLimits = self.dataStorage.get("speedLimits")
        if (speedLimits is not None and len(speedLimits) > 0) and (stationSpeedLimits is not None and len(stationSpeedLimits) > 0):
            line, = self.canvas.ax_speed.step(stationSpeedLimits, speedLimits, where="post", marker='s', linestyle='-', label=lan["speed_lim"])
            self.plotSpeedData["speedLimits"] = line
            line.set_visible(self.toggleSpeedAction.isChecked())

        speedLimits100 = self.dataStorage.get("speedLimits100")
        if (speedLimits100 is not None and len(speedLimits100) > 0) and (stationSpeed100 is not None and len(stationSpeed100) > 0):
            line, = self.canvas.ax_speed.step(stationSpeed100, speedLimits100, where="post", marker='s', linestyle='-', label=lan["speed_lim_100"])
            self.plotSpeedData["speedLimits100"] = line
            line.set_visible(self.toggleSpeed100Action.isChecked())

        speedLimits130 = self.dataStorage.get("speedLimits130")
        if (speedLimits130 is not None and len(speedLimits130) > 0) and (stationSpeed130 is not None and len(stationSpeed130) > 0):
            line, = self.canvas.ax_speed.step(stationSpeed130, speedLimits130, where="post", marker='s', linestyle='-', label=lan["speed_lim_130"])
            self.plotSpeedData["speedLimits130"] = line
            line.set_visible(self.toggleSpeed130Action.isChecked())

        speedLimits150 = self.dataStorage.get("speedLimits150")
        if (speedLimits150 is not None and len(speedLimits150) > 0) and (stationSpeed150 is not None and len(stationSpeed150) > 0):
            line, = self.canvas.ax_speed.step(stationSpeed150, speedLimits150, where="post", marker='s', linestyle='-', label=lan["speed_lim_150"])
            self.plotSpeedData["speedLimits150"] = line
            line.set_visible(self.toggleSpeed150Action.isChecked())

        speedLimitsK = self.dataStorage.get("speedLimitsK")
        if (speedLimitsK is not None and len(speedLimitsK) > 0) and (stationSpeedK is not None and len(stationSpeedK) > 0):
            line, = self.canvas.ax_speed.step(stationSpeedK, speedLimitsK, where="post", marker='s', linestyle='-', label=lan["speed_lim_K"])
            self.plotSpeedData["speedLimitsK"] = line
            line.set_visible(self.toggleSpeedKAction.isChecked())

        self.canvas.ax_speed.grid(True)
        self.canvas.ax_speed.autoscale(enable=True, axis='x', tight=True)
        self.canvas.ax_speed.set_xlabel(lan["station"])
        self.canvas.ax_speed.set_ylabel(lan["speed_lim"])
        self.canvas.ax_speed.set_title(f'{lan["speed_lim"]} vs {lan["station"]}')
        self.canvas.ax_speed.legend()
        self.canvas.draw()


    def cleanData(self):
        self.textboxRawLandXML.setPlainText("")
        self.textboxRawTTP.setPlainText("")
        self.tableLandXML.setData({})
        self.tableTTP.setData({})
        self.canvas.ax_cant.clear()
        self.canvas.ax_speed.clear()
        self.canvas.ax_curvature.clear()
        self.dataStorage.clear()
        self.plotCantData.clear()
        self.plotSpeedData.clear()
        self.plotCurvatureData.clear()
        self.canvas.draw()


    def cleanTTPData(self):
        self.textboxRawTTP.setPlainText("")
        self.tableTTP.setData({})
        while self.canvas.ax_speed.lines:
            self.canvas.ax_speed.lines[0].remove()
        self.dataStorage["stationSpeedLimits"] = []
        self.dataStorage["speedLimits"] = []
        self.plotSpeedData.clear()
        self.canvas.draw()


    def cleanLandXMLData(self):
        self.textboxRawLandXML.setPlainText("")
        self.tableLandXML.setData({})
        self.dataStorage["stationHorizontal"] = []
        self.dataStorage["stationCant"] = []
        self.dataStorage["cant"] = []
        self.dataStorage["curvature"] = []
        self.plotCantData.clear()
        self.canvas.draw()

    # Set visibility
    def toggleCantVisibility(self, isChecked):
        if 'cant' in self.plotCantData:
            self.plotCantData["cant"].set_visible(isChecked)
            self.canvas.draw()

    def toggleCantDefPossibleVisibility(self, isChecked):
        if 'cantDefPossible' in self.plotCantData:
            self.plotCantData["cantDefPossible"].set_visible(isChecked)
            self.canvas.draw()

    def toggleCantPossibleVisibility(self, isChecked):
        if 'cantPossible' in self.plotCantData:
            self.plotCantData["cantPossible"].set_visible(isChecked)
            self.canvas.draw()

    def toggleCantPlusCantDefPossibleVisibility(self, isChecked):
        if 'cantPlusCantDefPossible' in self.plotCantData:
            self.plotCantData["cantPlusCantDefPossible"].set_visible(isChecked)
            self.canvas.draw()

    def toggleCurvatureVisibility(self, isChecked):
        if 'curvature' in self.plotCurvatureData:
            self.plotCurvatureData["curvature"].set_visible(isChecked)
            self.canvas.draw()

    def toggleCurvatureNewVisibility(self, isChecked):
        if 'curvatureNew' in self.plotCurvatureData:
            self.plotCurvatureData["curvatureNew"].set_visible(isChecked)
            self.canvas.draw()

    def toggleSpeedVisibility(self, isChecked):
        if 'speedLimits' in self.plotSpeedData:
            self.plotSpeedData["speedLimits"].set_visible(isChecked)
            self.canvas.draw()

    def toggleSpeed100Visibility(self, isChecked):
        if 'speedLimits100' in self.plotSpeedData:
            self.plotSpeedData["speedLimits100"].set_visible(isChecked)
            self.canvas.draw()

    def toggleSpeed130Visibility(self, isChecked):
        if 'speedLimits130' in self.plotSpeedData:
            self.plotSpeedData["speedLimits130"].set_visible(isChecked)
            self.canvas.draw()

    def toggleSpeed150Visibility(self, isChecked):
        if 'speedLimits150' in self.plotSpeedData:
            self.plotSpeedData["speedLimits150"].set_visible(isChecked)
            self.canvas.draw()
    
    def toggleSpeedKVisibility(self, isChecked):
        if 'speedLimitsK' in self.plotSpeedData:
            self.plotSpeedData["speedLimitsK"].set_visible(isChecked)
            self.canvas.draw()

    # Map settings
    def openMapSettings(self):
        lan = lang.DIC[self.current_language]
        dialog = gui_overlay.MapSettingsDialog(self.epsgInput, lan, self)
        if dialog.exec():
            self.epsgInput = dialog.getEPSG()

    # Update tables
    def updateTableLandXML(self, data):
        stations = np.concatenate((data["stationCant"], data["stationHorizontal"], data["stationVertical"]))
        uniqueStations = np.unique(stations)
        tableData = []
        lan = lang.DIC[self.current_language]
        for station in uniqueStations:
            cant = data["cant"][np.where(data["stationCant"] == station)]
            horizontalRadius = data["radius"][np.where(data["stationHorizontal"] == station)]
            horizonralCurvature = data["curvature"][np.where(data["stationHorizontal"] == station)]
            vertical = data["elevation"][np.where(data["stationVertical"] == station)]
            tableData.append({
                lan["station"]: station,
                lan["cant"]: cant[0] if len(cant) > 0 else "",
                lan["radius"]: horizontalRadius[0] if len(horizontalRadius) > 0 else "",
                lan["curvature"]: horizonralCurvature[0] if len(horizonralCurvature) > 0 else "",
                lan["elevation"]: vertical[0] if len(vertical) > 0 else "",
            })
        # Plot data in table    
        self.tableLandXML.setData(tableData)

    def TTPSections(self, stations):
        if len(stations) == 0:
            return []
        
        sections = []
        startID = 0

        for i in range(1, len(stations)):
            diff = stations[i] - stations[i-1]

            # Defining possible sections for further selection by the user
            if abs(diff) > 20 or (i > 1 and np.sign(stations[i-1] - stations[i-2]) != np.sign(diff) and diff != 0 and (stations[i-1] - stations[i-2]) != 0):
                sections.append({
                    "startID": startID,
                    "endID": i-1,
                    "stationStart": stations[startID],
                    "stationEnd": stations[i-1]
                })
                
                # Save for next iteration step
                startID = i
        
        # Add the last section
        sections.append({
            "startID": startID,
            "endID": len(stations)-1,
            "stationStart": stations[startID],
            "stationEnd": stations[len(stations)-1]
        })

        return sections



    
        

