# Chimera Backtest Analysis

This directory contains scripts for historical data collection and backtesting to validate the MEV liquidation bot strategy before deployment.

## Overview

The backtest analysis consists of three main components:

1. **Historical Data Collection** - Collects liquidation events and gas prices from Base mainnet
2. **Backtest Engine** - Simulates bot behavior and calculates profitability metrics
3. **Sensitivity Analysis** - Generates scenario analysis and GO/STOP/PIVOT recommendation

## Prerequisites

- Python 3.9+
- Web3.py installed (`pip install web3`)
- Valid Alchemy API key for Base mainnet
- Environment variable `RPC_PRIMARY_HTTP` set

## Usage

### Step 1: Collect Historical Data

Collects last 30 days (~1.3M blocks) of liquidation events from Moonwell and Seamless Protocol on Base mainnet.

```bash
# Set your Alchemy API key
export RPC_PRIMARY_HTTP='https://base-mainnet.g.alchemy.com/v2/YOUR_KEY'

# Run data collection (takes 30-60 minutes)
cd chimera
python scripts/collect_historical_data.py
```

**Output:**

- `data/historical_liquidations.csv` - All liquidation events
- `data/historical_gas_prices.csv` - Gas price samples

### Step 2: Run Backtest Engine

Analyzes historical liquidations to determine if bot would have been profitable.

```bash
python scripts/backtest_engine.py
```

**Output:**

- `data/backtest_results.csv` - Detailed results for each liquidation
- Console summary with win rate, profitability, and ROI projections

### Step 3: Generate Sensitivity Analysis

Creates scenario analysis with varying parameters.

```bash
python scripts/sensitivity_analysis.py
```

**Output:**

- `data/sensitivity_analysis.txt` - Comprehensive report with recommendation
- Console output with scenario comparison table

### All-in-One: Run Complete Analysis

Run all steps together (assumes data already collected):

```bash
python scripts/run_backtest_analysis.py
```

## Backtest Methodology

### Bot Parameters

- **Detection Latency**: 500ms (time to detect opportunity)
- **Build Latency**: 200ms (time to construct and submit transaction)
- **Total Latency**: 700ms

### Cost Model

1. **Gas Costs**: L2 execution + L1 data posting (~40% overhead)
2. **Builder Bribe**: 15% of gross profit (baseline)
3. **Flash Loan Premium**: 0.09% of debt amount
4. **DEX Slippage**: 1% of collateral value

### Profit Estimation

- **Liquidation Bonus**: 5-10% of collateral value (protocol-specific)
- **Arbitrage Opportunity**: 2-5% of collateral value
- **Conservative Estimate**: 8% of collateral value

### Win Determination

Bot wins if: `bot_latency < winner_latency`

Where `winner_latency` is estimated from transaction index in block:

- First tx in block: ~200ms latency
- Each subsequent tx: +50ms

## Sensitivity Analysis Scenarios

### Optimistic

- Win rate: 30%
- Avg gross profit: $200
- Bribe: 12%
- Opportunities: +20%

### Base Case

- Win rate: From backtest
- Avg gross profit: From backtest
- Bribe: 15%
- Opportunities: From backtest

### Pessimistic

- Win rate: -30%
- Avg gross profit: -20%
- Bribe: 20%
- Opportunities: -20%

### Worst Case

- Win rate: -50%
- Avg gross profit: -40%
- Bribe: 25%
- Opportunities: -40%

## Decision Criteria

### GO

- Base Case ROI > 100%
- Pessimistic ROI > 50%
- **Action**: Proceed to testnet validation

### PIVOT

- Base Case ROI 50-100%
- OR Pessimistic ROI 0-50%
- **Action**: Optimize strategy before deployment

### STOP

- Base Case ROI < 50%
- OR Pessimistic ROI < 0%
- **Action**: Strategy not viable, consider alternatives

## Expected Results

Based on Base L2 liquidation activity:

- **Liquidations per day**: 5-15 (varies by market conditions)
- **Win rate**: 15-25% (Python latency disadvantage)
- **Average profit per win**: $80-150
- **Monthly profit**: $500-2,000 (Base Case)
- **Annual ROI**: 50-200% (on $2,000 capital)

## Limitations

1. **Simplified profit model**: Actual profits depend on real-time oracle prices and DEX liquidity
2. **Latency estimation**: Winner latency estimated from tx_index, not actual timing data
3. **Competition dynamics**: Assumes static competition; may change over time
4. **Protocol coverage**: Only Moonwell and Seamless; other protocols may exist
5. **Market conditions**: Historical data may not reflect future opportunities

## Next Steps After Backtest

If recommendation is **GO**:

1. Complete smart contract audit
2. Deploy to Base Sepolia testnet
3. Execute 50+ test liquidations
4. Validate metrics:
   - Inclusion rate > 60%
   - Simulation accuracy > 90%
   - Uptime > 95%
5. Proceed to mainnet with Tier 1 limits ($500 single / $2,500 daily)

## Troubleshooting

### "RPC connection failed"

- Verify `RPC_PRIMARY_HTTP` environment variable is set
- Check Alchemy API key is valid and has Base mainnet access
- Ensure sufficient API credits

### "No liquidations found"

- Verify protocol addresses in `collect_historical_data.py` are correct
- Check block range covers period with liquidation activity
- Try reducing batch size if RPC rate limits hit

### "Insufficient data"

- Collect longer time period (increase days parameter)
- Verify CSV files are not empty
- Check for data collection errors in logs

## Files Generated

```
chimera/data/
├── historical_liquidations.csv    # Raw liquidation events
├── historical_gas_prices.csv      # Gas price samples
├── backtest_results.csv           # Detailed backtest results
└── sensitivity_analysis.txt       # Scenario analysis report
```

## Requirements

See `chimera/requirements.txt` for Python dependencies.

Key dependencies:

- `web3>=6.0.0` - Ethereum interaction
- `eth-abi>=4.0.0` - ABI encoding/decoding
- `pydantic>=2.0.0` - Data validation

## Support

For issues or questions:

1. Check logs in `chimera/logs/`
2. Review requirements document: `.kiro/specs/mev-liquidation-bot/requirements.md`
3. Review design document: `.kiro/specs/mev-liquidation-bot/design.md`
