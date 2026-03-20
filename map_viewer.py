import io
import folium
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView

class MapWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        self.mapBrowser = QWebEngineView()
        self.layout.addWidget(self.mapBrowser)

        self.resetMap()

    def resetMap(self):
        m = folium.Map(location=[49.8, 15.5], zoom_start=7, tiles="CartoDB Positron")
        self.renderMap(m)

    def drawAlignment(self, alignment):
        if len(alignment) < 2:
            return
        
        startLat, startLon = alignment[0]

        # Bounds
        lats = [coord[0] for coord in alignment]
        lons = [coord[1] for coord in alignment]
        centerLat = (min(lats) + max(lats)) / 2
        centerLon = (min(lons) + max(lons)) / 2

        m = folium.Map(location=[centerLat, centerLon], zoom_start=11, tiles="CartoDB Positron")

        folium.PolyLine(alignment, color="red", weight=2.5, opacity=1, tooltip="Alignment").add_to(m)

        

        self.renderMap(m)


    def renderMap(self, m):
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.mapBrowser.setHtml(data.getvalue().decode())

