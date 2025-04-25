from lxml import etree

# File paths
input_xml = "Treasure_Map_Locations.xml"
output_xml = "Treasure_Map_Locations_FIXED.xml"

# Load XML
tree = etree.parse(input_xml)
root = tree.getroot()

# Prefixes that need custom icons
prefixes = ["N", "E", "S", "W", "CC", "X"]

# Update markers
for marker in root.iter('Marker'):
    name = marker.attrib.get('Name', '')
    if any(name.startswith(prefix) for prefix in prefixes):
        marker.attrib['Icon'] = name  # Set Icon to match Name

# Save updated XML
tree.write(output_xml, pretty_print=True, xml_declaration=True, encoding="UTF-8")

print("✅ Updated XML saved as Treasure_Map_Locations_FIXED.xml")