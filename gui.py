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
        self.exitMenu = main_menu.addMenu(lan["exit"])
        self.helpMenu = main_menu.addMenu(lan["help"])

        # Submenu - Exit
        exitAction = QAction(lan["exit"], self)
        self.exitMenu.addAction(exitAction)
        exitAction.triggered.connect(self.close)

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

        # Submenus - Language
        self.languageMenu = self.settingsMenu.addMenu(lan["language"])
        
        langCZAction = QAction("Čeština", self)
        self.languageMenu.addAction(langCZAction)
        langCZAction.triggered.connect(lambda: self.change_language("cz"))

        langENAction = QAction("English", self)
        self.languageMenu.addAction(langENAction)
        langENAction.triggered.connect(lambda: self.change_language("en"))

        langDEAction = QAction("Deutsch", self)
        self.languageMenu.addAction(langDEAction)
        langDEAction.triggered.connect(lambda: self.change_language("de"))

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

        # Matplotlib canvas
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layoutPlots.addWidget(self.canvas, stretch=3)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layoutPlots.addWidget(self.toolbar)

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
        self.setWindowTitle(lan["app_title"])
        self.fileMenu.setTitle(lan["file"])
        self.settingsMenu.setTitle(lan["settings"])
        self.languageMenu.setTitle(lan["language"])
        self.fileMenu.actions()[0].setText(lan["open_file"])
        self.fileMenu.actions()[1].setText(lan["autodetect"])
        self.fileMenu.actions()[2].setText(lan["open_parse_landxml"])
        self.fileMenu.actions()[3].setText(lan["open_parse_xmlttp"])

        self.labelXMLTTPRaw.setText(lan["raw_data"])
        self.labelXMLTTPParsed.setText(lan["parsed_data"])
        self.labelLandXMLRaw.setText(lan["raw_data"])
        self.labelLandXMLParsed.setText(lan["parsed_data"])
        


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
            LandXMLData = readfile.ReadFile().ParseLandXML(file_content)
            self.updateTableLandXML(LandXMLData)
            self.LandXMLStations = LandXMLData["stationHorizontal"]
            self.plotCant(LandXMLData["stationCant"], LandXMLData["cant"])
            self.plotCurvature(LandXMLData["stationHorizontal"], LandXMLData["curvature"])
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

            stations = XMLTTPData["stationSpeedLimits"]
            speedLimits = XMLTTPData["speedLimits"]

            sections = self.TTPSections(stations)

            if len(sections) > 0:
                sectionsInfo = []

                # Create a list of section descriptions for the dialog
                for i, section in enumerate(sections):
                    sectionsInfo.append(f"{lan['station']} {section['stationStart']:.6f} km - {section['stationEnd']:.6f} km")

                # LandXML data availability check for cropping option in TTP sections dialog
                HasLandXML = hasattr(self, 'LandXMLStations') and len(self.LandXMLStations) > 0

                # Show the section selection dialog
                dialog = gui_overlay.TTPSelectSectionDialog(sectionsInfo, HasLandXML, lan, self)
                if dialog.exec():
                    selectedSectionID, cropToLandXML = dialog.get_selected_section()
                else:
                    return  # User cancelled the dialog, do nothing
            
            else:
                selectedSectionID = 0
                cropToLandXML = False

            # Crop to LandXML data range if option is selected and LandXML data is available
            CurrentSection = sections[selectedSectionID]
            startID = CurrentSection["startID"]
            endID = CurrentSection["endID"]+1

            stations = stations[startID:endID]
            speedLimits = speedLimits[startID:endID]

            if cropToLandXML and hasattr(self, 'LandXMLStations'):
                LandXMLMin = min(self.LandXMLStations)
                LandXMLMax = max(self.LandXMLStations)
                croppedIndices = np.where((stations >= LandXMLMin) & (stations <= LandXMLMax))

                if len(croppedIndices[0]) > 0:
                    stations = stations[croppedIndices]
                    speedLimits = speedLimits[croppedIndices]

            TTPData = {
                "stationSpeedLimits": stations,
                "speedLimits": speedLimits
            }

            self.tableTTP.setData(TTPData)
            self.plotSpeedLimits(stations, speedLimits)
        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["no_file"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def plotCant(self, stationCant, cant):
        lan = lang.DIC[self.current_language]

        # Initial check to avoid plotting empty data which can cause errors in Matplotlib
        if len(stationCant) == 0 or len(cant) == 0:
            return  # No data to plot

        self.canvas.ax_cant.clear()
        self.canvas.ax_cant.plot(stationCant, cant, marker='o', linestyle='-', color='tab:blue', label=lan["cant"])
        self.canvas.ax_cant.grid(True)
        self.canvas.ax_cant.autoscale(enable=True, axis='x', tight=True)
        self.canvas.ax_cant.set_xlabel(lan["station"])
        self.canvas.ax_cant.set_ylabel(lan["cant"])
        self.canvas.ax_cant.set_title(f'{lan["cant"]} vs {lan["station"]}', loc = 'left')
        self.canvas.ax_cant.tick_params(axis='y', labelcolor='tab:blue')
        self.canvas.ax_cant.legend(loc = 'upper left')
        self.canvas.draw()

    def plotCurvature(self, stationHorizontal, curvature):
        lan = lang.DIC[self.current_language]

        # Initial check to avoid plotting empty data which can cause errors in Matplotlib
        if len(stationHorizontal) == 0 or len(curvature) == 0:
            return  # No data to plot
        
        def fractionFormatter(x, pos):
            if np.isclose(x, 0, atol=1e-6):
                return "0"
            else:
                return f"1/{int(round(1/x))}"

        self.canvas.ax_curvature.clear()
        self.canvas.ax_curvature.yaxis.set_label_position("right")
        self.canvas.ax_curvature.yaxis.tick_right()
        self.canvas.ax_curvature.plot(stationHorizontal, curvature, marker='o', linestyle='-', color='tab:orange', label=lan["curvature"])
        self.canvas.ax_curvature.grid(True)
        self.canvas.ax_curvature.autoscale(enable=True, axis='x', tight=True)
        self.canvas.ax_curvature.set_xlabel(lan["station"])
        self.canvas.ax_curvature.set_ylabel(lan["curvature"])
        self.canvas.ax_curvature.set_title(f'{lan["curvature"]} vs {lan["station"]}', loc ='right')
        self.canvas.ax_curvature.tick_params(axis='y', labelcolor='tab:orange')
        self.canvas.ax_curvature.yaxis.set_major_formatter(FuncFormatter(fractionFormatter))
        self.canvas.ax_curvature.legend(loc = 'upper right')
        self.canvas.draw()

    def plotSpeedLimits(self, stationSpeedLimits, speedLimits):
        lan = lang.DIC[self.current_language]

        # Initial check to avoid plotting empty data which can cause errors in Matplotlib
        if len(stationSpeedLimits) == 0 or len(speedLimits) == 0:
            return  # No data to plot

        self.canvas.ax_speed.clear()
        self.canvas.ax_speed.step(stationSpeedLimits, speedLimits, where="post", marker='s', linestyle='-', label=lan["speed_lim"])
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
        self.canvas.draw()

    def cleanTTPData(self):
        self.textboxRawTTP.setPlainText("")
        self.tableTTP.setData({})
        while self.canvas.ax_speed.lines:
            self.canvas.ax_speed.lines[0].remove()
        self.canvas.draw()

    def cleanLandXMLData(self):
        self.textboxRawLandXML.setPlainText("")
        self.tableLandXML.setData({})
        while self.canvas.ax_cant.lines:
            self.canvas.ax_cant.lines[0].remove()
        while self.canvas.ax_curvature.lines:
            self.canvas.ax_curvature.lines[0].remove()
        self.canvas.draw()

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
            if abs(diff) > 50 or (i > 1 and np.sign(stations[i-1] - stations[i-2]) != np.sign(diff) and diff != 0 and (stations[i-1] - stations[i-2]) != 0):
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



    
        

