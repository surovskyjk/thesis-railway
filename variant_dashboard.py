# Third central view: overlaid variant plots and side-by-side comparison tables
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QListWidget, QListWidgetItem, QLabel

from plot_widgets import CoypuPlotWidget
import batch_metrics


class VariantOverlayPlotWidget(CoypuPlotWidget):
    def __init__(self, lan, parent=None):
        super().__init__(lan, parent)
        self.plotSpeed = self.addPlotRow("speed", 0)
        self.plotCantDef = self.addPlotRow("cantDef", 1)
        self.plotCantDef.setXLink(self.plotSpeed)
        self.updateLabels(lan)
        self.enableCursorTracking("speed")
        self.applyTheme(False)

    def updateLabels(self, lan):
        self.plotSpeed.setLabel("left", lan.get("dashboardSpeedPlot", "Speed profile v(s)"))
        self.plotCantDef.setLabel("left", lan.get("dashboardCantDefPlot", "Cant deficiency I(s)"))
        self.plotCantDef.setLabel("bottom", lan.get("statsChainageColumn", "Chainage [km]"))
        self.retranslateMenus(lan)

    def hasData(self, values):
        return batch_metrics.hasData(values)

    def clearAll(self):
        self.clearPlot("speed")
        self.clearPlot("cantDef")

    # Overlay every visible, successfully calculated variant's speed and cant deficiency curves
    def setVariantSeries(self, resultStore, visibleIds):
        self.clearAll()
        for result in resultStore.results():
            if result["variantId"] not in visibleIds or result["status"] != "ok":
                continue
            series = result.get("seriesForPlot", {})
            stationKm = series.get("stationKm")
            speedProfile = series.get("speedProfile")
            cantDeficiency = series.get("cantDeficiency")
            color = resultStore.colorFor(result["variantId"])
            label = result.get("spec", {}).get("label", result["variantId"])
            if self.hasData(stationKm) and self.hasData(speedProfile):
                self.setSeriesData("speed", result["variantId"], stationKm, speedProfile, name=label, color=color)
            if self.hasData(stationKm) and self.hasData(cantDeficiency):
                self.setSeriesData("cantDef", result["variantId"], stationKm, cantDeficiency, name=label, color=color)


