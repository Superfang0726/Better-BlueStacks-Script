@echo off
chcp 65001 >nul
title Better BlueStacks Script

echo ========================================
echo   Better BlueStacks Script Launcher
echo ========================================
echo.

:: Check if venv exists
if not exist "venv" (
    echo [INFO] 虛擬環境不存在，正在建立...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] 建立虛擬環境失敗！請確認已安裝 Python 3.9+
        pause
        exit /b 1
    )
    echo [OK] 虛擬環境建立完成
    echo.
)

:: Activate venv
echo [INFO] 啟用虛擬環境...
call venv\Scripts\activate.bat

:: Check if dependencies are installed by checking for flask
python -c "import flask" 2>nul
if errorlevel 1 (
    echo [INFO] 依賴套件未安裝，正在安裝...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] 安裝依賴失敗！
        pause
        exit /b 1
    )
    echo [OK] 依賴套件安裝完成
    echo.
)

:: Run the server
echo [INFO] 啟動伺服器...
echo.
python run.py

:: Keep window open if server stops
pause
