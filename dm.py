from logging import root
import os
import re
import string
import traceback
import xml.etree.ElementTree as ET
import xml.dom.minidom
import requests
import yaml
from pathlib import Path
import ctypes
import sys
from tkinter import filedialog, Tk
from PIL import Image, ImageDraw, ImageFont

# Fix console encoding for Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

DEBUG_MODE = os.getenv("DM_DEBUG", "0") == "1"


def safe_print(message):
    """
    Print a message safely, handling Unicode encoding errors.

    Args:
        message: The message to print
    """
    try:
        print(message)
    except UnicodeEncodeError:
        # Strip emojis and special characters if encoding fails
        clean_message = message.encode('ascii', 'ignore').decode('ascii')
        print(clean_message)


def log_debug(message):
    """
    Write a debug message to the log file.

    Args:
        message: The message to log
    """
    if DEBUG_MODE:
        with open("marker_debug.log", "a", encoding="utf-8") as log:
            log.write(message + "\n")

def get_resource_path(filename):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, filename)
    return os.path.join(os.path.abspath("."), filename)


TREASURE_COLOR = "#FF33CC"
DOCKMASTER_COLOR = "#00FFFF"
HOUSE_COLOR = "#00FF00"  # Green for player houses
DUNGEON_COLOR = "#FFCC00"  # Ultra bright neon orange for dungeon locations
FACTION_COLOR = "#FF3333"  # Bright red for faction wayposts

# Constants
GITHUB_BASE_URL = "https://raw.githubusercontent.com/LeoPiro/GG_Dms/main/"

