import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
from PIL import Image, ImageDraw, ImageFont

# === CONFIG ===
OUTPUT_XML = "Gridlines.xml"
OUTPUT_ICON_FOLDER = "MapIcons"
GRID_STEP = 1000
X_RANGE = (0, 6000)
Y_RANGE = (0, 1000)
ICONS = ["hline", "vline", "cross"]

def create_icon(char, output_folder):
    width, height = 54, 54
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 32)
    except IOError:
        font = ImageFont.load_default()

    text_width, text_height = draw.textbbox((0, 0), char, font=font)[2:]
    x = (width - text_width) // 2
    y = (height - text_height) // 2

    for dx in [-1, 0, 1]:
        for dy in [-1, 0, 1]:
            if dx or dy:
                draw.text((x + dx, y + dy), char, font=font, fill="black")

    draw.text((x, y), char, font=font, fill="cyan")

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

    # Horizontal lines (Y fixed, X varies)
    for y in range(y_range[0], y_range[1] + 1, step):
        for x in range(x_range[0], x_range[1] + 1, step // 10):  # finer spacing
            if x % step == 0:
                icon = "cross"
            else:
                icon = "hline"
            marker = ET.Element("Marker", Name=f"{x},{y}", X=str(x), Y=str(y), Icon=icon, Facet="0")
            pack.append(marker)

    # Vertical lines (X fixed, Y varies)
    for x in range(x_range[0], x_range[1] + 1, step):
        for y in range(y_range[0], y_range[1] + 1, step // 10):  # finer spacing
            if y % step == 0:
                continue  # already placed cross or hline
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