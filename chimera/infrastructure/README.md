# Chimera Infrastructure

This directory contains infrastructure configuration and documentation for Project Chimera.

## Overview

The infrastructure supports three deployment modes:

1. **Local Development**: Docker Compose with PostgreSQL, Redis, and optional services
2. **Local Testing**: Includes Anvil for Base mainnet fork testing
3. **Production**: AWS-based deployment (EC2, RDS, ElastiCache)

## Directory Contents

### Configuration Files

- `init.sql` - PostgreSQL database initialization script
- `prometheus.yml` - Prometheus metrics collection configuration
- `prometheus-alerts.yml` - Alerting rules for local development
- `grafana-provisioning/` - Grafana datasources and dashboard provisioning
- `grafana-dashboard.json` - Chimera bot monitoring dashboard

### Documentation

- `README.md` - This file (infrastructure overview)
- `MONITORING.md` - Monitoring stack setup and usage
- `MONITORING_SETUP_SUMMARY.md` - Monitoring implementation summary
- `ANVIL_SETUP.md` - Anvil local fork detailed guide
- `ANVIL_QUICK_REFERENCE.md` - Quick command reference for Anvil

### Test Scripts

- `test-anvil.sh` - Bash script to verify Anvil setup (Linux/Mac)
- `test-anvil.bat` - Batch script to verify Anvil setup (Windows)
- `test-monitoring.py` - Python script to test monitoring integration

## Docker Compose Profiles

The `docker-compose.yml` in the project root uses profiles to organize services:

### Core Services (Always Available)

```bash
docker-compose up -d
```

- `postgres` - PostgreSQL database
- `redis` - Redis cache
- `bot` - Chimera MEV bot application

### Optional Profiles

**Management Tools** (`tools` profile):

```bash
docker-compose --profile tools up -d
```

