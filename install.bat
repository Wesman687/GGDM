@echo off
echo 🔄 Cleaning...
rmdir /s /q build
rmdir /s /q dist

echo ⚙️ Activating virtual environment...
call .venv\Scripts\activate.bat

:: === Build Release (no debug) ===
echo 🚀 Building dm.exe (release)...
set DM_DEBUG=0
pyinstaller --onefile --console --add-data "DejaVuSans-Bold.ttf;." --name dm dm.py

:: === Build Debug version ===
echo 🐞 Building dmdebug.exe (with DEBUG_MODE=True)...
set DM_DEBUG=1
pyinstaller --onefile --console --add-data "DejaVuSans-Bold.ttf;." --name dmdebug dm.py

echo ✅ Both builds complete. Press Enter to exit.
pause