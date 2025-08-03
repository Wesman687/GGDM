import sys
import os

def is_running_as_admin():
    """Check if script is running with admin privileges (Windows only)."""
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def relaunch_as_admin():
    """Relaunch the current script with admin rights."""
    import ctypes
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    try:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
        sys.exit()
    except Exception as e:
        print("❌ Failed to request admin privileges.")
        sys.exit(1)