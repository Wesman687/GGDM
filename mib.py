import os
import re
import sys
import ctypes
import string
import concurrent.futures
from tkinter import filedialog, Tk
from pathlib import Path
from collections import defaultdict
from PIL import Image, ImageDraw, ImageFont
import xml.etree.ElementTree as ET

SOS_PATTERN = re.compile(r"Razor: a waterstained SOS message \(located at (\d+), (\d+)\)", re.IGNORECASE)

# ===== Admin Check =====
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception as e:
        print(f"[ERROR] Admin check failed: {e}")
        return False

def restart_as_admin():
    print("🛡️ Restarting with admin privileges...")
    if getattr(sys, 'frozen', False):
        exe_path = sys.executable
        params = ""
    else:
        exe_path = sys.executable
        params = f'"{os.path.abspath(__file__)}"'

    ctypes.windll.shell32.ShellExecuteW(None, "runas", exe_path, params, None, 1)
    sys.exit()

# ===== Install Location Search =====
def get_all_windows_drives():
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

def search_for_game_folders():
    target_ending = os.path.join("ClassicUO", "Data", "Client")
    found = []
    all_drives = get_all_windows_drives()

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
                    print(f"⚠️ Error searching a root: {e}")
        return local_results

    found = run_search(search_roots)

    if not found:
        print("🔍 No folders found in standard locations. Falling back to full-drive scan...")
        found = run_search(get_all_windows_drives())

    return found

def prompt_user_for_folder():
    root = Tk()
    root.withdraw()
    path = filedialog.askdirectory(title="Select the 'Client' folder inside Ultima Online Outlands")
    return Path(path) if path else None

def find_ultima_folder():
    print("🔎 Searching for Ultima Online Outlands installation...")
    found = search_for_game_folders()
    if found:
        print(f"✅ Found installation: {found[0]}")
        return found[0]
    else:
        print("❌ No installation found automatically.")
        selected = prompt_user_for_folder()
        if selected and (selected / "JournalLogs").exists():
            print(f"✅ Using selected folder: {selected}")
            return selected
        else:
            print("🚫 Invalid selection or JournalLogs folder missing.")
            return None

# ===== Core Logic =====
def get_latest_logs(directory: Path, max_logs: int = 5):
    try:
        all_files = sorted(directory.glob("*_journal.txt"), key=os.path.getmtime, reverse=True)
        print(f"📁 Found {len(all_files)} journal log files, using up to {max_logs}")
        for file in all_files[:max_logs]:
            print(f"  - {file.name}")
        return all_files[:max_logs]
    except Exception as e:
        print(f"[ERROR] Failed to get latest logs: {e}")
        return []

def extract_coordinates(log_files):
    coord_counts = defaultdict(int)
    for file_path in log_files:
        print(f"🔍 Scanning log file: {file_path}")
        found_any = False
        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    match = SOS_PATTERN.search(line)
                    if match:
                        x, y = match.groups()
                        coord_counts[(int(x), int(y))] += 1
                        print(f"📌 Found SOS at ({x}, {y})")
                        found_any = True
        except Exception as e:
            print(f"[ERROR] Could not read {file_path}: {e}")

        if found_any:
            print(f"✅ Found SOS entries in {file_path.name}, stopping search.")
            break
        else:
            print(f"❌ No SOS entries in {file_path.name}")
    return coord_counts

def generate_numbered_icons(base_icon_path, output_folder, counts):
    print(f"🎨 Generating numbered icons for counts: {sorted(counts)}")
    os.makedirs(output_folder, exist_ok=True)

    try:
        base_icon = Image.open(base_icon_path).convert("RGBA")
        icon_w, icon_h = base_icon.size

        # Step 1: Get visual (non-transparent) center of icon
        non_transparent_pixels = [
            (x, y)
            for y in range(icon_h)
            for x in range(icon_w)
            if base_icon.getpixel((x, y))[3] > 0  # alpha > 0
        ]
        if not non_transparent_pixels:
            print("⚠️ No visible pixels found in base icon.")
            visual_cx, visual_cy = icon_w // 2, icon_h // 2
        else:
            xs, ys = zip(*non_transparent_pixels)
            visual_cx = (min(xs) + max(xs)) // 2
            visual_cy = (min(ys) + max(ys)) // 2

        for count in counts:
            label = str(count)
            icon = base_icon.copy()
            draw = ImageDraw.Draw(icon)

            # Start with large font and shrink to fit
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

            # Center over the visual content (not canvas)
            text_x = visual_cx - text_w // 2
            text_y = visual_cy - text_h // 2

            # Draw outline
            for dx in [-1, 1]:
                draw.text((text_x + dx, text_y), label, font=font, fill="black")
            for dy in [-1, 1]:
                draw.text((text_x, text_y + dy), label, font=font, fill="black")

            # Draw main number
            draw.text((text_x, text_y), label, font=font, fill="white")

            output_path = os.path.join(output_folder, f"TREASURE_{label}.png")
            icon.save(output_path)
            print(f"  ✅ Created icon: {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to generate icons: {e}")


def create_xml(coord_counts, output_path):
    print(f"🛠️ Creating XML file at {output_path}...")
    try:
        pack = ET.Element("Pack", Name="MIB_locations", Revision="0")

        for (x, y), count in coord_counts.items():
            name = f"{count}"
            icon = f"TREASURE_{count}"
            print(f"🧷 Writing marker: Name={name}, X={x}, Y={y}, Icon={icon}")
            ET.SubElement(pack, "Marker", Name=name, X=str(x), Y=str(y), Icon=icon, Facet="0")

        tree = ET.ElementTree(pack)
        ET.indent(tree, space="  ", level=0)
        tree.write(output_path, encoding="utf-8", xml_declaration=True)
        print(f"✅ Wrote {len(coord_counts)} marker(s) to: {output_path}")

    except Exception as e:
        print(f"[ERROR] Failed to write XML: {e}")

# ===== MAIN =====
def main():
    print("🚀 Starting MIB Extractor Script")

    if not is_admin():
        restart_as_admin()

    client_path = find_ultima_folder()
    if not client_path:
        input("Press Enter to exit...")
        return

    journal_log_dir = client_path / "JournalLogs"
    output_xml_path = client_path / "Mib_locations.xml"
    icon_folder = client_path / "MapIcons"
    icon_source = icon_folder / "TREASURE.png"

    if not icon_source.exists():
        print(f"❌ Missing base treasure icon: {icon_source}")
        input("Press Enter to exit...")
        return

    latest_logs = get_latest_logs(journal_log_dir)
    if not latest_logs:
        print("❌ No journal logs found.")
        input("Press Enter to exit...")
        return

    coords = extract_coordinates(latest_logs)
    if not coords:
        print("⚠️ No SOS messages found in the latest logs.")
        input("Press Enter to exit...")
        return

    icon_counts = set(coords.values())
    generate_numbered_icons(str(icon_source), str(icon_folder), icon_counts)
    create_xml(coords, str(output_xml_path))

    print("✅ Done.")
    input("Press Enter to exit...")

if __name__ == "__main__":
    main()
