@echo off
rem Run Desk Panel Tray from source (no build). First run installs dependencies.
cd /d "%~dp0"
if not exist .venv (py -3 -m venv .venv && .venv\Scripts\python -m pip install -r requirements.txt)
start "" .venv\Scripts\pythonw.exe run_deskpanel.py
