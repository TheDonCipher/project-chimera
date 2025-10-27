# Design Document: MEV Liquidation Bot (Project Chimera)

## Overview

Project Chimera is a sophisticated MEV system architected for profitable liquidation execution on Base L2. The design follows a modular, safety-first approach with clear separation between on-chain execution (Solidity smart contract) and off-chain intelligence (Python agent).

### Design Principles

1. **Simulation-First**: Never execute without on-chain simulation validation
2. **Safety by Design**: Multiple layers of automated safety controls prevent catastrophic losses
3. **L2-Aware**: Explicitly handles Base L2 characteristics (L1 data costs, sequencer centralization)
4. **Gradual Scaling**: Conservative limit progression with validation gates
5. **Observable**: Complete audit trail and real-time metrics for all operations
6. **Resilient**: Graceful degradation and automatic recovery from transient failures

### Key Design Decisions

- **Python vs Rust/Go**: Python chosen for rapid development despite 100-500ms latency disadvantage
- **Block-Level Reconciliation**: State reconciliation every block to minimize divergence window
- **Stateless Contract**: Smart contract holds no token balances between transactions
- **Multi-RPC Architecture**: Three independent RPC connections provide redundancy

## Architecture

### System Components

The system consists of four main off-chain modules and one on-chain smart contract:

**Off-Chain Modules**:

1. **StateEngine**: Real-time blockchain state synchronization
2. **OpportunityDetector**: Liquidation opportunity identification
3. **ExecutionPlanner**: Transaction simulation and bundle construction
4. **SafetyController**: Limit enforcement and state management

**On-Chain Component**: 5. **Chimera Contract**: Atomic liquidation execution

### Data Flow

1. Base Sequencer produces blocks
2. WebSocket events received from RPC providers
3. StateEngine processes events and updates position cache
4. OpportunityDetector scans positions every 5 seconds
5. ExecutionPlanner simulates profitable opportunities
6. SafetyController validates execution is allowed
7. Bundle submitted to optimal submission path
8. Outcome tracked and metrics updated

## Components and Interfaces

### StateEngine Module

**Purpose**: Maintain authoritative, real-time view of blockchain state

**Key Responsibilities**:

- Subscribe to WebSocket block headers from multiple RPC providers
- Parse lending protocol events (Borrow, Repay, Liquidate)
- Maintain position cache in Redis with 60-second TTL
- Reconcile cached state vs canonical state every block
- Detect sequencer anomalies (block gaps, timestamp jumps)

**State Reconciliation**: Every block, compare cached position data against eth_call results. If divergence exceeds 10 basis points (0.1%), trigger HALT state immediately.

**Sequencer Health Monitoring**: Detect block gaps, timestamp jumps >20 seconds, and unusual reorg depths. Enter HALT state on anomaly detection.

### OpportunityDetector Module

**Purpose**: Identify liquidatable positions with minimal false positives

**Key Responsibilities**:

- Scan all positions every 5 seconds
- Calculate health factors using Chainlink oracle prices
- Apply multi-layer false positive filtering
- Estimate rough profitability before simulation

**Health Factor Calculation**:

```
health_factor = (collateral_amount * collateral_price * liquidation_threshold) / (debt_amount * debt_price)
Position is liquidatable when health_factor < 1.0
```

**Multi-Layer Filtering**:

1. Multi-oracle sanity check (skip if >5% divergence)
2. Price movement detection (skip if >30% in one block)
3. Confirmation blocks (require 2 blocks unhealthy)
4. Protocol state check (verify liquidation not paused)

### ExecutionPlanner Module

**Purpose**: Simulate transactions and construct profitable bundles

**Key Responsibilities**:

- Build complete transaction with Chimera contract call
- Simulate via eth_call (NEVER skip this step)
- Calculate L2 execution gas + L1 data posting costs
- Optimize builder bribe dynamically
- Submit to optimal submission path

**Base L2 Cost Calculation**:

```
l2_cost = gas_estimate * (base_fee + priority_fee)
l1_cost = calldata_size * l1_gas_price * l1_scalar
total_gas_cost = l2_cost + l1_cost
```

