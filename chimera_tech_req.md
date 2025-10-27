# **Project Chimera: Technical Requirements Document**

**Document Type:** Technical Requirements Specification  
**Version:** 3.1  
**Date:** October 2025  
**Classification:** Internal - Technical Specification  
**Target Chain:** Base L2 (Optimism Stack)

---

## 1. Executive Summary

### 1.1 Project Overview

Project Chimera is a MEV (Maximal Extractable Value) system designed to execute profitable liquidations on Base L2 lending protocols. The system consists of an off-chain Python agent and an on-chain Solidity smart contract that work together to identify, simulate, and execute atomic liquidation transactions.

### 1.2 Success Criteria

**Phase 1 (Historical Validation):**
- Base Case annualized ROI >100% in backtest
- Win rate >15% of historical liquidation opportunities
- All automated tests passing with >80% code coverage

**Phase 2 (Testnet Validation):**
- Bundle inclusion rate >60% over 2-week period
- System uptime >95% (excluding planned maintenance)
- Simulation accuracy >90% (actual vs predicted profit)

**Phase 3 (Mainnet Operation):**
- Net positive cumulative profit after 100 executions
- Zero critical security incidents
- Graduated scaling to $5,000+ single execution limit

### 1.3 Risk Assessment

**Critical Risks:**
- Smart contract vulnerability leading to loss of funds (HIGH)
- Competition from faster bots reducing win rate below viability threshold (HIGH)
- Base sequencer downtime causing operational failures (MEDIUM)
- Regulatory action against MEV activities (MEDIUM)
- Alpha decay: strategy profitability degrading over time (MEDIUM)

**Mitigation Strategies:**
- Professional security audit by reputable firm ($15-30K budget)
- Conservative scaling with extensive validation at each tier
- Automated halt mechanisms for sequencer anomalies
- Legal counsel engagement before mainnet deployment
- Continuous profitability monitoring with clear pivot triggers

---

## 2. System Architecture

### 2.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   Off-Chain Agent (Python)              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │ StateEngine  │─▶│ Opportunity  │─▶│  Execution   │ │
│  │              │  │  Detector    │  │   Planner    │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│         │                  │                  │         │
│         └──────────────────┴──────────────────┘         │
│                           │                             │
│                  ┌────────▼────────┐                    │
│                  │ SafetyController│                    │
│                  └────────┬────────┘                    │
└───────────────────────────┼─────────────────────────────┘
                            │
                  ┌─────────▼──────────┐
                  │   RPC Providers    │
                  │ (Alchemy/QuickNode)│
                  └─────────┬──────────┘
                            │
                  ┌─────────▼──────────┐
                  │   Base Mainnet     │
                  │                    │
                  │  ┌──────────────┐  │
                  │  │ Chimera.sol  │  │
                  │  │  (Gnosis Safe│  │
                  │  │   Treasury)  │  │
                  │  └──────────────┘  │
                  └────────────────────┘
