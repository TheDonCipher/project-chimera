# Test Infrastructure

This directory contains the test infrastructure for Project Chimera.

## Quick Start

```bash
# 1. Start test databases
./run_tests.sh setup
# or on Windows:
run_tests.bat setup

# 2. Run all tests
./run_tests.sh all
# or on Windows:
run_tests.bat all

# 3. View coverage report
# Open htmlcov/index.html in your browser
```

## Directory Structure

```
chimera/
├── bot/
│   ├── src/                          # Source code
│   ├── test_state_engine.py          # StateEngine unit tests
│   ├── test_opportunity_detector.py  # OpportunityDetector unit tests
│   ├── test_execution_planner.py     # ExecutionPlanner unit tests
│   ├── test_safety_controller.py     # SafetyController unit tests
│   ├── test_integration.py           # Integration tests
│   └── test_main_integration.py      # E2E tests
├── scripts/
│   └── test_backtest_engine.py       # Backtest tests
├── tests/                            # This directory
│   └── README.md                     # This file
├── conftest.py                       # Shared test fixtures
├── pytest.ini                        # Pytest configuration
├── .env.test                         # Test environment variables
├── run_tests.sh                      # Test runner (Linux/Mac)
├── run_tests.bat                     # Test runner (Windows)
└── TESTING.md                        # Comprehensive testing guide
```

## Test Categories

### Unit Tests

- **Location**: `bot/test_*.py`, `scripts/test_*.py`
- **Marker**: `@pytest.mark.unit`
- **Dependencies**: None (uses mocks)
- **Speed**: Fast (<1s per test)
- **Coverage Target**: 80%+

### Integration Tests

- **Location**: `bot/test_integration.py`
- **Marker**: `@pytest.mark.integration`
- **Dependencies**: Test databases (optional)
- **Speed**: Medium (1-5s per test)
- **Coverage Target**: 90%+

### End-to-End Tests

- **Location**: `bot/test_main_integration.py`
- **Marker**: `@pytest.mark.e2e`
- **Dependencies**: Anvil fork, test databases
- **Speed**: Slow (5-30s per test)
- **Coverage Target**: 95%+

## Available Fixtures

See `conftest.py` for complete fixture documentation.

### Configuration

- `test_config`: Complete test configuration
- `redis_config`: Redis configuration

### Databases

- `mock_db_manager`: Mock PostgreSQL manager
- `redis_manager`: Real Redis manager (with fallback)
- `db_session`: Mock database session

### Mock RPC

- `mock_web3`: Mock Web3 with Base mainnet responses
- `mock_rpc_responses`: Realistic RPC response data
- `mock_websocket`: Mock WebSocket connection

### Test Data Generators

- `position_generator`: Generate Position objects
- `opportunity_generator`: Generate Opportunity objects
- `execution_record_generator`: Generate ExecutionRecord objects
- `batch_position_generator`: Generate multiple positions

### Mock Contracts

- `mock_chainlink_oracle`: Mock Chainlink oracle
- `mock_lending_protocol`: Mock lending protocol

## Running Tests

### Basic Commands

```bash
# All tests
pytest

# Specific module
pytest bot/test_state_engine.py

# Specific test
pytest bot/test_state_engine.py::test_block_processing

# With coverage
pytest --cov=bot/src --cov-report=html
```

### Using Test Runner Scripts

```bash
# Linux/Mac
./run_tests.sh [TYPE]

# Windows
run_tests.bat [TYPE]

# Available types:
# - all: All tests
# - unit: Unit tests only
# - integration: Integration tests
# - e2e: End-to-end tests
# - coverage: Tests with coverage report
# - fast: Fast tests only
# - state: StateEngine tests
# - opportunity: OpportunityDetector tests
# - execution: ExecutionPlanner tests
# - safety: SafetyController tests
# - backtest: Backtest tests
# - setup: Start test databases
# - teardown: Stop test databases
```

## Test Markers

Use markers to run specific test categories:

```bash
# By category
pytest -m unit
pytest -m integration
pytest -m e2e

# By module
pytest -m state_engine
pytest -m opportunity_detector
pytest -m execution_planner
pytest -m safety_controller

# By requirements
pytest -m requires_db
pytest -m requires_redis
pytest -m requires_rpc
pytest -m requires_fork

# Exclude slow tests
pytest -m "not slow"
```

## Coverage Reports

```bash
# Generate HTML report
pytest --cov=bot/src --cov-report=html

# View in browser
# Windows: start htmlcov\index.html
# Linux: xdg-open htmlcov/index.html
# Mac: open htmlcov/index.html

# Terminal report with missing lines
pytest --cov=bot/src --cov-report=term-missing

# Fail if coverage below threshold
pytest --cov-fail-under=80
```

## Writing Tests

### Example Unit Test

```python
import pytest
from src.module import MyModule

@pytest.mark.unit
@pytest.mark.module_name
def test_basic_functionality(test_config):
    """Test basic functionality"""
    module = MyModule(test_config)
    result = module.do_something()
    assert result is not None
```

### Example Integration Test

```python
import pytest

@pytest.mark.integration
@pytest.mark.requires_db
async def test_database_integration(test_config, db_session):
    """Test database integration"""
    module = MyModule(test_config)
    await module.save_to_db(db_session)
    assert db_session.add.called
```

### Example E2E Test

```python
import pytest

@pytest.mark.e2e
@pytest.mark.requires_fork
@pytest.mark.slow
async def test_full_pipeline(test_config, mock_web3):
    """Test complete liquidation pipeline"""
    # Setup
    state_engine = StateEngine(test_config)
    detector = OpportunityDetector(test_config)
    planner = ExecutionPlanner(test_config)

    # Execute
    await state_engine.start()
    opportunities = await detector.scan()
    bundles = await planner.plan(opportunities)

    # Verify
    assert len(bundles) > 0
```

## Troubleshooting

### Database Connection Issues

```bash
# Check if test databases are running
docker-compose ps postgres-test redis-test

# Restart test databases
docker-compose restart postgres-test redis-test

# View logs
docker-compose logs postgres-test
docker-compose logs redis-test
```

### Import Errors

```bash
# Ensure you're in chimera directory
cd chimera

# Install dependencies
pip install -r requirements.txt

# Run with explicit Python path
PYTHONPATH=. pytest
```

### Slow Tests

```bash
# Identify slow tests
pytest --durations=10

# Run fast tests only
pytest -m "not slow"

# Use parallel execution
pip install pytest-xdist
pytest -n auto
```

## Best Practices

1. **Use Fixtures**: Leverage shared fixtures from `conftest.py`
2. **Mark Tests**: Add appropriate markers for categorization
3. **Isolate Tests**: Each test should be independent
4. **Mock External Dependencies**: Use mocks for RPC, databases in unit tests
5. **Test Edge Cases**: Include boundary conditions and error scenarios
6. **Keep Tests Fast**: Unit tests should run in milliseconds
7. **Document Tests**: Add docstrings explaining what is being tested
8. **Clean Up**: Use fixtures for automatic cleanup

## Resources

- [Full Testing Guide](../TESTING.md)
- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [pytest-asyncio Documentation](https://pytest-asyncio.readthedocs.io/)

---

**Task 10.1**: Local testing infrastructure setup complete.
