import io
import json
import folium
from folium import DivIcon
from folium.features import ColorLine
import math
from PySide6.QtCore import QFile, QIODevice, QObject, Qt, QUrl, Signal, Slot
from PySide6.QtWidgets import (QComboBox, QFrame, QHBoxLayout, QLabel, QPushButton,
                               QSlider, QWidget, QVBoxLayout)
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtWebChannel import QWebChannel
import numpy as np
import branca.colormap as bcm

import icons
from geometry_engine import SLEW_VISIBLE_THRESHOLD_MM
from ribbon import SERIES_TOGGLE_PROPERTY

# Maximum number of alignment samples handed to the page for nearest point lookup
MAX_LOOKUP_POINTS = 2000

# Width and opacity of the heat line marking the sections that actually moved
SLEW_INDICATOR_WEIGHT = 7
SLEW_INDICATOR_OPACITY = 0.55

# Base maps offered by the overlay selector, the value is stored in currentBaseMap
BASEMAP_CHOICES = [
    ("positron", "mapPositron", "CartoDB Positron"),
    ("osm", "mapOSM", "OpenStreetMap"),
    ("cuzk", "mapCUZK", "CUZK orthophoto"),
    ("cartodbDark", "mapCartoDark", "CartoDB Dark"),
]

# Alignment rendering styles offered by the style selector
DRAW_MODE_SINGLE = "single"
DRAW_MODE_SPEED = "speed"
DRAW_MODE_TYPE = "type"

# Alignment style combo entries, the value is emitted by drawModeChanged
DRAW_MODE_CHOICES = [
    (DRAW_MODE_SINGLE, "mapDrawSingleColor", "Single Color"),
    (DRAW_MODE_TYPE, "mapDrawByType", "By Element Type"),
    (DRAW_MODE_SPEED, "mapDrawBySpeed", "By Speed Limit"),
]

# Offset of the floating control panel, chosen to clear the Leaflet zoom buttons
CONTROL_PANEL_MARGIN = 10
CONTROL_PANEL_TOP = 88

# Injected into every rendered map so the chainage crosshair works in both directions
CURSOR_SCRIPT_TEMPLATE = """
<script>{webChannelSource}</script>
<script>
window.coypuCursorMarker = null;
window.coypuBridge = null;
window.coypuPoints = {lookupPoints};
window.coypuLabels = {slewLabels};
window.coypuTooltip = null;
window.coypuLastSent = 0;

// Railway style chainage caption, 12.345 km becomes km 12+345
window.coypuFormatChainage = function (stationKm) {{
    var whole = Math.floor(stationKm);
    var metres = (stationKm - whole) * 1000.0;
    return 'km ' + whole + '+' + ('00' + metres.toFixed(0)).slice(-3);
}};

window.coypuHideTooltip = function () {{
    if (window.coypuTooltip !== null) {{ window.coypuTooltip.style.display = 'none'; }}
}};

// Show chainage, lateral slew and the radius change of the curve group under the cursor
window.coypuUpdateTooltip = function (event, point) {{
    if (point.length < 4 || point[3] === null) {{ window.coypuHideTooltip(); return; }}

    if (window.coypuTooltip === null) {{
        window.coypuTooltip = document.createElement('div');
        window.coypuTooltip.style.cssText = 'position:fixed;z-index:10000;pointer-events:none;' +
            'padding:3px 7px;border-radius:3px;font:11px sans-serif;white-space:nowrap;' +
            'background:rgba(30,30,30,0.88);color:#ffffff;';
        document.body.appendChild(window.coypuTooltip);
    }}

    var text = window.coypuFormatChainage(point[0]) +
               ' | ' + window.coypuLabels.slew + ': ' + point[3].toFixed(0) + ' mm';
    if (point.length > 5 && point[4] !== null && point[5] !== null) {{
        text += ' | R ' + point[4].toFixed(0) + ' \u2192 ' + point[5].toFixed(0) + ' m';
    }}

    window.coypuTooltip.textContent = text;
    window.coypuTooltip.style.display = 'block';
    window.coypuTooltip.style.left = (event.originalEvent.clientX + 14) + 'px';
    window.coypuTooltip.style.top = (event.originalEvent.clientY + 14) + 'px';
}};

window.setTrackCursor = function (lat, lon) {{
    var mapObject = {mapName};
    if (!mapObject) {{ return; }}
    if (window.coypuCursorMarker === null) {{
        window.coypuCursorMarker = L.circleMarker([lat, lon], {{
            radius: 7, color: '#2f6fb5', weight: 3,
            fillColor: '#ffffff', fillOpacity: 1.0
        }}).addTo(mapObject);
    }} else {{
        window.coypuCursorMarker.setLatLng([lat, lon]);
    }}
}};

// Report the chainage of the alignment point nearest to the mouse back to Qt
window.coypuReportNearest = function (event) {{
    if (window.coypuPoints.length === 0) {{ return; }}
    var now = Date.now();
    if (now - window.coypuLastSent < 50) {{ return; }}
    window.coypuLastSent = now;

    var latlng = event.latlng;
    var scale = Math.cos(latlng.lat * Math.PI / 180.0);
    var bestIndex = -1;
    var bestDistance = Infinity;
    for (var i = 0; i < window.coypuPoints.length; i++) {{
        var dLat = window.coypuPoints[i][1] - latlng.lat;
        var dLon = (window.coypuPoints[i][2] - latlng.lng) * scale;
        var distance = dLat * dLat + dLon * dLon;
        if (distance < bestDistance) {{ bestDistance = distance; bestIndex = i; }}
    }}
    if (bestIndex < 0) {{ return; }}

    if (window.coypuBridge) {{
        window.coypuBridge.reportChainage(window.coypuPoints[bestIndex][0]);
    }}
    window.coypuUpdateTooltip(event, window.coypuPoints[bestIndex]);
}};

if (typeof qt !== 'undefined' && qt.webChannelTransport) {{
    new QWebChannel(qt.webChannelTransport, function (channel) {{
        window.coypuBridge = channel.objects.coypuBridge;
    }});
}}

{mapName}.on('mousemove', function (event) {{ window.coypuReportNearest(event); }});
{mapName}.on('mouseout', function () {{ window.coypuHideTooltip(); }});

// Report the camera back to Qt so the viewport survives a project save and reload
{mapName}.on('moveend', function () {{
    if (!window.coypuBridge) {{ return; }}
    var center = {mapName}.getCenter();
    window.coypuBridge.reportViewState(center.lat, center.lng, {mapName}.getZoom());
}});
</script>
"""


