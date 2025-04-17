import os
import json
from pathlib import Path

def dump_original_icons():
    mapicons_path = Path(r"C:\Program Files (x86)\Ultima Online Outlands\ClassicUO\Data\Client\MapIcons")
    icons = []
    for file in os.listdir(mapicons_path):
        if file.lower().endswith(".png"):
            icon_name = os.path.splitext(file)[0]
            icons.append(icon_name)

    with open("original_icons.json", "w") as f:
        json.dump(sorted(icons), f, indent=2)

    print(f"✅ Saved {len(icons)} original icons to original_icons.json")

if __name__ == "__main__":
    dump_original_icons()