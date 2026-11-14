@echo off
rem Double-click this file to open the dashboard in your browser.
rem The first run sets up the Python environment, which takes a few minutes.
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Setting up Python packages for the first time. Please wait...
    python -m venv .venv
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)
echo Starting the dashboard. Close this window to stop it.
".venv\Scripts\python.exe" -m streamlit run app\main.py
pause
