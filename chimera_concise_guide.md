# **Project Chimera: Concise Implementation Guide**

**Target Audience:** AI Coding Agent  
**Version:** 1.0  
**Date:** October 2025  
**Objective:** Build MEV liquidation bot for Base L2 in 12 weeks

---

## Implementation Roadmap

### Phase 1: Local Development (Weeks 1-12)
**Goal:** Prove strategy profitability via historical backtest

### Phase 2: Testnet Validation (Weeks 13-20)
**Goal:** Validate infrastructure and submission paths

### Phase 3: Mainnet Deployment (Week 21+)
**Goal:** Execute profitably at small scale, scale gradually

---

## Week 1-2: Setup & Data Collection

### Task 1: Project Structure

Create directory structure:
```
chimera/
├── contracts/          # Solidity smart contracts
│   ├── src/
│   ├── test/
│   └── script/
├── bot/               # Python bot
│   ├── src/
│   ├── tests/
│   └── requirements.txt
├── data/              # Historical data
├── logs/              # Runtime logs
└── scripts/           # Utilities
```

### Task 2: Install Dependencies

**Python (requirements.txt):**
```
web3==6.11.0
eth-abi==4.2.1
pandas==2.1.3
asyncio==3.4.3
sqlalchemy==2.0.23
pytest==7.4.3
```

