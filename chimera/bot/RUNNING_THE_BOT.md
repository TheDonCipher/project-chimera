# Running the Chimera MEV Liquidation Bot

## Quick Start Guide

### Prerequisites

1. **Python 3.9+** installed
2. **PostgreSQL** database running
3. **Redis** server running (optional, will use in-memory fallback)
4. **Base RPC endpoints** (Alchemy, QuickNode, or similar)
5. **Operator wallet** with at least 0.1 ETH on Base

### Step 1: Install Dependencies

```bash
cd chimera/bot
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in the `chimera/` directory:

```bash
# Operator wallet
OPERATOR_PRIVATE_KEY=0x1234567890abcdef...
OPERATOR_ADDRESS=0xYourOperatorAddress...

# Database
DB_USER=chimera
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5432

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=your_redis_password  # Optional

# RPC Endpoints
RPC_PRIMARY_HTTP=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY
RPC_PRIMARY_WS=wss://base-mainnet.g.alchemy.com/v2/YOUR_KEY
RPC_BACKUP_HTTP=https://base.quicknode.pro/YOUR_KEY
RPC_BACKUP_WS=wss://base.quicknode.pro/YOUR_KEY

# Chimera Contract
CHIMERA_CONTRACT=0xYourChimeraContractAddress...

# Monitoring (optional)
ALERT_EMAIL=your-email@example.com
```

### Step 3: Configure config.yaml

Edit `chimera/config.yaml` to set:

- Protocol addresses (Moonwell, Seamless)
- Oracle addresses (Chainlink price feeds)
- DEX router addresses (Uniswap V3, Aerodrome)
- Safety limits (start with Tier 1: $500 single, $2500 daily)
- Flash loan addresses (Aave V3 pool)

### Step 4: Initialize Database

```bash
cd chimera/bot/src
python -c "from bot.src.database import init_database; from bot.src.config import get_config; init_database(get_config().database)"
```

This will create all required tables:

- `executions`
- `state_divergences`
- `performance_metrics`
- `system_events`

### Step 5: Run the Bot

```bash
cd chimera
python -m bot.src.main
```

Or with environment file:

```bash
cd chimera
export $(cat .env | xargs) && python -m bot.src.main
```

### Step 6: Monitor the Bot

Watch the logs in `chimera/logs/`:

```bash
tail -f chimera/logs/chimera.log
```

## System States

The bot operates in three states:

### NORMAL

- Full operation (100% execution rate)
- All opportunities are evaluated and executed if profitable
- Default state on startup

### THROTTLED

- Reduced operation (50% execution rate)
- Randomly skips 50% of opportunities
- Triggered when:
  - Inclusion rate 50-60%
  - Simulation accuracy 85-90%

### HALTED

- No execution (manual intervention required)
- All opportunities are skipped
- Triggered when:
  - Inclusion rate < 50%
  - Simulation accuracy < 85%
  - Consecutive failures ≥ 3
  - Critical errors (RPC failure, state divergence > 10 BPS)

## Manual Intervention

### Resume from HALTED State

The bot requires manual operator intervention to resume from HALTED state:

```python
from bot.src.safety_controller import SafetyController
from bot.src.database import get_db_manager
from bot.src.config import get_config

config = get_config()
db_manager = get_db_manager()
safety_controller = SafetyController(config, db_manager)

# Resume operation
safety_controller.manual_resume(
    operator="operator_name",
    reason="Issue resolved, resuming operations"
)
```

### Check System Status

```python
from bot.src.safety_controller import SafetyController
from bot.src.database import get_db_manager
from bot.src.config import get_config

config = get_config()
db_manager = get_db_manager()
safety_controller = SafetyController(config, db_manager)

