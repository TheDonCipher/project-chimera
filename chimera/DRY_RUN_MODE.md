# Dry-Run Mode Documentation

## Overview

Dry-run mode allows you to test the Chimera MEV liquidation bot against live Base mainnet data **without submitting any actual transactions**. This is essential for:

- Validating opportunity detection logic
- Testing simulation accuracy
- Measuring theoretical profitability
- Debugging issues safely
- Collecting performance data before risking capital

## How It Works

In dry-run mode, the bot:

1. ✅ **Connects to live Base mainnet** via RPC providers
2. ✅ **Monitors real-time blockchain state** (blocks, events, positions)
3. ✅ **Detects liquidation opportunities** using actual on-chain data
4. ✅ **Simulates transactions** via `eth_call` to calculate profit
5. ✅ **Logs all results** with detailed metrics
6. ❌ **Does NOT submit transactions** to the blockchain
7. ❌ **Does NOT spend gas** or risk capital

All opportunity detection, health factor calculations, oracle price checks, and profit simulations run exactly as they would in production mode. The only difference is that bundle submission is skipped.

## Usage

### Starting Dry-Run Mode

```bash
# Basic usage
python -m chimera.bot.src.main --dry-run

# With custom configuration
python -m chimera.bot.src.main --dry-run --config config.yaml
```

### Stopping Dry-Run Mode

Press `Ctrl+C` to gracefully shutdown the bot. All logs will be flushed before exit.

### Monitoring Dry-Run Execution

The bot logs dry-run events with the `[DRY-RUN]` prefix:

```bash
# Tail logs in real-time
tail -f logs/chimera.log | grep "DRY-RUN"

# Or use the logs script
./logs.sh
```

Example log output:

```json
{
  "timestamp": "2024-10-28T15:30:45.123Z",
  "level": "INFO",
  "module": "chimera",
  "event": "[DRY-RUN] Would submit bundle",
  "context": {
    "dry_run": true,
    "protocol": "moonwell",
    "borrower": "0x1234...",
    "net_profit_usd": 75.5,
    "simulated_profit_usd": 120.0,
    "total_cost_usd": 44.5,
    "submission_path": "mempool",
    "health_factor": 0.85,
    "theoretical_profit_total": 1250.75,
    "simulations_success": 18,
    "simulations_failed": 2
  }
}
```

### Generating Performance Reports

After running in dry-run mode for a period (recommended: 24 hours), generate a performance report:

```bash
# Analyze last 24 hours
python chimera/bot/dry_run_report.py --hours 24

# Analyze all logs
python chimera/bot/dry_run_report.py

# Save detailed report to JSON
python chimera/bot/dry_run_report.py --hours 24 --output report.json
```

Example report output:

```
================================================================================
DRY-RUN PERFORMANCE REPORT
================================================================================

📊 SUMMARY
--------------------------------------------------------------------------------
  Time Period:              2024-10-27T15:00:00 to 2024-10-28T15:00:00
  Duration:                 24.00 hours
  Total Opportunities:      42
  Opportunities/Hour:       1.75
  Simulation Success Rate:  100.00%

💰 THEORETICAL PROFITABILITY
--------------------------------------------------------------------------------
  Total Profit:             $3,150.00
  Average/Opportunity:      $75.00
  Hourly Rate:              $131.25/hour
  Daily Projection:         $3,150.00/day
  Monthly Projection:       $94,500.00/month

📈 PROFIT DISTRIBUTION
--------------------------------------------------------------------------------
  Minimum:                  $52.00
  25th Percentile:          $65.00
  Median:                   $72.50
  75th Percentile:          $85.00
  90th Percentile:          $95.00
  Maximum:                  $125.00

🏦 PROTOCOL BREAKDOWN
--------------------------------------------------------------------------------
  MOONWELL:
    Opportunities:          28
    Total Profit:           $2,100.00
    Average Profit:         $75.00
  SEAMLESS:
    Opportunities:          14
    Total Profit:           $1,050.00
    Average Profit:         $75.00

⏰ HOURLY BREAKDOWN (First 5 and Last 5 hours)
--------------------------------------------------------------------------------
  2024-10-27T15:00:00: 2 opportunities, $150.00
  2024-10-27T16:00:00: 1 opportunities, $75.00
  2024-10-27T17:00:00: 3 opportunities, $225.00
  ...

================================================================================

⚠️  NOTE: These are THEORETICAL projections based on simulation results.
   Actual results will vary based on:
   - Competition from other MEV bots
   - Transaction inclusion rates
   - Gas price volatility
   - Market conditions
================================================================================
```