- `pgadmin` - PostgreSQL web interface (http://localhost:5050)
- `redis-commander` - Redis web interface (http://localhost:8081)

**Monitoring Stack** (`monitoring` profile):

```bash
docker-compose --profile monitoring up -d
```

- `prometheus` - Metrics collection (http://localhost:9090)
- `grafana` - Metrics visualization (http://localhost:3000)

**Testing Stack** (`testing` profile):

```bash
docker-compose --profile testing up -d
```

- `anvil` - Local Base mainnet fork (http://localhost:8545)

### Combined Profiles

Start multiple profiles together:

```bash
# Full development stack
docker-compose --profile tools --profile monitoring --profile testing up -d

# Or using Makefile shortcuts
make start          # Core services only
make tools          # Core + management tools
make monitoring     # Core + monitoring stack
make anvil          # Core + Anvil fork
```

## Quick Start Guides

### Local Development

1. **Start core services**:

   ```bash
   docker-compose up -d
   # Or: make start
   ```

2. **Verify services**:

   ```bash
   docker-compose ps
   # Or: make status
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f
   # Or: make logs
   ```

### Local Testing with Anvil

1. **Start Anvil fork**:

   ```bash
   docker-compose --profile testing up -d anvil
   # Or: make anvil
   ```

2. **Verify Anvil**:

   ```bash
   cast block-number --rpc-url http://localhost:8545
   ```

3. **Run tests**:

   ```bash
   cd chimera/contracts
   forge test --fork-url http://localhost:8545 -vvv
   # Or: make fork-test
   ```

4. **Reset fork state**:
   ```bash
   reset.bat anvil
   # Or: make anvil-reset
   ```

See `ANVIL_SETUP.md` for detailed documentation.

### Monitoring Setup

1. **Start monitoring stack**:

   ```bash
   docker-compose --profile monitoring up -d
   # Or: make monitoring
   ```

2. **Access dashboards**:

   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090

3. **View metrics**:
   - Bot metrics: http://localhost:8000/metrics
   - Bot health: http://localhost:8000/health

See `MONITORING.md` for detailed documentation.

## Service Ports

| Service         | Port | Profile    | URL                   |
| --------------- | ---- | ---------- | --------------------- |
| PostgreSQL      | 5432 | core       | localhost:5432        |
| Redis           | 6379 | core       | localhost:6379        |
| Bot (metrics)   | 8000 | core       | http://localhost:8000 |
| pgAdmin         | 5050 | tools      | http://localhost:5050 |
| Redis Commander | 8081 | tools      | http://localhost:8081 |
| Prometheus      | 9090 | monitoring | http://localhost:9090 |
| Grafana         | 3000 | monitoring | http://localhost:3000 |
| Anvil RPC       | 8545 | testing    | http://localhost:8545 |

## Data Persistence

All services use Docker volumes for data persistence:

- `postgres_data` - PostgreSQL database files
- `redis_data` - Redis persistence files
- `pgadmin_data` - pgAdmin configuration
- `prometheus_data` - Prometheus time-series data
- `grafana_data` - Grafana dashboards and settings
- `anvil_state` - Anvil fork state (auto-saved every 10s)

### Backup Data

```bash
# Using backup script
backup.bat
# Or: make backup
```

### Reset All Data

```bash
# WARNING: This deletes all data!
reset.bat
# Or: make reset
```

### Reset Specific Service

```bash
# Reset only Anvil fork state
reset.bat anvil
# Or: make anvil-reset
```

## Environment Variables

Key environment variables (set in `.env` file):

### RPC Endpoints

- `ALCHEMY_API_KEY` - Alchemy API key
- `ALCHEMY_WSS` - Alchemy WebSocket URL
- `ALCHEMY_HTTPS` - Alchemy HTTPS URL
- `QUICKNODE_HTTPS` - QuickNode HTTPS URL

### Anvil Configuration

- `BASE_RPC_URL` - RPC URL to fork from (default: https://mainnet.base.org)
- `FORK_BLOCK_NUMBER` - Specific block to fork at (optional)

### Database

- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string

### Operator Wallet

- `OPERATOR_PRIVATE_KEY` - Private key for signing transactions
- `OPERATOR_ADDRESS` - Operator wallet address
- `TREASURY_ADDRESS` - Treasury address for profits

See `.env.example` for complete list and documentation.

## Troubleshooting

### Services Won't Start

```bash
# Check Docker is running
docker info

# Check for port conflicts
netstat -an | findstr "5432 6379 8545"

# View service logs
docker-compose logs <service-name>
```

### Database Connection Issues

```bash
# Test PostgreSQL connection
docker-compose exec postgres psql -U chimera_user -d chimera -c "SELECT 1;"

# Test Redis connection
docker-compose exec redis redis-cli ping
```

### Anvil Issues

```bash
# Check Anvil is running
docker ps | grep anvil

# View Anvil logs
docker-compose --profile testing logs anvil

# Test Anvil connection
cast block-number --rpc-url http://localhost:8545

# Reset Anvil state
reset.bat anvil
```

### Monitoring Issues

```bash
# Check Prometheus targets
# Visit: http://localhost:9090/targets

# Check bot metrics endpoint
curl http://localhost:8000/metrics

# Restart monitoring stack
docker-compose --profile monitoring restart
```

## Production Deployment

For production deployment on AWS:

1. **Infrastructure as Code**: Use Terraform/CloudFormation (to be implemented in task 9.6)
2. **Secrets Management**: Use AWS Secrets Manager for private keys
3. **Monitoring**: Use CloudWatch instead of Prometheus/Grafana
4. **High Availability**: Multi-AZ RDS, ElastiCache, and EC2 Auto Scaling

See task 9.6 and 9.7 in the implementation plan for production deployment.

## Resources

### Internal Documentation

- `../README.md` - Project overview
- `../SETUP.md` - Setup instructions
- `.kiro/specs/mev-liquidation-bot/design.md` - System design
- `.kiro/specs/mev-liquidation-bot/tasks.md` - Implementation tasks

### External Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Foundry Book (Anvil)](https://book.getfoundry.sh/anvil/)
- [Base Network Documentation](https://docs.base.org/)

## Support

For issues or questions:

1. Check the troubleshooting section above
2. Review service logs: `docker-compose logs <service>`
3. Check the relevant documentation file in this directory
4. Review the implementation tasks in `.kiro/specs/mev-liquidation-bot/tasks.md`
