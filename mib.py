import os
import sys
import ctypes
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import xml.etree.ElementTree as ET

from journal_reader import get_latest_logs
from mib_coord_extractor import get_first_valid_mibs
from run_as_admin import is_running_as_admin, relaunch_as_admin
from ultima_locator import find_ultima_install

# ===== Icon Generator =====
def generate_numbered_icons(base_icon_path, output_folder, counts):
    print(f"🎨 Generating numbered icons for counts: {sorted(counts)}")
    os.makedirs(output_folder, exist_ok=True)

    try:
        base_icon = Image.open(base_icon_path).convert("RGBA")
        icon_w, icon_h = base_icon.size

        non_transparent_pixels = [
            (x, y)
            for y in range(icon_h)
            for x in range(icon_w)
            if base_icon.getpixel((x, y))[3] > 0
        ]
        if not non_transparent_pixels:
            visual_cx, visual_cy = icon_w // 2, icon_h // 2
        else:
            xs, ys = zip(*non_transparent_pixels)
            visual_cx = (min(xs) + max(xs)) // 2
            visual_cy = (min(ys) + max(ys)) // 2

        for count in counts:
            label = str(count)
            icon = base_icon.copy()
            draw = ImageDraw.Draw(icon)

            font_size = int(icon_h * 0.9)
            while font_size > 4:
                try:
                    font = ImageFont.truetype("arialbd.ttf", font_size)
                except:
                    font = ImageFont.load_default()
                bbox = font.getbbox(label)
                text_w = bbox[2] - bbox[0]
                text_h = bbox[3] - bbox[1]
                if text_w <= icon_w and text_h <= icon_h:
                    break
                font_size -= 1

            text_x = visual_cx - text_w // 2
            text_y = visual_cy - text_h // 2

            for dx in [-1, 1]:
                draw.text((text_x + dx, text_y), label, font=font, fill="black")
            for dy in [-1, 1]:
                draw.text((text_x, text_y + dy), label, font=font, fill="black")
            draw.text((text_x, text_y), label, font=font, fill="white")

            output_path = os.path.join(output_folder, f"TREASURE_{label}.png")
            icon.save(output_path)
            print(f"  ✅ Created icon: {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to generate icons: {e}")

# ===== XML Output =====
def create_xml(coord_counts, output_path):
    print(f"🛠️ Creating XML file at {output_path}...")
    try:
        pack = ET.Element("Pack", Name="MIB_locations", Revision="0")
        for (x, y), count in coord_counts.items():
            name = f"{count}"
            icon = f"TREASURE_{count}"
            ET.SubElement(pack, "Marker", Name=name, X=str(x), Y=str(y), Icon=icon, Facet="0")

        tree = ET.ElementTree(pack)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        print(f"✅ Wrote {len(coord_counts)} marker(s) to: {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to write XML: {e}")

def main():
    print("🚀 Starting MIB Extractor Script")

    # Relaunch with admin if needed
    if not is_running_as_admin():
        print("🛡️ Relaunching with admin rights...")
        relaunch_as_admin()
        return  # very important: don't continue current run

        
    client_path = Path(find_ultima_install())
    if not client_path:
        input("Press Enter to exit...")
        return

    journal_log_dir = client_path / "Data" / "Client" / "JournalLogs"
    output_xml_path = client_path / "Data" / "Client" / "Mib_locations.xml"
    icon_folder = client_path / "Data" / "Client" / "MapIcons"
    icon_source = icon_folder / "TREASURE.png"

    if not icon_source.exists():
        print(f"❌ Missing base treasure icon: {icon_source}")
        input("Press Enter to exit...")
        return

    latest_logs = get_latest_logs(journal_log_dir, max_logs=20)

    mibs = []
    total = 0
    for log in latest_logs:
        mibs, total = get_first_valid_mibs([log])
        if mibs:
            print(f"📄 Using log file: {log.name}")
            break

    if not mibs:
        print("⚠️ No SOS messages found in the latest logs.")
        input("Press Enter to exit...")
        return


    coord_counts = defaultdict(int)
    for entry in mibs:
        coord_counts[(entry["x"], entry["y"])] += 1

    icon_counts = set(coord_counts.values())
    generate_numbered_icons(str(icon_source), str(icon_folder), icon_counts)
    create_xml(coord_counts, str(output_xml_path))

    print("✅ Done.")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
