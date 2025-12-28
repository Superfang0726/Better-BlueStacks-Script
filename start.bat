@echo off
title Better BlueStacks Script

echo ========================================
echo   Better BlueStacks Script Launcher
echo ========================================
echo.

:: Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo         Please install Python 3.9+ from https://python.org
    echo         Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

:: Check if venv exists
if not exist "venv" (
    echo [INFO] Virtual environment not found, creating...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [OK] Virtual environment created
    echo.
)

:: Activate venv
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

:: Check if dependencies are installed by checking for flask
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [INFO] Dependencies not installed, installing...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies!
        pause
        exit /b 1
    )
    echo [OK] Dependencies installed
    echo.
)

:: Run the server
echo [INFO] Starting server...
echo.
python run.py

:: Keep window open if server stops
pause
