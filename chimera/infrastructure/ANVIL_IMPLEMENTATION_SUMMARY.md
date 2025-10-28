# Anvil Local Fork Implementation Summary

## Task 9.3: Implement local RPC node (optional for advanced testing)

**Status**: ✅ Complete

## What Was Implemented

### 1. Docker Compose Configuration

**File**: `docker-compose.yml`

Added Anvil service with the following features:

- **Base Image**: `ghcr.io/foundry-rs/foundry:latest` (official Foundry image)
- **Network**: Integrated into `chimera-network` for container communication
- **Port**: Exposed on `8545` (standard Ethereum RPC port)
- **Profile**: `testing` (only starts with `--profile testing` flag)
- **Fork Configuration**:
  - Forks from Base mainnet (chain ID 8453)
  - Configurable fork block via `FORK_BLOCK_NUMBER` env var
  - Configurable RPC endpoint via `BASE_RPC_URL` env var
- **State Persistence**:
  - Automatic state saving every 10 seconds
  - Persistent volume `anvil_state` for state storage
  - State survives container restarts
- **Performance Settings**:
  - 10 pre-funded accounts with 10,000 ETH each
  - 30M gas limit per block
  - 50KB code size limit
  - No rate limiting
- **Health Check**: Uses `cast block-number` to verify RPC is responding

### 2. Documentation

Created comprehensive documentation:

#### `ANVIL_SETUP.md` (Full Guide)

- Overview and benefits of using Anvil
- Quick start instructions
- Configuration options (fork block, RPC endpoint)
- State persistence and reset procedures
- Testing workflows (replay liquidations, test contracts, debug)
- Advanced features (impersonate accounts, mine blocks, snapshots)
- Performance considerations (memory, RPC limits, block time)
- Troubleshooting common issues
- Integration with testing (Foundry, Python, E2E)
- Best practices

#### `ANVIL_QUICK_REFERENCE.md` (Command Reference)

- Quick command reference for common operations
- Starting/stopping/restarting Anvil
- Configuration examples
- Reset procedures
- Testing commands
- Useful Cast commands (balance, impersonate, mine, snapshot)
- Bot configuration
- Common workflows
- Troubleshooting commands

#### `README.md` (Infrastructure Overview)

- Added Anvil to infrastructure overview
- Documented testing profile
- Added Anvil to service ports table
- Included Anvil in troubleshooting section

### 3. Scripts and Tooling

#### Test Scripts

**`test-anvil.sh`** (Linux/Mac):

- Automated test suite for Anvil setup
- Checks Docker and Foundry installation
- Starts Anvil if not running
- Waits for Anvil to be ready
- Tests RPC connection
- Verifies chain ID (8453 for Base)
- Tests block retrieval
- Tests account queries
- Tests state manipulation (Anvil-specific)
- Tests block mining
- Provides summary and next steps

**`test-anvil.bat`** (Windows):

- Windows equivalent of test-anvil.sh
- Same test coverage
- Batch script compatible with Windows cmd

#### Reset Script Enhancement

**`reset.bat`** (Updated):

- Added `reset.bat anvil` command
- Stops Anvil container
- Removes anvil_state volume
- Restarts Anvil with fresh fork
- Preserves existing full reset functionality

#### Makefile Commands

**Added to `Makefile`**:

- `make anvil` - Start Anvil local fork
- `make anvil-reset` - Reset Anvil fork state
- `make anvil-logs` - View Anvil logs
- `make fork-test` - Run tests against local fork
- `make monitoring` - Start monitoring stack (bonus)
- Updated help text with new commands

### 4. Configuration

#### `.env.example` (Updated)

Added Anvil configuration section:

- `BASE_RPC_URL` - RPC URL to fork from
- `FORK_BLOCK_NUMBER` - Specific block to fork at
- Instructions for using Anvil with bot
- Examples and documentation

#### `SETUP.md` (Updated)

Added "Optional: Anvil Local Fork" section:

- Overview of Anvil benefits
- Quick start instructions
- Verification steps
- Bot configuration
- Fork configuration
- Reset procedures
- Test execution
- Reference to detailed documentation

#### `README.md` (Updated)

Added Anvil to development section:

- Quick command to start Anvil
- Reference to documentation

## Requirements Met

✅ **Define Anvil/Hardhat container for Base mainnet fork**

- Anvil container defined in docker-compose.yml
- Configured to fork Base mainnet (chain ID 8453)
- Uses official Foundry image

