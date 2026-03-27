import xml.etree.ElementTree as ET
import numpy as np
import re
from pyproj import Transformer
from pyclothoids import Clothoid

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
        try:
            root = ET.fromstring(xml_data)
            
            if "LandXML" in root.tag:
                return 1
            elif "ArrayOfTab6b" in root.tag:
                return 2
            else:
                return 0
        except:
            return 0

    def ParseLandXML(self, xml_data, epsgInput) -> dict:

        # Check if xml_data is provided
        if not xml_data:
            return {"error": "No data could be parsed / Keine Daten konnten geparst werden / Žádná data nelze zpracovat."}

        # Use the provided XML data string instead of opening a file            
        root = ET.fromstring(xml_data)

        # Alignment length
        length = []
        for alig in root.iter():
            if alig.tag.endswith('Alignment'):
                length.append(alig.get('length'))
                length.append(alig.get('staStart'))
        length = np.array(length, dtype=float)

        # Extract stations where cant is defined
        stationCant = []
        for km in root.iter():
            if km.tag.endswith('CantStation'):
                stationCant.append(km.get('station'))
        stationCant.append(length[0]+length[1])

        # Extract cant values
        cant = []
        for mm in root.iter():
            if mm.tag.endswith('CantStation'):
                cant.append(mm.get('appliedCant'))
        cant.append(cant[-1])

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

        # Extract start and end of elements coordinates
        lineStartX = []
        lineStartY = []
        lineEndX = []
        lineEndY = []

        for lineCoordinates in root.iter():
            if lineCoordinates.tag.endswith('Line'):
                for coordinate in lineCoordinates:
                    if coordinate.tag.endswith('Start'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            lineStartX.append(coordinatesTemp[0])
                            lineStartY.append(coordinatesTemp[1])
                    elif coordinate.tag.endswith('End'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            lineEndX.append(coordinatesTemp[0])
                            lineEndY.append(coordinatesTemp[1])

        spiralStartX = []
        spiralStartY = []
        spiralEndX = []
        spiralEndY = []
        spiralPIX = []
        spiralPIY = []

        for spiralCoordinates in root.iter():
            if spiralCoordinates.tag.endswith('Spiral'):
                for coordinate in spiralCoordinates:
                    if coordinate.tag.endswith('Start'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            spiralStartX.append(coordinatesTemp[0])
                            spiralStartY.append(coordinatesTemp[1])    
                    elif coordinate.tag.endswith('End'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            spiralEndX.append(coordinatesTemp[0])
                            spiralEndY.append(coordinatesTemp[1])
                    elif coordinate.tag.endswith('PI'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            spiralPIX.append(coordinatesTemp[0])
                            spiralPIY.append(coordinatesTemp[1])

        curveStartX = []
        curveStartY = []
        curveEndX = []
        curveEndY = []
        curveCenterX = []
        curveCenterY = []

        for curveCoordinates in root.iter():
            if curveCoordinates.tag.endswith('Curve'):
                for coordinate in curveCoordinates:
                    if coordinate.tag.endswith('Start'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            curveStartX.append(coordinatesTemp[0])
                            curveStartY.append(coordinatesTemp[1])
                    elif coordinate.tag.endswith('End'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            curveEndX.append(coordinatesTemp[0])
                            curveEndY.append(coordinatesTemp[1])
                    elif coordinate.tag.endswith('Center'):
                        coordinatesTemp = coordinate.text.strip().split()
                        if len(coordinatesTemp) >= 2:
                            curveCenterX.append(coordinatesTemp[0])
                            curveCenterY.append(coordinatesTemp[1])

        # Extract station, where horizontal alignment is being changed
        stationHorizontal = []
        elements = []
        for el in root.iter():
            if el.tag.endswith('Line') or el.tag.endswith('Spiral') or el.tag.endswith('Curve'):
                if el.get('staStart') is not None:
                    elements.append(el)

        for i, km in enumerate(elements):
            staStart = float(km.get('staStart',"0"))
            
            if i+1 < len(elements):
                staEnd = float(elements[i+1].get('staStart',"0"))
            else:
                staEnd = length[0]+length[1]
            
            stationHorizontal.append(staStart)
            stationHorizontal.append(staEnd)

        # Extract radius values
        radius = []
        curvature = []
        curvatureSign = []
        geometryType = []
        
        for r in elements:
            sign = 1.0
            if r.tag.endswith('Curve') or r.tag.endswith('Spiral'):
                if r.get('rot') == "ccw":
                    sign = -1.0

            if r.tag.endswith('Line'):
                radius.append('INF')    # Infinite radius for straight lines
                radius.append('INF')    # Once again for station end
                geometryType.append('Line')
                geometryType.append('Line')
                curvature.append(0)
                curvature.append(0)
                curvatureSign.append(sign)
                curvatureSign.append(sign)

            elif r.tag.endswith('Spiral'):
                radius.append(r.get('radiusStart'))
                radius.append(r.get('radiusEnd'))
                geometryType.append('Spiral')
                geometryType.append('Spiral')
                try:
                    curvature.append(1/float(r.get('radiusStart')))
                except:
                    curvature.append(0)
                try:
                    curvature.append(1/float(r.get('radiusEnd')))
                except:
                    curvature.append(0)
                curvatureSign.append(sign)
                curvatureSign.append(sign)

            elif r.tag.endswith('Curve'):
                radius.append(r.get('radius'))
                radius.append(r.get('radius'))
                geometryType.append('Curve')
                geometryType.append('Curve')
                try:
                    curvature.append(1/float(r.get('radius')))
                except:
                    curvature.append(0)
                try:
                    curvature.append(1/float(r.get('radius')))
                except:
                    curvature.append(0)
                curvatureSign.append(sign)
                curvatureSign.append(sign)

        # Parse line station
        lineStationStart = []
        for km in root.iter():
            if km.tag.endswith('Line'):
                lineStationStart.append(km.get('staStart'))

        # Parse spiral attributes
        spiralStationStart = []
        spiralLength = []
        spiralRadiusStart = []
        spiralRadiusEnd = []
        spiralRot = []
        spiralType = []
        spiralConst = []

        for spiral in root.iter():
            if spiral.tag.endswith('Spiral') and spiral.get('staStart') is not None:
                
                spiralStationStart.append(spiral.get('staStart'))
                
                spiralLength.append(spiral.get('length'))
                
                spiralRadiusStart.append(spiral.get('radiusStart'))

                spiralRadiusEnd.append(spiral.get('radiusEnd'))

                spiralRot.append(spiral.get('rot'))

                spiralType.append(spiral.get('spiType'))

                spiralConst.append(spiral.get('consant'))

        # Parse curve attributes
        curveStationStart = []
        curveRot = []
        curveType = []
        curveRadius = []

        for curve in root.iter():
            if curve.tag.endswith('Curve') and curve.get('staStart') is not None:
                
                curveStationStart.append(curve.get('staStart'))

                curveRot.append(curve.get('rot'))

                curveType.append(curve.get('crvType'))

                curveRadius.append(curve.get('radius'))
        
        # Convert to numpy arrays (float only)
        stationCant = np.array(stationCant, dtype=float)/1000  # Convert from m to km
        cant = np.array(cant, dtype=float)
        stationHorizontal = np.array(stationHorizontal, dtype=float)/1000  # Convert from m to km
        geometryType = np.array(geometryType)
        radius = np.array(radius, dtype=float)
        curvature = np.array(curvature, dtype=float)
        curvatureSign = np.array(curvatureSign, dtype=float)
        stationVertical = np.array(stationVertical, dtype=float)/1000  # Convert from m to km
        elevation = np.array(elevation, dtype=float)
        lineStartX = np.array(lineStartX, dtype=float)
        lineStartY = np.array(lineStartY, dtype=float)
        lineEndX = np.array(lineEndX, dtype=float)
        lineEndY = np.array(lineEndY, dtype=float)
        spiralStartX = np.array(spiralStartX, dtype=float)
        spiralStartY = np.array(spiralStartY, dtype=float)
        spiralEndX = np.array(spiralEndX, dtype=float)
        spiralEndY = np.array(spiralEndY, dtype=float)
        spiralPIX = np.array(spiralPIX, dtype=float)
        spiralPIY = np.array(spiralPIY, dtype=float)
        curveStartX = np.array(curveStartX, dtype=float)
        curveStartY = np.array(curveStartY, dtype=float)
        curveEndX = np.array(curveEndX, dtype=float)
        curveEndY = np.array(curveEndY, dtype=float)
        curveCenterX = np.array(curveCenterX, dtype=float)
        curveCenterY = np.array(curveCenterY, dtype=float)
        lineStationStart = np.array(lineStationStart, dtype=float)/1000  # Convert from m to km
        spiralStationStart = np.array(spiralStationStart, dtype=float)/1000  # Convert from m to km
        spiralLength = np.array(spiralLength, dtype=float)
        spiralRadiusStart = np.array(spiralRadiusStart, dtype=float)
        spiralRadiusEnd = np.array(spiralRadiusEnd, dtype=float)
        spiralConst = np.array(spiralConst, dtype=float)
        spiralRot = np.array(spiralRot)
        spiralType = np.array(spiralType)
        curveStationStart = np.array(curveStationStart, dtype=float)/1000  # Convert from m to km
        curveRadius = np.array(curveRadius, dtype=float)
        curveRot = np.array(curveRot)
        curveType = np.array(curveType)

        # Combine extracted data into a structured dictionary
        parsedXML = {
            "stationCant": stationCant,
            "cant": cant,
            "stationHorizontal": stationHorizontal,
            "geometryType": geometryType,
            "radius": radius,
            "curvature": curvature,
            "curvatureSign": curvatureSign,
            "stationVertical": stationVertical,
            "elevation": elevation,
            "lineStartX": lineStartX,
            "lineStartY": lineStartY,
            "lineEndX": lineEndX,
            "lineEndY": lineEndY,
            "spiralStartX": spiralStartX,
            "spiralStartY": spiralStartY,
            "spiralEndX": spiralEndX,
            "spiralEndY": spiralEndY,
            "spiralPIX": spiralPIX,
            "spiralPIY": spiralPIY,
            "curveStartX": curveStartX,
            "curveStartY": curveStartY,
            "curveEndX": curveEndX,
            "curveEndY": curveEndY,
            "curveCenterX": curveCenterX,
            "curveCenterY": curveCenterY,
            "lineStationStart": lineStationStart,
            "spiralStationStart": spiralStationStart,
            "spiralLength": spiralLength,
            "spiralRadiusStart": spiralRadiusStart,
            "spiralRadiusEnd": spiralRadiusEnd,
            "spiralRot": spiralRot,
            "spiralType": spiralType,
            "spiralConst": spiralConst,
            "curveStationStart": curveStationStart,
            "curveRot": curveRot,
            "curveType": curveType,
            "curveRadius": curveRadius
        }

        # Add transformed coordinates and more points for transition curves
        self.alignmentCoordinates(parsedXML, epsgInput, "EPSG:4326")

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
    
    def alignmentCoordinates(self, parsedXML, epsgInput, epsgOutput):
        
        alignmentCoords = []
        alignmentCoordsOriginal = []
        
        transformer = Transformer.from_crs(epsgInput, epsgOutput, always_xy=True)

        # Universal add segment method

        def addSegment(x, y):

            originalCoords = np.column_stack((x, y)).tolist()
            alignmentCoordsOriginal.append(originalCoords)

            if epsgInput == "EPSG:5514":
                easting = -np.array(y)
                northing = -np.array(x)

            else:
                easting = np.array(x)
                northing = np.array(y)

            lon, lat = transformer.transform(easting, northing)

            transformedCoords = np.column_stack((lat, lon)).tolist()
            alignmentCoords.append(transformedCoords)

        # Line
        if "lineStartX" in parsedXML:
            for i in range(len(parsedXML["lineStartX"])):
                addSegment([parsedXML["lineStartX"][i], parsedXML["lineEndX"][i]], [parsedXML["lineStartY"][i], parsedXML["lineEndY"][i]])

        # Spiral
        if "spiralStartX" in parsedXML:
            for i in range(len(parsedXML["spiralStartX"])):
                x, y = self.discretizeSpiral(
                    parsedXML["spiralStartX"][i],
                    parsedXML["spiralStartY"][i],
                    parsedXML["spiralPIX"][i],
                    parsedXML["spiralPIY"][i],
                    parsedXML["spiralLength"][i],
                    parsedXML["spiralRadiusStart"][i],
                    parsedXML["spiralRadiusEnd"][i],
                    parsedXML["spiralRot"][i],
                    smoothness = 50,
                    epsgInput = epsgInput
                    )
                
                addSegment(x, y)   

        # Curve
        if "curveStartX" in parsedXML:
            for i in range(len(parsedXML["curveStartX"])):
                x, y = self.discretizeCurve(
                    parsedXML["curveStartX"][i],
                    parsedXML["curveStartY"][i],
                    parsedXML["curveEndX"][i],
                    parsedXML["curveEndY"][i],
                    parsedXML["curveCenterX"][i],
                    parsedXML["curveCenterY"][i],
                    parsedXML["curveRot"][i],
                    parsedXML["curveRadius"][i],
                    smoothness = 50,
                    epsgInput = epsgInput
                    )
                
                addSegment(x, y)

        parsedXML["alignmentCoordinates"] = alignmentCoords
        parsedXML["alignmentCoordsOriginal"] = alignmentCoordsOriginal

        return parsedXML
    
    def discretizeCurve(self, startX, startY, endX, endY, centerX, centerY, rotDir, radius, smoothness, epsgInput):
        angleStart = np.arctan2(startY-centerY, startX-centerX)
        angleEnd = np.arctan2(endY-centerY, endX-centerX)

        if epsgInput == "EPSG:5514":
            if rotDir == "cw":
                if angleEnd < angleStart:
                    angleEnd += 2*np.pi
            else:
                if angleEnd > angleStart:
                    angleEnd -= 2*np.pi
        else:
            if rotDir == "cw":
                if angleEnd > angleStart:
                    angleEnd -= 2*np.pi
            else:
                if angleEnd < angleStart:
                    angleEnd += 2*np.pi
        
        anglesLinspace = np.linspace(angleStart, angleEnd, smoothness)

        x = centerX + radius * np.cos(anglesLinspace)
        y = centerY + radius * np.sin(anglesLinspace)

        return x, y
    
    def discretizeSpiral(self, startX, startY, piX, piY, length, radiusStart, radiusEnd, rot, smoothness, epsgInput):
        # Calculate azimuth for clothoids library
        azimuth = np.arctan2(piY-startY, piX-startX)

        # Calculate curvature

        kappaStart = 1/radiusStart if (radiusStart != 0 and radiusStart != float('inf')) else 0.0
        kappaEnd = 1/radiusEnd if (radiusEnd != 0 and radiusEnd != float('inf')) else 0.0

        # Clockwise / Counterclockwise
        if epsgInput == "EPSG:5514":
            if rot == "cw":
                kappaStart, kappaEnd = abs(kappaStart), abs(kappaEnd)
            else:
                kappaStart, kappaEnd = -abs(kappaStart), -abs(kappaEnd)
        else:
            if rot == "cw":
                kappaStart, kappaEnd = -abs(kappaStart), -abs(kappaEnd)
            else:
                kappaStart, kappaEnd = abs(kappaStart), abs(kappaEnd)

        dKappa = (kappaEnd - kappaStart) / length
        spiral = Clothoid.StandardParams(startX, startY, azimuth, kappaStart, dKappa, length)

        spiralLinspace = np.linspace(0, length, smoothness)
        x = [spiral.X(t) for t in spiralLinspace]
        y = [spiral.Y(t) for t in spiralLinspace]

        return x, y