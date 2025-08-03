import os
from pathlib import Path
from ultima_locator import find_ultima_install
from journal_reader import get_latest_logs, get_first_valid_mibs


def extract_mib_coordinates(max_logs=5):
    ultima_path = find_ultima_install()
    if not ultima_path:
        raise FileNotFoundError("Ultima Online installation not found.")

    journal_dir = Path(ultima_path) / "Data" / "Client" / "JournalLogs"
    print("📂 Journal directory:", journal_dir)

    latest_logs = get_latest_logs(journal_dir, max_logs=max_logs)
    print("📥 Selected logs:", [f.name for f in latest_logs])

    mib_data, total_found = get_first_valid_mibs(latest_logs)
    print(f"🔍 Found {len(mib_data)} valid MIBs out of {total_found} entries.")
    return mib_data, total_found


if __name__ == "__main__":
    mibs, total = extract_mib_coordinates()
    for mib in mibs:
        print(f"Serial: {mib['serial']}, X: {mib['x']}, Y: {mib['y']}")
    print(f"Total valid MIBs parsed: {len(mibs)} out of {total}")
