# Track geometry and speed profile with a linked X axis and a shared crosshair
import numpy as np

from plot_widgets import CoypuPlotWidget

# Cant and cant deficiency curves drawn on the left axis of the geometry plot
GEOMETRY_SERIES = [
    ("cant", "stationCant", "cant", "cant"),
    ("cantPossible", "stationCantPossible", "cantPossible", "cant_possible"),
    ("cDef100", "stationCantPossible", "cDef100", "cdef_100"),
    ("cDef130", "stationCantPossible", "cDef130", "cdef_130"),
    ("cDef150", "stationCantPossible", "cDef150", "cdef_150"),
    ("cDefK", "stationCantPossible", "cDefK", "cdef_K"),
    ("cantDef100", "stationCantPossible", "cantDef100", "cant_def_100"),
    ("cantDef130", "stationCantPossible", "cantDef130", "cant_def_130"),
    ("cantDef150", "stationCantPossible", "cantDef150", "cant_def_150"),
    ("cantDefK", "stationCantPossible", "cantDefK", "cant_def_K"),
]

# Curvature curves drawn on the secondary right axis of the geometry plot
CURVATURE_SERIES = [
    ("curvature", "stationHorizontal", "curvature", "curvature"),
    ("curvatureNew", "stationHorizontalNew", "curvatureNew", "curvature_new"),
]

# Speed limit step curves drawn on the lower plot
SPEED_SERIES = [
    ("speedLimits", "stationSpeedLimits", "speedLimits", "speed_lim"),
    ("speedLimits100", "stationSpeed100", "speedLimits100", "speed_lim_100"),
    ("speedLimits130", "stationSpeed130", "speedLimits130", "speed_lim_130"),
    ("speedLimits150", "stationSpeed150", "speedLimits150", "speed_lim_150"),
    ("speedLimitsK", "stationSpeedK", "speedLimitsK", "speed_lim_K"),
]

# Fixed vertical range of the cant axis, matching the previous alignment plot
CANT_RANGE = 500.0

# Extra headroom above the fastest speed curve so the top line stays readable
SPEED_RANGE_HEADROOM = 1.05