**Solidity:**
```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### Task 3: RPC Provider Setup

1. **Alchemy:** Sign up, create Base Mainnet app, copy API key
2. **QuickNode:** Create Base endpoint as backup
3. **Store in `.env`:**
```
ALCHEMY_API_KEY=your_key
ALCHEMY_WSS=wss://base-mainnet.g.alchemy.com/v2/YOUR-KEY
ALCHEMY_HTTPS=https://base-mainnet.g.alchemy.com/v2/YOUR-KEY
QUICKNODE_HTTPS=https://your-endpoint.base.quiknode.pro/
```

### Task 4: Collect Historical Data

**Objective:** Collect 30 days of Base liquidations

**Script: `scripts/collect_historical_data.py`**

Key steps:
1. Connect to Base mainnet via Alchemy
2. Scan last 1.3M blocks (~30 days at 2s/block)
3. Filter for liquidation events from Moonwell, Seamless
4. Save to `data/historical_liquidations.csv`
5. Collect gas prices for same period

**Expected output:** 50-200 liquidation events

**RED FLAG:** If <20 liquidations in 30 days, Base volume may be too low for strategy viability.

---

## Week 3-4: Smart Contract Development

### Task 5: Core Liquidation Contract

**File: `contracts/src/Chimera.sol`**

**Key functions:**
- `executeLiquidation()`: Atomic liquidation via flash loan
- `pause()` / `unpause()`: Emergency controls
- `setTreasury()`: Update profit destination
- `rescueTokens()`: Recover mistaken transfers

**Security requirements:**
- Reentrancy protection (ReentrancyGuard)
- Access control (Ownable)
- Pause mechanism
- No token balances retained (stateless)

**Critical:** Contract MUST be professionally audited before mainnet. Budget: $15-30K.

### Task 6: Comprehensive Tests

**File: `contracts/test/Chimera.t.sol`**

**Test coverage required:**
- Pause/unpause functionality
- Access control enforcement
- Liquidation execution (mocked)
- Token rescue
- Reentrancy protection

**Target:** >80% code coverage

**Run tests:**
```bash
forge test -vvv
forge coverage
```

---

## Week 5-8: Bot Core Modules

### Task 7: StateEngine

**File: `bot/src/state_engine.py`**

**Purpose:** Maintain synchronized view of lending protocol state

**Key responsibilities:**
1. **WebSocket subscription:** Monitor new blocks in real-time
2. **Event processing:** Parse liquidation-relevant events
3. **State reconciliation:** Compare cached state vs. canonical chain EVERY BLOCK
4. **Reorg detection:** Handle sequencer restarts and chain reorganizations

**Critical configuration:**
```python
RECONCILIATION_FREQUENCY_BLOCKS = 1  # Every block, not every 5
MAX_STATE_DIVERGENCE_BPS = 10  # 0.1% divergence triggers HALT
```

**L2-Specific:** Monitor for sequencer gaps (missing block numbers) and timestamp anomalies.

### Task 8: OpportunityDetector

**File: `bot/src/opportunity_detector.py`**

**Purpose:** Identify liquidatable positions with high precision

**Detection strategy:**
1. **Fast oracle (Chainlink):** Calculate health factors for speed
2. **Sanity checks:**
   - Compare vs. secondary oracle (Pyth/Redstone) - divergence >5% = skip
   - Price movement >30% in one block = suspicious, flag for review
   - Position unhealthy for >2 blocks = confirmation, not flash crash
3. **Rough profit estimate:** Filter before expensive simulation

**Key threshold:**
```python
HEALTH_FACTOR_THRESHOLD = 1.0  # Below = liquidatable
MIN_PROFIT_USD = 50  # Skip small opportunities
```

### Task 9: ExecutionPlanner

**File: `bot/src/execution_planner.py`**

**Purpose:** Simulate, cost, and build profitable bundles

**Critical flow:**
1. **Build transaction** using Chimera contract call
2. **Simulate via eth_call** (GROUND TRUTH - never skip)
3. **Calculate ALL costs:**
   - L2 execution gas (estimate from simulation)
   - L1 data posting (Base-specific: ~50% of L2 cost)
   - Builder bribe (15% of profit, tune dynamically)
   - Flash loan premium (0.05-0.09%)
   - DEX slippage (1% budget)
4. **Check profitability:** Net profit > $50 minimum
5. **Build final bundle** with bribe transaction

**L1 Data Cost Calculation (Base-specific):**
```python
l2_gas_cost_wei = gas_estimate * (base_fee + priority_fee)
l1_data_cost_wei = l2_gas_cost_wei * 0.5  # Estimate, varies with L1 gas
total_gas_cost = l2_gas_cost_wei + l1_data_cost_wei
```

**Dynamic Bribe Strategy:**
```python
BASE_BRIBE_PCT = 0.15  # Start at 15%
# Track inclusion rate every 100 submissions
# If inclusion <60%: increase bribe by 5%
# If inclusion >90%: decrease bribe by 2%
# Never exceed 40% cap
```

### Task 10: SafetyController

**File: `bot/src/safety_controller.py`**

**Purpose:** Enforce limits and trigger safety states

**Hard limits:**
```python
MAX_SINGLE_EXECUTION_USD = 500  # Start conservative
MAX_DAILY_VOLUME_USD = 2500
MIN_PROFIT_USD = 50
MAX_CONSECUTIVE_FAILURES = 3
```

**State machine:**
- **NORMAL:** Full operation
- **THROTTLED:** 50% execution rate (random skip)
- **HALTED:** No executions until manual resume

**Auto-transitions:**
- Inclusion rate <50% → HALTED
- Inclusion rate 50-60% → THROTTLED  
- Simulation accuracy <85% → HALTED
- Simulation accuracy 85-90% → THROTTLED
- 3 consecutive failures → HALTED
- Sequencer anomaly detected → HALTED

---

## Week 9-10: Integration & Testing

### Task 11: Main Bot Orchestrator

**File: `bot/src/main.py`**

**Main loop:**
```python
async def run(self):
    # Start StateEngine in background
    asyncio.create_task(self.state_engine.start())
    
    while True:
        # Check if halted
        if self.safety.state == HALTED:
            await asyncio.sleep(60)
            continue
            
        # Scan for opportunities
        opportunities = self.detector.scan_for_opportunities()
        
        # Process each
        for opp in opportunities:
            # Plan execution (simulate)
            bundle = self.planner.plan_execution(opp)
            
            if bundle is None:
                continue  # Not profitable
                
            # Check safety
            allowed, reason = self.safety.check_execution_allowed(opp, bundle)
            
            if not allowed:
                continue
                
            # Submit
            self.planner.submit_bundle(bundle)
            
        await asyncio.sleep(5)  # Scan every 5 seconds
