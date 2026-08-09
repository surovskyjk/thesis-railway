# Track Statistics panel summarising length, design/actual speed maxima and travel times
from PySide6.QtWidgets import (QComboBox, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QScrollArea, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)
import numpy as np

from ui_kit import CollapsibleSection, MetricCard
from vehicle_catalog import MAX_VEHICLES

# Design speed profiles offered by the profile selector, matches gui_overlay's MapSettingsDialog
DESIGN_PROFILE_CHOICES = [
    ("TTP", "TTP"),
    ("100", "V100"),
    ("130", "V130"),
    ("150", "V150"),
    ("K", "VK"),
]

# Design profile selected by default, matches MapWidget's own default speed profile
DEFAULT_DESIGN_PROFILE = "150"

# Row height used to size the segment tables without letting them grow unbounded
TABLE_ROW_HEIGHT_PX = 22

# Most rows a segment table shows before it starts scrolling internally
TABLE_MAX_VISIBLE_ROWS = 6


class TrackStatisticsWidget(QWidget):
    def __init__(self, lan, parent=None):
        super().__init__(parent)

        self.lan = lan or {}
        self.lastDataStorage = {}
        self.vehicleNameResolver = None

        scrollArea = QScrollArea(self)
        scrollArea.setWidgetResizable(True)
        scrollArea.setFrameShape(QScrollArea.Shape.NoFrame)

        rootLayout = QVBoxLayout(self)
        rootLayout.setContentsMargins(0, 0, 0, 0)
        rootLayout.addWidget(scrollArea)

        contentWidget = QWidget()
        scrollArea.setWidget(contentWidget)

        outerLayout = QVBoxLayout(contentWidget)
        outerLayout.setContentsMargins(4, 4, 4, 4)
        outerLayout.setSpacing(4)

        # Compact selector row, replaces two separate form rows
        selectorLayout = QHBoxLayout()
        selectorLayout.setSpacing(4)
        self.designProfileRowLabel = QLabel()
        self.designProfileCombo = QComboBox()
        for profileKey, displayText in DESIGN_PROFILE_CHOICES:
            self.designProfileCombo.addItem(displayText, profileKey)
        defaultIndex = self.designProfileCombo.findData(DEFAULT_DESIGN_PROFILE)
        self.designProfileCombo.setCurrentIndex(max(0, defaultIndex))
        self.designProfileCombo.currentIndexChanged.connect(self.onDesignProfileChanged)
        selectorLayout.addWidget(self.designProfileRowLabel)
        selectorLayout.addWidget(self.designProfileCombo, 1)

        self.vehicleRowLabel = QLabel()
        self.vehicleCombo = QComboBox()
        self.vehicleCombo.currentIndexChanged.connect(self.onVehicleChanged)
        selectorLayout.addWidget(self.vehicleRowLabel)
        selectorLayout.addWidget(self.vehicleCombo, 1)
        outerLayout.addLayout(selectorLayout)

        # KPI cards, a compact grid replaces the four free growing group boxes
        cardsLayout = QGridLayout()
        cardsLayout.setSpacing(4)
        self.lengthCard = MetricCard()
        self.designMaxCard = MetricCard()
        self.actualMaxCard = MetricCard()
        self.totalTimeCard = MetricCard()
        self.originDestCard = MetricCard()
        cardsLayout.addWidget(self.lengthCard, 0, 0)
        cardsLayout.addWidget(self.designMaxCard, 0, 1)
        cardsLayout.addWidget(self.actualMaxCard, 1, 0)
        cardsLayout.addWidget(self.totalTimeCard, 1, 1)
        cardsLayout.addWidget(self.originDestCard, 2, 0, 1, 2)
        outerLayout.addLayout(cardsLayout)

        # Detail tables live in collapsible sections, built eagerly so refreshes always find them
        self.designSegmentTable = self.buildSegmentTable(3)
        self.designSection = CollapsibleSection()
        self.designSection.setContentWidget(self.designSegmentTable)
        outerLayout.addWidget(self.designSection)

        self.actualSegmentTable = self.buildSegmentTable(3)
        self.actualSection = CollapsibleSection()
        self.actualSection.setContentWidget(self.actualSegmentTable)
        outerLayout.addWidget(self.actualSection)

        self.interstationTable = self.buildSegmentTable(2)
        self.interstationSection = CollapsibleSection(startExpanded=True)
        self.interstationSection.setContentWidget(self.interstationTable)
        outerLayout.addWidget(self.interstationSection)

        outerLayout.addStretch(1)

        self.rebuildVehicleCombo()
        self.updateTexts(self.lan)

    # Build one compact, read only segment table with the given column count
    def buildSegmentTable(self, columnCount):
        table = QTableWidget(0, columnCount)
        table.verticalHeader().setVisible(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setFixedHeight(20)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.verticalHeader().setDefaultSectionSize(TABLE_ROW_HEIGHT_PX)
        return table

    # Cap a table's height to a handful of rows so it stops stealing vertical space
    def constrainTableHeight(self, table):
        visibleRows = min(max(table.rowCount(), 1), TABLE_MAX_VISIBLE_ROWS)
        table.setMaximumHeight(table.horizontalHeader().height() + visibleRows * TABLE_ROW_HEIGHT_PX + 4)

    # Guard used before touching any optional array
    def hasData(self, values):
        return values is not None and len(values) > 0

    # Fallback text shown wherever a statistic cannot be computed yet
    def noDataText(self):
        return self.lan.get("statsNoData", "No data")

    # Render a duration in seconds as MM:SS, or the no-data placeholder
    def formatDuration(self, seconds):
        if seconds is None:
            return self.noDataText()
        minutes, secs = divmod(max(0.0, seconds), 60)
        return f"{int(minutes):02d}:{int(secs):02d}"

    # Scheduled stops in the order they were imported, never sorted by chainage
    def stopsList(self, dataStorage):
        stops = []
        for stop in (dataStorage.get("settingsData", {}) or {}).get("trainStops", []):
            try:
                stationKm = float(stop[0])
                dwell = float(stop[1])
                name = str(stop[2]) if len(stop) > 2 else ""
            except (IndexError, ValueError, TypeError):
                continue
            stops.append((stationKm, dwell, name))
        return stops

    # Track length in kilometres derived from the parsed alignment chainage
    def computeTrackLength(self, dataStorage):
        stationHorizontal = dataStorage.get("LandXML", {}).get("stationHorizontal")
        if not self.hasData(stationHorizontal):
            return None
        stationHorizontal = np.asarray(stationHorizontal, dtype=float)
        return float(np.max(stationHorizontal) - np.min(stationHorizontal))

    # Design speed limit and matching chainage arrays for the requested GPK profile
    def resolveDesignSpeedArrays(self, dataStorage, profile):
        if profile == "TTP":
            speeds = dataStorage.get("speedLimits")
            stations = dataStorage.get("stationSpeedLimits")
        else:
            speeds = dataStorage.get(f"speedLimits{profile}")
            stations = dataStorage.get(f"stationSpeed{profile}")

        if not self.hasData(speeds) or not self.hasData(stations):
            return None, None

        speeds = np.asarray(speeds, dtype=float)
        stations = np.asarray(stations, dtype=float)
        valid = np.isfinite(speeds) & np.isfinite(stations) & (speeds > 0)
        speeds, stations = speeds[valid], stations[valid]
        if len(speeds) == 0:
            return None, None
        return speeds, stations

    # Simulated actual speed [km/h] and chainage [km] arrays for one vehicle
    def resolveActualSpeedArrays(self, dataStorage, vehicleIndex):
        speedsMs = dataStorage.get(f"kinematicsSpeedM_{vehicleIndex}")
        stationsM = dataStorage.get(f"kinematicsStationM_{vehicleIndex}")
        if not self.hasData(speedsMs) or not self.hasData(stationsM):
            return None, None
        speedsKmh = np.asarray(speedsMs, dtype=float) * 3.6
        stationsKm = np.asarray(stationsM, dtype=float) / 1000.0
        return speedsKmh, stationsKm

    # Highest value in a speed array and the chainage at which it occurs
    def globalMax(self, speeds, stations):
        if not self.hasData(speeds):
            return None
        index = int(np.argmax(speeds))
        return float(speeds[index]), float(stations[index])

    # Fill a Segment / Max speed / Chainage table from consecutive stop boundaries
    def fillSegmentTable(self, table, speeds, stations, boundaries):
        table.setRowCount(0)
        if not self.hasData(speeds) or len(boundaries) < 2:
            return

        for segmentIndex in range(len(boundaries) - 1):
            startKm, startName = boundaries[segmentIndex]
            endKm, endName = boundaries[segmentIndex + 1]
            loKm, hiKm = sorted((startKm, endKm))
            mask = (stations >= loKm) & (stations <= hiKm)

            row = table.rowCount()
            table.insertRow(row)
            label = f"{startName or f'{startKm:.3f}'} → {endName or f'{endKm:.3f}'}"
            table.setItem(row, 0, QTableWidgetItem(label))
            if np.any(mask):
                bestIndex = int(np.argmax(speeds[mask]))
                table.setItem(row, 1, QTableWidgetItem(f"{speeds[mask][bestIndex]:.0f}"))
                table.setItem(row, 2, QTableWidgetItem(f"{stations[mask][bestIndex]:.3f}"))
            else:
                table.setItem(row, 1, QTableWidgetItem("-"))
                table.setItem(row, 2, QTableWidgetItem("-"))

        self.constrainTableHeight(table)

    # Cumulative time at the chainage nearest to a stop, mirrors generateVehicleReport's lookup
    def lookupTimeAtStation(self, stationsM, timesS, stationKm):
        if not self.hasData(stationsM) or not self.hasData(timesS):
            return None
        stationsM = np.asarray(stationsM, dtype=float)
        index = int(np.argmin(np.abs(stationsM - stationKm * 1000.0)))
        return float(timesS[index])

    # Arrival (before dwelling) and departure (after dwelling) time at one stop
    def stopTiming(self, stationsM, timesS, stationKm, dwellSeconds):
        depTime = self.lookupTimeAtStation(stationsM, timesS, stationKm)
        if depTime is None:
            return None, None
        return max(0.0, depTime - dwellSeconds), depTime

    # Total, origin-to-destination and inter-station travel times for one vehicle
    def computeTravelTimeSections(self, dataStorage, vehicleIndex):
        stationsM = dataStorage.get(f"kinematicsStationM_{vehicleIndex}")
        timesS = dataStorage.get(f"kinematicsTimeS_{vehicleIndex}")
        totalTime = float(timesS[-1]) if self.hasData(timesS) else None

        stops = self.stopsList(dataStorage)
        originDestTime = None
        interstationRows = []

        if self.hasData(stationsM) and self.hasData(timesS) and len(stops) >= 2:
            _, depFirst = self.stopTiming(stationsM, timesS, stops[0][0], stops[0][1])
            arrLast, _ = self.stopTiming(stationsM, timesS, stops[-1][0], stops[-1][1])
            if depFirst is not None and arrLast is not None:
                originDestTime = arrLast - depFirst

            for legIndex in range(len(stops) - 1):
                kmA, dwellA, nameA = stops[legIndex]
                kmB, dwellB, nameB = stops[legIndex + 1]
                _, depA = self.stopTiming(stationsM, timesS, kmA, dwellA)
                arrB, _ = self.stopTiming(stationsM, timesS, kmB, dwellB)
                if depA is None or arrB is None:
                    continue
                label = f"{nameA or f'{kmA:.3f}'} → {nameB or f'{kmB:.3f}'}"
                interstationRows.append((label, arrB - depA))

        return totalTime, originDestTime, interstationRows

    # Rebuild the vehicle selector from the currently simulated vehicle count
    def rebuildVehicleCombo(self):
        dataStorage = self.lastDataStorage or {}
        vehicleCount = int(dataStorage.get("num_vehicles", 1) or 1)
        vehicleCount = max(1, min(vehicleCount, MAX_VEHICLES))

        previousData = self.vehicleCombo.currentData()
        self.vehicleCombo.blockSignals(True)
        self.vehicleCombo.clear()
        for vehicleIndex in range(vehicleCount):
            caption = f'{self.lan.get("vehicle", "Vehicle")} {vehicleIndex + 1}'
            vehicleName = self.vehicleNameResolver(vehicleIndex) if self.vehicleNameResolver else ""
            if vehicleName:
                caption = f"{caption} — {vehicleName}"
            self.vehicleCombo.addItem(caption, vehicleIndex)
        restoredIndex = self.vehicleCombo.findData(previousData) if previousData is not None else -1
        self.vehicleCombo.setCurrentIndex(restoredIndex if restoredIndex >= 0 else 0)
        self.vehicleCombo.blockSignals(False)

    # Re-render every section from the currently cached data storage
    def refreshAll(self):
        self.refreshTrackLength()
        self.refreshDesignSpeedSection()
        self.refreshActualSpeedSection()
        self.refreshTravelTimeSection()

    def refreshTrackLength(self):
        length = self.computeTrackLength(self.lastDataStorage or {})
        self.lengthCard.setValue(f"{length:.3f} km" if length is not None else self.noDataText())

    def refreshDesignSpeedSection(self):
        dataStorage = self.lastDataStorage or {}
        profile = self.designProfileCombo.currentData() or DEFAULT_DESIGN_PROFILE
        speeds, stations = self.resolveDesignSpeedArrays(dataStorage, profile)

        peak = self.globalMax(speeds, stations)
        if peak is None:
            self.designMaxCard.setValue(self.noDataText())
        else:
            maxSpeed, location = peak
            self.designMaxCard.setValue(f"{maxSpeed:.0f} km/h", f"@ {location:.3f} km")

        boundaries = [(km, name) for km, dwell, name in self.stopsList(dataStorage)]
        self.fillSegmentTable(self.designSegmentTable, speeds, stations, boundaries)

    def refreshActualSpeedSection(self):
        dataStorage = self.lastDataStorage or {}
        vehicleIndex = self.vehicleCombo.currentData()
        if vehicleIndex is None:
            self.actualMaxCard.setValue(self.noDataText())
            self.actualSegmentTable.setRowCount(0)
            return

        speeds, stations = self.resolveActualSpeedArrays(dataStorage, vehicleIndex)
        peak = self.globalMax(speeds, stations)
        if peak is None:
            self.actualMaxCard.setValue(self.noDataText())
        else:
            maxSpeed, location = peak
            self.actualMaxCard.setValue(f"{maxSpeed:.0f} km/h", f"@ {location:.3f} km")

        boundaries = [(km, name) for km, dwell, name in self.stopsList(dataStorage)]
        self.fillSegmentTable(self.actualSegmentTable, speeds, stations, boundaries)

    def refreshTravelTimeSection(self):
        dataStorage = self.lastDataStorage or {}
        vehicleIndex = self.vehicleCombo.currentData()
        if vehicleIndex is None:
            self.totalTimeCard.setValue(self.noDataText())
            self.originDestCard.setValue(self.noDataText())
            self.interstationTable.setRowCount(0)
            return

        totalTime, originDestTime, legs = self.computeTravelTimeSections(dataStorage, vehicleIndex)
        self.totalTimeCard.setValue(self.formatDuration(totalTime))
        self.originDestCard.setValue(self.formatDuration(originDestTime))

        self.interstationTable.setRowCount(0)
        for label, legTime in legs:
            row = self.interstationTable.rowCount()
            self.interstationTable.insertRow(row)
            self.interstationTable.setItem(row, 0, QTableWidgetItem(label))
            self.interstationTable.setItem(row, 1, QTableWidgetItem(self.formatDuration(legTime)))
        self.constrainTableHeight(self.interstationTable)

    # Re-render the design speed section only, used by the profile selector
    def onDesignProfileChanged(self, index):
        self.refreshDesignSpeedSection()

    # Re-render the vehicle dependent sections only, used by the vehicle selector
    def onVehicleChanged(self, index):
        self.refreshActualSpeedSection()
        self.refreshTravelTimeSection()

    # Main entry point called whenever alignment, TTP or simulation data changes
    def updateStatistics(self, dataStorage, vehicleNameResolver=None):
        self.lastDataStorage = dataStorage or {}
        self.vehicleNameResolver = vehicleNameResolver
        self.rebuildVehicleCombo()
        self.refreshAll()

    # Refresh every caption, header and cached value after a language change
    def updateTexts(self, lan):
        self.lan = lan or {}

        self.designProfileRowLabel.setText(self.lan.get("statsDesignProfileRow", "Design profile"))
        self.vehicleRowLabel.setText(self.lan.get("statsVehicleRow", "Vehicle"))

        self.lengthCard.setCaption(self.lan.get("statsCardLength", "Total length"))
        self.designMaxCard.setCaption(self.lan.get("statsCardDesignSpeed", "Max design speed"))
        self.actualMaxCard.setCaption(self.lan.get("statsCardActualSpeed", "Max achieved speed"))
        self.totalTimeCard.setCaption(self.lan.get("statsCardTotalTime", "Total travel time"))
        self.originDestCard.setCaption(self.lan.get("statsCardOriginDest", "Origin → Destination"))

        self.designSection.setTitle(self.lan.get("statsSectionDesign", "Design segments"))
        self.actualSection.setTitle(self.lan.get("statsSectionActual", "Achieved segments"))
        self.interstationSection.setTitle(self.lan.get("statsSectionInterstation", "Inter-station times"))

        segmentHeaders = [
            self.lan.get("statsSegmentColumn", "Segment"),
            self.lan.get("statsMaxSpeedColumn", "Max speed [km/h]"),
            self.lan.get("statsChainageColumn", "Chainage [km]"),
        ]
        self.designSegmentTable.setHorizontalHeaderLabels(segmentHeaders)
        self.actualSegmentTable.setHorizontalHeaderLabels(segmentHeaders)
        self.interstationTable.setHorizontalHeaderLabels([
            self.lan.get("statsSegmentColumn", "Segment"),
            self.lan.get("statsTravelTimeColumn", "Travel time [mm:ss]"),
        ])

        self.rebuildVehicleCombo()
        self.refreshAll()

    # Restyle the KPI cards and the tables with the active theme's tokens
    def applyTheme(self, isDark, tokens=None):
        backgroundColor = tokens.get("base", "#ffffff") if tokens else ("#1e1e1e" if isDark else "#ffffff")

        for card in (self.lengthCard, self.designMaxCard, self.actualMaxCard,
                    self.totalTimeCard, self.originDestCard):
            card.applyTheme(isDark, tokens)

        for table in (self.designSegmentTable, self.actualSegmentTable, self.interstationTable):
            table.setAlternatingRowColors(True)
            table.setStyleSheet(f"QTableWidget {{ background: {backgroundColor}; }}")
