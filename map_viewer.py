import io
import folium
from folium import DivIcon
from folium.features import ColorLine
import math
from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView
import numpy as np
import matplotlib.cm as cm
import matplotlib.colors as mcolors

class MapWidget(QWidget):
    def __init__(self, parent=None):
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
        self.resetMap()

    def setDrawOptions(self, draw_mode, speed_profile):
        self.drawMode = draw_mode
        self.speedProfile = speed_profile
        if len(self.alignment) >= 2:
            self.drawAlignment(self.alignment, self.lxml)

    def setBaseMap(self, base_map):
        self.currentBaseMap = base_map
        if len(self.alignment) >= 2:
            self.drawAlignment(self.alignment, self.lxml)
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

    def drawAlignment(self, alignment, lxml=None):
        self.alignment = alignment
        self.lxml = lxml
        if len(alignment) < 2:
            self.resetMap()
            return
        
        # Bounds
        all_points = [pt for segment_data in alignment for pt in segment_data[0]]
        if not all_points:
            self.resetMap()
            return

        lats = [pt[0] for pt in all_points]
        lons = [pt[1] for pt in all_points]
        centerLat = (min(lats) + max(lats)) / 2
        centerLon = (min(lons) + max(lons)) / 2
        m = folium.Map(location=[centerLat, centerLon], zoom_start=11, tiles=None)
        self._add_tiles(m)

        if self.drawMode == "single":
            all_coords = [segment_data[0] for segment_data in alignment]
            folium.PolyLine(all_coords, color="red", weight=2.5, opacity=1, tooltip="Alignment").add_to(m)
        elif self.drawMode == "type":
            type_colors = {"Line": "blue", "Spiral": "orange", "Curve": "purple"}
            for segment_coords, segment_type in alignment:
                color = type_colors.get(segment_type, "gray")
                folium.PolyLine(segment_coords, color=color, weight=2.5, opacity=1, tooltip=segment_type).add_to(m)
        elif self.drawMode == "speed" and lxml:
            self._draw_speed_colored_alignment(m, lxml)
        else:
            all_coords = [segment_data[0] for segment_data in alignment]
            folium.PolyLine(all_coords, color="red", weight=2.5, opacity=1, tooltip="Alignment").add_to(m)
            
        self.renderMap(m)

    def _draw_speed_colored_alignment(self, m, lxml):
        dense_alignment = lxml.get("denseAlignment")
        if not dense_alignment or len(dense_alignment) < 2: return

        speed_profile_key = f"speedLimits{self.speedProfile}"
        station_profile_key = f"stationSpeed{self.speedProfile}"

        speeds = lxml.get(speed_profile_key)
        stations = lxml.get(station_profile_key)

        if speeds is None or stations is None or len(speeds) == 0:
            all_coords = [segment_data[0] for segment_data in self.alignment]
            folium.PolyLine(all_coords, color="red", weight=2.5, opacity=1, tooltip="Alignment (speed data missing)").add_to(m)
            return

        min_speed, max_speed = np.min(speeds), np.max(speeds)
        norm = mcolors.Normalize(vmin=min_speed, vmax=max_speed) if max_speed > min_speed else mcolors.Normalize(vmin=min_speed - 1, vmax=max_speed + 1)
        cmap = cm.get_cmap('RdYlGn')

        points = [(p[1], p[2]) for p in dense_alignment]
        colors = []
        sort_indices = np.argsort(stations)
        sorted_stations, sorted_speeds = stations[sort_indices], speeds[sort_indices]

        for i in range(len(dense_alignment) - 1):
            avg_station = (dense_alignment[i][0] + dense_alignment[i+1][0]) / 2.0
            idx = np.clip(np.searchsorted(sorted_stations, avg_station, side='right') - 1, 0, len(sorted_speeds) - 1)
            colors.append(mcolors.to_hex(cmap(norm(sorted_speeds[idx]))))

        if points and colors: ColorLine(points, colors=colors, weight=3).add_to(m)

    def renderMap(self, m):
        data = io.BytesIO()
        m.save(data, close_file=False)
        self.mapBrowser.setHtml(data.getvalue().decode(), QUrl("http://localhost"))

    def _get_bearing(self, lat1, lon1, lat2, lon2):
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