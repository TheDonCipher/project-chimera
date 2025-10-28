# Running Foundry Tests

## Quick Start

```bash
# Run all tests (unit + integration, excluding fork tests)
forge test --no-match-test Fork -vv

# Run all tests including fork tests (requires BASE_RPC_URL in .env)
forge test -vv

# Run only unit tests
forge test --match-path test/Chimera.t.sol -vv

# Run only integration tests
forge test --match-path test/ChimeraIntegration.t.sol -vv

# Run only fork tests (requires RPC)
forge test --match-path test/ChimeraFork.t.sol -vv --fork-url $BASE_RPC_URL
```

## Test Summary

- **Unit Tests (Chimera.t.sol)**: 31 tests
- **Integration Tests (ChimeraIntegration.t.sol)**: 10 tests
- **Fork Tests (ChimeraFork.t.sol)**: 12 tests
- **Total**: 53 tests

## Coverage Report

```bash
# Generate coverage report
forge coverage --no-match-test Fork

# Generate coverage with fork tests (requires RPC)
forge coverage
```

## Gas Report

```bash
# Generate gas usage report
forge test --gas-report --no-match-test Fork
```

## Troubleshooting

### Stack Too Deep Error

✅ **FIXED** - Updated `foundry.toml` to use `via_ir = true`

### Fork Tests Require RPC

Fork tests need a Base mainnet RPC URL. Create a `.env` file:

```bash
BASE_RPC_URL=https://mainnet.base.org
# or use Alchemy/QuickNode/etc
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_API_KEY
```

Then run:

```bash
source .env
forge test --match-path test/ChimeraFork.t.sol -vv --fork-url $BASE_RPC_URL
```

## Expected Results

All tests should pass:

- ✅ 31 unit tests
- ✅ 10 integration tests
- ✅ 12 fork tests (with RPC)

Expected coverage: **>95%**
