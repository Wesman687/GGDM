import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
from PIL import Image, ImageDraw, ImageFont

# === CONFIG ===
OUTPUT_XML = "Gridlines.xml"
OUTPUT_ICON_FOLDER = "MapIcons"
GRID_STEP = 1000
X_RANGE = (0, 4800)
Y_RANGE = (0, 6000)
ICONS = ["hline", "vline", "cross"]
FILL_COLOR = (100, 100, 100, 200)
LINE_DENSITY = GRID_STEP // 10 
HLINE_SPACING = 10    # Horizontal grid density
VLINE_SPACING = 10    # Vertical grid density

def create_icon(char, output_folder):
    canvas_size = 128
    line_width = 2
    center = canvas_size // 2

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    draw.rectangle([0, 0, canvas_size, canvas_size], fill=(0, 0, 0, 0))  # transparent bg

    if char == "-":
        draw.rectangle(
            [(0, center - line_width // 2), (canvas_size, center + line_width // 2)],
            fill=FILL_COLOR
        )
    elif char == "|":
        draw.rectangle(
            [(center - line_width // 2, 0), (center + line_width // 2, canvas_size)],
            fill=FILL_COLOR
        )
    elif char == "+":
        draw.rectangle(
            [(0, center - line_width // 2), (canvas_size, center + line_width // 2)],
            fill=FILL_COLOR
        )
        draw.rectangle(
            [(center - line_width // 2, 0), (center + line_width // 2, canvas_size)],
            fill=FILL_COLOR
        )

    os.makedirs(output_folder, exist_ok=True)
    filename = f"{safe_filename(char)}.png"
    canvas.save(os.path.join(output_folder, filename))

    
def safe_filename(char):
    return {
        "|": "vline",
        "-": "hline",
        "+": "cross"
    }.get(char, char)

def generate_grid_markers(x_range, y_range, step):
    pack = ET.Element("Pack", Name="Gridlines", Revision="0")

    # Horizontal lines (Y fixed)
    for y in range(y_range[0] + step, y_range[1] + 1, step):  # skip y=0
        for x in range(x_range[0], x_range[1] + 1, HLINE_SPACING):
            if x % step == 0 and x != 0:
                icon = "cross"
            else:
                icon = "hline"
            marker = ET.Element("Marker", Name=f"{x},{y}", X=str(x), Y=str(y), Icon=icon, Facet="0")
            pack.append(marker)

    # Vertical lines (X fixed)
    for x in range(x_range[0] + step, x_range[1] + 1, step):  # skip x=0
        for y in range(y_range[0], y_range[1] + 1, VLINE_SPACING):
            if y % step == 0:
                continue  # skip cross, already placed
            icon = "vline"
            marker = ET.Element("Marker", Name=f"{x},{y}", X=str(x), Y=str(y), Icon=icon, Facet="0")
            pack.append(marker)

    return pack

# === MAIN ===
def main():
    print("🧱 Generating grid markers...")
    pack = generate_grid_markers(X_RANGE, Y_RANGE, GRID_STEP)

    print("🖼️ Generating icons...")
    for symbol in ICONS:
        # Use the visual character that matches the icon name
        char = {
            "hline": "-",
            "vline": "|",
            "cross": "+"
        }[symbol]
        create_icon(char, OUTPUT_ICON_FOLDER)

    print(f"💾 Writing XML to {OUTPUT_XML}")
    xml_string = ET.tostring(pack, encoding="utf-8")
    pretty = xml.dom.minidom.parseString(xml_string).toprettyxml(indent="  ", encoding="UTF-8")

    with open(OUTPUT_XML, "wb") as f:
        f.write(pretty.replace(b"\n", b"\r\n"))

    print("✅ Done.")

if __name__ == "__main__":
    main()