# Implementation Plan: MEV Liquidation Bot (Project Chimera)

This implementation plan breaks down the feature into discrete, manageable coding tasks. Each task builds incrementally on previous tasks, with all code integrated into the system. Tasks are focused exclusively on writing, modifying, or testing code.

## Current Status

**Phase 1 (Local Development)**: ✅ **COMPLETE** - All core modules implemented and tested

- Smart contract (Chimera.sol) with flash loan integration, DEX swaps, and security controls
- Bot modules: StateEngine, OpportunityDetector, ExecutionPlanner, SafetyController
- Database schema and connection management (PostgreSQL + Redis)
- Logging infrastructure with structured JSON logging
- Backtest engine with historical data collection and sensitivity analysis
- Local development infrastructure (Docker Compose with all services)
- Monitoring stack (Prometheus + Grafana dashboards)

**Phase 2 (Testnet Validation)**: 🔄 **IN PROGRESS** - Ready for testnet deployment

- Deployment scripts created and documented
- Configuration management system complete
- All operational procedures documented

**Phase 3 (Mainnet Deployment)**: ⏳ **PENDING** - Awaiting Phase 2 validation

- Production infrastructure code (AWS) needs to be created
- Operational runbooks need to be written
- Professional audit needs to be completed

## Remaining Work

The remaining tasks focus on:

1. **End-to-end testing** on local fork to validate complete system integration
2. **Testnet deployment and validation** over 2-week period to prove operational readiness
3. **Production infrastructure** setup (AWS Terraform/CloudFormation)
4. **Operational runbooks** for incident response and recovery procedures
5. **Phase completion reports** documenting results and providing go/no-go recommendations

## Task List

- [x] 1. Set up project structure and core infrastructure

- [x] 1.1 Create directory structure for contracts, bot, scripts, and infrastructure

  - Create chimera/ root with contracts/, bot/, scripts/, data/, logs/, infrastructure/ subdirectories
  - Set up bot/src/ with module files (state_engine.py, opportunity_detector.py, execution_planner.py, safety_controller.py, config.py, types.py, main.py)
  - Set up contracts/src/, contracts/test/, contracts/script/ directories
  - _Requirements: Project organization for maintainability_

- [x] 1.2 Implement configuration management system

  - Create config.py with hierarchical configuration loading (environment variables, config.yaml, database)
  - Implement Pydantic models for configuration validation
  - Create .env.example template with all required secrets
  - Create config.yaml with static parameters (protocol addresses, oracle addresses, DEX routers, thresholds)
  - _Requirements: 1.1, 5.1, 7.1_

- [x] 1.3 Define core data models and types

  - Create types.py with Pydantic/dataclass models for Position, Opportunity, Bundle, ExecutionRecord
  - Define SystemState enum (NORMAL, THROTTLED, HALTED)
  - Define error types and exception classes
  - _Requirements: 1.1, 1.2, 2.1, 3.3, 7.1_

- [x] 1.4 Set up database schema and connection handling

  - Create SQLAlchemy models for executions, state_divergences, performance_metrics, system_events tables
  - Implement database connection pooling with automatic reconnection
  - Create database migration scripts
  - Implement Redis connection handling with fallback to in-memory cache
  - _Requirements: 1.1, 5.1, 7.1, 7.7_

- [x] 1.5 Implement basic logging infrastructure

  - Create structured JSON logging with module, level, timestamp, context
  - Implement log rotation and retention policies
  - Set up CloudWatch integration for log aggregation
  - _Requirements: 7.7_

- [x] 2. Implement Chimera smart contract

- [x] 2.1 Create Chimera.sol with security patterns

  - Implement contract inheriting from Ownable2Step, Pausable, ReentrancyGuard
  - Add treasury address state variable and constructor
  - Implement executeLiquidation function signature with parameters (lendingProtocol, borrower, collateralAsset, debtAsset, debtAmount, minProfit)
  - Add pause(), unpause(), setTreasury(), rescueTokens() functions
  - Define LiquidationExecuted and TreasuryUpdated events
  - _Requirements: 3.5.1, 3.5.4, 3.5.5, 3.5.6, 6.1_

