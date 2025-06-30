from logging import root
import os
import re
import string
import traceback
import xml.etree.ElementTree as ET
import xml.dom.minidom
import requests
from pathlib import Path
import ctypes
import sys
from tkinter import filedialog, Tk
from PIL import Image, ImageDraw, ImageFont
import os
DEBUG_MODE = os.getenv("DM_DEBUG", "0") == "1"

def log_debug(message):
    if DEBUG_MODE:
        with open("marker_debug.log", "a", encoding="utf-8") as log:
            log.write(message + "\n")

def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)


TREASURE_COLOR = "#FF33CC"
DOCKMASTER_COLOR = "#00FFFF"

# Constants
GITHUB_BASE_URL = "https://raw.githubusercontent.com/LeoPiro/GG_Dms/main/"
FILES_TO_DOWNLOAD = [
    {
        "filename": "GG DOCKMASTERS.txt",
        "output_xml": "GG_Dockmasters.xml",
        "pack_name": "GG DOCKMASTERS",
        "icon": "shipwright"
    },
    {
        "filename": "PUBLIC DOCKMASTERS.txt",
        "output_xml": "Public_Dockmasters.xml",
        "pack_name": "Public DOCKMASTERS",
        "icon": "shipwright"
    },
    {
        "filename": "TREASURE.txt",
        "output_xml": "Treasure_Map_Locations.xml",
        "pack_name": "Treasure Map Locations",
        "icon": "landmark"
    },
]

DEFAULT_INSTALL_PATH = r"C:\\Program Files (x86)\\Ultima Online Outlands"


def split_name(name):
    if '-' in name:
        top, bottom = name.split('-', 1)
        return top.strip().upper(), bottom.strip().upper()
    match = re.match(r"^([A-Z]+)(\d+)$", name, re.IGNORECASE)
    if match:
        return match.group(1).upper(), match.group(2)
    return name.upper(), ""

def is_treasure_marker(name):
    return re.match(r"^(N|E|S|W|CC|X)\d+$", name.upper())


def is_dockmaster_marker(name):
    name = name.upper()
    return (
        re.match(r"^\d+[A-Z]-[NESW]$", name) or       # e.g., 1A-W
        re.match(r"^XD\d+$", name) or                # e.g., XD13
        re.match(r"^XP\d+$", name) or                # e.g., XP2
        re.match(r"^PUB[-]?(X\d+|\d+)$", name) or     # e.g., PUB-X3, PUB9
        re.match(r"^M(?:[1-9]|1[0-9]|2[0-9]|30)$", name)  # M1–M30
    )

def is_large_marker(name):
    name = name.upper()
    return re.match(r"^M(?:[1-9]|1[0-9]|2[0-9]|30)$", name) is not None

