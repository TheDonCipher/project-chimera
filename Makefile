# Chimera MEV Bot - Makefile
# Common commands for development workflow

.PHONY: help start stop restart logs reset backup test build clean status shell db-shell redis-shell tools monitoring anvil anvil-reset anvil-logs fork-test

# Default target
help:
	@echo ========================================
	@echo Chimera MEV Bot - Available Commands
	@echo ========================================
	@echo.
	@echo   make start         - Start all services
	@echo   make stop          - Stop all services
	@echo   make restart       - Restart all services
	@echo   make logs          - View container logs
	@echo   make reset         - Reset environment (removes all data)
	@echo   make backup        - Backup database and data
	@echo   make test          - Run tests
	@echo   make build         - Build Docker images
	@echo   make clean         - Clean up containers and images
	@echo   make status        - Show service status
	@echo   make shell         - Open shell in bot container
	@echo   make db-shell      - Open PostgreSQL shell
	@echo   make redis-shell   - Open Redis CLI
	@echo   make tools         - Start management tools (pgAdmin, Redis Commander)
	@echo   make monitoring    - Start monitoring stack (Prometheus, Grafana)
	@echo   make anvil         - Start Anvil local fork
	@echo   make anvil-reset   - Reset Anvil fork state
	@echo   make anvil-logs    - View Anvil logs
	@echo   make fork-test     - Run tests against local fork
	@echo.
	@echo ========================================

# Start services
start:
	@echo Starting Chimera services...
	@if not exist .env copy .env.example .env
	@if not exist logs mkdir logs
	@if not exist data mkdir data
	@docker-compose up -d
	@echo.
	@echo Services started! Access at:
	@echo   PostgreSQL: localhost:5432
	@echo   Redis: localhost:6379
	@echo.

# Stop services
stop:
	@echo Stopping Chimera services...
	@docker-compose down
	@echo Services stopped.

# Restart services
restart: stop start

# View logs
logs:
	@docker-compose logs -f --tail=100

# Reset environment (WARNING: deletes all data)
reset:
	@echo WARNING: This will delete all data!
	@set /p confirm="Continue? (yes/no): "
	@if "%confirm%"=="yes" (docker-compose down -v && echo Reset complete.)

# Backup data
backup:
	@echo Creating backup...
	@backup.bat

# Run tests
test:
	@echo Running tests...
	@docker-compose exec bot python -m pytest bot/ -v --cov=bot --cov-report=term-missing

# Build Docker images
build:
	@echo Building Docker images...
	@docker-compose build --no-cache

# Clean up
clean:
	@echo Cleaning up containers and images...
	@docker-compose down -v --rmi all
	@echo Cleanup complete.

# Show service status
status:
	@docker-compose ps

# Open shell in bot container
shell:
	@docker-compose exec bot /bin/bash

# Open PostgreSQL shell
db-shell:
	@docker-compose exec postgres psql -U chimera_user -d chimera

# Open Redis CLI
redis-shell:
	@docker-compose exec redis redis-cli

# Start management tools
tools:
	@echo Starting management tools...
	@docker-compose --profile tools up -d
	@echo.
	@echo Management tools started:
	@echo   pgAdmin: http://localhost:5050
	@echo   Redis Commander: http://localhost:8081
	@echo.

# Start monitoring stack
monitoring:
	@echo Starting monitoring stack...
	@docker-compose --profile monitoring up -d
	@echo.
	@echo Monitoring stack started:
	@echo   Prometheus: http://localhost:9090
	@echo   Grafana: http://localhost:3000 (admin/admin)
	@echo.

# Start Anvil local fork
anvil:
	@echo Starting Anvil local fork...
	@docker-compose --profile testing up -d anvil
	@echo.
	@echo Anvil started:
	@echo   RPC URL: http://localhost:8545
	@echo   Chain ID: 8453 (Base)
	@echo.
	@echo Verify with: cast block-number --rpc-url http://localhost:8545
	@echo.

# Reset Anvil fork state
anvil-reset:
	@echo Resetting Anvil fork state...
	@reset.bat anvil

# View Anvil logs
anvil-logs:
	@docker-compose --profile testing logs -f anvil

# Run tests against local fork
fork-test:
	@echo Running tests against Anvil fork...
	@docker-compose --profile testing up -d anvil
	@timeout /t 10 /nobreak >nul
	@cd chimera\contracts && forge test --fork-url http://localhost:8545 -vvv