- [x] 2.2 Implement flash loan integration

  - Implement IFlashLoanReceiver interface for Aave V3
  - Add executeOperation callback function with flash loan repayment logic
  - Implement flash loan request in executeLiquidation
  - Add support for Balancer flash loans as backup
  - Verify repayment amount calculation including premium
  - _Requirements: 3.5.2_

- [x] 2.3 Implement DEX swap integration

  - Add Uniswap V3 swap logic in executeOperation callback
  - Implement exact input swap with minimum output amount
  - Add Aerodrome swap as backup (if available on Base)
  - Use SafeERC20 for all token approvals and transfers
  - Approve only exact amounts needed (no infinite approvals)
  - _Requirements: 3.5.3, 3.5.6_

- [x] 2.4 Complete atomic liquidation flow

  - Implement complete executeOperation flow: approve → liquidate → swap → verify → repay → transfer profit
  - Add input validation for all parameters (non-zero addresses, positive amounts)
  - Verify profit >= minProfit before completing
  - Transfer all profits to treasury address
  - Emit LiquidationExecuted event with protocol, borrower, profitAmount, gasUsed
  - _Requirements: 3.5.1, 3.5.6_

- [x] 2.5 Write comprehensive Foundry tests for Chimera contract

  - Write unit tests for pause/unpause, setTreasury, rescueTokens
  - Write access control tests (onlyOwner enforcement)
  - Write reentrancy protection tests
  - Write fork tests for complete liquidation on Base mainnet fork
  - Write fuzz tests for profit calculations and parameter validation
  - Achieve >95% code coverage
  - _Requirements: 7.3.1, 7.3.2, 7.3.3_

- [x] 2.6 Create deployment scripts

  - Create Deploy.s.sol Foundry script for testnet and mainnet deployment
  - Add contract verification logic for BaseScan
  - Create deployment documentation with step-by-step instructions
  - _Requirements: 8.2.2_

- [-] 3. Implement StateEngine module

- [x] 3.1 Create WebSocket connection management

  - Implement WebSocket connection to Alchemy (primary) and QuickNode (backup)
  - Add automatic reconnection with exponential backoff
  - Implement connection health monitoring and failover within 5 seconds
  - Subscribe to newHeads for real-time block monitoring
  - _Requirements: 1.1, 3.1.1, 3.1.5_

- [x] 3.2 Implement event parsing for lending protocols

  - Parse Borrow, Repay, Liquidate events from Moonwell and Seamless Protocol
  - Parse Chainlink oracle price update events
  - Update position cache in Redis within 100ms of event receipt
  - Store event checkpoints every 10 blocks for recovery
  - _Requirements: 1.2, 1.3, 3.1.3_

- [x] 3.3 Implement block-level state reconciliation

  - For each position in cache, construct eth_call to lending protocol
  - Fetch canonical debt_amount and collateral_amount from archive RPC
  - Calculate divergence in basis points: |cached - canonical| / canonical \* 10000
  - Trigger HALT if any position diverges >10 BPS
  - Log all divergences to state_divergences table
  - Execute reconciliation every 1 block (not every 5)
  - _Requirements: 1.2, 3.1.2_

- [x] 3.4 Implement sequencer health monitoring

  - Verify sequential block numbers (current == previous + 1)
  - Detect timestamp jumps >20 seconds
  - Detect block production stalls (no new block for >10 seconds)
  - Detect unusual reorg depth (>3 blocks)
  - Enter HALT state on sequencer anomaly detection
  - _Requirements: 1.3, 3.1.4_

- [x] 3.5 Implement position cache management

  - Maintain position map in Redis with 60-second TTL
  - Implement get_position(protocol, user) and get_all_positions() methods
  - Track last_update_block and blocks_unhealthy for each position
  - Implement cache rebuild from blockchain on Redis reconnection
  - _Requirements: 1.4, 3.1.3_

-

- [x] 3.6 Write unit tests for StateEngine

  - Test block processing with various event combinations
  - Test state reconciliation with mock divergence scenarios
  - Test sequencer health detection (gaps, timestamp jumps)
  - Test WebSocket reconnection logic
  - Test chain reorganization handling
  - _Requirements: 7.1.1_

