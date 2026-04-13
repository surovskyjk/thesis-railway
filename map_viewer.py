import io
import folium
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView

class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        self.mapBrowser = QWebEngineView()
        self.layout.addWidget(self.mapBrowser)
        self.currentBaseMap = "positron"
        self.alignment = []
        self.resetMap()

    def setBaseMap(self, base_map):
        self.currentBaseMap = base_map
        if len(self.alignment) >= 2:
            self.drawAlignment(self.alignment)
        else:
            self.resetMap()

    def _add_tiles(self, m):
        if self.currentBaseMap == "positron":
            folium.TileLayer("CartoDB Positron").add_to(m)
        elif self.currentBaseMap == "osm":
            folium.TileLayer("OpenStreetMap").add_to(m)
        elif self.currentBaseMap == "orm":
            folium.TileLayer("OpenStreetMap").add_to(m)
            folium.TileLayer(
                tiles='https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png',
                attr='Map data: &copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> | Style: &copy; <a href="https://www.openrailwaymap.org/">OpenRailwayMap</a>',
                name='OpenRailwayMap',
                subdomains='abc',
                overlay=True,
                transparent=True,
                max_zoom=19,
                show=True
            ).add_to(m)
        elif self.currentBaseMap == "cuzk":
            folium.WmsTileLayer(
                url="https://ags.cuzk.gov.cz/arcgis1/services/ORTOFOTO/MapServer/WMSServer",
                layers="0",
                name="ČÚZK Ortofoto",
                fmt="image/jpeg",
                transparent=False,
                attr="© ČÚZK",
                overlay=False
            ).add_to(m)

    def resetMap(self):
        m = folium.Map(location=[49.8, 15.5], zoom_start=7, tiles=None)
        self._add_tiles(m)
        self.renderMap(m)

    def drawAlignment(self, alignment):
        self.alignment = alignment
        if len(alignment) < 2:
            self.resetMap()
            return
        
        # Bounds
        lats = [pt[0] for segment in alignment for pt in segment]
        lons = [pt[1] for segment in alignment for pt in segment]
        centerLat = (min(lats) + max(lats)) / 2
        centerLon = (min(lons) + max(lons)) / 2
        m = folium.Map(location=[centerLat, centerLon], zoom_start=11, tiles=None)
        self._add_tiles(m)
        folium.PolyLine(alignment, color="red", weight=2.5, opacity=1, tooltip="Alignment").add_to(m)
        self.renderMap(m)

    def renderMap(self, m):
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.mapBrowser.setHtml(data.getvalue().decode(), QUrl("http://localhost"))