## Recommended Testing Workflow

### 1. Initial Validation (1-2 hours)

Run dry-run mode for 1-2 hours to verify basic functionality:

```bash
python -m chimera.bot.src.main --dry-run
```

**Check for:**

- Bot connects successfully to RPC providers
- State synchronization is working
- Opportunities are being detected
- Simulations are succeeding
- No errors or crashes

### 2. Extended Testing (24 hours)

Run dry-run mode for a full 24-hour period to collect meaningful data:

```bash
# Start in background (Linux/Mac)
nohup python -m chimera.bot.src.main --dry-run > dry_run.out 2>&1 &

# Or use screen/tmux
screen -S chimera-dryrun
python -m chimera.bot.src.main --dry-run
# Ctrl+A, D to detach
```

**Collect metrics:**

- Opportunities detected per hour
- Simulation success rate
- Theoretical profit projections
- Protocol distribution
- Time-of-day patterns

### 3. Analysis and Decision

After 24 hours, generate the report and analyze:

```bash
python chimera/bot/dry_run_report.py --hours 24 --output report_24h.json
```

**Decision criteria:**

- ✅ **Proceed to testnet** if:

  - Opportunities/hour > 1.0
  - Simulation success rate > 95%
  - Theoretical daily profit > $500
  - No critical errors

- ⚠️ **Investigate further** if:

  - Opportunities/hour < 1.0
  - Simulation success rate < 95%
  - Theoretical daily profit < $500
  - Frequent errors or warnings

- ❌ **Do not proceed** if:
  - No opportunities detected
  - Simulation success rate < 80%
  - Theoretical daily profit < $100
  - Critical errors or crashes

## Key Metrics to Monitor

### Opportunities Detected Per Hour

**Target:** > 1.0 opportunities/hour

This indicates there is sufficient liquidation activity on Base to make the bot viable. Lower values may indicate:

- Low lending protocol activity
- Overly conservative detection thresholds
- Competition already capturing opportunities

### Simulation Success Rate

**Target:** > 95%

This measures how often simulations succeed vs. fail. High failure rates may indicate:

- Incorrect contract addresses
- ABI mismatches
- RPC provider issues
- Logic errors in simulation code

### Theoretical Profit

**Target:** > $500/day (Base Case)

This is the gross profit assuming 100% inclusion rate. Actual profit will be lower due to:

- Competition (estimated 15-30% win rate)
- Failed inclusions (target 60%+ inclusion rate)
- Gas price volatility
- Slippage

**Realistic expectations:**

- Theoretical: $500/day
- With 20% win rate: $100/day
- With 60% inclusion: $60/day
- After costs: $40-50/day net

### Protocol Distribution

Monitor which protocols provide opportunities:

- **Moonwell:** Typically larger TVL, more opportunities
- **Seamless:** Smaller TVL, fewer but potentially higher-profit opportunities

Diversification across protocols reduces risk.

## Troubleshooting

### No Opportunities Detected

**Possible causes:**

1. RPC connection issues
2. State synchronization not working
3. No unhealthy positions on-chain
4. Detection thresholds too conservative

**Debug steps:**

```bash
# Check RPC connectivity
curl -X POST $RPC_PRIMARY_HTTP \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check logs for state engine errors
grep "state_engine" logs/chimera.log | grep "ERROR"

# Lower health factor threshold temporarily (in config.yaml)
# confirmation_blocks: 1  # Reduce from 2
```

### High Simulation Failure Rate

**Possible causes:**

1. Incorrect contract addresses
2. ABI mismatches
3. Insufficient gas estimates
4. RPC provider rate limiting

