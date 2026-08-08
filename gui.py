# PySide6 imports
from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtWidgets import (QTabWidget, QApplication, QMainWindow, QPushButton, QWidget,
                                QHBoxLayout, QVBoxLayout, QLabel, QPlainTextEdit, QFileDialog,
                                QSplitter, QMessageBox, QStyle, QToolBar, QMenu, QStackedWidget,
                                QStatusBar)
from PySide6.QtGui import QAction, QActionGroup, QIcon, QCursor

# pyqtgraph imports
import pyqtgraph as pg

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
import theme_manager
import icons
from theme_manager import ThemeManager
from lazy_dock import LazyDockWidget
from ribbon import RibbonBar, SERIES_TOGGLE_PROPERTY
from workflow_dock import WorkflowStepperWidget
from graphs_dock import PerformanceGraphsWidget
from profile_dock import ProfilePlotWidget
from kinematics_dock import KinematicsPlotWidget
from help_dock import HelpWidget
from xml_editor import XmlCodeEditor
import copy

# Central viewport page indices
VIEW_MAP = 0
VIEW_REPORT = 1

# How long a transient status bar confirmation stays visible in milliseconds
SERIES_STATUS_TIMEOUT = 4000

# Vector icon assigned to each ribbon action, regenerated on every theme switch
ACTION_ICONS = {
    "openFileAction": "openText",
    "autodetectXMLAction": "open",
    "openParseLandXMLAction": "openLandxml",
    "openParseXMLTTPAction": "openTtp",
    "appendAutodetectXMLAction": "append",
    "appendLandXMLAction": "appendLandxml",
    "appendXMLTTPAction": "appendTtp",
    "exitAction": "exit",
    "helpAction": "help",
    "calculateGeometryAction": "calculate",
    "calculateGeometryIAction": "calculateAlt",
    "calculateTrainSpeedAction": "run",
    "cleanTTPDataAction": "cleanPart",
    "cleanLandXMLDataAction": "cleanPart",
    "cleanDataAction": "clean",
    "cleanCalculatedCantsAction": "cleanPart",
    "cleanCalculatedSpeedsAction": "cleanPart",
    "mapSettingsAction": "map",
    "geometrySettingsAction": "settings",
    "vehicleSettingsAction": "vehicle",
    "stopsSettingsAction": "stops",
    "speedSettingsAction": "settings",
    "designApproachAction": "settings",
    "toggleUnitsAction": "units",
    "themeAutoAction": "themeAuto",
    "themeLightAction": "themeLight",
    "themeDarkAction": "themeDark",
    "showMapAction": "viewMap",
    "showReportAction": "viewReport",
    "resetLayoutAction": "resetLayout",
    "foldAllAction": "foldAll",
    "unfoldAllAction": "unfoldAll",
    "reportGeometryAction": "report",
    "exportGeometryReportAction": "export",
}

# Compact ribbon captions for the data series toggles, full text stays in the tooltip
SERIES_SHORT_KEYS = {
    "toggleCantAction": "shortSeriesCant",
    "toggleCantPossibleAction": "shortSeriesCantPossible",
    "toggleCDef100Action": "shortSeriesCDef100",
    "toggleCDef130Action": "shortSeriesCDef130",
    "toggleCDef150Action": "shortSeriesCDef150",
    "toggleCDefKAction": "shortSeriesCDefK",
    "toggleCantDef100Action": "shortSeriesCantDef100",
    "toggleCantDef130Action": "shortSeriesCantDef130",
    "toggleCantDef150Action": "shortSeriesCantDef150",
    "toggleCantDefKAction": "shortSeriesCantDefK",
    "toggleCurvatureAction": "shortSeriesCurvature",
    "toggleCurvatureNewAction": "shortSeriesCurvatureNew",
    "toggleSpeedAction": "shortSeriesSpeed",
    "toggleSpeed100Action": "shortSeriesSpeed100",
    "toggleSpeed130Action": "shortSeriesSpeed130",
    "toggleSpeed150Action": "shortSeriesSpeed150",
    "toggleSpeedKAction": "shortSeriesSpeedK",
    "toggleProfileAction": "shortSeriesProfile",
    "toggleKinematicsSpeedLimitTrackAction": "shortSeriesTachoTrack",
    "toggleKinematicsSpeedLimitTimeAction": "shortSeriesTachoTime",
    "toggleKinematicsDistanceTimeAction": "shortSeriesDistTime",
    "toggleKinematicsForcesAction": "shortSeriesForces",
}

