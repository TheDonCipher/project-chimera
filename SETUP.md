# Setup Instructions: Project Chimera

This guide provides step-by-step instructions for setting up the Project Chimera development environment.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Initial Setup](#initial-setup)
3. [Smart Contract Setup](#smart-contract-setup)
4. [Python Bot Setup](#python-bot-setup)
5. [Database Setup](#database-setup)
6. [Configuration](#configuration)
7. [Verification](#verification)
8. [Troubleshooting](#troubleshooting)

## Prerequisites

### Required Software

- **Python 3.11+**: [Download](https://www.python.org/downloads/)
- **Node.js 18+**: [Download](https://nodejs.org/)
- **Git**: [Download](https://git-scm.com/downloads)
- **PostgreSQL 15+**: [Download](https://www.postgresql.org/download/)
- **Redis 7+**: [Download](https://redis.io/download/)

### Optional but Recommended

- **Docker Desktop**: [Download](https://www.docker.com/products/docker-desktop/) (for easy database setup)
- **VS Code**: [Download](https://code.visualstudio.com/) (recommended IDE)
- **AWS CLI**: [Install Guide](https://aws.amazon.com/cli/) (for production deployment)

### RPC Provider Accounts

You'll need API keys from:

1. **Alchemy**: [Sign up](https://www.alchemy.com/)

   - Create a Base Mainnet app
   - Copy your API key and endpoints

2. **QuickNode**: [Sign up](https://www.quicknode.com/)
   - Create a Base endpoint
   - Copy your endpoint URL

## Initial Setup

### 1. Clone the Repository

```bash
git clone <repository-url>
cd chimera
```

### 2. Verify Prerequisites

```bash
# Check Python version (should be 3.11+)
python --version

# Check Node.js version (should be 18+)
node --version

# Check Git
git --version

# Check PostgreSQL (if installed locally)
psql --version

# Check Redis (if installed locally)
redis-cli --version
```

## Smart Contract Setup

### 1. Install Foundry

**On macOS/Linux:**

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

**On Windows:**

```powershell
# Using WSL (Windows Subsystem for Linux)
wsl --install
# Then follow macOS/Linux instructions in WSL
```

### 2. Verify Foundry Installation

```bash
forge --version
cast --version
anvil --version
```

### 3. Install Contract Dependencies

```bash
cd contracts
forge install
```

### 4. Compile Contracts

```bash
forge build
```

Expected output:

```
[⠊] Compiling...
[⠒] Compiling 10 files with 0.8.24
[⠢] Solc 0.8.24 finished in 2.5s
Compiler run successful!
```

### 5. Run Contract Tests

```bash
forge test -vvv
```

All tests should pass.

## Python Bot Setup

### 1. Create Virtual Environment

**On macOS/Linux:**

```bash
cd bot
python3 -m venv venv
source venv/bin/activate
```

**On Windows:**

```powershell
cd bot
python -m venv venv
.\venv\Scripts\activate
```

### 2. Upgrade pip

```bash
python -m pip install --upgrade pip
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

This will install:

- web3.py (Ethereum interactions)
- sqlalchemy (Database ORM)
- redis (Cache)
- pandas (Data analysis)
- pytest (Testing)
- pydantic (Configuration validation)
- And other dependencies

### 4. Verify Installation

```bash
python -c "import web3; print(f'web3.py version: {web3.__version__}')"
python -c "import sqlalchemy; print(f'SQLAlchemy version: {sqlalchemy.__version__}')"
```

## Database Setup

### Option 1: Using Docker (Recommended)

#### 1. Install Docker Desktop

Download and install from [docker.com](https://www.docker.com/products/docker-desktop/)

#### 2. Create docker-compose.yml

Create a file named `docker-compose.yml` in the project root:

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: chimera-postgres
    environment:
      POSTGRES_DB: chimera
      POSTGRES_USER: chimera_user
      POSTGRES_PASSWORD: chimera_password
    ports:
      - '5432:5432'
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ['CMD-SHELL', 'pg_isready -U chimera_user -d chimera']
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: chimera-redis
    ports:
      - '6379:6379'
    volumes:
      - redis_data:/data
    healthcheck:
      test: ['CMD', 'redis-cli', 'ping']
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  redis_data:
```

#### 3. Start Services

```bash
docker-compose up -d
```

#### 4. Verify Services

```bash
# Check containers are running
docker-compose ps

# Test PostgreSQL connection
docker exec -it chimera-postgres psql -U chimera_user -d chimera -c "SELECT version();"

# Test Redis connection
docker exec -it chimera-redis redis-cli ping
```

Expected output: `PONG`

### Option 2: Local Installation

#### PostgreSQL

**On macOS:**

```bash
brew install postgresql@15
brew services start postgresql@15
createdb chimera
```

**On Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install postgresql-15
sudo systemctl start postgresql
sudo -u postgres createdb chimera
sudo -u postgres createuser chimera_user
```

**On Windows:**

1. Download installer from [postgresql.org](https://www.postgresql.org/download/windows/)
2. Run installer and follow prompts
3. Use pgAdmin to create database `chimera`

#### Redis

**On macOS:**

```bash
brew install redis
brew services start redis
```

**On Ubuntu/Debian:**

```bash
sudo apt update
sudo apt install redis-server
sudo systemctl start redis-server
```

**On Windows:**

1. Download from [redis.io](https://redis.io/download/)
2. Extract and run `redis-server.exe`

## Configuration

### 1. Create Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

### 2. Edit .env File

Open `.env` in your editor and fill in the values:

```bash
# RPC Providers
ALCHEMY_API_KEY=your_alchemy_api_key_here
ALCHEMY_WSS=wss://base-mainnet.g.alchemy.com/v2/YOUR_KEY_HERE
ALCHEMY_HTTPS=https://base-mainnet.g.alchemy.com/v2/YOUR_KEY_HERE
QUICKNODE_HTTPS=https://your-endpoint.base.quiknode.pro/YOUR_KEY_HERE

# RPC Providers (Testnet)
ALCHEMY_WSS_TESTNET=wss://base-sepolia.g.alchemy.com/v2/YOUR_KEY_HERE
ALCHEMY_HTTPS_TESTNET=https://base-sepolia.g.alchemy.com/v2/YOUR_KEY_HERE

# Database
DATABASE_URL=postgresql://chimera_user:chimera_password@localhost:5432/chimera
REDIS_URL=redis://localhost:6379/0

# Operator Wallet (Development only - use AWS Secrets Manager in production)
# Generate a new wallet: cast wallet new
OPERATOR_PRIVATE_KEY=0x0000000000000000000000000000000000000000000000000000000000000000

# Environment
ENVIRONMENT=development  # development, testnet, mainnet

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 3. Create Configuration File

Copy the example configuration:

```bash
cp config.yaml.example config.yaml
```

Edit `config.yaml` with protocol addresses and settings. For development, you can use the defaults.

### 4. Generate Operator Wallet (Development)

```bash
# Generate new wallet
cast wallet new

# Output will show:
# Successfully created new keypair.
# Address:     0x...
# Private key: 0x...
```

Copy the private key to your `.env` file.

**⚠️ WARNING**: Never commit real private keys to git. The `.env` file is in `.gitignore`.

## Database Initialization

### 1. Run Migrations

```bash
cd bot
python src/migrations/init_db.py
```

Expected output:

```
Creating database schema...
✓ Created table: executions
✓ Created table: state_divergences
✓ Created table: performance_metrics
✓ Created table: system_events
✓ Created indexes
Database initialization complete!
```

### 2. Verify Tables

```bash
# Using Docker
docker exec -it chimera-postgres psql -U chimera_user -d chimera -c "\dt"

# Using local PostgreSQL
psql -U chimera_user -d chimera -c "\dt"
```

You should see tables: `executions`, `state_divergences`, `performance_metrics`, `system_events`

## Verification

### 1. Run Smart Contract Tests

```bash
cd contracts
forge test -vvv
```

All tests should pass.

### 2. Run Python Tests

```bash
cd bot
pytest tests/ -v
```

All tests should pass.

### 3. Test RPC Connections

```bash
cd bot
python -c "
from web3 import Web3
import os
from dotenv import load_dotenv

load_dotenv()

# Test Alchemy connection
w3 = Web3(Web3.HTTPProvider(os.getenv('ALCHEMY_HTTPS')))
print(f'Connected to Base: {w3.is_connected()}')
print(f'Latest block: {w3.eth.block_number}')
print(f'Chain ID: {w3.eth.chain_id}')
"
```

Expected output:

```
Connected to Base: True
Latest block: 12345678
Chain ID: 8453
```

### 4. Test Database Connection

```bash
cd bot
python -c "
from sqlalchemy import create_engine
import os
from dotenv import load_dotenv

load_dotenv()

engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    result = conn.execute('SELECT version();')
    print(f'PostgreSQL version: {result.fetchone()[0]}')
"
```

### 5. Test Redis Connection

```bash
cd bot
python -c "
import redis
import os
from dotenv import load_dotenv

load_dotenv()

r = redis.from_url(os.getenv('REDIS_URL'))
r.set('test_key', 'test_value')
value = r.get('test_key')
print(f'Redis test: {value.decode()}')
r.delete('test_key')
"
```

Expected output: `Redis test: test_value`

## Running the Bot

### Development Mode

```bash
cd bot
export ENVIRONMENT=development  # On Windows: set ENVIRONMENT=development
python src/main.py
```

The bot will start in development mode with verbose logging.

### Testnet Mode

```bash
cd bot
export ENVIRONMENT=testnet  # On Windows: set ENVIRONMENT=testnet
python src/main.py
```

## Troubleshooting

### Issue: "forge: command not found"

**Solution**: Foundry not installed or not in PATH

```bash
# Reinstall Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.foundry/bin:$PATH"
```

### Issue: "ModuleNotFoundError: No module named 'web3'"

**Solution**: Virtual environment not activated or dependencies not installed

```bash
# Activate virtual environment
source venv/bin/activate  # On Windows: .\venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Issue: "psycopg2.OperationalError: could not connect to server"

**Solution**: PostgreSQL not running or wrong connection string

```bash
# Check if PostgreSQL is running
docker-compose ps  # If using Docker
# OR
sudo systemctl status postgresql  # If using local install

# Verify connection string in .env matches your setup
```

### Issue: "redis.exceptions.ConnectionError"

**Solution**: Redis not running

```bash
# Check if Redis is running
docker-compose ps  # If using Docker
# OR
redis-cli ping  # Should return PONG
```

### Issue: "Web3 connection failed"

**Solution**: Invalid RPC endpoint or API key

```bash
# Test RPC endpoint manually
curl -X POST $ALCHEMY_HTTPS \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

# Should return: {"jsonrpc":"2.0","id":1,"result":"0x..."}
```

### Issue: "Permission denied" on database

**Solution**: Database user doesn't have permissions

```bash
# Grant permissions (PostgreSQL)
psql -U postgres -c "GRANT ALL PRIVILEGES ON DATABASE chimera TO chimera_user;"
```

## Next Steps

After successful setup:

1. **Read the documentation**:

   - `README.md` - Project overview
   - `AGENTS.md` - Development guide
   - `.kiro/specs/mev-liquidation-bot/requirements.md` - Requirements
   - `.kiro/specs/mev-liquidation-bot/design.md` - Design
   - `.kiro/specs/mev-liquidation-bot/tasks.md` - Implementation tasks

2. **Start implementing**:

   - Open `.kiro/specs/mev-liquidation-bot/tasks.md`
   - Start with Task 1.1: Create directory structure
   - Follow the task list sequentially

3. **Run tests frequently**:

   ```bash
   # Smart contract tests
   cd contracts && forge test -vvv

   # Python tests
   cd bot && pytest tests/ -v --cov=src
   ```

4. **Commit regularly**:
   ```bash
   git add .
   git commit -m "Implement task X.Y: Description"
   git push
   ```

## Getting Help

If you encounter issues not covered here:

1. Check the logs in `logs/` directory
2. Review error messages carefully
3. Search for similar issues in documentation
4. Ask for help with specific error messages and context

---

**Setup complete!** You're ready to start implementing Project Chimera. 🚀
