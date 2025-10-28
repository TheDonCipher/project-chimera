@echo off
REM Chimera MEV Bot - Start Script (Windows)
REM Launches all Docker services for local development

echo ========================================
echo Chimera MEV Bot - Starting Services
echo ========================================
echo.

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running. Please start Docker Desktop and try again.
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo [WARNING] .env file not found. Creating from .env.example...
    copy .env.example .env
    echo [INFO] Please edit .env file with your actual configuration before running the bot.
    echo.
)

REM Create logs and data directories if they don't exist
if not exist logs mkdir logs
if not exist data mkdir data

echo [INFO] Starting Docker Compose services...
echo.

REM Start services
docker-compose up -d

if errorlevel 1 (
    echo.
    echo [ERROR] Failed to start services. Check the error messages above.
    exit /b 1
)

echo.
echo ========================================
echo Services Started Successfully!
echo ========================================
echo.
echo PostgreSQL:      localhost:5432
echo Redis:           localhost:6379
echo Bot:             Running in container
echo.
echo Management Tools (optional):
echo   pgAdmin:       http://localhost:5050
echo   Redis Commander: http://localhost:8081
echo.
echo To start management tools:
echo   docker-compose --profile tools up -d
echo.
echo To view logs:
echo   logs.bat
echo.
echo To stop services:
echo   stop.bat
echo.
echo ========================================
