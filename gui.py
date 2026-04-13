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
        openParseXMLTTPAction.triggered.connect(self.openXMLTTP)
        
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
        self.reportWidget = QPlainTextEdit()
        self.reportWidget.setReadOnly(True)
        layoutPlotsReport.addWidget(self.reportWidget)

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
        self.cleanMenu.setTitle(lan["clean"])
        self.exitMenu.setTitle(lan["exit"])
        self.helpMenu.setTitle(lan["help"])

        self.fileMenu.actions()[0].setText(lan["open_file"])
        self.fileMenu.actions()[1].setText(lan["autodetect"])
        self.fileMenu.actions()[2].setText(lan["open_parse_landxml"])
        self.fileMenu.actions()[3].setText(lan["open_parse_xmlttp"])
        # self.fileMenu.actions()[4].setText(lan.get("importStopsTTP", "Import Stops from XML TTP"))

        self.settingsMenu.actions()[2].setText(lan["mapSettings"])
        self.settingsMenu.actions()[3].setText(lan["geometrySettings"])
        self.settingsMenu.actions()[4].setText(lan.get("vehicleSettings", "Vehicle Settings"))
        self.settingsMenu.actions()[5].setText(lan.get("stopsSettings", "Stops Settings"))
        self.settingsMenu.actions()[6].setText(lan["designApproach"])

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

    def openLandXML(self):
        file_content = self.getFileContent()
        self.parseLandXML(file_content)

    def openXMLTTP(self):
        file_content = self.getFileContent()
        self.parseXMLTTP(file_content)

    def parseLandXML(self, file_content):
        if file_content is not None:
            self.textboxRawLandXML.setPlainText(file_content)
            LandXMLData = readfile.ReadFile().ParseLandXML(file_content, self.epsgInput)
            self.updateTableLandXML(LandXMLData)

            # Save data to central data storage
            self.dataStorage["LandXML"] = LandXMLData

            # Plot and draw data
            lxml = self.dataStorage.get("LandXML",{})
            self.plotCant()
            self.plotCurvature()
            self.plotProfile()
            self.mapWidget.drawAlignment(lxml.get("alignmentCoordinates",{}))

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
                return f"1/{int(round(1/x))}"

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
        self.canvasAlignment.ax_curvature.grid(True)
        self.canvasAlignment.ax_curvature.autoscale(enable=True, axis='x', tight=True)
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

        stationSpeedLimits = self.dataStorage.get("stationSpeedLimitM")
        speedLimits = self.dataStorage.get("speedLimitsM")
        speedLimitsT = self.dataStorage.get("speedLimitsT")

        if (speedLimits is not None and len(speedLimits) > 0) and (stationSpeedLimits is not None and len(stationSpeedLimits) > 0):
            line, = self.canvasKinematics.ax_tacho_track.step(stationSpeedLimits / d_factor, speedLimits * v_factor, where="post", marker='s', linestyle='-', color='crimson', label=speed_lim_lbl)
            self.plotKinematicsData["tachoTrack"] = line
            line.set_visible(self.toggleKinematicsSpeedLimitTrackAction.isChecked())

        if (speedLimitsT is not None and len(speedLimitsT) > 0) and (speedLimits is not None and len(speedLimits) > 0):
            line, = self.canvasKinematics.ax_tacho_time.step(speedLimitsT / t_factor, speedLimits * v_factor, where="post", marker='s', linestyle='-', color='crimson', label=speed_lim_lbl)
            self.plotKinematicsData["tachoTime"] = line
            line.set_visible(self.toggleKinematicsSpeedLimitTimeAction.isChecked())

        if (speedLimitsT is not None and len(speedLimitsT) > 0) and (stationSpeedLimits is not None and len(stationSpeedLimits) > 0):
            line, = self.canvasKinematics.ax_dist_time.plot(speedLimitsT / t_factor, stationSpeedLimits / d_factor, marker='s', linestyle='-', color='crimson', label=dist_lbl)
            self.plotKinematicsData["distTime"] = line
            line.set_visible(self.toggleKinematicsDistanceTimeAction.isChecked())

        kinematicsStation = self.dataStorage.get("kinematicsStationM")
        kinematicsSpeed = self.dataStorage.get("kinematicsSpeedM")
        kinematicsTime = self.dataStorage.get("kinematicsTimeS")

        if (kinematicsStation is not None and len(kinematicsStation) > 0) and (kinematicsSpeed is not None and len(kinematicsSpeed) > 0):
            line2, = self.canvasKinematics.ax_tacho_track.plot(kinematicsStation / d_factor, kinematicsSpeed * v_factor, linestyle='-', color='blue', label=speed_lbl)
            self.plotKinematicsData["simTrack"] = line2
            line2.set_visible(self.toggleKinematicsSpeedLimitTrackAction.isChecked())

        if (kinematicsTime is not None and len(kinematicsTime) > 0) and (kinematicsSpeed is not None and len(kinematicsSpeed) > 0):
            line2, = self.canvasKinematics.ax_tacho_time.plot(kinematicsTime / t_factor, kinematicsSpeed * v_factor, linestyle='-', color='blue', label=speed_lbl)
            self.plotKinematicsData["simTime"] = line2
            line2.set_visible(self.toggleKinematicsSpeedLimitTimeAction.isChecked())

        if (kinematicsTime is not None and len(kinematicsTime) > 0) and (kinematicsStation is not None and len(kinematicsStation) > 0):
            line2, = self.canvasKinematics.ax_dist_time.plot(kinematicsTime / t_factor, kinematicsStation / d_factor, linestyle='-', color='blue', label=dist_lbl)
            self.plotKinematicsData["distTimeSim"] = line2
            line2.set_visible(self.toggleKinematicsDistanceTimeAction.isChecked())

        forceTrac = self.dataStorage.get("kinematicsForceTractionKN")
        forceBrake = self.dataStorage.get("kinematicsForceBrakingKN")
        forceRes = self.dataStorage.get("kinematicsForceResistanceKN")

        if forceTrac is not None and len(forceTrac) > 0 and kinematicsStation is not None and len(kinematicsStation) > 0:
            line3, = self.canvasKinematics.ax_forces.plot(kinematicsStation / d_factor, forceTrac, linestyle='-', color='green', label=lan.get("forceTraction", "Tractive Force [kN]"))
            self.plotKinematicsData["forceTrac"] = line3
            line3.set_visible(self.toggleKinematicsForcesAction.isChecked())

        if forceBrake is not None and len(forceBrake) > 0 and kinematicsStation is not None and len(kinematicsStation) > 0:
            line4, = self.canvasKinematics.ax_forces.plot(kinematicsStation / d_factor, forceBrake, linestyle='-', color='red', label=lan.get("forceBraking", "Braking Force [kN]"))
            self.plotKinematicsData["forceBrake"] = line4
            line4.set_visible(self.toggleKinematicsForcesAction.isChecked())

        if forceRes is not None and len(forceRes) > 0 and kinematicsStation is not None and len(kinematicsStation) > 0:
            line5, = self.canvasKinematics.ax_forces.plot(kinematicsStation / d_factor, forceRes, linestyle='-', color='orange', label=lan.get("forceResistance", "Resistance [kN]"))
            self.plotKinematicsData["forceRes"] = line5
            line5.set_visible(self.toggleKinematicsForcesAction.isChecked())

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
        self.dataStorage["kinematicsStationM"] = []
        self.dataStorage["kinematicsSpeedM"] = []
        self.dataStorage["kinematicsTimeS"] = []
        self.dataStorage["kinematicsAcceleration"] = []
        self.dataStorage["kinematicsForceTractionKN"] = []
        self.dataStorage["kinematicsForceBrakingKN"] = []
        self.dataStorage["kinematicsForceResistanceKN"] = []
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
        if 'tachoTrack' in self.plotKinematicsData:
            self.plotKinematicsData["tachoTrack"].set_visible(isChecked)
        if 'simTrack' in self.plotKinematicsData:
            self.plotKinematicsData["simTrack"].set_visible(isChecked)
            self.canvasKinematics.draw()

    def toggleKinematicsSpeedLimitTimeVisibility(self, isChecked):
        if 'tachoTime' in self.plotKinematicsData:
            self.plotKinematicsData["tachoTime"].set_visible(isChecked)
        if 'simTime' in self.plotKinematicsData:
            self.plotKinematicsData["simTime"].set_visible(isChecked)
        self.canvasKinematics.draw()

    def toggleKinematicsDistanceTimeVisibility(self, isChecked):
        if 'distTime' in self.plotKinematicsData:
            self.plotKinematicsData["distTime"].set_visible(isChecked)
        if 'distTimeSim' in self.plotKinematicsData:
            self.plotKinematicsData["distTimeSim"].set_visible(isChecked)
            self.canvasKinematics.draw()

    def toggleKinematicsForcesVisibility(self, isChecked):
        if 'forceTrac' in self.plotKinematicsData:
            self.plotKinematicsData["forceTrac"].set_visible(isChecked)
        if 'forceBrake' in self.plotKinematicsData:
            self.plotKinematicsData["forceBrake"].set_visible(isChecked)
        if 'forceRes' in self.plotKinematicsData:
            self.plotKinematicsData["forceRes"].set_visible(isChecked)
        self.canvasKinematics.draw()

    # Map settings
    def openMapSettings(self):
        lan = lang.DIC[self.current_language]
        dialog = gui_overlay.MapSettingsDialog(self.epsgInput, self.mapWidget.currentBaseMap, lan, self)
        if dialog.exec():
            self.epsgInput, selected_map = dialog.getMapSettings()
            self.mapWidget.setBaseMap(selected_map)

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

    # Design approach settings
    def openDesignApproach(self):
        lan = lang.DIC[self.current_language]

        dialog = gui_overlay.DesignApproachDialog(lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"]["designApproach"] = dialog.getDesignApproach()

    # Help
    def openHelp(self):
        lan = lang.DIC[self.current_language]
        dialog = gui_overlay.HelpDialog(lan, self)
        dialog.exec()

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

        self.plotCant()
        self.plotSpeedLimits()

    def calculateGeometryI(self):

        if "alignmentCoordinates" not in self.dataStorage.get("LandXML",{}):
            return
        
        calculate = geometry_engine.GeometryCalculator(self.dataStorage)
        calculate.runCalculationLoopI()

        self.plotCant()
        self.plotSpeedLimits()

    def calculateTrainSpeed(self):

        # TO DO - Edit this line - changeable via dialogue window

        vehicle = vehicle_engine.VehicleCalculator(self.dataStorage)
        vehicle.calculateKinematics()
        vehicle.speedLimitsToTime()

        self.plotKinematics()
        