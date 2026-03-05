# PySide6 imports
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import (QTabWidget, QApplication, QMainWindow, QPushButton, QWidget,
                                QHBoxLayout, QVBoxLayout, QLabel, QPlainTextEdit, QFileDialog, 
                                QSplitter, QMessageBox)
from PySide6.QtGui import QAction, QIcon

# pyqtgraph imports
import pyqtgraph as pg

# Matplotlib imports for Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

# Local imports

import lang
import readfile

class MplCanvas(FigureCanvas):
    # Canvas widget for Matplotlib plots
    def __init__(self, parent=None, width=5, height=6, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi)
        
        self.ax_speed = self.fig.add_subplot(211)

        self.ax_cant = self.fig.add_subplot(212, sharex=self.ax_speed)

        self.fig.subplots_adjust(hspace=0.3)

        super().__init__(self.fig)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Window settings

        self.resize(QSize(800, 600))
        self.current_language = "en"
        lan = lang.DIC[self.current_language]
        self.setWindowTitle(lan["app_title"])
        

        # Layouts - main grid

        layoutH = QHBoxLayout()
        layoutV = QVBoxLayout()
        layoutPlots = QVBoxLayout()
        layoutTabsXML = QTabWidget()

        # Central widget

        widget = QWidget()
        self.setCentralWidget(widget)

        # Menu bar
        main_menu = self.menuBar()
        self.fileMenu = main_menu.addMenu(lan["file"])
        self.settingsMenu = main_menu.addMenu(lan["settings"])

        # Submenus - File
        openFileAction = QAction(lan["open_file"], self)
        self.fileMenu.addAction(openFileAction)
        openFileAction.triggered.connect(self.openFile)

        openParseLandXMLAction = QAction(lan["open_parse_landxml"], self)
        self.fileMenu.addAction(openParseLandXMLAction)
        openParseLandXMLAction.triggered.connect(self.openParseLandXML)

        openParseXMLTTPAction = QAction(lan["open_parse_xmlttp"], self)      
        self.fileMenu.addAction(openParseXMLTTPAction)
        openParseXMLTTPAction.triggered.connect(self.openParseXMLTTP)

        cleanDataAction = QAction(lan["clean"], self)
        self.fileMenu.addAction(cleanDataAction)
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

        # Set layouts
        layoutH.addLayout(layoutV)
        widget.setLayout(layoutH)
        layoutV.addWidget(layoutTabsXML, stretch=1)
        layoutH.addLayout(layoutPlots, stretch=2)

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
        layoutXMLLand = QVBoxLayout(layoutXMLLand_container)

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

        self.labelXMLTTPRaw = QLabel("Raw Data")
        self.labelXMLTTPParsed = QLabel("Parsed Data")
        self.labelLandXMLRaw = QLabel("Raw Data")
        self.labelLandXMLParsed = QLabel("Parsed Data")

        layoutXMLTTPRaw.addWidget(self.labelXMLTTPRaw)
        layoutXMLTTPRaw.addWidget(self.textboxRawTTP)
        layoutXMLTTPParsed.addWidget(self.labelXMLTTPParsed)
        layoutXMLTTPParsed.addWidget(self.tableTTP)
    
        layoutXMLLandRaw.addWidget(self.labelLandXMLRaw)
        layoutXMLLandRaw.addWidget(self.textboxRawLandXML)
        layoutXMLLandParsed.addWidget(self.labelLandXMLParsed)
        layoutXMLLandParsed.addWidget(self.tableLandXML)
        

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


        # Matplotlib canvas
        self.canvas = MplCanvas(self, width=5, height=4, dpi=100)
        layoutPlots.addWidget(self.canvas, stretch=3)
        self.toolbar = NavigationToolbar(self.canvas, self)
        layoutPlots.addWidget(self.toolbar)

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
        self.fileMenu.actions()[1].setText(lan["open_parse_landxml"])
        self.fileMenu.actions()[2].setText(lan["open_parse_xmlttp"])
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
                

    def openParseLandXML(self):
        file_content = self.getFileContent()
        if file_content is not None:
            self.textboxRawLandXML.setPlainText(file_content)
            LandXMLData = readfile.ReadFile().ParseLandXML(file_content)
            self.tableLandXML.setData(LandXMLData)
            self.plotCant(LandXMLData["stationCant"], LandXMLData["cant"])
        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["no_file"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def openParseXMLTTP(self):
        file_content = self.getFileContent()
        if file_content is not None:
            self.textboxRawTTP.setPlainText(file_content)
            XMLTTPData = readfile.ReadFile().ParseXMLTTP(file_content)
            self.tableTTP.setData(XMLTTPData)
            self.plotSpeedLimits(XMLTTPData["stationSpeedLimits"], XMLTTPData["speedLimits"])
        else:
            lan = lang.DIC[self.current_language]
            err = QMessageBox()
            err.setWindowTitle(lan["error"])
            err.setText(lan["no_file"])
            err.setIcon(QMessageBox.Icon.Warning)
            err.exec()

    def plotCant(self, stationCant, cant):
        self.canvas.ax_cant.clear()
        self.canvas.ax_cant.plot(stationCant, cant, marker='o', linestyle='-')
        self.canvas.ax_cant.grid(True)
        self.canvas.ax_cant.autoscale(enable=True, axis='x', tight=True)
        self.canvas.ax_cant.set_xlabel('Station (km)')
        self.canvas.ax_cant.set_ylabel('Cant (mm)')
        self.canvas.ax_cant.set_title('Cant vs Station')
        self.canvas.draw()

    def plotSpeedLimits(self, stationSpeedLimits, speedLimits):
        self.canvas.ax_speed.clear()
        self.canvas.ax_speed.step(stationSpeedLimits, speedLimits, where="post", marker='s', linestyle='-')
        self.canvas.ax_speed.grid(True)
        self.canvas.ax_speed.autoscale(enable=True, axis='x', tight=True)
        self.canvas.ax_speed.set_xlabel('Station (km)')
        self.canvas.ax_speed.set_ylabel('Speed Limit (km/h)')
        self.canvas.ax_speed.set_title('Speed Limit vs Station')
        self.canvas.draw()

    def cleanData(self):
        self.textboxRawLandXML.setPlainText("")
        self.textboxRawTTP.setPlainText("")
        self.tableLandXML.setData({})
        self.tableTTP.setData({})
        self.canvas.ax_cant.clear()
        self.canvas.ax_speed.clear()
        self.canvas.draw()
        

