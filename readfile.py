import xml.etree.ElementTree as ET
import numpy as np
import re

# Open file dialog

class ReadFile:
    def Read(self, filepath):
        try:
            # filepath = filedialog.askopenfilename(initialdir="C:\\",
            #                                 title="Open file",
            #                                 filetypes= (("text files","*.txt"),
            #                                             ("XML files","*.xml"),
            #                                 ("all files","*.*")))
            
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
        # file.close()

    def ParseLandXML(self, xml_data):

        # Check if xml_data is provided
        if not xml_data:
            return ["No data could be parsed"]

        # Use the provided XML data string instead of opening a file            
        root = ET.fromstring(xml_data)

        # Extract stations where cant is defined
        station = []
        for km in root.iter():
            if km.tag.endswith('CantStation'):
                station.append(km.get('station')) 

        # Extract cant values
        cant = []
        for mm in root.iter():
            if mm.tag.endswith('CantStation'):
                cant.append(mm.get('appliedCant'))
            
        # Convert to numpy arrays

        station = np.array(station)
        
        cant = np.array(cant)

        parsedXML = np.column_stack((station, cant))

        return parsedXML
    
    def ParseXMLTTP(self, xml_data):
        
        # Check if xml_data is provided
        if not xml_data:
            return ["No data could be parsed"]

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

        stations = np.array(stations)
        speedLimits = np.array(speedLimits)
        parsedTTP = np.column_stack((stations, speedLimits))
                
        return parsedTTP