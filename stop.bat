@echo off
REM Chimera MEV Bot - Stop Script (Windows)
REM Gracefully shuts down all Docker services

echo ========================================
echo Chimera MEV Bot - Stopping Services
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    exit /b 1
)

echo [INFO] Stopping Docker Compose services...
echo.

REM Stop services gracefully
docker-compose down

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to stop services. Check the error messages above.
    exit /b 1
)

echo.
echo ========================================
echo Services Stopped Successfully!
echo ========================================
echo.
echo Data is preserved in Docker volumes.
echo.
echo To start services again:
echo   start.bat
echo.
echo To remove all data and reset:
echo   reset.bat
echo.
echo ========================================
