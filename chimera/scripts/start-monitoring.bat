@echo off
REM Start Chimera bot with monitoring stack (Windows)

echo Starting Chimera bot with monitoring stack...
echo.

REM Check if docker-compose is available
where docker-compose >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: docker-compose is not installed
    echo Please install docker-compose: https://docs.docker.com/compose/install/
    exit /b 1
)

REM Check if .env file exists
if not exist "..\\.env" (
    echo Warning: .env file not found
    echo Copying .env.example to .env...
    copy "..\.env.example" "..\.env"
    echo Please edit .env with your actual values before running the bot
    exit /b 1
)

REM Start services
echo Starting services...
cd ..
docker-compose --profile monitoring up -d

echo.
echo Services started successfully!
echo.
echo Access the dashboards:
echo   - Grafana:     http://localhost:3000 (admin/admin)
echo   - Prometheus:  http://localhost:9090
echo   - Bot Metrics: http://localhost:8000/metrics
echo   - Bot Health:  http://localhost:8000/health
echo.
echo View logs:
echo   docker logs -f chimera-bot
echo.
echo Stop services:
echo   docker-compose --profile monitoring down
echo.
