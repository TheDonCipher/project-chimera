# Anvil Quick Reference

Quick command reference for working with Anvil local fork.

## Starting and Stopping

```bash
# Start Anvil
docker-compose --profile testing up -d anvil
make anvil

# Stop Anvil
docker-compose --profile testing stop anvil

# Restart Anvil
docker-compose --profile testing restart anvil

# View logs
docker-compose --profile testing logs -f anvil
make anvil-logs
```

## Configuration

```bash
# Fork from specific block
FORK_BLOCK_NUMBER=10000000 docker-compose --profile testing up -d anvil

# Use custom RPC endpoint
BASE_RPC_URL=https://your-rpc-url docker-compose --profile testing up -d anvil
```

## Reset State

```bash
# Reset to fresh fork
reset.bat anvil           # Windows
./reset.sh anvil          # Linux/Mac
make anvil-reset          # Any platform
```

## Testing

```bash
# Run Foundry tests against fork
make fork-test
cd chimera/contracts && forge test --fork-url http://localhost:8545 -vvv

# Check connection
cast block-number --rpc-url http://localhost:8545
cast chain-id --rpc-url http://localhost:8545
```

## Useful Cast Commands

```bash
# Get block information
cast block latest --rpc-url http://localhost:8545
cast block 10000000 --rpc-url http://localhost:8545

# Get account balance
cast balance <ADDRESS> --rpc-url http://localhost:8545

# Set account balance (for testing)
cast rpc anvil_setBalance <ADDRESS> 0x1000000000000000000 --rpc-url http://localhost:8545

# Impersonate account
cast rpc anvil_impersonateAccount <ADDRESS> --rpc-url http://localhost:8545

# Mine blocks
cast rpc evm_mine --rpc-url http://localhost:8545
cast rpc anvil_mine 10 --rpc-url http://localhost:8545

# Set block timestamp
cast rpc evm_setNextBlockTimestamp 1700000000 --rpc-url http://localhost:8545

# Create snapshot
cast rpc evm_snapshot --rpc-url http://localhost:8545

# Revert to snapshot
cast rpc evm_revert <SNAPSHOT_ID> --rpc-url http://localhost:8545

# Get transaction receipt
cast receipt <TX_HASH> --rpc-url http://localhost:8545

# Call contract (read-only)
cast call <CONTRACT> "functionName()" --rpc-url http://localhost:8545

# Send transaction
cast send <CONTRACT> "functionName()" --rpc-url http://localhost:8545 --private-key <KEY>
```

## Bot Configuration

```bash
# Update .env to use Anvil
ALCHEMY_HTTPS=http://localhost:8545
QUICKNODE_HTTPS=http://localhost:8545

# Or from bot container
ALCHEMY_HTTPS=http://anvil:8545
QUICKNODE_HTTPS=http://anvil:8545
```

## Common Workflows

### Replay Historical Liquidation

```bash
# 1. Fork at block before liquidation
FORK_BLOCK_NUMBER=9500000 docker-compose --profile testing up -d anvil

# 2. Update bot config to use Anvil
# Edit .env: ALCHEMY_HTTPS=http://localhost:8545

# 3. Run bot
docker-compose up bot

# 4. Check logs
docker-compose logs -f bot
```

### Test Contract Deployment

```bash
# 1. Start Anvil
make anvil

# 2. Deploy contract
cd chimera/contracts
forge script script/Deploy.s.sol --rpc-url http://localhost:8545 --broadcast

# 3. Verify deployment
cast call <CONTRACT_ADDRESS> "owner()" --rpc-url http://localhost:8545
```

### Debug Transaction

```bash
# 1. Send transaction
TX_HASH=$(cast send <CONTRACT> "functionName()" --rpc-url http://localhost:8545 --private-key <KEY> --json | jq -r .transactionHash)

# 2. Get receipt
cast receipt $TX_HASH --rpc-url http://localhost:8545

# 3. Trace transaction
cast run $TX_HASH --rpc-url http://localhost:8545 --debug
```

## Troubleshooting

```bash
# Check if Anvil is running
docker ps | grep anvil

# Check Anvil health
cast block-number --rpc-url http://localhost:8545

# View Anvil logs
docker-compose --profile testing logs anvil

# Check disk usage
docker system df

# Clean up old state
docker volume rm project-chimera_anvil_state
```

## Resources

- Full documentation: `chimera/infrastructure/ANVIL_SETUP.md`
- Foundry Book: https://book.getfoundry.sh/anvil/
- Cast Reference: https://book.getfoundry.sh/reference/cast/
