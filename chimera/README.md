# Project Chimera - MEV Liquidation Bot

An MEV system designed for profitable liquidation execution on Base L2 lending protocols.

## Project Structure

```
chimera/
├── bot/
│   └── src/
│       ├── __init__.py
│       ├── config.py              # Configuration management
│       ├── types.py                # Core data models
│       ├── database.py             # Database and Redis managers
│       ├── state_engine.py         # Blockchain state synchronization
│       ├── opportunity_detector.py # Liquidation opportunity detection
│       ├── execution_planner.py    # Transaction simulation and bundling
│       ├── safety_controller.py    # Safety limits and state management
│       └── main.py                 # Main orchestrator
├── contracts/
│   ├── src/                        # Solidity contracts
│   ├── test/                       # Contract tests
│   └── script/                     # Deployment scripts
├── scripts/
│   ├── init_database.py            # Database initialization
│   └── migrate_database.sql        # SQL migration script
├── data/                           # Historical data
├── logs/                           # Application logs
├── infrastructure/                 # Terraform/IaC files
├── config.yaml                     # Static configuration
├── .env.example                    # Environment variables template
└── requirements.txt                # Python dependencies
```

## Setup

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

Copy `.env.example` to `.env` and fill in your credentials:

```bash
cp .env.example .env
# Edit .env with your actual values
```

### 3. Update Configuration

Edit `config.yaml` with protocol addresses and parameters for Base L2.

### 4. Initialize Database

```bash
# Create PostgreSQL database and user
psql -U postgres -f scripts/migrate_database.sql

# Initialize tables
python scripts/init_database.py
```

### 5. Verify Setup

```bash
python -c "from bot.src.config import init_config; config = init_config(); print('✓ Configuration loaded')"
```

## Configuration

### Environment Variables (.env)

- `DB_USER`, `DB_PASSWORD`, `DB_HOST`: Database credentials
- `REDIS_HOST`, `REDIS_PASSWORD`: Redis credentials
- `RPC_PRIMARY_HTTP`, `RPC_PRIMARY_WS`: Primary RPC endpoints
- `OPERATOR_ADDRESS`: Bot operator address
- `CHIMERA_CONTRACT`: Deployed contract address

### Static Configuration (config.yaml)

- Protocol addresses (Moonwell, Seamless)
- Oracle addresses (Chainlink, Pyth)
- DEX router addresses (Uniswap V3, Aerodrome)
- Safety limits and thresholds
- Operational parameters

## Dry-Run Mode (Testing Without Risk)

**Test the bot against live Base mainnet without submitting transactions!**

Dry-run mode allows you to validate strategy profitability before deploying capital:

```bash
# Start in dry-run mode
python -m bot.src.maata models and types defined
- ✓ Task 1.4: Database schema and connection handling implemented

### Next Steps

- Task 2: Implement Chimera smart contract
- Task 3: Implement StateEngine module
- Task 4: Implement OpportunityDetector module
- Task 5: Implement ExecutionPlanner module
- Task 6: Implement SafetyController module
- Task 7: Implement main bot orchestrator

## Architecture

The system follows a modular design with clear separation of concerns:

1. **StateEngine**: Maintains real-time blockchain state via WebSocket
2. **OpportunityDetector**: Identifies liquidatable positions
3. **ExecutionPlanner**: Simulates and constructs profitable bundles
4. **SafetyController**: Enforces limits and manages system state
5. **Chimera Contract**: Executes atomic liquidations on-chain

## Safety Features

- Multi-layer safety controls (NORMAL/THROTTLED/HALTED states)
- Mandatory on-chain simulation before execution
- Graduated scaling with validation gates
- Comprehensive audit trail
- Real-time monitoring and alerting

## Monitoring Stack (Optional)

The project includes a complete monitoring stack with Prometheus and Grafana for local development:

### Start with monitoring

```bash
docker-compose --profile monitoring up -d
```

### Access dashboards

- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Bot Metrics**: http://localhost:8000/metrics

### Features

- Real-time metrics visualization
- Performance tracking (inclusion rate, simulation accuracy)
- Profitability monitoring (total profit, daily volume)
- System health monitoring (state, failures, balance)
- Console-based alerting for local development

See [infrastructure/MONITORING.md](infrastructure/MONITORING.md) for detailed documentation.

## License

Proprietary - All rights reserved