def create_marker_icon(name, output_dir, base_top_font, base_bottom_font):
    try:
        log_debug(f"== Creating icon: {name}")
        log_debug(f"Output folder: {output_dir}")

        top_text, bottom_text = split_name(name)

        if is_treasure_marker(name):
            color = TREASURE_COLOR
        elif is_dockmaster_marker(name):
            color = DOCKMASTER_COLOR
        else:
            color = "gray"

        # === M-marker logic ===
        if is_large_marker(name):
            icon_size = 108
            canvas_size = 256  # Add transparency padding
            top_font = ImageFont.truetype(base_top_font.path, base_top_font.size * 2)
            bottom_font = ImageFont.truetype(base_bottom_font.path, base_bottom_font.size * 2)
        else:
            icon_size = 54
            canvas_size = 54
            top_font = base_top_font
            bottom_font = base_bottom_font

        # === Create canvas (with or without padding)
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # === If padding, draw in center; else, draw normally
        draw_x = (canvas_size - icon_size) // 2
        draw_y = (canvas_size - icon_size) // 2

        # === Sub-layer for drawing text (optional but cleaner)
        icon_layer = Image.new("RGBA", (icon_size, icon_size), (0, 0, 0, 0))
        icon_draw = ImageDraw.Draw(icon_layer)

        # === Text positioning
        top_bbox = icon_draw.textbbox((0, 0), top_text, font=top_font)
        top_width, top_height = top_bbox[2] - top_bbox[0], top_bbox[3] - top_bbox[1]
        top_x = (icon_size - top_width) // 2
        top_y = 2

        bottom_bbox = icon_draw.textbbox((0, 0), bottom_text, font=bottom_font)
        bottom_width = bottom_bbox[2] - bottom_bbox[0]
        spacing = 4
        bottom_x = (icon_size - bottom_width) // 2
        bottom_y = top_y + top_height + spacing

        # === Draw text with shadow
        for x_off in [-1, 0, 1]:
            for y_off in [-1, 0, 1]:
                if x_off or y_off:
                    icon_draw.text((top_x + x_off, top_y + y_off), top_text, font=top_font, fill="black")
                    icon_draw.text((bottom_x + x_off, bottom_y + y_off), bottom_text, font=bottom_font, fill="black")

        icon_draw.text((top_x, top_y), top_text, font=top_font, fill=color)
        icon_draw.text((bottom_x, bottom_y), bottom_text, font=bottom_font, fill=color)

        # === Paste small icon layer into main canvas (centered for M-markers)
        canvas.paste(icon_layer, (draw_x, draw_y), icon_layer)

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{name}.png")
        canvas.save(output_file)
        log_debug(f"✅ Saved icon to: {output_file}")

    except Exception as e:
        log_debug(f"❌ Failed to create icon for {name}: {e}")
        log_debug(traceback.format_exc())


def get_all_windows_drives():
    """Returns a list of all available drive letters on Windows, like ['C:\\', 'D:\\']"""
    drives = []
    bitmask = ctypes.windll.kernel32.GetLogicalDrives()
    for i in range(26):
        if bitmask & (1 << i):
            drives.append(f"{string.ascii_uppercase[i]}:\\")
    return drives

def walk_root(root, target_ending):
    local_found = []
    if not root or not os.path.exists(root):
        return local_found

    for dirpath, dirnames, filenames in os.walk(root):
        if dirpath.count(os.sep) - root.count(os.sep) > 4:
            dirnames[:] = []
            continue

        if dirpath.lower().endswith(target_ending.lower()):
            local_found.append(Path(dirpath))
    return local_found


def split_dockmaster_name(name):
    """
    Splits a name like '1A-W' into ('1A', 'W') or 'XD10' into ('XD', '10').
    Returns a tuple: (top_text, bottom_text)
    """
    # Handle hyphenated names like '1A-W'
    if '-' in name:
        top, bottom = name.split('-', 1)
        return top.strip().upper(), bottom.strip().upper()
    
    # Handle non-hyphen dockmasters like 'XD13' or 'XP2'
    match = re.match(r"^([A-Z]+)(\d+)$", name, re.IGNORECASE)
    if match:
        top, bottom = match.groups()
        return top.upper(), bottom

    return name.upper(), ""  # fallback for names like "GH" or "Gym"


import concurrent.futures

def search_for_game_folders():
    """Search for all ClassicUO/Data/Client folders across all drives, with fallback to full-drive scan."""
    target_ending = os.path.join("ClassicUO", "Data", "Client")
    found = []

    all_drives = get_all_windows_drives()

    # Build root paths like D:\Games, D:\Program Files, etc.
    search_roots = []
    for drive in all_drives:
        search_roots.extend([
            os.path.join(drive, "Program Files"),
            os.path.join(drive, "Program Files (x86)"),
            os.path.join(drive, "Games"),
            os.path.join(drive, "Users"),
            os.path.join(drive, "ProgramData"),
        ])

    def run_search(roots):
        local_results = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(walk_root, root, target_ending) for root in roots]
            for future in concurrent.futures.as_completed(futures):
                try:
                    result = future.result()
                    local_results.extend(result)
                except Exception as e:
                    print(f"⚠️ Error searching {root}: {e}")
        return local_results

    # Initial search (quick, shallow)
    found = run_search(search_roots)

    # Fallback: deep search across entire drives
    if not found:
        print("🔍 No folders found in standard locations. Falling back to full-drive scan...")
        log_debug("Not Found in normal drive, searching for multiple drives.")
        found = run_search(all_drives)

    return found


