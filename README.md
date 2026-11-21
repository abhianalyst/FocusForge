# FocusForge

Offline-first Windows desktop productivity tracker built with Python, PySide6 and SQLite.

## First release
- Dashboard with today's tasks, habits and focus time
- Task creation, completion, deletion, due dates and priorities
- Custom daily habits with date-based check-ins
- Pomodoro focus timer (25-minute focus / 5-minute break)
- Local SQLite database stored in %LOCALAPPDATA%\FocusForge\

## Run locally (Windows)
Install Python 3.12 (64-bit), then run in PowerShell:

    py -3.12 -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    python main.py

## Build installer
Open the repository Actions tab. Run Build Windows Installer, or push a commit to main. Download the FocusForge-Windows-Installer artifact from a successful workflow run.

Uninstalling the application does not remove the database from Local AppData.


Build workflow configured: every push to main attempts a Windows x64 installer build.