L1 data posting can be 30-50% of total gas cost. Fetch L1 scalar from Base system contracts at address 0x4200000000000000000000000000000000000015.

**Dynamic Bribe Optimization**:

- Start at 15% of gross profit
- Track inclusion rate over last 100 submissions
- Increase by 5% if inclusion <60%
- Decrease by 2% if inclusion >90%
- Cap at 40% maximum

### SafetyController Module

**Purpose**: Enforce operational limits and manage system state

**Key Responsibilities**:

- Maintain three-state machine (NORMAL/THROTTLED/HALTED)
- Enforce single execution and daily volume limits
- Track performance metrics (inclusion rate, simulation accuracy)
- Trigger automatic state transitions

**State Machine**:

- **NORMAL**: Full operation (100% execution rate)
- **THROTTLED**: Reduced operation (50% random skip)
- **HALTED**: No execution (manual intervention required)

**State Transitions**:

- NORMAL → THROTTLED: inclusion 50-60% OR accuracy 85-90%
- NORMAL → HALTED: inclusion <50% OR accuracy <85% OR failures ≥3
- THROTTLED → NORMAL: inclusion >60% AND accuracy >90%
- HALTED → NORMAL: Manual operator intervention only

**Limit Enforcement**:

- MAX_SINGLE_EXECUTION_USD: Tier 1 starts at $500
- MAX_DAILY_VOLUME_USD: Tier 1 starts at $2,500
- MIN_PROFIT_USD: $50 minimum
- MAX_CONSECUTIVE_FAILURES: 3 failures triggers HALT

### Chimera Smart Contract

**Purpose**: Execute atomic liquidations on-chain

**Key Responsibilities**:

- Execute flash loan → liquidate → swap → repay → profit sweep atomically
- Enforce access control (owner-only execution)
- Provide emergency pause mechanism
- Maintain stateless operation (no token storage)

**Security Patterns**:

- ReentrancyGuard: Prevents reentrancy attacks
- Ownable2Step: Requires new owner acceptance
- Pausable: Emergency stop mechanism
- SafeERC20: Handles non-standard token returns
- Stateless: No token balances stored between transactions

**Execution Flow**:

1. Validate inputs (non-zero addresses, positive amounts)
2. Request flash loan from Aave V3
3. In callback: approve → liquidate → swap → verify → repay → transfer profit
4. Emit LiquidationExecuted event
5. Return profit amount

## Data Models

### Position Model

- protocol: "moonwell" or "seamless"
- user: Ethereum address (checksummed)
- collateral_asset: Token address
- collateral_amount: Amount in wei
- debt_asset: Token address
- debt_amount: Amount in wei
- liquidation_threshold: Protocol-specific (0.75-0.85)
- last_update_block: Block number of last update
- blocks_unhealthy: Consecutive blocks with health_factor < 1.0

### Opportunity Model

- position: Position object
- health_factor: Calculated ratio
- collateral_price_usd: Current price
- debt_price_usd: Current price
- liquidation_bonus: Protocol-specific (0.05-0.10)
- estimated_gross_profit_usd: Rough estimate
- estimated_net_profit_usd: After costs
- detected_at_block: Block number
- detected_at_timestamp: Datetime

### Bundle Model

- opportunity: Opportunity object
- transaction: Transaction object
- simulated_profit_wei: From eth_call
- simulated_profit_usd: USD conversion
- gas_estimate: From eth_estimateGas
- l2_gas_cost_usd: L2 execution cost
- l1_data_cost_usd: L1 data posting cost
- bribe_usd: Builder bribe
- flash_loan_cost_usd: Premium cost
- slippage_cost_usd: DEX slippage
- total_cost_usd: Sum of all costs
- net_profit_usd: Simulated profit minus costs
- submission_path: "mempool", "builder", or "private_rpc"
- created_at: Datetime

### Execution Record Model

- timestamp, block_number, protocol, borrower
- collateral_asset, debt_asset, health_factor
- simulation_success, simulated_profit_wei, simulated_profit_usd
- bundle_submitted, tx_hash, submission_path, bribe_wei
- included, inclusion_block, actual_profit_wei, actual_profit_usd
- operator_address, state_at_execution, rejection_reason

