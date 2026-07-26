# Vertical alignment plot with gradient annotations and a synchronised crosshair
import numpy as np
import pyqtgraph as pg

from plot_widgets import CoypuPlotWidget

# Vertical offset applied to the gradient captions above the profile line
LABEL_OFFSET = 0.1


class ProfilePlotWidget(CoypuPlotWidget):
    def __init__(self, lan, parent=None):
        super().__init__(lan, parent)

        self.gradientLabels = []

        self.plotProfile = self.addPlotRow("profile", 0)
        self.updateLabels(lan)
        self.enableCursorTracking("profile")
        self.applyTheme(False)

    # Refresh axis labels and the plot caption after a language change
    def updateLabels(self, lan):
        self.lan = lan

        self.plotTitles["profile"] = lan.get("profile", "Profile")
        self.plotProfile.setLabel("left", lan.get("elevation", "Elevation"))
        self.plotProfile.setLabel("bottom", lan.get("station", "Chainage"))

        self.retranslateMenus(lan)

    # Replace the profile curve and its per segment gradient captions
    def updateProfileData(self, lxml, isVisible=True):
        self.clearGradientLabels()
        self.clearPlot("profile")
        if not lxml:
            return

        stationVertical = lxml.get("stationVertical")
        elevation = lxml.get("elevation")
        if not (self.hasData(stationVertical) and self.hasData(elevation)):
            return

        self.setSeriesData("profile", "profile", stationVertical, elevation,
                           name=self.lan.get("profile", "Profile"), symbol="o",
                           isVisible=isVisible)

        slope = lxml.get("slope")
        if isVisible and self.hasData(slope):
            self.drawGradientLabels(stationVertical, elevation, slope)

    # Place one gradient caption at the midpoint of every profile segment
    def drawGradientLabels(self, stationVertical, elevation, slope):
        stations = np.asarray(stationVertical, dtype=float)
        elevations = np.asarray(elevation, dtype=float)
        slopes = np.asarray(slope, dtype=float)

        midStations = (stations[:-1] + stations[1:]) / 2.0
        midElevations = (elevations[:-1] + elevations[1:]) / 2.0
        foreground = self.tokens["plotForeground"] if self.tokens else "#1c1c1c"

        for index in range(min(len(midStations), len(slopes))):
            label = pg.TextItem(f"{slopes[index]:.2f} ‰", anchor=(0.5, 1.0),
                                color=foreground)
            label.setPos(float(midStations[index]), float(midElevations[index]) + LABEL_OFFSET)
            self.plotProfile.addItem(label, ignoreBounds=True)
            self.gradientLabels.append(label)

    # Drop every gradient caption before a redraw or a theme change
    def clearGradientLabels(self):
        for label in self.gradientLabels:
            self.plotProfile.removeItem(label)
        self.gradientLabels = []

    # Recolour the gradient captions along with the rest of the plot
    def applyTheme(self, isDark, tokens=None):
        super().applyTheme(isDark, tokens)

        foreground = tokens["plotForeground"] if tokens else ("#e6e6e6" if isDark else "#1c1c1c")
        for label in self.gradientLabels:
            label.setColor(foreground)

    # Show or hide the profile curve together with its captions
    def setProfileVisible(self, isVisible):
        self.setSeriesVisible("profile", "profile", isVisible)
        for label in self.gradientLabels:
            label.setVisible(bool(isVisible))

    # Guard used before touching any optional array
    def hasData(self, values):
        return values is not None and len(values) > 0

    # Remove the curve and its captions, used by the clean actions
    def clearAll(self):
        self.clearGradientLabels()
        self.clearPlot("profile")