```

### Task 12: Module Tests

**For each module, write pytest tests:**
- State reconciliation logic
- Health factor calculations
- Simulation result parsing
- Cost calculations
- Safety limit enforcement

**Run all tests:**
```bash
pytest tests/ -v --cov=src
```

---

## Week 11-12: Historical Backtesting

### Task 13: Backtest Engine

**File: `scripts/backtest.py`**

**Purpose:** Replay historical liquidations to validate profitability

**For each historical liquidation:**

1. **Would bot detect?** Check if health factor <1.0 with Chainlink oracle
2. **Would bot win?** Compare latency:
   ```python
   bot_latency_ms = detection_latency (500ms) + build_latency (200ms)
   winner_latency_ms = (winner_block - oracle_block) * 2000ms
   would_win = bot_latency_ms < winner_latency_ms
   ```
3. **Would be profitable?** Calculate net profit:
   ```python
   gross_profit = liquidation_bonus + arbitrage
   costs = gas + l1_data + bribe + flash_loan + slippage
   net_profit = gross_profit - costs
   profitable = net_profit >= 50
   ```

**Key metrics:**
- **Win rate:** % of detected opportunities won
- **Profitable rate:** % of wins that were profitable
- **Avg net profit:** Average profit per win
- **Monthly profit:** Total over 30 days
- **Annual ROI:** (annual_profit / capital) * 100

### Task 14: Sensitivity Analysis

**Build scenario table:**

| Scenario | Win Rate | Avg Profit | Bribe % | Monthly Profit | Annual ROI |
|----------|----------|------------|---------|----------------|------------|
| Optimistic | 25% | $150 | 15% | $12,000 | 180% |
| Base Case | 18% | $100 | 20% | $6,500 | 105% |
| Pessimistic | 12% | $60 | 30% | $2,000 | 35% |
| Worst Case | 8% | $30 | 40% | -$500 | -10% |

**CRITICAL DECISION POINT:**

**PROCEED to Phase 2 if:**
- Base Case ROI >100%
- Win rate >15% in backtest
- All tests passing

**STOP if:**
- Base Case ROI <50%
- Win rate <10%
- Can't win any historical liquidations due to latency

**PIVOT if:**
- Strategy unprofitable on Base but model works elsewhere
- Consider Ethereum mainnet, Arbitrum, or different MEV strategy

---

## Week 13-16: Testnet Deployment

### Task 15: Base Sepolia Setup

**Get testnet ETH:**
- Visit Base Sepolia faucet
- Fund operator wallet with 0.5+ testnet ETH

**Deploy contract:**
```bash
forge script script/Deploy.s.sol --rpc-url <sepolia-rpc> --broadcast
```

**Configure bot for testnet:**
```python
# Use environment variable to switch
environment = os.getenv('ENVIRONMENT', 'testnet')
if environment == 'testnet':
    rpc = os.getenv('ALCHEMY_WSS_TESTNET')
    # etc.
