@echo off
REM Test runner script for Project Chimera (Windows)
REM Task 10.1: Local testing infrastructure

echo ========================================
echo Project Chimera - Test Runner
echo ========================================
echo.

REM Check if we're in the chimera directory
if not exist "pytest.ini" (
    echo Error: Must be run from chimera directory
    echo Current directory: %CD%
    exit /b 1
)

REM Parse command line arguments
set TEST_TYPE=%1
if "%TEST_TYPE%"=="" set TEST_TYPE=all

echo Test Type: %TEST_TYPE%
echo.

REM Start test databases if needed
if "%TEST_TYPE%"=="setup" (
    echo Starting test databases...
    cd ..
    docker-compose --profile test up -d postgres-test redis-test
    cd chimera
    echo.
    echo Waiting for databases to be ready...
    timeout /t 10 /nobreak >nul
    echo Test databases ready!
    exit /b 0
)

if "%TEST_TYPE%"=="teardown" (
    echo Stopping test databases...
    cd ..
    docker-compose --profile test down
    cd chimera
    echo Test databases stopped!
    exit /b 0
)

REM Run tests based on type
if "%TEST_TYPE%"=="all" (
    echo Running all tests...
    pytest -v
) else if "%TEST_TYPE%"=="unit" (
    echo Running unit tests...
    pytest -m unit -v
) else if "%TEST_TYPE%"=="integration" (
    echo Running integration tests...
    pytest -m integration -v
) else if "%TEST_TYPE%"=="e2e" (
    echo Running end-to-end tests...
    pytest -m e2e -v
) else if "%TEST_TYPE%"=="coverage" (
    echo Running tests with coverage...
    pytest --cov=bot/src --cov=scripts --cov-report=html --cov-report=term-missing
    echo.
    echo Coverage report generated: htmlcov\index.html
) else if "%TEST_TYPE%"=="fast" (
    echo Running fast tests only...
    pytest -m "unit and not slow" -v
) else if "%TEST_TYPE%"=="state" (
    echo Running StateEngine tests...
    pytest -m state_engine -v
) else if "%TEST_TYPE%"=="opportunity" (
    echo Running OpportunityDetector tests...
    pytest -m opportunity_detector -v
) else if "%TEST_TYPE%"=="execution" (
    echo Running ExecutionPlanner tests...
    pytest -m execution_planner -v
) else if "%TEST_TYPE%"=="safety" (
    echo Running SafetyController tests...
    pytest -m safety_controller -v
) else if "%TEST_TYPE%"=="backtest" (
    echo Running backtest tests...
    pytest -m backtest -v
) else (
    echo Unknown test type: %TEST_TYPE%
    echo.
    echo Usage: run_tests.bat [TYPE]
    echo.
    echo Available types:
    echo   all          - Run all tests (default)
    echo   unit         - Run unit tests only
    echo   integration  - Run integration tests
    echo   e2e          - Run end-to-end tests
    echo   coverage     - Run tests with coverage report
    echo   fast         - Run fast tests only
    echo   state        - Run StateEngine tests
    echo   opportunity  - Run OpportunityDetector tests
    echo   execution    - Run ExecutionPlanner tests
    echo   safety       - Run SafetyController tests
    echo   backtest     - Run backtest tests
    echo   setup        - Start test databases
    echo   teardown     - Stop test databases
    exit /b 1
)

echo.
echo ========================================
echo Tests completed!
echo ========================================
