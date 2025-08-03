import os
import re
from pathlib import Path


class JournalAccessError(Exception):
    pass

def get_latest_logs(directory: Path, max_logs: int = 5):
    try:
        all_files = sorted(directory.glob("*_journal.txt"), key=os.path.getmtime, reverse=True)
        print(f"✨ Found {len(all_files)} journal log files, using up to {max_logs}")
        latest = []

        for file in all_files:
            try:
                with open(file, "r", encoding="utf-8", errors="ignore") as f:
                    f.read(1)
                latest.append(file)
            except PermissionError:
                print(f"[ERROR] Reading {file.name}: Permission denied.")
            except Exception as e:
                print(f"[ERROR] Reading {file.name}: {e}")

            if len(latest) >= max_logs:
                break

        if not latest:
            raise JournalAccessError("No accessible journal logs found.")
        return latest

    except Exception as e:
        raise JournalAccessError(str(e))


RZ_COORD_PATTERN = re.compile(r'a waterstained SOS message \(located at (\d+), (\d+)\)')
RZ_SERIAL_PATTERN = re.compile(r'Added (\d+) to ignore list')

def get_first_valid_mibs(log_files):
    """
    Extract MIBs from Razor journal logs.
    Stops after the first journal that contains any valid MIBs.
    """
    seen = set()

    for log in log_files:
        sos_data = []
        try:
            with open(log, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            i = 0
            while i < len(lines):
                coord_match = RZ_COORD_PATTERN.search(lines[i])
                if coord_match:
                    x, y = map(int, coord_match.groups())
                    for j in range(i + 1, min(i + 5, len(lines))):
                        serial_match = RZ_SERIAL_PATTERN.search(lines[j])
                        if serial_match:
                            serial = serial_match.group(1)
                            if serial not in seen:
                                seen.add(serial)
                                sos_data.append({'x': x, 'y': y, 'serial': serial})
                            break
                i += 1

            if sos_data:
                return sos_data, len(sos_data)

        except Exception as e:
            print(f"[ERROR] Reading {log.name}: {e}")

    return [], 0