**Debug steps:**

```bash
# Check simulation errors
grep "Simulation failed" logs/chimera.log

# Verify contract addresses
python -c "
from chimera.bot.src.config import get_config
config = get_config()
print(f'Chimera: {config.execution.chimera_contract_address}')
print(f'Moonwell: {config.protocols[\"moonwell\"].address}')
"

# Test contract calls manually
python -c "
from web3 import Web3
w3 = Web3(Web3.HTTPProvider('$RPC_PRIMARY_HTTP'))
contract = w3.eth.contract(address='$CHIMERA_CONTRACT', abi=[...])
print(contract.functions.treasury().call())
"
```

### Bot Crashes or Hangs

**Possible causes:**

1. Memory leak
2. Deadlock in async code
3. RPC provider timeout
4. Database connection issues

**Debug steps:**

```bash
# Monitor memory usage
watch -n 5 'ps aux | grep python'

# Check for deadlocks in logs
grep "timeout\|deadlock\|hung" logs/chimera.log

# Enable debug logging
# In config.yaml or environment:
export LOG_LEVEL=DEBUG
python -m chimera.bot.src.main --dry-run
```

## Differences from Production Mode

| Feature               | Dry-Run Mode    | Production Mode       |
| --------------------- | --------------- | --------------------- |
| RPC Connection        | ✅ Live mainnet | ✅ Live mainnet       |
| State Monitoring      | ✅ Real-time    | ✅ Real-time          |
| Opportunity Detection | ✅ Full logic   | ✅ Full logic         |
| On-chain Simulation   | ✅ Via eth_call | ✅ Via eth_call       |
| Transaction Signing   | ❌ Skipped      | ✅ With operator key  |
| Bundle Submission     | ❌ Skipped      | ✅ To mempool/builder |
| Gas Costs             | ❌ None         | ✅ Real costs         |
| Capital Risk          | ❌ None         | ✅ Real risk          |
| Safety Limits         | ✅ Enforced     | ✅ Enforced           |
| State Transitions     | ✅ Simulated    | ✅ Real               |
| Database Logging      | ✅ Full logging | ✅ Full logging       |

## Next Steps

After successful dry-run testing:

1. **Review the report** and validate assumptions
2. **Adjust configuration** if needed (thresholds, limits, etc.)
3. **Deploy to testnet** (Base Sepolia) for live transaction testing
4. **Run testnet validation** for 2 weeks minimum
5. **Deploy to mainnet** with conservative limits (Tier 1)

See [DEPLOYMENT.md](DEPLOYMENT.md) for testnet and mainnet deployment procedures.

## FAQ

### Q: How long should I run dry-run mode?

**A:** Minimum 24 hours to capture a full day's activity patterns. Ideally 48-72 hours to account for day-of-week variations.

### Q: Can I run dry-run mode on testnet?

**A:** Yes, but it's less useful since testnet has minimal lending activity. Dry-run on mainnet is safe and provides realistic data.

### Q: Does dry-run mode use my operator private key?

**A:** Yes, the key is loaded for initialization checks (balance verification), but it's never used to sign transactions.

### Q: Will dry-run mode trigger any on-chain state changes?

**A:** No. All simulations use `eth_call` which is read-only. No transactions are broadcast.

### Q: How much does it cost to run dry-run mode?

**A:** Zero on-chain costs. Only RPC provider costs (if using paid tier). Free tier RPC is usually sufficient.

### Q: Can I run multiple dry-run instances simultaneously?

**A:** Yes, but they'll compete for the same RPC rate limits. Use different RPC providers or paid tiers.

### Q: What if the report shows low profitability?

**A:** This could indicate:

- Low market activity (try different time periods)
- High competition (expected on mainnet)
- Conservative thresholds (adjust in config)
- Need for strategy optimization

Remember: Dry-run shows theoretical maximum. Actual results will be 10-30% of theoretical due to competition and inclusion rates.

## Support

For issues or questions:

1. Check logs: `logs/chimera.log`
2. Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
3. Open an issue on GitHub
4. Contact the development team

---

**Last Updated:** October 28, 2024
