# Anvil Local RPC Node Setup

This guide explains how to use the Anvil local RPC node for advanced testing with a Base mainnet fork.

## Overview

Anvil is a local Ethereum node designed for development and testing. It's part of the Foundry toolkit and provides:

- **Fast forking**: Fork Base mainnet at any block height
- **State persistence**: Automatically saves state between restarts
- **Unlimited funds**: Pre-funded test accounts
- **No rate limits**: Unlimited RPC calls
- **Instant mining**: Zero block time for fast testing

## Quick Start

### 1. Start Anvil Node

```bash
# Start Anvil with the testing profile
docker-compose --profile testing up -d anvil

# Or start all testing services
docker-compose --profile testing up -d
```

### 2. Verify Node is Running

```bash
# Check container status
docker ps | grep anvil

# Check block number (should match fork block or be higher)
cast block-number --rpc-url http://localhost:8545

# Get chain ID (should be 8453 for Base)
cast chain-id --rpc-url http://localhost:8545
```

### 3. Use in Bot Configuration

Update your `.env` file to use the local Anvil node:

```bash
# Use Anvil for local testing
ALCHEMY_HTTPS=http://localhost:8545
QUICKNODE_HTTPS=http://localhost:8545

# Or use Anvil as backup
# ALCHEMY_HTTPS=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
# QUICKNODE_HTTPS=http://localhost:8545
```

## Configuration

### Fork Block Number

By default, Anvil forks from the latest block. To fork from a specific block:

```bash
# Set in .env file
FORK_BLOCK_NUMBER=10000000

# Or pass directly
docker-compose --profile testing run --rm anvil \
  anvil --fork-url $BASE_RPC_URL --fork-block-number 10000000
```

### Fork URL

By default, Anvil forks from `https://mainnet.base.org`. To use a different RPC:

```bash
# Set in .env file
BASE_RPC_URL=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY

# Restart Anvil
docker-compose --profile testing restart anvil
```

## State Persistence

Anvil automatically saves state to `/anvil-state/state.json` every 10 seconds. This means:

- State persists between container restarts
- You can stop and start Anvil without losing data
- Transactions and state changes are preserved

### Reset Fork State

To reset Anvil to a fresh fork:

```bash
# Stop Anvil
docker-compose --profile testing stop anvil

# Remove state volume
docker volume rm project-chimera_anvil_state

# Start Anvil (will create fresh fork)
docker-compose --profile testing up -d anvil
```

Or use the reset script:

```bash
# Windows
reset.bat anvil

# Linux/Mac
./reset.sh anvil
```

## Testing Workflows

### Replay Historical Liquidations

```bash
# 1. Fork at specific block before liquidation
FORK_BLOCK_NUMBER=9500000 docker-compose --profile testing up -d anvil

# 2. Configure bot to use Anvil
# Update .env: ALCHEMY_HTTPS=http://localhost:8545

# 3. Run bot in dry-run mode
docker-compose up bot

# 4. Observe bot detecting and simulating liquidation
# Check logs: docker-compose logs -f bot
```

### Test Contract Interactions

```bash
# 1. Start Anvil
docker-compose --profile testing up -d anvil

# 2. Deploy contract to local fork
cd chimera/contracts
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# 3. Interact with contract
cast call <CONTRACT_ADDRESS> "owner()" --rpc-url http://localhost:8545

# 4. Send transactions (instant mining)
cast send <CONTRACT_ADDRESS> "pause()" \
  --rpc-url http://localhost:8545 \
  --private-key <PRIVATE_KEY>
```

### Test State Reconciliation

```bash
# 1. Start Anvil and bot
docker-compose --profile testing up -d anvil
docker-compose up -d bot

# 2. Manually manipulate state
cast rpc anvil_setBalance <ADDRESS> 0x1000000000000000000 \
  --rpc-url http://localhost:8545

# 3. Observe bot detecting state divergence
docker-compose logs -f bot | grep "divergence"
```

## Advanced Features

### Impersonate Accounts

```bash
# Impersonate any address (useful for testing liquidations)
cast rpc anvil_impersonateAccount <ADDRESS> --rpc-url http://localhost:8545

# Send transaction as impersonated account
cast send <CONTRACT> "liquidate(...)" \
  --from <ADDRESS> \
  --rpc-url http://localhost:8545 \
  --unlocked
```

### Mine Blocks Manually

```bash
# Mine a single block
cast rpc evm_mine --rpc-url http://localhost:8545

# Mine multiple blocks
cast rpc anvil_mine 10 --rpc-url http://localhost:8545

# Set block timestamp
cast rpc evm_setNextBlockTimestamp 1700000000 --rpc-url http://localhost:8545
```

### Snapshot and Revert

