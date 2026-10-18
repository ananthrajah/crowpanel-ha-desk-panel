@echo off
rem Desk Panel Tray - build a single DeskPanel.exe (Windows, Python 3.11+)
setlocal
cd /d "%~dp0"
where py >nul 2>nul || (echo Python 3.11+ is not installed. Get it from https://www.python.org/downloads/ and tick "Add to PATH". & pause & exit /b 1)
if not exist .venv py -3 -m venv .venv || (echo Could not create venv & pause & exit /b 1)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip >nul
pip install -r requirements.txt pyinstaller || (pause & exit /b 1)
pyinstaller --noconfirm --clean --onefile --windowed --name DeskPanel --icon assets\deskpanel.ico --collect-submodules keyring --hidden-import win32ctypes.core run_deskpanel.py || (pause & exit /b 1)
echo.
echo Built: %CD%\dist\DeskPanel.exe
echo Copy it anywhere (e.g. %%LOCALAPPDATA%%\DeskPanel) and double-click to run.
pause
