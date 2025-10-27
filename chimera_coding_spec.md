# **Project Chimera: Coding Agent Technical Specification**

**Document Type:** Implementation Guide for AI Coding Agent  
**Version:** 1.0  
**Date:** October 26, 2025  
**Purpose:** Detailed implementation specification building upon Technical Requirements Document

---

## 1. Implementation Strategy

### 1.1 Document Purpose

This specification translates the Technical Requirements Document into actionable implementation instructions for an AI coding agent. It provides detailed guidance on what to build, how to structure code, which patterns to use, and how to validate correctness at each step.

**Key Principles:**
- **Requirements Traceability**: Every implementation decision maps to specific requirements (REQ-XX-NNN)
- **Incremental Development**: Build and validate in logical phases
- **Test-Driven Approach**: Write tests alongside implementation
- **Clear Success Criteria**: Explicit validation for each component

### 1.2 Development Phases

**Phase 1: Foundation (Week 1)**
- Project structure and environment setup
- Configuration management system
- Database schema and connection handling
- Basic logging infrastructure

**Phase 2: Smart Contract (Week 2)**
- Chimera.sol implementation with security patterns
- Comprehensive test suite (>95% coverage required)
- Deployment scripts for testnet and mainnet
- Contract verification procedures

**Phase 3: State Management (Week 3)**
- StateEngine with block-level reconciliation
- Event parsing for lending protocols
- Sequencer health monitoring
- Cache management with Redis

**Phase 4: Opportunity Detection (Week 4)**
- Health factor calculation engine
- Multi-oracle price aggregation
- Sanity check framework
- Profit estimation algorithms

**Phase 5: Execution Planning (Week 5)**
- On-chain simulation framework
- Base L2-specific cost calculation (L1 + L2)
- Dynamic bribe optimization
- Bundle construction and signing

**Phase 6: Safety Systems (Week 6)**
- SafetyController with state machine
- Limit enforcement engine
- Performance monitoring and alerting
- Automatic throttling and halt mechanisms

**Phase 7: Integration & Testing (Weeks 7-8)**
- Main orchestrator connecting all modules
- Historical backtest engine
- End-to-end integration tests
- Performance profiling and optimization

### 1.3 Critical Success Factors

**Requirement Compliance:**
Every component must satisfy its requirements from the Technical Requirements Document. Use requirement IDs (e.g., REQ-SE-002) in code comments to maintain traceability.

**Simulation-First Philosophy:**
The most critical requirement is REQ-EP-002: NEVER execute a transaction without successful on-chain simulation. This is the foundation of profitability validation.

**L2-Specific Implementation:**
Base L2 has unique characteristics that must be handled:
- L1 data posting costs (significant expense)
- Sequencer centralization risks
- Block-level state reconciliation requirements
- No Flashbots relay availability

**Safety by Design:**
Multiple layers of safety checks prevent catastrophic losses:
- Automated limit enforcement (REQ-SC-001)
- State machine transitions (REQ-SC-002)
- Performance-based throttling (REQ-SC-004)
- Manual intervention capabilities (REQ-SC-002)

---

## 2. Project Foundation

### 2.1 Directory Structure

**Requirements**: Project organization for maintainability and scalability.

Create a hierarchical structure separating concerns:

```
chimera/
├── contracts/              # Solidity smart contracts
│   ├── src/               # Contract source files
│   ├── test/              # Foundry tests
│   ├── script/            # Deployment scripts
│   └── foundry.toml       # Foundry configuration
├── bot/                   # Python MEV bot
│   ├── src/               # Source code
│   │   ├── state_engine.py
│   │   ├── opportunity_detector.py
│   │   ├── execution_planner.py
│   │   ├── safety_controller.py
│   │   ├── config.py
│   │   ├── types.py       # Data structures
│   │   └── main.py        # Orchestrator
│   ├── tests/             # Pytest test suite
│   └── requirements.txt   # Python dependencies
├── data/                  # Historical data for backtesting
├── logs/                  # Runtime logs
├── scripts/               # Utility scripts
│   ├── collect_data.py   # Historical data collection
│   ├── backtest.py       # Backtesting engine
│   └── monitor.py        # Monitoring dashboard
└── infrastructure/        # AWS deployment
    └── terraform/         # Infrastructure as code
```

**Rationale**: Clear separation between smart contracts, bot logic, testing, and infrastructure. This structure supports independent development and testing of each component.

