#!/bin/bash
# Test runner script for Project Chimera (Linux/Mac)
# Task 10.1: Local testing infrastructure

set -e

echo "========================================"
echo "Project Chimera - Test Runner"
echo "========================================"
echo ""

# Check if we're in the chimera directory
if [ ! -f "pytest.ini" ]; then
    echo "Error: Must be run from chimera directory"
    echo "Current directory: $(pwd)"
    exit 1
fi

# Parse command line arguments
TEST_TYPE=${1:-all}

echo "Test Type: $TEST_TYPE"
echo ""

# Start test databases if needed
if [ "$TEST_TYPE" = "setup" ]; then
    echo "Starting test databases..."
    cd ..
    docker-compose --profile test up -d postgres-test redis-test
    cd chimera
    echo ""
    echo "Waiting for databases to be ready..."
    sleep 10
    echo "Test databases ready!"
    exit 0
fi

if [ "$TEST_TYPE" = "teardown" ]; then
    echo "Stopping test databases..."
    cd ..
    docker-compose --profile test down
    cd chimera
    echo "Test databases stopped!"
    exit 0
fi

# Run tests based on type
case $TEST_TYPE in
    all)
        echo "Running all tests..."
        pytest -v
        ;;
    unit)
        echo "Running unit tests..."
        pytest -m unit -v
        ;;
    integration)
        echo "Running integration tests..."
        pytest -m integration -v
        ;;
    e2e)
        echo "Running end-to-end tests..."
        pytest -m e2e -v
        ;;
    coverage)
        echo "Running tests with coverage..."
        pytest --cov=bot/src --cov=scripts --cov-report=html --cov-report=term-missing
        echo ""
        echo "Coverage report generated: htmlcov/index.html"
        ;;
    fast)
        echo "Running fast tests only..."
        pytest -m "unit and not slow" -v
        ;;
    state)
        echo "Running StateEngine tests..."
        pytest -m state_engine -v
        ;;
    opportunity)
        echo "Running OpportunityDetector tests..."
        pytest -m opportunity_detector -v
        ;;
    execution)
        echo "Running ExecutionPlanner tests..."
        pytest -m execution_planner -v
        ;;
    safety)
        echo "Running SafetyController tests..."
        pytest -m safety_controller -v
        ;;
    backtest)
        echo "Running backtest tests..."
        pytest -m backtest -v
        ;;
    *)
        echo "Unknown test type: $TEST_TYPE"
        echo ""
        echo "Usage: ./run_tests.sh [TYPE]"
        echo ""
        echo "Available types:"
        echo "  all          - Run all tests (default)"
        echo "  unit         - Run unit tests only"
        echo "  integration  - Run integration tests"
        echo "  e2e          - Run end-to-end tests"
        echo "  coverage     - Run tests with coverage report"
        echo "  fast         - Run fast tests only"
        echo "  state        - Run StateEngine tests"
        echo "  opportunity  - Run OpportunityDetector tests"
        echo "  execution    - Run ExecutionPlanner tests"
        echo "  safety       - Run SafetyController tests"
        echo "  backtest     - Run backtest tests"
        echo "  setup        - Start test databases"
        echo "  teardown     - Stop test databases"
        exit 1
        ;;
esac

echo ""
echo "========================================"
echo "Tests completed!"
echo "========================================"