```

### Task 16: Test Submission Paths

**Research and test ALL available paths on Base:**

1. **Direct mempool (always available)**
   - Method: `eth_sendRawTransaction`
   - Pros: Simple, no dependencies
   - Cons: Public competition

2. **Base-native builders (research required)**
   - Find if any Base-specific MEV infrastructure exists
   - Test if available

3. **Private RPC priority (research required)**
   - Check if Alchemy/QuickNode offer priority submission on Base

**For each path, measure:**
- Inclusion rate (% that land on-chain)
- Inclusion latency (blocks until included)
- Additional costs
- Reliability

**Test protocol:** Submit 10 test transactions per path, analyze results.

### Task 17: Two-Week Live Operation

**Run bot continuously on Base Sepolia:**
```bash
python src/main.py testnet
```

**Monitor metrics:**
- Uptime (target: >95%)
- Inclusion rate (target: >60%)
- Simulation accuracy (target: >90%)
- Consecutive failures (should never hit 3)
- State divergence events (should be rare)

**Generate weekly reports:**
Track performance trends, document any incidents.

---

## Week 17-20: Testnet Analysis & Audit Prep

### Task 18: Performance Analysis

**Calculate key metrics:**
```python
inclusion_rate = successful_submissions / total_submissions
simulation_accuracy = actual_profit / simulated_profit (average)
uptime = time_in_normal_state / total_time
```

**Phase 3 readiness checklist:**
- [ ] Inclusion rate >60% sustained
- [ ] Simulation accuracy >90%
- [ ] Uptime >95% over 2 weeks
- [ ] All operational runbooks tested
- [ ] Smart contract audit completed
- [ ] Capital prepared ($1,000-2,000)

### Task 19: Smart Contract Audit

**DO NOT SKIP THIS STEP**

1. **Engage professional auditors:**
   - Trail of Bits, OpenZeppelin, or Consensys Diligence
   - Budget: $15,000-$30,000
   - Timeline: 2-4 weeks

2. **Prepare:**
   - Freeze contract code
   - Document all functionality
   - Provide comprehensive test suite

3. **Remediate:**
   - Fix all high/critical findings
   - Re-audit if significant changes

**Mainnet deployment without audit is NEGLIGENT.**

---

## Week 21+: Mainnet Deployment

### Task 20: Production Infrastructure

**AWS setup:**
- EC2: c7g.xlarge in us-east-1 (low latency to Base sequencer)
- RDS: PostgreSQL for immutable logs
- ElastiCache: Redis for hot state
- Secrets Manager: All private keys and API keys
- CloudWatch: Monitoring and alerting

**Cost estimate:** ~$550/month

### Task 21: Deploy to Mainnet (PAUSED)

**Deploy contract:**
```bash
forge script script/Deploy.s.sol --rpc-url $ALCHEMY_HTTPS --broadcast --verify
```

**IMMEDIATELY pause:**
```bash
cast send $CHIMERA_ADDRESS "pause()" --private-key $OPERATOR_KEY
```

**Fund operator wallet:**
- Send 0.5 ETH for gas
- Keep treasury on hardware wallet (Ledger/Trezor)

### Task 22: Graduated Scaling

**Tier 1: $500 limit (Weeks 21-28)**
- Target: 100 successful executions
- Minimum: 8 weeks at this tier
- Criteria: Net positive profit, >60% inclusion, zero incidents

**Tier 2: $1,000 limit (Weeks 29-40)**
- Target: 100 successful executions
- Minimum: 12 weeks
- Criteria: $5K+ profit, >65% inclusion, >100% ROI

**Tier 3: $2,500 limit (Weeks 41-52)**
- Target: 50 successful executions
- Minimum: 12 weeks
- Criteria: $3K+/month sustained, >70% inclusion

**Tier 4: $5,000 limit (Month 13+)**
- Consider protocol partnerships
- Evaluate Rust rewrite for speed
- Expand to other chains

**Graduation rules:**
- NEVER advance if criteria not met
- If unprofitable for 2 months → reduce to previous tier
- If unprofitable for 3 months → wind down

---

## Critical Success Factors

### 1. Cost Modeling Must Be Accurate

**All costs in USD for each opportunity:**
```
Total Cost = L2_gas + L1_data + Bribe + FlashLoan + Slippage
```

**L1 data cost is significant (30-50% of L2 gas).** Don't ignore it.

### 2. Simulation is Ground Truth

**NEVER execute without successful `eth_call` simulation.**

Off-chain math is always wrong due to:
- Slippage variations
- Protocol fee calculations  
- Rounding errors
- Hidden edge cases

### 3. State Reconciliation Prevents Catastrophe

**Reconcile EVERY BLOCK, not every 5 blocks.**

A 60-second lag means:
- 30 blocks of potential reorgs missed
- 5+ invalid bundles submitted
- Gas wasted on bad state

### 4. Competition is Real

**Your Python bot is slower than Rust/Go competitors.**

Expect to win only:
- 15-25% of opportunities (not 30-40%)
- "Slower" liquidations (not edge cases)
- When latency advantage doesn't matter

**This is OK if economics still work.**

### 5. L2 Risks Are Different

**Base-specific concerns:**
- Sequencer centralization (single point of failure)
- L1 data costs (invisible but real)
- Potential for deep reorgs during sequencer restarts
- Less mature MEV infrastructure than Ethereum

**Monitor sequencer health proactively.**

### 6. Scale Slowly or Die Fast

**Resist temptation to rush graduation.**

Six months at small scale proves:
- Strategy viability
- Operational competence
- Safety mechanisms work
- Economics are sustainable

**Premature scaling kills more projects than technical bugs.**

---

## Risk Management Rules

### Never Violate These:

1. **No execution without simulation** (prevents bad trades)
2. **No mainnet without audit** (prevents contract exploits)
3. **No limit increases without criteria met** (prevents premature scaling)
4. **30% reserve fund always maintained** (prevents operational failures)
5. **Manual halt on 3 consecutive failures** (prevents cascading losses)

### Shutdown Triggers:

**Immediate wind-down if:**
- Legal cease-and-desist received
- Critical contract vulnerability found post-deployment
- Unrecoverable key compromise
- Loss event >50% of capital

**Planned wind-down if:**
- ROI <50% for 3 consecutive months
- Competition makes strategy unviable
- Regulatory environment becomes hostile

---

## Key Metrics Dashboard

**Track these in real-time:**

```
System Health:
- State: NORMAL / THROTTLED / HALTED
- Uptime: 99.8% (7 days)
- Last Execution: 12 min ago
- Operator Balance: 0.47 ETH

