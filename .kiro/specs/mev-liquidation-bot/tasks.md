# Implementation Plan: MEV Liquidation Bot (Project Chimera)

This implementation plan breaks down the feature into discrete, manageable coding tasks. Each task builds incrementally on previous tasks, with all code integrated into the system. Tasks are focused exclusively on writing, modifying, or testing code.

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

- [ ] 6. Implement SafetyController module
- [ ] 6.1 Implement state machine management

  - Maintain three states: NORMAL, THROTTLED, HALTED
  - Implement state transition logic based on performance metrics
  - NORMAL → THROTTLED: inclusion 50-60% OR accuracy 85-90%
  - NORMAL → HALTED: inclusion <50% OR accuracy <85% OR failures ≥3
  - THROTTLED → NORMAL: inclusion >60% AND accuracy >90%
  - HALTED → NORMAL: Manual operator intervention only
  - _Requirements: 1.3, 3.4.2, 3.4.4_

- [ ] 6.2 Implement limit enforcement

  - Enforce MAX_SINGLE_EXECUTION_USD before every execution
  - Enforce MAX_DAILY_VOLUME_USD with daily reset at midnight UTC
  - Enforce MIN_PROFIT_USD as minimum acceptable net profit
  - Track consecutive failure count (reset on success)
  - Reject executions that would violate any limit
  - Log all limit violations with opportunity details
  - _Requirements: 1.3, 3.4.1, 3.4.5_

- [ ] 6.3 Implement performance metrics calculation

  - Track inclusion rate over last 100 submissions
  - Track simulation accuracy over last 100 successful executions
  - Calculate inclusion_rate = successful_inclusions / total_submissions
  - Calculate simulation_accuracy = actual_profit / simulated_profit (average)
  - Recalculate metrics every 10 minutes
  - _Requirements: 1.3, 3.4.3_

- [ ] 6.4 Implement automatic state transitions

  - Apply state transition rules based on calculated metrics
  - Log state transitions with triggering reason and timestamp
  - Send alerts on THROTTLED or HALTED transitions
  - Implement manual_resume() function for operator intervention
  - _Requirements: 1.3, 3.4.4, 3.4.5_

- [ ] 6.5 Implement execution tracking

  - Record every execution attempt to executions table within 1 second
  - Include timestamp, opportunity details, simulation result, actual result
  - Update consecutive failure count on submission
  - Reset consecutive failures on successful inclusion
  - Maintain execution history for performance analysis
  - _Requirements: 1.4, 3.4.5, 7.7_

- [ ]\* 6.6 Write unit tests for SafetyController

  - Test state machine transitions (all paths)
  - Test limit enforcement (single, daily, minimum)
  - Test consecutive failure tracking
  - Test metrics calculation (inclusion rate, simulation accuracy)
  - Test throttling logic (50% random skip)
  - _Requirements: 7.1.1_

- [ ] 7. Implement main bot orchestrator and integration
- [ ] 7.1 Create main bot orchestrator

  - Implement initialization: load config, establish database connections, connect to RPC providers
  - Load smart contract ABI and create contract instance
  - Initialize all modules (StateEngine, OpportunityDetector, ExecutionPlanner, SafetyController)
  - Verify operator wallet has sufficient gas balance
  - _Requirements: 1.2, 1.4_

- [ ] 7.2 Implement main event loop

  - Start StateEngine in background as async task
  - Check SafetyController state (skip if HALTED, throttle if THROTTLED)
  - Get opportunities from OpportunityDetector
  - For each opportunity: plan execution, check safety, submit bundle
  - Update performance metrics every 100 submissions
  - Sleep 5 seconds between scan cycles
  - _Requirements: 1.1, 3.1, 3.2, 3.3, 3.4_

- [ ] 7.3 Implement error handling and graceful degradation

  - Catch RPC errors and switch to backup provider
  - Catch database errors and queue operations in memory
  - Catch unexpected exceptions, log with stack trace, continue
  - Enter HALTED state on critical errors
  - Never crash the main loop
  - _Requirements: 4.2.1, 4.2.2_

- [ ] 7.4 Implement monitoring integration

  - Export metrics to CloudWatch every 60 seconds
  - Send CRITICAL alerts (phone + SMS) for HALTED state, security incidents, operator balance <0.1 ETH
  - Send HIGH alerts (SMS) for THROTTLED state, inclusion <50%, consecutive failures = 2
  - Send MEDIUM alerts (email) for approaching limits, key rotation due
  - Send LOW alerts (email) for daily summaries
  - _Requirements: 4.4.1, 4.4.2_

