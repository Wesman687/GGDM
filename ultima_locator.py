import os
import psutil

COMMON_PATHS = [
    "C:\\Program Files (x86)\\Ultima Online Outlands\\ClassicUO",
    "C:\\Games\\Ultima Online Outlands\\ClassicUO",
]

def find_ultima_process_path():
    """Try to locate the running Ultima Online client via process list."""
    for proc in psutil.process_iter(['pid', 'name', 'exe']):
        try:
            name = proc.info['name'] or ''
            if 'client' in name.lower() or 'ultima' in name.lower():
                exe_path = proc.info['exe']
                if exe_path and os.path.exists(exe_path):
                    return os.path.dirname(exe_path)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return None

def deep_scan_for_ultima():
    """Fallback if process check fails: scan drives for known Ultima locations."""
    for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ":
        drive_path = f"{drive}:\\"
        for path in COMMON_PATHS:
            full_path = os.path.join(drive_path, *path.split("\\")[1:])
            if os.path.exists(full_path):
                return full_path
    return None

def find_ultima_install():
    """Unified function: try process check first, then deep scan."""
    return find_ultima_process_path() or deep_scan_for_ultima()
