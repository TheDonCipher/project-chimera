# Dry-Run Mode Quick Start

Get started with dry-run testing in 5 minutes.

## Prerequisites

- Python 3.11+ installed
- Docker and Docker Compose installed
- RPC endpoints configured (Alchemy or QuickNode)
- Environment variables set in `.env`

## Quick Start

### 1. Start Infrastructure

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Verify services are running
docker-compose ps
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and set:
# - RPC_PRIMARY_HTTP (your Alchemy/QuickNode HTTP endpoint)
# - RPC_PRIMARY_WS (your WebSocket endpoint)
# - OPERATOR_ADDRESS (any valid address, won't be used for transactions)
# - OPERATOR_PRIVATE_KEY (any valid key, won't be used for transactions)
# - DB_USER, DB_PASSWORD (from docker-compose.yml)

# Example:
nano .env
```

### 3. Install Dependencies

```bash
cd chimera
pip install -r requirements.txt
```

### 4. Run Dry-Run Mode

```bash
# Start the bot in dry-run mode
python -m bot.src.main --dry-run
```

You should see output like:

```
================================================================================
DRY-RUN MODE ENABLED
Opportunities will be detected and simulated, but NO transactions will be submitted
================================================================================

{"timestamp": "2024-10-28T15:30:00.000Z", "level": "INFO", "module": "chimera", "event": "chimera_starting", ...}
{"timestamp": "2024-10-28T15:30:01.000Z", "level": "INFO", "module": "state_engine", "event": "Starting StateEngine", ...}
{"timestamp": "2024-10-28T15:30:02.000Z", "level": "INFO", "module": "opportunity_detector", "event": "Starting OpportunityDetector", ...}
```

### 5. Monitor in Real-Time

Open a new terminal and tail the logs:

```bash
# Watch for dry-run events
tail -f logs/chimera.log | grep "DRY-RUN"

# Or use the logs script
./logs.sh
```

### 6. Let It Run

Leave the bot running for at least 24 hours to collect meaningful data.

### 7. Generate Report

After 24 hours, stop the bot (Ctrl+C) and generate a report:

```bash
python bot/dry_run_report.py --hours 24
```

## Expected Results

After 24 hours, you should see:

- **Opportunities detected:** 20-50+ (depends on market conditions)
- **Simulation success rate:** >95%
- **Theoretical profit:** $500-2000+ (highly variable)

## Troubleshooting

### No opportunities detected

```bash
# Check RPC connection
curl -X POST $RPC_PRIMARY_HTTP \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Check state engine logs
grep "state_engine" logs/chimera.log | tail -20
```

### Bot crashes immediately

```bash
# Check database connection
docker-compose logs postgres

# Check configuration
python -c "from bot.src.config import get_config; print(get_config())"
```

### High simulation failure rate

```bash
# Check simulation errors
grep "Simulation failed" logs/chimera.log | head -10

# Verify contract addresses in config.yaml
```

## Next Steps

1. ✅ Review the dry-run report
2. ✅ Validate opportunity detection is working
3. ✅ Check simulation success rate >95%
4. ✅ Analyze theoretical profitability
5. ➡️ Proceed to testnet deployment (see [DEPLOYMENT.md](DEPLOYMENT.md))

## Full Documentation

For detailed information, see [DRY_RUN_MODE.md](DRY_RUN_MODE.md)

---

**Need Help?**

- Check logs: `logs/chimera.log`
- Review [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
- Open an issue on GitHub