```

### 2.2 Component Specifications

#### 2.2.1 Off-Chain Agent

**Language:** Python 3.11+  
**Framework:** asyncio for concurrent operations  
**Runtime:** AWS EC2 c7g.xlarge (ARM Graviton3, 4 vCPU, 8GB RAM)  
**OS:** Ubuntu 22.04 LTS  

**Key Libraries:**
- web3.py 6.11.0 - Ethereum interactions
- eth-abi 4.2.1 - ABI encoding/decoding
- pandas 2.1.3 - Data analysis
- sqlalchemy 2.0.23 - Database ORM
- redis 5.0.1 - State caching

**Performance Requirements:**
- Detection latency: <500ms from oracle event to candidate identification
- Build latency: <200ms from detection to bundle submission
- Memory usage: <4GB steady state, <6GB peak
- CPU usage: <70% average, <90% peak

#### 2.2.2 On-Chain Smart Contract

**Language:** Solidity 0.8.24  
**Framework:** Foundry  
**Deployment:** Immutable contract with Gnosis Safe as owner  
**Gas Optimization:** Enabled with 200 runs  

**Security Features:**
- OpenZeppelin ReentrancyGuard
- OpenZeppelin Ownable for access control
- Emergency pause mechanism (owner only)
- No state storage (fully stateless operations)
- Explicit flash loan repayment checks

**Size Constraint:** <24KB deployed bytecode

#### 2.2.3 Infrastructure Components

**Database:** Amazon RDS PostgreSQL 15 (db.t4g.medium, Multi-AZ)  
**Cache:** Amazon ElastiCache Redis 7 (cache.t4g.small)  
**Secrets:** AWS Secrets Manager with IAM role-based access  
**Monitoring:** AWS CloudWatch + PagerDuty for alerting  
**Logging:** Structured JSON logs to PostgreSQL (3-year retention)

---

## 3. Functional Requirements

### 3.1 StateEngine Module

**REQ-SE-001: Real-Time Block Monitoring**
- MUST subscribe to WebSocket block headers within 2 seconds of connection
- MUST process new blocks within 500ms of receipt
- MUST maintain connection with automatic reconnection on failure
- MUST handle WebSocket disconnection gracefully without data loss

**REQ-SE-002: State Reconciliation**
- MUST reconcile cached state against canonical chain state every 1 block
- MUST compare cached values against eth_call results from archive node
- MUST calculate divergence as: `|cached - canonical| / canonical * 10000` (basis points)
- MUST trigger HALT if divergence exceeds 10 basis points (0.1%)

**REQ-SE-003: Event Processing**
- MUST parse Borrow, Repay, Liquidate, and oracle price update events
- MUST update internal position cache within 100ms of event receipt
- MUST store event checkpoints every 10 blocks for recovery
- MUST detect and handle chain reorganizations (reorgs)

**REQ-SE-004: Sequencer Health Monitoring**
- MUST verify sequential block numbers (no gaps)
- MUST verify block timestamps are sequential
- MUST detect timestamp jumps >20 seconds as sequencer anomaly
- MUST enter HALT state on sequencer anomaly detection

**REQ-SE-005: Multi-RPC Redundancy**
- MUST maintain connections to minimum 2 RPC providers
- MUST failover to backup RPC within 5 seconds of primary failure
- MUST log all RPC failures and latency >500ms
- MUST distribute read load across providers for non-critical queries

### 3.2 OpportunityDetector Module

**REQ-OD-001: Position Scanning**
- MUST scan all known positions every 5 seconds maximum
- MUST calculate health factor as: `(collateral_value * liquidation_threshold) / debt_value`
- MUST identify positions where health_factor < 1.0 as liquidatable
- MUST maintain position list from lending protocol events

**REQ-OD-002: Oracle Integration**
- MUST use Chainlink as primary oracle for speed (detection phase)
- MUST fetch secondary oracle price (Pyth or Redstone) for sanity check
- MUST flag opportunity for review if oracle divergence >5%
- MUST reject opportunity if primary oracle price moved >30% in one block

**REQ-OD-003: False Positive Filtering**
- MUST reject positions that have been unhealthy for <2 blocks
- MUST reject positions with estimated profit <$50 USD
- MUST reject positions where protocol liquidation function is paused
- MUST maintain false positive rate <10%

**REQ-OD-004: Profitability Estimation**
- MUST estimate liquidation bonus based on protocol parameters
- MUST estimate collateral value using current oracle prices
- MUST estimate arbitrage profit based on DEX liquidity
- MUST calculate rough cost estimate (gas + bribes + fees)
- MUST skip opportunities where estimated net profit <$50

### 3.3 ExecutionPlanner Module

**REQ-EP-001: Transaction Construction**
- MUST build complete transaction with all parameters (nonce, gas, data)
- MUST use Chimera contract's executeLiquidation function
- MUST include minProfit parameter set to 50% of estimated profit
- MUST set gas limit based on simulation results + 10% buffer

**REQ-EP-002: On-Chain Simulation (CRITICAL)**
- MUST simulate ALL transactions via eth_call before submission
- MUST parse simulation result to extract actual profit amount
- MUST verify simulation success before proceeding
- MUST reject opportunity if simulation fails or shows <$50 profit
- MUST NEVER execute without successful simulation

**REQ-EP-003: Cost Calculation**
- MUST calculate L2 execution gas cost: `gas_estimate * (base_fee + priority_fee)`
- MUST calculate L1 data posting cost: `calldata_size * L1_gas_price * L1_scalar`
- MUST fetch L1 scalar from Base system contracts
- MUST calculate builder bribe as percentage of gross profit
- MUST calculate flash loan premium (0.05-0.09% depending on protocol)
- MUST budget 1% slippage for DEX swaps
- MUST calculate total cost in USD using real-time ETH/USD oracle

**REQ-EP-004: Profitability Validation**
- MUST calculate net profit: `simulated_profit - (L2_gas + L1_data + bribe + flash_loan + slippage)`
- MUST reject if net_profit < $50 USD
- MUST log all rejected opportunities with reason
- MUST track rejection reasons for strategy optimization

**REQ-EP-005: Dynamic Bribe Optimization**
- MUST start with 15% of gross profit as baseline bribe
- MUST track inclusion rate over last 100 submissions per submission path
- MUST increase bribe by 5% if inclusion rate <60%
- MUST decrease bribe by 2% if inclusion rate >90%
- MUST cap bribe at 40% of gross profit (reject opportunity if needed)
- MUST update bribe model every 100 submissions

**REQ-EP-006: Bundle Submission**
- MUST sign transaction with operator private key from Secrets Manager
- MUST submit to all available submission paths simultaneously if economics allow
- MUST track submission timestamp and block number
- MUST log complete bundle details (transaction hash, bribe amount, expected profit)
- MUST implement retry logic with exponential backoff (max 3 retries)

**REQ-EP-007: Submission Path Management**
- MUST implement adapters for: direct mempool, Base-native builders (if available), private RPCs
- MUST test all paths on testnet and document performance characteristics
- MUST select optimal path based on: `EV = (profit * inclusion_rate) - (bribe + fees)`
- MUST failover to alternative path if primary fails

### 3.4 SafetyController Module

**REQ-SC-001: Limit Enforcement**
- MUST enforce MAX_SINGLE_EXECUTION_USD before every execution
- MUST enforce MAX_DAILY_VOLUME_USD with daily reset at midnight UTC
- MUST enforce MIN_PROFIT_USD as minimum acceptable net profit
- MUST reject executions that would violate any limit
- MUST log all limit violations with opportunity details

**REQ-SC-002: State Machine Management**
- MUST maintain three states: NORMAL, THROTTLED, HALTED
- MUST allow execution in NORMAL state
- MUST randomly skip 50% of executions in THROTTLED state
- MUST block ALL executions in HALTED state
- MUST require manual operator intervention to resume from HALTED

**REQ-SC-003: Performance Monitoring**
- MUST track inclusion rate over last 100 submissions
- MUST track simulation accuracy over last 100 successful executions
- MUST track consecutive failure count (resets on success)
- MUST calculate simulation accuracy as: `actual_profit / simulated_profit`
- MUST recalculate metrics every 10 minutes

**REQ-SC-004: Automatic State Transitions**
- MUST enter HALTED if: inclusion_rate <50% OR simulation_accuracy <85% OR consecutive_failures >=3
- MUST enter THROTTLED if: inclusion_rate 50-60% OR simulation_accuracy 85-90%
- MUST enter NORMAL if: inclusion_rate >60% AND simulation_accuracy >90% AND consecutive_failures <3
- MUST log state transitions with triggering reason
- MUST send alerts on THROTTLED or HALTED transitions

**REQ-SC-005: Execution Tracking**
- MUST record every execution attempt with: timestamp, opportunity details, simulation result, actual result
- MUST update consecutive failure count on submission
- MUST reset consecutive failures on successful inclusion
- MUST maintain execution history for performance analysis
- MUST persist execution records to PostgreSQL within 1 second

### 3.5 Smart Contract (Chimera.sol)

**REQ-SC-001: Liquidation Execution**
- MUST accept parameters: lending_protocol, borrower, collateral_asset, debt_asset, debt_amount, min_profit
- MUST execute atomically: flash_loan → liquidate → swap → repay_loan → sweep_profit
- MUST revert entire transaction if any step fails
- MUST transfer all profits to treasury address
- MUST emit LiquidationExecuted event with: protocol, borrower, profit_amount, gas_used

**REQ-SC-002: Flash Loan Integration**
- MUST support Aave V3 flash loans as primary provider
- MUST support Balancer flash loans as backup provider
- MUST calculate exact repayment amount including premium
- MUST revert if insufficient funds to repay flash loan
- MUST implement IFlashLoanReceiver interface correctly

**REQ-SC-003: DEX Integration**
- MUST support Uniswap V3 for collateral swaps
- MUST support Aerodrome (if available on Base) as backup
- MUST set minimum output amount to prevent sandwich attacks
- MUST use exact input swap for predictable gas costs
- MUST approve DEX router only for exact swap amount (no infinite approvals)

**REQ-SC-004: Access Control**
- MUST restrict executeLiquidation to owner only
- MUST restrict pause/unpause to owner only
- MUST restrict setTreasury to owner only
- MUST use OpenZeppelin Ownable2Step for ownership transfer
- MUST emit events for all access-controlled actions

**REQ-SC-005: Emergency Controls**
- MUST implement pause mechanism that blocks executeLiquidation
- MUST allow pause to be called by owner instantly (no timelock)
- MUST allow unpause only by owner
- MUST NOT allow fund withdrawal via emergency functions (no rug vector)
- MUST implement rescueTokens function for mistaken transfers only

**REQ-SC-006: Security Requirements**
- MUST use ReentrancyGuard on executeLiquidation function
- MUST validate all external call return values
- MUST use SafeERC20 for token transfers
- MUST NOT store token balances between transactions (stateless)
- MUST NOT have selfdestruct or delegatecall functionality

---

## 4. Non-Functional Requirements

### 4.1 Performance Requirements

**REQ-PERF-001: Latency**
- Target total latency (oracle update to bundle submission): <700ms
- Detection latency: <500ms
- Build latency: <200ms
- Simulation latency: <1000ms (includes RPC round-trip)

**REQ-PERF-002: Throughput**
- MUST handle 10+ opportunities per minute during high activity
- MUST process 100+ positions per scan cycle
- MUST support 1000+ transactions logged per day

**REQ-PERF-003: Resource Usage**
- CPU: <70% average, <90% peak on c7g.xlarge
- Memory: <4GB average, <6GB peak
- Database: <100GB storage per year of logs
- Network: <1GB/day bandwidth

### 4.2 Reliability Requirements

**REQ-REL-001: Availability**
- Target uptime: 99.5% (excluding planned maintenance)
- Maximum unplanned downtime: 30 minutes per incident
- Maximum planned maintenance: 2 hours per month
- Recovery Time Objective (RTO): <5 minutes for automatic recovery

**REQ-REL-002: Fault Tolerance**
- MUST survive single RPC provider failure without downtime
- MUST survive WebSocket disconnection with automatic reconnection
- MUST survive database connection loss with automatic reconnection
- MUST queue operations during temporary failures (max queue: 100 items)

**REQ-REL-003: Data Integrity**
- MUST persist all execution records to PostgreSQL with ACID guarantees
- MUST use Multi-AZ database with automated failover
- MUST maintain automated backups with 7-day retention
- MUST verify data integrity via checksums on critical records

### 4.3 Security Requirements

**REQ-SEC-001: Key Management**
- MUST store operator private key in AWS Secrets Manager
- MUST rotate operator key every 90 days
- MUST use IAM roles for AWS service authentication (no long-lived credentials)
- MUST store treasury key on hardware wallet (Ledger or Trezor)
- MUST NEVER log or expose private keys in any form

**REQ-SEC-002: Network Security**
- MUST deploy bot in private VPC subnet (no direct internet access)
- MUST use NAT gateway for outbound connections only
- MUST restrict security groups to necessary ports only (443, 5432, 6379)
- MUST use TLS 1.3 for all external connections
- MUST implement rate limiting on API endpoints (if exposed)

**REQ-SEC-003: Smart Contract Security**
- MUST complete professional security audit before mainnet deployment
- MUST remediate all high and critical findings
- MUST implement comprehensive test suite (>80% coverage)
- MUST verify contract source code on BaseScan
- MUST use established patterns (OpenZeppelin libraries)

**REQ-SEC-004: Operational Security**
- MUST implement role-based access control for infrastructure
- MUST enable AWS CloudTrail for audit logging
- MUST require MFA for all AWS console access
- MUST encrypt all data at rest (RDS, EBS volumes)
- MUST encrypt all data in transit (TLS)

### 4.4 Monitoring and Observability

**REQ-MON-001: Metrics Collection**
- MUST collect metrics every 60 seconds: state, volume, failures, latency, inclusion rate
- MUST export metrics to CloudWatch
- MUST maintain 30-day metrics history
- MUST create dashboard with all key metrics visible

**REQ-MON-002: Alerting**
- MUST send CRITICAL alerts (phone + SMS) for: HALTED state, security incident, operator balance <0.1 ETH
- MUST send HIGH alerts (SMS) for: THROTTLED state, inclusion <50%, 3 consecutive failures
- MUST send MEDIUM alerts (email) for: inclusion 50-60%, approaching limits, key rotation due
- MUST integrate with PagerDuty for on-call rotation

**REQ-MON-003: Logging**
- MUST log all opportunities (detected, accepted, rejected) with full details
- MUST log all executions (submitted, included, failed) with transaction data
- MUST log all state transitions with triggering conditions
- MUST log all errors with stack traces
- MUST use structured logging (JSON format) for parsing
- MUST persist logs to PostgreSQL with 3-year retention

**REQ-MON-004: Audit Trail**
- MUST create immutable record of every execution attempt
- MUST include: timestamp, block, opportunity, simulation, costs, actual outcome
- MUST sign log records with cryptographic hash for integrity
- MUST enable export of audit trail for compliance/legal review

### 4.5 Compliance and Legal

**REQ-COMP-001: Legal Framework**
- MUST obtain legal opinion on market manipulation before mainnet
- MUST obtain legal opinion on securities law implications
- MUST implement geo-blocking if counsel advises
- MUST maintain legal compliance folder with all documentation

**REQ-COMP-002: Data Retention**
- MUST retain all transaction logs for minimum 3 years
- MUST retain all audit trails for minimum 3 years
- MUST enable log export in standard formats (CSV, JSON)
- MUST protect logs from deletion or tampering

**REQ-COMP-003: Transparency**
- SHOULD publish quarterly transparency reports (if pursuing partnerships)
- SHOULD open-source non-critical components (if pursuing partnerships)
- SHOULD maintain public dashboard (if pursuing partnerships)

---

## 5. Data Requirements

### 5.1 Database Schema

**Table: executions**
```sql
CREATE TABLE executions (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    
    -- Opportunity
    protocol VARCHAR(50) NOT NULL,
    borrower VARCHAR(42) NOT NULL,
    collateral_asset VARCHAR(42) NOT NULL,
    debt_asset VARCHAR(42) NOT NULL,
    health_factor DECIMAL(18,6),
    
    -- Simulation
    simulation_success BOOLEAN,
    simulated_profit_wei NUMERIC(78,0),
    simulated_profit_usd DECIMAL(18,2),
    gas_estimate INTEGER,
    
    -- Execution
    bundle_submitted BOOLEAN,
    tx_hash VARCHAR(66),
    submission_path VARCHAR(50),
    bribe_wei NUMERIC(78,0),
    
    -- Outcome
    included BOOLEAN,
    inclusion_block BIGINT,
    actual_profit_wei NUMERIC(78,0),
    actual_profit_usd DECIMAL(18,2),
    gas_used INTEGER,
    
    -- Metadata
    operator_address VARCHAR(42),
    state_at_execution VARCHAR(20),
    
    CONSTRAINT chk_simulation CHECK (
        simulation_success IS NOT NULL OR bundle_submitted = false
    )
);