# Short text badges rendered as icons for the data series toggle actions
SERIES_BADGES = {
    "toggleCantAction": "D",
    "toggleCantPossibleAction": "Dp",
    "toggleCDef100Action": "I100",
    "toggleCDef130Action": "I130",
    "toggleCDef150Action": "I150",
    "toggleCDefKAction": "IK",
    "toggleCantDef100Action": "D+I100",
    "toggleCantDef130Action": "D+I130",
    "toggleCantDef150Action": "D+I150",
    "toggleCantDefKAction": "D+IK",
    "toggleCurvatureAction": "1/R",
    "toggleCurvatureNewAction": "1/Rn",
    "toggleSpeedAction": "v_lim",
    "toggleSpeed100Action": "V100",
    "toggleSpeed130Action": "V130",
    "toggleSpeed150Action": "V150",
    "toggleSpeedKAction": "VK",
    "toggleProfileAction": "H",
    "toggleKinematicsSpeedLimitTrackAction": "v-s",
    "toggleKinematicsSpeedLimitTimeAction": "v-t",
    "toggleKinematicsDistanceTimeAction": "s-t",
    "toggleKinematicsForcesAction": "F",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window settings
        self.resize(QSize(1400, 900))
        self.currentLanguage = "en"
        lan = lang.DIC[self.currentLanguage]
        self.setWindowTitle(lan["app_title"])

        # Other default settings
        self.epsgInput = "EPSG:5514"

        # Empty dictionaries for data to be loaded and plotted
        self.dataStorage = {}

        # Import default values to dataStorage
        self.dataStorage["settingsData"] = {}
        self.dataStorage["settingsData"] = copy.deepcopy(default_values.defVal)

        # Persistent settings store for layout, theme and language
        self.appSettings = QSettings("COYPU", "COYPU")

        # Right-click context menu keeps popup dialogs alive in this list
        self.popupWindows = []

        self.themeManager = ThemeManager(self)

        self.buildActions()
        self.buildCentralViews()
        self.buildDocks()

        # Icons need the dock toggle actions, so they are assigned after buildDocks
        self.applyActionIcons()

        self.buildRibbon()
        self.buildStatusBar()
        self.connectCursorSignals()
        self.connectMapSignals()

        self.themeManager.themeChanged.connect(self.onThemeChanged)
        self.restoreSession()

    # Create every QAction once and keep a named reference for translation
    def buildActions(self):
        lan = lang.DIC[self.currentLanguage]
        style = self.style()

        # File actions
        self.openFileAction = QAction(lan["open_file"], self)
        self.openFileAction.triggered.connect(self.openFile)

        self.autodetectXMLAction = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon), lan["autodetect"], self)
        self.autodetectXMLAction.setStatusTip(lan["autodetect_tip"])
        self.autodetectXMLAction.setShortcut("Ctrl+O")
        self.autodetectXMLAction.triggered.connect(self.openAutodetectXML)

        self.appendAutodetectXMLAction = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_FileLinkIcon),
            lan.get("append_autodetect", "Append Autodetect"), self)
        self.appendAutodetectXMLAction.setStatusTip(lan.get("append_autodetect_tip", "Autodetect and append"))
        self.appendAutodetectXMLAction.triggered.connect(self.appendAutodetectXML)

        self.openParseLandXMLAction = QAction(lan["open_parse_landxml"], self)
        self.openParseLandXMLAction.triggered.connect(self.openLandXML)

        self.appendLandXMLAction = QAction(lan.get("append_landxml", "Append LandXML"), self)
        self.appendLandXMLAction.triggered.connect(self.appendLandXML)

        self.openParseXMLTTPAction = QAction(lan["open_parse_xmlttp"], self)
        self.openParseXMLTTPAction.triggered.connect(self.openXMLTTP)

        self.appendXMLTTPAction = QAction(lan.get("append_xmlttp", "Append XML TTP"), self)
        self.appendXMLTTPAction.triggered.connect(self.appendXMLTTP)

        self.exitAction = QAction(lan["exit"], self)
        self.exitAction.triggered.connect(self.close)

        self.helpAction = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogHelpButton), lan["help"], self)
        self.helpAction.triggered.connect(self.openHelp)

        # Calculate actions
        self.calculateGeometryAction = QAction(lan["calculate_geometry"], self)
        self.calculateGeometryAction.triggered.connect(self.calculateGeometry)

        self.calculateGeometryIAction = QAction(lan["calculate_geometry_I"], self)
        self.calculateGeometryIAction.triggered.connect(self.calculateGeometryI)

        self.calculateTrainSpeedAction = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay), lan["calculate_train_speed"], self)
        self.calculateTrainSpeedAction.triggered.connect(self.calculateTrainSpeed)

        # Clean actions
        self.cleanTTPDataAction = QAction(lan["cleanTTP"], self)
        self.cleanTTPDataAction.triggered.connect(self.cleanTTPData)

        self.cleanLandXMLDataAction = QAction(lan["cleanLandXML"], self)
        self.cleanLandXMLDataAction.triggered.connect(self.cleanLandXMLData)

        self.cleanDataAction = QAction(
            QIcon.fromTheme("user-trash", style.standardIcon(QStyle.StandardPixmap.SP_TrashIcon)),
            lan["cleanAll"], self)
        self.cleanDataAction.triggered.connect(self.cleanData)

        self.cleanCalculatedCantsAction = QAction(lan["cleanCants"], self)
        self.cleanCalculatedCantsAction.triggered.connect(self.cleanCalculatedCants)

        self.cleanCalculatedSpeedsAction = QAction(lan["cleanSpeeds"], self)
        self.cleanCalculatedSpeedsAction.triggered.connect(self.cleanCalculatedSpeeds)

        # Settings actions
        self.mapSettingsAction = QAction(
            QIcon.fromTheme("internet-web-browser",
                            style.standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon)),
            lan["mapSettings"], self)
        self.mapSettingsAction.triggered.connect(self.openMapSettings)

        self.geometrySettingsAction = QAction(lan["geometrySettings"], self)
        self.geometrySettingsAction.triggered.connect(self.openGeometrySettings)

        self.vehicleSettingsAction = QAction(
            QIcon.fromTheme("preferences-system",
                            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)),
            lan.get("vehicleSettings", "Vehicle Settings"), self)
        self.vehicleSettingsAction.triggered.connect(self.openVehicleSettings)

        self.stopsSettingsAction = QAction(
            QIcon.fromTheme("appointment-new",
                            style.standardIcon(QStyle.StandardPixmap.SP_DialogResetButton)),
            lan.get("stopsSettings", "Stops Settings"), self)
        self.stopsSettingsAction.triggered.connect(self.openStopsSettings)

        self.speedSettingsAction = QAction(lan.get("speedSettings", "Speed Limits Settings"), self)
        self.speedSettingsAction.triggered.connect(self.openSpeedSettings)

        self.designApproachAction = QAction(lan["designApproach"], self)
        self.designApproachAction.triggered.connect(self.openDesignApproach)

        self.toggleUnitsAction = QAction(lan["units_kmh"], self)
        self.toggleUnitsAction.setCheckable(True)
        self.toggleUnitsAction.setChecked(False)
        self.toggleUnitsAction.triggered.connect(self.plotKinematics)

        # Language actions
        self.langCZAction = QAction("Čeština", self)
        self.langCZAction.triggered.connect(lambda: self.changeLanguage("cz"))
        self.langENAction = QAction("English", self)
        self.langENAction.triggered.connect(lambda: self.changeLanguage("en"))
        self.langDEAction = QAction("Deutsch", self)
        self.langDEAction.triggered.connect(lambda: self.changeLanguage("de"))

        # Theme override actions behave as a single exclusive choice
        self.themeGroup = QActionGroup(self)
        self.themeGroup.setExclusive(True)

        self.themeAutoAction = QAction(lan.get("themeAuto", "System default (auto)"), self)
        self.themeLightAction = QAction(lan.get("themeLight", "Always light"), self)
        self.themeDarkAction = QAction(lan.get("themeDark", "Always dark"), self)
        for action, mode in ((self.themeAutoAction, theme_manager.MODE_AUTO),
                             (self.themeLightAction, theme_manager.MODE_LIGHT),
                             (self.themeDarkAction, theme_manager.MODE_DARK)):
            action.setCheckable(True)
            action.setData(mode)
            self.themeGroup.addAction(action)
            action.triggered.connect(lambda checked=False, m=mode: self.applyThemeMode(m))
        self.themeAutoAction.setChecked(True)

        # Central viewport switching actions
        self.viewGroup = QActionGroup(self)
        self.viewGroup.setExclusive(True)

        self.showMapAction = QAction(
            QIcon.fromTheme("internet-web-browser",
                            style.standardIcon(QStyle.StandardPixmap.SP_DriveNetIcon)),
            lan.get("viewMap", "Map"), self)
        self.showMapAction.setCheckable(True)
        self.showMapAction.setChecked(True)
        self.showMapAction.triggered.connect(self.showMapView)
        self.viewGroup.addAction(self.showMapAction)

        self.showReportAction = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogContentsView),
            lan.get("viewReport", "Report"), self)
        self.showReportAction.setCheckable(True)
        self.showReportAction.triggered.connect(self.showReportView)
        self.viewGroup.addAction(self.showReportAction)

        # Layout action, the tooltip spells out what the short caption hides
        self.resetLayoutAction = QAction(lan.get("resetLayout", "Reset Layout"), self)
        self.resetLayoutAction.setToolTip(
            lan.get("resetLayoutTip", "Restore Default Window Layout"))
        self.resetLayoutAction.triggered.connect(self.resetLayout)

        # XML folding actions
        self.foldAllAction = QAction(lan.get("foldAll", "Fold all"), self)
        self.foldAllAction.triggered.connect(self.foldAllXml)
        self.unfoldAllAction = QAction(lan.get("unfoldAll", "Unfold all"), self)
        self.unfoldAllAction.triggered.connect(self.unfoldAllXml)

        # Report actions
        self.reportGeometryAction = QAction(lan.get("reportGeometry", "Report - Geometry"), self)
        self.reportGeometryAction.triggered.connect(self.generateGeometryReport)

        self.reportVehicleActions = []
        self.exportVehicleReportActions = []
        for vehicleIndex in range(3):
            reportAction = QAction(f'{lan.get("vehicle", "Vehicle")} {vehicleIndex + 1}', self)
            reportAction.triggered.connect(
                lambda checked=False, index=vehicleIndex: self.generateVehicleReport(index))
            self.reportVehicleActions.append(reportAction)

            exportAction = QAction(f'{lan.get("vehicle", "Vehicle")} {vehicleIndex + 1}', self)
            exportAction.triggered.connect(
                lambda checked=False, index=vehicleIndex: self.exportVehicleReport(index))
            self.exportVehicleReportActions.append(exportAction)

        self.exportGeometryReportAction = QAction(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton),
            lan.get("exportGeometryReport", "Export Geometry Report"), self)
        self.exportGeometryReportAction.triggered.connect(self.exportGeometryReport)

        self.buildSeriesActions()

    # Create the checkable series visibility actions used by the View ribbon tab
    def buildSeriesActions(self):
        lan = lang.DIC[self.currentLanguage]

        # Each entry maps an attribute name to its language key and handler
        seriesDefinitions = [
            ("toggleCantAction", "cant", self.toggleCantVisibility),
            ("toggleCantPossibleAction", "cant_possible", self.toggleCantPossibleVisibility),
            ("toggleCDef100Action", "cdef_100", self.toggleCDef100Visibility),
            ("toggleCDef130Action", "cdef_130", self.toggleCDef130Visibility),
            ("toggleCDef150Action", "cdef_150", self.toggleCDef150Visibility),
            ("toggleCDefKAction", "cdef_K", self.toggleCDefKVisibility),
            ("toggleCantDef100Action", "cant_def_100", self.toggleCantDef100Visibility),
            ("toggleCantDef130Action", "cant_def_130", self.toggleCantDef130Visibility),
            ("toggleCantDef150Action", "cant_def_150", self.toggleCantDef150Visibility),
            ("toggleCantDefKAction", "cant_def_K", self.toggleCantDefKVisibility),
            ("toggleCurvatureAction", "curvature", self.toggleCurvatureVisibility),
            ("toggleCurvatureNewAction", "curvature_new", self.toggleCurvatureNewVisibility),
            ("toggleSpeedAction", "speed_lim", self.toggleSpeedVisibility),
            ("toggleSpeed100Action", "speed_lim_100", self.toggleSpeed100Visibility),
            ("toggleSpeed130Action", "speed_lim_130", self.toggleSpeed130Visibility),
            ("toggleSpeed150Action", "speed_lim_150", self.toggleSpeed150Visibility),
            ("toggleSpeedKAction", "speed_lim_K", self.toggleSpeedKVisibility),
            ("toggleProfileAction", "profile", self.toggleProfileVisibility),
            ("toggleKinematicsSpeedLimitTrackAction", "kinematicsSpeedLimitTrack",
             self.toggleKinematicsSpeedLimitTrackVisibility),
            ("toggleKinematicsSpeedLimitTimeAction", "kinematicsSpeedLimitTime",
             self.toggleKinematicsSpeedLimitTimeVisibility),
            ("toggleKinematicsDistanceTimeAction", "kinematicsDistanceTime",
             self.toggleKinematicsDistanceTimeVisibility),
            ("toggleKinematicsForcesAction", "kinematicsForces",
             self.toggleKinematicsForcesVisibility),
        ]

        # Keyed by attribute name so updateTexts can retranslate them generically
        self.seriesActionKeys = {}

        for attributeName, languageKey, handler in seriesDefinitions:
            action = QAction(lan.get(languageKey, languageKey), self)

            # Every series toggles on its own, they are deliberately not exclusive
            action.setCheckable(True)
            action.setChecked(True)
            action.setProperty(SERIES_TOGGLE_PROPERTY, True)
            action.triggered.connect(handler)
            action.triggered.connect(
                lambda isChecked=False, toggledAction=action:
                self.announceSeriesToggle(toggledAction, isChecked))
            setattr(self, attributeName, action)
            self.seriesActionKeys[attributeName] = languageKey

    # Report the new visibility of a data series in the status bar
    def announceSeriesToggle(self, action, isChecked):
        lan = lang.DIC[self.currentLanguage]
        stateText = (lan.get("seriesShown", "shown") if isChecked
                     else lan.get("seriesHidden", "hidden"))
        self.statusBarWidget.showMessage(f"{action.text()}: {stateText}",
                                         SERIES_STATUS_TIMEOUT)

    # Give every ribbon action a generated vector icon or a short text badge
    def applyActionIcons(self):
        for attributeName, iconName in ACTION_ICONS.items():
            action = getattr(self, attributeName, None)
            if action is not None:
                action.setIcon(icons.makeIcon(iconName))

        for attributeName, badgeText in SERIES_BADGES.items():
            action = getattr(self, attributeName, None)
            if action is not None:
                action.setIcon(icons.makeBadge(badgeText))

        for vehicleIndex in range(len(self.reportVehicleActions)):
            self.reportVehicleActions[vehicleIndex].setIcon(icons.makeIcon("report"))
            self.exportVehicleReportActions[vehicleIndex].setIcon(icons.makeIcon("export"))

        for dock in self.allDocks():
            dock.toggleViewAction().setIcon(icons.makeIcon("panel"))

    # Every dock of the main window in a stable order, empty before buildDocks runs
    def allDocks(self):
        dockNames = ("dockWorkflow", "dockGraphs", "dockProfile", "dockKinematics",
                     "dockLandXmlRaw", "dockLandXmlParsed", "dockTtpRaw",
                     "dockTtpParsed", "dockHelp")
        return tuple(getattr(self, name) for name in dockNames if hasattr(self, name))

    # Build the central stacked viewport holding the map and the report page
    def buildCentralViews(self):
        self.centralStack = QStackedWidget()

        # View 1 is the interactive alignment map
        self.mapWidget = MapWidget(self, lang.DIC[self.currentLanguage])
        self.centralStack.addWidget(self.mapWidget)

        # View 2 is the generated calculation report
        reportPage = QWidget()
        reportLayout = QVBoxLayout(reportPage)
        reportLayout.setContentsMargins(0, 0, 0, 0)
        reportLayout.setSpacing(0)

        self.reportSplitter = QSplitter(Qt.Orientation.Horizontal)
        self.reportGeometryWidget = QPlainTextEdit()
        self.reportGeometryWidget.setReadOnly(True)
        self.reportSplitter.addWidget(self.reportGeometryWidget)
        self.reportVehicleTable = pg.TableWidget(sortable=False)
        self.reportSplitter.addWidget(self.reportVehicleTable)
        reportLayout.addWidget(self.reportSplitter)

        self.centralStack.addWidget(reportPage)
        self.setCentralWidget(self.centralStack)

    # Build every dockable panel and arrange the default layout
    def buildDocks(self):
        lan = lang.DIC[self.currentLanguage]

        self.setDockNestingEnabled(True)
        self.setDockOptions(QMainWindow.DockOption.AllowNestedDocks |
                            QMainWindow.DockOption.AllowTabbedDocks |
                            QMainWindow.DockOption.AnimatedDocks)

        # Dock 1 - interactive workflow guide
        self.workflowWidget = WorkflowStepperWidget(lan)
        self.workflowWidget.stepTriggered.connect(self.onWorkflowStep)
        self.dockWorkflow = LazyDockWidget(lan.get("dockWorkflow", "Workflow"), "dockWorkflow")
        self.dockWorkflow.setWidget(self.workflowWidget)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockWorkflow)

        # XML source viewers with folding support
        self.textboxRawLandXML = XmlCodeEditor()
        self.dockLandXmlRaw = LazyDockWidget(lan.get("dockLandXmlRaw", "LandXML - source"),
                                             "dockLandXmlRaw")
        self.dockLandXmlRaw.setWidget(self.textboxRawLandXML)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockLandXmlRaw)

        self.textboxRawTTP = XmlCodeEditor()
        self.dockTtpRaw = LazyDockWidget(lan.get("dockTtpRaw", "XML TTP - source"), "dockTtpRaw")
        self.dockTtpRaw.setWidget(self.textboxRawTTP)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dockTtpRaw)

        # Parsed XML tables
        self.tableLandXML = pg.TableWidget(sortable=False)
        self.dockLandXmlParsed = LazyDockWidget(lan.get("dockLandXmlParsed", "LandXML - data"),
                                                "dockLandXmlParsed", self.renderTableLandXML)
        self.dockLandXmlParsed.setWidget(self.tableLandXML)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockLandXmlParsed)

        self.tableTTP = pg.TableWidget(sortable=False)
        self.dockTtpParsed = LazyDockWidget(lan.get("dockTtpParsed", "XML TTP - data"),
                                            "dockTtpParsed")
        self.dockTtpParsed.setWidget(self.tableTTP)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockTtpParsed)

        # Dock 2 - linked track geometry and speed profile graphs
        self.graphsWidget = PerformanceGraphsWidget(lan)
        self.dockGraphs = LazyDockWidget(lan.get("dockGraphs", "Track geometry and speed profile"),
                                         "dockGraphs", self.refreshGraphsDock)
        self.dockGraphs.setWidget(self.graphsWidget)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.dockGraphs)

        # Remaining plot docks, all rendered with pyqtgraph
        self.profileWidget = ProfilePlotWidget(lan)
        self.dockProfile = LazyDockWidget(lan.get("dockProfile", "Plots - Profile"),
                                          "dockProfile", self.renderProfile)
        self.dockProfile.setWidget(self.profileWidget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockProfile)

        self.kinematicsWidget = KinematicsPlotWidget(lan)
        self.dockKinematics = LazyDockWidget(lan.get("dockKinematics", "Plots - Kinematics"),
                                             "dockKinematics", self.renderKinematics)
        self.dockKinematics.setWidget(self.kinematicsWidget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockKinematics)

        # Documentation panel rendering the project README
        self.helpWidget = HelpWidget(lan)
        self.dockHelp = LazyDockWidget(lan.get("dockHelp", "Help"), "dockHelp")
        self.dockHelp.setWidget(self.helpWidget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.dockHelp)
        self.dockHelp.hide()

        # Group related docks into tab stacks so the default layout stays readable
        self.tabifyDockWidget(self.dockLandXmlRaw, self.dockTtpRaw)
        self.tabifyDockWidget(self.dockLandXmlParsed, self.dockTtpParsed)
        self.tabifyDockWidget(self.dockLandXmlParsed, self.dockGraphs)
        self.tabifyDockWidget(self.dockProfile, self.dockKinematics)
        self.tabifyDockWidget(self.dockProfile, self.dockHelp)

        self.dockLandXmlRaw.raise_()
        self.dockGraphs.raise_()
        self.dockProfile.raise_()

        # Every dock builds its own title bar menu from the active translations
        for dock in self.allDocks():
            dock.setLanguage(lan)

        # Snapshot of the freshly built arrangement used by the reset action
        self.defaultLayoutState = self.saveState()
        self.defaultGeometry = self.saveGeometry()

    # Assemble the ribbon tabs from the previously created actions
    def buildRibbon(self):
        lan = lang.DIC[self.currentLanguage]

        self.ribbonBar = RibbonBar()

        projectPage = self.ribbonBar.addPage("project", lan.get("ribbonProject", "Project"),
                                             "ribbonProject")
        openGroup = projectPage.addGroup(lan.get("groupOpen", "Open"), "groupOpen")
        openGroup.addAction(self.autodetectXMLAction, shortKey="shortAutodetect")
        openGroup.addAction(self.openParseLandXMLAction, shortKey="shortLandxml")
        openGroup.addAction(self.openParseXMLTTPAction, shortKey="shortTtp")
        openGroup.addAction(self.openFileAction, shortKey="shortOpenFile")

        appendGroup = projectPage.addGroup(lan.get("groupAppend", "Append"), "groupAppend")
        appendGroup.addAction(self.appendAutodetectXMLAction, shortKey="shortAutodetect")
        appendGroup.addAction(self.appendLandXMLAction, shortKey="shortLandxml")
        appendGroup.addAction(self.appendXMLTTPAction, shortKey="shortTtp")

        cleanGroup = projectPage.addGroup(lan.get("groupClean", "Clean"), "groupClean")
        cleanGroup.addAction(self.cleanDataAction, shortKey="shortCleanAll")
        cleanGroup.addAction(self.cleanLandXMLDataAction, shortKey="shortLandxml")
        cleanGroup.addAction(self.cleanTTPDataAction, shortKey="shortTtp")

        exitGroup = projectPage.addGroup(lan.get("groupSession", "Session"), "groupSession")
        exitGroup.addAction(self.helpAction, shortKey="shortHelp")
        exitGroup.addAction(self.exitAction, shortKey="shortExit")

        geometryPage = self.ribbonBar.addPage("geometry", lan.get("ribbonGeometry", "Geometry"),
                                              "ribbonGeometry")
        calculateGroup = geometryPage.addGroup(lan.get("groupCalculate", "Calculate"),
                                               "groupCalculate")
        calculateGroup.addAction(self.calculateGeometryAction, shortKey="shortCalcDesign")
        calculateGroup.addAction(self.calculateGeometryIAction, shortKey="shortCalcAsBuilt")

        geometryCleanGroup = geometryPage.addGroup(lan.get("groupClean", "Clean"), "groupClean")
        geometryCleanGroup.addAction(self.cleanCalculatedCantsAction, shortKey="shortCleanCants")
        geometryCleanGroup.addAction(self.cleanCalculatedSpeedsAction, shortKey="shortCleanSpeeds")

        geometryConfigGroup = geometryPage.addGroup(lan.get("groupConfig", "Configuration"),
                                                    "groupConfig")
        geometryConfigGroup.addAction(self.geometrySettingsAction, shortKey="shortLimits")
        geometryConfigGroup.addAction(self.designApproachAction, shortKey="shortApproach")
        geometryConfigGroup.addAction(self.speedSettingsAction, shortKey="shortSpeeds")

        geometryReportGroup = geometryPage.addGroup(lan.get("groupReport", "Report"), "groupReport")
        geometryReportGroup.addAction(self.reportGeometryAction, shortKey="shortReport")
        geometryReportGroup.addAction(self.exportGeometryReportAction, shortKey="shortExport")

        simulationPage = self.ribbonBar.addPage("simulation", lan.get("ribbonSimulation", "Simulation"),
                                                "ribbonSimulation")
        runGroup = simulationPage.addGroup(lan.get("groupCalculate", "Calculate"), "groupCalculate")
        runGroup.addAction(self.calculateTrainSpeedAction, shortKey="shortRunSimulation")

        simulationConfigGroup = simulationPage.addGroup(lan.get("groupConfig", "Configuration"),
                                                        "groupConfig")
        simulationConfigGroup.addAction(self.vehicleSettingsAction, shortKey="shortVehicles")
        simulationConfigGroup.addAction(self.stopsSettingsAction, shortKey="shortStops")
        simulationConfigGroup.addAction(self.toggleUnitsAction, shortKey="shortUnits")

        simulationReportGroup = simulationPage.addGroup(lan.get("groupReport", "Report"), "groupReport")
        for reportAction in self.reportVehicleActions:
            simulationReportGroup.addAction(reportAction, isLarge=False)

        simulationExportGroup = simulationPage.addGroup(lan.get("groupExport", "Export"), "groupExport")
        for exportAction in self.exportVehicleReportActions:
            simulationExportGroup.addAction(exportAction, isLarge=False)

        viewPage = self.ribbonBar.addPage("view", lan.get("ribbonView", "View"), "ribbonView")
        centralGroup = viewPage.addGroup(lan.get("groupCentral", "Central view"), "groupCentral")
        centralGroup.addAction(self.showMapAction, shortKey="viewMap")
        centralGroup.addAction(self.showReportAction, shortKey="viewReport")

        panelsGroup = viewPage.addGroup(lan.get("groupPanels", "Panels"), "groupPanels")
        panelShortKeys = ("shortPanelWorkflow", "shortPanelGraphs", "shortPanelProfile",
                          "shortPanelKinematics", "shortPanelLandxmlRaw", "shortPanelLandxmlData",
                          "shortPanelTtpRaw", "shortPanelTtpData", "shortPanelHelp")
        for dock, shortKey in zip(self.allDocks(), panelShortKeys):
            panelsGroup.addAction(dock.toggleViewAction(), isLarge=False, shortKey=shortKey)

        layoutGroup = viewPage.addGroup(lan.get("groupLayout", "Layout"), "groupLayout")
        layoutGroup.addAction(self.resetLayoutAction, isLarge=False, shortKey="shortResetLayout")
        layoutGroup.addAction(self.foldAllAction, isLarge=False, shortKey="foldAll")
        layoutGroup.addAction(self.unfoldAllAction, isLarge=False, shortKey="unfoldAll")

        seriesPage = self.ribbonBar.addPage("series", lan.get("groupSeries", "Data series"),
                                            "groupSeries")
        cantSeriesGroup = seriesPage.addGroup(lan.get("groupSeriesCant", "Cant"), "groupSeriesCant")
        for attributeName in ("toggleCantAction", "toggleCantPossibleAction", "toggleCDef100Action",
                              "toggleCDef130Action", "toggleCDef150Action", "toggleCDefKAction",
                              "toggleCantDef100Action", "toggleCantDef130Action",
                              "toggleCantDef150Action", "toggleCantDefKAction",
                              "toggleCurvatureAction", "toggleCurvatureNewAction"):
            cantSeriesGroup.addAction(getattr(self, attributeName), isLarge=False,
                                      shortKey=SERIES_SHORT_KEYS[attributeName])

        speedSeriesGroup = seriesPage.addGroup(lan.get("groupSeriesSpeed", "Speed"),
                                               "groupSeriesSpeed")
        for attributeName in ("toggleSpeedAction", "toggleSpeed100Action", "toggleSpeed130Action",
                              "toggleSpeed150Action", "toggleSpeedKAction", "toggleProfileAction"):
            speedSeriesGroup.addAction(getattr(self, attributeName), isLarge=False,
                                       shortKey=SERIES_SHORT_KEYS[attributeName])

        kinematicsSeriesGroup = seriesPage.addGroup(lan.get("plotsKinematics", "Kinematics"),
                                                    "plotsKinematics")
        for attributeName in ("toggleKinematicsSpeedLimitTrackAction",
                              "toggleKinematicsSpeedLimitTimeAction",
                              "toggleKinematicsDistanceTimeAction",
                              "toggleKinematicsForcesAction"):
            kinematicsSeriesGroup.addAction(getattr(self, attributeName), isLarge=False,
                                            shortKey=SERIES_SHORT_KEYS[attributeName])

        settingsPage = self.ribbonBar.addPage("settings", lan.get("ribbonSettings", "Settings"),
                                              "ribbonSettings")
        themeGroup = settingsPage.addGroup(lan.get("groupTheme", "Theme"), "groupTheme")
        themeGroup.addAction(self.themeAutoAction, isLarge=False, shortKey="shortThemeAuto")
        themeGroup.addAction(self.themeLightAction, isLarge=False, shortKey="shortThemeLight")
        themeGroup.addAction(self.themeDarkAction, isLarge=False, shortKey="shortThemeDark")

        languageGroup = settingsPage.addGroup(lan.get("groupLanguage", "Language"), "groupLanguage")
        languageGroup.addAction(self.langCZAction, isLarge=False)
        languageGroup.addAction(self.langENAction, isLarge=False)
        languageGroup.addAction(self.langDEAction, isLarge=False)

        settingsConfigGroup = settingsPage.addGroup(lan.get("groupConfig", "Configuration"),
                                                    "groupConfig")
        settingsConfigGroup.addAction(self.mapSettingsAction, shortKey="shortMap")
        settingsConfigGroup.addAction(self.vehicleSettingsAction, shortKey="shortVehicles")
        settingsConfigGroup.addAction(self.stopsSettingsAction, shortKey="shortStops")
        settingsConfigGroup.addAction(self.geometrySettingsAction, shortKey="shortLimits")

        # The ribbon replaces the classic menu bar at the top of the window
        self.setMenuWidget(self.ribbonBar)

    # Build the status bar showing engine state, chainage and active theme
    def buildStatusBar(self):
        lan = lang.DIC[self.currentLanguage]

        self.statusBarWidget = QStatusBar()
        self.setStatusBar(self.statusBarWidget)

        self.statusEngineLabel = QLabel()
        self.statusChainageLabel = QLabel()
        self.statusThemeLabel = QLabel()

        self.statusBarWidget.addWidget(self.statusEngineLabel, 1)
        self.statusBarWidget.addPermanentWidget(self.statusChainageLabel)
        self.statusBarWidget.addPermanentWidget(self.statusThemeLabel)

        self.setEngineStatus(lan.get("statusReady", "Ready"))
        self.updateStatusChainage(None)

    # Connect the crosshair signals so graphs, profile, map and status bar stay in sync
    def connectCursorSignals(self):
        self.graphsWidget.cursorMoved.connect(self.onCursorMoved)
        self.profileWidget.cursorMoved.connect(self.onCursorMoved)
        self.mapWidget.cursorMoved.connect(self.onCursorMoved)

    # Keep the map settings dialog and the floating map controls in agreement
    def connectMapSignals(self):
        self.mapWidget.controlsPanel.drawModeChanged.connect(self.onMapDrawModeChanged)
        self.mapWidget.setStations(self.collectStations())

    # Remember the style chosen from the floating map controls
    def onMapDrawModeChanged(self, drawMode):
        self.dataStorage.setdefault("settingsData", {})["mapDrawMode"] = drawMode

    # Push the scheduled stops into every view that can show them
    def refreshStations(self):
        stations = self.collectStations()
        self.mapWidget.setStations(stations)
        self.graphsWidget.setStations(stations)
        self.profileWidget.setStations(stations)

    # Propagate a chainage to every view regardless of which one produced it
    def onCursorMoved(self, stationKm):
        self.updateStatusChainage(stationKm)
        self.graphsWidget.setCursorStation(stationKm)
        self.profileWidget.setCursorStation(stationKm)
        self.mapWidget.setCursorStation(stationKm)

    # Render the chainage readout in the status bar
    def updateStatusChainage(self, stationKm):
        lan = lang.DIC[self.currentLanguage]
        label = lan.get("statusChainage", "Chainage")
        if stationKm is None:
            self.statusChainageLabel.setText(f"{label}: -")
        else:
            self.statusChainageLabel.setText(f"{label}: {stationKm:.3f} km")

    # Render the core engine state in the status bar
    def setEngineStatus(self, text):
        lan = lang.DIC[self.currentLanguage]
        self.statusEngineLabel.setText(f'{lan.get("statusEngine", "Engine")}: {text}')

    # Render the active theme name in the status bar
    def updateStatusTheme(self):
        lan = lang.DIC[self.currentLanguage]
        modeLabels = {
            theme_manager.MODE_AUTO: lan.get("themeAuto", "System default (auto)"),
            theme_manager.MODE_LIGHT: lan.get("themeLight", "Always light"),
            theme_manager.MODE_DARK: lan.get("themeDark", "Always dark"),
        }
        activeName = lan.get("dark", "Dark") if self.themeManager.isDarkActive else lan.get("light", "Light")
        modeName = modeLabels.get(self.themeManager.currentMode, activeName)
        self.statusThemeLabel.setText(f'{lan.get("statusTheme", "Theme")}: {modeName}')

    # Apply a theme mode and remember the choice for the next session
    def applyThemeMode(self, mode):
        self.themeManager.applyTheme(mode)
        self.appSettings.setValue("theme/mode", mode)

    # React to a theme switch by restyling widgets that hold their own colours
    def onThemeChanged(self, mode):
        isDark = self.themeManager.isDarkActive
        tokens = self.themeManager.currentTokens

        # Icons are regenerated so their strokes match the new foreground colour
        icons.iconFactory.applyTheme(tokens)
        self.applyActionIcons()

        for editor in (self.textboxRawLandXML, self.textboxRawTTP):
            editor.applyTheme(isDark, tokens)

        self.workflowWidget.applyTheme(isDark, tokens)
        self.graphsWidget.applyTheme(isDark, tokens)
        self.profileWidget.applyTheme(isDark, tokens)
        self.kinematicsWidget.applyTheme(isDark, tokens)
        self.helpWidget.applyTheme(isDark, tokens)
        self.mapWidget.applyTheme(isDark, tokens)
        self.updateStatusTheme()

    # Switch the central viewport to the map page
    def showMapView(self):
        self.centralStack.setCurrentIndex(VIEW_MAP)
        self.showMapAction.setChecked(True)

    # Switch the central viewport to the report page
    def showReportView(self):
        self.centralStack.setCurrentIndex(VIEW_REPORT)
        self.showReportAction.setChecked(True)

    # Collapse every node in both XML source viewers
    def foldAllXml(self):
        self.textboxRawLandXML.foldAll()
        self.textboxRawTTP.foldAll()

    # Expand every node in both XML source viewers
    def unfoldAllXml(self):
        self.textboxRawLandXML.unfoldAll()
        self.textboxRawTTP.unfoldAll()

    # Push the current data into the linked track geometry and speed graphs
    def refreshGraphsDock(self):
        self.graphsWidget.setStations(self.collectStations())
        self.graphsWidget.updateGeometryData(self.dataStorage.get("LandXML", {}),
                                             self.seriesVisibility())
        self.graphsWidget.updateSpeedData(self.dataStorage, self.seriesVisibility())

    # Map every series toggle action onto the series key used by the plots
    def seriesVisibility(self):
        visibilityKeys = {
            "cant": self.toggleCantAction,
            "cantPossible": self.toggleCantPossibleAction,
            "cDef100": self.toggleCDef100Action,
            "cDef130": self.toggleCDef130Action,
            "cDef150": self.toggleCDef150Action,
            "cDefK": self.toggleCDefKAction,
            "cantDef100": self.toggleCantDef100Action,
            "cantDef130": self.toggleCantDef130Action,
            "cantDef150": self.toggleCantDef150Action,
            "cantDefK": self.toggleCantDefKAction,
            "curvature": self.toggleCurvatureAction,
            "curvatureNew": self.toggleCurvatureNewAction,
            "speedLimits": self.toggleSpeedAction,
            "speedLimits100": self.toggleSpeed100Action,
            "speedLimits130": self.toggleSpeed130Action,
            "speedLimits150": self.toggleSpeed150Action,
            "speedLimitsK": self.toggleSpeedKAction,
            "kinematicsSpeedLimitTrack": self.toggleKinematicsSpeedLimitTrackAction,
            "kinematicsSpeedLimitTime": self.toggleKinematicsSpeedLimitTimeAction,
            "kinematicsDistanceTime": self.toggleKinematicsDistanceTimeAction,
            "kinematicsForces": self.toggleKinematicsForcesAction,
        }
        return {seriesKey: action.isChecked() for seriesKey, action in visibilityKeys.items()}

    # Build the chainage and name pairs of every scheduled stop
    def collectStations(self):
        stations = []
        for stop in self.dataStorage.get("settingsData", {}).get("trainStops", []):
            try:
                stationKm = float(stop[0])
            except (IndexError, ValueError, TypeError):
                continue
            stations.append((stationKm, str(stop[2]) if len(stop) > 2 else ""))
        return stations

    # Dispatchers keep the existing call sites while honouring the lazy docks
    def plotCant(self):
        self.dockGraphs.requestUpdate()

    def plotCurvature(self):
        self.dockGraphs.requestUpdate()

    def plotSpeedLimits(self):
        self.dockGraphs.requestUpdate()

    def plotProfile(self):
        self.dockProfile.requestUpdate()

    def plotKinematics(self):
        self.dockKinematics.requestUpdate()
        self.dockGraphs.requestUpdate()

    # Run the action belonging to a workflow step and mark it as completed
    def onWorkflowStep(self, stepIndex):
        stepHandlers = [
            self.openLandXML,
            self.openXMLTTP,
            self.openStopsSettings,
            self.openVehicleSettings,
            self.calculateGeometry,
            self.calculateTrainSpeed,
            self.exportGeometryReport,
        ]
        if 0 <= stepIndex < len(stepHandlers):
            stepHandlers[stepIndex]()
            self.workflowWidget.markCompleted(stepIndex)

    # Restore geometry, dock state, theme and language from the previous session
    def restoreSession(self):
        savedLanguage = self.appSettings.value("ui/language", "en")
        if savedLanguage in lang.DIC:
            self.currentLanguage = savedLanguage

        savedGeometry = self.appSettings.value("layout/geometry")
        if savedGeometry is not None:
            self.restoreGeometry(savedGeometry)

        savedState = self.appSettings.value("layout/state")
        if savedState is not None:
            self.restoreState(savedState)

        savedMode = self.appSettings.value("theme/mode", theme_manager.MODE_AUTO)
        if savedMode not in (theme_manager.MODE_AUTO, theme_manager.MODE_LIGHT,
                             theme_manager.MODE_DARK):
            savedMode = theme_manager.MODE_AUTO

        for action in self.themeGroup.actions():
            action.setChecked(action.data() == savedMode)

        self.themeManager.applyTheme(savedMode)
        self.updateTexts()

    # Persist geometry and dock state so the next launch reopens the same layout
    def saveSession(self):
        self.appSettings.setValue("layout/geometry", self.saveGeometry())
        self.appSettings.setValue("layout/state", self.saveState())
        self.appSettings.setValue("ui/language", self.currentLanguage)
        self.appSettings.setValue("theme/mode", self.themeManager.currentMode)

    # Return every dock to the arrangement captured right after construction
    def resetLayout(self):
        lan = lang.DIC[self.currentLanguage]

        answer = QMessageBox.question(
            self, lan.get("resetLayout", "Reset Layout"),
            lan.get("resetLayoutConfirm",
                    "Are you sure you want to reset all windows and docks "
                    "to their default layout?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return

        # Rebuilding the dock layout inside the closing dialog crashes the web view
        QTimer.singleShot(0, self.applyDefaultLayout)

    # Restore the captured default arrangement and confirm it in the status bar
    def applyDefaultLayout(self):
        lan = lang.DIC[self.currentLanguage]

        self.restoreGeometry(self.defaultGeometry)
        self.restoreState(self.defaultLayoutState)
        self.statusBarWidget.showMessage(
            lan.get("statusLayoutReset", "Window layout restored to defaults"),
            SERIES_STATUS_TIMEOUT)

    def closeEvent(self, event):
        self.saveSession()
        super().closeEvent(event)

    # Change language function
    def changeLanguage(self, langCode):
        self.currentLanguage = langCode
        self.appSettings.setValue("ui/language", langCode)
        self.updateTexts()

    def updateTexts(self):
        lan = lang.DIC[self.currentLanguage]

        self.setWindowTitle(lan["app_title"])

        # Ribbon tab captions
        self.ribbonBar.setPageTitle("project", lan.get("ribbonProject", "Project"))
        self.ribbonBar.setPageTitle("geometry", lan.get("ribbonGeometry", "Geometry"))
        self.ribbonBar.setPageTitle("simulation", lan.get("ribbonSimulation", "Simulation"))
        self.ribbonBar.setPageTitle("view", lan.get("ribbonView", "View"))
        self.ribbonBar.setPageTitle("series", lan.get("groupSeries", "Data series"))
        self.ribbonBar.setPageTitle("settings", lan.get("ribbonSettings", "Settings"))

        # File actions
        self.openFileAction.setText(lan["open_file"])
        self.autodetectXMLAction.setText(lan["autodetect"])
        self.autodetectXMLAction.setStatusTip(lan["autodetect_tip"])
        self.appendAutodetectXMLAction.setText(lan.get("append_autodetect", "Append Autodetect"))
        self.appendAutodetectXMLAction.setStatusTip(lan.get("append_autodetect_tip", "Autodetect and append"))
        self.openParseLandXMLAction.setText(lan["open_parse_landxml"])
        self.appendLandXMLAction.setText(lan.get("append_landxml", "Append LandXML"))
        self.openParseXMLTTPAction.setText(lan["open_parse_xmlttp"])
        self.appendXMLTTPAction.setText(lan.get("append_xmlttp", "Append XML TTP"))
        self.exitAction.setText(lan["exit"])
        self.helpAction.setText(lan["help"])

        # Calculate actions
        self.calculateGeometryAction.setText(lan["calculate_geometry"])
        self.calculateGeometryIAction.setText(lan["calculate_geometry_I"])
        self.calculateTrainSpeedAction.setText(lan["calculate_train_speed"])

        # Clean actions
        self.cleanTTPDataAction.setText(lan["cleanTTP"])
        self.cleanLandXMLDataAction.setText(lan["cleanLandXML"])
        self.cleanDataAction.setText(lan["cleanAll"])
        self.cleanCalculatedCantsAction.setText(lan["cleanCants"])
        self.cleanCalculatedSpeedsAction.setText(lan["cleanSpeeds"])

        # Settings actions
        self.mapSettingsAction.setText(lan["mapSettings"])
        self.geometrySettingsAction.setText(lan["geometrySettings"])
        self.vehicleSettingsAction.setText(lan.get("vehicleSettings", "Vehicle Settings"))
        self.stopsSettingsAction.setText(lan.get("stopsSettings", "Stops Settings"))
        self.speedSettingsAction.setText(lan.get("speedSettings", "Speed Limits Settings"))
        self.designApproachAction.setText(lan["designApproach"])
        self.toggleUnitsAction.setText(lan["units_kmh"])

        # Theme, view and layout actions
        self.themeAutoAction.setText(lan.get("themeAuto", "System default (auto)"))
        self.themeLightAction.setText(lan.get("themeLight", "Always light"))
        self.themeDarkAction.setText(lan.get("themeDark", "Always dark"))
        self.showMapAction.setText(lan.get("viewMap", "Map"))
        self.showReportAction.setText(lan.get("viewReport", "Report"))
        self.resetLayoutAction.setText(lan.get("resetLayout", "Reset Layout"))
        self.resetLayoutAction.setToolTip(
            lan.get("resetLayoutTip", "Restore Default Window Layout"))
        self.foldAllAction.setText(lan.get("foldAll", "Fold all"))
        self.unfoldAllAction.setText(lan.get("unfoldAll", "Unfold all"))

        # Series visibility actions are translated from their recorded keys
        for attributeName, languageKey in self.seriesActionKeys.items():
            getattr(self, attributeName).setText(lan.get(languageKey, languageKey))

        # Report actions
        self.reportGeometryAction.setText(lan.get("reportGeometry", "Report - Geometry"))
        self.exportGeometryReportAction.setText(lan.get("exportGeometryReport", "Export Geometry Report"))
        for vehicleIndex in range(3):
            caption = f'{lan.get("vehicle", "Vehicle")} {vehicleIndex + 1}'
            self.reportVehicleActions[vehicleIndex].setText(caption)
            self.exportVehicleReportActions[vehicleIndex].setText(caption)

        # Dock titles
        self.dockWorkflow.setWindowTitle(lan.get("dockWorkflow", "Workflow"))
        self.dockGraphs.setWindowTitle(lan.get("dockGraphs", "Track geometry and speed profile"))
        self.dockProfile.setWindowTitle(lan.get("dockProfile", "Plots - Profile"))
        self.dockKinematics.setWindowTitle(lan.get("dockKinematics", "Plots - Kinematics"))
        self.dockLandXmlRaw.setWindowTitle(lan.get("dockLandXmlRaw", "LandXML - source"))
        self.dockLandXmlParsed.setWindowTitle(lan.get("dockLandXmlParsed", "LandXML - data"))
        self.dockTtpRaw.setWindowTitle(lan.get("dockTtpRaw", "XML TTP - source"))
        self.dockTtpParsed.setWindowTitle(lan.get("dockTtpParsed", "XML TTP - data"))
        self.dockHelp.setWindowTitle(lan.get("dockHelp", "Help"))

        for dock in self.allDocks():
            dock.setLanguage(lan)

        # Child widgets holding their own captions
        self.workflowWidget.updateTexts(lan)
        self.graphsWidget.updateLabels(lan)
        self.profileWidget.updateLabels(lan)
        self.kinematicsWidget.updateLabels(lan)
        self.helpWidget.updateTexts(lan)
        self.mapWidget.updateTexts(lan)
        self.ribbonBar.retranslate(lan)

        self.setEngineStatus(lan.get("statusReady", "Ready"))
        self.updateStatusChainage(None)
        self.updateStatusTheme()

    def getVehicleName(self, vehicleIndex):
        # trainParam[0][0] from vehicle settings, returns an empty string when not available
        vehicles = self.dataStorage.get("settingsData", {}).get("vehicles", [])
        try:
            return str(vehicles[vehicleIndex]["trainParam"][0][0]).strip()
        except (IndexError, KeyError, TypeError):
            return ""

    def getFileContent(self):
        filepath, _ = QFileDialog.getOpenFileName(self, "Open File", "", "All Files (*);;Text Files (*.txt);;XML Files (*.xml)")
        
        # If cancelled, do nothing    
        if not filepath:
            return
        
        # Read file content
        fileContent = readfile.ReadFile().Read(filepath)
        return fileContent
    
    def openFile(self):
        fileContent = self.getFileContent()
        if fileContent is not None:
            self.textboxRawLandXML.setXmlText(fileContent)

    def openAutodetectXML(self):
        fileContent = self.getFileContent()
        if fileContent is None:
            return
        
        xmlType = readfile.ReadFile().XMLType(fileContent)
        if xmlType == 1:
            self.parseLandXML(fileContent)
        elif xmlType == 2:
            self.parseXMLTTP(fileContent)
        else:
            lan = lang.DIC[self.currentLanguage]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("unknown_xml_file", "Unknown XML file format."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def appendAutodetectXML(self):
        fileContent = self.getFileContent()
        if fileContent is None:
            return
        
        xmlType = readfile.ReadFile().XMLType(fileContent)
        if xmlType == 1:
            self.appendLandXMLContent(fileContent)
        elif xmlType == 2:
            self.appendXMLTTPContent(fileContent)
        else:
            lan = lang.DIC[self.currentLanguage]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("unknown_xml_file", "Unknown XML format."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def openLandXML(self):
        fileContent = self.getFileContent()
        self.parseLandXML(fileContent)

    def openXMLTTP(self):
        fileContent = self.getFileContent()
        self.parseXMLTTP(fileContent)

    def appendXMLTTP(self):
        if "stationSpeedLimits" not in self.dataStorage or len(self.dataStorage.get("stationSpeedLimits", [])) == 0:
            lan = lang.DIC[self.currentLanguage]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        fileContent = self.getFileContent()
        if not fileContent:
            return
        self.appendXMLTTPContent(fileContent)

    def appendXMLTTPContent(self, fileContent):
        if "stationSpeedLimits" not in self.dataStorage or len(self.dataStorage.get("stationSpeedLimits", [])) == 0:
            lan = lang.DIC[self.currentLanguage]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        XMLTTPData = readfile.ReadFile().ParseXMLTTP(fileContent)
        newStations = XMLTTPData["stationSpeedLimits"]
        newSpeeds = XMLTTPData["speedLimits"]

        validMask = (newSpeeds != 0) & ~np.isnan(newSpeeds)
        newStations = newStations[validMask]
        newSpeeds = newSpeeds[validMask]

        lan = lang.DIC[self.currentLanguage]
        sections = self.TTPSections(newStations)
        
        if len(sections) > 0:
            sectionsInfo = []
            for i, section in enumerate(sections):
                sectionsInfo.append(f"{lan['station']} {section['stationStart']:.6f} km - {section['stationEnd']:.6f} km")

            HasLandXML = "stationHorizontal" in self.dataStorage.get("LandXML",{}) and len(self.dataStorage.get("LandXML",{}).get("stationHorizontal")) > 0

            dialog = gui_overlay.TTPSelectSectionDialog(sectionsInfo, HasLandXML, lan, self)
            if dialog.exec():
                selectedSectionIDs, cropToLandXML, loadAll = dialog.getSelectedSection()
            else:
                return
        else:
            selectedSectionIDs = []
            HasLandXML = False
            cropToLandXML = False
            loadAll = True

        stationsRaw = np.array(newStations)
        speedLimitsRaw = np.array(newSpeeds)

        if not loadAll:
            if not selectedSectionIDs:
                return
            tempStations = []
            tempSpeedLimits = []
            for sectionID in sorted(selectedSectionIDs):
                currentSection = sections[sectionID]
                startID = currentSection["startID"]
                endID = currentSection["endID"]+1
                secSt = stationsRaw[startID:endID]
                secSp = speedLimitsRaw[startID:endID]
                # Correct reversed (descending km) sections so that
                # getSpeedLimitAt() post-step semantics give the right limit.
                secSt, secSp = self.correctReversedTTPSection(secSt, secSp)
                tempStations.append(secSt)
                tempSpeedLimits.append(secSp)
            stationsRaw = np.concatenate(tempStations)
            speedLimitsRaw = np.concatenate(tempSpeedLimits)

            # Sort by station so the step plot is always monotonically increasing
            sortIdx = np.argsort(stationsRaw, kind='stable')
            stationsRaw    = stationsRaw[sortIdx]
            speedLimitsRaw = speedLimitsRaw[sortIdx]

        else:
            # loadAll=True — correct any reversed sections in the raw data.
            allSections = self.TTPSections(stationsRaw)
            tempStations = []
            tempSpeedLimits = []
            for section in allSections:
                secSt = stationsRaw[section["startID"]:section["endID"] + 1]
                secSp = speedLimitsRaw[section["startID"]:section["endID"] + 1]
                secSt, secSp = self.correctReversedTTPSection(secSt, secSp)
                tempStations.append(secSt)
                tempSpeedLimits.append(secSp)
            stationsRaw = np.concatenate(tempStations)
            speedLimitsRaw = np.concatenate(tempSpeedLimits)
            sortIdx = np.argsort(stationsRaw, kind='stable')
            stationsRaw    = stationsRaw[sortIdx]
            speedLimitsRaw = speedLimitsRaw[sortIdx]

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

        oldText = self.textboxRawTTP.toPlainText()
        self.textboxRawTTP.setXmlText(oldText + "\n\n<!-- MERGED XML TTP -->\n\n" + fileContent)

        oldStations = self.dataStorage["stationSpeedLimits"]
        oldSpeeds = self.dataStorage["speedLimits"]

        oldStart = np.nanmin(oldStations)
        oldEnd = np.nanmax(oldStations)
        newStart = np.nanmin(stationsRaw)
        newEnd = np.nanmax(stationsRaw)

        # Kontrola mezery (ve staničení TTP používáme [km], proto 0.1 je 100 m)
        if newStart >= oldEnd or (abs(newStart - oldEnd) <= abs(newEnd - oldStart)):
            isAppend = True
            cropStation = oldEnd
            if abs(newStart - oldEnd) > 0.1:
                QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))
        else:
            isAppend = False
            cropStation = oldStart
            if abs(oldStart - newEnd) > 0.1:
                QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))

        if isAppend:
            mask = stationsRaw > cropStation
            mergedStations = np.concatenate((oldStations, stationsRaw[mask]))
            mergedSpeeds = np.concatenate((oldSpeeds, speedLimitsRaw[mask]))
        else:
            mask = stationsRaw < cropStation
            mergedStations = np.concatenate((stationsRaw[mask], oldStations))
            mergedSpeeds = np.concatenate((speedLimitsRaw[mask], oldSpeeds))

        self.dataStorage["stationSpeedLimits"] = mergedStations
        self.dataStorage["speedLimits"] = mergedSpeeds

        TTPData = {
            "stationSpeedLimits": mergedStations,
            "speedLimits": mergedSpeeds
        }
        self.tableTTP.setData(TTPData)
        
        self.cleanCalculatedSpeeds()
        self.plotSpeedLimits()
        self.updateMapWithSpeeds()

    def appendLandXML(self):
        if "LandXML" not in self.dataStorage or len(self.dataStorage.get("LandXML", {}).get("stationHorizontal", [])) == 0:
            lan = lang.DIC[self.currentLanguage]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        fileContent = self.getFileContent()
        if not fileContent:
            return
        self.appendLandXMLContent(fileContent)

    def appendLandXMLContent(self, fileContent):
        if "LandXML" not in self.dataStorage or len(self.dataStorage.get("LandXML", {}).get("stationHorizontal", [])) == 0:
            lan = lang.DIC[self.currentLanguage]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan.get("no_data", "No data available. Calculate values first."))
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()
            return

        alignments = readfile.ReadFile().GetAlignments(fileContent)
        selectedIdx = 0
        if len(alignments) > 1:
            lan = lang.DIC[self.currentLanguage]
            dialog = gui_overlay.AlignmentSelectDialog(alignments, lan, self)
            if dialog.exec():
                selectedIdx = dialog.getSelectedIndex()
            else:
                return

        newLandXMLData = readfile.ReadFile().ParseLandXML(fileContent, self.epsgInput, selectedIdx)
        
        oldText = self.textboxRawLandXML.toPlainText()
        self.textboxRawLandXML.setXmlText(oldText + "\n\n<!-- MERGED XML -->\n\n" + fileContent)

        self.mergeLandXMLData(newLandXMLData)

    def mergeLandXMLData(self, newData):
        oldData = self.dataStorage.get("LandXML", {})
        
        if len(newData.get("stationHorizontal", [])) == 0:
            return
            
        oldStart = np.nanmin(oldData["stationHorizontal"])
        oldEnd = np.nanmax(oldData["stationHorizontal"])
        newStart = np.nanmin(newData["stationHorizontal"])
        newEnd = np.nanmax(newData["stationHorizontal"])

        lan = lang.DIC[self.currentLanguage]

        if newStart >= oldEnd or (abs(newStart - oldEnd) <= abs(newEnd - oldStart)):
            isAppend = True
            cropStation = oldEnd
            if "keyX" in oldData and "keyY" in oldData and "keyX" in newData and "keyY" in newData:
                if len(oldData["keyX"]) > 0 and len(newData["keyX"]) > 0:
                    oldLastX, oldLastY = oldData["keyX"][-1], oldData["keyY"][-1]
                    newFirstX, newFirstY = newData["keyX"][0], newData["keyY"][0]
                    dist = np.sqrt((newFirstX - oldLastX)**2 + (newFirstY - oldLastY)**2)
                    if dist > 100:
                        QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))
        else:
            isAppend = False
            cropStation = oldStart
            if "keyX" in oldData and "keyY" in oldData and "keyX" in newData and "keyY" in newData:
                if len(oldData["keyX"]) > 0 and len(newData["keyX"]) > 0:
                    oldFirstX, oldFirstY = oldData["keyX"][0], oldData["keyY"][0]
                    newLastX, newLastY = newData["keyX"][-1], newData["keyY"][-1]
                    dist = np.sqrt((newLastX - oldFirstX)**2 + (newLastY - oldFirstY)**2)
                    if dist > 100:
                        QMessageBox.warning(self, lan.get("merge_gap_warning_title", "Warning"), lan.get("merge_gap_warning_desc", "Gap > 100m"))

        stationMap = {
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

        def mergeArrays(key):
            if key not in oldData or key not in newData:
                return oldData.get(key, newData.get(key, []))
            
            oldArr = oldData[key]
            newArr = newData[key]

            if key == "denseAlignment":
                if isAppend:
                    newArrCropped = [p for p in newArr if p[0] > cropStation]
                    return oldArr + newArrCropped
                else:
                    newArrCropped = [p for p in newArr if p[0] < cropStation]
                    return newArrCropped + oldArr

            if key in ["keyStations", "keyTypes", "keyX", "keyY", "keyLat", "keyLon"]:
                newStations = np.array(newData["keyStations"])
                mask = newStations > cropStation if isAppend else newStations < cropStation
            elif key in stationMap:
                sKey = stationMap[key]
                newStations = np.array(newData[sKey])
                
                if sKey == "stationHorizontal":
                    mask = np.zeros(len(newStations), dtype=bool)
                    # Zpracování polí definovaných v párech (počátek-konec segmentu)
                    for i in range(0, len(newStations), 2):
                        if isAppend: keep = newStations[i+1] > cropStation
                        else: keep = newStations[i] < cropStation
                        mask[i] = keep
                        if i+1 < len(newStations): mask[i+1] = keep
                            
                    if key == "stationHorizontal":
                        if isinstance(newArr, np.ndarray): newArr = np.copy(newArr)
                        else: newArr = list(newArr)
                            
                        for i in range(0, len(newStations), 2):
                            if mask[i]:
                                if isAppend and newArr[i] < cropStation: newArr[i] = cropStation
                                elif not isAppend and (i+1) < len(newArr) and newArr[i+1] > cropStation: newArr[i+1] = cropStation
                else:
                    mask = newStations > cropStation if isAppend else newStations < cropStation
            elif key in ["alignmentCoordinates", "alignmentCoordsOriginal"]:
                if isAppend: return oldArr + newArr
                else: return newArr + oldArr
            else:
                if isinstance(oldArr, np.ndarray) and isinstance(newArr, np.ndarray):
                    if isAppend: return np.concatenate((oldArr, newArr))
                    else: return np.concatenate((newArr, oldArr))
                elif isinstance(oldArr, list) and isinstance(newArr, list):
                    if isAppend: return oldArr + newArr
                    else: return newArr + oldArr
                return oldArr

            if isinstance(newArr, np.ndarray):
                newArrCropped = newArr[mask]
                if isAppend:
                    return np.concatenate((oldArr, newArrCropped))
                else:
                    return np.concatenate((newArrCropped, oldArr))
            elif isinstance(newArr, list):
                newArrCropped = [item for i, item in enumerate(newArr) if mask[i]]
                if isAppend:
                    return oldArr + newArrCropped
                else:
                    return newArrCropped + oldArr
            return oldArr

        mergedData = {}
        allKeys = set(list(oldData.keys()) + list(newData.keys()))
        for k in allKeys:
            mergedData[k] = mergeArrays(k)

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

    def parseLandXML(self, fileContent):
        if fileContent is not None:
            self.textboxRawLandXML.setXmlText(fileContent)
            
            # Check for multiple alignments and prompt the user if needed
            alignments = readfile.ReadFile().GetAlignments(fileContent)
            selectedIdx = 0
            if len(alignments) > 1:
                lan = lang.DIC[self.currentLanguage]
                dialog = gui_overlay.AlignmentSelectDialog(alignments, lan, self)
                if dialog.exec():
                    selectedIdx = dialog.getSelectedIndex()
                else:
                    return  # User cancelled the dialog, do nothing

            LandXMLData = readfile.ReadFile().ParseLandXML(fileContent, self.epsgInput, selectedIdx)
            self.updateTableLandXML(LandXMLData)

            # Save data to central data storage
            self.dataStorage["LandXML"] = LandXMLData

            # Plot and draw data
            lxml = self.dataStorage.get("LandXML",{})
            self.plotCant()
            self.plotCurvature()
            self.plotProfile()
            self.mapWidget.drawAlignment(lxml.get("alignmentCoordinates",[]), lxml)

            # Step 1 of the workflow guide is done once LandXML is parsed
            self.workflowWidget.markCompleted(0)
            self.setEngineStatus(lang.DIC[self.currentLanguage].get("dockLandXmlParsed", "LandXML"))

        else:
            lan = lang.DIC[self.currentLanguage]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["no_file"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def parseXMLTTP(self, fileContent):
        if fileContent is not None:
            self.textboxRawTTP.setXmlText(fileContent)
            XMLTTPData = readfile.ReadFile().ParseXMLTTP(fileContent)

            lan = lang.DIC[self.currentLanguage]

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
                    selectedSectionIDs, cropToLandXML, loadAll = dialog.getSelectedSection()
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

                    secSt = stationsRaw[startID:endID]
                    secSp = speedLimitsRaw[startID:endID]
                    # Correct reversed (descending km) sections so that
                    # getSpeedLimitAt() post-step semantics give the right limit.
                    secSt, secSp = self.correctReversedTTPSection(secSt, secSp)
                    tempStations.append(secSt)
                    tempSpeedLimits.append(secSp)

                stationsRaw = np.concatenate(tempStations)
                speedLimitsRaw = np.concatenate(tempSpeedLimits)

                # Sort by station so the step plot is always monotonically increasing.
                # This acts as a safety net for any edge case the section detector may miss
                # (e.g. non-standard TTP layouts or multiple selected sections).
                sortIdx = np.argsort(stationsRaw, kind='stable')
                stationsRaw    = stationsRaw[sortIdx]
                speedLimitsRaw = speedLimitsRaw[sortIdx]

            else:
                # loadAll=True — apply the same reversed-section correction to every
                # monotone section present in the raw data before storing.
                allSections = self.TTPSections(stationsRaw)
                tempStations = []
                tempSpeedLimits = []
                for section in allSections:
                    secSt = stationsRaw[section["startID"]:section["endID"] + 1]
                    secSp = speedLimitsRaw[section["startID"]:section["endID"] + 1]
                    secSt, secSp = self.correctReversedTTPSection(secSt, secSp)
                    tempStations.append(secSt)
                    tempSpeedLimits.append(secSp)
                stationsRaw = np.concatenate(tempStations)
                speedLimitsRaw = np.concatenate(tempSpeedLimits)
                sortIdx = np.argsort(stationsRaw, kind='stable')
                stationsRaw    = stationsRaw[sortIdx]
                speedLimitsRaw = speedLimitsRaw[sortIdx]

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
            self.updateMapWithSpeeds()
        else:
            lan = lang.DIC[self.currentLanguage]
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
    #         lan = lang.DIC[self.currentLanguage]
    #         msg = QMessageBox()
    #         msg.setWindowTitle(lan.get("importStopsTTP", "Import Stops"))
    #         msg.setText(f"Imported {len(stations)} stops.")
    #         msg.setIcon(QMessageBox.Icon.Information)
    #         msg.exec()
    #     else:
    #         lan = lang.DIC[self.currentLanguage]
    #         err = QMessageBox()
    #         err.setWindowTitle(lan["error"])
    #         err.setText(lan["no_file"])
    #         err.setIcon(QMessageBox.Icon.Warning)
    #         err.exec()

    # Redraw the vertical alignment plot from the parsed LandXML data
    def renderProfile(self):
        self.profileWidget.updateProfileData(self.dataStorage.get("LandXML", {}),
                                             self.toggleProfileAction.isChecked())

    # Redraw every kinematics plot from the latest simulation results
    def renderKinematics(self):
        self.kinematicsWidget.updateKinematicsData(
            self.dataStorage,
            self.toggleUnitsAction.isChecked(),
            self.getVehicleName,
            self.seriesVisibility())

    # ------------------------------------------------------------------
    # Pop-up plot windows (right-click context menu on any canvas)
    # ------------------------------------------------------------------

    # Build and display the QMenu with a fixed list of all graphs
    def showGraphContextMenu(self, globalPos):
        lan = lang.DIC[self.currentLanguage]

        graphDefs = [
            ("speed",       lan.get("speed_lim",                   "Speed Limits")),
            ("cant_curv",   f'{lan.get("cant","Cant")} / {lan.get("curvature","Curvature")}'),
            ("profile",     lan.get("profile",                     "Profile")),
            ("tacho_track", lan.get("kinematicsSpeedLimitTrack",   "Speed–Distance")),
            ("tacho_time",  lan.get("kinematicsSpeedLimitTime",    "Speed–Time")),
            ("dist_time",   lan.get("kinematicsDistanceTime",      "Distance–Time")),
            ("forces",      lan.get("kinematicsForces",            "Forces")),
        ]

        menu = QMenu(self)
        menu.addSection(lan.get("openGraphMenu", "Open graph in new window"))
        for graphId, graphName in graphDefs:
            action = menu.addAction(graphName)
            # Default-argument binding prevents loop-variable capture issues
            action.triggered.connect(
                lambda checked=False, gid=graphId: self.openPopupPlot(gid)
            )
        menu.exec(globalPos)

    # Collect data from dataStorage and open a PopupPlotWindow for the given graph
    def openPopupPlot(self, graphId):
        lan  = lang.DIC[self.currentLanguage]
        lxml = self.dataStorage.get("LandXML", {})

        # Unit factors (shared with plotKinematics)
        useKmh   = self.toggleUnitsAction.isChecked()
        vFactor  = 3.6    if useKmh else 1.0
        dFactor  = 1000.0 if useKmh else 1.0
        tFactor  = 60.0   if useKmh else 1.0
        spdLbl   = lan.get("speedKmh",    "Speed [km/h]")  if useKmh else lan.get("speedM",    "Speed [m/s]")
        splimLbl = lan.get("speedLimKmh", "Speed Limit [km/h]") if useKmh else lan.get("speedLimM", "Speed Limit [m/s]")
        distLbl  = lan.get("distanceKm",  "Distance [km]") if useKmh else lan.get("distance",   "Distance [m]")
        timeLbl  = lan.get("timeMin",     "Time [min]")    if useKmh else lan.get("time",        "Time [s]")

        numVehicles    = self.dataStorage.get("num_vehicles", 1)
        colorsSpeed    = ['tab:red',   'tab:green',  'tab:blue']
        colorsTrac     = ['green',    'lime',       'darkgreen']
        colorsBrake    = ['red',      'darkred',    'salmon']
        colorsRes      = ['orange',   'darkorange', 'gold']
        limitColors    = ['lightcoral','lightgreen','lightskyblue']

        def vehicleLabel(vIdx):
            if numVehicles <= 1:
                return ""
            vname = self.getVehicleName(vIdx)
            return f" {vname}" if vname else f" V{vIdx+1}"

        # ---- helper: build stop-expanded time/speed/station arrays ----------
        # Insert arrival points with zero speed for dwell stops
        def expandStops(vIdx, baseTimes, baseValues):
            dwells = self.dataStorage.get(f"kinematicsDwellTimesS_{vIdx}")
            if dwells is None:
                return np.array(baseTimes), np.array(baseValues)
            tList = list(baseTimes)
            vList = list(baseValues)
            stopIdx = np.where(dwells > 0)[0]
            offset = 0
            for idx in stopIdx:
                ai = idx + offset
                arrival = tList[ai] - dwells[idx]
                tList.insert(ai, arrival)
                vList.insert(ai, 0.0)
                offset += 1
            return np.array(tList), np.array(vList)

        # Same as above but preserves the station value for the distance-time plot
        def expandStopsStation(vIdx, baseTimes, baseStations):
            dwells = self.dataStorage.get(f"kinematicsDwellTimesS_{vIdx}")
            if dwells is None:
                return np.array(baseTimes), np.array(baseStations)
            tList = list(baseTimes)
            sList = list(baseStations)
            stopIdx = np.where(dwells > 0)[0]
            offset = 0
            for idx in stopIdx:
                ai = idx + offset
                arrival = tList[ai] - dwells[idx]
                tList.insert(ai, arrival)
                sList.insert(ai, sList[ai])
                offset += 1
            return np.array(tList), np.array(sList)

        # ==================================================================
        if graphId == "speed":
            title   = lan.get("speed_lim", "Speed Limits")
            primary = []
            pairs = [
                ("stationSpeedLimits", "speedLimits",   lan.get("speed_lim"),       'black'),
                ("stationSpeed100",    "speedLimits100", lan.get("speed_lim_100"),   'red'),
                ("stationSpeed130",    "speedLimits130", lan.get("speed_lim_130"),   'teal'),
                ("stationSpeed150",    "speedLimits150", lan.get("speed_lim_150"),   'darkorchid'),
                ("stationSpeedK",      "speedLimitsK",   lan.get("speed_lim_K"),     'cornflowerblue'),
            ]
            for sk, vk, lbl, col in pairs:
                st = self.dataStorage.get(sk)
                sp = self.dataStorage.get(vk)
                if st is not None and sp is not None and len(st) > 0 and len(sp) > 0:
                    primary.append(dict(x=st, y=sp, label=lbl, color=col,
                                        step=True, marker='s'))
            win = gui_overlay.PopupPlotWindow(title, self, lan)
            win.drawData(primary,
                          xlabel=lan.get("station","Station [km]"),
                          ylabel=lan.get("speed_lim","Speed Limits"),
                          title=title)

        # ------------------------------------------------------------------
        elif graphId == "cant_curv":
            title   = f'{lan.get("cant","Cant")} / {lan.get("curvature","Curvature")}'
            primary = []
            secondary = []

            cantSeries = [
                ("stationCant",         "cant",       lan.get("cant"),         'black'),
                ("stationCantPossible", "cantPossible",lan.get("cant_possible"),'green'),
                ("stationCantPossible", "cDef100",    lan.get("cdef_100"),     'red'),
                ("stationCantPossible", "cDef130",    lan.get("cdef_130"),     'teal'),
                ("stationCantPossible", "cDef150",    lan.get("cdef_150"),     'darkorchid'),
                ("stationCantPossible", "cDefK",      lan.get("cdef_K"),       'cornflowerblue'),
                ("stationCantPossible", "cantDef100", lan.get("cant_def_100"), 'tomato'),
                ("stationCantPossible", "cantDef130", lan.get("cant_def_130"), 'aqua'),
                ("stationCantPossible", "cantDef150", lan.get("cant_def_150"), 'mediumorchid'),
                ("stationCantPossible", "cantDefK",   lan.get("cant_def_K"),   'royalblue'),
            ]
            for sk, dk, lbl, col in cantSeries:
                x = lxml.get(sk)
                y = lxml.get(dk)
                if x is not None and y is not None and len(x) > 0 and len(y) > 0:
                    primary.append(dict(x=x, y=y, label=lbl, color=col,
                                        linestyle='-', marker='o'))

            for sk, ck, lbl, col in [
                ("stationHorizontal",    "curvature",    lan.get("curvature"),     'tab:gray'),
                ("stationHorizontalNew", "curvatureNew", lan.get("curvature_new"), 'tab:orange'),
            ]:
                x = lxml.get(sk)
                y = lxml.get(ck)
                if x is not None and y is not None and len(x) > 0 and len(y) > 0:
                    secondary.append(dict(x=x, y=y, label=lbl, color=col,
                                          linestyle='-', marker='o'))

            def fracFmt(x, pos=None):
                if np.isclose(x, 0, atol=1e-6):
                    return "0"
                sign = "-" if x < 0 else ""
                return f"{sign}1/{abs(int(round(1/x)))}"

            win = gui_overlay.PopupPlotWindow(title, self, lan)
            win.drawData(
                primary,
                xlabel=lan.get("station","Station [km]"),
                ylabel=lan.get("cant","Cant [mm]"),
                title=title,
                secondarySeries=secondary or None,
                secondaryYlabel=lan.get("curvature","Curvature [1/m]"),
                secondaryFormatter=fracFmt,
                symmetricYlim=True,
            )

        # ------------------------------------------------------------------
        elif graphId == "profile":
            title   = lan.get("profile", "Profile")
            primary = []
            annotations = []
            stV = lxml.get("stationVertical")
            elev = lxml.get("elevation")
            slp  = lxml.get("slope")
            if stV is not None and elev is not None and len(stV) > 0:
                primary.append(dict(x=stV, y=elev,
                                    label=lan.get("profile","Profile"),
                                    color='tab:gray', linestyle='-', marker='o'))
                if slp is not None and len(slp) > 0:
                    midX = (stV[:-1] + stV[1:]) / 2
                    midZ = (elev[:-1] + elev[1:]) / 2
                    for i in range(len(midX)):
                        annotations.append(dict(x=midX[i], y=float(midZ[i]) + 0.1,
                                                 text=f"{slp[i]:.2f} ‰", fontsize=6))
            win = gui_overlay.PopupPlotWindow(title, self, lan)
            win.drawData(primary,
                          xlabel=lan.get("station","Station [km]"),
                          ylabel=lan.get("elevation","Elevation [m]"),
                          title=title,
                          textAnnotations=annotations)

        # ------------------------------------------------------------------
        elif graphId == "tacho_track":
            title   = lan.get("kinematicsSpeedLimitTrack", "Speed–Distance")
            primary = []
            vehiclesSettTt = self.dataStorage.get("settingsData", {}).get("vehicles", [])
            for vIdx in range(numVehicles):
                stLim = self.dataStorage.get(f"stationSpeedLimitM_{vIdx}")
                spLim = self.dataStorage.get(f"speedLimitsM_{vIdx}")
                stKin = self.dataStorage.get(f"kinematicsStationM_{vIdx}")
                spKin = self.dataStorage.get(f"kinematicsSpeedM_{vIdx}")
                if stLim is not None and spLim is not None and len(stLim) > 0:
                    # Same ascending-sort fix as plotKinematics tacho_track
                    isRevTt = (vIdx < len(vehiclesSettTt) and
                                 vehiclesSettTt[vIdx].get("runReversed", False))
                    if isRevTt and len(stLim) > 1:
                        si = np.argsort(stLim)
                        stLimP = stLim[si]
                        spLimP = spLim[si]
                    else:
                        stLimP, spLimP = stLim, spLim
                    primary.append(dict(x=stLimP/dFactor, y=spLimP*vFactor,
                                        label=splimLbl+vehicleLabel(vIdx),
                                        color=limitColors[vIdx], step=True, marker='s',
                                        linestyle='--', alpha=0.7))
                if stKin is not None and spKin is not None and len(stKin) > 0:
                    primary.append(dict(x=stKin/dFactor, y=spKin*vFactor,
                                        label=spdLbl+vehicleLabel(vIdx),
                                        color=colorsSpeed[vIdx]))
            # Stop markers – vertical line at each station position
            axlines = []
            trainStops = self.dataStorage.get("settingsData", {}).get("trainStops", [])
            for stop in trainStops:
                try:
                    sM  = float(stop[0]) * 1000.0
                    name = str(stop[2]) if len(stop) > 2 else ""
                except (IndexError, ValueError):
                    continue
                al = dict(axis="x", pos=sM/dFactor,
                          color="gray", linestyle="--", alpha=0.7)
                if name:
                    al.update(label_text=f" {name}", label_rotation=90,
                              label_va="bottom", label_color="black",
                              label_fontsize=8, label_alpha=0.7, label_y=0)
                axlines.append(al)
            win = gui_overlay.PopupPlotWindow(title, self, lan)
            win.drawData(primary, xlabel=distLbl, ylabel=splimLbl,
                          title=title, axlines=axlines or None)

        # ------------------------------------------------------------------
        elif graphId == "tacho_time":
            title   = lan.get("kinematicsSpeedLimitTime", "Speed–Time")
            primary = []
            for vIdx in range(numVehicles):
                spLimT = self.dataStorage.get(f"speedLimitsT_{vIdx}")
                spLim   = self.dataStorage.get(f"speedLimitsM_{vIdx}")
                kinT    = self.dataStorage.get(f"kinematicsTimeS_{vIdx}")
                kinSp   = self.dataStorage.get(f"kinematicsSpeedM_{vIdx}")
                if spLimT is not None and spLim is not None and len(spLimT) > 0:
                    primary.append(dict(x=spLimT/tFactor, y=spLim*vFactor,
                                        label=splimLbl+vehicleLabel(vIdx),
                                        color=limitColors[vIdx], step=True, marker='s',
                                        linestyle='--', alpha=0.7))
                if kinT is not None and kinSp is not None and len(kinT) > 0:
                    pt, pv = expandStops(vIdx, kinT, kinSp)
                    primary.append(dict(x=pt/tFactor, y=pv*vFactor,
                                        label=spdLbl+vehicleLabel(vIdx),
                                        color=colorsSpeed[vIdx]))
            # Stop markers – vertical line at interpolated arrival time per vehicle
            axlines = []
            trainStops    = self.dataStorage.get("settingsData", {}).get("trainStops", [])
            vehiclesSett = self.dataStorage.get("settingsData", {}).get("vehicles", [])
            for stop in trainStops:
                try:
                    sM  = float(stop[0]) * 1000.0
                    name = str(stop[2]) if len(stop) > 2 else ""
                except (IndexError, ValueError):
                    continue
                for vIdx in range(numVehicles):
                    kinSt = self.dataStorage.get(f"kinematicsStationM_{vIdx}")
                    kinT2 = self.dataStorage.get(f"kinematicsTimeS_{vIdx}")
                    isRev = (vehiclesSett[vIdx].get("runReversed", False)
                              if vIdx < len(vehiclesSett) else False)
                    if kinSt is None or kinT2 is None or len(kinSt) == 0:
                        continue
                    xp, fp = kinSt, kinT2
                    if isRev:
                        xp, fp = kinSt[::-1], kinT2[::-1]
                    stopTime = np.interp(sM, xp, fp)
                    al = dict(axis="x", pos=stopTime/tFactor,
                              color=limitColors[vIdx], linestyle=":", alpha=0.5)
                    if name:
                        al.update(label_text=f" {name} (V{vIdx+1})",
                                  label_rotation=90, label_va="bottom",
                                  label_color=limitColors[vIdx],
                                  label_fontsize=7, label_alpha=0.7, label_y=0)
                    axlines.append(al)
            win = gui_overlay.PopupPlotWindow(title, self, lan)
            win.drawData(primary, xlabel=timeLbl, ylabel=splimLbl,
                          title=title, axlines=axlines or None)

        # ------------------------------------------------------------------
        elif graphId == "dist_time":
            title   = lan.get("kinematicsDistanceTime", "Distance–Time")
            primary = []
            for vIdx in range(numVehicles):
                spLimT = self.dataStorage.get(f"speedLimitsT_{vIdx}")
                stLim   = self.dataStorage.get(f"stationSpeedLimitM_{vIdx}")
                kinT    = self.dataStorage.get(f"kinematicsTimeS_{vIdx}")
                kinSt   = self.dataStorage.get(f"kinematicsStationM_{vIdx}")
                if spLimT is not None and stLim is not None and len(spLimT) > 0:
                    primary.append(dict(x=spLimT/tFactor, y=stLim/dFactor,
                                        label=splimLbl+vehicleLabel(vIdx),
                                        color=limitColors[vIdx], marker='s',
                                        linestyle='--', alpha=0.7))
                if kinT is not None and kinSt is not None and len(kinT) > 0:
                    pt, ps = expandStopsStation(vIdx, kinT, kinSt)
                    primary.append(dict(x=pt/tFactor, y=ps/dFactor,
                                        label=distLbl+vehicleLabel(vIdx),
                                        color=colorsSpeed[vIdx]))
            # Stop markers – horizontal line at each station position
            axlines = []
            trainStops = self.dataStorage.get("settingsData", {}).get("trainStops", [])
            for stop in trainStops:
                try:
                    sM  = float(stop[0]) * 1000.0
                    name = str(stop[2]) if len(stop) > 2 else ""
                except (IndexError, ValueError):
                    continue
                al = dict(axis="y", pos=sM/dFactor,
                          color="gray", linestyle="--", alpha=0.7)
                if name:
                    al.update(label_text=f" {name}", label_va="bottom",
                              label_color="black", label_fontsize=8,
                              label_alpha=0.7, label_x=0)
                axlines.append(al)
            win = gui_overlay.PopupPlotWindow(title, self, lan)
            win.drawData(primary, xlabel=timeLbl, ylabel=distLbl,
                          title=title, axlines=axlines or None)

        # ------------------------------------------------------------------
        elif graphId == "forces":
            title   = lan.get("kinematicsForces", "Forces Profile")
            primary = []
            for vIdx in range(numVehicles):
                kinSt = self.dataStorage.get(f"kinematicsStationM_{vIdx}")
                fTrac = self.dataStorage.get(f"kinematicsForceTractionKN_{vIdx}")
                fBrk  = self.dataStorage.get(f"kinematicsForceBrakingKN_{vIdx}")
                fRes  = self.dataStorage.get(f"kinematicsForceResistanceKN_{vIdx}")
                if kinSt is None or len(kinSt) == 0:
                    continue
                x = kinSt / dFactor
                for arr, col, lblKey in [
                    (fTrac, colorsTrac[vIdx],  "forceTraction"),
                    (fBrk,  colorsBrake[vIdx], "forceBraking"),
                    (fRes,  colorsRes[vIdx],   "forceResistance"),
                ]:
                    if arr is not None and len(arr) > 0:
                        primary.append(dict(x=x, y=arr,
                                            label=lan.get(lblKey, lblKey)+vehicleLabel(vIdx),
                                            color=col))
            win = gui_overlay.PopupPlotWindow(title, self, lan)
            win.drawData(primary,
                          xlabel=distLbl,
                          ylabel=lan.get("forceKN", "Force [kN]"),
                          title=title)

        else:
            return  # unknown id — do nothing

        # Adopt the active theme so the popup does not open with default colours
        win.applyTheme(self.themeManager.isDarkActive, self.themeManager.currentTokens)

        # Show window and keep reference alive so Qt doesn't GC it
        win.show()
        self.popupWindows.append(win)

    def cleanData(self):
        self.cleanLandXMLData()
        self.cleanTTPData()
        self.cleanCalculatedCants()
        self.cleanCalculatedSpeeds()

        keep = ["settingsData",]

        for key in list(self.dataStorage.keys()):
            if key not in keep:
                del self.dataStorage[key]

        # Reset the workflow guide and every plot along with the data
        self.workflowWidget.resetAll()
        self.graphsWidget.clearAll()
        self.profileWidget.clearAll()
        self.kinematicsWidget.clearAll()
        self.setEngineStatus(lang.DIC[self.currentLanguage].get("statusNoData", "No data"))
        self.updateStatusChainage(None)

    def cleanTTPData(self):
        self.textboxRawTTP.setXmlText("")
        self.tableTTP.setData({})
        self.dataStorage["stationSpeedLimits"] = []
        self.dataStorage["speedLimits"] = []
        self.plotSpeedLimits()
        self.plotKinematics()

    def cleanLandXMLData(self):
        self.textboxRawLandXML.setXmlText("")
        self.tableLandXML.setData({})
        self.dataStorage["LandXML"] = {}
        self.plotCant()
        self.plotCurvature()
        self.plotProfile()

    def cleanCalculatedCants(self):
        lxml = self.dataStorage.setdefault("LandXML", {})

        # Cant and cant-deficiency arrays
        for key in ["stationCantPossible", "cantPossible",
                    "cDef100", "cDef130", "cDef150", "cDefK",
                    "cantDef100", "cantDef130", "cantDef150", "cantDefK"]:
            lxml[key] = []

        # Rate-of-change arrays written by the geometry engine
        # (note: suffix is "100/130/150/K", no leading "I")
        for suffix in ["100", "130", "150", "K"]:
            lxml[f"dDdt{suffix}"] = []
            lxml[f"dIdt{suffix}"] = []

        # Utilisation and limit-reached flags (profile names: I100/I130/I150/K)
        for profile in ["I100", "I130", "I150", "K"]:
            lxml[f"util_D_{profile}"]        = []
            lxml[f"util_I_{profile}"]        = []
            lxml[f"limitReachedD_{profile}"] = []
            lxml[f"limitReachedI_{profile}"] = []

        self.reportGeometryWidget.setPlainText("")
        self.plotCant()
        self.plotSpeedLimits()

    def cleanCalculatedSpeeds(self):
        # Geometry-derived speed profiles (all four speed classes)
        for suffix in ["100", "130", "150", "K"]:
            self.dataStorage[f"stationSpeed{suffix}"] = []
            self.dataStorage[f"speedLimits{suffix}"]  = []

        # Per-vehicle kinematics and speed-limit arrays
        for vIdx in range(3):
            self.dataStorage[f"kinematicsStationM_{vIdx}"]        = []
            self.dataStorage[f"kinematicsSpeedM_{vIdx}"]          = []
            self.dataStorage[f"kinematicsTimeS_{vIdx}"]           = []
            self.dataStorage[f"kinematicsAcceleration_{vIdx}"]    = []
            self.dataStorage[f"kinematicsForceTractionKN_{vIdx}"] = []
            self.dataStorage[f"kinematicsForceBrakingKN_{vIdx}"]  = []
            self.dataStorage[f"kinematicsForceResistanceKN_{vIdx}"] = []
            self.dataStorage[f"kinematicsDwellTimesS_{vIdx}"]     = []
            self.dataStorage[f"stationSpeedLimitM_{vIdx}"]        = []
            self.dataStorage[f"speedLimitsM_{vIdx}"]              = []
            self.dataStorage[f"speedLimitsT_{vIdx}"]              = []
            # Warning flag — remove entirely so downstream code gets None / missing key
            self.dataStorage.pop(f"kinematicsWarning_{vIdx}", None)

        self.reportVehicleTable.setData({})
        self.plotSpeedLimits()
        self.plotKinematics()

    # Set visibility
    def toggleCantVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cant", isChecked)

    def toggleCantPossibleVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cantPossible", isChecked)

    def toggleCDef100Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cDef100", isChecked)

    def toggleCDef130Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cDef130", isChecked)

    def toggleCDef150Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cDef150", isChecked)

    def toggleCDefKVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cDefK", isChecked)

    def toggleCantDef100Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cantDef100", isChecked)

    def toggleCantDef130Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cantDef130", isChecked)

    def toggleCantDef150Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cantDef150", isChecked)

    def toggleCantDefKVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "cantDefK", isChecked)

    def toggleCurvatureVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "curvature", isChecked)

    def toggleCurvatureNewVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("geometry", "curvatureNew", isChecked)

    def toggleSpeedVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("speed", "speedLimits", isChecked)

    def toggleSpeed100Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("speed", "speedLimits100", isChecked)

    def toggleSpeed130Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("speed", "speedLimits130", isChecked)

    def toggleSpeed150Visibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("speed", "speedLimits150", isChecked)

    def toggleSpeedKVisibility(self, isChecked):
        self.graphsWidget.setSeriesVisible("speed", "speedLimitsK", isChecked)

    def toggleProfileVisibility(self, isChecked):
        self.profileWidget.setProfileVisible(isChecked)

    def toggleKinematicsSpeedLimitTrackVisibility(self, isChecked):
        self.kinematicsWidget.setPlotVisible("tachoTrack", isChecked)

    def toggleKinematicsSpeedLimitTimeVisibility(self, isChecked):
        self.kinematicsWidget.setPlotVisible("tachoTime", isChecked)

    def toggleKinematicsDistanceTimeVisibility(self, isChecked):
        self.kinematicsWidget.setPlotVisible("distTime", isChecked)

    def toggleKinematicsForcesVisibility(self, isChecked):
        self.kinematicsWidget.setPlotVisible("forces", isChecked)

    # Map settings
    def openMapSettings(self):
        lan = lang.DIC[self.currentLanguage]
        dialog = gui_overlay.MapSettingsDialog(self.epsgInput, self.mapWidget.currentBaseMap, self.mapWidget.drawMode, self.mapWidget.speedProfile, lan, self)
        if dialog.exec():
            self.epsgInput, selectedMap, drawMode, speedProfile = dialog.getMapSettings()
            self.mapWidget.setBaseMap(selectedMap)
            self.mapWidget.setDrawOptions(drawMode, speedProfile)

    # Geometry settings
    def openGeometrySettings(self):
        lan = lang.DIC[self.currentLanguage]

        dialog = gui_overlay.GeometrySettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())

    # Vehicle settings
    def openVehicleSettings(self):
        lan = lang.DIC[self.currentLanguage]

        dialog = gui_overlay.VehicleSettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())
            # Step 4 of the workflow guide covers the vehicle definition
            self.workflowWidget.markCompleted(3)

    # Stops settings
    def openStopsSettings(self):
        lan = lang.DIC[self.currentLanguage]
        dialog = gui_overlay.StopsSettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())
            # Step 3 of the workflow guide covers the scheduled stops
            self.workflowWidget.markCompleted(2)
            # New stops must reach the map and both station aware plots
            self.refreshStations()
            self.plotKinematics()

    # Speed settings
    def openSpeedSettings(self):
        lan = lang.DIC[self.currentLanguage]
        dialog = gui_overlay.SpeedSettingsDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"].update(dialog.getSettings())

    # Design approach settings
    def openDesignApproach(self):
        lan = lang.DIC[self.currentLanguage]

        dialog = gui_overlay.DesignApproachDialog(self.dataStorage.get("settingsData", {}), lan, self)
        if dialog.exec():
            self.dataStorage["settingsData"]["designApproach"] = dialog.getDesignApproach()

    # Help, reveals the documentation dock instead of opening a modal dialog
    def openHelp(self):
        self.dockHelp.show()
        self.dockHelp.raise_()
        self.helpWidget.reloadDocument()

    # Reports
    def generateGeometryReport(self):
        lan = lang.DIC[self.currentLanguage]
        lxml = self.dataStorage.get("LandXML", {})
        if not lxml or "stationCantPossible" not in lxml or len(lxml.get("stationCantPossible", [])) < 2:
            self.reportGeometryWidget.setPlainText(lan.get("no_data", "No data available. Calculate values first."))
            self.showReportView()
            return

        stations = lxml["stationCantPossible"]
        geomType = lxml.get("geometryType", [])

        # Localised element-type names used in report headers
        elemTypeNames = {
            "Curve":  lan.get("elemCurve",  "Curve"),
            "Spiral": lan.get("elemSpiral", "Spiral"),
            "Line":   lan.get("elemLine",   "Line"),
        }
        utilDLbl = lan.get("utilD", "Util D")
        utilILbl = lan.get("utilI", "Util I")
        
        if len(geomType) != len(stations):
            self.reportGeometryWidget.setPlainText(lan.get("error", "Error") + ": Data lengths do not match. Please recalculate.")
            self.showReportView()
            return

        def safeGet(d, key, fallback):
            val = d.get(key)
            if val is None or len(val) != len(stations):
                return fallback
            return val

        cant = safeGet(lxml, "cantPossible", np.zeros_like(stations))
        cDef100 = safeGet(lxml, "cDef100", np.zeros_like(stations))
        cDef130 = safeGet(lxml, "cDef130", np.zeros_like(stations))
        cDef150 = safeGet(lxml, "cDef150", np.zeros_like(stations))
        cDefK = safeGet(lxml, "cDefK", np.zeros_like(stations))

        v100 = safeGet(self.dataStorage, "speedLimits100", np.zeros_like(stations))
        v130 = safeGet(self.dataStorage, "speedLimits130", np.zeros_like(stations))
        v150 = safeGet(self.dataStorage, "speedLimits150", np.zeros_like(stations))
        vK = safeGet(self.dataStorage, "speedLimitsK", np.zeros_like(stations))

        dDdt100 = safeGet(lxml, "dDdt100", np.zeros_like(stations))
        dIdt100 = safeGet(lxml, "dIdt100", np.zeros_like(stations))
        dDdt130 = safeGet(lxml, "dDdt130", np.zeros_like(stations))
        dIdt130 = safeGet(lxml, "dIdt130", np.zeros_like(stations))
        dDdt150 = safeGet(lxml, "dDdt150", np.zeros_like(stations))
        dIdt150 = safeGet(lxml, "dIdt150", np.zeros_like(stations))
        dDdtK = safeGet(lxml, "dDdtK", np.zeros_like(stations))
        dIdtK = safeGet(lxml, "dIdtK", np.zeros_like(stations))

        limD100 = safeGet(lxml, "limitReachedD_I100", np.zeros(len(stations), dtype=bool))
        limI100 = safeGet(lxml, "limitReachedI_I100", np.zeros(len(stations), dtype=bool))
        limD130 = safeGet(lxml, "limitReachedD_I130", np.zeros(len(stations), dtype=bool))
        limI130 = safeGet(lxml, "limitReachedI_I130", np.zeros(len(stations), dtype=bool))
        limD150 = safeGet(lxml, "limitReachedD_I150", np.zeros(len(stations), dtype=bool))
        limI150 = safeGet(lxml, "limitReachedI_I150", np.zeros(len(stations), dtype=bool))
        limDK = safeGet(lxml, "limitReachedD_K", np.zeros(len(stations), dtype=bool))
        limIK = safeGet(lxml, "limitReachedI_K", np.zeros(len(stations), dtype=bool))
        
        radius = safeGet(lxml, "radius", np.full(len(stations), np.inf))
        curvature = safeGet(lxml, "curvature", np.zeros_like(stations))

        utilD100 = safeGet(lxml, "util_D_I100", np.zeros_like(stations))
        utilI100 = safeGet(lxml, "util_I_I100", np.zeros_like(stations))
        utilD130 = safeGet(lxml, "util_D_I130", np.zeros_like(stations))
        utilI130 = safeGet(lxml, "util_I_I130", np.zeros_like(stations))
        utilD150 = safeGet(lxml, "util_D_I150", np.zeros_like(stations))
        utilI150 = safeGet(lxml, "util_I_I150", np.zeros_like(stations))
        utilDK = safeGet(lxml, "util_D_K", np.zeros_like(stations))
        utilIK = safeGet(lxml, "util_I_K", np.zeros_like(stations))

        reportLines = [lan.get("reportGeometryTitle", "=== Geometry Report ==="), ""]

        def calcN(LM, dVal, v):
            if abs(dVal) < 1e-3 or v < 1e-3: return "INF"
            return f"{LM * 1000 / (abs(dVal) * v):.2f}"
            
        def formatR(rVal):
            if np.isinf(rVal) or np.isnan(rVal): return "INF"
            return f"{rVal:.0f}"

        stats = {
            "V100": {"limit_D": 0, "limit_I": 0},
            "V130": {"limit_D": 0, "limit_I": 0},
            "V150": {"limit_D": 0, "limit_I": 0},
            "VK":   {"limit_D": 0, "limit_I": 0}
        }
        profileStats = {
            "V100": {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0},
            "V130": {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0},
            "V150": {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0},
            "VK":   {"min_n": float('inf'), "min_nI": float('inf'), "min_nI_all": float('inf'), "min_nI_all_dI": 0.0, "max_dd_dt": 0.0, "max_di_dt": 0.0, "max_D": 0.0, "max_I": 0.0, "max_deltaI": 0.0, "weighted_util_sum_D": 0.0, "weighted_util_sum_I": 0.0, "total_length": 0.0}
        }
        totalElements = 0
        
        limitsDI = self.dataStorage.get("settingsData", {}).get("dI", [])
        approach = self.dataStorage.get("settingsData", {}).get("designApproach", "standard")
        currAppDI = approach.get("dI", "standard") if isinstance(approach, dict) else approach
        colDI = {"standard": 2, "limit": 3, "minmax": 4}.get(currAppDI, 3)

        def getDeficiencyLimit(v):
            for row in limitsDI:
                if row[0] < v <= row[1]: return row[colDI]
            return limitsDI[-1][colDI] if limitsDI else 0

        for i in range(len(stations) - 1):
            L = (stations[i+1] - stations[i]) * 1000

            profiles = [
                ("V100", v100, cDef100, dDdt100, dIdt100, limD100, limI100, utilD100, utilI100),
                ("V130", v130, cDef130, dDdt130, dIdt130, limD130, limI130, utilD130, utilI130),
                ("V150", v150, cDef150, dDdt150, dIdt150, limD150, limI150, utilD150, utilI150),
                ("VK", vK, cDefK, dDdtK, dIdtK, limDK, limIK, utilDK, utilIK),
            ]

            if L <= 0:
                transitionData = []
                anyDeltaI = False
                dKappa = abs(curvature[i+1] - curvature[i])
                for pName, vArr, iArr, dDArr, dIArr, lDArr, lIArr, utilDArr, utilIArr in profiles:
                    vMin = min(vArr[i], vArr[i+1])
                    # Physical deltaI: D is continuous at L=0 boundary (Stage 3), so D cancels
                    deltaI = 11.8 * vMin**2 * dKappa if vMin > 1e-3 else 0.0
                    dILim = getDeficiencyLimit(vMin)
                    exceeded = deltaI > dILim + 1e-3
                    profileStats[pName]["max_deltaI"] = max(profileStats[pName]["max_deltaI"], deltaI)
                    transitionData.append((pName, deltaI, vMin, dILim, exceeded))
                    if deltaI > 1e-3:
                        anyDeltaI = True
                
                gTypeFrom = geomType[i] if i < len(geomType) else "-"
                gTypeTo = geomType[i+1] if i+1 < len(geomType) else "-"
                if anyDeltaI and gTypeFrom != "Spiral" and gTypeTo != "Spiral":
                    lblFrom = elemTypeNames.get(gTypeFrom, gTypeFrom)
                    lblTo   = elemTypeNames.get(gTypeTo,   gTypeTo)
                    reportLines.append(f"--- {lan.get('reportTransition', 'Transition')} | {lan['station']}: {stations[i]:.3f} | {lblFrom} -> {lblTo} ---")
                    for pName, dIVal, vVal, dILimVal, exceeded in transitionData:
                        flag = " (!)" if exceeded else ""
                        lineStr = f"  [{pName}] V: {vVal:.0f} km/h | deltaI: {dIVal:.0f} mm (limit {dILimVal:.0f} mm){flag}"
                        reportLines.append(lineStr)
                    reportLines.append("")
                continue
            
            gType = geomType[i]
            if gType in ["Curve", "Spiral"]:
                totalElements += 1

            rStart = radius[i] if i < len(radius) else float('inf')
            rEnd = radius[i+1] if i+1 < len(radius) else float('inf')
            
            maxVElem = max(v100[i], v100[i+1], v130[i], v130[i+1], v150[i], v150[i+1], vK[i], vK[i+1])
            xVal = L / maxVElem if maxVElem > 0 else float('inf')
            strX = f"{xVal:.2f}" if maxVElem > 0 else "INF"
            
            gTypeLbl  = elemTypeNames.get(gType, gType)
            headerLine = f"--- {gTypeLbl} | {lan['station']}: {stations[i]:.3f} - {stations[i+1]:.3f} | L = {L:.2f} m ({strX}*V)"
            if gType == "Curve":
                headerLine += f" | R: {formatR(rStart)} m"
            elif gType == "Spiral":
                headerLine += f" | R: {formatR(rStart)} -> {formatR(rEnd)} m"
            headerLine += " ---"
            reportLines.append(headerLine)

            for pName, vArr, iArr, dDArr, dIArr, lDArr, lIArr, utilDArr, utilIArr in profiles:
                vStart, vEnd = vArr[i], vArr[i+1]
                signDStart = np.sign(cant[i]) if cant[i] != 0 else 1.0
                signDEnd = np.sign(cant[i+1]) if cant[i+1] != 0 else 1.0
                dStart = signDStart * np.floor(np.abs(cant[i]))
                dEnd = signDEnd * np.floor(np.abs(cant[i+1]))
                signIStart = np.sign(iArr[i]) if iArr[i] != 0 else 1.0
                signIEnd = np.sign(iArr[i+1]) if iArr[i+1] != 0 else 1.0
                iStart = signIStart * np.ceil(np.abs(iArr[i]))
                iEnd = signIEnd * np.ceil(np.abs(iArr[i+1]))
                ddDt = dDArr[i]
                diDt = dIArr[i]

                profileStats[pName]["max_D"] = max(profileStats[pName]["max_D"], abs(dStart), abs(dEnd))
                profileStats[pName]["max_I"] = max(profileStats[pName]["max_I"], abs(iStart), abs(iEnd))
                profileStats[pName]["max_dd_dt"] = max(profileStats[pName]["max_dd_dt"], abs(ddDt))
                profileStats[pName]["max_di_dt"] = max(profileStats[pName]["max_di_dt"], abs(diDt))

                lineStr = f"  [{pName}] V: {vStart:.0f} -> {vEnd:.0f} km/h"
                if gType == "Curve":
                    lineStr += f" | D: {dStart:.0f} mm | I: {iStart:.0f} mm"
                elif gType == "Spiral":
                    dD = abs(dEnd - dStart)
                    dI = abs(iEnd - iStart)
                    
                    if dD > 1e-3 and vStart > 1e-3:
                        nValF = L * 1000 / (dD * vStart)
                        profileStats[pName]["min_n"] = min(profileStats[pName]["min_n"], nValF)
                    if dI > 1e-3 and vStart > 1e-3:
                        nIValF = L * 1000 / (dI * vStart)
                        if dI > getDeficiencyLimit(vStart):
                            profileStats[pName]["min_nI"] = min(profileStats[pName]["min_nI"], nIValF)
                        if nIValF < profileStats[pName]["min_nI_all"]:
                            profileStats[pName]["min_nI_all"] = nIValF
                            profileStats[pName]["min_nI_all_dI"] = dI
                        
                    nVal = calcN(L, dD, vStart)
                    nIVal = calcN(L, dI, vStart)
                    lineStr += f" | D: {dStart:.0f} -> {dEnd:.0f} mm | I: {iStart:.0f} -> {iEnd:.0f} mm | n: {nVal} | nI: {nIVal} | deltaI: {dI:.0f} mm | dD/dt: {ddDt:.2f} mm/s | dI/dt: {diDt:.2f} mm/s"

                utilDVal = max(utilDArr[i], utilDArr[i+1])
                utilIVal = max(utilIArr[i], utilIArr[i+1])
                lineStr += f" | {utilDLbl}: {utilDVal*100:.1f}% | {utilILbl}: {utilIVal*100:.1f}%"

                if gType in ["Curve", "Spiral"]:
                    profileStats[pName]["weighted_util_sum_D"] += utilDVal * L
                    profileStats[pName]["weighted_util_sum_I"] += utilIVal * L
                    profileStats[pName]["total_length"] += L

                if gType in ["Curve", "Spiral"]:
                    if lDArr[i] or lDArr[i+1]: stats[pName]["limit_D"] += 1
                    if lIArr[i] or lIArr[i+1]: stats[pName]["limit_I"] += 1

                reportLines.append(lineStr)
            reportLines.append("")

        reportLines.append(lan.get("reportStatisticsTitle", "=== Limiting Factors Statistics ==="))
        reportLines.append(f"{lan.get('totalElements', 'Total evaluated elements (Curve/Spiral)')}: {totalElements}")
        reportLines.append("")

        for pName in ["V100", "V130", "V150", "VK"]:
            reportLines.append(f"--- {pName} ---")
            reportLines.append(f"  {lan.get('lim_D', 'D (Cant)')} limit: {stats[pName]['limit_D']}x")
            reportLines.append(f"  {lan.get('lim_I', 'I (Cant Deficiency)')} limit: {stats[pName]['limit_I']}x")
            reportLines.append("")

        reportLines.append(lan.get("reportExtremesTitle", "=== Extremes of Geometric Parameters ==="))
        reportLines.append("")

        for pName in ["V100", "V130", "V150", "VK"]:
            reportLines.append(f"--- {pName} ---")
            pStats = profileStats[pName]
            
            strN = f"{pStats['min_n']:.2f}" if pStats['min_n'] != float('inf') else "-"
            strNI = f"{pStats['min_nI']:.2f}" if pStats['min_nI'] != float('inf') else "-"
            strNIAll = f"{pStats['min_nI_all']:.2f} (deltaI = {pStats['min_nI_all_dI']:.0f} mm)" if pStats['min_nI_all'] != float('inf') else "-"
            
            weightedAvgUtilD = pStats["weighted_util_sum_D"] / pStats["total_length"] if pStats["total_length"] > 0 else 0.0
            weightedAvgUtilI = pStats["weighted_util_sum_I"] / pStats["total_length"] if pStats["total_length"] > 0 else 0.0
            reportLines.append(f"  {lan.get('stat_weighted_avg_util_D', 'Weighted Avg Util D [-]')}: {weightedAvgUtilD*100:.2f}%")
            reportLines.append(f"  {lan.get('stat_weighted_avg_util_I', 'Weighted Avg Util I [-]')}: {weightedAvgUtilI*100:.2f}%")

            reportLines.append(f"  {lan.get('stat_min_n', 'Min n [-]')}: {strN}")
            reportLines.append(f"  {lan.get('stat_min_nI', 'Min nI [-]')}: {strNI}")
            reportLines.append(f"  {lan.get('stat_min_nI_all', 'Min nI (all) [-]')}: {strNIAll}")
            reportLines.append(f"  {lan.get('stat_max_dDdt', 'Max dD/dt [mm/s]')}: {pStats['max_dd_dt']:.2f}")
            reportLines.append(f"  {lan.get('stat_max_dIdt', 'Max dI/dt [mm/s]')}: {pStats['max_di_dt']:.2f}")
            reportLines.append(f"  {lan.get('stat_max_D', 'Max D [mm]')}: {pStats['max_D']:.0f}")
            reportLines.append(f"  {lan.get('stat_max_I', 'Max I [mm]')}: {pStats['max_I']:.0f}")
            reportLines.append(f"  {lan.get('stat_max_deltaI', 'Max deltaI [mm]')}: {pStats['max_deltaI']:.0f}")
            reportLines.append("")

        self.reportGeometryWidget.setPlainText("\n".join(reportLines))
        self.showReportView()

    def generateVehicleReport(self, vIdx=0):
        lan = lang.DIC[self.currentLanguage]
        stations = self.dataStorage.get(f"kinematicsStationM_{vIdx}", [])
        if len(stations) == 0:
            self.reportVehicleTable.setData([{"Info": lan.get("no_data", "No data available. Calculate values first.")}])
            self.showReportView()
            return

        speeds = self.dataStorage.get(f"kinematicsSpeedM_{vIdx}", np.zeros_like(stations))
        accels = self.dataStorage.get(f"kinematicsAcceleration_{vIdx}", np.zeros_like(stations))
        fTrac = self.dataStorage.get(f"kinematicsForceTractionKN_{vIdx}", np.zeros_like(stations))
        fBrake = self.dataStorage.get(f"kinematicsForceBrakingKN_{vIdx}", np.zeros_like(stations))
        fRes = self.dataStorage.get(f"kinematicsForceResistanceKN_{vIdx}", np.zeros_like(stations))
        times = self.dataStorage.get(f"kinematicsTimeS_{vIdx}", [])
        hasTimes = len(times) == len(stations)

        # Shorthand column key names (keeps dict literals concise and order consistent)
        kSta   = lan.get("station", "Station [km]")
        kTime  = lan.get("time", "Time [s]")
        kSpd   = lan.get("speed", "Speed [km/h]")
        kAcc   = lan.get("accel", "Accel [m/s²]")
        kTrac  = lan.get("forceTraction", "Tractive Force [kN]")
        kBrake = lan.get("forceBraking", "Braking Force [kN]")
        kRes   = lan.get("forceResistance", "Resistance [kN]")

        tableData = []

        # Vehicle name for report header
        vehicleName = self.getVehicleName(vIdx)
        summaryTitle = lan.get('run_summary_title', 'RUN SUMMARY')
        if vehicleName:
            summaryTitle = f"{summaryTitle} — {vehicleName}"

        # Travel time, average speed, and maximum speed
        if len(stations) > 1 and len(times) > 1:
            totalDistanceM = abs(stations[-1] - stations[0])
            totalTimeS = times[-1]
            avgSpeedMs = totalDistanceM / totalTimeS if totalTimeS > 0 else 0
            avgSpeedKmh = avgSpeedMs * 3.6
            maxSpeedKmh = float(np.max(speeds)) * 3.6 if len(speeds) > 0 else 0.0
            minutes, seconds = divmod(totalTimeS, 60)

            tableData.append({
                kSta:   f"=== {summaryTitle} ===",
                kTime:  "",
                kSpd:   lan.get('total_travel_time', 'Total travel time:'),
                kAcc:   f"{int(minutes):02d} min {int(seconds):02d} s",
                kTrac:  lan.get('average_speed', 'Average speed:'),
                kBrake: f"{avgSpeedKmh:.2f} km/h",
                kRes:   f"{lan.get('maxSpeed_achieved', 'Max speed:')} {maxSpeedKmh:.0f} km/h"
            })
            tableData.append({k: "---" for k in tableData[0].keys()})

        # Energy calculation (use abs(dx) so reversed vehicles give positive values)
        dx = np.abs(np.diff(stations))
        dx = np.append(dx, 0)
        energyKwh = np.sum(fTrac * dx) / 3600.0
        brakeEnergyKwh = np.sum(fBrake * dx) / 3600.0

        tableData.append({
            kSta:   f"=== {lan.get('energy_title', 'ENERGY')} ===",
            kTime:  "",
            kSpd:   f"{lan.get('energyTraction', 'Traction [kWh]')}:",
            kAcc:   f"{energyKwh:.2f}",
            kTrac:  f"{lan.get('energyBraking', 'Braking [kWh]')}:",
            kBrake: f"{brakeEnergyKwh:.2f}",
            kRes:   ""
        })
        tableData.append({k: "---" for k in tableData[0].keys()})

        # Train stops summary block
        trainStops = self.dataStorage.get("settingsData", {}).get("trainStops", [])
        if trainStops:
            tableData.append({
                kSta:   f"=== {lan.get('stopsHeader', 'STOPS')} ===",
                kTime:  "",
                kSpd:   "",
                kAcc:   "",
                kTrac:  "",
                kBrake: "",
                kRes:   ""
            })
            for stop in trainStops:
                try:
                    sKm = float(stop[0])
                    dwell = float(stop[1])
                    name = str(stop[2]) if len(stop) > 2 else ""
                    sM = sKm * 1000.0
                    idx = np.argmin(np.abs(stations - sM))
                    if np.abs(stations[idx] - sM) < 2.0:
                        depTime = self.dataStorage.get(f"kinematicsTimeS_{vIdx}")[idx]
                        arrTime = max(0, depTime - dwell)
                        tableData.append({
                            kSta:   f"{sKm:.3f} {name}",
                            kTime:  "",
                            kSpd:   f"Arr: {arrTime:.1f} s",
                            kAcc:   f"Dep: {depTime:.1f} s",
                            kTrac:  f"Dwell: {dwell} s",
                            kBrake: "-",
                            kRes:   "-"
                        })
                except Exception:
                    continue
            tableData.append({k: "---" for k in tableData[0].keys()})

        # Every 10th point + always include first and last (V=0 endpoints)
        stepIndices = list(range(0, len(stations), 10))
        if len(stations) - 1 not in stepIndices:
            stepIndices.append(len(stations) - 1)
        for i in stepIndices:
            sKm = stations[i] / 1000.0
            tableData.append({
                kSta:   f"{sKm:.3f}",
                kTime:  f"{times[i]:.1f}" if hasTimes else "",
                kSpd:   f"{speeds[i]*3.6:.1f}",
                kAcc:   f"{accels[i]:.3f}",
                kTrac:  f"{fTrac[i]:.1f}",
                kBrake: f"{fBrake[i]:.1f}",
                kRes:   f"{fRes[i]:.1f}"
            })

        self.reportVehicleTable.setData(tableData)
        self.showReportView()

    def exportGeometryReport(self):
        lan = lang.DIC[self.currentLanguage]
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

    def exportVehicleReport(self, vIdx=0):
        lan = lang.DIC[self.currentLanguage]
        stations = self.dataStorage.get(f"kinematicsStationM_{vIdx}", [])
        if len(stations) == 0:
            QMessageBox.warning(self, lan.get("error", "Error"), lan.get("no_data", "No data available. Calculate values first."))
            return

        filepath, _ = QFileDialog.getSaveFileName(self, lan.get("exportVehicleReport", "Export Vehicle Report"), "", "CSV Files (*.csv);;All Files (*)")
        if not filepath:
            return

        try:
            speeds = self.dataStorage.get(f"kinematicsSpeedM_{vIdx}", np.zeros_like(stations))
            accels = self.dataStorage.get(f"kinematicsAcceleration_{vIdx}", np.zeros_like(stations))
            fTrac = self.dataStorage.get(f"kinematicsForceTractionKN_{vIdx}", np.zeros_like(stations))
            fBrake = self.dataStorage.get(f"kinematicsForceBrakingKN_{vIdx}", np.zeros_like(stations))
            fRes = self.dataStorage.get(f"kinematicsForceResistanceKN_{vIdx}", np.zeros_like(stations))
            times = self.dataStorage.get(f"kinematicsTimeS_{vIdx}", [])
            hasTimes = len(times) == len(stations)

            with open(filepath, "w", newline="", encoding="utf-8") as file:
                writer = csv.writer(file)

                # === RUN SUMMARY ===
                vehicleName = self.getVehicleName(vIdx)
                if len(stations) > 1 and len(times) > 1:
                    totalDistanceM = abs(stations[-1] - stations[0])
                    totalTimeS = times[-1]
                    avgSpeedMs = totalDistanceM / totalTimeS if totalTimeS > 0 else 0
                    avgSpeedKmh = avgSpeedMs * 3.6
                    maxSpeedKmh = float(np.max(speeds)) * 3.6 if len(speeds) > 0 else 0.0
                    minutes, seconds = divmod(totalTimeS, 60)
                    writer.writerow([f"=== {lan.get('run_summary_title', 'RUN SUMMARY')} ==="])
                    if vehicleName:
                        writer.writerow([lan.get('vehicle', 'Vehicle') + ":", vehicleName])
                    writer.writerow([lan.get('total_travel_time', 'Total travel time:'),
                                     f"{int(minutes):02d} min {int(seconds):02d} s"])
                    writer.writerow([lan.get('average_speed', 'Average speed:'),
                                     f"{avgSpeedKmh:.2f} km/h"])
                    writer.writerow([lan.get('maxSpeed_achieved', 'Maximum speed achieved:'),
                                     f"{maxSpeedKmh:.0f} km/h"])
                    writer.writerow([])

                # === ENERGY (abs(dx) so reversed vehicles give positive values) ===
                dx = np.abs(np.diff(stations))
                dx = np.append(dx, 0)
                energyKwh = np.sum(fTrac * dx) / 3600.0
                brakeEnergyKwh = np.sum(fBrake * dx) / 3600.0
                writer.writerow([f"=== {lan.get('energy_title', 'ENERGY')} ==="])
                writer.writerow([lan.get('energyTraction', 'Traction [kWh]'), f"{energyKwh:.2f}"])
                writer.writerow([lan.get('energyBraking', 'Braking [kWh]'), f"{brakeEnergyKwh:.2f}"])
                writer.writerow([])

                # === STOPS ===
                trainStops = self.dataStorage.get("settingsData", {}).get("trainStops", [])
                if trainStops and hasTimes:
                    writer.writerow([f"=== {lan.get('stopsHeader', 'STOPS')} ==="])
                    writer.writerow([
                        lan.get("station", "Station [km]"),
                        lan.get("stopName", "Stop Name"),
                        lan.get("arrivalTime", "Arr [s]"),
                        lan.get("departureTime", "Dep [s]"),
                        lan.get("dwellTimeTable", "Dwell Time [s]")
                    ])
                    for stop in trainStops:
                        try:
                            sKm = float(stop[0])
                            dwell = float(stop[1])
                            name = str(stop[2]) if len(stop) > 2 else ""
                            sM = sKm * 1000.0
                            idx = np.argmin(np.abs(stations - sM))
                            if np.abs(stations[idx] - sM) < 2.0:
                                depTime = times[idx]
                                arrTime = max(0.0, depTime - dwell)
                                writer.writerow([f"{sKm:.3f}", name,
                                                 f"{arrTime:.1f}", f"{depTime:.1f}",
                                                 f"{dwell:.0f}"])
                        except Exception:
                            continue
                    writer.writerow([])

                # === DATA ROWS ===
                writer.writerow([
                    lan.get("station", "Station [km]"),
                    lan.get("time", "Time [s]"),
                    lan.get("speed", "Speed [km/h]"),
                    "Accel [m/s2]",
                    lan.get("forceTraction", "Tractive Force [kN]"),
                    lan.get("forceBraking", "Braking Force [kN]"),
                    lan.get("forceResistance", "Resistance [kN]")
                ])
                for i in range(len(stations)):
                    sKm = stations[i] / 1000.0
                    writer.writerow([
                        f"{sKm:.3f}",
                        f"{times[i]:.1f}" if hasTimes else "",
                        f"{speeds[i]*3.6:.1f}",
                        f"{accels[i]:.3f}",
                        f"{fTrac[i]:.1f}",
                        f"{fBrake[i]:.1f}",
                        f"{fRes[i]:.1f}"
                    ])

        except Exception as e:
            QMessageBox.critical(self, lan.get("error", "Error"), f"{e}")

    # Store the parsed data and defer the table build until the dock is visible
    def updateTableLandXML(self, data):
        self.pendingLandXmlTableData = data
        self.dockLandXmlParsed.requestUpdate()

    # Build the LandXML overview table from the last parsed dataset
    def renderTableLandXML(self):
        data = getattr(self, "pendingLandXmlTableData", None)
        if not data:
            return

        stations = np.concatenate((data["stationCant"], data["stationHorizontal"], data["stationVertical"]))
        uniqueStations = np.unique(stations)
        tableData = []
        lan = lang.DIC[self.currentLanguage]
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

    # Split station array into monotone sections on direction reversal or gap over 20 km
    # Tracks the last non-zero diff so duplicate stations do not mask a later reversal
    def TTPSections(self, stations):
        if len(stations) == 0:
            return []

        sections = []
        startID = 0
        prevNonzeroDiff = 0   # direction of the most recent non-zero step

        for i in range(1, len(stations)):
            diff = stations[i] - stations[i-1]

            isBoundary = abs(diff) > 20

            if not isBoundary and diff != 0:
                if prevNonzeroDiff != 0 and np.sign(diff) != np.sign(prevNonzeroDiff):
                    isBoundary = True
                prevNonzeroDiff = diff   # update only on non-zero steps

            if isBoundary:
                sections.append({
                    "startID": startID,
                    "endID": i - 1,
                    "stationStart": stations[startID],
                    "stationEnd": stations[i - 1]
                })
                startID = i
                # Reset: direction of the new section is unknown until we see its
                # first non-zero step; setting to 0 avoids a false split at i+1.
                prevNonzeroDiff = 0

        # Add the last section
        sections.append({
            "startID": startID,
            "endID": len(stations) - 1,
            "stationStart": stations[startID],
            "stationEnd": stations[len(stations) - 1]
        })

        return sections

    @staticmethod
    # Fix post-step semantics for a descending-order TTP section
    # After ascending sort, getSpeedLimitAt assigns each sign limit one segment too early
    # The fix inserts a synthetic station at stations[0]-1e-6 and appends the last limit
    # so every limit applies to the interval below its sign, and is a no-op when ascending
    def correctReversedTTPSection(secStations, secLimits):
        if len(secStations) <= 1:
            return secStations, secLimits

        # Only transform sections that were originally in descending order
        if secStations[0] <= secStations[-1]:
            return secStations, secLimits

        sortIdx = np.argsort(secStations, kind='stable')
        stAsc = secStations[sortIdx]
        spAsc = secLimits[sortIdx]

        # Prepend a synthetic point 1 µm below the lowest real sign.
        # It carries the lowest sign's own limit so that getSpeedLimitAt(x)
        # for x < st_asc[0] still returns the correct value (sp_asc[0]).
        stationsOut = np.concatenate(([stAsc[0] - 1e-6], stAsc))
        # Each sign's limit now applies from just-below its own km up to the
        # next sign's km (the shift gives post-step semantics in ascending order).
        limitsOut = np.append(spAsc, spAsc[-1])
        return stationsOut, limitsOut

    def calculateGeometry(self):

        if "alignmentCoordinates" not in self.dataStorage.get("LandXML",{}):
            return
        
        calculate = geometry_engine.GeometryCalculator(self.dataStorage)
        calculate.runCalculationLoop()

        self.updateMapWithSpeeds()
        self.plotCant()
        self.plotSpeedLimits()

        # Step 5 of the workflow guide covers the GPK calculation
        self.workflowWidget.markCompleted(4)
        self.setEngineStatus(lang.DIC[self.currentLanguage].get("statusGeometryDone", "Geometry calculated"))

    def calculateGeometryI(self):

        if "alignmentCoordinates" not in self.dataStorage.get("LandXML",{}):
            return
        
        calculate = geometry_engine.GeometryCalculator(self.dataStorage)
        calculate.runCalculationLoopI()

        self.updateMapWithSpeeds()
        self.plotCant()
        self.plotSpeedLimits()

        # Step 5 of the workflow guide covers the GPK calculation
        self.workflowWidget.markCompleted(4)
        self.setEngineStatus(lang.DIC[self.currentLanguage].get("statusGeometryDone", "Geometry calculated"))

    def calculateTrainSpeed(self):
        vehicle = vehicle_engine.VehicleCalculator(self.dataStorage)
        vehicle.calculateKinematics()
        
        warnings = []
        for i in range(3):
            if self.dataStorage.get(f"kinematicsWarning_{i}") == "train_too_long":
                warnings.append(str(i+1))
                
        if warnings:
            lan = lang.DIC[self.currentLanguage]
            msg = lan["train_too_long"] + f" (Vehicle: {', '.join(warnings)})"
            QMessageBox.warning(self, lan["error"], msg)

        vehicle.speedLimitsToTime()

        self.plotKinematics()

        # Step 6 of the workflow guide covers the running simulation
        self.workflowWidget.markCompleted(5)
        self.setEngineStatus(lang.DIC[self.currentLanguage].get("statusSimulationDone", "Simulation finished"))

    def updateMapWithSpeeds(self):
        lxml = self.dataStorage.get("LandXML", {})
        if not lxml:
            return

        # Geometry profiles (V100 / V130 / V150 / VK)
        for profile in ["100", "130", "150", "K"]:
            lxml[f"speedLimits{profile}"] = self.dataStorage.get(f"speedLimits{profile}")
            lxml[f"stationSpeed{profile}"] = self.dataStorage.get(f"stationSpeed{profile}")

        # TTP raw speed limits – nearest-station extrapolation is handled in map_viewer
        lxml["speedLimitsTTP"]  = np.asarray(self.dataStorage.get("speedLimits",      []))
        lxml["stationSpeedTTP"] = np.asarray(self.dataStorage.get("stationSpeedLimits", []))

        self.mapWidget.drawAlignment(lxml.get("alignmentCoordinates", []), lxml)
        