- [x] 4. Implement OpportunityDetector module

- [x] 4.1 Implement health factor calculation

  - Fetch Chainlink oracle prices for collateral and debt assets
  - Calculate health*factor = (collateral_amount * collateral*price * liquidation_threshold) / (debt_amount \* debt_price)
  - Identify positions where health_factor < 1.0 as liquidatable
  - Scan all positions every 5 seconds maximum
  - _Requirements: 1.2, 3.2.1, 3.2.2_

- [x] 4.2 Implement multi-oracle sanity checks

  - Fetch secondary oracle price from Pyth or Redstone
  - Calculate divergence: |primary - secondary| / primary
  - Skip opportunity if divergence >5%
  - Compare current price to previous block price
  - Skip if price moved >30% in one block
  - _Requirements: 1.2, 3.2.2, 3.2.3_

- [x] 4.3 Implement confirmation blocks logic

  - Track blocks_unhealthy counter for each position
  - Increment counter each block when health_factor < 1.0
  - Require minimum 2 blocks unhealthy before flagging as liquidatable
  - Reset counter when health_factor >= 1.0
  - _Requirements: 1.2, 3.2.3_

- [x] 4.4 Implement protocol state checks

  - Verify liquidation function is not paused via protocol contract call
  - Check protocol rate limits
  - Validate position size within protocol bounds
  - Skip opportunity if any check fails
  - _Requirements: 1.2, 3.2.3_

- [x] 4.5 Implement rough profit estimation

  - Estimate liquidation bonus: collateral*amount * collateral*price * liquidation_bonus
  - Estimate arbitrage profit (~2-5% of collateral value)
  - Estimate costs: gas ($10-20) + bribe (20% of gross) + flash loan (0.09%) + slippage (1%)
  - Calculate net_estimate = gross_profit - estimated_costs
  - Skip if net_estimate < $50
  - _Requirements: 1.2, 3.2.4_

- [x] 4.6 Write unit tests for OpportunityDetector

  - Test health factor calculation with various collateral/debt ratios
  - Test multi-oracle sanity checks with divergent prices
  - Test price movement detection (30% threshold)
  - Test confirmation blocks logic (2-block minimum)
  - Test profit estimation accuracy
  - _Requirements: 7.1.1_

- [x] 5. Implement ExecutionPlanner module

- [x] 5.1 Implement transaction construction

  - Build complete transaction with Chimera contract executeLiquidation call
  - Encode function parameters (lendingProtocol, borrower, collateralAsset, debtAsset, debtAmount, minProfit)
  - Set gas limit, nonce, max_fee_per_gas, priority_fee_per_gas
  - Set minProfit parameter to 50% of estimated profit
  - _Requirements: 1.3, 3.3.1_

- [x] 5.2 Implement on-chain simulation (CRITICAL)

  - Execute eth_call with transaction data against current block
  - Parse simulation result to extract actual profit amount in wei
  - Call eth_estimateGas for accurate gas usage
  - Validate simulation success (status == 1 and profit > 0)
  - NEVER proceed if simulation fails or shows loss
  - Log all simulation failures with opportunity details
  - _Requirements: 1.3, 3.3.2_

- [x] 5.3 Implement Base L2 cost calculation

  - Calculate L2 execution cost: gas_estimate \* (base_fee + priority_fee)
  - Fetch L1 scalar and gas price from Base system contracts (0x4200000000000000000000000000000000000015)
  - Calculate L1 data posting cost: calldata*size * l1*gas_price * l1_scalar
  - Calculate total gas cost: l2_cost + l1_cost
  - Convert to USD using real-time ETH/USD oracle price
  - _Requirements: 1.3, 3.3.3_

- [x] 5.4 Implement complete cost calculation

  - Calculate builder bribe as percentage of gross profit
  - Calculate flash loan premium (0.05-0.09% depending on protocol)
  - Budget 1% slippage for DEX swaps
  - Calculate total_cost_usd = gas_cost + bribe + flash_loan + slippage
  - Calculate net_profit_usd = simulated_profit_usd - total_cost_usd
  - Reject if net_profit_usd < $50
  - _Requirements: 1.3, 3.3.3, 3.3.4_

