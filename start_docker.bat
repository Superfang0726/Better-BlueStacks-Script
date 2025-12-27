@echo off
chcp 65001 >nul
echo ==========================================
echo       BlueStacks Bot Docker Setup
echo ==========================================
echo.

REM Check if Docker is running
REM 檢查 Docker 是否正在運行
docker info >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Docker is not running or not installed.
    echo [錯誤] Docker 未運行或未安裝。
    echo.
    echo Please install Docker Desktop and make sure it is running.
    echo 請安裝 Docker Desktop 並確保它正在運行。
    echo.
    pause
    exit /b
)

echo [INFO] Docker is running.
echo [INFO] Building Docker environment and installing dependencies...
echo [INFO] 開始建置 Docker 環境並安裝依賴...
echo.

echo [INFO] Launching Web UI in browser...
start "" "http://localhost:5000"

REM Run docker-compose build and up
REM 執行 docker-compose 建置並啟動
docker-compose up --build

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] Something went wrong while running the container.
    echo [錯誤] 執行容器時發生錯誤。
    timeout /t 3
) else (
    echo.
    echo [INFO] Container stopped.
    echo [INFO] 容器已停止。
    REM No pause here, let it close
)
