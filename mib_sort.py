import os
import pyperclip
import traceback
from pathlib import Path
from journal_reader import JournalAccessError
from mib_coord_extractor import extract_mib_coordinates
import ctypes

from run_as_admin import is_running_as_admin, relaunch_as_admin

CHEST_GRID = {
    1: ((0, 1499), (0, 2999)),
    2: ((1500, 2999), (0, 2999)),
    3: ((3000, 4499), (0, 2999)),
    4: ((4500, 6100), (0, 2999)),
    5: ((0, 1499), (3000, 6100)),
    6: ((1500, 2999), (3000, 6100)),
    7: ((3000, 4499), (3000, 6100)),
    8: ((4500, 6100), (3000, 6100)),
}

def get_chest_zone(x, y):
    for chest_num, ((xmin, xmax), (ymin, ymax)) in CHEST_GRID.items():
        if xmin <= x <= xmax and ymin <= y <= ymax:
            return chest_num
    return None

def scale_drop_coords(x, y):
    chest = get_chest_zone(x, y)
    if not chest:
        return 0, 0
    (xmin, xmax), (ymin, ymax) = CHEST_GRID[chest]
    xgrid = 20 + ((x - xmin) * 180) // max(1, xmax - xmin)
    ygrid = 20 + ((y - ymin) * 140) // max(1, ymax - ymin)
    return xgrid, ygrid

def generate_razor_script(sos_data):
    lines = [
        "// Razor Script to Sort MIBs into 8 Chests Based on Coordinates",
        "// Assumes @setvar mibchest1 - mibchest8 are already set.\n"
    ]
    for index, mib in enumerate(sos_data):
        chest = get_chest_zone(mib['x'], mib['y'])
        if chest is None:
            continue
        xgrid, ygrid = scale_drop_coords(mib['x'], mib['y'])
        lines += [
            f"// MIB at ({mib['x']}, {mib['y']}) -> Chest {chest} @ {xgrid}, {ygrid}",
            f"lift {mib['serial']}",
            f"overhead 'Placing MIB {index+1}/{len(sos_data)} at {mib['x']},{mib['y']} in Chest {chest}' 65",
            f"drop 'mibchest{chest}' {xgrid} {ygrid} 0",
            "pause 650\n"
        ]
    return "\n".join(lines)

def show_message(title, message, icon=0):
    ctypes.windll.user32.MessageBoxW(0, message, title, icon)

if __name__ == "__main__":
    try:
        if not is_running_as_admin():
            relaunch_as_admin()
        sos_data, total_found = extract_mib_coordinates(max_logs=5)
        if len(sos_data) == 0:
            raise ValueError("No MIBs found.")

        razor_script = generate_razor_script(sos_data)

        output_folder = "./output"
        os.makedirs(output_folder, exist_ok=True)
        output_path = os.path.join(output_folder, "sort_mibs.razor")
        with open(output_path, "w") as f:
            f.write(razor_script)

        pyperclip.copy(razor_script)
        show_message("Success", "✅ MIB sorting script copied to clipboard.", icon=0x40)

    except JournalAccessError:
        show_message("Error Loading Journal", "❌ Error loading journal.\nPlease close the game and try again.", icon=0x10)

    except Exception as e:
        show_message("Error", f"❌ MIB sorting failed.\n{str(e)}", icon=0x10)
        traceback.print_exc()