class MapControlsPanel(QFrame):
    # Emitted with the identifier of the newly selected base map
    baseMapChanged = Signal(str)

    # Emitted with the enabled flag and the opacity fraction of the rail overlay
    railOverlayChanged = Signal(bool, float)

    # Emitted with the alignment rendering style identifier
    drawModeChanged = Signal(str)

    # Emitted when the station marker toggle is switched
    stationsToggled = Signal(bool)

    def __init__(self, lan, parent=None):
        super().__init__(parent)

        self.lan = lan or {}
        self.setObjectName("mapControlsPanel")
        self.setFrameShape(QFrame.Shape.StyledPanel)

        panelLayout = QVBoxLayout(self)
        panelLayout.setContentsMargins(6, 6, 6, 6)
        panelLayout.setSpacing(4)

        self.baseMapCombo = QComboBox()
        for baseMapKey, languageKey, fallbackName in BASEMAP_CHOICES:
            self.baseMapCombo.addItem(self.lan.get(languageKey, fallbackName), baseMapKey)
        self.baseMapCombo.currentIndexChanged.connect(self.onBaseMapSelected)
        panelLayout.addWidget(self.baseMapCombo)

        overlayRow = QWidget()
        overlayLayout = QHBoxLayout(overlayRow)
        overlayLayout.setContentsMargins(0, 0, 0, 0)
        overlayLayout.setSpacing(4)

        self.railOverlayButton = QPushButton()
        self.railOverlayButton.setCheckable(True)
        self.railOverlayButton.setIcon(icons.makeIcon("railway"))
        self.railOverlayButton.setProperty(SERIES_TOGGLE_PROPERTY, True)
        self.railOverlayButton.toggled.connect(self.onRailOverlayToggled)
        overlayLayout.addWidget(self.railOverlayButton)

        self.railOpacitySlider = QSlider(Qt.Orientation.Horizontal)
        self.railOpacitySlider.setRange(10, 100)
        self.railOpacitySlider.setValue(70)
        self.railOpacitySlider.setFixedWidth(70)
        self.railOpacitySlider.setEnabled(False)
        self.railOpacitySlider.sliderReleased.connect(self.onRailOpacityChanged)
        overlayLayout.addWidget(self.railOpacitySlider)

        panelLayout.addWidget(overlayRow)

        self.alignmentStyleCombo = QComboBox()
        for drawModeKey, languageKey, fallbackName in DRAW_MODE_CHOICES:
            self.alignmentStyleCombo.addItem(self.lan.get(languageKey, fallbackName), drawModeKey)
        self.alignmentStyleCombo.currentIndexChanged.connect(self.onAlignmentStyleSelected)
        panelLayout.addWidget(self.alignmentStyleCombo)

        self.stationsButton = QPushButton()
        self.stationsButton.setCheckable(True)
        self.stationsButton.setChecked(True)
        self.stationsButton.setIcon(icons.makeIcon("station"))
        self.stationsButton.setProperty(SERIES_TOGGLE_PROPERTY, True)
        self.stationsButton.toggled.connect(self.stationsToggled)
        panelLayout.addWidget(self.stationsButton)

        self.currentDrawMode = DRAW_MODE_SPEED
        self.updateTexts(self.lan)

    # Report the base map the user picked from the combo box
    def onBaseMapSelected(self, index):
        self.baseMapChanged.emit(self.baseMapCombo.itemData(index))

    # Enable the opacity slider together with the rail overlay itself
    def onRailOverlayToggled(self, isChecked):
        self.railOpacitySlider.setEnabled(isChecked)
        self.railOverlayChanged.emit(isChecked, self.railOpacitySlider.value() / 100.0)

    # Report a new overlay opacity once the slider is released
    def onRailOpacityChanged(self):
        if self.railOverlayButton.isChecked():
            self.railOverlayChanged.emit(True, self.railOpacitySlider.value() / 100.0)

    # Report the alignment rendering style the user picked from the combo box
    def onAlignmentStyleSelected(self, index):
        self.currentDrawMode = self.alignmentStyleCombo.itemData(index)
        self.drawModeChanged.emit(self.currentDrawMode)

    # Adopt the state owned by the map widget without re-emitting signals
    def syncState(self, baseMap, drawMode, railEnabled, railOpacity, showStations):
        for controlWidget in (self.baseMapCombo, self.railOverlayButton,
                              self.alignmentStyleCombo, self.stationsButton):
            controlWidget.blockSignals(True)

        comboIndex = self.baseMapCombo.findData(baseMap)
        if comboIndex >= 0:
            self.baseMapCombo.setCurrentIndex(comboIndex)

        validModes = (DRAW_MODE_SINGLE, DRAW_MODE_TYPE, DRAW_MODE_SPEED)
        self.currentDrawMode = drawMode if drawMode in validModes else DRAW_MODE_SPEED
        styleIndex = self.alignmentStyleCombo.findData(self.currentDrawMode)
        if styleIndex >= 0:
            self.alignmentStyleCombo.setCurrentIndex(styleIndex)
        self.railOverlayButton.setChecked(bool(railEnabled))
        self.railOpacitySlider.setEnabled(bool(railEnabled))
        self.railOpacitySlider.setValue(int(round(railOpacity * 100)))
        self.stationsButton.setChecked(bool(showStations))

        for controlWidget in (self.baseMapCombo, self.railOverlayButton,
                              self.alignmentStyleCombo, self.stationsButton):
            controlWidget.blockSignals(False)

    # Refresh every caption after a language change
    def updateTexts(self, lan):
        self.lan = lan or {}

        self.baseMapCombo.blockSignals(True)
        for itemIndex, (baseMapKey, languageKey, fallbackName) in enumerate(BASEMAP_CHOICES):
            self.baseMapCombo.setItemText(itemIndex, self.lan.get(languageKey, fallbackName))
        self.baseMapCombo.blockSignals(False)

        self.alignmentStyleCombo.blockSignals(True)
        for itemIndex, (drawModeKey, languageKey, fallbackName) in enumerate(DRAW_MODE_CHOICES):
            self.alignmentStyleCombo.setItemText(itemIndex, self.lan.get(languageKey, fallbackName))
        self.alignmentStyleCombo.blockSignals(False)

        self.baseMapCombo.setToolTip(self.lan.get("mapBasemap", "Base map"))
        self.railOverlayButton.setText(self.lan.get("mapRailOverlay", "Railways"))
        self.railOverlayButton.setToolTip(self.lan.get("mapRailOverlayTip",
                                                       "Toggle the OpenRailwayMap overlay"))
        self.railOpacitySlider.setToolTip(self.lan.get("mapRailOpacity", "Overlay transparency"))
        self.stationsButton.setText(self.lan.get("mapShowStations", "Stations"))
        self.alignmentStyleCombo.setToolTip(self.lan.get("mapAlignmentStyle", "Alignment style"))

    # Rebuild the icons so they follow the active theme colours
    def applyTheme(self, isDark, tokens=None):
        self.railOverlayButton.setIcon(icons.makeIcon("railway"))
        self.stationsButton.setIcon(icons.makeIcon("station"))

        background = "rgba(43, 43, 43, 235)" if isDark else "rgba(255, 255, 255, 235)"
        border = tokens["border"] if tokens else "#999999"
        self.setStyleSheet(f"#mapControlsPanel {{ background: {background};"
                           f" border: 1px solid {border}; border-radius: 4px; }}")


