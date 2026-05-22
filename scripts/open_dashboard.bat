@echo off
REM RSS-Radar — local dashboard launcher (Windows)
REM Usage: scripts\open_dashboard.bat

cd /d "%~dp0\.."

if not "%1"=="--no-pull" (
    echo Pulling latest changes...
    git pull --ff-only
)

if not exist "docs\index.html" (
    echo Error: docs\index.html not found. Run 'python scripts\fetch_and_report.py' first.
    pause
    exit /b 1
)

echo Opening dashboard...
start "" "docs\index.html"