## Error Handling

### Error Categories

**Transient Errors** (Automatic Retry):

- RPC connection timeout → Switch to backup provider
- WebSocket disconnection → Reconnect with exponential backoff
- Database connection loss → Queue operations, retry
- Temporary network issues → Retry with backoff (max 3 attempts)

**Recoverable Errors** (Log and Continue):

- Simulation failure → Log opportunity, skip execution
- Insufficient profit → Log rejection reason, continue
- Oracle price unavailable → Skip opportunity, continue
- Position already liquidated → Remove from cache, continue

**Critical Errors** (Enter HALTED State):

- State divergence >10 BPS → HALT, alert, rebuild state
- Sequencer anomaly detected → HALT, alert, wait for recovery
- Consecutive failures ≥3 → HALT, alert, investigate
- Smart contract revert pattern → HALT, alert, investigate

**Fatal Errors** (Shutdown Required):

- Configuration validation failure → Exit with error message
- Database schema mismatch → Exit with migration instructions
- Operator key compromise detected → HALT, alert, manual intervention
- Smart contract ownership lost → HALT, alert, emergency procedures

### Graceful Degradation

**RPC Provider Failure**:

- Primary WebSocket fails → Switch to backup WebSocket
- Both WebSockets fail → Fall back to HTTP polling
- All providers fail → Enter HALTED state, alert operators

**Database Unavailability**:

- PostgreSQL connection lost → Queue writes in memory (max 100 items)
- Queue full → Drop oldest non-critical logs, keep execution records
- Extended outage → Enter HALTED state after 5 minutes

**Redis Cache Unavailability**:

- Redis connection lost → Fall back to in-memory cache
- Increased memory usage → Monitor and alert if approaching limits
- Extended outage → Rebuild cache from blockchain on reconnection

## Testing Strategy

### Unit Testing

**Coverage Requirements**:

- Overall code coverage: >80%
- Critical paths (simulation, cost calculation, safety): >95%

**Test Categories**:

- StateEngine: Block processing, reconciliation, sequencer health
- OpportunityDetector: Health factor calculation, filtering, profit estimation
- ExecutionPlanner: Simulation parsing, cost calculation, bribe optimization
- SafetyController: State transitions, limit enforcement, metrics calculation

### Integration Testing

**Local Fork Testing**:

- Use Hardhat/Anvil to fork Base mainnet
- Replay 100+ historical liquidations
- Validate profit calculations match simulation
- Test all failure scenarios

**Component Integration**:

- StateEngine → OpportunityDetector data flow
- OpportunityDetector → ExecutionPlanner handoff
- ExecutionPlanner → SafetyController validation
- SafetyController → Database logging

### Smart Contract Testing

**Foundry Test Suite**:

- Unit tests for all functions (success and failure cases)
- Access control enforcement
- Reentrancy protection validation
- Pause mechanism testing
- Event emission verification
- > 95% code coverage required

**Fork Tests**:

- Complete liquidation on Base mainnet fork
- Flash loan integration (Aave V3, Balancer)
- DEX swap integration (Uniswap V3)
- Profit calculation accuracy

**Security Testing**:

- Slither static analysis
- Mythril symbolic execution
- Manual code review
- Professional audit (Trail of Bits, OpenZeppelin, or Consensys Diligence)

### Testnet Validation

**Base Sepolia Testing**:

- Deploy contract and verify on BaseScan
- Execute 50+ liquidations over 2-week period
- Measure inclusion rate (target: >60%)
- Measure simulation accuracy (target: >90%)
- Measure uptime (target: >95%)
- Test operational procedures (pause, resume, key rotation)

## Deployment Strategy

### Phase 1: Local Development (Weeks 1-12)

**Goal**: Prove strategy profitability via historical backtest

**Infrastructure**:

- Local development environment
- PostgreSQL database (Docker container)
- Redis cache (Docker container)
- Hardhat/Anvil for local fork testing

**Deliverables**:

- Complete codebase with >80% test coverage
- Smart contract with >95% test coverage
- Historical data collection (30 days of Base liquidations)
- Backtest report showing Base Case ROI >100%
- Sensitivity analysis

**Exit Criteria**:

- Base Case annual ROI >100%
- Win rate >15% in latency analysis
- All tests passing
- Audit budget secured ($15-30K)

### Phase 2: Testnet Validation (Weeks 13-20)

**Goal**: Validate infrastructure and submission paths

**Infrastructure**:

- AWS EC2 instance (t3.medium for testing)
- RDS PostgreSQL (db.t4g.small)
- ElastiCache Redis (cache.t4g.micro)
- Base Sepolia testnet

**Deliverables**:

- Contract deployed and verified on Base Sepolia
- Bot running continuously for 2 weeks
- 50+ successful liquidations executed
- Performance analysis report
- Professional smart contract audit completed

**Exit Criteria**:

- Inclusion rate >60% sustained
- Simulation accuracy >90%
- Uptime >95%
- Audit completed with no high/critical findings
- Capital prepared ($1,000-2,000)

### Phase 3: Mainnet Deployment (Week 21+)

**Goal**: Execute profitably at small scale, scale gradually

**Infrastructure**:

- AWS EC2 c7g.xlarge (ARM Graviton3)
- RDS PostgreSQL db.t4g.medium (Multi-AZ)
- ElastiCache Redis cache.t4g.small
- AWS Secrets Manager
- CloudWatch + PagerDuty
- Base mainnet

**Graduated Scaling Tiers**:

**Tier 1** ($500 single / $2,500 daily):

- Duration: Minimum 8 weeks
- Target: 100 successful executions
- Criteria: Net positive profit, >60% inclusion, zero incidents

**Tier 2** ($1,000 single / $5,000 daily):

- Duration: Minimum 12 weeks
- Target: 100 successful executions
- Criteria: $5K+ profit, >65% inclusion, >100% ROI

**Tier 3** ($2,500 single / $12,500 daily):

- Duration: Minimum 12 weeks
- Target: 50 successful executions
- Criteria: $3K+/month sustained, >70% inclusion

**Tier 4** ($5,000 single / $25,000 daily):

- Duration: Ongoing
- Criteria: Sustained profitability, consider partnerships

## Monitoring and Observability

### Real-Time Metrics Dashboard

**System Health**:

- Current state (NORMAL/THROTTLED/HALTED)
- Uptime percentage (7-day rolling)
- Last execution timestamp
- Operator wallet balance (ETH)
- Treasury balance (USD)

**Performance (24-hour window)**:

- Opportunities detected
- Bundles submitted
- Successful inclusions
- Win rate (%)
- Inclusion rate (%)
- Net profit (USD)

**Risk Metrics**:

- Consecutive failures (current count)
- Daily volume (current / limit)
- Reserve fund (% of target)
- State divergence events (count)

### Alerting Configuration

**CRITICAL** (Phone + SMS + PagerDuty):

- System entered HALTED state
- Security incident detected
- Operator balance <0.1 ETH
- Database unavailable >5 minutes
- Smart contract ownership changed

**HIGH** (SMS + PagerDuty):

- System entered THROTTLED state
- Inclusion rate <50%
- Simulation accuracy <85%
- Consecutive failures = 2
- Daily volume >90% of limit

**MEDIUM** (Email + Slack):

- Inclusion rate 50-60%
- Simulation accuracy 85-90%
- Daily volume >80% of limit
- Key rotation due in 7 days
- RPC provider degraded performance

**LOW** (Email):

- Daily performance summary
- Weekly report generated
- Monthly profitability analysis

### Logging Strategy

**Structured JSON Logs**: All logs written in JSON format for easy parsing

**Log Retention**:

- Hot storage (PostgreSQL): 3 years
- Cold storage (S3 Glacier): 7 years total
- Real-time logs (CloudWatch): 30 days

**Audit Trail**:

- Every execution attempt logged with complete context
- Immutable records (append-only)
- Cryptographic hash for integrity verification
- Export capability for compliance/legal review