### 2.2 Configuration Management

**Requirements**: REQ-OPS-001 (operational configuration), secure key management

Design a hierarchical configuration system loading from multiple sources:

**Environment Variables** (.env file):
- RPC provider URLs and API keys
- Database connection strings
- Wallet private keys (for development only)
- Feature flags and operational limits

**Configuration File** (config.yaml):
- Static protocol addresses (Moonwell, Seamless)
- Oracle contract addresses (Chainlink, Pyth)
- DEX router addresses (Uniswap V3, Aerodrome)
- Fixed thresholds and constants

**Runtime State** (Database):
- Current system state (NORMAL/THROTTLED/HALTED)
- Daily volume counters
- Performance metrics
- Dynamic limit adjustments

**Configuration Validation**:
On startup, validate all configuration:
- Required fields are present and non-empty
- Numeric values are within acceptable ranges
- Addresses are valid Ethereum addresses (checksummed)
- RPC connections are functional
- Database is accessible

Fail fast with clear error messages if configuration is invalid. Never proceed with partial or default configuration in production.

### 2.3 Data Persistence Layer

**Requirements**: REQ-MON-003 (audit logging), REQ-REL-003 (data integrity)

**PostgreSQL Schema Design**:

Design tables to support complete audit trail and performance analysis:

**executions table**: Immutable record of every execution attempt
- Primary identifiers: timestamp, block number, transaction hash
- Opportunity details: protocol, borrower, assets, amounts
- Simulation data: predicted profit, gas estimate
- Execution data: actual profit, gas used, inclusion status
- Metadata: system state, rejection reasons

**metrics table**: Aggregated performance statistics
- Time-windowed data: 1-hour, 24-hour, 7-day aggregations
- Inclusion rates and simulation accuracy
- Profit summaries (gross, net, average)
- System state distribution

**state_divergences table**: State reconciliation audit trail
- Divergence events with magnitude in basis points
- Affected positions and canonical vs cached values
- Actions taken (continued, throttled, halted)

**system_events table**: Operational event log
- State transitions with triggering conditions
- Alerts and their severity levels
- Operator actions and manual interventions

**Redis Cache Structure**:

Use Redis for hot data with short TTLs:
- Position data: 60-second TTL (refreshed every block)
- Oracle prices: 60-second TTL
- System state: No TTL (persistent until changed)
- Performance metrics: 5-minute rolling windows

**Data Retention Policy**:
- Hot PostgreSQL storage: 3 years
- Cold archive (S3 Glacier): 7 years total
- Redis cache: Short TTL only (no persistence)

---

## 3. Smart Contract Implementation

### 3.1 Security-First Design

**Requirements**: REQ-SEC-003 (smart contract security), REQ-SC-006 (security requirements)

**Core Security Patterns**:

**Reentrancy Protection**: Use OpenZeppelin's ReentrancyGuard on all external functions. This prevents the classic reentrancy attack where malicious contracts call back during execution.

**Access Control**: Implement Ownable2Step for ownership management. This requires new owner to accept ownership, preventing accidental transfers to wrong addresses.

**Safe Token Handling**: Use SafeERC20 for all token operations. This handles tokens with non-standard return values and prevents silent failures.

**Input Validation**: Validate all parameters at function entry. Check for zero addresses, zero amounts, and valid address ranges. Fail early with descriptive custom errors.

**State Checks**: Verify contract state before executing critical operations. Check pause status, authorization, and system invariants.

**Flash Loan Safety**: Validate flash loan callbacks come from expected providers. Verify repayment amounts before returning control. Ensure atomic execution (all operations succeed or all revert).

**No State Storage**: Keep contract stateless - don't hold token balances between transactions. This reduces attack surface and simplifies security audits.

### 3.2 Contract Structure

**Requirements**: REQ-SC-001 through REQ-SC-006

**Chimera.sol Architecture**:

The contract follows a simple, auditable pattern:

**Initialization**: Constructor takes treasury address, validates non-zero. Sets owner to deployer via Ownable. Initializes paused state to false.

**Main Execution Function**: executeLiquidation() orchestrates the complete flow:
- Check paused state (revert if paused)
- Validate parameters (non-zero addresses, positive amounts)
- Track gas usage for profitability analysis
- Request flash loan from Aave V3
- Execute liquidation callback
- Transfer profits to treasury
- Emit detailed event with execution data

