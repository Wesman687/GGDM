import asyncio
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
    if not client_path:
        print("⚠️ Could not auto-detect Ultima Online installation.")
        client_path = prompt_user_for_folder()

    if not client_path or not client_path.exists():
        print("❌ No valid folder selected. Exiting.")
        return

    for file_info in FILES_TO_DOWNLOAD:
        full_url = GITHUB_BASE_URL + file_info["filename"].replace(" ", "%20")  # Encode spaces
        print(f"🌐 Fetching {file_info['filename']} from GitHub...")

        response = requests.get(full_url)
        if response.status_code != 200:
            print(f"❌ Failed to download {file_info['filename']}: HTTP {response.status_code}")
            continue

        lines = response.text.strip().splitlines()
        markers = []
        for line in lines:
            marker = parse_line(line, file_info["icon"])
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