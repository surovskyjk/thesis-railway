import xml.etree.ElementTree as ET


# Use the provided XML data string instead of opening a file            
tree = ET.parse('D:\\MT\\Data\\Samples\\Classified\\SampleAlignment.xml')
root = tree.getroot()

# Extract stations where cant is defined

station = []
for km in root.iter():
    if km.tag.endswith('CantStation'):
        station.append(km.get('station')) 

# Extract cant values
cant = []
# for mm in root.iter():
#     if mm.tag.endswith('CantStation'):
#         cant.append(mm.get('appliedCant'))

for mm in root.iter('{http://www.landxml.org/schema/LandXML-1.2}CantStation'):
    cant.append(mm.get('appliedCant'))

helper = []
for elem in root.iter('{http://www.landxml.org/schema/LandXML-1.2}Application'):
    helper.append(elem.get('name'))

print("Stations:", station)
print("Cant values:", cant)
print("Helper values:", helper)
            


