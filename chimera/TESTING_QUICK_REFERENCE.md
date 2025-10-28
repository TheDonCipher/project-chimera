# Testing Quick Reference Card

## Setup (One-Time)

```bash
# Install dependencies
pip install -r requirements.txt

# Start test databases
./run_tests.sh setup    # Linux/Mac
run_tests.bat setup     # Windows
```

## Common Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bot/src --cov-report=html

# Run specific module
pytest bot/test_state_engine.py

# Run by marker
pytest -m unit
pytest -m integration
pytest -m state_engine

# Run fast tests only
pytest -m "not slow"

# Verbose output
pytest -v --showlocals
```

## Test Runner Scripts

```bash
./run_tests.sh [TYPE]    # Linux/Mac
run_tests.bat [TYPE]     # Windows

# Types:
# all          - All tests
# unit         - Unit tests only
# integration  - Integration tests
# e2e          - End-to-end tests
# coverage     - With coverage report
# fast         - Fast tests only
# state        - StateEngine tests
# opportunity  - OpportunityDetector tests
# execution    - ExecutionPlanner tests
# safety       - SafetyController tests
# backtest     - Backtest tests
# setup        - Start test databases
# teardown     - Stop test databases
```

## Coverage

```bash
# Generate HTML report
pytest --cov=bot/src --cov-report=html

# View report
start htmlcov\index.html    # Windows
open htmlcov/index.html     # Mac
xdg-open htmlcov/index.html # Linux

# Terminal report
pytest --cov=bot/src --cov-report=term-missing
```

## Test Markers

```bash
-m unit              # Unit tests
-m integration       # Integration tests
-m e2e               # End-to-end tests
-m slow              # Slow tests
-m "not slow"        # Fast tests only
-m requires_db       # Needs database
-m requires_redis    # Needs Redis
-m requires_rpc      # Needs RPC
-m requires_fork     # Needs Anvil fork
-m state_engine      # StateEngine tests
-m opportunity_detector  # OpportunityDetector tests
-m execution_planner     # ExecutionPlanner tests
-m safety_controller     # SafetyController tests
-m backtest          # Backtest tests
```

## Troubleshooting

```bash
# Check test databases
docker-compose ps postgres-test redis-test

# Restart test databases
docker-compose restart postgres-test redis-test

# View logs
docker-compose logs postgres-test
docker-compose logs redis-test

# Clean environment
docker-compose --profile test down -v
rm -rf htmlcov/ .pytest_cache/ .coverage
```

## Files

- `pytest.ini` - Pytest configuration
- `conftest.py` - Shared fixtures
- `.env.test` - Test environment
- `TESTING.md` - Full guide
- `tests/README.md` - Test infrastructure docs

## Coverage Targets

- Overall: 80% minimum
- Critical modules: 95% minimum
- New code: 90% minimum