CREATE INDEX idx_timestamp ON executions(timestamp);
CREATE INDEX idx_block ON executions(block_number);
CREATE INDEX idx_included ON executions(included);
CREATE INDEX idx_protocol ON executions(protocol);
```

**Table: state_divergences**
```sql
CREATE TABLE state_divergences (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    block_number BIGINT NOT NULL,
    divergence_bps INTEGER NOT NULL,
    position_key VARCHAR(100),
    cached_value NUMERIC(78,0),
    canonical_value NUMERIC(78,0),
    action_taken VARCHAR(50)
);
```

**Table: performance_metrics**
```sql
CREATE TABLE performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL,
    metric_window VARCHAR(20), -- '1h', '24h', '7d'
    
    opportunities_detected INTEGER,
    bundles_submitted INTEGER,
    bundles_included INTEGER,
    inclusion_rate DECIMAL(5,2),
    
    avg_simulated_profit DECIMAL(18,2),
    avg_actual_profit DECIMAL(18,2),
    simulation_accuracy DECIMAL(5,2),
    
    total_gross_profit DECIMAL(18,2),
    total_net_profit DECIMAL(18,2),
    
    state VARCHAR(20)
);
```

### 5.2 Cache Schema (Redis)

**Keys:**
- `state:positions:{protocol}:{user}` → Position data (TTL: 300s)
- `state:oracle:{asset}` → Oracle price (TTL: 60s)
- `state:block:latest` → Latest processed block number (TTL: 30s)
- `state:sequencer:health` → Sequencer health status (TTL: 30s)
- `metrics:inclusion_rate` → Rolling inclusion rate (TTL: 3600s)
- `metrics:consecutive_failures` → Current failure streak (TTL: 3600s)

### 5.3 Configuration Management

**Configuration loaded from:**
1. Environment variables (.env file or AWS Secrets Manager)
2. Configuration file (config.yaml for static settings)
3. Database (for dynamic settings that can be updated without restart)

**Critical configuration parameters:**
```yaml
limits:
  max_single_execution_usd: 500  # Start value
  max_daily_volume_usd: 2500
  min_profit_usd: 50

