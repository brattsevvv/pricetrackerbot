@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment .venv was not found!
    pause
    exit /b 1
)

echo Starting Price Tracker Bot...
.venv\Scripts\python.exe main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Bot exited with error. Check BOT_TOKEN in .env
    pause
)