class MapBridge(QObject):
    # Emitted with the chainage in kilometres reported by the page
    chainageReported = Signal(float)

    # Emitted with the map centre and zoom level after every pan or zoom
    viewStateReported = Signal(float, float, int)

    # Invoked from JavaScript through the web channel on every throttled mouse move
    @Slot(float)
    def reportChainage(self, stationKm):
        self.chainageReported.emit(float(stationKm))

    # Invoked from JavaScript once the Leaflet camera settles after a pan or zoom
    @Slot(float, float, int)
    def reportViewState(self, centerLat, centerLon, zoomLevel):
        self.viewStateReported.emit(float(centerLat), float(centerLon), int(zoomLevel))

class MapWidget(QWidget):
    # Emitted with the chainage in kilometres when the alignment is hovered on the map
    cursorMoved = Signal(float)

    def __init__(self, parent=None, lan=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.mapBrowser = QWebEngineView()
        self.layout.addWidget(self.mapBrowser)
        self.currentBaseMap = "positron"
        self.drawMode = "single"
        self.speedProfile = "150"
        self.alignment = []
        self.lxml = None
        self.denseAlignment = []
        self.denseStations = []
        self.stationList = []
        self.showStations = True
        self.railOverlayEnabled = False
        self.railOverlayOpacity = 0.7
        self.isMapReady = False
        self.wasDarkTheme = False
        self.lan = lan or {}
        self.themeTokens = None
        # Live Leaflet camera, restored from a project file or reported back by the page
        self.viewCenterLat = None
        self.viewCenterLon = None
        self.viewZoom = None
        self.mapBrowser.loadFinished.connect(self.onMapLoadFinished)

        # Floating Qt controls sit above the web view and survive every page reload
        self.controlsPanel = MapControlsPanel(lan or {}, self)
        self.controlsPanel.baseMapChanged.connect(self.setBaseMap)
        self.controlsPanel.railOverlayChanged.connect(self.setRailOverlay)
        self.controlsPanel.drawModeChanged.connect(self.setDrawMode)
        self.controlsPanel.stationsToggled.connect(self.setStationsVisible)
        self.controlsPanel.applyTheme(False)

        # The bridge lets the page report the chainage under the mouse back to Qt
        self.bridge = MapBridge(self)
        self.bridge.chainageReported.connect(self.cursorMoved)
        self.bridge.viewStateReported.connect(self.onViewStateReported)
        self.webChannel = QWebChannel(self)
        self.webChannel.registerObject("coypuBridge", self.bridge)
        self.mapBrowser.page().setWebChannel(self.webChannel)

        self.webChannelSource = self.readWebChannelSource()
        self.resetMap()

    # Read the Qt supplied qwebchannel.js so the page needs no external request
    def readWebChannelSource(self):
        resource = QFile(":/qtwebchannel/qwebchannel.js")
        if not resource.open(QIODevice.OpenModeFlag.ReadOnly):
            return ""
        source = bytes(resource.readAll()).decode("utf-8", errors="replace")
        resource.close()
        return source

    def setDrawOptions(self, drawMode, speedProfile):
        self.drawMode = drawMode
        self.speedProfile = speedProfile
        self.syncControlsPanel()
        self.redraw()

    # Switch the alignment rendering style from the floating quick toggle
    def setDrawMode(self, drawMode):
        self.drawMode = drawMode
        self.redraw()

    def setBaseMap(self, baseMap):
        # The dedicated rail overlay replaced the former combined orm base map
        if baseMap == "orm":
            self.railOverlayEnabled = True
            baseMap = "osm"

        self.currentBaseMap = baseMap
        self.syncControlsPanel()
        self.redraw()

    # Enable or disable the OpenRailwayMap overlay and set its transparency
    def setRailOverlay(self, isEnabled, opacity=None):
        self.railOverlayEnabled = bool(isEnabled)
        if opacity is not None:
            self.railOverlayOpacity = float(opacity)
        self.redraw()

    # Show or hide the station and stop markers on the map
    def setStationsVisible(self, isVisible):
        self.showStations = bool(isVisible)
        self.redraw()

    # Remember the camera the page just settled on, no redraw is needed for a pure pan or zoom
    def onViewStateReported(self, centerLat, centerLon, zoomLevel):
        self.viewCenterLat = centerLat
        self.viewCenterLon = centerLon
        self.viewZoom = zoomLevel

    # Current map camera as a (lat, lon, zoom) triple, all None while the map was never moved
    def getViewState(self):
        return self.viewCenterLat, self.viewCenterLon, self.viewZoom

    # Restore a previously saved camera, any missing component falls back to the computed view
    def setViewState(self, centerLat, centerLon, zoomLevel):
        if centerLat is None or centerLon is None or zoomLevel is None:
            return
        self.viewCenterLat = float(centerLat)
        self.viewCenterLon = float(centerLon)
        self.viewZoom = int(zoomLevel)

    # Forget the saved camera so the next draw re-frames the alignment
    def clearViewState(self):
        self.viewCenterLat = None
        self.viewCenterLon = None
        self.viewZoom = None

    # Build the folium map on the saved camera when there is one, otherwise on the computed view
    def buildMap(self, centerLat, centerLon, zoomStart):
        if self.viewCenterLat is not None and self.viewZoom is not None:
            return folium.Map(location=[self.viewCenterLat, self.viewCenterLon],
                              zoom_start=self.viewZoom, tiles=None)
        return folium.Map(location=[centerLat, centerLon], zoom_start=zoomStart, tiles=None)

    # Store the scheduled stops so they can be placed along the alignment
    def setStations(self, stations):
        self.stationList = list(stations or [])
        self.redraw()

    # Redraw the alignment when there is data, otherwise show the empty map
    def redraw(self):
        if len(self.alignment) >= 2:
            self.drawAlignment(self.alignment, self.lxml)
        else:
            self.resetMap()

    # Push the current state into the floating controls without emitting signals
    def syncControlsPanel(self):
        self.controlsPanel.syncState(self.currentBaseMap, self.drawMode,
                                     self.railOverlayEnabled, self.railOverlayOpacity,
                                     self.showStations)

    # Keep the floating controls pinned below the Leaflet zoom buttons
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.controlsPanel.adjustSize()
        self.controlsPanel.move(CONTROL_PANEL_MARGIN, CONTROL_PANEL_TOP)
        self.controlsPanel.raise_()

    # Refresh the floating control captions after a language change
    def updateTexts(self, lan):
        self.lan = lan or {}
        self.controlsPanel.updateTexts(lan)

    # Restyle the floating controls when the application theme changes, and default
    # to the dark basemap the first time the app switches into dark mode
    def applyTheme(self, isDark, tokens=None):
        if isDark and not self.wasDarkTheme and self.currentBaseMap != "cartodbDark":
            self.setBaseMap("cartodbDark")
        self.wasDarkTheme = isDark
        self.themeTokens = tokens
        self.controlsPanel.applyTheme(isDark, tokens)

    def addTiles(self, m):
        if self.currentBaseMap == "cuzk":
            folium.WmsTileLayer(
                url="https://ags.cuzk.gov.cz/arcgis1/services/ORTOFOTO/MapServer/WMSServer",
                layers="0",
                name="ČÚZK Ortofoto",
                fmt="image/jpeg",
                transparent=False,
                attr="© ČÚZK",
                overlay=False
            ).add_to(m)
        elif self.currentBaseMap == "osm":
            folium.TileLayer("OpenStreetMap").add_to(m)
        elif self.currentBaseMap == "cartodbDark":
            folium.TileLayer("CartoDB dark_matter").add_to(m)
        else:
            folium.TileLayer("CartoDB Positron").add_to(m)

        # The railway overlay is independent of the chosen base map
        if self.railOverlayEnabled:
            folium.TileLayer(
                tiles='https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
                attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> | Style: &copy; <a href="https://www.openrailwaymap.org/">OpenRailwayMap</a>',
                name='OpenRailwayMap',
                subdomains='abc',
                overlay=True,
                transparent=True,
                opacity=self.railOverlayOpacity,
                max_zoom=19,
                show=True
            ).add_to(m)

    # Place one interactive marker per imported station or stop
    def addStationMarkers(self, m):
        if not self.showStations or not self.stationList or len(self.denseAlignment) < 2:
            return

        for stationKm, stationName in self.stationList:
            position = self.interpolatePosition(stationKm)
            if position is None:
                continue

            latitude, longitude = position
            caption = stationName or f"{float(stationKm):.3f} km"
            folium.CircleMarker(
                [latitude, longitude], radius=6, color="#1a3d7c", weight=2,
                fill=True, fill_color="#ffffff", fill_opacity=1.0,
                tooltip=f"{caption} ({float(stationKm):.3f} km)",
                popup=caption).add_to(m)

    def resetMap(self):
        m = self.buildMap(49.8, 15.5, 7)
        self.addTiles(m)
        self.renderMap(m)

    def drawAlignment(self, alignment, lxml=None):
        self.alignment = alignment
        self.lxml = lxml
        self.denseAlignment = (lxml or {}).get("denseAlignment") or []

        # The chainage column is cached because the cursor lookup runs on every mouse move
        self.denseStations = [point[0] for point in self.denseAlignment]

        if len(alignment) < 2:
            self.resetMap()
            return
        
        # Bounds
        optimizedAlignment = (lxml or {}).get("alignmentCoordinatesNew") or []
        allPoints = [pt for segmentData in alignment for pt in segmentData[0]]
        allPoints += [pt for segmentData in optimizedAlignment for pt in segmentData[0]]
        if not allPoints:
            self.resetMap()
            return

        lats = [pt[0] for pt in allPoints]
        lons = [pt[1] for pt in allPoints]
        centerLat = (min(lats) + max(lats)) / 2
        centerLon = (min(lons) + max(lons)) / 2
        m = self.buildMap(centerLat, centerLon, 11)
        self.addTiles(m)

        if self.drawMode == "single":
            allCoords = [segmentData[0] for segmentData in alignment]
            baselineColor = "#888888" if optimizedAlignment else "red"
            baselineTooltip = self.lan.get("mapBaselineAlignment", "Baseline alignment") if optimizedAlignment else "Alignment"
            folium.PolyLine(allCoords, color=baselineColor, weight=2.5, opacity=1, tooltip=baselineTooltip).add_to(m)
        elif self.drawMode == "type":
            typeColors = {"Line": "blue", "Spiral": "orange", "Curve": "purple"}
            for segmentCoords, segmentType in alignment:
                color = "#888888" if optimizedAlignment else typeColors.get(segmentType, "gray")
                folium.PolyLine(segmentCoords, color=color, weight=2.5, opacity=1, tooltip=segmentType).add_to(m)
        elif self.drawMode == "speed" and lxml:
            self.drawSpeedColoredAlignment(m, lxml, isDimmed=bool(optimizedAlignment))
        else:
            allCoords = [segmentData[0] for segmentData in alignment]
            folium.PolyLine(allCoords, color="red", weight=2.5, opacity=1, tooltip="Alignment").add_to(m)

        if optimizedAlignment:
            self.drawSlewIndicators(m, lxml or {})
            self.drawOptimizedOverlay(m, optimizedAlignment)

        self.addStationMarkers(m)
        self.renderMap(m)

    # Draws the optimizer's revised axis in the theme accent colour on top of the baseline
    def drawOptimizedOverlay(self, m, optimizedAlignment):
        accentColor = (self.themeTokens or {}).get("highlight", "#2f6fb5")
        tooltip = self.lan.get("mapNewAlignment", "New Alignment")
        newCoords = [segmentData[0] for segmentData in optimizedAlignment]
        folium.PolyLine(newCoords, color=accentColor, weight=3.5, opacity=1, tooltip=tooltip).add_to(m)

    # Heat line over every stretch whose lateral shift clears the visibility threshold
    def drawSlewIndicators(self, m, lxml):
        denseOptimized = lxml.get("denseAlignmentNew") or []
        stations = lxml.get("slewProfileStationKm")
        offsets = lxml.get("slewProfileOffsetMm")
        if len(denseOptimized) < 2 or stations is None or offsets is None or len(stations) < 2:
            return

        stations = np.asarray(stations, dtype=float)
        offsets = np.asarray(offsets, dtype=float)
        order = np.argsort(stations)
        stations, offsets = stations[order], offsets[order]

        peakMm = float(np.max(np.abs(offsets)))
        if peakMm <= SLEW_VISIBLE_THRESHOLD_MM:
            return

        colorMap = bcm.LinearColormap(
            ['#ffd166', '#ef7d3b', '#c1121f'],
            vmin=SLEW_VISIBLE_THRESHOLD_MM, vmax=peakMm,
            caption=self.lan.get("mapSlewLegend", "Lateral slew [mm]"))
        colorMap.add_to(m)

        # Contiguous runs are drawn one polyline at a time so unshifted stretches stay clean
        runCoords = []
        runPeakMm = 0.0
        for point in denseOptimized:
            slewMm = abs(float(np.interp(point[0], stations, offsets)))
            if slewMm > SLEW_VISIBLE_THRESHOLD_MM:
                runCoords.append((point[1], point[2]))
                runPeakMm = max(runPeakMm, slewMm)
            elif runCoords:
                self.addSlewRun(m, runCoords, runPeakMm, colorMap)
                runCoords, runPeakMm = [], 0.0
        self.addSlewRun(m, runCoords, runPeakMm, colorMap)

    def addSlewRun(self, m, runCoords, runPeakMm, colorMap):
        if len(runCoords) < 2:
            return
        tooltip = f"{self.lan.get('mapSlewSection', 'Slew section')}: {runPeakMm:.0f} mm"
        folium.PolyLine(runCoords, color=colorMap(runPeakMm), weight=SLEW_INDICATOR_WEIGHT,
                        opacity=SLEW_INDICATOR_OPACITY, tooltip=tooltip).add_to(m)

    def drawSpeedColoredAlignment(self, m, lxml, isDimmed=False):
        denseAlignment = lxml.get("denseAlignment")
        if not denseAlignment or len(denseAlignment) < 2:
            return

        # Resolve data keys — TTP uses its own stored arrays
        if self.speedProfile == "TTP":
            speedKey   = "speedLimitsTTP"
            stationKey = "stationSpeedTTP"
        else:
            speedKey   = f"speedLimits{self.speedProfile}"
            stationKey = f"stationSpeed{self.speedProfile}"

        speeds   = lxml.get(speedKey)
        stations = lxml.get(stationKey)

        missing = (speeds is None or stations is None or
                    (hasattr(speeds, '__len__') and len(speeds) == 0))
        if missing:
            allCoords = [seg[0] for seg in self.alignment]
            folium.PolyLine(allCoords, color="gray", weight=2.5, opacity=0.6,
                            tooltip="Speed data not yet calculated").add_to(m)
            return

        speeds   = np.asarray(speeds,   dtype=float)
        stations = np.asarray(stations, dtype=float)

        # Drop NaN / zero entries (geometry engine initialises arrays to 0)
        valid = np.isfinite(speeds) & np.isfinite(stations) & (speeds > 0)
        speeds, stations = speeds[valid], stations[valid]
        if len(speeds) == 0:
            allCoords = [seg[0] for seg in self.alignment]
            folium.PolyLine(allCoords, color="gray", weight=2.5, opacity=0.6,
                            tooltip="Speed data not yet calculated").add_to(m)
            return

        minSpd = float(np.min(speeds))
        maxSpd = float(np.max(speeds))
        if maxSpd <= minSpd:
            maxSpd = minSpd + 1.0

        # Branca colormap: red (slow) → yellow → green (fast).
        # Adding it to the map automatically renders a colour-scale legend.
        cmapBc = bcm.LinearColormap(
            ['#d73027', '#fee08b', '#1a9850'],
            vmin=minSpd,
            vmax=maxSpd,
            caption='Speed [km/h]',
        )
        cmapBc.add_to(m)

        sortIdx    = np.argsort(stations)
        sortedSt   = stations[sortIdx]
        sortedSp   = speeds[sortIdx]
        n           = len(sortedSp)

        points     = [(p[1], p[2]) for p in denseAlignment]
        spdValues = []
        for i in range(len(denseAlignment) - 1):
            avg = (denseAlignment[i][0] + denseAlignment[i + 1][0]) * 0.5
            idx = int(np.clip(
                np.searchsorted(sortedSt, avg, side='right') - 1,
                0, n - 1
            ))
            spdValues.append(float(sortedSp[idx]))

        if points and spdValues:
            # An optimized overlay takes visual priority, so the speed coloured baseline steps back
            ColorLine(points, colors=spdValues, colormap=cmapBc, weight=3,
                      opacity=0.45 if isDimmed else 1.0).add_to(m)

    def renderMap(self, m):
        # Expose the JavaScript hooks that drive the crosshair in both directions
        cursorScript = CURSOR_SCRIPT_TEMPLATE.format(
            mapName=m.get_name(),
            webChannelSource=self.webChannelSource,
            lookupPoints=json.dumps(self.buildLookupPoints()),
            slewLabels=json.dumps({"slew": self.lan.get("mapSlewTooltip", "Slew")}),
        )
        m.get_root().html.add_child(folium.Element(cursorScript))

        self.isMapReady = False
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.mapBrowser.setHtml(data.getvalue().decode(), QUrl("http://localhost"))

    # Subsample the densified alignment so the in page lookup stays responsive
    def buildLookupPoints(self):
        if len(self.denseAlignment) < 2:
            return []
        step = max(1, len(self.denseAlignment) // MAX_LOOKUP_POINTS)
        sampledPoints = self.denseAlignment[::step]

        slewByStation = self.buildSlewLookup()
        radiusByStation = self.buildRadiusLookup()
        lookupPoints = []
        for point in sampledPoints:
            stationKm = float(point[0])
            row = [stationKm, float(point[1]), float(point[2])]
            row.append(slewByStation(stationKm))
            row.extend(radiusByStation(stationKm))
            lookupPoints.append(row)
        return lookupPoints

    # Interpolator over the optimizer's slew profile, returns None wherever no profile exists
    def buildSlewLookup(self):
        lxml = self.lxml or {}
        stations = lxml.get("slewProfileStationKm")
        offsets = lxml.get("slewProfileOffsetMm")
        if stations is None or offsets is None or len(stations) < 2:
            return lambda stationKm: None

        stations = np.asarray(stations, dtype=float)
        offsets = np.asarray(offsets, dtype=float)
        order = np.argsort(stations)
        stations, offsets = stations[order], offsets[order]

        def lookup(stationKm):
            if stationKm < stations[0] or stationKm > stations[-1]:
                return None
            return round(float(np.interp(stationKm, stations, offsets)), 1)
        return lookup

    # Original and optimized radius of the curve group covering a chainage, None outside every group
    def buildRadiusLookup(self):
        summary = (self.lxml or {}).get("optimizationSummary") or {}
        groupRanges = [(g["startKm"], g["endKm"], g["radiusOldM"], g["radiusNewM"])
                       for g in summary.get("groups", [])
                       if g.get("radiusOldM") is not None and g.get("radiusNewM") is not None]
        if not groupRanges:
            return lambda stationKm: [None, None]

        def lookup(stationKm):
            for startKm, endKm, radiusOld, radiusNew in groupRanges:
                if startKm <= stationKm <= endKm:
                    return [round(float(radiusOld), 1), round(float(radiusNew), 1)]
            return [None, None]
        return lookup

    # The JavaScript hook only exists once the page has finished loading
    def onMapLoadFinished(self, isOk):
        self.isMapReady = bool(isOk)

    # Move the map cursor marker to the position matching a chainage in kilometres
    def setCursorStation(self, stationKm):
        if not self.isMapReady or len(self.denseAlignment) < 2:
            return

        position = self.interpolatePosition(stationKm)
        if position is None:
            return

        latitude, longitude = position
        self.mapBrowser.page().runJavaScript(
            f"if (window.setTrackCursor) {{ window.setTrackCursor({latitude}, {longitude}); }}")

    # Linear interpolation of latitude and longitude along the densified alignment
    def interpolatePosition(self, stationKm):
        stations = self.denseStations
        if not stations:
            return None

        # denseAlignment stores chainage in kilometres like the rest of the geometry
        target = float(stationKm)
        if target <= stations[0]:
            return self.denseAlignment[0][1], self.denseAlignment[0][2]
        if target >= stations[-1]:
            return self.denseAlignment[-1][1], self.denseAlignment[-1][2]

        index = int(np.searchsorted(stations, target, side='right')) - 1
        index = max(0, min(index, len(self.denseAlignment) - 2))

        startStation, startLat, startLon = self.denseAlignment[index]
        endStation, endLat, endLon = self.denseAlignment[index + 1]
        span = endStation - startStation
        ratio = 0.0 if span == 0 else (target - startStation) / span

        return startLat + ratio * (endLat - startLat), startLon + ratio * (endLon - startLon)

    def getBearing(self, lat1, lon1, lat2, lon2):
        lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
        dLon = lon2 - lon1
        y = math.sin(dLon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        bearing = math.degrees(math.atan2(y, x))
        return (bearing + 360) % 360

    # def _draw_stationing(self, m, lxml):
    #     keyLat = lxml.get("keyLat", [])
    #     keyLon = lxml.get("keyLon", [])
    #     keyTypes = lxml.get("keyTypes", [])
    #     keyStations = lxml.get("keyStations", [])
    #     denseAlignment = lxml.get("denseAlignment", [])

    #     if len(keyLat) == 0 or len(denseAlignment) < 2:
    #         return

    #     # Klíčové body ZÚ, KÚ, ZO, KO, ZP, KP
    #     for i in range(len(keyLat)):
    #         lat, lon = keyLat[i], keyLon[i]
    #         ktype = keyTypes[i]
    #         sta = keyStations[i]
            
    #         closest_idx = 0
    #         min_dist = float('inf')
    #         for j, p in enumerate(denseAlignment):
    #             dist = (p[1]-lat)**2 + (p[2]-lon)**2
    #             if dist < min_dist:
    #                 min_dist = dist; closest_idx = j
            
    #         if closest_idx < len(denseAlignment) - 1:
    #             p1 = denseAlignment[closest_idx]; p2 = denseAlignment[closest_idx + 1]
    #         else:
    #             p1 = denseAlignment[closest_idx - 1]; p2 = denseAlignment[closest_idx]
                
    #         bearing = self._get_bearing(p1[1], p1[2], p2[1], p2[2])
            
    #         if ktype in ["ZÚ", "KÚ"]:
    #             angle = bearing - 90
    #             transform_style = f"transform: rotate({angle % 360}deg) translate(15px, -10px);"
    #         else:
    #             angle = bearing
    #             transform_style = f"transform: rotate({angle % 360}deg) translate(5px, -15px);"

    #         angle = angle % 360
    #         if 90 < angle <= 270:
    #             angle += 180
    #             if ktype in ["ZÚ", "KÚ"]: transform_style = f"transform: rotate({angle % 360}deg) translate(-15px, 10px);"
    #             else: transform_style = f"transform: rotate({angle % 360}deg) translate(-5px, 15px);"
            
    #         html = f'''
    #             <div style="font-size: 10pt; color: black; font-weight: bold; text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff; {transform_style} white-space: nowrap;">
    #                 {ktype} {sta:.3f}
    #             </div>
    #         '''
    #         folium.Marker([lat, lon], icon=DivIcon(icon_size=(150, 36), icon_anchor=(0, 0), html=html)).add_to(m)
            
    #         if ktype in ["ZÚ", "KÚ"]:
    #             tick_len = 0.0003
    #             tick_ang = math.radians(bearing - 90)
    #             folium.PolyLine([(lat + tick_len * math.cos(tick_ang), lon + tick_len * math.sin(tick_ang)), 
    #                              (lat - tick_len * math.cos(tick_ang), lon - tick_len * math.sin(tick_ang))], 
    #                             color="black", weight=2).add_to(m)
    #         else:
    #             folium.CircleMarker([lat, lon], radius=3, color='black', fill=True, fill_color='black').add_to(m)

    #     # Kilometrovníky
    #     min_sta = math.ceil(denseAlignment[0][0])
    #     max_sta = math.floor(denseAlignment[-1][0])
        
    #     for km in range(min_sta, max_sta + 1):
    #         p1 = None; p2 = None
    #         for i in range(len(denseAlignment) - 1):
    #             if denseAlignment[i][0] <= km <= denseAlignment[i+1][0]:
    #                 p1 = denseAlignment[i]; p2 = denseAlignment[i+1]
    #                 break
    #         if not p1 or not p2: continue
                
    #         s1, lat1, lon1 = p1
    #         s2, lat2, lon2 = p2
    #         ratio = 0 if s2 == s1 else (km - s1) / (s2 - s1)
                
    #         lat = lat1 + ratio * (lat2 - lat1)
    #         lon = lon1 + ratio * (lon2 - lon1)
            
    #         bearing = self._get_bearing(lat1, lon1, lat2, lon2)
    #         angle = bearing % 360
    #         transform_style = f"transform: rotate({angle}deg) translate(0px, -20px);"
            
    #         if 90 < angle <= 270:
    #             angle += 180
    #             transform_style = f"transform: rotate({angle % 360}deg) translate(0px, 20px);"
            
    #         html = f'''
    #             <div style="font-size: 11pt; color: blue; font-weight: bold; text-shadow: -1px -1px 0 #fff, 1px -1px 0 #fff, -1px 1px 0 #fff, 1px 1px 0 #fff; {transform_style} white-space: nowrap;">
    #                 {km}
    #             </div>
    #         '''
    #         folium.Marker([lat, lon], icon=DivIcon(icon_size=(100, 20), icon_anchor=(0, 0), html=html)).add_to(m)
    #         folium.CircleMarker([lat, lon], radius=4, color='blue', fill=True, fill_color='white').add_to(m)