# Marker packs with YAML preferred, text fallback
# New dm.exe will try YAML first; old dm.exe will only see the text file
MARKER_PACKS = [
    {
        "yaml_filename": "dockmasters.yaml",
        "text_filename": "GG DOCKMASTERS.txt",
        "output_xml": "GG_Dockmasters.xml",
        "pack_name": "GG DOCKMASTERS",
        "default_icon": "shipwright"
    },
    {
        "yaml_filename": "public_dockmasters.yaml",
        "text_filename": "PUBLIC DOCKMASTERS.txt",
        "output_xml": "Public_Dockmasters.xml",
        "pack_name": "Public DOCKMASTERS",
        "default_icon": "shipwright"
    },
    {
        "yaml_filename": "treasure.yaml",
        "text_filename": "TREASURE.txt",
        "output_xml": "Treasure_Map_Locations.xml",
        "pack_name": "Treasure Map Locations",
        "default_icon": "landmark"
    },
    {
        "yaml_filename": "playerhouses.yaml",
        "text_filename": None,                      # No legacy text format
        "output_xml": "Player_Houses.xml",
        "pack_name": "Player Houses",
        "default_icon": "house"
    },
    {
        "yaml_filename": "dung_locs.yaml",
        "text_filename": None,                      # No legacy text format
        "output_xml": "Dungeon_Locations.xml",
        "pack_name": "Dungeon Locations",
        "default_icon": "dungeon"
    },
    {
        "yaml_filename": "faction_points.yaml",
        "text_filename": None,                      # No legacy text format
        "output_xml": "Faction_Wayposts.xml",
        "pack_name": "Faction Wayposts",
        "default_icon": "landmark"
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
    """
    Check if a marker name matches treasure location patterns.

    Args:
        name: The marker name to check

    Returns:
        True if the name matches a treasure marker pattern
    """
    return re.match(r"^(N|E|S|W|CC|X|A)\d+$", name.upper())


def is_faction_marker(name):
    """
    Check if a marker name matches faction waypost patterns (F1-F18).

    Args:
        name: The marker name to check

    Returns:
        True if the name matches a faction marker pattern
    """
    return re.match(r"^F\d+$", name.upper())


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


def is_dungeon_marker(name):
    """
    Check if a marker name matches dungeon location patterns.
    
    Matches patterns like: inf1, ssc1, cav1, dm1, pul1, oss1, mau1, aeg1, um1, nus1, kra1, pet1, tt1, etc.

    Args:
        name: The marker name to check

    Returns:
        True if the name matches a dungeon marker pattern
    """
    # Match 2-3 letters followed by 1-3 digits (e.g., inf1, ssc13, cav32, dm20, pul1, etc.)
    return re.match(r"^[A-Z]{2,3}\d{1,3}$", name.upper()) is not None

def create_marker_icon(name, output_dir, base_top_font, base_bottom_font):
    try:
        log_debug(f"== Creating icon: {name}")
        log_debug(f"Output folder: {output_dir}")

        top_text, bottom_text = split_name(name)

        if is_treasure_marker(name):
            color = TREASURE_COLOR
        elif is_dockmaster_marker(name):
            color = DOCKMASTER_COLOR
        elif is_faction_marker(name):
            color = FACTION_COLOR
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


def create_house_icon(output_dir, icon_name="house", color=HOUSE_COLOR, size=8):
    """
    Create a simple colored circle icon for player houses.

    Args:
        output_dir: Directory to save the icon
        icon_name: Name of the icon file (without extension)
        color: Fill color for the circle (default green)
        size: Size of the icon in pixels (default 12)
    """
    try:
        log_debug(f"== Creating house icon: {icon_name} ({size}x{size})")

        # Create transparent canvas
        canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # Draw filled circle with black outline
        # Black outline circle
        draw.ellipse(
            [(0, 0), (size - 1, size - 1)],
            fill="black"
        )
        # Colored fill (slightly smaller for outline effect)
        draw.ellipse(
            [(1, 1), (size - 2, size - 2)],
            fill=color
        )

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{icon_name}.png")
        canvas.save(output_file)
        log_debug(f"✅ Saved house icon to: {output_file}")

    except Exception as e:
        log_debug(f"❌ Failed to create house icon: {e}")
        log_debug(traceback.format_exc())


def create_dungeon_icon(name, output_dir, base_top_font, base_bottom_font):
    """
    Create a smaller dungeon location icon (64% size of normal markers).
    Only displays the number part of the name (e.g., "pul19" shows as "19").

    Args:
        name: The dungeon marker name (e.g., "inf1", "ssc1", "cav1", etc.)
        output_dir: Directory to save the icon
        base_top_font: Base font for top text
        base_bottom_font: Base font for bottom text
    """
    try:
        log_debug(f"== Creating dungeon icon: {name}")
        log_debug(f"Output folder: {output_dir}")

        # Extract only the number part
        top_text, number_text = split_name(name)
        color = DUNGEON_COLOR

        # 64% of normal icon size (54 -> 34)
        icon_size = 34
        canvas_size = 34

        # Use a larger font since we're only displaying the number
        try:
            number_font = ImageFont.truetype(base_top_font.path, int(base_top_font.size * 0.75))
        except Exception:
            number_font = base_top_font

        # Create canvas
        canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(canvas)

        # Center the number vertically and horizontally
        number_bbox = draw.textbbox((0, 0), number_text, font=number_font)
        number_width = number_bbox[2] - number_bbox[0]
        number_height = number_bbox[3] - number_bbox[1]
        number_x = (icon_size - number_width) // 2
        number_y = (icon_size - number_height) // 2

        # Draw text with shadow
        for x_off in [-1, 0, 1]:
            for y_off in [-1, 0, 1]:
                if x_off or y_off:
                    draw.text((number_x + x_off, number_y + y_off), number_text, font=number_font, fill="black")

        draw.text((number_x, number_y), number_text, font=number_font, fill=color)

        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, f"{name}.png")
        canvas.save(output_file)
        log_debug(f"✅ Saved dungeon icon to: {output_file}")

    except Exception as e:
        log_debug(f"❌ Failed to create dungeon icon for {name}: {e}")
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
    """Search for all ClassicUO/Data/Client folders across all drives with user-driven scan options."""
    target_ending = os.path.join("ClassicUO", "Data", "Client")
    found = []

    # Initial quick scan in common locations
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
                    safe_print(f"⚠️ Error searching {root}: {e}")
                    log_debug(f"⚠️ Error searching {root}: {e}")
        return local_results

    # Perform initial quick scan
    safe_print("🔍 Performing quick scan in common locations...")
    found = run_search(search_roots)

    if found:
        return found

    # If nothing found, show drives and prompt user
    safe_print("\n⚠️ No Ultima Online installations found in common locations.")
    safe_print("Available drives:")
    for idx, drive in enumerate(all_drives, 1):
        safe_print(f"  [{idx}] {drive}")

    prompt = (
        "\nEnter the numbers of drives to quick scan (e.g., '1 2 3' or '1,2,3'), "
        "or press Enter to perform a full scan of all drives: "
    )
    user_input = input(prompt).strip()

    if not user_input:
        # Full scan of all drives
        safe_print("🔍 Performing full scan of all drives...")
        log_debug("User chose full scan of all drives.")
        found = run_search(all_drives)
    else:
        # Parse user input for specific drives
        try:
            selected_indices = [
                int(i.strip()) - 1 for i in user_input.replace(",", " ").split()
            ]
            valid_indices = [i for i in selected_indices if 0 <= i < len(all_drives)]
            if not valid_indices:
                safe_print("⚠️ No valid drive numbers selected. Performing full scan...")
                log_debug("No valid drive numbers selected, falling back to full scan.")
                found = run_search(all_drives)
            else:
                selected_drives = [all_drives[i] for i in valid_indices]
                safe_print(f"🔍 Performing quick scan on selected drives: {', '.join(selected_drives)}")
                log_debug(f"User selected drives for quick scan: {selected_drives}")
                # Build search roots for selected drives
                selected_roots = []
                for drive in selected_drives:
                    selected_roots.extend([
                        os.path.join(drive, "Program Files"),
                        os.path.join(drive, "Program Files (x86)"),
                        os.path.join(drive, "Games"),
                        os.path.join(drive, "Users"),
                        os.path.join(drive, "ProgramData"),
                    ])
                found = run_search(selected_roots)
                if not found:
                    safe_print("⚠️ No installations found on selected drives. Performing full scan...")
                    log_debug("No installations found on selected drives, falling back to full scan.")
                    found = run_search(all_drives)
        except ValueError:
            safe_print("⚠️ Invalid input. Performing full scan...")
            log_debug("Invalid input for drive selection, falling back to full scan.")
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
    """
    Parse a line from the legacy text format.

    Args:
        line: A line of text in format "Name X Y Facet Visible"
        default_icon: Fallback icon name if marker doesn't match known patterns

    Returns:
        An XML Element for the marker, or None if invalid/hidden
    """
    parts = line.strip().split()
    if len(parts) != 5:
        return None

    name, x, y, facet, visible = parts

    if visible.lower() != "true":
        return None

    if is_treasure_marker(name) or is_dockmaster_marker(name):
        icon = name  # use marker name
    else:
        icon = default_icon  # fallback icon (e.g., 'shipwright')

    return ET.Element("Marker", Name=name, X=x, Y=y, Icon=icon, Facet=facet)


def parse_yaml_markers(yaml_content, default_icon, default_facet=0):
    """
    Parse YAML marker data into a list of marker elements.

    Supports multiple root keys: dockmasters, markers, houses, locations.

    Args:
        yaml_content: Raw YAML string content
        default_icon: Fallback icon name for non-standard markers
        default_facet: Default map facet (0 for Outlands)

    Returns:
        Tuple of (list of XML marker elements, pack_name, revision)
    """
    data = yaml.safe_load(yaml_content)

    pack_name = data.get("pack_name", "Markers")
    revision = data.get("revision", 0)

    # Support multiple root keys for flexibility
    marker_data = {}
    for key in ["dockmasters", "markers", "houses", "locations", "treasures", "dungeon_locations"]:
        if key in data and data[key]:
            marker_data = data[key]
            log_debug(f"📋 Using '{key}' as marker root key")
            break

    if not marker_data:
        log_debug("⚠️ No marker data found in YAML")
        return [], pack_name, revision

    markers = []
    for name, attributes in marker_data.items():
        # Handle case where attributes might be None
        if attributes is None:
            log_debug(f"⚠️ Skipping {name}: no attributes defined")
            continue

        x = attributes.get("x")
        y = attributes.get("y")
        owner = attributes.get("owner", "unknown")
        facet = attributes.get("facet", default_facet)
        visible = attributes.get("visible", True)

        # Skip if missing required coordinates or not visible
        if x is None or y is None:
            log_debug(f"⚠️ Skipping {name}: missing x or y coordinate")
            continue

        if not visible:
            log_debug(f"⚠️ Skipping {name}: marked as not visible")
            continue

        # Determine icon name
        if is_treasure_marker(name) or is_dockmaster_marker(name) or is_dungeon_marker(name) or is_faction_marker(name):
            icon = name
        else:
            icon = attributes.get("icon", default_icon)

        marker = ET.Element(
            "Marker",
            Name=name,
            X=str(x),
            Y=str(y),
            Icon=icon,
            Facet=str(facet)
        )
        markers.append(marker)

        log_debug(f"✅ Parsed marker: {name} at ({x}, {y}) owner={owner}")

    return markers, pack_name, revision


def ensure_icon_exists(icon_name, output_folder, top_font, bottom_font):
    """
    Create a marker icon if it matches known patterns.

    Args:
        icon_name: Name of the icon to create
        output_folder: Directory to save the icon
        top_font: Font for top text
        bottom_font: Font for bottom text
    """
    if is_treasure_marker(icon_name) or is_dockmaster_marker(icon_name) or is_faction_marker(icon_name):
        create_marker_icon(icon_name, output_folder, top_font, bottom_font)
    elif is_dungeon_marker(icon_name):
        create_dungeon_icon(icon_name, output_folder, top_font, bottom_font)
    elif icon_name == "house":
        create_house_icon(output_folder, icon_name, HOUSE_COLOR, size=8)
            

def install_gridlines(mapicons_path, client_path, FILL_COLOR=(180, 180, 180, 180)):
    safe_print("🧱 Generating gridline markers and icon...")
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
        safe_print(f"✅ Gridlines.xml written to {gridlines_xml_path}")
        log_debug(f"✅ Gridlines.xml written to {gridlines_xml_path}")
    except Exception as e:
        safe_print(f"❌ Failed to write Gridlines.xml: {e}")
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
            safe_print("⚠️ Couldn't load embedded TTF font, using default.")
            top_font = ImageFont.load_default()
            bottom_font = ImageFont.load_default()

        client_paths = search_for_game_folders()
        log_debug(f"🔍 Detected game folders: {client_paths}")

        if not client_paths:
            safe_print("⚠️ Could not auto-detect any Ultima Online installations.")
            client_path = prompt_user_for_folder()
            log_debug(f"🧭 User selected folder: {client_path}")
        elif len(client_paths) == 1:
            client_path = client_paths[0]
            log_debug(f"✅ Single client path auto-selected: {client_path}")
        else:
            safe_print("🔍 Multiple Ultima Online installations found:")
            for idx, path in enumerate(client_paths):
                safe_print(f"  [{idx+1}] {path}")
                log_debug(f"  [{idx+1}] {path}")

            while True:
                choice = input(f"\nPlease select which installation to update (1 - {len(client_paths)}): ")
                if choice.isdigit():
                    choice_idx = int(choice) - 1
                    if 0 <= choice_idx < len(client_paths):
                        client_path = client_paths[choice_idx]
                        log_debug(f"✅ User selected client path: {client_path}")
                        break
                safe_print("⚠️ Invalid choice. Try again.")
                log_debug("⚠️ Invalid choice input received.")

        if not client_path or not client_path.exists():
            safe_print("❌ No valid folder selected. Exiting.")
            log_debug("❌ No valid client path selected. Exiting early.")
            return

        mapicons_path = client_path / "MapIcons"
        log_debug(f"🖼️ Icon output path: {mapicons_path}")

        # === Process marker packs (YAML preferred, text fallback) ===
        for file_info in MARKER_PACKS:
            default_icon = file_info["default_icon"]
            yaml_filename = file_info.get("yaml_filename")
            text_filename = file_info.get("text_filename")

            markers = []
            pack_name = file_info["pack_name"]
            revision = 0
            used_format = None

            # Try YAML first if available
            if yaml_filename:
                yaml_url = GITHUB_BASE_URL + yaml_filename.replace(" ", "%20")
                log_debug(f"🌐 Trying YAML: {yaml_filename} → {yaml_url}")

                response = requests.get(yaml_url)
                if response.status_code == 200:
                    log_debug(f"📄 Downloaded YAML content from {yaml_filename}")
                    try:
                        markers, pack_name, revision = parse_yaml_markers(
                            response.text, default_icon
                        )
                        used_format = "YAML"
                        safe_print(f"✅ Using YAML format: {yaml_filename}")
                    except Exception as e:
                        safe_print(f"⚠️ Failed to parse YAML {yaml_filename}: {e}")
                        log_debug(f"⚠️ YAML parse error, will try text fallback: {e}")
                        markers = []  # Reset to try text fallback
                else:
                    log_debug(f"⚠️ YAML not found (HTTP {response.status_code}), trying text fallback")

            # Fall back to text format if YAML failed or wasn't available
            if not markers and text_filename:
                text_url = GITHUB_BASE_URL + text_filename.replace(" ", "%20")
                log_debug(f"🌐 Trying text fallback: {text_filename} → {text_url}")

                response = requests.get(text_url)
                if response.status_code == 200:
                    lines = response.text.strip().splitlines()
                    log_debug(f"📄 Downloaded {len(lines)} lines from {text_filename}")

                    for line in lines:
                        marker = parse_line(line, default_icon)
                        if marker is not None:
                            markers.append(marker)

                    used_format = "text"
                    safe_print(f"✅ Using text format: {text_filename}")
                else:
                    safe_print(f"❌ Failed to download {text_filename}: HTTP {response.status_code}")
                    log_debug(f"❌ Download failed: {text_filename} → HTTP {response.status_code}")
                    continue

            if not markers:
                safe_print(f"❌ No markers loaded for {file_info['output_xml']}")
                continue

            # Ensure icons exist for all markers
            for marker in markers:
                icon_name = marker.attrib.get("Icon")
                log_debug(f"🔧 Ensuring icon exists: {icon_name}")
                ensure_icon_exists(icon_name, mapicons_path, top_font, bottom_font)

            markers.sort(key=custom_sort)
            log_debug(f"✅ Parsed and sorted {len(markers)} markers ({used_format} format)")

            # Write XML
            pack = ET.Element("Pack", Name=pack_name, Revision=str(revision))
            for marker in markers:
                pack.append(marker)

            rough_string = ET.tostring(pack, encoding="utf-8")
            reparsed = xml.dom.minidom.parseString(rough_string)
            pretty_xml = reparsed.toprettyxml(indent="  ", encoding="UTF-8")

            xml_path = client_path / file_info["output_xml"]
            os.makedirs(xml_path.parent, exist_ok=True)

            safe_print(f"💾 Writing {file_info['output_xml']} ({len(markers)} markers)")
            log_debug(f"💾 Writing XML to: {xml_path}")
            try:
                with open(xml_path, "wb") as f:
                    f.write(pretty_xml.replace(b"\n", b"\r\n"))
                safe_print(f"🎉 {file_info['output_xml']} successfully updated.")
                log_debug(f"🎉 {file_info['output_xml']} written successfully.")
            except Exception as e:
                safe_print(f"❌ Failed to write {file_info['output_xml']}: {e}")
                log_debug(f"❌ Failed to write XML {file_info['output_xml']}: {e}")

        # === Prompt for gridlines AFTER all standard packs are handled ===
        install_grid = input("📐 Do you want to install gridlines? (y/n): ").strip().lower()
        if install_grid == "y":
            log_debug("🧱 User chose to install gridlines.")
            safe_print("\n🎨 Choose a gridline color:")
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
                safe_print(f"  [{key}] {label}")

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
                    safe_print("⚠️ Invalid format. Using default light gray.")
                    base_rgb = (180, 180, 180)

            FILL_COLOR = base_rgb + (255,)


            install_gridlines(mapicons_path, client_path, FILL_COLOR)
        else:
            log_debug("🧱 User skipped gridline installation.")
            gridline_path = client_path / "Gridlines.xml"
            if gridline_path.exists():
                try:
                    os.remove(gridline_path)
                    safe_print("🧹 Removed existing Gridlines.xml")
                    log_debug("🧹 Removed Gridlines.xml because user chose not to install.")
                except Exception as e:
                    safe_print(f"⚠️ Failed to remove Gridlines.xml: {e}")
                    log_debug(f"⚠️ Failed to delete Gridlines.xml: {e}")

    except Exception as e:
        safe_print("❌ Error in update_markers()")
        log_debug(f"❌ Exception in update_markers(): {e}")
        log_debug(traceback.format_exc())



if __name__ == "__main__":
    try:
        if DEBUG_MODE:
            with open("marker_debug.log", "w", encoding="utf-8") as log:
                log.write("=== Debug Log Started ===\n")

        # Skip admin check in debug mode for testing
        if not DEBUG_MODE and not is_admin():
            safe_print("🛡️ Restarting with admin privileges...")
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
        safe_print("\n❌ An unexpected error occurred:")
        if DEBUG_MODE:
            log_debug("❌ Unexpected exception occurred:")
            log_debug(traceback.format_exc())  # ✅ this is how to capture the actual traceback
        traceback.print_exc()