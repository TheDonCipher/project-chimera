# Project Chimera: MEV Liquidation Bot

**Version:** 1.0  
**Target Chain:** Base L2 (Optimism Stack)  
**Status:** Phase 1 - Local Development

## Overview

Project Chimera is a sophisticated MEV (Maximal Extractable Value) system designed to execute profitable liquidations on Base L2 lending protocols. The system consists of an off-chain Python agent and an on-chain Solidity smart contract that work together to identify, simulate, and execute atomic liquidation transactions.

### Key Features

- **Real-Time State Synchronization**: Block-level reconciliation with multi-RPC redundancy
- **Simulation-First Execution**: Never execute without on-chain validation
- **Base L2 Optimized**: Accounts for L1 data posting costs (30-50% of total gas)
- **Dynamic Bribe Optimization**: Automatically adjusts builder bribes based on inclusion performance
- **Multi-Layer Safety Controls**: Three-state machine (NORMAL/THROTTLED/HALTED) with automatic transitions
- **Comprehensive Observability**: Complete audit trail and real-time metrics

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   Off-Chain Agent (Python)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │
│  │ StateEngine  │─▶│ Opportunity  │─▶│  Execution   │    │
│  │              │  │  Detector    │  │   Planner    │    │
│  └──────────────┘  └──────────────┘  └──────────────┘    │
│                           │                                │
│                  ┌────────▼────────┐                       │
│                  │ SafetyController│                       │
│                  └────────┬────────┘                       │
└───────────────────────────┼─────────────────────────────────┘
                            │
                  ┌─────────▼──────────┐
                  │   Base L2 Network  │
                  │  ┌──────────────┐  │
                  │  │ Chimera.sol  │  │
                  │  └──────────────┘  │
                  └────────────────────┘
```

## Project Structure

```
chimera/
├── contracts/              # Solidity smart contracts
│   ├── src/               # Contract source files
│   │   └── Chimera.sol    # Main liquidation contract
│   ├── test/              # Foundry tests
│   └── script/            # Deployment scripts
├── bot/                   # Python MEV bot
│   ├── src/               # Source code
│   │   ├── state_engine.py
│   │   ├── opportunity_detector.py
│   │   ├── execution_planner.py
│   │   ├── safety_controller.py
│   │   ├── config.py
│   │   ├── types.py
│   │   └── main.py
│   ├── tests/             # Pytest test suite
│   └── requirements.txt   # Python dependencies
├── data/                  # Historical data for backtesting
├── logs/                  # Runtime logs
├── scripts/               # Utility scripts
│   ├── collect_data.py   # Historical data collection
│   └── backtest.py       # Backtesting engine
└── infrastructure/        # AWS deployment
    └── terraform/         # Infrastructure as code
```

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- Foundry (for smart contract development)
- PostgreSQL 15+
- Redis 7+
- AWS CLI (for production deployment)

### Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd chimera
```

2. **Install Foundry**

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

3. **Install Python dependencies**

```bash
cd bot
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

4. **Set up environment variables**

```bash
cp .env.example .env
# Edit .env with your RPC keys and configuration
```

5. **Set up local database**

```bash
# Using Docker
docker-compose up -d postgres redis
```

6. **Run database migrations**

```bash
python bot/src/migrations/init_db.py
```

### Development

**Run smart contract tests:**

```bash
cd contracts
forge test -vvv
forge coverage
```

**Run Python tests:**

```bash
cd bot
pytest tests/ -v --cov=src
```

**Run the bot (testnet):**

```bash
export ENVIRONMENT=testnet
python bot/src/main.py
```

## Development Phases

### Phase 1: Local Development (Weeks 1-12)

**Goal:** Prove strategy profitability via historical backtest

**Key Deliverables:**

- Complete codebase with >80% test coverage
- Smart contract with >95% test coverage
- Backtest report showing Base Case ROI >100%
- Sensitivity analysis

**Exit Criteria:**

- Base Case annual ROI >100%
- Win rate >15% in latency analysis
- All tests passing

### Phase 2: Testnet Validation (Weeks 13-20)

**Goal:** Validate infrastructure and submission paths

**Key Deliverables:**

- Contract deployed on Base Sepolia
- 50+ successful liquidations executed
- Performance analysis report
- Professional smart contract audit completed

**Exit Criteria:**

- Inclusion rate >60% sustained
- Simulation accuracy >90%
- Uptime >95%

### Phase 3: Mainnet Deployment (Week 21+)

**Goal:** Execute profitably at small scale, scale gradually

**Graduated Scaling:**

- **Tier 1**: $500 single / $2,500 daily (8+ weeks)
- **Tier 2**: $1,000 single / $5,000 daily (12+ weeks)
- **Tier 3**: $2,500 single / $12,500 daily (12+ weeks)
- **Tier 4**: $5,000 single / $25,000 daily (ongoing)

## Configuration

### Environment Variables (.env)

```bash
# RPC Providers
ALCHEMY_API_KEY=your_key
ALCHEMY_WSS=wss://base-mainnet.g.alchemy.com/v2/YOUR-KEY
ALCHEMY_HTTPS=https://base-mainnet.g.alchemy.com/v2/YOUR-KEY
QUICKNODE_HTTPS=https://your-endpoint.base.quiknode.pro/

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/chimera
REDIS_URL=redis://localhost:6379/0