**Flash Loan Callback**: executeOperation() handles flash loan repayment:
- Verify caller is Aave Pool (prevent unauthorized calls)
- Verify initiator is self (prevent external abuse)
- Approve lending protocol to take debt tokens
- Call protocol's liquidate function
- Receive discounted collateral
- Swap collateral for debt token on Uniswap V3
- Verify sufficient tokens to repay flash loan + premium
- Calculate profit after repayment
- Verify profit exceeds minimum threshold
- Approve Aave to take repayment
- Transfer profit to treasury
- Return true (flash loan success)

**Emergency Controls**: Pause and unpause functions restrict contract execution without affecting existing state. Only owner can call.

**Maintenance Functions**: setTreasury allows changing profit destination. rescueTokens recovers mistakenly sent tokens.

### 3.3 Testing Requirements

**Requirements**: REQ-TEST-005 (smart contract testing), >95% coverage

**Test Categories**:

**Unit Tests**: Test each function in isolation
- State changes (pause, unpause, treasury updates)
- Access control (only owner can call restricted functions)
- Input validation (reject zero addresses, invalid amounts)
- Event emissions (correct events with correct parameters)

**Integration Tests**: Test complete execution flows
- Successful liquidation end-to-end on mainnet fork
- Flash loan repayment verification
- Profit calculation accuracy
- Multiple sequential liquidations

**Security Tests**: Test attack vectors
- Reentrancy attempts (should fail with ReentrancyGuard)
- Unauthorized access (should fail with Ownable check)
- Flash loan callback spoofing (should fail verification)
- Insufficient profit scenarios (should revert gracefully)

**Fuzz Tests**: Test with random inputs
- Random amounts for profit calculations
- Random addresses for parameter validation
- Boundary conditions (max uint256, zero values)

**Gas Optimization Tests**: Measure and benchmark gas usage for typical operations.

---

## 4. StateEngine Module

### 4.1 Real-Time State Synchronization

**Requirements**: REQ-SE-001 (real-time monitoring), REQ-SE-002 (reconciliation)

**Core Responsibilities**:

The StateEngine is the authoritative source of truth for blockchain state relevant to liquidation opportunities. It must maintain perfect synchronization while being resilient to network issues.

**Multi-RPC Strategy**:

Connect to three independent RPC providers:
- **Primary WebSocket** (Alchemy): Real-time event streaming
- **Backup WebSocket** (QuickNode): Automatic failover
- **Archive HTTP** (Alchemy): State reconciliation and verification

Use WebSocket for speed (events arrive in ~500ms) but verify via HTTP for reliability (100% accurate, slightly slower). Never trust a single source.

**Block Processing Pipeline**:

When new block arrives via WebSocket:
1. **Receive**: Get block header and transaction list
2. **Parse**: Extract relevant events (Borrow, Repay, Liquidate, Oracle updates)
3. **Update**: Modify in-memory position cache with new data
4. **Reconcile**: Compare cached state vs canonical chain state
5. **Validate**: Check sequencer health (block continuity, timestamps)
6. **Checkpoint**: Store snapshot every 10 blocks for recovery

**Event Processing**:

Parse events from lending protocols:
- **Borrow events**: New debt position or increased borrowing
- **Repay events**: Debt reduction or position closure
- **Liquidate events**: Position was liquidated (remove from tracking)
- **Oracle updates**: New price data from Chainlink feeds

Maintain a map of positions: `{protocol}:{user} -> Position object`

Update position data incrementally as events arrive. Track last update block for staleness detection.

### 4.2 State Reconciliation

**Requirements**: REQ-SE-002 (block-level reconciliation), 0.1% divergence threshold

**Critical Importance**:

State divergence is catastrophic - it means your view of reality is wrong. You might:
- Try to liquidate positions that don't exist (waste gas)
- Miss real liquidation opportunities (lose profit)
- Calculate wrong health factors (execute unprofitable liquidations)

**Reconciliation Algorithm**:

