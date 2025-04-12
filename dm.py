
import os
import xml.etree.ElementTree as ET
import xml.dom.minidom
import requests
from pathlib import Path
import ctypes
import sys
from tkinter import filedialog, Tk
import os


# Constants
GITHUB_RAW_URL = "https://raw.githubusercontent.com/LeoPiro/GG_Dms/main/GG%20DOCKMASTERS.txt"
RELATIVE_XML_PATH = r"ClassicUO\\Data\\Client\\GG_Dockmasters.xml"
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

def parse_line(line):
    if not line.startswith("+"):
        return None
    parts = line[1:].strip().split()
    if len(parts) >= 3:
        name, x, y = parts[0], parts[1], parts[2]
        return ET.Element("Marker", Name=name, X=x, Y=y, Icon="shipwright", Facet="0")
    return None

def update_dockmasters():
    print("🌐 Fetching from GitHub...")
    response = requests.get(GITHUB_RAW_URL)
    if response.status_code != 200:
        print(f"❌ Failed to download file: HTTP {response.status_code}")
        return

    lines = response.text.strip().splitlines()
    markers = []
    for line in lines:
        marker = parse_line(line)
        if marker is not None:
            markers.append(marker)

    print(f"✅ Parsed {len(markers)} markers.")

    pack = ET.Element("Pack", Name="GG DOCKMASTERS", Revision="0")
    for marker in markers:
        pack.append(marker)

    rough_string = ET.tostring(pack, encoding="utf-8")
    reparsed = xml.dom.minidom.parseString(rough_string)
    pretty_xml = reparsed.toprettyxml(indent="  ")

    client_path = search_for_game_folder()

    # If not found, prompt GUI
    if not client_path:
        print("⚠️ Could not auto-detect Ultima Online installation.")
        client_path = prompt_user_for_folder()

    # Validate and set full XML output path
    if not client_path or not client_path.exists():
        print("❌ No valid folder selected. Exiting.")
        return

    xml_path = client_path / "GG_Dockmasters.xml"
    os.makedirs(xml_path.parent, exist_ok=True)

    print(f"💾 Writing to {xml_path}")
    with open(xml_path, "w", encoding="utf-8") as f:
        f.write(pretty_xml)

    print("🎉 GG_Dockmasters.xml successfully updated.")

if __name__ == "__main__":
    if not is_admin():
        print("🛡️ Restarting with admin privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, __file__, None, 1)
    else:
        update_dockmasters()