# Operator (Development only - use AWS Secrets Manager in production)
OPERATOR_PRIVATE_KEY=0x...

# Environment
ENVIRONMENT=development  # development, testnet, mainnet
```

### Configuration File (config.yaml)

See `config.yaml.example` for complete configuration options including:

- Protocol addresses (Moonwell, Seamless)
- Oracle addresses (Chainlink, Pyth)
- DEX router addresses (Uniswap V3, Aerodrome)
- Operational limits and thresholds

## Testing

### Unit Tests

```bash
# Python tests
cd bot
pytest tests/ -v --cov=src --cov-report=html

# Smart contract tests
cd contracts
forge test -vvv
```

### Integration Tests

```bash
# Fork testing against Base mainnet
cd contracts
forge test --fork-url $ALCHEMY_HTTPS -vvv
```

### Backtesting

```bash
# Collect historical data
python scripts/collect_data.py --days 30

# Run backtest
python scripts/backtest.py --data data/historical_liquidations.csv
```

## Monitoring

### Key Metrics

**System Health:**

- Current state (NORMAL/THROTTLED/HALTED)
- Uptime percentage
- Operator balance
- Last execution timestamp

**Performance (24h):**

- Opportunities detected
- Bundles submitted
- Successful inclusions
- Win rate / Inclusion rate
- Net profit

**Risk Metrics:**

- Consecutive failures
- Daily volume vs limit
- State divergence events

### Alerts

- **CRITICAL**: HALTED state, security incidents, low operator balance
- **HIGH**: THROTTLED state, low inclusion rate, consecutive failures
- **MEDIUM**: Approaching limits, key rotation due
- **LOW**: Daily summaries, weekly reports

## Security

### Critical Security Practices

1. **Never execute without simulation** - REQ-EP-002 is non-negotiable
2. **Professional audit required** - Budget $15-30K before mainnet
3. **Key management** - Use AWS Secrets Manager, 90-day rotation
4. **Graduated scaling** - Never skip validation gates
5. **Reserve fund** - Maintain 30% operational buffer

### Threat Model

- Smart contract vulnerabilities → Mitigated by audit, ReentrancyGuard, Ownable2Step
- State divergence → Mitigated by block-level reconciliation
- Sequencer downtime → Mitigated by automatic HALT
- Oracle manipulation → Mitigated by multi-oracle sanity checks
- Key compromise → Mitigated by Secrets Manager, minimal balance

## Documentation

- **Requirements**: `.kiro/specs/mev-liquidation-bot/requirements.md`
- **Design**: `.kiro/specs/mev-liquidation-bot/design.md`
- **Tasks**: `.kiro/specs/mev-liquidation-bot/tasks.md`
- **Development Guide**: `AGENTS.md`
- **Setup Instructions**: `SETUP.md`

## Contributing

This is a private MEV project. For internal development:

1. Follow the task list in `.kiro/specs/mev-liquidation-bot/tasks.md`
2. Maintain >80% test coverage for all new code
3. Update documentation as you implement features
4. Never commit private keys or sensitive data

## License

Proprietary - All Rights Reserved

## Disclaimer

This software is for educational and research purposes. MEV activities may be subject to legal and regulatory restrictions in your jurisdiction. Consult legal counsel before deployment. The authors assume no liability for financial losses or legal consequences.

---

**Status**: Phase 1 - Local Development  
**Last Updated**: October 2025  
**Next Milestone**: Complete backtest with ROI >100%