- [x] 5.5 Implement dynamic bribe optimization

  - Start with 15% of gross profit as baseline bribe
  - Track inclusion rate over last 100 submissions per submission path
  - Increase bribe by 5% if inclusion rate <60%
  - Decrease bribe by 2% if inclusion rate >90%
  - Cap bribe at 40% of gross profit
  - Reject opportunity if bribe would exceed cap
  - Update bribe model every 100 submissions
  - _Requirements: 1.3, 3.3.5_

- [x] 5.6 Implement submission path selection

  - Implement adapters for direct mempool, Base-native builders (if available), private RPCs
  - Calculate expected value for each path: EV = (profit \* inclusion_rate) - (bribe + fees)
  - Select path with highest expected value
  - Implement failover to alternative path if primary fails
  - _Requirements: 1.3, 3.3.7_

- [x] 5.7 Implement bundle signing and submission

  - Sign transaction with operator private key from AWS Secrets Manager
  - Submit to selected submission path
  - Track submission timestamp and block number
  - Log complete bundle details to executions table
  - Implement retry logic with exponential backoff (max 3 retries)
  - _Requirements: 1.3, 1.4, 3.3.6_

- [x] 5.8 Write unit tests for ExecutionPlanner

  - Test simulation result parsing
  - Test L2 + L1 cost calculation with various gas prices
  - Test bribe optimization algorithm (increase/decrease logic)
  - Test net profit calculation with all cost components
  - Test submission path selection
  - _Requirements: 7.1.1_

- [x] 6. Implement SafetyController module

- [x] 6.1 Implement state machine management

  - Maintain three states: NORMAL, THROTTLED, HALTED
  - Implement state transition logic based on performance metrics
  - NORMAL → THROTTLED: inclusion 50-60% OR accuracy 85-90%
  - NORMAL → HALTED: inclusion <50% OR accuracy <85% OR failures ≥3
  - THROTTLED → NORMAL: inclusion >60% AND accuracy >90%
  - HALTED → NORMAL: Manual operator intervention only
  - _Requirements: 1.3, 3.4.2, 3.4.4_

- [x] 6.2 Implement limit enforcement

  - Enforce MAX_SINGLE_EXECUTION_USD before every execution
  - Enforce MAX_DAILY_VOLUME_USD with daily reset at midnight UTC
  - Enforce MIN_PROFIT_USD as minimum acceptable net profit
  - Track consecutive failure count (reset on success)
  - Reject executions that would violate any limit
  - Log all limit violations with opportunity details
  - _Requirements: 1.3, 3.4.1, 3.4.5_

- [x] 6.3 Implement performance metrics calculation

  - Track inclusion rate over last 100 submissions
  - Track simulation accuracy over last 100 successful executions
  - Calculate inclusion_rate = successful_inclusions / total_submissions
  - Calculate simulation_accuracy = actual_profit / simulated_profit (average)
  - Recalculate metrics every 10 minutes
  - _Requirements: 1.3, 3.4.3_

- [x] 6.4 Implement automatic state transitions

  - Apply state transition rules based on calculated metrics
  - Log state transitions with triggering reason and timestamp
  - Send alerts on THROTTLED or HALTED transitions
  - Implement manual_resume() function for operator intervention
  - _Requirements: 1.3, 3.4.4, 3.4.5_

- [x] 6.5 Implement execution tracking

  - Record every execution attempt to executions table within 1 second
  - Include timestamp, opportunity details, simulation result, actual result
  - Update consecutive failure count on submission
  - Reset consecutive failures on successful inclusion
  - Maintain execution history for performance analysis
  - _Requirements: 1.4, 3.4.5, 7.7_

- [x] 6.6 Write unit tests for SafetyController

  - Test state machine transitions (all paths)
  - Test limit enforcement (single, daily, minimum)
  - Test consecutive failure tracking
  - Test metrics calculation (inclusion rate, simulation accuracy)
  - Test throttling logic (50% random skip)
  - _Requirements: 7.1.1_