Every block (not every 5 blocks - that's too slow):
1. For each position in cache, construct eth_call to lending protocol
2. Fetch canonical position data from archive RPC
3. Compare cached debt_amount vs canonical debt_amount
4. Calculate divergence: `|cached - canonical| / canonical * 10000` (basis points)
5. If any position diverges >10 BPS (0.1%), trigger HALT
6. Log all divergences for analysis

**Why Every Block**:
Base produces blocks every ~2 seconds. A 5-block lag (60 seconds) means:
- 30 blocks of potential reorgs undetected
- Multiple invalid bundles submitted before detection
- Wasted gas, bribes, and opportunity cost

**Divergence Response**:
When divergence detected:
- Immediately enter HALTED state (stop all executions)
- Alert operators via PagerDuty
- Rebuild state from canonical source
- Identify root cause (reorg, RPC issue, bug)
- Only resume after manual verification

### 4.3 Sequencer Health Monitoring

**Requirements**: REQ-SE-004 (sequencer anomaly detection), Base L2-specific

**L2 Centralization Risk**:

Base uses a single sequencer controlled by Coinbase. If it fails:
- All transactions stop (no mempool alternatives)
- Potential for deep reorgs when restored
- Your bot is completely non-operational

**Detection Mechanisms**:

Monitor for sequencer issues:
- **Block Gap**: Current block number != previous + 1
- **Timestamp Jump**: Current timestamp - previous > 20 seconds (normal: ~2s)
- **Block Production Stall**: No new blocks for >10 seconds
- **Unusual Reorg Depth**: Reorg deeper than 3 blocks

**Response Protocol**:
On sequencer anomaly:
- Immediately enter HALTED state
- Do NOT attempt to execute (high reorg risk)
- Monitor Base status page (https://status.base.org)
- Wait for 10 consecutive normal blocks before considering resume
- Rebuild state completely after sequencer recovery

**Historical Context**:
Base has experienced sequencer outages. Most notable: multi-hour downtime in 2024 causing significant disruption. This is not theoretical - it will happen.

---

## 5. Opportunity Detection

### 5.1 Health Factor Calculation

**Requirements**: REQ-OD-001 (position scanning), REQ-OD-002 (oracle integration)

**Liquidation Fundamentals**:

A lending position becomes liquidatable when:
`health_factor = (collateral_value * liquidation_threshold) / debt_value < 1.0`

Where:
- `collateral_value`: Amount of collateral × current price
- `liquidation_threshold`: Protocol-defined (typically 0.75-0.85)
- `debt_value`: Amount of debt × current price

**Oracle Strategy**:

Use **single fast oracle** (Chainlink) for detection:
- Speed matters - being first is critical
- Chainlink updates frequently (< 1% price deviation or 1 hour)
- Base has mature Chainlink infrastructure

Do NOT use multiple oracles for detection:
- Median calculation adds 3x latency
- Waiting for consensus means you're always slower
- Oracle validation happens later in simulation

**Calculation Process**:

For each position in cache:
1. Fetch Chainlink price for collateral asset
2. Fetch Chainlink price for debt asset
3. Calculate collateral value in USD: `(amount / 10^decimals) * price`
4. Calculate debt value in USD: `(amount / 10^decimals) * price`
5. Apply liquidation threshold: `(collateral_value * threshold) / debt_value`
6. If result < 1.0, position is liquidatable

### 5.2 False Positive Prevention

**Requirements**: REQ-OD-003 (false positive filtering), <10% false positive rate

**Multi-Layer Validation**:

**Layer 1: Multi-Oracle Sanity Check**
After detecting with Chainlink, verify with secondary oracle (Pyth):
- Fetch price from both sources
- Calculate divergence: `|primary - secondary| / primary`
- If divergence >5%, flag as suspicious and skip
- Protects against oracle manipulation or stale data

**Layer 2: Price Movement Detection**
Compare current price to previous price:
- If price moved >30% in one block, flag as suspicious
- Likely oracle manipulation or flash crash
- Skip execution until price stabilizes

**Layer 3: Confirmation Blocks**
Track how long position has been unhealthy:
- Increment `blocks_unhealthy` counter each block below threshold
- Require minimum 2 blocks unhealthy before executing
- Prevents triggering on temporary price spikes

**Layer 4: Protocol State Check**
Verify protocol allows liquidations:
- Check if liquidation function is paused
- Check if protocol has rate limiting
- Check if position size exceeds protocol limits

**Why This Matters**:
False positives waste gas and bribes. At 200k gas + 15% bribe, each false positive costs $20-50. With 10-20 opportunities per day, 10% false positive rate = $2-10 daily waste.

### 5.3 Profit Estimation

**Requirements**: REQ-OD-004 (profitability estimation), $50 minimum

**Rough Estimation Purpose**:

Before expensive simulation, do quick profitability check:
- Estimated profit >= $50: Worth simulating
- Estimated profit < $50: Skip to save computation

**Estimation Formula**:

Gross profit sources:
- Liquidation bonus: `collateral_amount * bonus_percentage * price`
- Arbitrage profit: `~2-5% of collateral value` (DEX price difference)

Estimated costs:
- Gas: $10-20 (rough estimate, varies with gas price)
- Bribe: 20% of gross (conservative estimate)
- Flash loan: 0.09% of loan amount
- Slippage: 1% of swap amount

Net estimate: `gross - costs`

**Accuracy Requirements**:
This is screening, not ground truth. Acceptable accuracy: ±50%

The on-chain simulation (REQ-EP-002) provides actual profitability.

---

## 6. Execution Planning

### 6.1 On-Chain Simulation (Critical)

**Requirements**: REQ-EP-002 (simulation required), ground truth for profitability

**The Most Important Function**:

This is the single most critical requirement in the entire system. NEVER execute without successful simulation.

**Why Simulation is Non-Negotiable**:

Off-chain math is always wrong due to:
- DEX slippage (varies with liquidity)
- Protocol fees (complex calculation)
- Rounding errors (EVM vs floating point)
- Hidden costs (L1 data posting)
- Edge cases (maximum liquidation amounts)
- Competition (MEV bot interference)

Simulation uses eth_call to execute transaction without committing:
- Returns exact profit amount
- Accounts for all on-chain costs
- Validates transaction won't revert
- Provides accurate gas estimate

**Simulation Process**:

1. Build complete transaction with exact parameters
2. Call `eth_call` with transaction data against current block
3. Parse return data to extract profit amount
4. Call `eth_estimateGas` for accurate gas usage
5. Validate: success=true and profit>0
6. Only proceed if simulation succeeds

**Failure Handling**:
If simulation fails or shows loss:
- Log opportunity with failure reason
- Increment false_positive counter
- Skip execution completely
- Never attempt "maybe it will work"

### 6.2 Cost Calculation (Base L2-Specific)

**Requirements**: REQ-EP-003 (L2 cost calculation), accurate USD conversion

**Two-Component Gas Model**:

Base L2 has unique cost structure:
- **L2 Execution Cost**: Standard gas for computation
- **L1 Data Posting Cost**: Ethereum mainnet gas for data availability

**L2 Execution Cost**:
```
l2_cost = gas_estimate * (base_fee_per_gas + priority_fee_per_gas)
```

Use 75th percentile of recent base fees (not median - need priority).
Add priority fee for competitive inclusion.

**L1 Data Posting Cost** (Critical for Base):
```
l1_cost = calldata_size * l1_gas_price * l1_scalar
```

Where:
- `calldata_size`: Transaction data size in bytes
- `l1_gas_price`: Current Ethereum mainnet gas price
- `l1_scalar`: Base's compression factor (from L1Block precompile)

Fetch from Base system contracts:
- L1Block precompile: `0x4200000000000000000000000000000000000015`
- Get L1 scalar and gas price from contract state

**L1 Cost Significance**:
L1 data posting can be 30-50% of total gas cost. During Ethereum gas spikes (e.g., popular NFT mint), L1 costs can spike 10x, making Base liquidations suddenly unprofitable.

**Complete Cost Formula**:
```
total_cost_usd = (
    (l2_cost + l1_cost) * eth_price_usd +
    gross_profit * bribe_percentage +
    loan_amount * flash_loan_premium +
    swap_amount * slippage_estimate
)
```

**Dynamic USD Conversion**:
Fetch ETH/USD price from Chainlink oracle in real-time. Never use stale or hardcoded prices. Convert all costs to USD before profitability check.

### 6.3 Dynamic Bribe Optimization

**Requirements**: REQ-EP-005 (dynamic bribe optimization), 15-40% range

**Bribe Economics**:

Builder bribe is payment to block builder to include your transaction with priority. It's your second-largest cost after gas.

**Baseline Strategy**:
- Start at 15% of gross profit
- Track inclusion rate per submission path
- Adjust based on performance

**Adjustment Algorithm**:

Monitor last 100 submissions:
- Calculate inclusion_rate = included_count / total_count

If inclusion_rate < 60%:
- Competition is intense or bribe too low
- Increase bribe by 5% (multiply by 1.05)

If inclusion_rate > 90%:
- Overpaying, can reduce bribe
- Decrease bribe by 2% (multiply by 0.98)

Cap at 40% maximum:
- If you need >40% bribe, opportunity is not worth taking
- Competition has made it unprofitable

**Per-Path Tracking**:
Track inclusion rate separately for each submission path:
- Direct mempool
- Base-native builders (if discovered)
- Private RPCs (if available)

Select path with highest expected value:
`EV = (profit * inclusion_rate) - (bribe + fees)`

---

## 7. Safety Controller

### 7.1 State Machine Design

**Requirements**: REQ-SC-002 (state machine), three operational states

**System States**:

**NORMAL**: Full operation
- Execute all opportunities that pass checks
- 100% execution rate
- All systems functioning within thresholds

**THROTTLED**: Reduced operation
- Execute 50% of opportunities (random selection)
- Performance degraded but acceptable
- Warning indicators present

**HALTED**: No execution
- Block all new executions
- Critical issue detected
- Requires manual investigation and resume

**State Transitions**:

NORMAL → THROTTLED when:
- Inclusion rate 50-60% (below target but not critical)
- Simulation accuracy 85-90% (concerning but not failed)
- No other HALT conditions met

NORMAL → HALTED when:
- Inclusion rate <50% (critically low)
- Simulation accuracy <85% (predictions failing)
- Consecutive failures ≥3 (repeated execution failures)
- State divergence detected (cache is wrong)
- Sequencer anomaly detected (L2 infrastructure issue)

THROTTLED → NORMAL when:
- Inclusion rate >60% AND simulation accuracy >90%
- Metrics sustained for 100+ submissions

THROTTLED → HALTED when:
- Any HALT condition met

HALTED → NORMAL:
- Only via manual operator intervention
- After root cause identified and fixed
- After testing on testnet if code changed

### 7.2 Limit Enforcement

**Requirements**: REQ-SC-001 (limit enforcement), graduated scaling

**Hard Limits (Never Exceeded)**:

Check before every execution:

**Single Execution Limit**:
- Purpose: Prevent outsized loss on single bad trade
- Check: `simulation_result.profit_usd <= MAX_SINGLE_EXECUTION_USD`
- Tier 1: $500, gradually increases to Tier 4: $5,000

**Daily Volume Limit**:
- Purpose: Cap daily exposure
- Track: `daily_volume_usd` (resets at midnight UTC)
- Check: `daily_volume + profit_usd <= MAX_DAILY_VOLUME_USD`
- Tier 1: $2,500, increases with graduation

**Minimum Profit**:
- Purpose: Avoid noise and marginal trades
- Check: `net_profit_usd >= MIN_PROFIT_USD`
- Ensures execution worth the gas and complexity

**Consecutive Failures**:
- Purpose: Stop hemorrhaging on systematic failures
- Track: Counter incremented on failure, reset on success
- Check: `consecutive_failures < MAX_CONSECUTIVE_FAILURES`
- Triggers HALT at 3 failures

**Reserve Fund**:
- Purpose: Maintain operational buffer
- Track: Separate wallet balance
- Check: Reserve fund ≥30% of total capital
- Used for emergency gas, bug bounties, unexpected costs

### 7.3 Performance Monitoring

**Requirements**: REQ-SC-004 (automatic state transitions), 10-minute check interval

**Key Metrics**:

**Inclusion Rate**: What percentage of submitted bundles land on-chain?
- Formula: `successful_inclusions / total_submissions`
- Threshold: >60% normal, 50-60% throttled, <50% halted
- Indicates: Competition intensity, bribe adequacy, network issues

**Simulation Accuracy**: How close are predictions to reality?
- Formula: `actual_profit / simulated_profit` (average over successful executions)
- Threshold: >90% normal, 85-90% throttled, <85% halted
- Indicates: State quality, cost model accuracy, unexpected issues

**Consecutive Failures**: How many failures in a row?
- Simple counter, reset on any success
- Threshold: 3 failures triggers HALT
- Indicates: Systematic problem (bug, network issue, contract change)

**State Divergence Frequency**: How often does reconciliation find problems?
- Count of divergence events per hour
- Threshold: >3 per hour indicates data quality issues
- Indicates: RPC problems, reorgs, bugs in state management

**Automated Response**:

Every 10 minutes, calculate metrics and apply state transitions:
1. Fetch last 100 executions from database
2. Calculate inclusion_rate and simulation_accuracy
3. Check consecutive_failures counter
4. Apply transition rules
5. If state changed, log event and send alert

---

## 8. Integration & Orchestration

### 8.1 Main Orchestrator

**Requirements**: Integration of all modules, main event loop

**Bot Lifecycle**:

**Initialization**:
1. Load and validate configuration
2. Establish database connections (PostgreSQL, Redis)
3. Connect to RPC providers (WebSocket + HTTP)
4. Load smart contract ABI and create contract instance
5. Initialize all modules (StateEngine, Detector, Planner, Safety)
6. Verify operator wallet has sufficient gas balance
7. Load Chimera contract and verify ownership

**Main Event Loop**:

```
Start StateEngine in background (async task)

While True:
    Check SafetyController state
    If HALTED:
        Sleep 60 seconds, continue (wait for manual resume)
    
    Get all opportunities from OpportunityDetector
    
    For each opportunity:
        Plan execution via ExecutionPlanner (simulate)
        If planning returns None: skip (not profitable)
        
        Check SafetyController.check_execution_allowed()
        If not allowed: skip with reason
        
        Submit bundle via ExecutionPlanner
        Track submission in database
        
    Update performance metrics (every 100 submissions)
    
    Sleep 5 seconds (scan interval)
```

**Error Handling**:

Graceful degradation:
- RPC error: Switch to backup provider, log warning
- Database error: Queue operations in memory, retry
- Unexpected exception: Log with stack trace, continue
- Critical error: Enter HALTED state, alert operators

Never crash the main loop. Catch exceptions at module boundaries.

### 8.2 Monitoring Integration

**Requirements**: REQ-MON-001 (metrics collection), REQ-MON-002 (alerting)

**Metrics Collection**:

Export to CloudWatch every 60 seconds:
- System state (NORMAL/THROTTLED/HALTED)
- Opportunities detected (count)
- Bundles submitted (count)
- Successful inclusions (count)
- Inclusion rate (percentage)
- Daily volume (USD)
- Operator balance (ETH)
- Database connection health
- RPC provider latency

**Alert Routing**:

**CRITICAL** (Phone + SMS + PagerDuty):
- System entered HALTED state
- Security incident detected
- Operator balance <0.1 ETH
- Database unavailable

**HIGH** (SMS + PagerDuty):
- System entered THROTTLED state
- Inclusion rate <50%
- Consecutive failures at 2 (before HALT)

**MEDIUM** (Email + Slack):
- Approaching daily volume limit (>80%)
- Key rotation due in 7 days
- RPC provider degraded

**LOW** (Email):
- Daily performance summary
- Weekly report generated

### 8.3 Database Integration

**Requirements**: REQ-REL-003 (data integrity), REQ-MON-003 (audit logging)

**Execution Logging**:

After every opportunity (executed or skipped):
```
INSERT INTO executions (
    timestamp, block_number, protocol, borrower,
    simulation_success, simulated_profit_usd,
    bundle_submitted, rejection_reason,
    included, actual_profit_usd,
    state, tx_hash
) VALUES (...)
```

Create immutable record for:
- Performance analysis
- Debugging failed executions
- Legal/compliance audit trail
- Profitability tracking

**Metrics Aggregation**:

Hourly job aggregates into metrics table:
```
INSERT INTO metrics (
    timestamp, window,
    opportunities_detected, bundles_submitted,
    bundles_included, inclusion_rate,
    total_gross_profit, total_net_profit,
    system_state
) VALUES (...)
```

Supports:
- Performance dashboards
- Trend analysis
- Anomaly detection

---

## Appendix A: Critical Implementation Notes

### A.1 Common Pitfalls

**1. Skipping Simulation** (NEVER DO THIS)
- Temptation: "Estimation looks good, skip expensive eth_call"
- Reality: Leads to unprofitable executions and wasted gas
- Solution: Always simulate (REQ-EP-002 is non-negotiable)

**2. Ignoring L1 Data Costs**
- Temptation: "L2 gas is so cheap, that's the only cost"
- Reality: L1 data posting is 30-50% of total gas cost
- Solution: Calculate and include L1 component (REQ-EP-003)

**3. Using Single RPC Provider**
- Temptation: "One provider is simpler"
- Reality: Single point of failure causes downtime
- Solution: