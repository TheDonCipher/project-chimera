# Requirements Document: MEV Liquidation Bot (Project Chimera)

## Introduction

Project Chimera is a MEV (Maximal Extractable Value) system designed to execute profitable liquidations on Base L2 lending protocols. The system consists of an off-chain Python agent and an on-chain Solidity smart contract that work together to identify, simulate, and execute atomic liquidation transactions. The bot targets lending protocols like Moonwell and Seamless Protocol on Base L2, competing with other MEV bots to capture liquidation opportunities profitably.

## Glossary

- **MEV Bot**: An automated system that extracts value from blockchain transactions by reordering, inserting, or censoring them
- **Liquidation**: The process of seizing collateral from an undercollateralized lending position
- **Health Factor**: A ratio measuring the collateralization of a lending position; values <1.0 indicate liquidatable positions
- **Flash Loan**: A loan that must be repaid within the same transaction, enabling capital-free liquidations
- **Base L2**: An Ethereum Layer 2 network built on the Optimism Stack, operated by Coinbase
- **Sequencer**: The centralized entity that orders transactions on Base L2
- **State Divergence**: A discrepancy between the bot's cached state and the canonical blockchain state
- **Simulation**: Executing a transaction via eth_call to predict outcomes without committing to the blockchain
- **Bribe**: Payment to block builders to prioritize transaction inclusion
- **L1 Data Posting Cost**: The cost to post transaction data to Ethereum mainnet (required for Base L2 transactions)
- **StateEngine**: The module responsible for maintaining synchronized blockchain state
- **OpportunityDetector**: The module that identifies liquidatable positions
- **ExecutionPlanner**: The module that simulates and constructs profitable transaction bundles
- **SafetyController**: The module that enforces limits and manages system operational states
- **Chimera Contract**: The on-chain smart contract that executes atomic liquidations

## Requirements

### Requirement 1: Real-Time Blockchain State Synchronization

**User Story:** As a MEV bot operator, I want the system to maintain an accurate, real-time view of blockchain state, so that liquidation opportunities are detected immediately and execution decisions are based on correct data.

#### Acceptance Criteria

1. WHEN a new block is produced on Base L2, THE StateEngine SHALL process the block within 500 milliseconds of receipt
2. WHILE the bot is operational, THE StateEngine SHALL maintain WebSocket connections to minimum 2 RPC providers with automatic failover within 5 seconds of primary failure
3. THE StateEngine SHALL reconcile cached state against canonical chain state every 1 block by comparing cached values against eth_call results
4. IF state divergence exceeds 10 basis points (0.1%), THEN THE StateEngine SHALL trigger HALTED state immediately
5. THE StateEngine SHALL detect sequencer anomalies by verifying sequential block numbers and detecting timestamp jumps exceeding 20 seconds

### Requirement 2: Accurate Liquidation Opportunity Detection

**User Story:** As a MEV bot operator, I want the system to accurately identify liquidatable positions with minimal false positives, so that gas and bribes are not wasted on unprofitable executions.

#### Acceptance Criteria

1. THE OpportunityDetector SHALL scan all known positions every 5 seconds maximum
2. THE OpportunityDetector SHALL calculate health factor as (collateral_value \* liquidation_threshold) / debt_value using Chainlink oracle prices
3. WHEN a position has health_factor less than 1.0, THE OpportunityDetector SHALL identify it as liquidatable
4. THE OpportunityDetector SHALL reject opportunities where primary oracle price diverges from secondary oracle by more than 5 percent
5. THE OpportunityDetector SHALL reject opportunities where oracle price moved more than 30 percent in one block
6. THE OpportunityDetector SHALL require positions to be unhealthy for minimum 2 blocks before flagging as liquidatable
7. THE OpportunityDetector SHALL maintain false positive rate below 10 percent

### Requirement 3: Guaranteed Profitability Through Simulation

**User Story:** As a MEV bot operator, I want every transaction to be simulated on-chain before execution, so that unprofitable trades are never submitted and capital is protected.

#### Acceptance Criteria

1. THE ExecutionPlanner SHALL simulate ALL transactions via eth_call before submission without exception
2. THE ExecutionPlanner SHALL parse simulation results to extract actual profit amount in wei
3. IF simulation fails or returns profit below $50 USD, THEN THE ExecutionPlanner SHALL reject the opportunity and log the reason
4. THE ExecutionPlanner SHALL calculate total cost including L2 execution gas, L1 data posting cost, builder bribe, flash loan premium, and DEX slippage
5. THE ExecutionPlanner SHALL fetch L1 scalar and gas price from Base system contracts at address 0x4200000000000000000000000000000000000015
6. THE ExecutionPlanner SHALL calculate net profit as simulated_profit minus all costs and reject if below $50 USD

### Requirement 4: Dynamic Bribe Optimization for Competitive Inclusion

**User Story:** As a MEV bot operator, I want the system to automatically adjust builder bribes based on inclusion performance, so that transactions are included competitively while minimizing costs.

#### Acceptance Criteria

1. THE ExecutionPlanner SHALL start with 15 percent of gross profit as baseline bribe
2. THE ExecutionPlanner SHALL track inclusion rate over last 100 submissions per submission path
3. WHEN inclusion rate falls below 60 percent, THE ExecutionPlanner SHALL increase bribe by 5 percent
4. WHEN inclusion rate exceeds 90 percent, THE ExecutionPlanner SHALL decrease bribe by 2 percent
5. THE ExecutionPlanner SHALL cap bribe at 40 percent of gross profit and reject opportunities requiring higher bribes
6. THE ExecutionPlanner SHALL update bribe model every 100 submissions

### Requirement 5: Multi-Layer Safety Controls and Limit Enforcement

**User Story:** As a MEV bot operator, I want the system to enforce strict operational limits and automatically halt on anomalies, so that catastrophic losses are prevented and capital is protected.

#### Acceptance Criteria

1. THE SafetyController SHALL enforce MAX_SINGLE_EXECUTION_USD limit before every execution
2. THE SafetyController SHALL enforce MAX_DAILY_VOLUME_USD limit with daily reset at midnight UTC
3. THE SafetyController SHALL maintain three states: NORMAL (full operation), THROTTLED (50 percent execution rate), and HALTED (no executions)
4. WHEN inclusion rate falls below 50 percent OR simulation accuracy falls below 85 percent OR consecutive failures reach 3, THEN THE SafetyController SHALL enter HALTED state
5. WHEN inclusion rate is between 50-60 percent OR simulation accuracy is between 85-90 percent, THEN THE SafetyController SHALL enter THROTTLED state
6. WHILE in HALTED state, THE SafetyController SHALL block all executions until manual operator intervention
7. THE SafetyController SHALL track consecutive failure count and reset to zero on any successful inclusion

### Requirement 6: Secure and Auditable Smart Contract Execution

**User Story:** As a MEV bot operator, I want the on-chain contract to execute liquidations atomically with comprehensive security controls, so that funds are protected from exploits and all operations are auditable.

#### Acceptance Criteria

1. THE Chimera Contract SHALL execute liquidations atomically: flash_loan → liquidate → swap → repay_loan → sweep_profit
2. THE Chimera Contract SHALL revert entire transaction if any step fails
3. THE Chimera Contract SHALL use OpenZeppelin ReentrancyGuard on executeLiquidation function
4. THE Chimera Contract SHALL use OpenZeppelin Ownable2Step for ownership management
5. THE Chimera Contract SHALL implement pause mechanism that blocks executeLiquidation when paused
6. THE Chimera Contract SHALL NOT store token balances between transactions (stateless operation)
7. THE Chimera Contract SHALL use SafeERC20 for all token transfers
8. THE Chimera Contract SHALL emit LiquidationExecuted event with protocol, borrower, profit_amount, and gas_used

### Requirement 7: Comprehensive Audit Trail and Performance Monitoring

**User Story:** As a MEV bot operator, I want complete logging of all execution attempts and performance metrics, so that I can analyze profitability, debug issues, and maintain compliance.

#### Acceptance Criteria

1. THE System SHALL persist every execution attempt to PostgreSQL within 1 second including timestamp, opportunity details, simulation result, and actual outcome
2. THE System SHALL log all state transitions with triggering conditions and timestamp
3. THE System SHALL calculate inclusion rate as successful_inclusions divided by total_submissions over last 100 submissions
4. THE System SHALL calculate simulation accuracy as actual_profit divided by simulated_profit over last 100 successful executions
5. THE System SHALL export metrics to CloudWatch every 60 seconds including system state, opportunities detected, bundles submitted, inclusion rate, and daily volume
6. THE System SHALL send CRITICAL alerts via phone and SMS for HALTED state, security incidents, and operator balance below 0.1 ETH
7. THE System SHALL retain all transaction logs for minimum 3 years

### Requirement 8: Graduated Scaling with Validation Gates

**User Story:** As a MEV bot operator, I want the system to scale execution limits gradually based on proven performance, so that risk is managed and profitability is validated at each tier.

#### Acceptance Criteria

1. THE System SHALL start at Tier 1 with MAX_SINGLE_EXECUTION_USD of $500 and MAX_DAILY_VOLUME_USD of $2,500
2. WHEN 100 successful executions are completed at Tier 1 with net positive cumulative profit AND inclusion rate above 60 percent AND zero critical incidents AND minimum 8 weeks elapsed, THEN THE System SHALL allow graduation to Tier 2
3. THE System SHALL increase limits to $1,000 single execution and $5,000 daily volume at Tier 2
4. WHEN 100 successful executions are completed at Tier 2 with cumulative profit above $5,000 AND inclusion rate above 65 percent AND annualized ROI above 100 percent AND minimum 12 weeks elapsed, THEN THE System SHALL allow graduation to Tier 3
5. THE System SHALL increase limits to $2,500 single execution and $12,500 daily volume at Tier 3
6. IF system is unprofitable for 2 consecutive months, THEN THE System SHALL reduce to previous tier
7. IF system is unprofitable for 3 consecutive months, THEN THE System SHALL initiate wind-down procedures

### Requirement 9: Historical Backtesting for Strategy Validation

**User Story:** As a MEV bot operator, I want to validate strategy profitability against historical data before deploying to mainnet, so that I can make informed go/no-go decisions based on realistic projections.

#### Acceptance Criteria

1. THE Backtest Engine SHALL collect minimum 30 days of historical liquidation events from Base mainnet
2. THE Backtest Engine SHALL replay each historical liquidation to determine if bot would have detected the opportunity
3. THE Backtest Engine SHALL calculate bot latency as detection_latency (500ms) plus build_latency (200ms)
4. THE Backtest Engine SHALL determine win probability by comparing bot latency against actual winner latency
5. THE Backtest Engine SHALL calculate net profit for each opportunity including all costs (gas, L1 data, bribe, flash loan, slippage)
6. THE Backtest Engine SHALL generate sensitivity analysis covering Optimistic, Base Case, Pessimistic, and Worst Case scenarios
7. WHEN Base Case annual ROI is below 100 percent OR win rate is below 15 percent, THEN THE System SHALL recommend STOP decision

### Requirement 10: Testnet Validation Before Mainnet Deployment

**User Story:** As a MEV bot operator, I want to validate all infrastructure and submission paths on testnet before mainnet deployment, so that operational issues are identified and resolved in a risk-free environment.

#### Acceptance Criteria

1. THE System SHALL execute minimum 50 liquidations on Base Sepolia testnet
2. THE System SHALL achieve inclusion rate above 60 percent sustained over 2-week period on testnet
3. THE System SHALL achieve simulation accuracy above 90 percent over 50+ executions on testnet
4. THE System SHALL achieve system uptime above 95 percent excluding planned maintenance on testnet
5. THE System SHALL test all submission paths (direct mempool, Base-native builders if available, private RPCs) and document performance characteristics
6. WHEN testnet validation criteria are met AND professional smart contract audit is completed with no high or critical findings, THEN THE System SHALL be approved for mainnet deployment