✅ **Configure fork from Base mainnet at specific block height**

- `FORK_BLOCK_NUMBER` environment variable
- Defaults to latest block if not specified
- Documented in .env.example and ANVIL_SETUP.md

✅ **Set up automatic state persistence between restarts**

- State saved to `/anvil-state/state.json` every 10 seconds
- Persistent Docker volume `anvil_state`
- State survives container restarts
- Documented in ANVIL_SETUP.md

✅ **Document how to reset fork state for testing**

- `reset.bat anvil` command
- `make anvil-reset` command
- Manual reset instructions in ANVIL_SETUP.md
- Documented in ANVIL_QUICK_REFERENCE.md

## Usage Examples

### Start Anvil

```bash
# Using Docker Compose
docker-compose --profile testing up -d anvil

# Using Makefile
make anvil
```

### Verify Anvil

```bash
# Check block number
cast block-number --rpc-url http://localhost:8545

# Run test suite
chimera/infrastructure/test-anvil.bat
```

### Configure Bot to Use Anvil

```bash
# Update .env
ALCHEMY_HTTPS=http://localhost:8545
QUICKNODE_HTTPS=http://localhost:8545
```

### Reset Fork State

```bash
# Using reset script
reset.bat anvil

# Using Makefile
make anvil-reset
```

### Run Tests Against Fork

```bash
# Using Makefile
make fork-test

# Or manually
cd chimera/contracts
forge test --fork-url http://localhost:8545 -vvv
```

## Files Created/Modified

### Created

1. `chimera/infrastructure/ANVIL_SETUP.md` - Comprehensive setup guide
2. `chimera/infrastructure/ANVIL_QUICK_REFERENCE.md` - Quick command reference
3. `chimera/infrastructure/ANVIL_IMPLEMENTATION_SUMMARY.md` - This file
4. `chimera/infrastructure/README.md` - Infrastructure overview
5. `chimera/infrastructure/test-anvil.sh` - Linux/Mac test script
6. `chimera/infrastructure/test-anvil.bat` - Windows test script

### Modified

1. `docker-compose.yml` - Added Anvil service and volume
2. `.env.example` - Added Anvil configuration section
3. `SETUP.md` - Added Anvil setup section
4. `README.md` - Added Anvil to development section
5. `reset.bat` - Added Anvil reset functionality
6. `Makefile` - Added Anvil commands

## Testing

The implementation can be tested using:

1. **Automated Test Suite**:

   ```bash
   chimera/infrastructure/test-anvil.bat
   ```

2. **Manual Verification**:

   ```bash
   # Start Anvil
   make anvil

   # Check it's running
   cast block-number --rpc-url http://localhost:8545

   # Test state manipulation
   cast rpc anvil_setBalance 0x1234567890123456789012345678901234567890 0x1000000000000000000 --rpc-url http://localhost:8545

   # Verify balance
   cast balance 0x1234567890123456789012345678901234567890 --rpc-url http://localhost:8545
   ```

3. **Integration Testing**:
   ```bash
   # Run Foundry tests against fork
   make fork-test
   ```

## Benefits

1. **Zero Gas Costs**: Test liquidations without spending real ETH
2. **Reproducible Tests**: Fork at specific blocks for consistent testing
3. **Fast Iteration**: Instant block mining, no waiting for confirmations
4. **State Manipulation**: Set balances, impersonate accounts, control time
5. **Realistic Environment**: Fork real mainnet state, not mocked data
6. **Debugging**: Trace transactions, inspect state, test edge cases
7. **CI/CD Ready**: Can be used in automated testing pipelines

## Next Steps

With Anvil implemented, you can now:

1. **Replay Historical Liquidations**: Fork at blocks with known liquidations and test bot logic
2. **Test Contract Deployment**: Deploy Chimera contract to local fork
3. **Debug Transactions**: Use Anvil's tracing features to debug failed transactions
4. **Benchmark Performance**: Measure bot latency on local fork
5. **Integration Testing**: Test full bot pipeline against realistic state
6. **Stress Testing**: Run bot for extended periods against fork

## References

- Task: `.kiro/specs/mev-liquidation-bot/tasks.md` - Task 9.3
- Requirements: `.kiro/specs/mev-liquidation-bot/requirements.md` - REQ-TEST-003, 7.2.1
- Design: `.kiro/specs/mev-liquidation-bot/design.md` - Local Fork Testing section
- Foundry Book: https://book.getfoundry.sh/anvil/
- Base Docs: https://docs.base.org/