## Security Considerations

### Threat Model

**Smart Contract Threats**:

- Reentrancy attacks → Mitigated by ReentrancyGuard
- Access control bypass → Mitigated by Ownable2Step
- Flash loan callback spoofing → Mitigated by caller verification
- Token approval exploits → Mitigated by exact approvals only
- Ownership transfer accidents → Mitigated by 2-step transfer

**Off-Chain Threats**:

- Operator key compromise → Mitigated by Secrets Manager, 90-day rotation, minimal balance
- RPC provider manipulation → Mitigated by multi-provider verification
- State divergence attacks → Mitigated by block-level reconciliation
- Database injection → Mitigated by parameterized queries
- Log tampering → Mitigated by cryptographic hashing

**Operational Threats**:

- Sequencer downtime → Mitigated by automatic HALT
- Oracle manipulation → Mitigated by multi-oracle sanity checks
- MEV competition → Mitigated by dynamic bribe optimization
- Gas price spikes → Mitigated by cost calculation and profitability checks
- Regulatory action → Mitigated by legal counsel, compliance documentation

### Security Best Practices

**Key Management**:

- Operator key stored in AWS Secrets Manager
- Treasury key on hardware wallet (Ledger/Trezor)
- 90-day key rotation schedule
- Never log or expose private keys
- IAM roles for AWS service authentication

**Network Security**:

- Bot deployed in private VPC subnet
- NAT gateway for outbound connections only
- Security groups restrict to necessary ports (443, 5432, 6379)
- TLS 1.3 for all external connections
- No direct internet access to bot instance

**Smart Contract Security**:

- Professional audit by reputable firm (mandatory)
- Comprehensive test suite (>95% coverage)
- Bug bounty program post-deployment
- Emergency pause mechanism
- Ownership via Gnosis Safe multisig

**Operational Security**:

- Role-based access control (RBAC)
- AWS CloudTrail audit logging
- MFA required for all AWS console access
- Encryption at rest (RDS, EBS)
- Encryption in transit (TLS)
- Regular security reviews

## Performance Optimization

### Latency Optimization

**Target Latency Breakdown**:

- Detection: <500ms (oracle update to opportunity identified)
- Simulation: <1000ms (includes RPC round-trip)
- Build: <200ms (transaction construction and signing)
- Total: <700ms (excluding simulation)

**Optimization Strategies**:

- Use WebSocket for real-time events (vs HTTP polling)
- Maintain hot cache in Redis (vs repeated RPC calls)
- Parallel oracle price fetching (vs sequential)
- Pre-compute gas estimates (vs on-demand)
- Connection pooling for database (vs new connections)
- Async/await for concurrent operations

### Resource Optimization

**Memory Management**:

- Position cache limited to active positions only
- Execution history limited to last 1000 records in memory
- Periodic garbage collection
- Monitor memory usage, alert if >6GB

**Database Optimization**:

- Indexes on frequently queried columns (timestamp, block_number, included)
- Partitioning for large tables (executions by month)
- Vacuum and analyze regularly
- Connection pooling (max 20 connections)

**Network Optimization**:

- Batch RPC calls where possible
- Compress WebSocket messages
- Use HTTP/2 for RPC connections
- Monitor bandwidth usage

## Future Enhancements

### Phase 4 Considerations (Month 13+)

**Performance Improvements**:

- Rust rewrite for 10x latency reduction
- Custom RPC node for zero-latency access
- Direct sequencer connection (if available)
- Hardware acceleration for signature generation

**Strategy Expansion**:

- Multi-chain support (Arbitrum, Optimism, Polygon)
- Additional MEV strategies (sandwich, arbitrage)
- Protocol partnerships for priority access
- Lending protocol integrations (Aave, Compound)

**Infrastructure Scaling**:

- Kubernetes deployment for high availability
- Multi-region deployment for redundancy
- Advanced monitoring (Datadog, New Relic)
- Machine learning for profit prediction

**Risk Management**:

- Dynamic limit adjustment based on volatility
- Portfolio diversification across chains
- Hedging strategies for market risk
- Insurance coverage for smart contract risk
