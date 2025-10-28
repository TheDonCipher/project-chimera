# Testing Guide for Project Chimera

This document provides comprehensive instructions for running tests locally for the MEV Liquidation Bot (Project Chimera).

**Task 10.1: Local Testing Infrastructure**

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Test Infrastructure Setup](#test-infrastructure-setup)
3. [Running Tests](#running-tests)
4. [Test Categories](#test-categories)
5. [Coverage Reports](#coverage-reports)
6. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.11+**: Core runtime
- **Docker & Docker Compose**: For test databases
- **pytest**: Testing framework (installed via requirements.txt)

### Installation

```bash
# Install Python dependencies
cd chimera
pip install -r requirements.txt

# Verify pytest installation
pytest --version
```

## Test Infrastructure Setup

### 1. Start Test Databases

The test infrastructure uses isolated database instances to avoid interfering with development data.

```bash
# Start test PostgreSQL and Redis instances
docker-compose --profile test up -d postgres-test redis-test

# Verify services are running
docker-compose ps

# Check health status
docker-compose exec postgres-test pg_isready -U chimera_test_user -d chimera_test
docker-compose exec redis-test redis-cli ping
```

**Test Database Configuration:**

- PostgreSQL: `localhost:5433` (separate port from dev)
- Redis: `localhost:6380` (separate port from dev)
- Database: `chimera_test`
- User: `chimera_test_user`
- Password: `chimera_test_password`

### 2. Environment Variables

Create a `.env.test` file for test-specific configuration:

```bash
# Test environment
ENVIRONMENT=test
LOG_LEVEL=DEBUG
DRY_RUN=true
ENABLE_EXECUTION=false

# Test database connections
DATABASE_URL=postgresql://chimera_test_user:chimera_test_password@localhost:5433/chimera_test
REDIS_HOST=localhost
REDIS_PORT=6380
REDIS_TEST_DB=1

# Mock RPC endpoints (tests use mocks, but these are required for config validation)
ALCHEMY_API_KEY=test_key
ALCHEMY_HTTPS=http://localhost:8545
ALCHEMY_WSS=ws://localhost:8545
QUICKNODE_HTTPS=http://localhost:8546

# Test operator wallet (DO NOT use real keys)
OPERATOR_PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000001
OPERATOR_ADDRESS=0x7E5F4552091A69125d5DfCb7b8C2659029395Bdf
TREASURY_ADDRESS=0x2B5AD5c4795c026514f8317c7a215E218DcCD6cF
```

### 3. Initialize Test Database

```bash
# Run database initialization script
docker-compose exec postgres-test psql -U chimera_test_user -d chimera_test -f /docker-entrypoint-initdb.d/init.sql

# Or use the Python initialization script
python scripts/init_database.py --test
```

## Running Tests

### Quick Start

```bash
# Run all tests with default configuration
cd chimera
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest bot/test_state_engine.py

# Run specific test function
pytest bot/test_state_engine.py::test_block_processing
```

### Test Categories

Tests are organized by markers for selective execution:

#### Unit Tests (Fast, No External Dependencies)

```bash
# Run all unit tests
pytest -m unit

# Run specific module unit tests
pytest -m state_engine
pytest -m opportunity_detector
pytest -m execution_planner
pytest -m safety_controller
```

#### Integration Tests (Multiple Modules)

```bash
# Run all integration tests
pytest -m integration

# Run with test databases
pytest -m "integration and requires_db"
```

#### End-to-End Tests (Full Pipeline)

```bash
# Run e2e tests (requires Anvil fork)
pytest -m e2e

# Run with all external dependencies
pytest -m "e2e and requires_fork"
```

### Advanced Test Execution

#### Run Tests by Module

```bash
# StateEngine tests
pytest -m state_engine -v

# OpportunityDetector tests
pytest -m opportunity_detector -v

# ExecutionPlanner tests
pytest -m execution_planner -v

# SafetyController tests
pytest -m safety_controller -v

# Backtest engine tests
pytest -m backtest -v
```

#### Run Tests with Specific Requirements

```bash
# Tests requiring RPC connection
pytest -m requires_rpc

# Tests requiring database
pytest -m requires_db

# Tests requiring Redis
pytest -m requires_redis

# Tests requiring Anvil fork
pytest -m requires_fork
```

#### Exclude Slow Tests

```bash
# Run fast tests only (exclude slow tests)
pytest -m "not slow"

# Run unit tests excluding slow ones
pytest -m "unit and not slow"
```

### Parallel Execution

```bash
# Install pytest-xdist for parallel execution
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4

# Run with auto-detection of CPU cores
pytest -n auto
```

## Coverage Reports

### Generate Coverage Reports

```bash
# Run tests with coverage (default configuration)
pytest --cov=bot/src --cov=scripts

# Generate HTML coverage report
pytest --cov=bot/src --cov=scripts --cov-report=html

# Open HTML report in browser
# Windows
start htmlcov/index.html

# View coverage in terminal
pytest --cov=bot/src --cov=scripts --cov-report=term-missing
```

### Coverage Thresholds

The project enforces minimum coverage thresholds:

- **Overall Coverage**: 80% minimum
- **Critical Modules**: 95% minimum
  - StateEngine
  - ExecutionPlanner
  - SafetyController

```bash
# Fail if coverage below 80%
pytest --cov-fail-under=80

# Check coverage for specific module
pytest --cov=bot/src/state_engine.py --cov-report=term-missing
```

### Coverage Reports Location

- **HTML Report**: `chimera/htmlcov/index.html`
- **XML Report**: `chimera/coverage.xml` (for CI/CD)
- **Terminal Report**: Displayed after test run

## Test Output and Logs

### Test Logs

```bash
# Enable CLI logging during tests
pytest --log-cli-level=INFO

# Save test logs to file
pytest --log-file=logs/pytest.log --log-file-level=DEBUG

# View test logs
cat logs/pytest.log
```

### Verbose Output

```bash
# Show all test output
pytest -v

# Show local variables on failure
pytest --showlocals

# Show summary of all test outcomes
pytest -ra
```

## Test Data and Fixtures

### Available Fixtures

The `conftest.py` provides comprehensive fixtures:

#### Configuration Fixtures

- `test_config`: Complete test configuration
- `redis_config`: Redis configuration for tests

#### Database Fixtures

- `mock_db_manager`: Mock database manager
- `redis_manager`: Real Redis manager (with fallback)
- `db_session`: Mock database session

#### Mock RPC Fixtures

- `mock_web3`: Mock Web3 instance with Base mainnet responses
- `mock_rpc_responses`: Realistic RPC response data
- `mock_websocket`: Mock WebSocket connection

#### Test Data Generators

- `position_generator`: Generate test Position objects
- `opportunity_generator`: Generate test Opportunity objects
- `execution_record_generator`: Generate test ExecutionRecord objects
- `batch_position_generator`: Generate multiple positions

#### Mock Contract Fixtures

- `mock_chainlink_oracle`: Mock Chainlink price oracle
- `mock_lending_protocol`: Mock lending protocol contract

### Using Fixtures in Tests

```python
def test_example(test_config, position_generator, mock_web3):
    """Example test using fixtures"""
    # Use test configuration
    assert test_config.safety.max_single_execution_usd == Decimal('500')

    # Generate test position
    position = position_generator(
        collateral_amount=2000000000000000000,  # 2 ETH
        debt_amount=3000000000  # 3000 USDC
    )

    # Use mock Web3
    block = mock_web3.eth.get_block('latest')
    assert block['number'] == 10000000
```

## Continuous Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_DB: chimera_test
          POSTGRES_USER: chimera_test_user
          POSTGRES_PASSWORD: chimera_test_password
        ports:
          - 5433:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      redis:
        image: redis:7-alpine
        ports:
          - 6380:6379
        options: >-
          --health-cmd "redis-cli ping"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd chimera
          pip install -r requirements.txt

      - name: Run tests
        run: |
          cd chimera
          pytest --cov=bot/src --cov=scripts --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./chimera/coverage.xml
```

## Troubleshooting

### Common Issues

#### 1. Database Connection Errors

```bash
# Check if test database is running
docker-compose ps postgres-test

# Restart test database
docker-compose restart postgres-test

# Check logs
docker-compose logs postgres-test

# Verify connection
docker-compose exec postgres-test psql -U chimera_test_user -d chimera_test -c "SELECT 1;"
```

#### 2. Redis Connection Errors

```bash
# Check if test Redis is running
docker-compose ps redis-test

# Restart test Redis
docker-compose restart redis-test

# Test connection
docker-compose exec redis-test redis-cli ping

# Clear test data
docker-compose exec redis-test redis-cli FLUSHDB
```

#### 3. Import Errors

```bash
# Ensure you're in the chimera directory
cd chimera

# Verify Python path
python -c "import sys; print(sys.path)"

# Install dependencies
pip install -r requirements.txt

# Run tests with Python path
PYTHONPATH=. pytest
```

#### 4. Coverage Not Generated

```bash
# Install coverage dependencies
pip install pytest-cov

# Run with explicit coverage options
pytest --cov=bot/src --cov-report=html --cov-report=term

# Check if htmlcov directory was created
ls -la htmlcov/
```

#### 5. Slow Tests

```bash
# Identify slow tests
pytest --durations=10

# Run fast tests only
pytest -m "not slow"

# Use parallel execution
pip install pytest-xdist
pytest -n auto
```

### Clean Test Environment

```bash
# Stop and remove test containers
docker-compose --profile test down -v

# Clear test data
rm -rf htmlcov/ .pytest_cache/ .coverage

# Restart fresh
docker-compose --profile test up -d postgres-test redis-test
pytest
```

## Best Practices

### Writing Tests

1. **Use Fixtures**: Leverage shared fixtures from `conftest.py`
2. **Mark Tests**: Add appropriate markers (`@pytest.mark.unit`, etc.)
3. **Isolate Tests**: Each test should be independent
4. **Mock External Dependencies**: Use mocks for RPC, databases in unit tests
5. **Test Edge Cases**: Include boundary conditions and error scenarios
6. **Keep Tests Fast**: Unit tests should run in milliseconds

### Test Organization

```
chimera/
├── bot/
│   ├── src/              # Source code
│   │   ├── state_engine.py
│   │   ├── opportunity_detector.py
│   │   └── ...
│   ├── test_state_engine.py          # Unit tests
│   ├── test_opportunity_detector.py  # Unit tests
│   ├── test_integration.py           # Integration tests
│   └── test_main_integration.py      # E2E tests
├── scripts/
│   ├── backtest_engine.py
│   └── test_backtest_engine.py       # Backtest tests
├── conftest.py           # Shared fixtures
├── pytest.ini            # Pytest configuration
└── TESTING.md           # This file
```

### Example Test Structure

```python
"""
Unit tests for ModuleName
Task X.Y: Description
"""

import pytest
from src.module import ModuleClass

@pytest.mark.unit
@pytest.mark.module_name
def test_basic_functionality(test_config):
    """Test basic functionality"""
    module = ModuleClass(test_config)
    result = module.do_something()
    assert result is not None

@pytest.mark.unit
@pytest.mark.module_name
async def test_async_functionality(test_config, mock_web3):
    """Test async functionality"""
    module = ModuleClass(test_config)
    result = await module.do_something_async()
    assert result is not None

@pytest.mark.integration
@pytest.mark.requires_db
def test_database_integration(test_config, db_session):
    """Test database integration"""
    module = ModuleClass(test_config)
    module.save_to_db(db_session)
    assert db_session.add.called
```

## Quick Reference

### Common Commands

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=bot/src --cov-report=html

# Run specific module
pytest -m state_engine

# Run fast tests only
pytest -m "unit and not slow"

# Run with verbose output
pytest -v --showlocals

# Run in parallel
pytest -n auto

# Generate coverage report
pytest --cov=bot/src --cov-report=term-missing
```

### Test Markers

- `unit`: Unit tests (fast, isolated)
- `integration`: Integration tests (multiple modules)
- `e2e`: End-to-end tests (full pipeline)
- `slow`: Tests that take significant time
- `requires_rpc`: Requires RPC connection
- `requires_db`: Requires database connection
- `requires_redis`: Requires Redis connection
- `requires_fork`: Requires Anvil fork

### Coverage Targets

- Overall: 80% minimum
- Critical modules: 95% minimum
- New code: 90% minimum

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

---

**Task 10.1 Complete**: Local testing infrastructure is fully configured and documented.