def get_resource_path(relative_path):
    """ Get the absolute path to a resource, works for dev and for PyInstaller bundled exe """
    if hasattr(sys, '_MEIPASS'):
        # If running in a PyInstaller bundle
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

def prompt_user_for_folder():
    root = Tk()
    root.withdraw()
    path = filedialog.askdirectory(title="Select the 'Client' folder inside Ultima Online Outlands")
    return Path(path) if path else None

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    
def custom_sort(marker):
    name = marker.attrib.get('Name', '').upper()

    match = re.match(r"^(N|E|S|W|CC|X)(\d+)$", name)
    dock_match = re.match(r"^(XD|XP|PUB-X)(\d+)$", name)

    if match:
        prefix, number = match.groups()
        return (0, prefix, int(number))

    elif dock_match:
        prefix, number = dock_match.groups()
        return (0, prefix, int(number))

    else:
        return (1, name)
    

def parse_line(line, default_icon):
    if not line.startswith("+"):
        return None
    parts = line[1:].strip().split()
    if len(parts) >= 5:
        name = " ".join(parts[:-4])
        x, y = parts[-4], parts[-3]

        if is_treasure_marker(name) or is_dockmaster_marker(name):
            icon = name  # use marker name
        else:
            icon = default_icon  # fallback to default (e.g., 'shipwright')

        return ET.Element("Marker", Name=name, X=x, Y=y, Icon=icon, Facet="0")
    return None

def ensure_icon_exists(icon_name, output_folder, top_font, bottom_font):
    if is_treasure_marker(icon_name) or is_dockmaster_marker(icon_name):
        create_marker_icon(icon_name, output_folder, top_font, bottom_font)
            

def install_gridlines(mapicons_path, client_path, FILL_COLOR=(180, 180, 180, 180)):
    print("🧱 Generating gridline markers and icon...")
    log_debug("📐 install_gridlines() called")

    # === Grid config ===
    GRID_STEP = 1000
    X_RANGE = (0, 4700)
    Y_RANGE = (0, 6100)
    canvas_size = 128
    center = canvas_size // 2
    HLINE_SPACING = 10
    VLINE_SPACING = 10
    icon_name = "gridline"

    # === Draw single line icon ===
    def draw_gridline_icon():
        log_debug("🎨 Drawing shared gridline icon")
        icon = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(icon)
        dot_size = 3
        half = dot_size // 2
        draw.rectangle(
            [(center - half, center - half), (center + half, center + half)],
            fill=FILL_COLOR
        )
        try:
            os.makedirs(mapicons_path, exist_ok=True)
            save_path = mapicons_path / f"{icon_name}.png"
            icon.save(save_path)
            log_debug(f"💾 Saved gridline icon: {save_path}")
        except Exception as e:
            log_debug(f"❌ Failed to save icon: {e}")

    draw_gridline_icon()

    # === Build XML markers ===
    pack = ET.Element("Pack", Name="Gridlines", Revision="0")

    for y in range(Y_RANGE[0] + GRID_STEP, Y_RANGE[1] + 1, GRID_STEP):
        for x in range(X_RANGE[0], X_RANGE[1] + 1, HLINE_SPACING):
            marker = ET.Element("Marker", Name=f"{x},{y}", X=str(x), Y=str(y), Icon=icon_name, Facet="0")
            pack.append(marker)

    for x in range(X_RANGE[0] + GRID_STEP, X_RANGE[1] + 1, GRID_STEP):
        for y in range(Y_RANGE[0], Y_RANGE[1] + 1, VLINE_SPACING):
            if y % GRID_STEP == 0:
                continue
            marker = ET.Element("Marker", Name=f"{x},{y}", X=str(x), Y=str(y), Icon=icon_name, Facet="0")
            pack.append(marker)

    # === Save XML ===
    xml_string = ET.tostring(pack, encoding="utf-8")
    pretty = xml.dom.minidom.parseString(xml_string).toprettyxml(indent="  ", encoding="UTF-8")

    gridlines_xml_path = client_path / "Gridlines.xml"
    try:
        with open(gridlines_xml_path, "wb") as f:
            f.write(pretty.replace(b"\n", b"\r\n"))
        print(f"✅ Gridlines.xml written to {gridlines_xml_path}")
        log_debug(f"✅ Gridlines.xml written to {gridlines_xml_path}")
    except Exception as e:
        print(f"❌ Failed to write Gridlines.xml: {e}")
        log_debug(f"❌ Failed to write Gridlines.xml: {e}")

    