- [x] 7. Implement main bot orchestrator and integration

- [x] 7.1 Create main bot orchestrator

  - Implement initialization: load config, establish database connections, connect to RPC providers
  - Load smart contract ABI and create contract instance
  - Initialize all modules (StateEngine, OpportunityDetector, ExecutionPlanner, SafetyController)
  - Verify operator wallet has sufficient gas balance
  - _Requirements: 1.2, 1.4_

- [x] 7.2 Implement main event loop

  - Start StateEngine in background as async task
  - Check SafetyController state (skip if HALTED, throttle if THROTTLED)
  - Get opportunities from OpportunityDetector
  - For each opportunity: plan execution, check safety, submit bundle
  - Update performance metrics every 100 submissions
  - Sleep 5 seconds between scan cycles
  - _Requirements: 1.1, 3.1, 3.2, 3.3, 3.4_

- [x] 7.3 Implement error handling and graceful degradation

  - Catch RPC errors and switch to backup provider
  - Catch database errors and queue operations in memory
  - Catch unexpected exceptions, log with stack trace, continue
  - Enter HALTED state on critical errors
  - Never crash the main loop
  - _Requirements: 4.2.1, 4.2.2_

- [x] 7.4 Implement monitoring integration

  - Export metrics to CloudWatch every 60 seconds
  - Send CRITICAL alerts (phone + SMS) for HALTED state, security incidents, operator balance <0.1 ETH
  - Send HIGH alerts (SMS) for THROTTLED state, inclusion <50%, consecutive failures = 2
  - Send MEDIUM alerts (email) for approaching limits, key rotation due
  - Send LOW alerts (email) for daily summaries
  - _Requirements: 4.4.1, 4.4.2_

- [x] 7.5 Write integration tests

  - Test StateEngine → OpportunityDetector data flow
  - Test OpportunityDetector → ExecutionPlanner handoff
  - Test ExecutionPlanner → SafetyController validation
  - Test SafetyController → Database logging
  - Test full pipeline with mocked RPC responses
  - _Requirements: 7.2.1, 7.2.2_

- [x] 8. Implement historical data collection and backtesting

- [x] 8.1 Create historical data collection script

  - Connect to Base mainnet via Alchemy
  - Scan last 1.3M blocks (~30 days at 2s/block)
  - Filter for liquidation events from Moonwell and Seamless Protocol
  - Collect gas prices for same period
  - Save to data/historical_liquidations.csv
  - _Requirements: 9.1_

- [x] 8.2 Implement backtest engine

  - Load historical liquidations from CSV
  - For each liquidation: determine if bot would have detected (health_factor < 1.0)
  - Calculate bot latency: detection_latency (500ms) + build_latency (200ms)
  - Determine if bot would have won by comparing latencies
  - Calculate net profit including all costs (gas, L1 data, bribe, flash loan, slippage)
  - Track win rate, profitable rate, average net profit
  - _Requirements: 9.2, 9.3_

- [x] 8.3 Generate sensitivity analysis

  - Calculate metrics for Optimistic, Base Case, Pessimistic, Worst Case scenarios
  - Vary win rate, average profit, bribe percentage
  - Calculate monthly profit and annual ROI for each scenario
  - Generate report with scenario table
  - Provide GO/STOP/PIVOT recommendation based on Base Case ROI
  - _Requirements: 9.4_

- [x] 8.4 Write tests for backtest engine

  - Test detection logic with various health factors
  - Test latency comparison logic
  - Test profit calculation with all cost components
  - Test scenario generation
  - _Requirements: 7.1.1_

- [-] 9. Create local development infrastructure

- [x] 9.1 Implement Docker Compose configuration for local development

  - Define PostgreSQL container (postgres:16-alpine) with persistent volume
  - Define Redis container (redis:7-alpine) with persistent volume
  - Define bot application container with Python 3.11
  - Define local secrets management using .env file (not AWS Secrets Manager)
  - Define volume mounts for logs/ and data/ directories
  - Configure networking between containers
  - Add healthchecks for all services
  - _Requirements: 8.1.1_

