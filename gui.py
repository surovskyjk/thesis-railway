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
import matplotlib as mpl

# numpy import for data handling
import numpy as np

import csv
# Local imports
import lang
import readfile
import gui_overlay
from map_viewer import MapWidget
import default_values
import geometry_engine
import vehicle_engine

# Apply global rcParams for text sizes
mpl.rcParams['axes.titlesize'] = 10
mpl.rcParams['axes.labelsize'] = 9
mpl.rcParams['xtick.labelsize'] = 8
mpl.rcParams['ytick.labelsize'] = 8
mpl.rcParams['legend.fontsize'] = 8
mpl.rcParams['figure.titlesize'] = 11
import copy

class AlignmentCanvas(FigureCanvas):
    # Canvas widget for Matplotlib plots - Horizontal Alignment data (Cant, Speed Limits)
    def __init__(self, parent=None, width=5, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        
        self.ax_speed = self.fig.add_subplot(211)

        self.ax_cant = self.fig.add_subplot(212, sharex=self.ax_speed)

        self.ax_curvature = self.ax_cant.twinx()

        super().__init__(self.fig)

class ProfileCanvas(FigureCanvas):
     # Canvas widget for Matplotlib plots - Vertical Alignment data
     def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        self.ax_profile = self.fig.add_subplot(111)
        super().__init__(self.fig)

class KinematicsCanvas(FigureCanvas):
    # Canvas widget for Matplotlib plots - Kinematics data
    def __init__(self, parent=None, width=5, height=8, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, layout="constrained")
        self.ax_tacho_track = self.fig.add_subplot(411)
        self.ax_tacho_time = self.fig.add_subplot(412)
        self.ax_dist_time = self.fig.add_subplot(413)
        self.ax_forces = self.fig.add_subplot(414)
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
        self.plotProfileData = {}
        self.plotKinematicsData = {}

        # Import default values to dataStorage
        self.dataStorage["settingsData"] = {}
        self.dataStorage["settingsData"] = copy.deepcopy(default_values.defVal)

        # Layouts - main grid
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
        self.calculateMenu = main_menu.addMenu(lan["calculate"])
        self.cleanMenu = main_menu.addMenu(lan["clean"])
        self.settingsMenu = main_menu.addMenu(lan["settings"])
        self.viewMenu = main_menu.addMenu(lan["view"])
        self.reportMenu = main_menu.addMenu(lan.get("reportMenu", "&Report"))
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

        append_autodetect_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon)
        appendAutodetectXMLAction = QAction(append_autodetect_icon, lan.get("append_autodetect", "Append Autodetect"), self)
        self.fileMenu.addAction(appendAutodetectXMLAction)
        appendAutodetectXMLAction.setStatusTip(lan.get("append_autodetect_tip", "Autodetect and append"))
        appendAutodetectXMLAction.triggered.connect(self.appendAutodetectXML)

        openParseLandXMLAction = QAction(lan["open_parse_landxml"], self)
        self.fileMenu.addAction(openParseLandXMLAction)
        openParseLandXMLAction.triggered.connect(self.openLandXML)

        appendLandXMLAction = QAction(lan.get("append_landxml", "Append LandXML"), self)
        self.fileMenu.addAction(appendLandXMLAction)
        appendLandXMLAction.triggered.connect(self.appendLandXML)

        openParseXMLTTPAction = QAction(lan["open_parse_xmlttp"], self)      
        self.fileMenu.addAction(openParseXMLTTPAction)
        openParseXMLTTPAction.triggered.connect(self.openXMLTTP)
        
        appendXMLTTPAction = QAction(lan.get("append_xmlttp", "Append XML TTP"), self)
        self.fileMenu.addAction(appendXMLTTPAction)
        appendXMLTTPAction.triggered.connect(self.appendXMLTTP)

        # importStopsTTPAction = QAction(lan.get("importStopsTTP", "Import Stops from XML TTP"), self)
        # self.fileMenu.addAction(importStopsTTPAction)
        # importStopsTTPAction.triggered.connect(self.importStopsTTP)
        
        self.fileMenu.addSeparator()
        
        # Submenu - Calculate
        calculateGeometryAction = QAction(lan["calculate_geometry"], self)
        self.calculateMenu.addAction(calculateGeometryAction)
        calculateGeometryAction.triggered.connect(self.calculateGeometry)

        calculateGeometryIAction = QAction(lan["calculate_geometry_I"], self)
        self.calculateMenu.addAction(calculateGeometryIAction)
        calculateGeometryIAction.triggered.connect(self.calculateGeometryI)

        calculateTrainSpeed = QAction(lan["calculate_train_speed"], self)
        self.calculateMenu.addAction(calculateTrainSpeed)
        calculateTrainSpeed.triggered.connect(self.calculateTrainSpeed)

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

        cleanCalculatedCantsAction = QAction(lan["cleanCants"], self)
        self.cleanMenu.addAction(cleanCalculatedCantsAction)
        cleanCalculatedCantsAction.triggered.connect(self.cleanCalculatedCants)

        cleanCalculatedSpeedsAction = QAction(lan["cleanSpeeds"], self)
        self.cleanMenu.addAction(cleanCalculatedSpeedsAction)
        cleanCalculatedSpeedsAction.triggered.connect(self.cleanCalculatedSpeeds)

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

        # Sub-submenu - Geometry settings
        geometrySettingsAction = QAction(lan["geometrySettings"], self)
        self.settingsMenu.addAction(geometrySettingsAction)
        geometrySettingsAction.triggered.connect(self.openGeometrySettings)

        # Sub-submenu - Vehicle settings
        vehicleSettingsAction = QAction(lan["vehicleSettings"], self)
        self.settingsMenu.addAction(vehicleSettingsAction)
        vehicleSettingsAction.triggered.connect(self.openVehicleSettings)
        
        # Sub-submenu - Stops settings
        stopsSettingsAction = QAction(lan.get("stopsSettings", "Stops Settings"), self)
        self.settingsMenu.addAction(stopsSettingsAction)
        stopsSettingsAction.triggered.connect(self.openStopsSettings)

        # Sub-submenu - Speed settings
        speedSettingsAction = QAction(lan.get("speedSettings", "Speed Limits Settings"), self)
        self.settingsMenu.addAction(speedSettingsAction)
        speedSettingsAction.triggered.connect(self.openSpeedSettings)

        # Sub-submenu - Design approach selection
        designApproachAction = QAction(lan["designApproach"], self)
        self.settingsMenu.addAction(designApproachAction)
        designApproachAction.triggered.connect(self.openDesignApproach)

        self.settingsMenu.addSeparator()

        # Sub-submenu - Units
        self.toggleUnitsAction = QAction(lan["units_kmh"], self)
        self.toggleUnitsAction.setCheckable(True)
        self.toggleUnitsAction.setChecked(False)
        self.toggleUnitsAction.triggered.connect(self.plotKinematics)
        self.settingsMenu.addAction(self.toggleUnitsAction)

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

        self.toggleCDef100Action = QAction(lan["cdef_100"], self)
        self.toggleCDef100Action.setCheckable(True)
        self.toggleCDef100Action.setChecked(True)
        self.toggleCDef100Action.triggered.connect(self.toggleCDef100Visibility)
        self.viewMenu.addAction(self.toggleCDef100Action)

        self.toggleCDef130Action = QAction(lan["cdef_130"], self)
        self.toggleCDef130Action.setCheckable(True)
        self.toggleCDef130Action.setChecked(True)
        self.toggleCDef130Action.triggered.connect(self.toggleCDef130Visibility)
        self.viewMenu.addAction(self.toggleCDef130Action)

        self.toggleCDef150Action = QAction(lan["cdef_150"], self)
        self.toggleCDef150Action.setCheckable(True)
        self.toggleCDef150Action.setChecked(True)
        self.toggleCDef150Action.triggered.connect(self.toggleCDef150Visibility)
        self.viewMenu.addAction(self.toggleCDef150Action)

        self.toggleCDefKAction = QAction(lan["cdef_K"], self)
        self.toggleCDefKAction.setCheckable(True)
        self.toggleCDefKAction.setChecked(True)
        self.toggleCDefKAction.triggered.connect(self.toggleCDefKVisibility)
        self.viewMenu.addAction(self.toggleCDefKAction)

        self.toggleCantDef100Action = QAction(lan["cant_def_100"], self)
        self.toggleCantDef100Action.setCheckable(True)
        self.toggleCantDef100Action.setChecked(True)
        self.toggleCantDef100Action.triggered.connect(self.toggleCantDef100Visibility)
        self.viewMenu.addAction(self.toggleCantDef100Action)

        self.toggleCantDef130Action = QAction(lan["cant_def_130"], self)
        self.toggleCantDef130Action.setCheckable(True)
        self.toggleCantDef130Action.setChecked(True)
        self.toggleCantDef130Action.triggered.connect(self.toggleCantDef130Visibility)
        self.viewMenu.addAction(self.toggleCantDef130Action)

        self.toggleCantDef150Action = QAction(lan["cant_def_150"], self)
        self.toggleCantDef150Action.setCheckable(True)
        self.toggleCantDef150Action.setChecked(True)
        self.toggleCantDef150Action.triggered.connect(self.toggleCantDef150Visibility)
        self.viewMenu.addAction(self.toggleCantDef150Action)

        self.toggleCantDefKAction = QAction(lan["cant_def_K"], self)
        self.toggleCantDefKAction.setCheckable(True)
        self.toggleCantDefKAction.setChecked(True)
        self.toggleCantDefKAction.triggered.connect(self.toggleCantDefKVisibility)
        self.viewMenu.addAction(self.toggleCantDefKAction)
        
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

        self.viewMenu.addSeparator()

        self.toggleProfileAction = QAction(lan["profile"], self)
        self.toggleProfileAction.setCheckable(True)
        self.toggleProfileAction.setChecked(True)
        self.toggleProfileAction.triggered.connect(self.toggleProfileVisibility)
        self.viewMenu.addAction(self.toggleProfileAction)

        self.viewMenu.addSeparator()

        self.toggleKinematicsSpeedLimitTrackAction = QAction(lan["kinematicsSpeedLimitTrack"], self)
        self.toggleKinematicsSpeedLimitTrackAction.setCheckable(True)
        self.toggleKinematicsSpeedLimitTrackAction.setChecked(True)
        self.toggleKinematicsSpeedLimitTrackAction.triggered.connect(self.toggleKinematicsSpeedLimitTrackVisibility)
        self.viewMenu.addAction(self.toggleKinematicsSpeedLimitTrackAction)

        self.toggleKinematicsSpeedLimitTimeAction = QAction(lan["kinematicsSpeedLimitTime"], self)
        self.toggleKinematicsSpeedLimitTimeAction.setCheckable(True)
        self.toggleKinematicsSpeedLimitTimeAction.setChecked(True)
        self.toggleKinematicsSpeedLimitTimeAction.triggered.connect(self.toggleKinematicsSpeedLimitTimeVisibility)
        self.viewMenu.addAction(self.toggleKinematicsSpeedLimitTimeAction)

        self.toggleKinematicsDistanceTimeAction = QAction(lan["kinematicsDistanceTime"], self)
        self.toggleKinematicsDistanceTimeAction.setCheckable(True)
        self.toggleKinematicsDistanceTimeAction.setChecked(True)
        self.toggleKinematicsDistanceTimeAction.triggered.connect(self.toggleKinematicsDistanceTimeVisibility)
        self.viewMenu.addAction(self.toggleKinematicsDistanceTimeAction)

        self.toggleKinematicsForcesAction = QAction(lan.get("kinematicsForces", "Forces Profile"), self)
        self.toggleKinematicsForcesAction.setCheckable(True)
        self.toggleKinematicsForcesAction.setChecked(True)
        self.toggleKinematicsForcesAction.triggered.connect(self.toggleKinematicsForcesVisibility)
        self.viewMenu.addAction(self.toggleKinematicsForcesAction)

        # Submenu - Report
        self.reportGeometryAction = QAction(lan.get("reportGeometry", "Report - Geometry"), self)
        self.reportMenu.addAction(self.reportGeometryAction)
        self.reportGeometryAction.triggered.connect(self.generateGeometryReport)

        self.reportVehicleMenu = self.reportMenu.addMenu(lan.get("reportVehicle", "Report - Vehicle"))
        self.reportVehicleAction1 = QAction(lan.get("vehicle", "Vehicle") + " 1", self)
        self.reportVehicleAction2 = QAction(lan.get("vehicle", "Vehicle") + " 2", self)
        self.reportVehicleAction3 = QAction(lan.get("vehicle", "Vehicle") + " 3", self)
        self.reportVehicleMenu.addAction(self.reportVehicleAction1)
        self.reportVehicleMenu.addAction(self.reportVehicleAction2)
        self.reportVehicleMenu.addAction(self.reportVehicleAction3)
        self.reportVehicleAction1.triggered.connect(lambda: self.generateVehicleReport(0))
        self.reportVehicleAction2.triggered.connect(lambda: self.generateVehicleReport(1))
        self.reportVehicleAction3.triggered.connect(lambda: self.generateVehicleReport(2))

        self.reportMenu.addSeparator()

        self.exportGeometryReportAction = QAction(lan.get("exportGeometryReport", "Export Geometry Report"), self)
        self.reportMenu.addAction(self.exportGeometryReportAction)
        self.exportGeometryReportAction.triggered.connect(self.exportGeometryReport)

        self.exportVehicleReportMenu = self.reportMenu.addMenu(lan.get("exportVehicleReport", "Export Vehicle Report"))
        self.exportVehicleReportAction1 = QAction(lan.get("vehicle", "Vehicle") + " 1", self)
        self.exportVehicleReportAction2 = QAction(lan.get("vehicle", "Vehicle") + " 2", self)
        self.exportVehicleReportAction3 = QAction(lan.get("vehicle", "Vehicle") + " 3", self)
        self.exportVehicleReportMenu.addAction(self.exportVehicleReportAction1)
        self.exportVehicleReportMenu.addAction(self.exportVehicleReportAction2)
        self.exportVehicleReportMenu.addAction(self.exportVehicleReportAction3)
        self.exportVehicleReportAction1.triggered.connect(lambda: self.exportVehicleReport(0))
        self.exportVehicleReportAction2.triggered.connect(lambda: self.exportVehicleReport(1))
        self.exportVehicleReportAction3.triggered.connect(lambda: self.exportVehicleReport(2))

        # Submenu - Exit
        exitAction = QAction(lan["exit"], self)
        self.exitMenu.addAction(exitAction)
        exitAction.triggered.connect(self.close)
        
        # Submenus - Help
        helpAction = QAction(lan["help"], self)
        self.helpMenu.addAction(helpAction)
        helpAction.triggered.connect(self.openHelp)

        # Create toolbar for the most common actions
        toolbar = self.addToolBar(lan["toolbar"])
        toolbar.addAction(autodetectXMLAction)
        toolbar.addAction(appendAutodetectXMLAction)

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

        # Plots, report and map tabs
        self.layoutTabsPlotsAlignment_container = QWidget()
        layoutPlotsAlignment = QVBoxLayout(self.layoutTabsPlotsAlignment_container)
        layoutPlotsAlignment.setContentsMargins(0,0,0,0)
        layoutPlotsAlignment.setSpacing(0)

        self.layoutTabsPlotsProfile_container = QWidget()
        layoutPlotsProfile = QVBoxLayout(self.layoutTabsPlotsProfile_container)
        layoutPlotsProfile.setContentsMargins(0,0,0,0)
        layoutPlotsProfile.setSpacing(0)

        self.layoutTabsPlotsKinematics_container = QWidget()
        layoutPlotsKinematics = QVBoxLayout(self.layoutTabsPlotsKinematics_container)
        layoutPlotsKinematics.setContentsMargins(0,0,0,0)
        layoutPlotsKinematics.setSpacing(0)

        self.layoutTabsPlotsReport_container = QWidget()
        layoutPlotsReport = QVBoxLayout(self.layoutTabsPlotsReport_container)
        layoutPlotsReport.setContentsMargins(0,0,0,0)
        layoutPlotsReport.setSpacing(0)

        self.layoutTabsPlotsMap_container = QWidget()
        layoutPlotsMap = QVBoxLayout(self.layoutTabsPlotsMap_container)
        layoutPlotsMap.setContentsMargins(0,0,0,0)
        layoutPlotsMap.setSpacing(0)

        # Matplotlib canvas - add widget for plots
        # Plots for Horizontal Alignment Data
        self.canvasAlignment = AlignmentCanvas(self, width=5, height=4, dpi=100)
        layoutPlotsAlignment.addWidget(self.canvasAlignment, stretch=3)
        self.toolbar = NavigationToolbar(self.canvasAlignment, self)
        layoutPlotsAlignment.addWidget(self.toolbar)

        # Plots for Vertical Alignment Data
        self.canvasProfile = ProfileCanvas(self, width=5, height=4, dpi=100)
        layoutPlotsProfile.addWidget(self.canvasProfile, stretch=3)
        self.toolbar = NavigationToolbar(self.canvasProfile, self)
        layoutPlotsProfile.addWidget(self.toolbar)

        # Plots for Train Kinematics
        self.canvasKinematics = KinematicsCanvas(self, width=5, height=8, dpi=100)
        layoutPlotsKinematics.addWidget(self.canvasKinematics, stretch=3)
        self.toolbar = NavigationToolbar(self.canvasKinematics, self)
        layoutPlotsKinematics.addWidget(self.toolbar)

        # Report - add widget for plotting reports
        self.reportSplitter = QSplitter(Qt.Orientation.Horizontal)
        
        self.reportGeometryWidget = QPlainTextEdit()
        self.reportGeometryWidget.setReadOnly(True)
        self.reportSplitter.addWidget(self.reportGeometryWidget)
        
        self.reportVehicleTable = pg.TableWidget(sortable=False)
        self.reportSplitter.addWidget(self.reportVehicleTable)
        layoutPlotsReport.addWidget(self.reportSplitter)

        # Map - add widget for maps
        self.mapWidget = MapWidget(self)
        layoutPlotsMap.addWidget(self.mapWidget)

        # Tabs for plots
        self.layoutTabsPlots.setTabPosition(QTabWidget.TabPosition.East)
        self.layoutTabsPlots.addTab(self.layoutTabsPlotsAlignment_container, lan["plotsAlignment"])
        self.layoutTabsPlots.addTab(self.layoutTabsPlotsProfile_container, lan["plotsProfile"])
        self.layoutTabsPlots.addTab(self.layoutTabsPlotsKinematics_container, lan["plotsKinematics"])

        # Tab for report
        self.layoutTabsPlots.addTab(self.layoutTabsPlotsReport_container, lan["report"])
        
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
        self.reportMenu.setTitle(lan.get("reportMenu", "&Report"))
        self.cleanMenu.setTitle(lan["clean"])
        self.exitMenu.setTitle(lan["exit"])
        self.helpMenu.setTitle(lan["help"])

        self.fileMenu.actions()[0].setText(lan["open_file"])
        self.fileMenu.actions()[1].setText(lan["autodetect"])
        self.fileMenu.actions()[1].setStatusTip(lan["autodetect_tip"])
        self.fileMenu.actions()[2].setText(lan.get("append_autodetect", "Append Autodetect"))
        self.fileMenu.actions()[2].setStatusTip(lan.get("append_autodetect_tip", "Autodetect and append"))
        self.fileMenu.actions()[3].setText(lan["open_parse_landxml"])
        self.fileMenu.actions()[4].setText(lan.get("append_landxml", "Append LandXML"))
        self.fileMenu.actions()[5].setText(lan["open_parse_xmlttp"])
        self.fileMenu.actions()[6].setText(lan.get("append_xmlttp", "Append XML TTP"))
        # self.fileMenu.actions()[4].setText(lan.get("importStopsTTP", "Import Stops from XML TTP"))

        self.settingsMenu.actions()[2].setText(lan["mapSettings"])
        self.settingsMenu.actions()[3].setText(lan["geometrySettings"])
        self.settingsMenu.actions()[4].setText(lan.get("vehicleSettings", "Vehicle Settings"))
        self.settingsMenu.actions()[5].setText(lan.get("stopsSettings", "Stops Settings"))
        self.settingsMenu.actions()[6].setText(lan.get("speedSettings", "Speed Limits Settings"))
        self.settingsMenu.actions()[7].setText(lan["designApproach"])

        self.viewMenu.actions()[0].setText(lan["cant"])
        self.viewMenu.actions()[1].setText(lan["cant_possible"])
        self.viewMenu.actions()[2].setText(lan["cdef_100"])
        self.viewMenu.actions()[3].setText(lan["cdef_130"])
        self.viewMenu.actions()[4].setText(lan["cdef_150"])
        self.viewMenu.actions()[5].setText(lan["cdef_K"])
        self.viewMenu.actions()[6].setText(lan["cant_def_100"])
        self.viewMenu.actions()[7].setText(lan["cant_def_130"])
        self.viewMenu.actions()[8].setText(lan["cant_def_150"])
        self.viewMenu.actions()[9].setText(lan["cant_def_K"])
        self.viewMenu.actions()[11].setText(lan["curvature"])
        self.viewMenu.actions()[12].setText(lan["curvature_new"])
        self.viewMenu.actions()[13].setText(lan["speed_lim"])
        self.viewMenu.actions()[14].setText(lan["speed_lim_100"])
        self.viewMenu.actions()[15].setText(lan["speed_lim_130"])
        self.viewMenu.actions()[16].setText(lan["speed_lim_150"])
        self.viewMenu.actions()[17].setText(lan["speed_lim_K"])

        self.cleanMenu.actions()[0].setText(lan["cleanTTP"])
        self.cleanMenu.actions()[1].setText(lan["cleanLandXML"])
        self.cleanMenu.actions()[2].setText(lan["cleanAll"])
        self.cleanMenu.actions()[3].setText(lan["cleanCants"])
        self.cleanMenu.actions()[4].setText(lan["cleanSpeeds"])

        self.reportGeometryAction.setText(lan.get("reportGeometry", "Report - Geometry"))
        self.reportVehicleMenu.setTitle(lan.get("reportVehicle", "Report - Vehicle"))
        self.exportGeometryReportAction.setText(lan.get("exportGeometryReport", "Export Geometry Report"))
        self.exportVehicleReportMenu.setTitle(lan.get("exportVehicleReport", "Export Vehicle Report"))

        self.reportVehicleAction1.setText(lan.get("vehicle", "Vehicle") + " 1")
        self.reportVehicleAction2.setText(lan.get("vehicle", "Vehicle") + " 2")
        self.reportVehicleAction3.setText(lan.get("vehicle", "Vehicle") + " 3")
        self.exportVehicleReportAction1.setText(lan.get("vehicle", "Vehicle") + " 1")
        self.exportVehicleReportAction2.setText(lan.get("vehicle", "Vehicle") + " 2")
        self.exportVehicleReportAction3.setText(lan.get("vehicle", "Vehicle") + " 3")

        self.exitMenu.actions()[0].setText(lan["exit"])

        self.helpMenu.actions()[0].setText(lan["help"])

        self.toggleUnitsAction.setText(lan["units_kmh"])
        self.toggleKinematicsSpeedLimitTrackAction.setText(lan["kinematicsSpeedLimitTrack"])
        self.toggleKinematicsSpeedLimitTimeAction.setText(lan["kinematicsSpeedLimitTime"])
        self.toggleKinematicsDistanceTimeAction.setText(lan["kinematicsDistanceTime"])
        self.toggleKinematicsForcesAction.setText(lan.get("kinematicsForces", "Forces Profile"))

        # Update labels
        self.labelXMLTTPRaw.setText(lan["raw_data"])
        self.labelXMLTTPParsed.setText(lan["parsed_data"])
        self.labelLandXMLRaw.setText(lan["raw_data"])
        self.labelLandXMLParsed.setText(lan["parsed_data"])

        # Update matplotlib canvas
        self.canvasAlignment.ax_speed.set_xlabel(lan["station"])
        self.canvasAlignment.ax_speed.set_ylabel(lan["speed_lim"])
        self.canvasAlignment.ax_speed.set_title(f'{lan["speed_lim"]} vs {lan["station"]}')
        
        self.canvasAlignment.ax_cant.set_xlabel(lan["station"])
        self.canvasAlignment.ax_cant.set_ylabel(lan["cant"])
        self.canvasAlignment.ax_cant.set_title(f'{lan["cant"]} vs {lan["station"]}', loc = 'left')

        self.canvasAlignment.ax_curvature.set_xlabel(lan["station"])
        self.canvasAlignment.ax_curvature.set_ylabel(lan["curvature"])
        self.canvasAlignment.ax_curvature.set_title(f'{lan["curvature"]} vs {lan["station"]}', loc ='right')

        # Update legends
        if self.canvasAlignment.ax_speed.lines:
            self.canvasAlignment.ax_speed.lines[0].set_label(lan["speed_lim"])
            self.canvasAlignment.ax_speed.legend()

        if self.canvasAlignment.ax_cant.lines:
            self.canvasAlignment.ax_cant.lines[0].set_label(lan["cant"])
            self.canvasAlignment.ax_cant.legend(loc = 'upper left')

        if self.canvasAlignment.ax_curvature.lines:
            self.canvasAlignment.ax_curvature.lines[0].set_label(lan["curvature"])
            self.canvasAlignment.ax_curvature.legend(loc = 'upper right')

        self.canvasAlignment.draw()

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

    def appendAutodetectXML(self):
        file_content = self.getFileContent()
        if file_content is None:
            return
        
        xml_type = readfile.ReadFile().XMLType(file_content)
        if xml_type == 1:
            self.appendLandXMLContent(file_content)
        elif xml_type == 2:
            self.appendXMLTTPContent(file_content)
        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("unknown_xml_file", "Unknown XML format."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def openLandXML(self):
        file_content = self.getFileContent()
        self.parseLandXML(file_content)

    def openXMLTTP(self):
        file_content = self.getFileContent()
        self.parseXMLTTP(file_content)

    def appendXMLTTP(self):
        if "stationSpeedLimits" not in self.dataStorage or len(self.dataStorage.get("stationSpeedLimits", [])) == 0:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        file_content = self.getFileContent()
        if not file_content:
            return
        self.appendXMLTTPContent(file_content)

    def appendXMLTTPContent(self, file_content):
        if "stationSpeedLimits" not in self.dataStorage or len(self.dataStorage.get("stationSpeedLimits", [])) == 0:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        XMLTTPData = readfile.ReadFile().ParseXMLTTP(file_content)
        new_stations = XMLTTPData["stationSpeedLimits"]
        new_speeds = XMLTTPData["speedLimits"]

        valid_mask = (new_speeds != 0) & ~np.isnan(new_speeds)
        new_stations = new_stations[valid_mask]
        new_speeds = new_speeds[valid_mask]

        lan = lang.DIC[self.current_language]
        sections = self.TTPSections(new_stations)
        
        if len(sections) > 0:
            sectionsInfo = []
            for i, section in enumerate(sections):
                sectionsInfo.append(f"{lan['station']} {section['stationStart']:.6f} km - {section['stationEnd']:.6f} km")

            HasLandXML = "stationHorizontal" in self.dataStorage.get("LandXML",{}) and len(self.dataStorage.get("LandXML",{}).get("stationHorizontal")) > 0

            dialog = gui_overlay.TTPSelectSectionDialog(sectionsInfo, HasLandXML, lan, self)
            if dialog.exec():
                selectedSectionIDs, cropToLandXML, loadAll = dialog.get_selected_section()
            else:
                return
        else:
            selectedSectionIDs = []
            HasLandXML = False
            cropToLandXML = False
            loadAll = True

        stationsRaw = np.array(new_stations)
        speedLimitsRaw = np.array(new_speeds)

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
            LandXMLMin = np.nanmin(self.dataStorage.get("LandXML",{}).get("stationHorizontal"))
            LandXMLMax = np.nanmax(self.dataStorage.get("LandXML",{}).get("stationHorizontal"))
            if not (np.isnan(LandXMLMin) or np.isnan(LandXMLMax)):
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
                stationsRaw = np.array(stationsCropped, dtype=float)
                speedLimitsRaw = np.array(speedLimitsCropped, dtype=float)

        if len(stationsRaw) == 0:
            return

        old_text = self.textboxRawTTP.toPlainText()
        self.textboxRawTTP.setPlainText(old_text + "\n\n<!-- MERGED XML TTP -->\n\n" + file_content)

        old_stations = self.dataStorage["stationSpeedLimits"]
        old_speeds = self.dataStorage["speedLimits"]

        old_start = np.nanmin(old_stations)
        old_end = np.nanmax(old_stations)
        new_start = np.nanmin(stationsRaw)
        new_end = np.nanmax(stationsRaw)

        # Kontrola mezery (ve staničení TTP používáme [km], proto 0.1 je 100 m)
        if new_start >= old_end or (abs(new_start - old_end) <= abs(new_end - old_start)):
            is_append = True
            crop_station = old_end
            if abs(new_start - old_end) > 0.1:
                QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))
        else:
            is_append = False
            crop_station = old_start
            if abs(old_start - new_end) > 0.1:
                QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))

        if is_append:
            mask = stationsRaw > crop_station
            merged_stations = np.concatenate((old_stations, stationsRaw[mask]))
            merged_speeds = np.concatenate((old_speeds, speedLimitsRaw[mask]))
        else:
            mask = stationsRaw < crop_station
            merged_stations = np.concatenate((stationsRaw[mask], old_stations))
            merged_speeds = np.concatenate((speedLimitsRaw[mask], old_speeds))

        self.dataStorage["stationSpeedLimits"] = merged_stations
        self.dataStorage["speedLimits"] = merged_speeds

        TTPData = {
            "stationSpeedLimits": merged_stations,
            "speedLimits": merged_speeds
        }
        self.tableTTP.setData(TTPData)
        
        self.cleanCalculatedSpeeds()
        self.plotSpeedLimits()

    def appendLandXML(self):
        if "LandXML" not in self.dataStorage or len(self.dataStorage.get("LandXML", {}).get("stationHorizontal", [])) == 0:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        file_content = self.getFileContent()
        if not file_content:
            return
        self.appendLandXMLContent(file_content)

    def appendLandXMLContent(self, file_content):
        if "LandXML" not in self.dataStorage or len(self.dataStorage.get("LandXML", {}).get("stationHorizontal", [])) == 0:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        alignments = readfile.ReadFile().GetAlignments(file_content)
        selected_idx = 0
        if len(alignments) > 1:
            lan = lang.DIC[self.current_language]
            dialog = gui_overlay.AlignmentSelectDialog(alignments, lan, self)
            if dialog.exec():
                selected_idx = dialog.get_selected_index()
            else:
                return

        newLandXMLData = readfile.ReadFile().ParseLandXML(file_content, self.epsgInput, selected_idx)
        
        old_text = self.textboxRawLandXML.toPlainText()
        self.textboxRawLandXML.setPlainText(old_text + "\n\n<!-- MERGED XML -->\n\n" + file_content)

        self.mergeLandXMLData(newLandXMLData)

    def mergeLandXMLData(self, newData):
        oldData = self.dataStorage.get("LandXML", {})
        
        if len(newData.get("stationHorizontal", [])) == 0:
            return
            
        old_start = np.nanmin(oldData["stationHorizontal"])
        old_end = np.nanmax(oldData["stationHorizontal"])
        new_start = np.nanmin(newData["stationHorizontal"])
        new_end = np.nanmax(newData["stationHorizontal"])

        lan = lang.DIC[self.current_language]

        if new_start >= old_end or (abs(new_start - old_end) <= abs(new_end - old_start)):
            is_append = True
            crop_station = old_end
            if "keyX" in oldData and "keyY" in oldData and "keyX" in newData and "keyY" in newData:
                if len(oldData["keyX"]) > 0 and len(newData["keyX"]) > 0:
                    old_last_x, old_last_y = oldData["keyX"][-1], oldData["keyY"][-1]
                    new_first_x, new_first_y = newData["keyX"][0], newData["keyY"][0]
                    dist = np.sqrt((new_first_x - old_last_x)**2 + (new_first_y - old_last_y)**2)
                    if dist > 100:
                        QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))
        else:
            is_append = False
            crop_station = old_start
            if "keyX" in oldData and "keyY" in oldData and "keyX" in newData and "keyY" in newData:
                if len(oldData["keyX"]) > 0 and len(newData["keyX"]) > 0:
                    old_first_x, old_first_y = oldData["keyX"][0], oldData["keyY"][0]
                    new_last_x, new_last_y = newData["keyX"][-1], newData["keyY"][-1]
                    dist = np.sqrt((new_last_x - old_first_x)**2 + (new_last_y - old_first_y)**2)
                    if dist > 100:
                        QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))

        station_map = {
            "cant": "stationCant",
            "stationCant": "stationCant",
            "stationHorizontal": "stationHorizontal",
            "geometryType": "stationHorizontal",
            "radius": "stationHorizontal",
            "curvature": "stationHorizontal",
            "curvatureSign": "stationHorizontal",
            "stationVertical": "stationVertical",
            "elevation": "stationVertical"
        }

        def merge_arrays(key):
            if key not in oldData or key not in newData:
                return oldData.get(key, newData.get(key, []))
            
            old_arr = oldData[key]
            new_arr = newData[key]

            if key == "denseAlignment":
                if is_append:
                    new_arr_cropped = [p for p in new_arr if p[0] > crop_station]
                    return old_arr + new_arr_cropped
                else:
                    new_arr_cropped = [p for p in new_arr if p[0] < crop_station]
                    return new_arr_cropped + old_arr

            if key in ["keyStations", "keyTypes", "keyX", "keyY", "keyLat", "keyLon"]:
                new_stations = np.array(newData["keyStations"])
                mask = new_stations > crop_station if is_append else new_stations < crop_station
            elif key in station_map:
                s_key = station_map[key]
                new_stations = np.array(newData[s_key])
                
                if s_key == "stationHorizontal":
                    mask = np.zeros(len(new_stations), dtype=bool)
                    # Zpracování polí definovaných v párech (počátek-konec segmentu)
                    for i in range(0, len(new_stations), 2):
                        if is_append: keep = new_stations[i+1] > crop_station
                        else: keep = new_stations[i] < crop_station
                        mask[i] = keep
                        if i+1 < len(new_stations): mask[i+1] = keep
                            
                    if key == "stationHorizontal":
                        if isinstance(new_arr, np.ndarray): new_arr = np.copy(new_arr)
                        else: new_arr = list(new_arr)
                            
                        for i in range(0, len(new_stations), 2):
                            if mask[i]:
                                if is_append and new_arr[i] < crop_station: new_arr[i] = crop_station
                                elif not is_append and (i+1) < len(new_arr) and new_arr[i+1] > crop_station: new_arr[i+1] = crop_station
                else:
                    mask = new_stations > crop_station if is_append else new_stations < crop_station
            elif key in ["alignmentCoordinates", "alignmentCoordsOriginal"]:
                if is_append: return old_arr + new_arr
                else: return new_arr + old_arr
            else:
                if isinstance(old_arr, np.ndarray) and isinstance(new_arr, np.ndarray):
                    if is_append: return np.concatenate((old_arr, new_arr))
                    else: return np.concatenate((new_arr, old_arr))
                elif isinstance(old_arr, list) and isinstance(new_arr, list):
                    if is_append: return old_arr + new_arr
                    else: return new_arr + old_arr
                return old_arr

            if isinstance(new_arr, np.ndarray):
                new_arr_cropped = new_arr[mask]
                if is_append:
                    return np.concatenate((old_arr, new_arr_cropped))
                else:
                    return np.concatenate((new_arr_cropped, old_arr))
            elif isinstance(new_arr, list):
                new_arr_cropped = [item for i, item in enumerate(new_arr) if mask[i]]
                if is_append:
                    return old_arr + new_arr_cropped
                else:
                    return new_arr_cropped + old_arr
            return old_arr

        mergedData = {}
        all_keys = set(list(oldData.keys()) + list(newData.keys()))
        for k in all_keys:
            mergedData[k] = merge_arrays(k)

        if "stationVertical" in mergedData and "elevation" in mergedData:
            deltaZ = np.diff(np.array(mergedData["elevation"], dtype=float))
            deltaX = np.diff(np.array(mergedData["stationVertical"], dtype=float))
            mergedData["slope"] = np.zeros_like(deltaX)
            valid = deltaX != 0
            mergedData["slope"][valid] = deltaZ[valid] / deltaX[valid]

        self.dataStorage["LandXML"] = mergedData
        self.updateTableLandXML(mergedData)

        self.cleanCalculatedCants()
        self.cleanCalculatedSpeeds()
        
        self.plotCant()
        self.plotCurvature()
        self.plotProfile()
        self.mapWidget.drawAlignment(mergedData.get("alignmentCoordinates",[]), mergedData)

    def parseLandXML(self, file_content):
        if file_content is not None:
            self.textboxRawLandXML.setPlainText(file_content)
            
            # Check for multiple alignments and prompt the user if needed
            alignments = readfile.ReadFile().GetAlignments(file_content)
            selected_idx = 0
            if len(alignments) > 1:
                lan = lang.DIC[self.current_language]
                dialog = gui_overlay.AlignmentSelectDialog(alignments, lan, self)
                if dialog.exec():
                    selected_idx = dialog.get_selected_index()
                else:
                    return  # User cancelled the dialog, do nothing

            LandXMLData = readfile.ReadFile().ParseLandXML(file_content, self.epsgInput, selected_idx)
            self.updateTableLandXML(LandXMLData)

            # Save data to central data storage
            self.dataStorage["LandXML"] = LandXMLData

            # Plot and draw data
            lxml = self.dataStorage.get("LandXML",{})
            self.plotCant()
            self.plotCurvature()
            self.plotProfile()
            self.mapWidget.drawAlignment(lxml.get("alignmentCoordinates",[]), lxml)

        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["no_file"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def parseXMLTTP(self, file_content):
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
                HasLandXML = "stationHorizontal" in self.dataStorage.get("LandXML",{}) and len(self.dataStorage.get("LandXML",{}).get("stationHorizontal")) > 0

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
                LandXMLMin = np.nanmin(self.dataStorage.get("LandXML",{}).get("stationHorizontal"))
                LandXMLMax = np.nanmax(self.dataStorage.get("LandXML",{}).get("stationHorizontal"))

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
            
    # def importStopsTTP(self):
    #     file_content = self.getFileContent()
    #     if file_content is not None:
    #         XMLTTPData = readfile.ReadFile().ParseXMLTTP(file_content)
    #         stations = XMLTTPData.get("stationSpeedLimits", [])
    #         settings = self.dataStorage.setdefault("settingsData", {})
    #         trainStops = settings.setdefault("trainStops", [])
    #         defaultDwell = float(settings.get("defaultDwellTime", 30.0))
    #         for st in stations:
    #             trainStops.append([float(st), defaultDwell])
    #         lan = lang.DIC[self.current_language]
    #         msg = QMessageBox()
    #         msg.setWindowTitle(lan.get("importStopsTTP", "Import Stops"))
    #         msg.setText(f"Imported {len(stations)} stops.")
    #         msg.setIcon(QMessageBox.Icon.Information)
    #         msg.exec()
    #     else:
    #         lan = lang.DIC[self.current_language]
    #         err = QMessageBox()
    #         err.setWindowTitle(lan["error"])
    #         err.setText(lan["no_file"])
    #         err.setIcon(QMessageBox.Icon.Warning)
    #         err.exec()

    def plotCant(self):
        lan = lang.DIC[self.current_language]
        lxml = self.dataStorage.get("LandXML",{})

        self.canvasAlignment.ax_cant.clear()
        self.plotCantData.clear()

        stationCant = lxml.get("stationCant")
        stationCantPossible = lxml.get("stationCantPossible")

        if (stationCant is None or len(stationCant) == 0) and (stationCantPossible is None or len(stationCantPossible) == 0):
            self.canvasAlignment.draw()
            return

        cant = lxml.get("cant")
        if (cant is not None and len(cant)>0) and (stationCant is not None and len(stationCant)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCant, cant, marker='o', linestyle='-', color='black', label=lan["cant"])
            self.plotCantData["cant"] = line
            line.set_visible(self.toggleCantAction.isChecked())

        cantPossible = lxml.get("cantPossible")
        if (cantPossible is not None and len(cantPossible)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cantPossible, marker='o', linestyle='-', color='green', label=lan["cant_possible"])
            self.plotCantData["cantPossible"] = line
            line.set_visible(self.toggleCantPossibleAction.isChecked())

        cDef100 = lxml.get("cDef100")
        if (cDef100 is not None and len(cDef100)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cDef100, marker='o', linestyle='-', color='red', label=lan["cdef_100"])
            self.plotCantData["cDef100"] = line
            line.set_visible(self.toggleCDef100Action.isChecked())

        cDef130 = lxml.get("cDef130")
        if (cDef130 is not None and len(cDef130)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cDef130, marker='o', linestyle='-', color='teal', label=lan["cdef_130"])
            self.plotCantData["cDef130"] = line
            line.set_visible(self.toggleCDef130Action.isChecked())

        cDef150 = lxml.get("cDef150")
        if (cDef150 is not None and len(cDef150)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cDef150, marker='o', linestyle='-', color='darkorchid', label=lan["cdef_150"])
            self.plotCantData["cDef150"] = line
            line.set_visible(self.toggleCDef150Action.isChecked())

        cDefK = lxml.get("cDefK")
        if (cDefK is not None and len(cDefK)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cDefK, marker='o', linestyle='-', color='cornflowerblue', label=lan["cdef_K"])
            self.plotCantData["cDefK"] = line
            line.set_visible(self.toggleCDefKAction.isChecked())

        cantDef100 = lxml.get("cantDef100")
        if (cantDef100 is not None and len(cantDef100)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cantDef100, marker='o', linestyle='-', color='tomato', label=lan["cant_def_100"])
            self.plotCantData["cantDef100"] = line
            line.set_visible(self.toggleCantDef100Action.isChecked())

        cantDef130 = lxml.get("cantDef130")
        if (cantDef130 is not None and len(cantDef130)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cantDef130, marker='o', linestyle='-', color='aqua', label=lan["cant_def_130"])
            self.plotCantData["cantDef130"] = line
            line.set_visible(self.toggleCantDef130Action.isChecked())

        cantDef150 = lxml.get("cantDef150")
        if (cantDef150 is not None and len(cantDef150)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cantDef150, marker='o', linestyle='-', color='mediumorchid', label=lan["cant_def_150"])
            self.plotCantData["cantDef150"] = line
            line.set_visible(self.toggleCantDef150Action.isChecked())

        cantDefK = lxml.get("cantDefK")
        if (cantDefK is not None and len(cantDefK)>0) and (stationCantPossible is not None and len(stationCantPossible)>0):
            line, = self.canvasAlignment.ax_cant.plot(stationCantPossible, cantDefK, marker='o', linestyle='-', color='royalblue', label=lan["cant_def_K"])
            self.plotCantData["cantDefK"] = line
            line.set_visible(self.toggleCantDefKAction.isChecked())

        self.canvasAlignment.ax_cant.grid(True)
        self.canvasAlignment.ax_cant.autoscale(enable=True, axis='x', tight=True)
        
        # Srovnání osy y tak, aby 0 byla přesně uprostřed grafu
        ymin, ymax = self.canvasAlignment.ax_cant.get_ylim()
        y_limit = 500
        self.canvasAlignment.ax_cant.set_ylim(-y_limit, y_limit)

        self.canvasAlignment.ax_cant.set_xlabel(lan["station"])
        self.canvasAlignment.ax_cant.set_ylabel(lan["cant"])
        self.canvasAlignment.ax_cant.set_title(f'{lan["cant"]} vs {lan["station"]}', loc = 'left')
        self.canvasAlignment.ax_cant.tick_params(axis='y', labelcolor='tab:blue')
        if self.canvasAlignment.ax_cant.lines:
            self.canvasAlignment.ax_cant.legend(loc = 'upper left')
        self.canvasAlignment.draw()

    def plotCurvature(self):
        lan = lang.DIC[self.current_language]
        lxml = self.dataStorage.get("LandXML",{})

        self.canvasAlignment.ax_curvature.clear()
        self.plotCurvatureData.clear()

        # Initial check to avoid plotting data without station available
        stationHorizontal = lxml.get("stationHorizontal")
        stationHorizontalNew = lxml.get("stationHorizontalNew")
        if (stationHorizontal is None or len(stationHorizontal) == 0) and (stationHorizontalNew is None or len(stationHorizontalNew) == 0):
            self.canvasAlignment.draw()
            return  # No data to plot
        
        def fractionFormatter(x, pos = None):
            if np.isclose(x, 0, atol=1e-6):
                return "0"
            else:
                sign = "-" if x < 0 else ""
                return f"{sign}1/{abs(int(round(1/x)))}"

        curvature = lxml.get("curvature")
        if (curvature is not None and len(curvature) > 0) and (stationHorizontal is not None and len(stationHorizontal) > 0):
            line, = self.canvasAlignment.ax_curvature.plot(stationHorizontal, curvature, marker='o', linestyle='-', color='tab:gray', label=lan["curvature"])
            self.plotCurvatureData["curvature"] = line
            line.set_visible(self.toggleCurvatureAction.isChecked())

        curvatureNew = lxml.get("curvatureNew")
        if (curvatureNew is not None and len(curvatureNew) > 0) and (stationHorizontalNew is not None and len(stationHorizontalNew) > 0):
            line, = self.canvasAlignment.ax_curvature.plot(stationHorizontalNew, curvatureNew, marker='o', linestyle='-', color='tab:gray', label=lan["curvature"])
            self.plotCurvatureData["curvatureNew"] = line
            line.set_visible(self.toggleCurvatureNewAction.isChecked())
        
        self.canvasAlignment.ax_curvature.yaxis.set_label_position("right")
        self.canvasAlignment.ax_curvature.yaxis.tick_right()
        self.canvasAlignment.ax_curvature.grid(False)
        self.canvasAlignment.ax_curvature.autoscale(enable=True, axis='x', tight=True)
        
        # Srovnání osy y tak, aby 0 byla přesně uprostřed grafu (sladění s ax_cant)
        ymin, ymax = self.canvasAlignment.ax_curvature.get_ylim()
        y_limit = max(abs(ymin), abs(ymax))
        self.canvasAlignment.ax_curvature.set_ylim(-y_limit, y_limit)

        self.canvasAlignment.ax_curvature.set_xlabel(lan["station"])
        self.canvasAlignment.ax_curvature.set_ylabel(lan["curvature"])
        self.canvasAlignment.ax_curvature.set_title(f'{lan["curvature"]} vs {lan["station"]}', loc ='right')
        self.canvasAlignment.ax_curvature.tick_params(axis='y', labelcolor='tab:orange')
        self.canvasAlignment.ax_curvature.yaxis.set_major_formatter(FuncFormatter(fractionFormatter))
        self.canvasAlignment.ax_curvature.legend(loc = 'upper right')
        self.canvasAlignment.draw()

    def plotProfile(self):
        lan = lang.DIC[self.current_language]
        lxml = self.dataStorage.get("LandXML",{})

        self.canvasProfile.ax_profile.clear()
        self.plotProfileData.clear()

        # Initial check to avoid plotting data without station available
        stationVertical = lxml.get("stationVertical")
        if (stationVertical is None or len(stationVertical) == 0):
            self.canvasProfile.draw()
            return  # No data to plot
        
        elevation = lxml.get("elevation")
        slope = lxml.get("slope")
        midX = (stationVertical[:-1] + stationVertical[1:]) / 2
        midZ = (elevation[:-1] + elevation[1:]) / 2

        if (elevation is not None and len(elevation) > 0) and (stationVertical is not None and len(stationVertical) > 0):
            line, = self.canvasProfile.ax_profile.plot(stationVertical, elevation, marker='o', linestyle='-', color='tab:gray', label=lan["profile"])
            self.plotCurvatureData["profile"] = line
            line.set_visible(self.toggleProfileAction.isChecked())
            
            if self.toggleProfileAction.isChecked():
                for i in range(len(midX)):
                    self.canvasProfile.ax_profile.text(midX[i], midZ[i] + 0.1, f"{slope[i]:.2f} ‰", fontsize = 6)

        self.canvasProfile.ax_profile.grid(True)
        self.canvasProfile.ax_profile.autoscale(enable=True, axis='x', tight=True)
        self.canvasProfile.ax_profile.set_xlabel(lan["station"])
        self.canvasProfile.ax_profile.set_ylabel(lan["elevation"])
        self.canvasProfile.ax_profile.set_title(f'{lan["profile"]}')
        self.canvasProfile.ax_profile.legend()
        self.canvasProfile.draw()

    def plotSpeedLimits(self):
        lan = lang.DIC[self.current_language]

        self.canvasAlignment.ax_speed.clear()
        self.plotSpeedData.clear()

        stationSpeedLimits = self.dataStorage.get("stationSpeedLimits")
        stationSpeed100 = self.dataStorage.get("stationSpeed100")
        stationSpeed130 = self.dataStorage.get("stationSpeed130")
        stationSpeed150 = self.dataStorage.get("stationSpeed150")
        stationSpeedK = self.dataStorage.get("stationSpeedK")

        if (stationSpeedLimits is None or len(stationSpeedLimits) == 0) and (stationSpeed100 is None or len(stationSpeed100) == 0) and (stationSpeed130 is None or len(stationSpeed130) == 0) and (stationSpeed150 is None or len(stationSpeed150) == 0) and (stationSpeedK is None or len(stationSpeedK) == 0):
            self.canvasAlignment.draw()
            return  # No data to plot
        
        speedLimits = self.dataStorage.get("speedLimits")
        if (speedLimits is not None and len(speedLimits) > 0) and (stationSpeedLimits is not None and len(stationSpeedLimits) > 0):
            line, = self.canvasAlignment.ax_speed.step(stationSpeedLimits, speedLimits, where="post", marker='s', linestyle='-', color = 'black', label=lan["speed_lim"])
            self.plotSpeedData["speedLimits"] = line
            line.set_visible(self.toggleSpeedAction.isChecked())

        speedLimits100 = self.dataStorage.get("speedLimits100")
        if (speedLimits100 is not None and len(speedLimits100) > 0) and (stationSpeed100 is not None and len(stationSpeed100) > 0):
            line, = self.canvasAlignment.ax_speed.step(stationSpeed100, speedLimits100, where="post", marker='s', linestyle='-', color = 'red', label=lan["speed_lim_100"])
            self.plotSpeedData["speedLimits100"] = line
            line.set_visible(self.toggleSpeed100Action.isChecked())

        speedLimits130 = self.dataStorage.get("speedLimits130")
        if (speedLimits130 is not None and len(speedLimits130) > 0) and (stationSpeed130 is not None and len(stationSpeed130) > 0):
            line, = self.canvasAlignment.ax_speed.step(stationSpeed130, speedLimits130, where="post", marker='s', linestyle='-', color = 'teal', label=lan["speed_lim_130"])
            self.plotSpeedData["speedLimits130"] = line
            line.set_visible(self.toggleSpeed130Action.isChecked())

        speedLimits150 = self.dataStorage.get("speedLimits150")
        if (speedLimits150 is not None and len(speedLimits150) > 0) and (stationSpeed150 is not None and len(stationSpeed150) > 0):
            line, = self.canvasAlignment.ax_speed.step(stationSpeed150, speedLimits150, where="post", marker='s', linestyle='-', color = 'darkorchid', label=lan["speed_lim_150"])
            self.plotSpeedData["speedLimits150"] = line
            line.set_visible(self.toggleSpeed150Action.isChecked())

        speedLimitsK = self.dataStorage.get("speedLimitsK")
        if (speedLimitsK is not None and len(speedLimitsK) > 0) and (stationSpeedK is not None and len(stationSpeedK) > 0):
            line, = self.canvasAlignment.ax_speed.step(stationSpeedK, speedLimitsK, where="post", marker='s', linestyle='-', color='cornflowerblue', label=lan["speed_lim_K"])
            self.plotSpeedData["speedLimitsK"] = line
            line.set_visible(self.toggleSpeedKAction.isChecked())

        self.canvasAlignment.ax_speed.grid(True)
        self.canvasAlignment.ax_speed.autoscale(enable=True, axis='x', tight=True)
        self.canvasAlignment.ax_speed.set_xlabel(lan["station"])
        self.canvasAlignment.ax_speed.set_ylabel(lan["speed_lim"])
        self.canvasAlignment.ax_speed.set_title(f'{lan["speed_lim"]} vs {lan["station"]}')
        self.canvasAlignment.ax_speed.legend()
        self.canvasAlignment.draw()

    def plotKinematics(self):
        lan = lang.DIC[self.current_language]
        self.canvasKinematics.ax_tacho_track.clear()
        self.canvasKinematics.ax_tacho_time.clear()
        self.canvasKinematics.ax_dist_time.clear()
        self.canvasKinematics.ax_forces.clear()
        self.plotKinematicsData.clear()

        use_kmh = self.toggleUnitsAction.isChecked()
        v_factor = 3.6 if use_kmh else 1.0
        d_factor = 1000.0 if use_kmh else 1.0
        t_factor = 60.0 if use_kmh else 1.0 # time in minutes

        speed_lbl = lan.get("speedKmh", "Speed [km/h]") if use_kmh else lan.get("speedM", "Speed [m/s]")
        speed_lim_lbl = lan.get("speedLimKmh", "Speed Limit [km/h]") if use_kmh else lan.get("speedLimM", "Speed Limit [m/s]")
        dist_lbl = lan.get("distanceKm", "Distance [km]") if use_kmh else lan.get("distance", "Distance [m]")
        time_lbl = lan.get("timeMin", "Time [min]") if use_kmh else lan.get("time", "Time [s]")

        colors_speed = ['blue', 'purple', 'brown']
        colors_trac = ['green', 'lime', 'darkgreen']
        colors_brake = ['red', 'darkred', 'salmon']
        colors_res = ['orange', 'darkorange', 'gold']
        limit_colors = ['crimson', 'darkred', 'lightcoral']

        num_vehicles = self.dataStorage.get("num_vehicles", 1)
        vehicles_settings = self.dataStorage.get("settingsData", {}).get("vehicles", [])

        for v_idx in range(num_vehicles):
            stationSpeedLimits = self.dataStorage.get(f"stationSpeedLimitM_{v_idx}")
            speedLimits = self.dataStorage.get(f"speedLimitsM_{v_idx}")
            speedLimitsT = self.dataStorage.get(f"speedLimitsT_{v_idx}")
            
            lbl_v = f" V{v_idx+1}" if num_vehicles > 1 else ""

            if (speedLimits is not None and len(speedLimits) > 0) and (stationSpeedLimits is not None and len(stationSpeedLimits) > 0):
                line, = self.canvasKinematics.ax_tacho_track.step(stationSpeedLimits / d_factor, speedLimits * v_factor, where="post", marker='s', linestyle='-', color=limit_colors[v_idx], label=speed_lim_lbl + lbl_v)
                self.plotKinematicsData[f"tachoTrack_{v_idx}"] = line
                line.set_visible(self.toggleKinematicsSpeedLimitTrackAction.isChecked())

            if (speedLimitsT is not None and len(speedLimitsT) > 0) and (speedLimits is not None and len(speedLimits) > 0):
                line, = self.canvasKinematics.ax_tacho_time.step(speedLimitsT / t_factor, speedLimits * v_factor, where="post", marker='s', linestyle='-', color=limit_colors[v_idx], label=speed_lim_lbl + lbl_v)
                self.plotKinematicsData[f"tachoTime_{v_idx}"] = line
                line.set_visible(self.toggleKinematicsSpeedLimitTimeAction.isChecked())

            if (speedLimitsT is not None and len(speedLimitsT) > 0) and (stationSpeedLimits is not None and len(stationSpeedLimits) > 0):
                line, = self.canvasKinematics.ax_dist_time.plot(speedLimitsT / t_factor, stationSpeedLimits / d_factor, marker='s', linestyle='-', color=limit_colors[v_idx], label=dist_lbl + lbl_v)
                self.plotKinematicsData[f"distTime_{v_idx}"] = line
                line.set_visible(self.toggleKinematicsDistanceTimeAction.isChecked())

            kinematicsStation = self.dataStorage.get(f"kinematicsStationM_{v_idx}")
            kinematicsSpeed = self.dataStorage.get(f"kinematicsSpeedM_{v_idx}")
            kinematicsTime = self.dataStorage.get(f"kinematicsTimeS_{v_idx}")
            kinematicsDwells = self.dataStorage.get(f"kinematicsDwellTimesS_{v_idx}")

            if kinematicsStation is None or len(kinematicsStation) == 0:
                continue

            # Create copies for plotting time-based graphs, inserting arrival points for stops
            plot_times = list(kinematicsTime)
            plot_speeds = list(kinematicsSpeed)
            plot_stations = list(kinematicsStation)
            
            if kinematicsDwells is not None:
                stop_indices = np.where(kinematicsDwells > 0)[0]
                offset = 0
                for idx in stop_indices:
                    actual_idx = idx + offset
                    departure_time = plot_times[actual_idx]
                    dwell_time = kinematicsDwells[idx]
                    arrival_time = departure_time - dwell_time
                    
                    # Insert arrival point (arrival_time, 0 speed)
                    plot_times.insert(actual_idx, arrival_time)
                    plot_speeds.insert(actual_idx, 0.0)
                    plot_stations.insert(actual_idx, plot_stations[actual_idx])
                    offset += 1

            plot_times_arr = np.array(plot_times)
            plot_speeds_arr = np.array(plot_speeds)
            plot_stations_arr = np.array(plot_stations)

            if kinematicsSpeed is not None and len(kinematicsSpeed) > 0:
                line2, = self.canvasKinematics.ax_tacho_track.plot(kinematicsStation / d_factor, kinematicsSpeed * v_factor, linestyle='-', color=colors_speed[v_idx], label=speed_lbl + lbl_v)
                self.plotKinematicsData[f"simTrack_{v_idx}"] = line2
                line2.set_visible(self.toggleKinematicsSpeedLimitTrackAction.isChecked())

            if len(plot_times_arr) > 0 and len(plot_speeds_arr) > 0:
                line2, = self.canvasKinematics.ax_tacho_time.plot(plot_times_arr / t_factor, plot_speeds_arr * v_factor, linestyle='-', color=colors_speed[v_idx], label=speed_lbl + lbl_v)
                self.plotKinematicsData[f"simTime_{v_idx}"] = line2
                line2.set_visible(self.toggleKinematicsSpeedLimitTimeAction.isChecked())

            if len(plot_times_arr) > 0 and len(plot_stations_arr) > 0:
                line2, = self.canvasKinematics.ax_dist_time.plot(plot_times_arr / t_factor, plot_stations_arr / d_factor, linestyle='-', color=colors_speed[v_idx], label=dist_lbl + lbl_v)
                self.plotKinematicsData[f"distTimeSim_{v_idx}"] = line2
                line2.set_visible(self.toggleKinematicsDistanceTimeAction.isChecked())

            forceTrac = self.dataStorage.get(f"kinematicsForceTractionKN_{v_idx}")
            forceBrake = self.dataStorage.get(f"kinematicsForceBrakingKN_{v_idx}")
            forceRes = self.dataStorage.get(f"kinematicsForceResistanceKN_{v_idx}")

            if forceTrac is not None and len(forceTrac) > 0 and kinematicsStation is not None and len(kinematicsStation) > 0:
                line3, = self.canvasKinematics.ax_forces.plot(kinematicsStation / d_factor, forceTrac, linestyle='-', color=colors_trac[v_idx], label=lan.get("forceTraction", "Tractive Force [kN]") + lbl_v)
                self.plotKinematicsData[f"forceTrac_{v_idx}"] = line3
                line3.set_visible(self.toggleKinematicsForcesAction.isChecked())

            if forceBrake is not None and len(forceBrake) > 0 and kinematicsStation is not None and len(kinematicsStation) > 0:
                line4, = self.canvasKinematics.ax_forces.plot(kinematicsStation / d_factor, forceBrake, linestyle='-', color=colors_brake[v_idx], label=lan.get("forceBraking", "Braking Force [kN]") + lbl_v)
                self.plotKinematicsData[f"forceBrake_{v_idx}"] = line4
                line4.set_visible(self.toggleKinematicsForcesAction.isChecked())

            if forceRes is not None and len(forceRes) > 0 and kinematicsStation is not None and len(kinematicsStation) > 0:
                line5, = self.canvasKinematics.ax_forces.plot(kinematicsStation / d_factor, forceRes, linestyle='-', color=colors_res[v_idx], label=lan.get("forceResistance", "Resistance [kN]") + lbl_v)
                self.plotKinematicsData[f"forceRes_{v_idx}"] = line5
                line5.set_visible(self.toggleKinematicsForcesAction.isChecked())

        # Add train stops markers
        trainStops = self.dataStorage.get("settingsData", {}).get("trainStops", [])
        if trainStops:
            for stop in trainStops:
                try:
                    s_m = float(stop[0]) * 1000.0
                    name = str(stop[2]) if len(stop) > 2 else ""
                except (IndexError, ValueError):
                    continue
                
                # Track-speed vertical line
                self.canvasKinematics.ax_tacho_track.axvline(x=s_m / d_factor, color='gray', linestyle='--', alpha=0.7)
                if name:
                    self.canvasKinematics.ax_tacho_track.text(s_m / d_factor, 0, f" {name}", rotation=90, verticalalignment='bottom', color='black', fontsize=8, alpha=0.7)
                
                # Distance-time horizontal line
                self.canvasKinematics.ax_dist_time.axhline(y=s_m / d_factor, color='gray', linestyle='--', alpha=0.7)
                if name:
                    self.canvasKinematics.ax_dist_time.text(0, s_m / d_factor, f" {name}", verticalalignment='bottom', color='black', fontsize=8, alpha=0.7)
                
                # Time-speed vertical line (individual per vehicle due to different arrival times)
                for v_idx in range(num_vehicles):
                    kinematicsStation = self.dataStorage.get(f"kinematicsStationM_{v_idx}")
                    kinematicsTime = self.dataStorage.get(f"kinematicsTimeS_{v_idx}")

                    is_reversed = False
                    if v_idx < len(vehicles_settings):
                        is_reversed = vehicles_settings[v_idx].get("runReversed", False)

                    if kinematicsStation is not None and len(kinematicsStation) > 0:
                        xp, fp = kinematicsStation, kinematicsTime
                        if is_reversed:
                            xp = kinematicsStation[::-1]
                            fp = kinematicsTime[::-1]

                        stop_time = np.interp(s_m, xp, fp)
                        self.canvasKinematics.ax_tacho_time.axvline(x=stop_time / t_factor, color=limit_colors[v_idx], linestyle=':', alpha=0.5)
                        if name:
                            self.canvasKinematics.ax_tacho_time.text(stop_time / t_factor, 0, f" {name} (V{v_idx+1})", rotation=90, verticalalignment='bottom', color=limit_colors[v_idx], fontsize=7, alpha=0.7)

        self.canvasKinematics.ax_tacho_track.grid(True)
        self.canvasKinematics.ax_tacho_track.autoscale(enable=True, axis='x', tight=True)
        self.canvasKinematics.ax_tacho_track.set_xlabel(dist_lbl)
        self.canvasKinematics.ax_tacho_track.set_ylabel(speed_lim_lbl)
        self.canvasKinematics.ax_tacho_track.set_title(f'{speed_lim_lbl} vs {dist_lbl}')
        self.canvasKinematics.ax_tacho_track.legend()

        self.canvasKinematics.ax_tacho_time.grid(True)
        self.canvasKinematics.ax_tacho_time.autoscale(enable=True, axis='x', tight=True)
        self.canvasKinematics.ax_tacho_time.set_xlabel(time_lbl)
        self.canvasKinematics.ax_tacho_time.set_ylabel(speed_lim_lbl)
        self.canvasKinematics.ax_tacho_time.set_title(f'{speed_lim_lbl} vs {time_lbl}')
        self.canvasKinematics.ax_tacho_time.legend()

        self.canvasKinematics.ax_dist_time.grid(True)
        self.canvasKinematics.ax_dist_time.autoscale(enable=True, axis='x', tight=True)
        self.canvasKinematics.ax_dist_time.set_xlabel(time_lbl)
        self.canvasKinematics.ax_dist_time.set_ylabel(dist_lbl)
        self.canvasKinematics.ax_dist_time.set_title(lan["kinematicsDistanceTime"])
        self.canvasKinematics.ax_dist_time.legend()

        self.canvasKinematics.ax_forces.grid(True)
        self.canvasKinematics.ax_forces.autoscale(enable=True, axis='x', tight=True)
        self.canvasKinematics.ax_forces.set_xlabel(dist_lbl)
        self.canvasKinematics.ax_forces.set_ylabel(lan.get("forceKN", "Force [kN]"))
        self.canvasKinematics.ax_forces.set_title(lan.get("kinematicsForces", "Forces Profile"))
        self.canvasKinematics.ax_forces.legend()

        self.canvasKinematics.draw()


    def cleanData(self):
        self.cleanLandXMLData()
        self.cleanTTPData()
        self.cleanCalculatedCants()
        self.cleanCalculatedSpeeds()

        keep = ["settingsData",]

        for key in list(self.dataStorage.keys()):
            if key not in keep:
                del self.dataStorage[key]

    def cleanTTPData(self):
        self.textboxRawTTP.setPlainText("")
        self.tableTTP.setData({})
        self.dataStorage["stationSpeedLimits"] = []
        self.dataStorage["speedLimits"] = []
        self.dataStorage["stationSpeedLimitM"] = []
        self.dataStorage["speedLimitsM"] = []
        self.dataStorage["speedLimitsT"] = []
        self.plotSpeedData.clear()
        self.plotSpeedLimits()
        self.plotKinematics()

    def cleanLandXMLData(self):
        self.textboxRawLandXML.setPlainText("")
        self.tableLandXML.setData({})
        self.dataStorage["LandXML"] = {}
        self.plotCantData.clear()
        self.plotCurvatureData.clear()
        self.plotProfileData.clear()
        self.plotCant()
        self.plotCurvature()
        self.plotProfile()

    def cleanCalculatedCants(self):
        lxml = self.dataStorage.setdefault("LandXML",{})
        lxml["stationCantPossible"] = []
        lxml["cDef100"] = []
        lxml["cDef130"] = []
        lxml["cDef150"] = []
        lxml["cDefK"] = []
        lxml["cantPossible"] = []
        lxml["cantDef100"] = []
        lxml["cantDef130"] = []
        lxml["cantDef150"] = []
        lxml["cantDefK"] = []
        self.plotCantData.clear()
        self.plotCant()

    def cleanCalculatedSpeeds(self):
        self.dataStorage["stationSpeed100"] = []
        self.dataStorage["stationSpeed130"] = []
        self.dataStorage["stationSpeed150"] = []
        self.dataStorage["stationSpeedK"] = []
        self.dataStorage["speedLimits100"] = []
        self.dataStorage["speedLimits130"] = []
        self.dataStorage["speedLimits150"] = []
        self.dataStorage["speedLimitsK"] = []
        for v_idx in range(3):
            self.dataStorage[f"kinematicsStationM_{v_idx}"] = []
            self.dataStorage[f"kinematicsSpeedM_{v_idx}"] = []
            self.dataStorage[f"kinematicsTimeS_{v_idx}"] = []
            self.dataStorage[f"kinematicsAcceleration_{v_idx}"] = []
            self.dataStorage[f"kinematicsForceTractionKN_{v_idx}"] = []
            self.dataStorage[f"kinematicsForceBrakingKN_{v_idx}"] = []
            self.dataStorage[f"kinematicsForceResistanceKN_{v_idx}"] = []
            self.dataStorage[f"stationSpeedLimitM_{v_idx}"] = []
            self.dataStorage[f"speedLimitsM_{v_idx}"] = []
            self.dataStorage[f"speedLimitsT_{v_idx}"] = []
        self.plotSpeedData.clear()
        self.plotKinematicsData.clear()
        self.plotSpeedLimits()
        self.plotKinematics()

    # Set visibility
    def toggleCantVisibility(self, isChecked):
        if 'cant' in self.plotCantData:
            self.plotCantData["cant"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCantPossibleVisibility(self, isChecked):
        if 'cantPossible' in self.plotCantData:
            self.plotCantData["cantPossible"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCDef100Visibility(self, isChecked):
        if 'cDef100' in self.plotCantData:
            self.plotCantData["cDef100"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCDef130Visibility(self, isChecked):
        if 'cDef130' in self.plotCantData:
            self.plotCantData["cDef130"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCDef150Visibility(self, isChecked):
        if 'cDef150' in self.plotCantData:
            self.plotCantData["cDef150"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCDefKVisibility(self, isChecked):
        if 'cDefK' in self.plotCantData:
            self.plotCantData["cDefK"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCantDef100Visibility(self, isChecked):
        if 'cantDef100' in self.plotCantData:
            self.plotCantData["cantDef100"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCantDef130Visibility(self, isChecked):
        if 'cantDef100' in self.plotCantData:
            self.plotCantData["cantDef130"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCantDef150Visibility(self, isChecked):
        if 'cantDef150' in self.plotCantData:
            self.plotCantData["cantDef150"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCantDefKVisibility(self, isChecked):
        if 'cantDefK' in self.plotCantData:
            self.plotCantData["cantDefK"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCurvatureVisibility(self, isChecked):
        if 'curvature' in self.plotCurvatureData:
            self.plotCurvatureData["curvature"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleCurvatureNewVisibility(self, isChecked):
        if 'curvatureNew' in self.plotCurvatureData:
            self.plotCurvatureData["curvatureNew"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleSpeedVisibility(self, isChecked):
        if 'speedLimits' in self.plotSpeedData:
            self.plotSpeedData["speedLimits"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleSpeed100Visibility(self, isChecked):
        if 'speedLimits100' in self.plotSpeedData:
            self.plotSpeedData["speedLimits100"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleSpeed130Visibility(self, isChecked):
        if 'speedLimits130' in self.plotSpeedData:
            self.plotSpeedData["speedLimits130"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleSpeed150Visibility(self, isChecked):
        if 'speedLimits150' in self.plotSpeedData:
            self.plotSpeedData["speedLimits150"].set_visible(isChecked)
            self.canvasAlignment.draw()
    
    def toggleSpeedKVisibility(self, isChecked):
        if 'speedLimitsK' in self.plotSpeedData:
            self.plotSpeedData["speedLimitsK"].set_visible(isChecked)
            self.canvasAlignment.draw()

    def toggleProfileVisibility(self, isChecked):
        if 'profile' in self.plotProfileData:
            self.plotProfileData["profile"].set_visible(isChecked)
            self.canvasProfile.draw()

    def toggleKinematicsSpeedLimitTrackVisibility(self, isChecked):
        for v_idx in range(3):
            if f'tachoTrack_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"tachoTrack_{v_idx}"].set_visible(isChecked)
            if f'simTrack_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"simTrack_{v_idx}"].set_visible(isChecked)
        self.canvasKinematics.draw()

    def toggleKinematicsSpeedLimitTimeVisibility(self, isChecked):
        for v_idx in range(3):
            if f'tachoTime_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"tachoTime_{v_idx}"].set_visible(isChecked)
            if f'simTime_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"simTime_{v_idx}"].set_visible(isChecked)
        self.canvasKinematics.draw()

    def toggleKinematicsDistanceTimeVisibility(self, isChecked):
        for v_idx in range(3):
            if f'distTime_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"distTime_{v_idx}"].set_visible(isChecked)
            if f'distTimeSim_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"distTimeSim_{v_idx}"].set_visible(isChecked)
        self.canvasKinematics.draw()

    def toggleKinematicsForcesVisibility(self, isChecked):
        for v_idx in range(3):
            if f'forceTrac_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"forceTrac_{v_idx}"].set_visible(isChecked)
            if f'forceBrake_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"forceBrake_{v_idx}"].set_visible(isChecked)
            if f'forceRes_{v_idx}' in self.plotKinematicsData:
                self.plotKinematicsData[f"forceRes_{v_idx}"].set_visible(isChecked)
        self.canvasKinematics.draw()

    # Map settings
    def openMapSettings(self):
        lan = lang.DIC[self.current_language]
        dialog = gui_overlay.MapSettingsDialog(self.epsgInput, self.mapWidget.currentBaseMap, self.mapWidget.drawMode, self.mapWidget.speedProfile, lan, self)
        if dialog.exec():
            self.epsgInput, selected_map, draw_mode, speed_profile = dialog.getMapSettings()
            self.mapWidget.setBaseMap(selected_map)
            self.mapWidget.setDrawOptions(draw_mode, speed_profile)

    # Geometry settings
    def openGeometrySettings(self):
        lan = lang.DIC[self.current_language]

        dialog = gui_overlay.GeometrySettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())

    # Vehicle settings
    def openVehicleSettings(self):
        lan = lang.DIC[self.current_language]

        dialog = gui_overlay.VehicleSettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())

    # Stops settings
    def openStopsSettings(self):
        lan = lang.DIC[self.current_language]
        dialog = gui_overlay.StopsSettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())

    # Speed settings
    def openSpeedSettings(self):
        lan = lang.DIC[self.current_language]
        dialog = gui_overlay.SpeedSettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())

    # Design approach settings
    def openDesignApproach(self):
        lan = lang.DIC[self.current_language]

        dialog = gui_overlay.DesignApproachDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"]["designApproach"] = dialog.getDesignApproach()

    # Help
    def openHelp(self):
        lan = lang.DIC[self.current_language]
        dialog = gui_overlay.HelpDialog(lan, self)
        dialog.exec()

    # Reports
    def generateGeometryReport(self):
        lan = lang.DIC[self.current_language]
        lxml = self.dataStorage.get("LandXML", {})
        if not lxml or "stationCantPossible" not in lxml or len(lxml.get("stationCantPossible", [])) < 2:
            self.reportGeometryWidget.setPlainText(lan.get("no_data", "No data available. Calculate values first."))
            self.layoutTabsPlots.setCurrentWidget(self.layoutTabsPlotsReport_container)
            return

        stations = lxml["stationCantPossible"]
        geomType = lxml.get("geometryType", [])
        
        if len(geomType) != len(stations):
            self.reportGeometryWidget.setPlainText(lan.get("error", "Error") + ": Data lengths do not match. Please recalculate.")
            self.layoutTabsPlots.setCurrentWidget(self.layoutTabsPlotsReport_container)
            return

        def safe_get(d, key, fallback):
            val = d.get(key)
            if val is None or len(val) != len(stations):
                return fallback
            return val

        cant = safe_get(lxml, "cantPossible", np.zeros_like(stations))
        cDef100 = safe_get(lxml, "cDef100", np.zeros_like(stations))
        cDef130 = safe_get(lxml, "cDef130", np.zeros_like(stations))
        cDef150 = safe_get(lxml, "cDef150", np.zeros_like(stations))
        cDefK = safe_get(lxml, "cDefK", np.zeros_like(stations))

        v100 = safe_get(self.dataStorage, "speedLimits100", np.zeros_like(stations))
        v130 = safe_get(self.dataStorage, "speedLimits130", np.zeros_like(stations))
        v150 = safe_get(self.dataStorage, "speedLimits150", np.zeros_like(stations))
        vK = safe_get(self.dataStorage, "speedLimitsK", np.zeros_like(stations))

        dDdt100 = safe_get(lxml, "dDdt100", np.zeros_like(stations))
        dIdt100 = safe_get(lxml, "dIdt100", np.zeros_like(stations))
        dDdt130 = safe_get(lxml, "dDdt130", np.zeros_like(stations))
        dIdt130 = safe_get(lxml, "dIdt130", np.zeros_like(stations))
        dDdt150 = safe_get(lxml, "dDdt150", np.zeros_like(stations))
        dIdt150 = safe_get(lxml, "dIdt150", np.zeros_like(stations))
        dDdtK = safe_get(lxml, "dDdtK", np.zeros_like(stations))
        dIdtK = safe_get(lxml, "dIdtK", np.zeros_like(stations))

        limD100 = safe_get(lxml, "limitReachedD_I100", np.zeros(len(stations), dtype=bool))
        limI100 = safe_get(lxml, "limitReachedI_I100", np.zeros(len(stations), dtype=bool))
        limD130 = safe_get(lxml, "limitReachedD_I130", np.zeros(len(stations), dtype=bool))
        limI130 = safe_get(lxml, "limitReachedI_I130", np.zeros(len(stations), dtype=bool))
        limD150 = safe_get(lxml, "limitReachedD_I150", np.zeros(len(stations), dtype=bool))
        limI150 = safe_get(lxml, "limitReachedI_I150", np.zeros(len(stations), dtype=bool))
        limDK = safe_get(lxml, "limitReachedD_K", np.zeros(len(stations), dtype=bool))
        limIK = safe_get(lxml, "limitReachedI_K", np.zeros(len(stations), dtype=bool))
        
        radius = safe_get(lxml, "radius", np.full(len(stations), np.inf))
        curvature = safe_get(lxml, "curvature", np.zeros_like(stations))

        util_D_100 = safe_get(lxml, "util_D_I100", np.zeros_like(stations))
        util_I_100 = safe_get(lxml, "util_I_I100", np.zeros_like(stations))
        util_D_130 = safe_get(lxml, "util_D_I130", np.zeros_like(stations))
        util_I_130 = safe_get(lxml, "util_I_I130", np.zeros_like(stations))
        util_D_150 = safe_get(lxml, "util_D_I150", np.zeros_like(stations))
        util_I_150 = safe_get(lxml, "util_I_I150", np.zeros_like(stations))
        util_D_K = safe_get(lxml, "util_D_K", np.zeros_like(stations))
        util_I_K = safe_get(lxml, "util_I_K", np.zeros_like(stations))

        report_lines = [lan.get("reportGeometryTitle", "=== Geometry Report ==="), ""]

        def calc_n(L_m, d_val, v):
            if abs(d_val) < 1e-3 or v < 1e-3: return "INF"
            return f"{L_m * 1000 / (abs(d_val) * v):.2f}"
            
        def format_r(r_val):
            if np.isinf(r_val) or np.isnan(r_val): return "INF"
            return f"{r_val:.0f}"

        stats = {
            "V100": {"limit_D": 0, "limit_I": 0},
            "V130": {"limit_D": 0, "limit_I": 0},
            "V150": {"limit_D": 0, "limit_I": 0},
            "VK":   {"limit_D": 0, "limit_I": 0}
        }
        profile_stats = {
            "V100": {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0},
            "V130": {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0},
            "V150": {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0},
            "VK":   {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0}
        }
        total_elements = 0
        
        limits_dI = self.dataStorage.get("settingsData", {}).get("dI", [])
        approach = self.dataStorage.get("settingsData", {}).get("designApproach", "standard")
        curr_app_dI = approach.get("dI", "standard") if isinstance(approach, dict) else approach
        col_dI = {"standard": 2, "limit": 3, "minmax": 4}.get(curr_app_dI, 3)

        def get_dI_lim(v):
            for row in limits_dI:
                if row[0] < v <= row[1]: return row[col_dI]
            return limits_dI[-1][col_dI] if limits_dI else 0

        for i in range(len(stations) - 1):
            L = (stations[i+1] - stations[i]) * 1000

            profiles = [
                ("V100", v100, cDef100, dDdt100, dIdt100, limD100, limI100, util_D_100, util_I_100),
                ("V130", v130, cDef130, dDdt130, dIdt130, limD130, limI130, util_D_130, util_I_130),
                ("V150", v150, cDef150, dDdt150, dIdt150, limD150, limI150, util_D_150, util_I_150),
                ("VK", vK, cDefK, dDdtK, dIdtK, limDK, limIK, util_D_K, util_I_K),
            ]

            if L <= 0:
                transition_data = []
                any_deltaI = False
                dKappa = abs(curvature[i+1] - curvature[i])
                for p_name, v_arr, i_arr, dD_arr, dI_arr, lD_arr, lI_arr, util_D_arr, util_I_arr in profiles:
                    v_min = min(v_arr[i], v_arr[i+1])
                    # Physical deltaI: D is continuous at L=0 boundary (Stage 3), so D cancels
                    deltaI = 11.8 * v_min**2 * dKappa if v_min > 1e-3 else 0.0
                    dI_lim = get_dI_lim(v_min)
                    exceeded = deltaI > dI_lim + 1e-3
                    profile_stats[p_name]["max_deltaI"] = max(profile_stats[p_name]["max_deltaI"], deltaI)
                    transition_data.append((p_name, deltaI, v_min, dI_lim, exceeded))
                    if deltaI > 1e-3:
                        any_deltaI = True
                
                g_type_from = geomType[i] if i < len(geomType) else "-"
                g_type_to = geomType[i+1] if i+1 < len(geomType) else "-"
                if any_deltaI and g_type_from != "Spiral" and g_type_to != "Spiral":
                    report_lines.append(f"--- {lan.get('reportTransition', 'Transition')} | {lan['station']}: {stations[i]:.3f} | {g_type_from} -> {g_type_to} ---")
                    for p_name, dI_val, v_val, dI_lim_val, exceeded in transition_data:
                        flag = " (!)" if exceeded else ""
                        line_str = f"  [{p_name}] V: {v_val:.0f} km/h | deltaI: {dI_val:.0f} mm (limit {dI_lim_val:.0f} mm){flag}"
                        report_lines.append(line_str)
                    report_lines.append("")
                continue
            
            g_type = geomType[i]
            if g_type in ["Curve", "Spiral"]:
                total_elements += 1

            r_start = radius[i] if i < len(radius) else float('inf')
            r_end = radius[i+1] if i+1 < len(radius) else float('inf')
            
            max_v_elem = max(v100[i], v100[i+1], v130[i], v130[i+1], v150[i], v150[i+1], vK[i], vK[i+1])
            x_val = L / max_v_elem if max_v_elem > 0 else float('inf')
            str_x = f"{x_val:.2f}" if max_v_elem > 0 else "INF"
            
            header_line = f"--- {g_type} | {lan['station']}: {stations[i]:.3f} - {stations[i+1]:.3f} | L = {L:.2f} m ({str_x}*V)"
            if g_type == "Curve":
                header_line += f" | R: {format_r(r_start)} m"
            elif g_type == "Spiral":
                header_line += f" | R: {format_r(r_start)} -> {format_r(r_end)} m"
            header_line += " ---"
            report_lines.append(header_line)

            for p_name, v_arr, i_arr, dD_arr, dI_arr, lD_arr, lI_arr, util_D_arr, util_I_arr in profiles:
                v_start, v_end = v_arr[i], v_arr[i+1]
                sign_d_start = np.sign(cant[i]) if cant[i] != 0 else 1.0
                sign_d_end = np.sign(cant[i+1]) if cant[i+1] != 0 else 1.0
                d_start = sign_d_start * np.floor(np.abs(cant[i]))
                d_end = sign_d_end * np.floor(np.abs(cant[i+1]))
                sign_i_start = np.sign(i_arr[i]) if i_arr[i] != 0 else 1.0
                sign_i_end = np.sign(i_arr[i+1]) if i_arr[i+1] != 0 else 1.0
                i_start = sign_i_start * np.ceil(np.abs(i_arr[i]))
                i_end = sign_i_end * np.ceil(np.abs(i_arr[i+1]))
                dd_dt = dD_arr[i]
                di_dt = dI_arr[i]

                profile_stats[p_name]["max_D"] = max(profile_stats[p_name]["max_D"], abs(d_start), abs(d_end))
                profile_stats[p_name]["max_I"] = max(profile_stats[p_name]["max_I"], abs(i_start), abs(i_end))
                profile_stats[p_name]["max_dd_dt"] = max(profile_stats[p_name]["max_dd_dt"], abs(dd_dt))
                profile_stats[p_name]["max_di_dt"] = max(profile_stats[p_name]["max_di_dt"], abs(di_dt))

                line_str = f"  [{p_name}] V: {v_start:.0f} -> {v_end:.0f} km/h"
                if g_type == "Curve":
                    line_str += f" | D: {d_start:.0f} mm | I: {i_start:.0f} mm"
                elif g_type == "Spiral":
                    dD = abs(d_end - d_start)
                    dI = abs(i_end - i_start)
                    
                    if dD > 1e-3 and v_start > 1e-3:
                        n_val_f = L * 1000 / (dD * v_start)
                        profile_stats[p_name]["min_n"] = min(profile_stats[p_name]["min_n"], n_val_f)
                    if dI > 1e-3 and v_start > 1e-3:
                        nI_val_f = L * 1000 / (dI * v_start)
                        if dI > get_dI_lim(v_start):
                            profile_stats[p_name]["min_nI"] = min(profile_stats[p_name]["min_nI"], nI_val_f)
                        if nI_val_f < profile_stats[p_name]["min_nI_all"]:
                            profile_stats[p_name]["min_nI_all"] = nI_val_f
                            profile_stats[p_name]["min_nI_all_dI"] = dI
                        
                    n_val = calc_n(L, dD, v_start)
                    nI_val = calc_n(L, dI, v_start)
                    line_str += f" | D: {d_start:.0f} -> {d_end:.0f} mm | I: {i_start:.0f} -> {i_end:.0f} mm | n: {n_val} | nI: {nI_val} | deltaI: {dI:.0f} mm | dD/dt: {dd_dt:.2f} mm/s | dI/dt: {di_dt:.2f} mm/s"

                util_D_val = max(util_D_arr[i], util_D_arr[i+1])
                util_I_val = max(util_I_arr[i], util_I_arr[i+1])
                line_str += f" | Util D: {util_D_val*100:.1f}% | Util I: {util_I_val*100:.1f}%"

                if g_type in ["Curve", "Spiral"]:
                    profile_stats[p_name]["weighted_util_sum_D"] += util_D_val * L
                    profile_stats[p_name]["weighted_util_sum_I"] += util_I_val * L
                    profile_stats[p_name]["total_length"] += L

                if g_type in ["Curve", "Spiral"]:
                    if lD_arr[i] or lD_arr[i+1]: stats[p_name]["limit_D"] += 1
                    if lI_arr[i] or lI_arr[i+1]: stats[p_name]["limit_I"] += 1

                report_lines.append(line_str)
            report_lines.append("")

        report_lines.append(lan.get("reportStatisticsTitle", "=== Limiting Factors Statistics ==="))
        report_lines.append(f"{lan.get('totalElements', 'Total evaluated elements (Curve/Spiral)')}: {total_elements}")
        report_lines.append("")

        for p_name in ["V100", "V130", "V150", "VK"]:
            report_lines.append(f"--- {p_name} ---")
            report_lines.append(f"  {lan.get('lim_D', 'D (Cant)')} limit: {stats[p_name]['limit_D']}x")
            report_lines.append(f"  {lan.get('lim_I', 'I (Cant Deficiency)')} limit: {stats[p_name]['limit_I']}x")
            report_lines.append("")

        report_lines.append(lan.get("reportExtremesTitle", "=== Extremes of Geometric Parameters ==="))
        report_lines.append("")

        for p_name in ["V100", "V130", "V150", "VK"]:
            report_lines.append(f"--- {p_name} ---")
            p_stats = profile_stats[p_name]
            
            str_n = f"{p_stats['min_n']:.2f}" if p_stats['min_n'] != float('inf') else "-"
            str_nI = f"{p_stats['min_nI']:.2f}" if p_stats['min_nI'] != float('inf') else "-"
            str_nI_all = f"{p_stats['min_nI_all']:.2f} (deltaI = {p_stats['min_nI_all_dI']:.0f} mm)" if p_stats['min_nI_all'] != float('inf') else "-"
            
            weighted_avg_util_D = p_stats["weighted_util_sum_D"] / p_stats["total_length"] if p_stats["total_length"] > 0 else 0.0
            weighted_avg_util_I = p_stats["weighted_util_sum_I"] / p_stats["total_length"] if p_stats["total_length"] > 0 else 0.0
            report_lines.append(f"  {lan.get('stat_weighted_avg_util_D', 'Weighted Avg Util D [-]')}: {weighted_avg_util_D*100:.2f}%")
            report_lines.append(f"  {lan.get('stat_weighted_avg_util_I', 'Weighted Avg Util I [-]')}: {weighted_avg_util_I*100:.2f}%")

            report_lines.append(f"  {lan.get('stat_min_n', 'Min n [-]')}: {str_n}")
            report_lines.append(f"  {lan.get('stat_min_nI', 'Min nI [-]')}: {str_nI}")
            report_lines.append(f"  {lan.get('stat_min_nI_all', 'Min nI (all) [-]')}: {str_nI_all}")
            report_lines.append(f"  {lan.get('stat_max_dDdt', 'Max dD/dt [mm/s]')}: {p_stats['max_dd_dt']:.2f}")
            report_lines.append(f"  {lan.get('stat_max_dIdt', 'Max dI/dt [mm/s]')}: {p_stats['max_di_dt']:.2f}")
            report_lines.append(f"  {lan.get('stat_max_D', 'Max D [mm]')}: {p_stats['max_D']:.0f}")
            report_lines.append(f"  {lan.get('stat_max_I', 'Max I [mm]')}: {p_stats['max_I']:.0f}")
            report_lines.append(f"  {lan.get('stat_max_deltaI', 'Max deltaI [mm]')}: {p_stats['max_deltaI']:.0f}")
            report_lines.append("")

        self.reportGeometryWidget.setPlainText("\n".join(report_lines))
        self.layoutTabsPlots.setCurrentWidget(self.layoutTabsPlotsReport_container)

    def generateVehicleReport(self, v_idx=0):
        lan = lang.DIC[self.current_language]
        stations = self.dataStorage.get(f"kinematicsStationM_{v_idx}", [])
        if len(stations) == 0:
            self.reportVehicleTable.setData([{"Info": lan.get("no_data", "No data available. Calculate values first.")}])
            self.layoutTabsPlots.setCurrentWidget(self.layoutTabsPlotsReport_container)
            return

        speeds = self.dataStorage.get(f"kinematicsSpeedM_{v_idx}", np.zeros_like(stations))
        accels = self.dataStorage.get(f"kinematicsAcceleration_{v_idx}", np.zeros_like(stations))
        f_trac = self.dataStorage.get(f"kinematicsForceTractionKN_{v_idx}", np.zeros_like(stations))
        f_brake = self.dataStorage.get(f"kinematicsForceBrakingKN_{v_idx}", np.zeros_like(stations))
        f_res = self.dataStorage.get(f"kinematicsForceResistanceKN_{v_idx}", np.zeros_like(stations))
        times = self.dataStorage.get(f"kinematicsTimeS_{v_idx}", [])

        tableData = []

        # Travel time and average speed calculation
        if len(stations) > 1 and len(times) > 1:
            total_distance_m = stations[-1] - stations[0]
            total_time_s = times[-1]
            avg_speed_ms = total_distance_m / total_time_s if total_time_s > 0 else 0
            avg_speed_kmh = avg_speed_ms * 3.6
            minutes, seconds = divmod(total_time_s, 60)

            tableData.append({
                lan.get("station", "Station [km]"): f"=== {lan.get('run_summary_title', 'SOUHRN JÍZDY')} ===",
                lan.get("speed", "Speed [km/h]"): lan.get('total_travel_time', 'Celková jízdní doba:'),
                "Accel [m/s2]": f"{int(minutes):02d} min {int(seconds):02d} s",
                lan.get("forceTraction", "Tractive Force [kN]"): lan.get('average_speed', 'Průměrná rychlost:'),
                lan.get("forceBraking", "Braking Force [kN]"): f"{avg_speed_kmh:.2f} km/h",
                lan.get("forceResistance", "Resistance [kN]"): ""
            })
            tableData.append({k: "---" for k in tableData[0].keys()})

        # Energy calculation
        dx = np.diff(stations)
        dx = np.append(dx, 0)
        energy_kwh = np.sum(f_trac * dx) / 3600.0
        brake_energy_kwh = np.sum(f_brake * dx) / 3600.0
        
        # Insert energy summary block at the beginning
        tableData.append({
            lan.get("station", "Station [km]"): f"=== {lan.get('energy_title', 'ENERGY')} ===",
            lan.get("speed", "Speed [km/h]"): f"{lan.get('energyTraction', 'Traction [kWh]')}:",
            "Accel [m/s2]": f"{energy_kwh:.2f}",
            lan.get("forceTraction", "Tractive Force [kN]"): f"{lan.get('energyBraking', 'Braking [kWh]')}:",
            lan.get("forceBraking", "Braking Force [kN]"): f"{brake_energy_kwh:.2f}",
            lan.get("forceResistance", "Resistance [kN]"): ""
        })
        tableData.append({k: "---" for k in tableData[0].keys()})

        # Insert train stops summary block at the beginning
        trainStops = self.dataStorage.get("settingsData", {}).get("trainStops", [])
        if trainStops:
            tableData.append({
                lan.get("station", "Station [km]"): "=== ZASTÁVKY / STOPS ===",
                lan.get("speed", "Speed [km/h]"): "",
                "Accel [m/s2]": "",
                lan.get("forceTraction", "Tractive Force [kN]"): "",
                lan.get("forceBraking", "Braking Force [kN]"): "",
                lan.get("forceResistance", "Resistance [kN]"): ""
            })
            for stop in trainStops:
                try:
                    s_km = float(stop[0])
                    dwell = float(stop[1])
                    name = str(stop[2]) if len(stop) > 2 else ""
                    s_m = s_km * 1000.0
                    idx = np.argmin(np.abs(stations - s_m))
                    if np.abs(stations[idx] - s_m) < 2.0:
                        dep_time = self.dataStorage.get(f"kinematicsTimeS_{v_idx}")[idx]
                        arr_time = max(0, dep_time - dwell)
                        tableData.append({
                            lan.get("station", "Station [km]"): f"{s_km:.3f} {name}",
                            lan.get("speed", "Speed [km/h]"): f"Arr: {arr_time:.1f} s",
                            "Accel [m/s2]": f"Dep: {dep_time:.1f} s",
                            lan.get("forceTraction", "Tractive Force [kN]"): f"Dwell: {dwell} s",
                            lan.get("forceBraking", "Braking Force [kN]"): "-",
                            lan.get("forceResistance", "Resistance [kN]"): "-"
                        })
                except Exception:
                    continue
            tableData.append({k: "---" for k in tableData[0].keys()})

        for i in range(0, len(stations), 10):
            s_km = stations[i] / 1000.0
            tableData.append({
                lan.get("station", "Station [km]"): f"{s_km:.3f}",
                lan.get("speed", "Speed [km/h]"): f"{speeds[i]*3.6:.1f}",
                "Accel [m/s2]": f"{accels[i]:.3f}",
                lan.get("forceTraction", "Tractive Force [kN]"): f"{f_trac[i]:.1f}",
                lan.get("forceBraking", "Braking Force [kN]"): f"{f_brake[i]:.1f}",
                lan.get("forceResistance", "Resistance [kN]"): f"{f_res[i]:.1f}"
            })

        self.reportVehicleTable.setData(tableData)
        self.layoutTabsPlots.setCurrentWidget(self.layoutTabsPlotsReport_container)

    def exportGeometryReport(self):
        lan = lang.DIC[self.current_language]
        content = self.reportGeometryWidget.toPlainText()
        if not content:
            QMessageBox.warning(self, lan.get("error", "Error"), lan.get("no_data", "No data available. Calculate values first."))
            return
            
        filepath, _ = QFileDialog.getSaveFileName(self, lan.get("exportGeometryReport", "Export Geometry Report"), "", "Text Files (*.txt);;All Files (*)")
        if filepath:
            try:
                with open(filepath, "w", encoding="utf-8") as file:
                    file.write(content)
            except Exception as e:
                QMessageBox.critical(self, lan.get("error", "Error"), f"{e}")

    def exportVehicleReport(self, v_idx=0):
        lan = lang.DIC[self.current_language]
        stations = self.dataStorage.get(f"kinematicsStationM_{v_idx}", [])
        if len(stations) == 0:
            QMessageBox.warning(self, lan.get("error", "Error"), lan.get("no_data", "No data available. Calculate values first."))
            return

        filepath, _ = QFileDialog.getSaveFileName(self, lan.get("exportVehicleReport", "Export Vehicle Report"), "", "CSV Files (*.csv);;All Files (*)")
        if filepath:
            try:
                with open(filepath, "w", newline="", encoding="utf-8") as file:
                    writer = csv.writer(file)
                    headers = [
                        lan.get("station", "Station [km]"),
                        lan.get("speed", "Speed [km/h]"),
                        "Accel [m/s2]",
                        lan.get("forceTraction", "Tractive Force [kN]"),
                        lan.get("forceBraking", "Braking Force [kN]"),
                        lan.get("forceResistance", "Resistance [kN]")
                    ]
                    writer.writerow(headers)

                    speeds = self.dataStorage.get(f"kinematicsSpeedM_{v_idx}", np.zeros_like(stations))
                    accels = self.dataStorage.get(f"kinematicsAcceleration_{v_idx}", np.zeros_like(stations))
                    f_trac = self.dataStorage.get(f"kinematicsForceTractionKN_{v_idx}", np.zeros_like(stations))
                    f_brake = self.dataStorage.get(f"kinematicsForceBrakingKN_{v_idx}", np.zeros_like(stations))
                    f_res = self.dataStorage.get(f"kinematicsForceResistanceKN_{v_idx}", np.zeros_like(stations))

                    dx = np.diff(stations)
                    dx = np.append(dx, 0)
                    energy_kwh = np.sum(f_trac * dx) / 3600.0
                    brake_energy_kwh = np.sum(f_brake * dx) / 3600.0
                    
                    writer.writerow([f"=== {lan.get('energy_title', 'ENERGY')} ==="])
                    writer.writerow([lan.get('energyTraction', 'Traction [kWh]'), f"{energy_kwh:.2f}"])
                    writer.writerow([lan.get('energyBraking', 'Braking [kWh]'), f"{brake_energy_kwh:.2f}"])
                    writer.writerow([])

                    for i in range(len(stations)):
                        s_km = stations[i] / 1000.0
                        row = [
                            f"{s_km:.3f}",
                            f"{speeds[i]*3.6:.1f}",
                            f"{accels[i]:.3f}",
                            f"{f_trac[i]:.1f}",
                            f"{f_brake[i]:.1f}",
                            f"{f_res[i]:.1f}"
                        ]
                        writer.writerow(row)
            except Exception as e:
                QMessageBox.critical(self, lan.get("error", "Error"), f"{e}")

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
    
    def calculateGeometry(self):

        if "alignmentCoordinates" not in self.dataStorage.get("LandXML",{}):
            return
        
        calculate = geometry_engine.GeometryCalculator(self.dataStorage)
        calculate.runCalculationLoop()

        self.update_map_with_speeds()
        self.plotCant()
        self.plotSpeedLimits()

    def calculateGeometryI(self):

        if "alignmentCoordinates" not in self.dataStorage.get("LandXML",{}):
            return
        
        calculate = geometry_engine.GeometryCalculator(self.dataStorage)
        calculate.runCalculationLoopI()

        self.update_map_with_speeds()
        self.plotCant()
        self.plotSpeedLimits()

    def calculateTrainSpeed(self):
        vehicle = vehicle_engine.VehicleCalculator(self.dataStorage)
        vehicle.calculateKinematics()
        
        warnings = []
        for i in range(3):
            if self.dataStorage.get(f"kinematicsWarning_{i}") == "train_too_long":
                warnings.append(str(i+1))
                
        if warnings:
            lan = lang.DIC[self.current_language]
            msg = lan["train_too_long"] + f" (Vehicle: {', '.join(warnings)})"
            QMessageBox.warning(self, lan["error"], msg)

        vehicle.speedLimitsToTime()

        self.plotKinematics()

    def update_map_with_speeds(self):
        lxml = self.dataStorage.get("LandXML", {})
        if not lxml: return
        
        for profile in ["100", "130", "150", "K"]:
            lxml[f"speedLimits{profile}"] = self.dataStorage.get(f"speedLimits{profile}")
            lxml[f"stationSpeed{profile}"] = self.dataStorage.get(f"stationSpeed{profile}")
        
        self.mapWidget.drawAlignment(lxml.get("alignmentCoordinates", []), lxml)
        