# Get current status
status = safety_controller.get_status()
print(f"State: {status['state']}")
print(f"Daily Volume: ${status['daily_volume_usd']:.2f} / ${status['daily_limit_usd']:.2f}")
print(f"Consecutive Failures: {status['consecutive_failures']}")
```

## Monitoring

### Metrics

The bot exports metrics every 60 seconds:

- **System State**: NORMAL, THROTTLED, or HALTED
- **Opportunities Detected**: Total count
- **Bundles Submitted**: Total count
- **Inclusion Rate**: Percentage of submitted bundles included
- **Simulation Accuracy**: Actual profit / Simulated profit
- **Daily Volume**: Current daily volume in USD
- **Consecutive Failures**: Current count
- **Positions Cached**: Number of positions in cache
- **Current Block**: Latest block processed

### Alerts

The bot sends alerts for:

**CRITICAL** (Phone + SMS):

- System entered HALTED state
- Operator balance < 0.1 ETH
- Security incidents

**HIGH** (SMS):

- System entered THROTTLED state
- Inclusion rate < 50%
- Consecutive failures = 2

**MEDIUM** (Email):

- Daily volume > 80% of limit
- Key rotation due

**LOW** (Email):

- Daily summaries

## Troubleshooting

### Bot Won't Start

1. Check environment variables are set:

   ```bash
   echo $OPERATOR_PRIVATE_KEY
   echo $DB_USER
   ```

2. Check database is running:

   ```bash
   psql -h localhost -U chimera -d chimera -c "SELECT 1"
   ```

3. Check RPC endpoints are accessible:
   ```bash
   curl -X POST $RPC_PRIMARY_HTTP \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
   ```

### Bot Enters HALTED State

1. Check logs for error messages:

   ```bash
   grep "CRITICAL" chimera/logs/chimera.log
   ```

2. Check system events in database:

   ```sql
   SELECT * FROM system_events
   WHERE severity = 'CRITICAL'
   ORDER BY timestamp DESC
   LIMIT 10;
   ```

3. Check performance metrics:

   ```sql
   SELECT * FROM performance_metrics
   ORDER BY timestamp DESC
   LIMIT 1;
   ```

4. Resolve the issue and manually resume

### No Opportunities Detected

1. Check StateEngine is running:

   ```bash
   grep "StateEngine" chimera/logs/chimera.log | tail -20
   ```

2. Check positions are cached:

   ```bash
   redis-cli KEYS "position:*"
   ```

3. Check lending protocols have active positions:
   - Visit Moonwell/Seamless Protocol dashboards
   - Verify there are borrowers with positions

### Bundles Not Being Included

1. Check inclusion rate:

   ```sql
   SELECT inclusion_rate FROM performance_metrics
   ORDER BY timestamp DESC LIMIT 1;
   ```

2. Check bribe percentage:

   - Review ExecutionPlanner logs
   - May need to increase baseline bribe

3. Check gas prices:
   - Ensure max_fee_per_gas is competitive
   - Check Base network congestion

## Performance Tuning

### Increase Scan Frequency

Edit `config.yaml`:

```yaml
scan_interval_seconds: 3 # Default: 5
```

### Adjust Safety Limits

Edit `config.yaml`:

```yaml
safety:
  max_single_execution_usd: 1000 # Increase from $500
  max_daily_volume_usd: 5000 # Increase from $2500
  min_profit_usd: 30 # Decrease from $50
```

### Optimize Bribe Strategy

Edit `config.yaml`:

```yaml
execution:
  baseline_bribe_percent: 20 # Increase from 15%
  max_bribe_percent: 50 # Increase from 40%
```

## Graceful Shutdown

To stop the bot gracefully:

```bash
# Send SIGINT (Ctrl+C)
Ctrl+C

# Or send SIGTERM
kill -TERM $(pgrep -f "python -m bot.src.main")
```

The bot will:

1. Stop accepting new opportunities
2. Stop StateEngine
3. Stop OpportunityDetector
4. Close database connections
5. Exit cleanly

## Production Deployment

For production deployment:

1. **Use AWS Secrets Manager** for operator key
2. **Enable CloudWatch** for metrics and logs
3. **Set up PagerDuty** for critical alerts
4. **Use Multi-AZ RDS** for database
5. **Use ElastiCache** for Redis
6. **Deploy on EC2** c7g.xlarge instance
7. **Set up monitoring dashboard**
8. **Configure log retention** (3 years)
9. **Enable automated backups**
10. **Set up key rotation** (90 days)

## Support

For issues or questions:

- Check logs in `chimera/logs/`
- Review implementation docs in `chimera/bot/`
- Check database for execution history
- Review system events for state transitions

## Safety Reminders

⚠️ **IMPORTANT**:

- Start with Tier 1 limits ($500 single, $2500 daily)
- Monitor closely for first 100 executions
- Never skip simulation (CRITICAL)
- Always maintain minimum 0.1 ETH balance
- Review all HALTED state triggers
- Keep operator key secure
- Rotate keys every 90 days
- Monitor for unusual activity
- Have emergency pause procedure ready

## Next Steps

After successful deployment:

1. Monitor for 2 weeks on testnet
2. Execute 50+ liquidations successfully
3. Achieve >60% inclusion rate
4. Achieve >90% simulation accuracy
5. Complete security audit
6. Graduate to mainnet with Tier 1 limits
7. Scale gradually through tiers based on performance