thresholds:
  min_inclusion_rate: 0.60
  min_simulation_accuracy: 0.90
  max_consecutive_failures: 3
  max_state_divergence_bps: 10

bribe:
  base_percentage: 0.15
  max_percentage: 0.40
  adjustment_window: 100

timing:
  scan_interval_seconds: 5
  reconciliation_interval_blocks: 1
  metrics_update_interval_seconds: 600
```

---

## 6. Integration Requirements

### 6.1 External Systems

**REQ-INT-001: RPC Providers**
- MUST integrate with Alchemy (primary) and QuickNode (backup)
- MUST support WebSocket and HTTPS endpoints
- MUST implement automatic failover between providers
- MUST monitor provider health (latency, error rate)

**REQ-INT-002: Blockchain Protocols**
- MUST integrate with Base mainnet (Chain ID: 8453)
- MUST integrate with Base Sepolia testnet (Chain ID: 84532)
- MUST support protocol-specific interfaces: Moonwell, Seamless Protocol
- MUST adapt to protocol upgrades with configuration updates (no code changes)

**REQ-INT-003: Oracle Networks**
- MUST integrate with Chainlink price feeds on Base
- MUST integrate with secondary oracle (Pyth or Redstone)
- MUST handle oracle update lag and staleness
- MUST implement fallback if oracle unreachable

**REQ-INT-004: DEX Protocols**
- MUST integrate with Uniswap V3 on Base
- MUST integrate with backup DEX (Aerodrome or similar)
- MUST fetch liquidity data for slippage estimation
- MUST handle DEX-specific fee tiers

**REQ-INT-005: Flash Loan Providers**
- MUST integrate with Aave V3 flash loans (primary)
- MUST integrate with Balancer flash loans (backup)
- MUST correctly calculate repayment amounts
- MUST handle flash loan failures gracefully

### 6.2 Monitoring and Alerting

**REQ-INT-006: CloudWatch Integration**
- MUST send custom metrics to CloudWatch every 60 seconds
- MUST create alarms for critical thresholds
- MUST maintain 30-day metric retention
- MUST use CloudWatch Logs for aggregated logging

**REQ-INT-007: PagerDuty Integration**
- MUST send critical alerts to PagerDuty with severity levels
- MUST include context (state, metrics, error details) in alerts
- MUST implement acknowledgment tracking
- MUST escalate unacknowledged critical alerts after 5 minutes

---

## 7. Testing Requirements

### 7.1 Unit Testing

**REQ-TEST-001: Code Coverage**
- MUST achieve >80% code coverage for all modules
- MUST achieve >95% coverage for critical paths (simulation, cost calculation, safety checks)
- MUST use pytest with coverage reporting
- MUST fail CI/CD pipeline if coverage drops below threshold

**REQ-TEST-002: Test Categories**
- MUST test all state transitions in SafetyController
- MUST test reconciliation logic with mock divergence
- MUST test cost calculations with various gas prices
- MUST test bribe optimization algorithm
- MUST test limit enforcement edge cases

### 7.2 Integration Testing

**REQ-TEST-003: Local Fork Testing**
- MUST test against mainnet fork using Hardhat/Anvil
- MUST replay 100+ historical liquidations
- MUST validate profit calculations match simulation
- MUST test all failure scenarios (reverts, insufficient balance, etc.)

**REQ-TEST-004: Testnet Testing**
- MUST execute 50+ liquidations on Base Sepolia
- MUST test all submission paths
- MUST validate monitoring and alerting
- MUST test operational procedures (pause, resume, key rotation)

### 7.3 Smart Contract Testing

**REQ-TEST-005: Foundry Tests**
- MUST achieve >95% code coverage
- MUST test all functions (success and failure cases)
- MUST test access control enforcement
- MUST test reentrancy protection
- MUST test pause mechanism
- MUST fuzz test numerical calculations

**REQ-TEST-006: Security Testing**
- MUST complete professional security audit
- MUST run Slither, Mythril, and other automated tools
- MUST test against OWASP Smart Contract Top 10 vulnerabilities
- MUST perform manual code review by senior Solidity developer

### 7.4 Performance Testing

**REQ-TEST-007: Load Testing**
- MUST test bot under 100+ opportunities per minute
- MUST verify latency requirements met under load
- MUST verify memory usage stays within limits
- MUST verify database can handle sustained write load

**REQ-TEST-008: Stress Testing**
- MUST test failover scenarios (RPC failure, DB failure, network partition)
- MUST test recovery from crashes
- MUST test behavior during sequencer downtime
- MUST test behavior during extreme gas price spikes

---

## 8. Deployment Requirements

### 8.1 Infrastructure as Code

**REQ-DEP-001: Terraform Configuration**
- MUST define all AWS resources in Terraform
- MUST use separate configurations for testnet and mainnet
- MUST enable state locking with DynamoDB
- MUST version control all infrastructure code

**REQ-DEP-002: CI/CD Pipeline**
- MUST implement automated testing on every commit
- MUST build Docker images for bot deployment
- MUST automate deployment to staging environment
- MUST require manual approval for production deployment

### 8.2 Deployment Procedure

**REQ-DEP-003: Mainnet Deployment Checklist**
- [ ] Smart contract audit completed (no high/critical findings)
- [ ] All tests passing (unit, integration, security)
- [ ] Testnet validation successful (2 weeks, >60% inclusion)
- [ ] Infrastructure deployed and tested
- [ ] Monitoring and alerting validated
- [ ] Operator and treasury wallets configured
- [ ] Contract deployed and verified on BaseScan
- [ ] Contract immediately paused after deployment
- [ ] Operator wallet funded with 0.5 ETH
- [ ] Legal opinions obtained
- [ ] Team trained on operational procedures

**REQ-DEP-004: Rollback Procedure**
- MUST have documented procedure to pause contract
- MUST have documented procedure to withdraw funds to treasury
- MUST have documented procedure to shut down bot
- MUST maintain previous working version for quick rollback

---

## 9. Operational Requirements

### 9.1 Daily Operations

**REQ-OPS-001: Monitoring**
- MUST check dashboard every morning
- MUST review overnight alerts
- MUST verify operator wallet balance >0.3 ETH
- MUST verify system state is NORMAL

**REQ-OPS-002: Weekly Reviews**
- MUST generate weekly performance report
- MUST analyze inclusion rate and simulation accuracy trends
- MUST review cost breakdown
- MUST assess if graduation criteria met

### 9.2 Maintenance

**REQ-OPS-003: Key Rotation**
- MUST rotate operator key every 90 days
- MUST follow documented rotation procedure
- MUST verify new key working before deactivating old key
- MUST maintain calendar reminders for rotation

**REQ-OPS-004: Software Updates**
- MUST apply security patches within 7 days of release
- MUST test updates on testnet before mainnet
- MUST schedule maintenance windows for updates
- MUST notify team of planned maintenance

### 9.3 Incident Response

**REQ-OPS-005: Incident Procedures**
- MUST have documented runbooks for: HALTED state, key compromise, sequencer outage, sustained losses
- MUST conduct incident post-mortems within 48 hours
- MUST implement improvements from lessons learned within 1 week
- MUST maintain incident log with root cause analysis

**REQ-OPS-006: Emergency Contacts**
- MUST maintain 24/7 on-call rotation
- MUST have escalation path for critical incidents
- MUST have contact information for: auditors, legal counsel, infrastructure providers
- MUST test emergency procedures quarterly

---

## 10. Acceptance Criteria

### 10.1 Phase 1 Completion (Historical Validation)

**MUST demonstrate ALL of the following:**
- [ ] Backtest report showing Base Case annual ROI >100%
- [ ] Sensitivity analysis covering Optimistic/Base/Pessimistic/Worst scenarios
- [ ] Latency analysis proving bot can win >15% of historical opportunities
- [ ] Smart contract compiling without warnings
- [ ] All unit tests passing with >80% coverage
- [ ] Integration tests passing on local fork
- [ ] Security scan (Slither/Mythril) showing no critical issues
- [ ] Professional audit firm engaged and deposit paid

**EXIT CRITERIA:**
- If Base Case ROI <50%: STOP, strategy not viable
- If win rate <10%: STOP, competition too intense
- If critical contract vulnerability found: STOP, fix before proceeding

### 10.2 Phase 2 Completion (Testnet Validation)

**MUST demonstrate ALL of the following:**
- [ ] 50+ successful liquidations on Base Sepolia
- [ ] Inclusion rate >60% sustained over 2 weeks
- [ ] Simulation accuracy >90% over 50+ executions
- [ ] System uptime >95% (excluding planned maintenance)
- [ ] Zero unrecoverable failures requiring manual intervention
- [ ] All submission paths tested and documented
- [ ] Smart contract professionally audited with no high/critical findings remaining
- [ ] Infrastructure deployed and monitored
- [ ] Operational runbooks complete and tested
- [ ] Weekly performance reports generated successfully

**EXIT CRITERIA:**
- If inclusion rate <50%: REFINE submission strategy or STOP
- If simulation accuracy <85%: REFINE cost model or STOP
- If audit reveals critical vulnerabilities: REMEDIATE before mainnet
- If uptime <90%: FIX infrastructure before mainnet

### 10.3 Phase 3 Tier 1 Completion ($500 Limit)

**MUST demonstrate ALL of the following:**
- [ ] 100 successful mainnet executions at $500 limit
- [ ] Cumulative net profit >$0 (any positive amount)
- [ ] Inclusion rate >60% sustained
- [ ] Simulation accuracy >90% sustained
- [ ] Zero critical security incidents
- [ ] Zero critical infrastructure failures
- [ ] Minimum 8 weeks of operation elapsed
- [ ] Monthly performance reports showing positive trend

**GRADUATION CRITERIA:**
- All above criteria met → Advance to Tier 2 ($1,000 limit)
- Criteria not met after 12 weeks → HOLD, investigate issues
- Net negative profit after 12 weeks → STOP or revert to lower limit

### 10.4 Phase 3 Tier 2 Completion ($1,000 Limit)

**MUST demonstrate ALL of the following:**
- [ ] 100 successful executions at $1,000 limit
- [ ] Cumulative net profit >$5,000
- [ ] Inclusion rate >65% sustained
- [ ] Simulation accuracy >92% sustained
- [ ] Annualized ROI >100% based on actual performance
- [ ] Zero critical incidents
- [ ] Minimum 12 weeks of operation elapsed
- [ ] Reserve fund maintained at 30% target

**GRADUATION CRITERIA:**
- All above criteria met → Advance to Tier 3 ($2,500 limit)
- Criteria not met after 16 weeks → HOLD, optimize strategy
- ROI <50% sustained → STOP, wind down operations

### 10.5 Phase 3 Tier 3 Completion ($2,500 Limit)

**MUST demonstrate ALL of the following:**
- [ ] 50 successful executions at $2,500 limit
- [ ] Monthly profit >$3,000 sustained for 3 months
- [ ] Inclusion rate >70% sustained
- [ ] Strong operational track record (no major incidents)
- [ ] Minimum 12 weeks of operation elapsed
- [ ] Team confident in scalability to Tier 4

**GRADUATION CRITERIA:**
- All above criteria met → Advance to Tier 4 ($5,000 limit)
- Criteria not met after 16 weeks → HOLD at Tier 3
- Margins compressing despite optimization → EVALUATE pivot strategies

---

## 11. Risk Register

### 11.1 Technical Risks

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| RISK-T-001 | Smart contract vulnerability exploited | Low | Critical | Professional audit, bug bounty, formal verification |
| RISK-T-002 | State divergence causing invalid executions | Medium | High | Block-level reconciliation, automatic halt on divergence |
| RISK-T-003 | RPC provider failure during critical execution | Medium | Medium | Multi-provider redundancy, automatic failover |
| RISK-T-004 | Database corruption or loss | Low | High | Multi-AZ deployment, automated backups, replication |
| RISK-T-005 | Key compromise (operator private key) | Low | High | Secrets Manager, HSM, 90-day rotation, minimal balance |
| RISK-T-006 | Python performance insufficient vs Rust competitors | High | Medium | Focus on slower opportunities, consider Rust rewrite in Phase 4 |
| RISK-T-007 | Flash loan provider failure | Low | Medium | Multiple flash loan sources, graceful degradation |
| RISK-T-008 | DEX liquidity insufficient causing high slippage | Medium | Medium | Liquidity checks before execution, dynamic slippage tolerance |

### 11.2 Operational Risks

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| RISK-O-001 | Base sequencer extended downtime | Medium | High | Automatic halt on sequencer anomaly, monitor status page |
| RISK-O-002 | Operator unavailable during critical incident | Low | Medium | 24/7 on-call rotation, automated procedures, clear runbooks |
| RISK-O-003 | Monitoring/alerting failure hiding issues | Low | High | Redundant alerting, daily manual checks, uptime monitoring |
| RISK-O-004 | Infrastructure cost exceeding revenue | Medium | High | Monthly cost review, automated budget alerts, cost optimization |
| RISK-O-005 | Operator error during manual intervention | Medium | Medium | Documented procedures, dry-run testing, peer review |

### 11.3 Market Risks

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| RISK-M-001 | Alpha decay: strategy profitability degrading | High | Critical | Monthly ROI tracking, clear pivot triggers, alternative strategies |
| RISK-M-002 | Competition intensifying reducing win rate | High | High | Dynamic bribe optimization, focus on efficiency, partnerships |
| RISK-M-003 | Base liquidation volume insufficient | Medium | Critical | Validated in Phase 1 backtest, pivot to other chains if needed |
| RISK-M-004 | Gas price spikes making executions unprofitable | Medium | Medium | Dynamic gas limits, skip during extreme spikes, L1 cost monitoring |
| RISK-M-005 | Lending protocol changes breaking integration | Low | High | Monitor protocol governance, test against upgrades, maintainer relationships |
| RISK-M-006 | Oracle manipulation triggering false liquidations | Low | High | Multi-oracle sanity checks, manipulation detection heuristics |

### 11.4 Regulatory Risks

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| RISK-R-001 | MEV activities deemed market manipulation | Low | Critical | Legal opinions before launch, compliance documentation, geographic restrictions |
| RISK-R-002 | Cease and desist from financial regulator | Low | Critical | Legal monitoring, immediate wind-down procedure, preserved records |
| RISK-R-003 | Tax implications unclear or adverse | Medium | Medium | Engage crypto tax specialist, maintain detailed records, set aside reserves |
| RISK-R-004 | Protocol teams blocking known liquidators | Medium | High | Maintain good reputation, pursue partnerships, offer value-add services |

### 11.5 Financial Risks

| Risk ID | Description | Probability | Impact | Mitigation |
|---------|-------------|-------------|--------|------------|
| RISK-F-001 | Sustained losses depleting capital | Medium | High | 30% reserve fund, automatic halt at 20% loss, strict limit enforcement |
| RISK-F-002 | Large single loss from bug or exploit | Low | Critical | Limit enforcement, simulation validation, professional audit |
| RISK-F-003 | Gas costs exceeding profit consistently | Medium | High | Dynamic cost calculation, skip unprofitable opportunities, L1 monitoring |
| RISK-F-004 | Bribe costs spiraling due to competition | High | Medium | Dynamic bribe cap at 40%, reject if unprofitable, track competition |

---

## 12. Constraints and Assumptions

### 12.1 Technical Constraints

**CONSTRAINT-001: Language Choice**
- Bot implemented in Python 3.11+ (not Rust/Go)
- Acknowledged: 100-500ms latency disadvantage vs optimized competitors
- Mitigation: Focus on opportunities where speed advantage is less critical

**CONSTRAINT-002: Chain Support**
- Initial deployment: Base L2 only
- No multi-chain support in Phase 1-3
- Expansion to other chains contingent on Phase 3 success

**CONSTRAINT-003: Capital Requirements**
- Minimum $10,000 capital for meaningful operation
- $1,000-2,000 for Phase 3 Tier 1 start
- Scale capital with limit increases

**CONSTRAINT-004: Infrastructure Budget**
- Monthly infrastructure cost: ~$550 (AWS + RPCs)
- Annual audit cost: $15,000-30,000 (one-time)
- Legal costs: $5,000-10,000 (initial setup)
- Total Year 1 costs: ~$30,000-50,000

### 12.2 Operational Assumptions

**ASSUMPTION-001: Base Network Stability**
- Assumes Base sequencer uptime >99%
- Assumes no protocol-level changes breaking integrations
- Validates: Monitor sequencer incidents, maintain backup plans

**ASSUMPTION-002: RPC Provider Reliability**
- Assumes Alchemy/QuickNode maintain >99.9% uptime
- Assumes latency <100ms for queries
- Validates: Multi-provider redundancy, SLA monitoring

**ASSUMPTION-003: Oracle Reliability**
- Assumes Chainlink updates within 1% deviation or 1 hour (whichever first)
- Assumes oracle manipulation is rare (<1% of opportunities)
- Validates: Multi-oracle sanity checks, staleness detection

**ASSUMPTION-004: Competition Level**
- Assumes win rate of 15-25% achievable
- Assumes not all liquidations are contested by ultra-low-latency bots
- Validates: Continuous monitoring, adjust strategy if win rate <10%

**ASSUMPTION-005: Liquidation Volume**
- Assumes Base has 50-200 liquidations per 30 days
- Assumes sufficient volume to justify infrastructure costs
- Validates: Historical data collection in Phase 1, monthly volume tracking

**ASSUMPTION-006: Regulatory Environment**
- Assumes MEV activities remain legal in operating jurisdictions
- Assumes no sudden regulatory crackdown
- Validates: Legal counsel engagement, monitoring regulatory developments

### 12.3 Success Assumptions

**ASSUMPTION-007: Profitability Persistence**
- Assumes historical profitability translates to future profitability
- Acknowledges: Alpha decay is real, margins compress over time
- Validates: Monthly ROI tracking, clear pivot triggers at <50% ROI

**ASSUMPTION-008: Infrastructure Sufficiency**
- Assumes Python + AWS is sufficient for target win rate
- Acknowledges: May need Rust rewrite if competition intensifies
- Validates: Latency monitoring, win rate tracking, technology reevaluation quarterly

**ASSUMPTION-009: Team Capacity**
- Assumes team can manage 24/7 operations
- Assumes technical expertise sufficient for troubleshooting
- Validates: On-call rotation, incident response testing, training

---

## 13. Glossary

**Alpha Decay:** Gradual reduction in strategy profitability as competition increases and opportunities are arbitraged away.

**Basis Points (BPS):** One hundredth of a percent (0.01%). Used for precise percentage measurements.

**Bundle:** A group of transactions submitted together, typically containing the liquidation transaction and a bribe payment to the block builder.

**Flash Loan:** A loan that must be repaid within the same transaction, enabling capital-free liquidations.

**Health Factor:** Ratio measuring collateralization of a lending position. <1.0 indicates liquidatable position.

**Inclusion Rate:** Percentage of submitted bundles that successfully land on-chain.

**L1 Data Posting Cost:** Cost to post transaction data to Ethereum L1 (required for Base L2 transactions).

**Liquidation Bonus:** Discount given to liquidators (typically 5-10%) when seizing collateral.

**MEV (Maximal Extractable Value):** Profit that can be extracted from reordering, inserting, or censoring transactions.

**Reorg (Reorganization):** When the blockchain history is rewritten, typically due to competing blocks or sequencer issues.

**Sequencer:** Centralized entity that orders transactions on L2 (Base uses Coinbase sequencer).

**Simulation Accuracy:** Ratio of actual profit to simulated profit, measuring prediction quality.

**Slippage:** Price movement during trade execution, causing worse fill price than expected.

**State Divergence:** Difference between bot's cached state and canonical blockchain state.

**TWAP (Time-Weighted Average Price):** Strategy of executing large trades gradually to minimize market impact.

---

## 14. References and Dependencies

### 14.1 External Documentation

**Base Network:**
- Base Documentation: https://docs.base.org
- Base Sepolia Testnet: https://docs.base.org/using-base
- Base Status Page: https://status.base.org

**Protocols:**
- Moonwell Documentation: https://docs.moonwell.fi
- Seamless Protocol Documentation: https://docs.seamlessprotocol.com
- Aave V3 Flash Loans: https://docs.aave.com/developers/guides/flash-loans

**Oracles:**
- Chainlink Price Feeds: https://docs.chain.link/data-feeds/price-feeds
- Pyth Network: https://docs.pyth.network

**DEXs:**
- Uniswap V3: https://docs.uniswap.org/protocol/V3/introduction
- Aerodrome Finance: https://docs.aerodrome.finance

### 14.2 Technical Dependencies

**Smart Contract:**
- OpenZeppelin Contracts 5.0: https://docs.openzeppelin.com/contracts/5.x/
- Foundry: https://book.getfoundry.sh

**Python Libraries:**
- web3.py: https://web3py.readthedocs.io
- eth-abi: https://eth-abi.readthedocs.io
- pandas: https://pandas.pydata.org/docs/
- SQLAlchemy: https://docs.sqlalchemy.org

**Infrastructure:**
- AWS Documentation: https://docs.aws.amazon.com
- Terraform: https://www.terraform.io/docs
- Docker: https://docs.docker.com

### 14.3 Security Resources

**Audit Firms:**
- Trail of Bits: https://www.trailofbits.com
- OpenZeppelin Security: https://openzeppelin.com/security-audits
- Consensys Diligence: https://consensys.net/diligence

**Security Tools:**
- Slither: https://github.com/crytic/slither
- Mythril: https://github.com/ConsenSys/mythril
- Echidna: https://github.com/crytic/echidna

---

## 15. Appendix: Parameter Reference Tables

### 15.1 Configuration Parameters (Default Values)

| Parameter | Phase 1 | Phase 2 | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|-----------|---------|---------|--------|--------|--------|--------|
| MAX_SINGLE_EXECUTION_USD | N/A | N/A | 500 | 1000 | 2500 | 5000 |
| MAX_DAILY_VOLUME_USD | N/A | N/A | 2500 | 5000 | 12500 | 25000 |
| MIN_PROFIT_USD | 50 | 50 | 50 | 50 | 75 | 75 |
| MIN_INCLUSION_RATE | N/A | 0.60 | 0.60 | 0.65 | 0.70 | 0.70 |
| MIN_SIMULATION_ACCURACY | 0.90 | 0.90 | 0.90 | 0.92 | 0.92 | 0.95 |
| MAX_CONSECUTIVE_FAILURES | N/A | 5 | 3 | 3 | 3 | 3 |
| BASE_BRIBE_PERCENTAGE | 0.15 | 0.15 | 0.15 | 0.15 | 0.15 | 0.15 |
| MAX_BRIBE_PERCENTAGE | 0.40 | 0.40 | 0.40 | 0.40 | 0.35 | 0.35 |
| RESERVE_FUND_PERCENTAGE | N/A | N/A | 0.30 | 0.30 | 0.30 | 0.25 |

### 15.2 Performance Thresholds

| Metric | Warning | Throttle | Halt |
|--------|---------|----------|------|
| Inclusion Rate | <70% | <60% | <50% |
| Simulation Accuracy | <92% | <90% | <85% |
| Consecutive Failures | 2 | N/A | 3 |
| State Divergence | >5 BPS | >8 BPS | >10 BPS |
| Operator Balance | <0.3 ETH | <0.2 ETH | <0.1 ETH |
| Daily Volume | >80% limit | >90% limit | 100% limit |

### 15.3 Cost Model Constants

| Cost Component | Formula | Typical Value |
|----------------|---------|---------------|
| L2 Execution Gas | `gas_estimate * (base_fee + priority_fee)` | 200k gas @ 0.05 gwei = ~$0.02 |
| L1 Data Posting | `calldata_size * L1_gas_price * L1_scalar` | ~50% of L2 cost |
| Builder Bribe | `gross_profit * bribe_percentage` | 15-40% of profit |
| Flash Loan Premium | `loan_amount * 0.0009` | 0.09% of loan |
| DEX Slippage | `swap_amount * 0.01` | 1% of swap |
| Competition Tax | `opportunities * 0.15` | 15% lost to competition |

### 15.4 Graduation Criteria Matrix

| Criteria | Tier 1→2 | Tier 2→3 | Tier 3→4 |
|----------|----------|----------|----------|
| Executions Required | 100 | 100 | 50 |
| Minimum Time | 8 weeks | 12 weeks | 12 weeks |
| Cumulative Profit | >$0 | >$5,000 | >$9,000 (3mo @ $3k/mo) |
| Inclusion Rate | >60% | >65% | >70% |
| Simulation Accuracy | >90% | >92% | >92% |
| Annualized ROI | N/A | >100% | >100% |
| Critical Incidents | 0 | 0 | 0 |

### 15.5 Alert Configuration

| Alert Type | Channel | Response Time | Escalation |
|------------|---------|---------------|------------|
| CRITICAL: System HALTED | Phone + SMS + PagerDuty | Immediate | 5 min |
| CRITICAL: Security Incident | Phone + SMS + PagerDuty | Immediate | 5 min |
| CRITICAL: Operator Balance <0.1 ETH | Phone + SMS | 15 min | 30 min |
| HIGH: System THROTTLED | SMS + PagerDuty | 30 min | 2 hours |
| HIGH: Inclusion <50% | SMS + PagerDuty | 30 min | 2 hours |
| MEDIUM: Inclusion 50-60% | Email + Slack | 2 hours | None |
| MEDIUM: Approaching Limits | Email + Slack | 4 hours | None |
| LOW: Daily Summary | Email | Next business day | None |

---

## 16. Document Control

**Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 3.1 | 2025-10-26 | Technical Team | Initial comprehensive requirements document |

**Approval:**

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Technical Lead | [TBD] | _________ | ______ |
| Security Reviewer | [TBD] | _________ | ______ |
| Legal Counsel | [TBD] | _________ | ______ |

**Review Schedule:**
- Minor updates: As needed when requirements clarified
- Major updates: After each phase completion
- Full review: Quarterly or after significant incidents

**Distribution:**
- Development team
- Security auditors
- Legal counsel (relevant sections)
- Operations team

---

**END OF TECHNICAL REQUIREMENTS DOCUMENT**