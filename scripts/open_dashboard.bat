@echo off
REM RSS Radar - Lokal dashboard görüntüleyici (Windows)
REM Kullanım: scripts\open_dashboard.bat

cd /d "%~dp0\.."

if not "%1"=="--no-pull" (
    echo Son degisiklikler cekiliyor...
    git pull --ff-only
)

if not exist "docs\index.html" (
    echo Hata: docs\index.html yok. Once 'python scripts\fetch_and_report.py' calistir.
    pause
    exit /b 1
)

echo Dashboard aciliyor...
start "" "docs\index.html"
