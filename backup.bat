@echo off
REM Chimera MEV Bot - Backup Script (Windows)
REM Backs up PostgreSQL database and Redis data

setlocal enabledelayedexpansion

echo ========================================
echo Chimera MEV Bot - Backup Data
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running.
    exit /b 1
)

REM Create backup directory with timestamp
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c-%%a-%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set timestamp=%mydate%_%mytime%
set backup_dir=backups\%timestamp%

if not exist backups mkdir backups
mkdir %backup_dir%

echo [INFO] Backup directory: %backup_dir%
echo.

REM Check if PostgreSQL container is running
docker ps | findstr "chimera-postgres" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] PostgreSQL container is not running.
    echo [INFO] Start services first: start.bat
    exit /b 1
)

echo [INFO] Backing up PostgreSQL database...
docker exec chimera-postgres pg_dump -U chimera_user chimera > %backup_dir%\postgres_backup.sql

if errorlevel 1 (
    echo [ERROR] Failed to backup PostgreSQL database.
    exit /b 1
)

echo [INFO] PostgreSQL backup complete: %backup_dir%\postgres_backup.sql
echo.

REM Check if Redis container is running
docker ps | findstr "chimera-redis" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Redis container is not running. Skipping Redis backup.
) else (
    echo [INFO] Backing up Redis data...
    docker exec chimera-redis redis-cli SAVE >nul 2>&1
    docker cp chimera-redis:/data/dump.rdb %backup_dir%\redis_backup.rdb
    
    if errorlevel 1 (
        echo [WARNING] Failed to backup Redis data.
    ) else (
        echo [INFO] Redis backup complete: %backup_dir%\redis_backup.rdb
    )
)

echo.

REM Copy logs if they exist
if exist logs (
    echo [INFO] Copying logs...
    xcopy /E /I /Q logs %backup_dir%\logs >nul 2>&1
    echo [INFO] Logs copied: %backup_dir%\logs
    echo.
)

REM Copy data if it exists
if exist data (
    echo [INFO] Copying data files...
    xcopy /E /I /Q data %backup_dir%\data >nul 2>&1
    echo [INFO] Data copied: %backup_dir%\data
    echo.
)

echo ========================================
echo Backup Complete!
echo ========================================
echo.
echo Backup location: %backup_dir%
echo.
echo Contents:
echo   - postgres_backup.sql (database dump)
echo   - redis_backup.rdb (cache snapshot)
echo   - logs/ (application logs)
echo   - data/ (historical data)
echo.
echo To restore from backup:
echo   1. Stop services: stop.bat
echo   2. Reset environment: reset.bat
echo   3. Start services: start.bat
echo   4. Restore database:
echo      docker exec -i chimera-postgres psql -U chimera_user chimera ^< %backup_dir%\postgres_backup.sql
echo.
echo ========================================

endlocal