- [ ]\* 7.5 Write integration tests

  - Test StateEngine → OpportunityDetector data flow
  - Test OpportunityDetector → ExecutionPlanner handoff
  - Test ExecutionPlanner → SafetyController validation
  - Test SafetyController → Database logging
  - Test full pipeline with mocked RPC responses
  - _Requirements: 7.2.1, 7.2.2_

- [ ] 8. Implement historical data collection and backtesting
- [ ] 8.1 Create historical data collection script

  - Connect to Base mainnet via Alchemy
  - Scan last 1.3M blocks (~30 days at 2s/block)
  - Filter for liquidation events from Moonwell and Seamless Protocol
  - Collect gas prices for same period
  - Save to data/historical_liquidations.csv
  - _Requirements: 9.1_

- [ ] 8.2 Implement backtest engine

  - Load historical liquidations from CSV
  - For each liquidation: determine if bot would have detected (health_factor < 1.0)
  - Calculate bot latency: detection_latency (500ms) + build_latency (200ms)
  - Determine if bot would have won by comparing latencies
  - Calculate net profit including all costs (gas, L1 data, bribe, flash loan, slippage)
  - Track win rate, profitable rate, average net profit
  - _Requirements: 9.2, 9.3_

- [ ] 8.3 Generate sensitivity analysis

  - Calculate metrics for Optimistic, Base Case, Pessimistic, Worst Case scenarios
  - Vary win rate, average profit, bribe percentage
  - Calculate monthly profit and annual ROI for each scenario
  - Generate report with scenario table
  - Provide GO/STOP/PIVOT recommendation based on Base Case ROI
  - _Requirements: 9.4_

- [ ]\* 8.4 Write tests for backtest engine

  - Test detection logic with various health factors
  - Test latency comparison logic
  - Test profit calculation with all cost components
  - Test scenario generation
  - _Requirements: 7.1.1_

- [ ] 9. Create infrastructure as code
- [ ] 9.1 Implement Terraform configuration for AWS

  - Define EC2 c7g.xlarge instance in private VPC subnet
  - Define RDS PostgreSQL db.t4g.medium (Multi-AZ)
  - Define ElastiCache Redis cache.t4g.small
  - Define AWS Secrets Manager for operator key
  - Define CloudWatch dashboards and alarms
  - Define IAM roles and security groups
  - _Requirements: 8.1.1_

- [ ] 9.2 Create deployment documentation

  - Document pre-deployment checklist
  - Document mainnet deployment steps
  - Document rollback procedure
  - Document operational procedures (pause, resume, key rotation)
  - _Requirements: 8.2.2, 8.2.3, 9.1, 9.2_

- [ ]\* 9.3 Create operational runbooks

  - Create runbook for HALTED state recovery
  - Create runbook for key compromise response
  - Create runbook for sequencer outage response
  - Create runbook for sustained losses response
  - _Requirements: 9.3.1_

- [ ] 10. Final integration and validation
- [ ] 10.1 Perform end-to-end testing on local fork

  - Use Hardhat/Anvil to fork Base mainnet
  - Replay 100+ historical liquidations
  - Validate profit calculations match simulation
  - Test all failure scenarios
  - Measure end-to-end latency
  - _Requirements: 7.2.1, 7.2.2_

- [ ] 10.2 Deploy and validate on Base Sepolia testnet

  - Deploy Chimera contract to Base Sepolia
  - Verify contract source code on BaseScan
  - Configure bot with testnet RPC endpoints
  - Execute 50+ liquidations over 2-week period
  - Measure inclusion rate (target: >60%)
  - Measure simulation accuracy (target: >90%)
  - Measure uptime (target: >95%)
  - _Requirements: 7.2.3, 10.1, 10.2_

- [ ] 10.3 Generate Phase 1 completion report

  - Document backtest results (Base Case ROI, win rate, sensitivity analysis)
  - Document test coverage (unit, integration, smart contract)
  - Document security scan results (Slither, Mythril)
  - Provide GO/STOP/PIVOT recommendation
  - _Requirements: 10.1.1_

- [ ] 10.4 Generate Phase 2 completion report
  - Document testnet performance (inclusion rate, simulation accuracy, uptime)
  - Document operational validation (pause, resume, key rotation)
  - Document audit status and findings
  - Provide mainnet deployment readiness assessment
  - _Requirements: 10.2.1_
