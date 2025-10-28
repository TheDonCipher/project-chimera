@echo off
REM Chimera MEV Bot - Logs Script (Windows)
REM Tail logs from Docker containers in real-time

echo ========================================
echo Chimera MEV Bot - Container Logs
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    exit /b 1
)

REM Check if services are running
docker-compose ps | findstr "Up" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] No services appear to be running.
    echo.
    echo To start services:
    echo   start.bat
    echo.
    exit /b 1
)

echo [INFO] Showing logs from all services...
echo [INFO] Press Ctrl+C to stop following logs
echo.
echo ========================================
echo.

REM Follow logs from all services
docker-compose logs -f --tail=100

REM Note: This will run until user presses Ctrl+C