```bash
# Create snapshot
SNAPSHOT_ID=$(cast rpc evm_snapshot --rpc-url http://localhost:8545)

# Make changes...

# Revert to snapshot
cast rpc evm_revert $SNAPSHOT_ID --rpc-url http://localhost:8545
```

## Performance Considerations

### Memory Usage

Anvil can use significant memory when forking mainnet:

- **Initial fork**: ~2-4 GB
- **After transactions**: Can grow to 8+ GB
- **With state persistence**: Disk usage grows over time

Monitor with:

```bash
docker stats chimera-anvil
```

### RPC Rate Limits

When forking, Anvil makes RPC calls to the upstream provider. Be aware of:

- **Alchemy**: 330 requests/second on free tier
- **QuickNode**: Varies by plan
- **Public RPCs**: Often rate limited

Use a paid RPC endpoint for best performance.

### Block Time

Anvil mines blocks instantly by default. To simulate real block times:

```bash
# Mine blocks every 2 seconds (Base L2 block time)
docker-compose --profile testing run --rm anvil \
  anvil --fork-url $BASE_RPC_URL --block-time 2
```

## Troubleshooting

### Issue: "Failed to get fork block"

**Cause**: Invalid fork block number or RPC endpoint

**Solution**:

```bash
# Check RPC endpoint is accessible
curl -X POST $BASE_RPC_URL \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Use latest block (remove FORK_BLOCK_NUMBER)
unset FORK_BLOCK_NUMBER
docker-compose --profile testing restart anvil
```

### Issue: "Connection refused" when bot tries to connect

**Cause**: Anvil not fully started or wrong network

**Solution**:

```bash
# Check Anvil is running
docker-compose --profile testing ps anvil

# Check Anvil logs
docker-compose --profile testing logs anvil

# Verify bot can reach Anvil (from bot container)
docker-compose exec bot curl http://anvil:8545
```

### Issue: State grows too large

**Cause**: Many transactions over time

**Solution**:

```bash
# Reset state (see "Reset Fork State" above)
docker-compose --profile testing stop anvil
docker volume rm project-chimera_anvil_state
docker-compose --profile testing up -d anvil
```

### Issue: Fork is outdated

**Cause**: Forked at old block, mainnet has moved forward

**Solution**:

```bash
# Fork from latest block
unset FORK_BLOCK_NUMBER
docker-compose --profile testing restart anvil

# Or fork from specific recent block
FORK_BLOCK_NUMBER=$(cast block-number --rpc-url $BASE_RPC_URL)
docker-compose --profile testing restart anvil
```

## Integration with Testing

### Unit Tests (Foundry)

```bash
# Run tests against local fork
cd chimera/contracts
forge test --fork-url http://localhost:8545 -vvv
```

### Integration Tests (Python)

```python
# bot/tests/test_integration.py
import pytest
from web3 import Web3

@pytest.fixture
def anvil_web3():
    """Connect to local Anvil node"""
    return Web3(Web3.HTTPProvider("http://localhost:8545"))

def test_liquidation_on_fork(anvil_web3):
    """Test liquidation against forked mainnet"""
    # Setup: Fork at block with liquidatable position
    # Execute: Run bot liquidation logic
    # Assert: Verify profit and state changes
    pass
```

### End-to-End Tests

```bash
# 1. Start full stack with Anvil
docker-compose --profile testing up -d

# 2. Run E2E test suite
cd chimera/bot
pytest tests/e2e/ -v

# 3. Verify results in database
docker-compose exec postgres psql -U chimera_user -d chimera \
  -c "SELECT * FROM executions ORDER BY timestamp DESC LIMIT 10;"
```

## Best Practices

1. **Use specific fork blocks**: For reproducible tests, always specify `FORK_BLOCK_NUMBER`
2. **Reset between test runs**: Clear state to ensure clean test environment
3. **Monitor resources**: Anvil can consume significant memory/disk
4. **Use snapshots**: For fast test iteration, use `evm_snapshot` and `evm_revert`
5. **Separate profiles**: Keep Anvil in `testing` profile to avoid accidental mainnet forks
6. **Document fork blocks**: Note which blocks have interesting liquidations for testing

## Resources

- [Foundry Book - Anvil](https://book.getfoundry.sh/anvil/)
- [Anvil RPC Methods](https://book.getfoundry.sh/reference/anvil/)
- [Cast CLI Reference](https://book.getfoundry.sh/reference/cast/)
- [Base Network Documentation](https://docs.base.org/)

## Next Steps

After setting up Anvil:

1. **Test contract deployment**: Deploy Chimera contract to local fork
2. **Replay liquidations**: Use historical data to test bot logic
3. **Benchmark performance**: Measure bot latency on local fork
4. **Validate state sync**: Test StateEngine reconciliation logic
5. **Stress test**: Run bot for extended periods to find edge cases
