import asyncio
import json
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
import requests
from pathlib import Path
import ctypes
import sys
from tkinter import filedialog, Tk

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

# Your known original Outlands standard icons
TOP_ICONS = [
    "shipwright", "landmark", "treasurechest", "bank", "moongate",
    "vendor", "citygate", "shrine", "stable", "dungeon",
    "blacksmith", "healer", "tavern", "dock", "house",
    "arena", "church", "guildhall", "mine", "portal"
]

def list_available_icons(mapicons_path):
    icons = []
    for file in os.listdir(mapicons_path):
        if file.lower().endswith(".png"):
            icon_name = os.path.splitext(file)[0]
            icons.append(icon_name)
    return sorted(icons)

    
def detect_custom_icons(mapicons_path):
    # Load original icons list
    try:
        with open(get_resource_path("original_icons.json"), "r") as f:
            original_icons = set(json.load(f))
    except Exception as e:
        print(f"⚠️ Failed to load original_icons.json: {e}")
        return []

    # Scan current icons
    all_icons = list_available_icons(mapicons_path)

    # Detect truly new icons
    custom_icons = [icon for icon in all_icons if icon not in original_icons]
    return sorted(custom_icons)

def prompt_icon_selection(file_display_name, icon_choices, default_icon, file_name):
    print(f"\n🌟 Choose an icon for {file_display_name}")
    print(f"(Press Enter to use default: '{default_icon}')")
    print(f"(Or type a custom icon name manually)")

    page_size = 20
    total = len(icon_choices)
    current_index = 0

    while True:
        print()
        print_icons_in_columns(icon_choices[current_index:current_index+page_size], start_index=current_index)
        
        choice = input(f"Select an icon number for {file_name}, custom name, or press Enter to show more: ").strip()

        if choice == "":
            current_index += page_size
            if current_index >= total:
                print("\n🚀 You've reached the end of the list. Showing all icons again.")
                current_index = 0
        else:
            try:
                idx = int(choice) - 1
                if 0 <= idx < total:
                    return icon_choices[idx]
            except ValueError:
                # Assume user typed custom name
                return choice
            print(f"⚠️ Invalid input. Please try again.")

def print_icons_in_columns(icon_choices, columns=4, start_index=0):
    for offset, icon_name in enumerate(icon_choices, start=start_index+1):
        print(f"[{offset:<3}] {icon_name:<15}", end=' ')
        if (offset) % columns == 0:
            print()
    print()


def search_for_game_folder():
    search_roots = [
        os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
        os.environ.get("ProgramW6432", r"C:\Program Files"),
        r"C:\Games",
        os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local"),
        os.path.join(os.environ.get("USERPROFILE", ""), "Documents"),
    ]
    target_ending = os.path.join("ClassicUO", "Data", "Client")

    for root in search_roots:
        for dirpath, dirnames, filenames in os.walk(root):
            if dirpath.endswith(target_ending):
                return Path(dirpath)

    return None

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
    
def ask_use_defaults():
    print("\n🔵 Do you want to use the default icons?")
    print("    [1] Yes (Recommended)")
    print("    [2] No, I want to choose icons manually")
    choice = input("Select 1 or 2: ").strip()
    return choice != "2"  # Return True if user picks default

def parse_line(line, icon):
    if not line.startswith("+"):
        return None
    parts = line[1:].strip().split()
    if len(parts) >= 5:
        name = " ".join(parts[:-4])  # Everything before the last 4 values
        x, y = parts[-4], parts[-3]
        return ET.Element("Marker", Name=name, X=x, Y=y, Icon=icon, Facet="0")
    return None

def update_markers():
    client_path = search_for_game_folder()
    use_defaults = ask_use_defaults()
    mapicons_path = Path(r"C:\Program Files (x86)\Ultima Online Outlands\ClassicUO\Data\Client\MapIcons")
    custom_icons = detect_custom_icons(mapicons_path)
    if not client_path:
        print("⚠️ Could not auto-detect Ultima Online installation.")
        client_path = prompt_user_for_folder()

    if not client_path or not client_path.exists():
        print("❌ No valid folder selected. Exiting.")
        return

    for file_info in FILES_TO_DOWNLOAD:
        if use_defaults:
            selected_icon = file_info["icon"]
        else:
            # Use custom icons if available, otherwise fallback to original icons
            if custom_icons:
                icon_choices = custom_icons
            else:
                # Load original icons.json
                try:
                    with open("original_icons.json", "r") as f:
                        icon_choices = json.load(f)
                except Exception as e:
                    print(f"⚠️ Failed to load original_icons.json: {e}")
                    icon_choices = TOP_ICONS  # fallback emergency

            selected_icon = prompt_icon_selection(file_info["pack_name"], icon_choices, file_info["icon"], file_info['filename'])
            
        full_url = GITHUB_BASE_URL + file_info["filename"].replace(" ", "%20")  # Encode spaces
        print(f"🌐 Fetching {file_info['filename']} from GitHub...")

        response = requests.get(full_url)
        if response.status_code != 200:
            print(f"❌ Failed to download {file_info['filename']}: HTTP {response.status_code}")
            continue

        lines = response.text.strip().splitlines()
        markers = []
        for line in lines:
            marker = parse_line(line, selected_icon)
            if marker is not None:
                markers.append(marker)

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
    if not is_admin():
        print("🛡️ Restarting with admin privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    else:
        update_markers()
        input("\n✅ Script finished. Press Enter to exit...")