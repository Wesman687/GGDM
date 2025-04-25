import os
import re
import traceback
import xml.etree.ElementTree as ET
import xml.dom.minidom
import requests
from pathlib import Path
import ctypes
import sys
from tkinter import filedialog, Tk
from PIL import Image, ImageDraw, ImageFont

def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)


TREASURE_COLOR = "purple"
DOCKMASTER_COLOR = "blue"

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
        re.match(r"^\d+[A-Z]-[NESW]$", name) or  # e.g., 1A-W
        re.match(r"^XD\d+$", name) or           # e.g., XD13
        re.match(r"^XP\d+$", name) or           # e.g., XP2
        re.match(r"^PUB[-]?(X\d+|\d+)$", name)   # e.g., PUB-X3, PUB9
    )

def create_marker_icon(name, output_dir, top_font, bottom_font):
    top_text, bottom_text = split_name(name)

    if is_treasure_marker(name):
        color = TREASURE_COLOR
    elif is_dockmaster_marker(name):
        color = DOCKMASTER_COLOR
    else:
        color = "gray"

    width, height = 54, 54
    canvas = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)

    # Measure text
    top_bbox = draw.textbbox((0, 0), top_text, font=top_font)
    top_width, top_height = top_bbox[2] - top_bbox[0], top_bbox[3] - top_bbox[1]
    top_x = (width - top_width) // 2
    top_y = 2

    bottom_bbox = draw.textbbox((0, 0), bottom_text, font=bottom_font)
    bottom_width = bottom_bbox[2] - bottom_bbox[0]
    bottom_x = (width - bottom_width) // 2

    # Add fixed space between top and bottom
    spacing = 4
    bottom_y = top_y + top_height + spacing

    # Draw outline
    for x_off in [-1, 0, 1]:
        for y_off in [-1, 0, 1]:
            if x_off or y_off:
                draw.text((top_x + x_off, top_y + y_off), top_text, font=top_font, fill="black")
                draw.text((bottom_x + x_off, bottom_y + y_off), bottom_text, font=bottom_font, fill="black")

    # Draw main text
    draw.text((top_x, top_y), top_text, font=top_font, fill=color)
    draw.text((bottom_x, bottom_y), bottom_text, font=bottom_font, fill=color)

    os.makedirs(output_dir, exist_ok=True)
    canvas.save(os.path.join(output_dir, f"{name}.png"))



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
    """Fast search for all Ultima Online folders across multiple roots."""
    search_roots = [
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramW6432", r"C:\Program Files"),
        r"C:\Games",
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local"),
        os.environ.get("PROGRAMDATA", r"C:\ProgramData"),  # Fixed
        os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
    ]

    target_ending = os.path.join("ClassicUO", "Data", "Client")
    found = []

    def walk_root(root):
        local_found = []
        if not root or not os.path.exists(root):
            return local_found

        for dirpath, dirnames, filenames in os.walk(root):
            # ✅ Limit how deep we search (e.g. max 5 levels deep)
            if dirpath.count(os.sep) - root.count(os.sep) > 4:
                # prevent going deeper by clearing dirnames
                dirnames[:] = []
                continue

            if dirpath.lower().endswith(target_ending.lower()):
                found.append(Path(dirpath))
        return local_found

    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(walk_root, root) for root in search_roots]
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                found.extend(result)
            except Exception as e:
                print(f"⚠️ Error searching: {e}")

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
            

def update_markers():
    try:
        font_path = get_resource_path("DejaVuSans-Bold.ttf")
        top_font = ImageFont.truetype(font_path, 12)
        bottom_font = ImageFont.truetype(font_path, 16)
    except IOError:
        print("⚠️ Couldn't load embedded TTF font, using default.")
        top_font = ImageFont.load_default()
        bottom_font = ImageFont.load_default()
        
    client_paths = search_for_game_folders()
    mapicons_path = Path(r"C:\Program Files (x86)\Ultima Online Outlands\ClassicUO\Data\Client\MapIcons")
    if not client_paths:
        print("⚠️ Could not auto-detect any Ultima Online installations.")
        client_path = prompt_user_for_folder()
    elif len(client_paths) == 1:
        client_path = client_paths[0]
    else:
        print("🔍 Multiple Ultima Online installations found:")
        for idx, path in enumerate(client_paths):
            print(f"  [{idx+1}] {path}")

        while True:
            choice = input("\nPlease select which installation to update (1 - {}): ".format(len(client_paths)))
            if choice.isdigit():
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(client_paths):
                    client_path = client_paths[choice_idx]
                    break
            print("⚠️ Invalid choice. Try again.")

    if not client_path or not client_path.exists():
        print("❌ No valid folder selected. Exiting.")
        return

    for file_info in FILES_TO_DOWNLOAD:
        selected_icon = file_info["icon"]            
        full_url = GITHUB_BASE_URL + file_info["filename"].replace(" ", "%20")
        print(f"🌐 Fetching {file_info['filename']} from GitHub...")
        response = requests.get(full_url)
        if response.status_code != 200:
            print(f"❌ Failed to download {file_info['filename']}: HTTP {response.status_code}")
            continue

        lines = response.text.strip().splitlines()
        markers = []

        # ⬇️ FIX: Move this block INTO the file loop
        for line in lines:
            marker = parse_line(line, selected_icon)
            if marker is not None:
                icon_name = marker.attrib.get("Icon")
                ensure_icon_exists(icon_name, mapicons_path, top_font, bottom_font)
                markers.append(marker)

        markers.sort(key=custom_sort)
        print(f"✅ Parsed {len(markers)} markers from {file_info['filename']}.")

        # Build XML
        pack = ET.Element("Pack", Name=file_info["pack_name"], Revision="0")
        for marker in markers:
            pack.append(marker)

        rough_string = ET.tostring(pack, encoding="utf-8")
        reparsed = xml.dom.minidom.parseString(rough_string)
        pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8")

        # Write XML
        xml_path = client_path / file_info["output_xml"]
        os.makedirs(xml_path.parent, exist_ok=True)

        print(f"💾 Writing {file_info['output_xml']}")
        try:
            with open(xml_path, "wb") as f:
                f.write(pretty_xml.replace(b"\n", b"\r\n"))
            print(f"🎉 {file_info['output_xml']} successfully updated.")
        except Exception as e:
            print(f"❌ Failed to write {file_info['output_xml']}: {e}")


if __name__ == "__main__":
    try:
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

        # 🧠 Now *only* the elevated process actually runs the updater
        update_markers()

    except Exception as e:
        print("\n❌ An unexpected error occurred:")
        traceback.print_exc()
        
