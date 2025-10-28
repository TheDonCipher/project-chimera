@echo off
REM Chimera MEV Bot - Reset Script (Windows)
REM Stops services, removes all data, and provides fresh start option

REM Check if specific service reset requested
if not "%1"=="" (
    if /i "%1"=="anvil" (
        echo ========================================
        echo Resetting Anvil Fork State
        echo ========================================
        echo.
        echo [INFO] Stopping Anvil...
        docker-compose --profile testing stop anvil
        echo.
        echo [INFO] Removing Anvil state volume...
        docker volume rm project-chimera_anvil_state 2>nul
        if errorlevel 1 (
            echo [WARNING] Anvil state volume not found or already removed.
        ) else (
            echo [INFO] Anvil state volume removed.
        )
        echo.
        echo [INFO] Restarting Anvil with fresh fork...
        docker-compose --profile testing up -d anvil
        echo.
        echo [SUCCESS] Anvil reset complete!
        echo.
        exit /b 0
    ) else (
        echo [ERROR] Unknown service: %1
        echo.
        echo Usage:
        echo   reset.bat          - Reset all services and data
        echo   reset.bat anvil    - Reset only Anvil fork state
        echo.
        exit /b 1
    )
)

echo ========================================
echo Chimera MEV Bot - Reset Environment
echo ========================================
echo.
echo [WARNING] This will:
echo   - Stop all running containers
echo   - Remove all Docker volumes (database, cache, and Anvil state)
echo   - Clear logs directory
echo   - Clear data directory
echo.

set /p confirm="Are you sure you want to continue? (yes/no): "
if /i not "%confirm%"=="yes" (
    echo.
    echo [INFO] Reset cancelled.
    exit /b 0
)

echo.
echo [INFO] Stopping services...
docker-compose down

echo.
echo [INFO] Removing Docker volumes...
docker-compose down -v

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to remove volumes. They may not exist or are in use.
)

echo.
echo [INFO] Clearing logs directory...
if exist logs (
    del /q logs\*.log 2>nul
    echo [INFO] Logs cleared.
) else (
    echo [INFO] Logs directory does not exist.
)

echo.
echo [INFO] Clearing data directory...
if exist data (
    del /q data\*.csv 2>nul
    del /q data\*.json 2>nul
    echo [INFO] Data cleared.
) else (
    echo [INFO] Data directory does not exist.
)

echo.
echo ========================================
echo Reset Complete!
echo ========================================
echo.
echo All data has been removed.
echo.
echo To start fresh:
echo   start.bat
echo.
echo ========================================