Performance (24h):
- Opportunities: 47
- Submissions: 23
- Wins: 9
- Win Rate: 19.1%
- Inclusion Rate: 39.1%
- Net Profit: $387

Risk Metrics:
- Consecutive Failures: 0
- Daily Volume: $1,234 / $2,500
- Reserve Fund: 101% of target
```

---

## Exit Criteria Summary

### Phase 1 → Phase 2: GO if ALL true
- [ ] Base Case ROI >100%
- [ ] Win rate >15% in latency analysis
- [ ] Audit budget secured ($15-30K)
- [ ] All tests passing

### Phase 2 → Phase 3: GO if ALL true
- [ ] 60%+ inclusion on testnet (2 weeks)
- [ ] 95%+ uptime
- [ ] Professional audit complete (no high/critical findings)
- [ ] $1K-2K capital ready

### Tier 1 → Tier 2: GO if ALL true
- [ ] 100 successful executions
- [ ] Net positive profit (any amount >$0)
- [ ] 60%+ inclusion sustained
- [ ] Zero critical incidents
- [ ] Minimum 8 weeks elapsed

### Continue vs. Stop:

**Stop if:**
- 6 months of effort, still unprofitable
- Backtest shows <50% ROI
- Competition gap insurmountable
- <20 liquidations/month on Base

**Pivot if:**
- Strategy works on Ethereum but not Base
- Different MEV approach more viable
- Partnership opportunities emerge

---

## Final Checklist

### Code Deliverables
- [ ] Chimera.sol (audited)
- [ ] StateEngine, OpportunityDetector, ExecutionPlanner, SafetyController
- [ ] Main bot orchestrator
- [ ] Historical data collection script
- [ ] Backtest engine
- [ ] Comprehensive test suite

### Documentation Deliverables  
- [ ] README with setup instructions
- [ ] Backtest report with sensitivity analysis
- [ ] Testnet performance analysis
- [ ] Operational runbooks
- [ ] Smart contract audit report

### Infrastructure Deliverables
- [ ] AWS production environment
- [ ] Database with logging
- [ ] Secrets management
- [ ] Monitoring and alerting
- [ ] Backup operator procedures

### Validation Milestones
- [ ] Historical profitability proven (ROI >100%)
- [ ] Testnet operation validated (inclusion >60%)
- [ ] Professional security audit passed
- [ ] 100+ mainnet executions profitable

---

## Estimated Timeline

**Phase 1 (Local):** 12 weeks  
**Phase 2 (Testnet):** 8 weeks  
**Phase 3 Tier 1:** 8+ weeks  
**Phase 3 Tier 2:** 12+ weeks  
**Phase 3 Tier 3:** 12+ weeks  

**Total to full operation:** 52+ weeks (1 year minimum)

**Realistic expectations:**
- First mainnet profit: Month 6-7
- Meaningful profit ($5K+/mo): Month 12-18  
- Full-scale operation: Year 2+

---

**This is a marathon, not a sprint. Execute with discipline, scale with patience, optimize continuously.**

**END OF GUIDE**