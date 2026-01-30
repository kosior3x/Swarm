@echo off
title SWARM UNIVERSAL LOADER
cd /d "%~dp0"
python loader.py
if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Loader failed. Checking if Python is installed...
    python --version >nul 2>&1
    if %errorlevel% neq 0 (
        echo [ERROR] Python not found in PATH! Please install Python 3.
    ) else (
        echo [ERROR] Script crashed. Check the log above.
    )
    pause
)
pause