- [x] 9.2 Create local monitoring stack (optional)

  - Define Prometheus container for metrics collection
  - Define Grafana container for visualization dashboards
  - Create Grafana dashboard JSON for bot metrics (inclusion rate, profit, state)
  - Configure Prometheus scraping from bot metrics endpoint
  - Add alerting rules for local development (console logs instead of SMS)
  - _Requirements: 4.4.1_

- [x] 9.3 Implement local RPC node (optional for advanced testing)

  - Define Anvil/Hardhat container for Base mainnet fork

  - Configure fork from Base mainnet at specific block height
  - Set up automatic state persistence between restarts
  - Document how to reset fork state for testing
  - _Requirements: 7.2.1_

- [x] 9.4 Create development scripts and tooling

  - Create start.sh script to launch all Docker services
  - Create stop.sh script to gracefully shutdown services
  - Create reset.sh script to clear all data and restart fresh
  - Create logs.sh script to tail bot logs in real-time
  - Create backup.sh script to backup database and Redis data
  - Add Makefile with common commands (make start, make logs, make test)
  - _Requirements: 8.2.2_

- [x] 9.5 Document local development setup

  - Document prerequisites (Docker, Docker Compose, Python)
  - Document environment variable configuration in .env
  - Document how to obtain RPC endpoints (Alchemy, QuickNode)
  - Document how to fund operator wallet on testnet
  - Document common troubleshooting steps
  - Create quick-start guide (5 commands to running bot)
  - _Requirements: 8.2.2, 8.2.3_

- [ ] 9.6 Create production infrastructure as code (AWS)

  - Create Terraform or CloudFormation templates for production infrastructure
  - Define EC2 c7g.xlarge instance in private VPC subnet with security groups
  - Define RDS PostgreSQL db.t4g.medium (Multi-AZ) with automated backups
  - Define ElastiCache Redis cache.t4g.small with automatic failover
  - Define AWS Secrets Manager secret for operator private key with rotation policy
  - Define CloudWatch dashboards for system metrics (state, inclusion rate, profit, balance)
  - Define CloudWatch alarms for CRITICAL, HIGH, and MEDIUM alert conditions
  - Define IAM roles with least-privilege permissions for EC2, RDS, ElastiCache, Secrets Manager
  - Define VPC, subnets, NAT gateway, and security groups for network isolation
  - Document infrastructure deployment procedure
  - _Requirements: 8.1.1_

- [x] 9.7 Create deployment documentation

  - Document pre-deployment checklist
  - Document mainnet deployment steps
  - Document rollback procedure
  - Document operational procedures (pause, resume, key rotation)
  - _Requirements: 8.2.2, 8.2.3, 9.1, 9.6_

- [x] 9.8 Create operational runbooks

  - Create runbook for HALTED state recovery (diagnosis, manual_resume procedure, validation steps)
  - Create runbook for key compromise response (immediate actions, key rotation, security audit)
  - Create runbook for sequencer outage response (detection, monitoring, recovery procedures)
  - Create runbook for sustained losses response (analysis, parameter adjustment, potential shutdown)
  - Create runbook for database/Redis outage recovery (queue management, data integrity checks)
  - Create runbook for RPC provider failover and reconnection procedures
  - Document escalation procedures and contact information for each scenario
  - _Requirements: 9.3.1_

- [ ] 10. Final integration and validation

- [x] 10.1 Set up local testing infrastructure

  - Create pytest configuration (pytest.ini) with test discovery, coverage settings, and markers
  - Create conftest.py with shared fixtures for database, Redis, RPC mocks, and test data
  - Set up test database and Redis instances using Docker Compose test profile
  - Create mock RPC provider fixtures that return realistic Base mainnet responses
  - Create test data generators for positions, opportunities, and execution records
  - Document how to run tests locally (pytest commands, coverage reports)
  - _Requirements: 7.1.1, 7.2.1_

