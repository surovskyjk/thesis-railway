import xml.etree.ElementTree as ET
import numpy as np
import re

# Open file dialog

class ReadFile:
    def Read(self, filepath):
        try:
                        
            if filepath:
                try:
                    with open(filepath, "r", encoding='utf-8-sig') as file:
                        return file.read()
                    
                except UnicodeDecodeError:
                    with open(filepath, "r", encoding='cp1250') as file:
                        return file.read()
                    
                except Exception as e:
                    return f"Error reading file: {e}"
                            
        except:
            return "Error while opening file"
        

    def XMLType(self, xml_data):
        return None


    def ParseLandXML(self, xml_data) -> dict:

        # Check if xml_data is provided
        if not xml_data:
            return {"error": "No data could be parsed / Keine Daten konnten geparst werden / Žádná data nelze zpracovat."}

        # Use the provided XML data string instead of opening a file            
        root = ET.fromstring(xml_data)

        # Extract stations where cant is defined
        stationCant = []
        for km in root.iter():
            if km.tag.endswith('CantStation'):
                stationCant.append(km.get('station')) 

        # Extract cant values
        cant = []
        for mm in root.iter():
            if mm.tag.endswith('CantStation'):
                cant.append(mm.get('appliedCant'))
            

        # Extract station, where horizontal alignment is being changed
        stationHorizontal = []
        for km in root.iter():
            if km.tag.endswith('Line') or km.tag.endswith('Spiral') or km.tag.endswith('Curve'):
                stationHorizontal.append(km.get('staStart'))

        # Extract radius values
        radius = []
        for r in root.iter():
            if r.tag.endswith('Line'):
                radius.append('INF')  # Infinite radius for straight lines"
            elif r.tag.endswith('Spiral'):
                radius.append(r.get('radiusStart'))
            elif r.tag.endswith('Curve'):
                radius.append(r.get('radius'))

        # Convert radius to curvature
        curvature = []
        for r in radius:
            try:
                curvature.append(1/float(r))
            except:
                curvature.append(0)

        # Vertical alignment data
        
        stationVertical = []
        elevation = []

        for vl in root.iter():
            if vl.tag.endswith('PVI') or vl.tag.endswith('CircCurve'):

                verticalData = vl.text

                if verticalData:
                    parts = verticalData.strip().split()

                    if len(parts) >= 2:
                        try:
                            stationVertical.append((parts[0]))
                            elevation.append((parts[1]))
                        
                        # Error handling, if conversion to float fails or entry is invalid, skip the entry
                        except ValueError:
                            continue


        # Convert to numpy arrays

        stationCant = np.array(stationCant, dtype=float)/1000  # Convert from m to km
        cant = np.array(cant, dtype=float)
        stationHorizontal = np.array(stationHorizontal, dtype=float)/1000  # Convert from m to km
        radius = np.array(radius, dtype=float)
        curvature = np.array(curvature, dtype=float)
        stationVertical = np.array(stationVertical, dtype=float)/1000  # Convert from m to km
        elevation = np.array(elevation, dtype=float)

        # Combine extracted data into a structured dictionary

        parsedXML = {
            "stationCant": stationCant,
            "cant": cant,
            "stationHorizontal": stationHorizontal,
            "radius": radius,
            "curvature": curvature,
            "stationVertical": stationVertical,
            "elevation": elevation
        }

        return parsedXML
    
    def ParseXMLTTP(self, xml_data) -> dict:
        
        # Check if xml_data is provided
        if not xml_data:
            return {"error": "No data could be parsed / Keine Daten konnten geparst werden / Žádná data nelze zpracovat."}

        # Use the provided XML data string instead of opening a file            
        root = ET.fromstring(xml_data)

        # Extract stations of speed limit signals
        stations = []

        for umisteni in root.iter('umisteni'):
            stations.append(umisteni.text)

        # Extract speed limits of speed limit signals
        speedLimits = []

        for rychlostnikN in root.iter('rychlostnikN'):
            speedLimits.append(rychlostnikN.text)

        # Combine stations and speed limits into a structured array
        
        # Clean non-numeric characters and convert to float
        for i in reversed(range(len(speedLimits))):
            
            try:
                station = stations[i].replace(',', '.')
                stations[i] = float(re.sub(r'[^\d.]', '', station))
                speedLimits[i] = float(re.sub(r'[^\d.]', '', speedLimits[i])) 
            except:
                stations.pop(i)
                speedLimits.pop(i)

        # Convert to numpy arrays

        stationSpeedLimits = np.array(stations, dtype=float)
        speedLimits = np.array(speedLimits, dtype=float)
        
        # Combine extracted data into a structured dictionary

        parsedTTP = {
            "stationSpeedLimits": stationSpeedLimits,
            "speedLimits": speedLimits
        }
                
        return parsedTTP