def update_markers():
    try:
        log_debug("🔧 Starting update_markers()")

        font_path = get_resource_path("DejaVuSans-Bold.ttf")
        log_debug(f"📁 Font path resolved to: {font_path}")

        try:
            top_font = ImageFont.truetype(font_path, 12)
            bottom_font = ImageFont.truetype(font_path, 16)
            log_debug("✅ Custom TTF font loaded successfully.")
        except IOError as e:
            log_debug(f"⚠️ Failed to load TTF font: {e}")
            print("⚠️ Couldn't load embedded TTF font, using default.")
            top_font = ImageFont.load_default()
            bottom_font = ImageFont.load_default()

        client_paths = search_for_game_folders()
        log_debug(f"🔍 Detected game folders: {client_paths}")

        if not client_paths:
            print("⚠️ Could not auto-detect any Ultima Online installations.")
            client_path = prompt_user_for_folder()
            log_debug(f"🧭 User selected folder: {client_path}")
        elif len(client_paths) == 1:
            client_path = client_paths[0]
            log_debug(f"✅ Single client path auto-selected: {client_path}")
        else:
            print("🔍 Multiple Ultima Online installations found:")
            for idx, path in enumerate(client_paths):
                print(f"  [{idx+1}] {path}")
                log_debug(f"  [{idx+1}] {path}")

            while True:
                choice = input(f"\nPlease select which installation to update (1 - {len(client_paths)}): ")
                if choice.isdigit():
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(client_paths):
                        client_path = client_paths[choice_idx]
                        log_debug(f"✅ User selected client path: {client_path}")
                        break
                print("⚠️ Invalid choice. Try again.")
                log_debug("⚠️ Invalid choice input received.")

        if not client_path or not client_path.exists():
            print("❌ No valid folder selected. Exiting.")
            log_debug("❌ No valid client path selected. Exiting early.")
            return

        mapicons_path = client_path / "MapIcons"
        log_debug(f"🖼️ Icon output path: {mapicons_path}")

        # === Update regular marker packs ===
        for file_info in FILES_TO_DOWNLOAD:
            selected_icon = file_info["icon"]
            full_url = GITHUB_BASE_URL + file_info["filename"].replace(" ", "%20")
            log_debug(f"🌐 Fetching: {file_info['filename']} → {full_url}")

            response = requests.get(full_url)
            if response.status_code != 200:
                print(f"❌ Failed to download {file_info['filename']}: HTTP {response.status_code}")
                log_debug(f"❌ Download failed: {file_info['filename']} → HTTP {response.status_code}")
                continue

            lines = response.text.strip().splitlines()
            log_debug(f"📄 Downloaded {len(lines)} lines from {file_info['filename']}")
            markers = []

            for line in lines:
                marker = parse_line(line, selected_icon)
                if marker is not None:
                    icon_name = marker.attrib.get("Icon")
                    log_debug(f"🔧 Ensuring icon exists: {icon_name}")
                    ensure_icon_exists(icon_name, mapicons_path, top_font, bottom_font)
                    markers.append(marker)

            markers.sort(key=custom_sort)
            log_debug(f"✅ Parsed and sorted {len(markers)} markers from {file_info['filename']}")

            # Write XML
            pack = ET.Element("Pack", Name=file_info["pack_name"], Revision="0")
            for marker in markers:
                pack.append(marker)

            rough_string = ET.tostring(pack, encoding="utf-8")
            reparsed = xml.dom.minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8")

            xml_path = client_path / file_info["output_xml"]
            os.makedirs(xml_path.parent, exist_ok=True)

            print(f"💾 Writing {file_info['output_xml']}")
            log_debug(f"💾 Writing XML to: {xml_path}")
            try:
                with open(xml_path, "wb") as f:
                    f.write(pretty_xml.replace(b"\n", b"\r\n"))
                print(f"🎉 {file_info['output_xml']} successfully updated.")
                log_debug(f"🎉 {file_info['output_xml']} written successfully.")
            except Exception as e:
                print(f"❌ Failed to write {file_info['output_xml']}: {e}")
                log_debug(f"❌ Failed to write XML {file_info['output_xml']}: {e}")

        # === Prompt for gridlines AFTER all standard packs are handled ===
        install_grid = input("📐 Do you want to install gridlines? (y/n): ").strip().lower()
        if install_grid == "y":
            log_debug("🧱 User chose to install gridlines.")
            print("\n🎨 Choose a gridline color:")
            preset_colors = {
                "1": ("Light Gray", (180, 180, 180)),
                "2": ("Cyan", (0, 255, 255)),
                "3": ("Red", (255, 80, 80)),
                "4": ("Green", (80, 255, 80)),
                "5": ("Yellow", (255, 255, 100)),
                "6": ("Orange", (255, 165, 0)),
                "7": ("Purple", (160, 32, 240)),
                "8": ("Pink", (255, 105, 180)),
                "9": ("White", (255, 255, 255)),
                "10": ("Custom RGB (e.g. 100,100,100)", None),
            }

            for key, (label, _) in preset_colors.items():
                print(f"  [{key}] {label}")

            color_choice = input("Select a color preset [1–10]: ").strip()
            if color_choice in preset_colors and color_choice != "10":
                base_rgb = preset_colors[color_choice][1]
            else:
                custom_input = input("Enter custom RGB (comma or space-separated, e.g. 60,60,60 or 60 60 60): ").strip()
                try:
                    base_rgb = tuple(int(c.strip()) for c in custom_input.replace(" ", ",").split(","))
                    if len(base_rgb) != 3:
                        raise ValueError()
                except Exception:
                    print("⚠️ Invalid format. Using default light gray.")
                    base_rgb = (180, 180, 180)

            FILL_COLOR = base_rgb + (255,)


            install_gridlines(mapicons_path, client_path, FILL_COLOR)
        else:
            log_debug("🧱 User skipped gridline installation.")
            gridline_path = client_path / "Gridlines.xml"
            if gridline_path.exists():
                try:
                    os.remove(gridline_path)
                    print("🧹 Removed existing Gridlines.xml")
                    log_debug("🧹 Removed Gridlines.xml because user chose not to install.")
                except Exception as e:
                    print(f"⚠️ Failed to remove Gridlines.xml: {e}")
                    log_debug(f"⚠️ Failed to delete Gridlines.xml: {e}")

    except Exception as e:
        print("❌ Error in update_markers()")
        log_debug(f"❌ Exception in update_markers(): {e}")
        log_debug(traceback.format_exc())



if __name__ == "__main__":
    try:
        if DEBUG_MODE:
            with open("marker_debug.log", "w", encoding="utf-8") as log:
                log.write("=== Debug Log Started ===\n")

        if not is_admin():
            print("🛡️ Restarting with admin privileges...")
            if getattr(sys, 'frozen', False):  # Running as bundled EXE
                exe_path = sys.executable
                params = ""
            else:  # Running as .py
                exe_path = sys.executable
                params = f'"{os.path.abspath(__file__)}"'

            ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, params, None, 1)
            sys.exit()

        # 🧠 Only elevated process runs the updater
        update_markers()

    except Exception as e:
        print("\n❌ An unexpected error occurred:")
        if DEBUG_MODE:
            log_debug("❌ Unexpected exception occurred:")
            log_debug(traceback.format_exc())  # ✅ this is how to capture the actual traceback
        traceback.print_exc()