- [x] 10.2 Run comprehensive unit tests locally

  - Execute all existing unit tests for StateEngine, OpportunityDetector, ExecutionPlanner, SafetyController
  - Execute Foundry tests for Chimera smart contract (forge test)
  - Generate coverage report and verify >90% coverage for bot modules
  - Generate coverage report for smart contract and verify >95% coverage
  - Fix any failing tests and document results
  - Run tests in CI/CD pipeline (GitHub Actions or similar)
  - _Requirements: 7.1.1, 7.3.1, 7.3.2, 7.3.3_

- [x] 10.3 Run integration tests with mocked dependencies

  - Test StateEngine → OpportunityDetector → ExecutionPlanner → SafetyController pipeline
  - Use mocked RPC responses to simulate various blockchain states
  - Test error handling: RPC failures, database disconnections, Redis outages
  - Test state transitions: NORMAL → THROTTLED → HALTED and recovery
  - Test limit enforcement: single execution, daily volume, minimum profit
  - Verify all modules integrate correctly without external dependencies
  - Document integration test results
  - _Requirements: 7.2.1, 7.2.2_

- [x] 10.4 Implement and test dry-run mode

  - Add --dry-run flag to main.py that disables actual transaction submission
  - In dry-run mode: detect opportunities, simulate executions, log results, but don't submit bundles
  - Create dry_run_report.py script to analyze dry-run logs and calculate theoretical performance
  - Test dry-run mode against live Base mainnet for 24 hours
  - Measure: opportunities detected per hour, simulation success rate, theoretical profit
  - Verify no transactions are submitted during dry-run
  - Document dry-run mode usage and results
  - _Requirements: 7.2.1, 8.2.3_

- [ ] 10.5 Perform end-to-end testing on local fork

  - Start Anvil fork of Base mainnet using docker-compose (already configured)
  - Deploy Chimera contract to local fork using deployment scripts
  - Fund operator wallet with forked ETH
  - Create test script (test_e2e_fork.py) to simulate liquidation scenarios
  - Impersonate lending protocol contracts to create unhealthy positions
  - Run bot against fork and verify it detects and executes liquidations
  - Test failure scenarios: reverted simulations, insufficient profit, state divergence
  - Measure end-to-end latency from detection to execution
  - Validate profit calculations match simulation results within 5%
  - Document test results and performance metrics
  - _Requirements: 7.2.1, 7.2.2_

- [ ] 10.6 Deploy and validate on Base Sepolia testnet

  - Deploy Chimera contract to Base Sepolia using existing deployment scripts
  - Verify contract source code on BaseScan using existing verification script
  - Update config.yaml with Base Sepolia RPC endpoints and contract addresses
  - Fund operator wallet with Sepolia ETH for gas (use faucet)
  - Run bot in testnet mode for 2-week validation period
  - Execute minimum 50 liquidations and track all metrics
  - Measure and document: inclusion rate (target >60%), simulation accuracy (target >90%), uptime (target >95%)
  - Test operational procedures: pause/unpause contract, manual state transitions, key rotation
  - Monitor for any unexpected errors or edge cases
  - _Requirements: 7.2.3, 10.1, 10.2_

- [ ] 10.7 Generate Phase 1 completion report

  - Compile backtest results from existing sensitivity analysis
  - Document Base Case ROI, win rate, and profitability projections
  - Compile test coverage reports from unit tests, integration tests, and smart contract tests
  - Document dry-run mode results (24-hour live detection test)
  - Document local fork testing results (e2e latency, profit accuracy)
  - Run Slither and Mythril security scans on Chimera contract
  - Document all security findings and mitigations
  - Provide GO/STOP/PIVOT recommendation based on backtest ROI threshold (>100%)
  - _Requirements: 10.1.1_

- [ ] 10.8 Generate Phase 2 completion report
  - Document testnet performance metrics over 2-week period
  - Analyze inclusion rate, simulation accuracy, and uptime statistics
  - Document operational validation results (pause, resume, state transitions, key rotation)
  - Compile professional audit status and findings (if audit completed)
  - Compare testnet results to backtest projections (variance analysis)
  - Assess mainnet deployment readiness against all Phase 2 exit criteria
  - Provide final mainnet deployment recommendation with risk assessment
  - _Requirements: 10.2.1_