class VariantDashboardWidget(QWidget):
    cursorMoved = Signal(float)

    def __init__(self, lan, parent=None):
        super().__init__(parent)
        self.lan = lan or {}
        self.resultStore = None

        rootLayout = QHBoxLayout(self)
        rootLayout.setContentsMargins(4, 4, 4, 4)
        rootLayout.setSpacing(4)

        self.variantList = QListWidget()
        self.variantList.setMaximumWidth(260)
        self.variantList.itemChanged.connect(self.onVariantVisibilityChanged)
        rootLayout.addWidget(self.variantList)

        rightSplitter = QSplitter(Qt.Orientation.Vertical)
        rootLayout.addWidget(rightSplitter, 1)

        self.overlayPlot = VariantOverlayPlotWidget(self.lan)
        self.overlayPlot.cursorMoved.connect(self.cursorMoved)
        rightSplitter.addWidget(self.overlayPlot)

        tablesWidget = QWidget()
        tablesLayout = QVBoxLayout(tablesWidget)
        tablesLayout.setContentsMargins(0, 0, 0, 0)
        tablesLayout.setSpacing(2)

        self.summaryLabel = QLabel()
        tablesLayout.addWidget(self.summaryLabel)
        self.summaryTable = pg.TableWidget(sortable=False)
        tablesLayout.addWidget(self.summaryTable, 1)

        self.interstationLabel = QLabel()
        tablesLayout.addWidget(self.interstationLabel)
        self.interstationTable = pg.TableWidget(sortable=False)
        tablesLayout.addWidget(self.interstationTable, 1)

        rightSplitter.addWidget(tablesWidget)
        rightSplitter.setStretchFactor(0, 2)
        rightSplitter.setStretchFactor(1, 1)

        self.updateLabels(self.lan)

    def updateLabels(self, lan):
        self.lan = lan or {}
        self.summaryLabel.setText(self.lan.get("dashboardSummary", "Summary"))
        self.interstationLabel.setText(self.lan.get("dashboardInterstation", "Inter-station travel times"))
        self.overlayPlot.updateLabels(self.lan)
        if self.resultStore is None or self.resultStore.isEmpty():
            self.variantList.clear()
            self.variantList.addItem(self.lan.get("dashboardNoResults", "No batch results yet"))

    def applyTheme(self, isDark, tokens=None):
        self.overlayPlot.applyTheme(isDark, tokens)

    def setCursorStation(self, stationKm):
        self.overlayPlot.setCursorStation(stationKm)

    def clearAll(self):
        self.resultStore = None
        self.variantList.clear()
        self.variantList.addItem(self.lan.get("dashboardNoResults", "No batch results yet"))
        self.overlayPlot.clearAll()
        self.summaryTable.setData({})
        self.interstationTable.setData({})

    def selectedVariantIds(self):
        variantIds = []
        for row in range(self.variantList.count()):
            item = self.variantList.item(row)
            if item.data(Qt.ItemDataRole.UserRole) is not None and item.checkState() == Qt.CheckState.Checked:
                variantIds.append(item.data(Qt.ItemDataRole.UserRole))
        return variantIds

    def setResults(self, resultStore):
        self.resultStore = resultStore
        self.refreshVariantList()
        self.refreshPlots()
        self.refreshTables()

    def refreshVariantList(self):
        self.variantList.blockSignals(True)
        self.variantList.clear()
        if self.resultStore is not None:
            for result in self.resultStore.results():
                label = result.get("spec", {}).get("label", result["variantId"])
                statusSuffix = "" if result["status"] == "ok" else f" [{result['status']}]"
                item = QListWidgetItem(f"{label}{statusSuffix}")
                item.setData(Qt.ItemDataRole.UserRole, result["variantId"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(Qt.CheckState.Checked if result["status"] == "ok" else Qt.CheckState.Unchecked)
                item.setForeground(QColor(self.resultStore.colorFor(result["variantId"])))
                if result["status"] != "ok":
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.variantList.addItem(item)
        self.variantList.blockSignals(False)

    def onVariantVisibilityChanged(self, item):
        self.refreshPlots()

    def refreshPlots(self):
        if self.resultStore is None:
            self.overlayPlot.clearAll()
            return
        self.overlayPlot.setVariantSeries(self.resultStore, set(self.selectedVariantIds()))

    def refreshTables(self):
        if self.resultStore is None:
            return
        self.buildSummaryTable()
        self.buildInterstationTable()

    def buildSummaryTable(self):
        variantColumn = self.lan.get("dashboardVariants", "Variants")
        rows = []
        for result in self.resultStore.results():
            label = result.get("spec", {}).get("label", result["variantId"])
            if result["status"] != "ok":
                rows.append({variantColumn: f"{label} [{result['status']}]"})
                continue
            metrics = result.get("metrics", {})
            rows.append({
                variantColumn: label,
                self.lan.get("statsCardDesignSpeed", "Max design speed"): self.formatSpeed(metrics.get("maxSpeedDesignKmh")),
                self.lan.get("statsCardActualSpeed", "Max achieved speed"): self.formatSpeed(metrics.get("maxSpeedActualKmh")),
                self.lan.get("statsCardTotalTime", "Total travel time"): batch_metrics.formatDuration(metrics.get("totalTimeS")),
                "Max I [mm]": self.formatNumber(metrics.get("maxCantDefMm")),
                "Max D [mm]": self.formatNumber(metrics.get("maxCantMm")),
                "Max slew [m]": self.formatNumber(metrics.get("maxSlewM")),
            })
        self.summaryTable.setData(rows)

    def buildInterstationTable(self):
        legLabelsInOrder = []
        seenLabels = set()
        variantColumns = []
        perVariantLegTimes = {}
        for result in self.resultStore.results():
            if result["status"] != "ok":
                continue
            label = result.get("spec", {}).get("label", result["variantId"])
            variantColumns.append(label)
            legMap = dict(result.get("metrics", {}).get("interstationRows", []))
            perVariantLegTimes[label] = legMap
            for legLabel in legMap:
                if legLabel not in seenLabels:
                    seenLabels.add(legLabel)
                    legLabelsInOrder.append(legLabel)

        legColumn = self.lan.get("statsSegmentColumn", "Segment")
        rows = []
        for legLabel in legLabelsInOrder:
            row = {legColumn: legLabel}
            for variantLabel in variantColumns:
                row[variantLabel] = batch_metrics.formatDuration(perVariantLegTimes[variantLabel].get(legLabel))
            rows.append(row)
        self.interstationTable.setData(rows)

    def formatSpeed(self, value):
        return f"{value:.0f} km/h" if value is not None else "-"

    def formatNumber(self, value):
        return f"{value:.0f}" if value is not None else "-"

    # Export the overlay panels to the given directory, returns the list of files written
    def exportPlotImages(self, directoryPath, formats):
        basePath = Path(directoryPath)
        exportedPaths = []
        if "png" in formats:
            speedPath, cantDefPath = basePath / "overlaySpeed.png", basePath / "overlayCantDeficiency.png"
            self.overlayPlot.exportPlotItemImage("speed", str(speedPath))
            self.overlayPlot.exportPlotItemImage("cantDef", str(cantDefPath))
            exportedPaths += [str(speedPath), str(cantDefPath)]
        if "svg" in formats:
            speedPath, cantDefPath = basePath / "overlaySpeed.svg", basePath / "overlayCantDeficiency.svg"
            self.overlayPlot.exportPlotItemVector("speed", str(speedPath))
            self.overlayPlot.exportPlotItemVector("cantDef", str(cantDefPath))
            exportedPaths += [str(speedPath), str(cantDefPath)]
        return exportedPaths