class PerformanceGraphsWidget(CoypuPlotWidget):
    def __init__(self, lan, parent=None):
        super().__init__(lan, parent)

        self.plotGeometry = self.addPlotRow("geometry", 0, rightAxis="fraction")
        self.plotSpeed = self.addPlotRow("speed", 1)

        self.addRightAxis("geometry")

        # Linking the bottom axis to the top one keeps both plots in step
        self.plotSpeed.setXLink(self.plotGeometry)

        self.plotGeometry.vb.setYRange(-CANT_RANGE, CANT_RANGE, padding=0)

        self.updateLabels(lan)
        self.enableCursorTracking("geometry")
        self.applyTheme(False)

    # Refresh axis labels and plot captions after a language change
    def updateLabels(self, lan):
        self.lan = lan

        self.plotTitles["geometry"] = lan.get("dockGeometryPlot", "Track geometry")
        self.plotTitles["speed"] = lan.get("dockSpeedPlot", "Speed profile")

        self.plotGeometry.setLabel("left", lan.get("cant", "Cant"))
        self.plotGeometry.setLabel("right", lan.get("curvature", "Curvature"))
        self.plotGeometry.setLabel("bottom", lan.get("station", "Chainage"))
        self.plotSpeed.setLabel("left", lan.get("speed_lim", "Speed"))
        self.plotSpeed.setLabel("bottom", lan.get("station", "Chainage"))

        self.retranslateMenus(lan)

    # Replace the geometry curves from the LandXML dictionary
    def updateGeometryData(self, lxml, visibility=None):
        self.clearPlot("geometry")
        if not lxml:
            return

        visibility = visibility or {}

        # Geometry chainage arrays are already stored in kilometres by the parser
        for seriesKey, stationKey, valueKey, labelKey in GEOMETRY_SERIES:
            stations = lxml.get(stationKey)
            values = lxml.get(valueKey)
            if not (self.hasData(stations) and self.hasData(values)):
                continue
            self.setSeriesData("geometry", seriesKey, stations, values,
                               name=self.lan.get(labelKey, labelKey), symbol="o",
                               isVisible=visibility.get(seriesKey, True))

        for seriesKey, stationKey, valueKey, labelKey in CURVATURE_SERIES:
            stations = lxml.get(stationKey)
            values = lxml.get(valueKey)
            if not (self.hasData(stations) and self.hasData(values)):
                continue
            self.setSeriesData("geometry", seriesKey, stations, values,
                               name=self.lan.get(labelKey, labelKey), onRight=True,
                               isVisible=visibility.get(seriesKey, True))

        self.plotGeometry.vb.setYRange(-CANT_RANGE, CANT_RANGE, padding=0)
        self.applySymmetricCurvature()

    # Centre the curvature axis on zero so it lines up with the cant axis
    def applySymmetricCurvature(self):
        peak = 1e-9
        for entry in self.plotSeries.get("geometry", {}).values():
            if not entry["onRight"] or entry["y"].size == 0:
                continue
            finiteValues = entry["y"][np.isfinite(entry["y"])]
            if finiteValues.size:
                peak = max(peak, float(np.max(np.abs(finiteValues))))

        rightView = self.plotRightViews.get("geometry")
        if rightView is not None:
            rightView.setYRange(-peak, peak, padding=0.05)

    # Replace the speed curves from the main data storage dictionary
    def updateSpeedData(self, dataStorage, visibility=None):
        self.clearPlot("speed")
        if not dataStorage:
            return

        visibility = visibility or {}

        # Speed profile chainage arrays are already stored in kilometres
        for seriesKey, stationKey, valueKey, labelKey in SPEED_SERIES:
            stations = dataStorage.get(stationKey)
            speeds = dataStorage.get(valueKey)
            if not (self.hasData(stations) and self.hasData(speeds)):
                continue
            self.setSeriesData("speed", seriesKey, stations, speeds,
                               name=self.lan.get(labelKey, labelKey), step=True, symbol="s",
                               isVisible=visibility.get(seriesKey, True))

        # Overlay the simulated running speed of every calculated vehicle
        vehicleCount = dataStorage.get("num_vehicles", 1)
        for vehicleIndex in range(vehicleCount):
            simulatedStations = dataStorage.get(f"kinematicsStationM_{vehicleIndex}")
            simulatedSpeeds = dataStorage.get(f"kinematicsSpeedM_{vehicleIndex}")
            if not (self.hasData(simulatedStations) and self.hasData(simulatedSpeeds)):
                continue

            # Kinematics arrays are stored in metres and metres per second
            self.setSeriesData(
                "speed", f"simulated{vehicleIndex}",
                np.asarray(simulatedStations, dtype=float) / 1000.0,
                np.asarray(simulatedSpeeds, dtype=float) * 3.6,
                styleKey="simulated",
                name=f"{self.lan.get('speedKmh', 'Speed')} V{vehicleIndex + 1}")

        self.applyFullSpeedRange()

    # Show the speed axis from standstill up to the fastest curve on the plot
    def applyFullSpeedRange(self):
        peak = 0.0
        for entry in self.plotSeries.get("speed", {}).values():
            if entry["y"].size == 0:
                continue
            finiteValues = entry["y"][np.isfinite(entry["y"])]
            if finiteValues.size:
                peak = max(peak, float(np.max(finiteValues)))

        if peak <= 0.0:
            self.plotSpeed.vb.enableAutoRange(axis="y")
            return

        self.plotSpeed.vb.setYRange(0.0, peak * SPEED_RANGE_HEADROOM, padding=0)

    # Guard used before touching any optional array
    def hasData(self, values):
        return values is not None and len(values) > 0

    # Remove every curve, used by the clean actions
    def clearAll(self):
        self.clearPlot("geometry")
        self.clearPlot("speed")
