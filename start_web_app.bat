@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv was not found!
    pause
    exit /b 1
)

echo Starting Price Tracker Web App...
.venv\Scripts\python.exe webapp.py

if errorlevel 1 (
    echo.
    echo [ERROR] Web app exited with error.
    pause
)
