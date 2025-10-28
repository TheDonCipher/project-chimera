# Operational Runbooks - Project Chimera

## Overview

This document contains operational procedures for responding to incidents and anomalies in the Chimera MEV liquidation bot. Each runbook provides step-by-step instructions for diagnosis, response, and recovery.

## Emergency Contacts

**Primary On-Call**: [Name] - [Phone] - [Email]  
**Secondary On-Call**: [Name] - [Phone] - [Email]  
**Infrastructure Lead**: [Name] - [Phone] - [Email]  
**Security Lead**: [Name] - [Phone] - [Email]

**Escalation Path**:

1. Primary On-Call (0-15 minutes)
2. Secondary On-Call (15-30 minutes)
3. Infrastructure Lead (30-60 minutes)
4. Security Lead (for security incidents)

**External Contacts**:

- AWS Support: [Account Number] - [Support Plan]
- RPC Provider Support: Alchemy, QuickNode
- Smart Contract Auditor: [Firm Name] - [Contact]

---

## Table of Contents

1. [HALTED State Recovery](#1-halted-state-recovery)
2. [Key Compromise Response](#2-key-compromise-response)
3. [Sequencer Outage Response](#3-sequencer-outage-response)
4. [Sustained Losses Response](#4-sustained-losses-response)
5. [Database/Redis Outage Recovery](#5-databaseredis-outage-recovery)
6. [RPC Provider Failover](#6-rpc-provider-failover)

---

## 1. HALTED State Recovery

**Severity**: HIGH  
**Response Time**: 15 minutes  
**Escalation**: Primary On-Call → Infrastructure Lead

### Symptoms

- CloudWatch alarm: "System State = HALTED"
- Bot logs show: "Entering HALTED state"
- No new executions being submitted
- Dashboard shows red status indicator

### Common Causes

- State divergence >10 BPS detected
- Inclusion rate dropped below 50%
- Simulation accuracy dropped below 85%
- 3 consecutive execution failures
- Sequencer anomaly detected

### Diagnosis Steps

1. **Check System Logs**

   ```bash
   # SSH into bot instance
   ssh -i ~/.ssh/chimera-key.pem ec2-user@<instance-ip>

   # View recent logs
   tail -n 100 /app/logs/chimera.log | grep "HALTED"

   # Check for state divergence
   grep "state_divergence" /app/logs/chimera.log | tail -n 20
   ```

2. **Query Database for Root Cause**

   ```bash
   # Connect to PostgreSQL
   psql -h <rds-endpoint> -U chimera -d chimera_db

   # Check recent system events
   SELECT * FROM system_events
   WHERE event_type = 'STATE_TRANSITION'
   ORDER BY timestamp DESC LIMIT 10;

   # Check for state divergences
   SELECT * FROM state_divergences
   WHERE timestamp > NOW() - INTERVAL '1 hour'
   ORDER BY divergence_bps DESC;

   # Check recent execution failures
   SELECT * FROM executions
   WHERE included = false
   ORDER BY timestamp DESC LIMIT 10;
   ```

3. **Check Performance Metrics**
   ```bash
   # View CloudWatch metrics
   aws cloudwatch get-metric-statistics \
     --namespace Chimera \
     --metric-name InclusionRate \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average
   ```

### Recovery Procedures

#### Scenario A: State Divergence Triggered HALT

**Root Cause**: Cached state diverged from canonical blockchain state

**Steps**:

1. Verify blockchain is stable (no major reorgs)
2. Clear Redis cache to force rebuild
   ```bash
   redis-cli -h <elasticache-endpoint> FLUSHDB
   ```
3. Restart bot to rebuild state from blockchain
   ```bash
   sudo systemctl restart chimera-bot
   ```
4. Monitor state reconciliation for 5 minutes
   ```bash
   tail -f /app/logs/chimera.log | grep "reconciliation"
   ```
5. If divergence persists, check RPC provider health
6. Once stable for 5 minutes, proceed to manual resume

#### Scenario B: Low Inclusion Rate Triggered HALT

**Root Cause**: Bundles not being included in blocks (<50% rate)

**Steps**:

1. Check if Base network is congested
   - Visit https://basescan.org/ and check gas prices
   - Compare current gas to historical average
2. Review recent bribe amounts
   ```sql
   SELECT AVG(bribe_wei), MIN(bribe_wei), MAX(bribe_wei)
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '1 hour';
   ```
3. Check if competitors increased activity
   - Review recent liquidations on BaseScan
   - Analyze time-to-inclusion for successful liquidations
4. Adjust bribe parameters if needed (see config.yaml)
5. If network is stable, consider increasing MIN_BRIBE_PERCENTAGE
6. Test with single execution before full resume

#### Scenario C: Low Simulation Accuracy Triggered HALT

**Root Cause**: Actual profits significantly differ from simulated (<85% accuracy)

**Steps**:

1. Review recent executions with large discrepancies
   ```sql
   SELECT protocol, borrower,
          simulated_profit_usd, actual_profit_usd,
          (actual_profit_usd / simulated_profit_usd) as accuracy
   FROM executions
   WHERE included = true
     AND timestamp > NOW() - INTERVAL '1 hour'
   ORDER BY accuracy ASC LIMIT 10;
   ```
2. Check for systematic issues:
   - DEX slippage higher than expected (>1%)
   - Gas costs miscalculated (L1 data cost changes)
   - Flash loan premiums changed
3. Review oracle price accuracy
4. If systematic issue found, update cost calculation parameters
5. Run simulation tests before resuming

#### Scenario D: Consecutive Failures Triggered HALT

**Root Cause**: 3 consecutive execution attempts failed

**Steps**:

1. Review failure reasons
   ```sql
   SELECT rejection_reason, COUNT(*)
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '1 hour'
     AND included = false
   GROUP BY rejection_reason;
   ```
2. Common failure patterns:
   - **Simulation reverts**: Protocol paused or position already liquidated
   - **Transaction reverts**: Insufficient profit or slippage exceeded
   - **Submission failures**: RPC errors or network issues
3. If protocol-specific issue, temporarily disable that protocol
4. If network issue, verify RPC provider health
5. Test with small execution before full resume

### Manual Resume Procedure

**Prerequisites**:

- Root cause identified and resolved
- System stable for minimum 5 minutes
- Operator approval obtained

**Steps**:

1. Connect to bot instance

   ```bash
   ssh -i ~/.ssh/chimera-key.pem ec2-user@<instance-ip>
   ```

2. Access Python shell

   ```bash
   cd /app
   source venv/bin/activate
   python3
   ```

3. Execute manual resume

   ```python
   from bot.src.safety_controller import SafetyController
   from bot.src.config import load_config

   config = load_config()
   safety = SafetyController(config)

   # Resume to NORMAL state
   safety.manual_resume()
   print(f"Current state: {safety.get_state()}")
   ```

4. Monitor for 15 minutes

   ```bash
   tail -f /app/logs/chimera.log
   ```

5. Verify metrics return to normal
   - Inclusion rate >60%
   - Simulation accuracy >90%
   - No immediate failures

### Validation Steps

- [ ] Root cause identified and documented
- [ ] Corrective action taken
- [ ] System stable for 5+ minutes
- [ ] Manual resume executed successfully
- [ ] First execution after resume succeeded
- [ ] Metrics within acceptable ranges
- [ ] Incident documented in system_events table
- [ ] Post-incident review scheduled

### Escalation Criteria

Escalate to Infrastructure Lead if:

- Unable to identify root cause within 30 minutes
- Issue persists after manual resume
- Multiple HALT events within 1 hour
- Suspected security incident

---

## 2. Key Compromise Response

**Severity**: CRITICAL  
**Response Time**: IMMEDIATE  
**Escalation**: Security Lead + Infrastructure Lead (parallel notification)

### Symptoms

- Unauthorized transactions from operator wallet
- Unexpected balance changes
- Alerts from wallet monitoring service
- Suspicious AWS Secrets Manager access logs
- Unauthorized contract interactions

### Immediate Actions (First 5 Minutes)

**DO NOT DELAY - Execute immediately upon suspicion**

1. **Pause Smart Contract**

   ```bash
   # From secure machine with treasury key
   cast send <CHIMERA_CONTRACT_ADDRESS> \
     "pause()" \
     --private-key <TREASURY_PRIVATE_KEY> \
     --rpc-url https://mainnet.base.org
   ```

2. **Stop Bot Service**

   ```bash
   ssh -i ~/.ssh/chimera-key.pem ec2-user@<instance-ip>
   sudo systemctl stop chimera-bot
   ```

3. **Revoke Compromised Key Access**

   ```bash
   # Rotate AWS Secrets Manager secret immediately
   aws secretsmanager rotate-secret \
     --secret-id chimera/operator-key \
     --rotation-lambda-arn <ROTATION_LAMBDA_ARN>
   ```

4. **Notify Security Team**
   - Call Security Lead immediately
   - Send email to security@company.com
   - Create incident ticket: "CRITICAL: Chimera Key Compromise"

### Investigation Steps (First 30 Minutes)

1. **Review Operator Wallet Activity**

   ```bash
   # Check all transactions from operator address
   # Visit BaseScan: https://basescan.org/address/<OPERATOR_ADDRESS>

   # Download transaction history
   curl "https://api.basescan.org/api?module=account&action=txlist&address=<OPERATOR_ADDRESS>&startblock=0&endblock=99999999&sort=desc&apikey=<API_KEY>"
   ```

2. **Audit AWS Access Logs**

   ```bash
   # Check Secrets Manager access
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceName,AttributeValue=chimera/operator-key \
     --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S) \
     --max-results 50

   # Check for unauthorized EC2 access
   aws cloudtrail lookup-events \
     --lookup-attributes AttributeKey=ResourceType,AttributeValue=AWS::EC2::Instance \
     --start-time $(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%S)
   ```

3. **Review Bot Logs for Anomalies**

   ```bash
   # Check for unusual execution patterns
   grep "executeLiquidation" /app/logs/chimera.log | tail -n 100

   # Check for configuration changes
   grep "config" /app/logs/chimera.log | tail -n 50
   ```

4. **Assess Financial Impact**

   ```sql
   -- Connect to database
   psql -h <rds-endpoint> -U chimera -d chimera_db

   -- Check recent executions
   SELECT timestamp, tx_hash, actual_profit_usd, operator_address
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '24 hours'
   ORDER BY timestamp DESC;

   -- Calculate total exposure
   SELECT SUM(actual_profit_usd) as total_at_risk
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '7 days';
   ```

### Key Rotation Procedure (After Investigation)

**Prerequisites**:

- Compromise confirmed or suspected
- Contract paused
- Bot service stopped
- Security team notified

**Steps**:

1. **Generate New Operator Key**

   ```bash
   # On secure, air-gapped machine
   cast wallet new
   # Save output securely: Address and Private Key
   ```

2. **Fund New Operator Wallet**

   ```bash
   # From treasury wallet, send 0.5 ETH for gas
   cast send <NEW_OPERATOR_ADDRESS> \
     --value 0.5ether \
     --private-key <TREASURY_PRIVATE_KEY> \
     --rpc-url https://mainnet.base.org
   ```

3. **Update AWS Secrets Manager**

   ```bash
   # Store new key in Secrets Manager
   aws secretsmanager update-secret \
     --secret-id chimera/operator-key \
     --secret-string '{"private_key":"<NEW_PRIVATE_KEY>"}'

   # Verify update
   aws secretsmanager get-secret-value \
     --secret-id chimera/operator-key \
     --query SecretString \
     --output text
   ```

4. **Update Bot Configuration**

   ```bash
   # SSH to bot instance
   ssh -i ~/.ssh/chimera-key.pem ec2-user@<instance-ip>

   # Update config.yaml with new operator address
   sudo nano /app/config.yaml
   # Update: operator_address: "<NEW_OPERATOR_ADDRESS>"
   ```

5. **Drain Old Operator Wallet**

   ```bash
   # Transfer remaining funds to treasury
   cast send <TREASURY_ADDRESS> \
     --value <REMAINING_BALANCE> \
     --private-key <OLD_PRIVATE_KEY> \
     --rpc-url https://mainnet.base.org
   ```

6. **Update Monitoring Alerts**
   ```bash
   # Update CloudWatch alarms with new operator address
   aws cloudwatch put-metric-alarm \
     --alarm-name chimera-operator-balance-low \
     --alarm-description "Operator balance below 0.1 ETH" \
     --metric-name OperatorBalance \
     --namespace Chimera \
     --statistic Average \
     --period 300 \
     --threshold 0.1 \
     --comparison-operator LessThanThreshold
   ```

### Security Audit Steps

1. **Full System Audit**

   - Review all AWS IAM permissions
   - Audit EC2 security groups
   - Review RDS access logs
   - Check for unauthorized SSH access
   - Scan for malware/backdoors

2. **Code Review**

   ```bash
   # Check for unauthorized code changes
   cd /app
   git status
   git diff HEAD

   # Verify code integrity
   sha256sum bot/src/*.py
   ```

3. **Infrastructure Review**

   - Rotate all AWS access keys
   - Review VPC security groups
   - Check for unauthorized EC2 instances
   - Audit S3 bucket permissions
   - Review CloudTrail logs comprehensively

4. **Third-Party Review**
   - Engage external security firm if needed
   - Conduct penetration testing
   - Review smart contract security

### Recovery and Resume

**Prerequisites**:

- New key generated and deployed
- Security audit completed
- No ongoing unauthorized activity
- All access logs reviewed
- Incident fully documented

**Steps**:

1. **Restart Bot with New Key**

   ```bash
   sudo systemctl start chimera-bot

   # Monitor startup
   tail -f /app/logs/chimera.log
   ```

2. **Verify New Key Operation**

   ```bash
   # Check operator address in logs
   grep "operator_address" /app/logs/chimera.log | tail -n 5

   # Verify balance
   cast balance <NEW_OPERATOR_ADDRESS> --rpc-url https://mainnet.base.org
   ```

3. **Unpause Smart Contract**

   ```bash
   # From secure machine with treasury key
   cast send <CHIMERA_CONTRACT_ADDRESS> \
     "unpause()" \
     --private-key <TREASURY_PRIVATE_KEY> \
     --rpc-url https://mainnet.base.org
   ```

4. **Test Execution**

   - Monitor for first successful execution
   - Verify transaction signed by new operator address
   - Confirm profit flows to treasury

5. **Enhanced Monitoring**
   - Increase alert sensitivity for 7 days
   - Daily manual review of all transactions
   - Weekly security check-ins

### Post-Incident Actions

- [ ] Incident report completed
- [ ] Root cause analysis documented
- [ ] Security improvements implemented
- [ ] Key rotation schedule reviewed
- [ ] Insurance claim filed (if applicable)
- [ ] Legal counsel consulted (if needed)
- [ ] Team debrief scheduled
- [ ] Monitoring enhanced

### Prevention Measures

- Implement hardware wallet for operator key (Ledger/Trezor)
- Enable AWS GuardDuty for threat detection
- Implement IP whitelisting for AWS access
- Require MFA for all AWS console access
- Reduce operator wallet balance to minimum (0.1 ETH)
- Implement transaction signing service with approval workflow
- Schedule regular key rotation (90 days)
- Conduct quarterly security audits

---

## 3. Sequencer Outage Response

**Severity**: HIGH  
**Response Time**: 10 minutes  
**Escalation**: Infrastructure Lead

### Symptoms

- No new blocks being produced on Base L2
- WebSocket connection receiving no newHeads events
- Block timestamp not advancing
- Bot logs show: "Sequencer anomaly detected"
- System automatically enters HALTED state

### Detection Indicators

1. **Block Production Stall**

   - No new block for >10 seconds
   - Last block timestamp >20 seconds old

2. **Unusual Reorg Depth**

   - Reorg depth >3 blocks
   - Multiple reorgs in short period

3. **Block Number Gaps**
   - Non-sequential block numbers
   - Missing blocks in sequence

### Diagnosis Steps

1. **Verify Sequencer Status**

   ```bash
   # Check Base status page
   curl https://status.base.org/api/v2/status.json

   # Check latest block
   cast block-number --rpc-url https://mainnet.base.org

   # Check block timestamp
   cast block latest --rpc-url https://mainnet.base.org | grep timestamp
   ```

2. **Check Multiple RPC Providers**

   ```bash
   # Alchemy
   cast block-number --rpc-url https://base-mainnet.g.alchemy.com/v2/<KEY>

   # QuickNode
   cast block-number --rpc-url https://base-mainnet.quiknode.pro/<KEY>

   # Public RPC
   cast block-number --rpc-url https://mainnet.base.org
   ```

3. **Review Bot Logs**

   ```bash
   tail -n 100 /app/logs/chimera.log | grep -E "sequencer|block|timestamp"
   ```

4. **Check Community Reports**
   - Base Discord: https://discord.gg/base
   - Base Twitter: https://twitter.com/base
   - Base Status: https://status.base.org

### Response Procedures

#### Scenario A: Confirmed Sequencer Outage

**Indicators**: All RPC providers show same stalled block, Base status page confirms outage

**Steps**:

1. **Verify Bot is HALTED**

   ```bash
   grep "HALTED" /app/logs/chimera.log | tail -n 5
   ```

2. **Monitor Base Status**

   - Set up alert for status page updates
   - Join Base Discord for real-time updates
   - Monitor Base Twitter for announcements

3. **Estimate Downtime Impact**

   ```sql
   -- Calculate missed opportunities (historical average)
   SELECT AVG(opportunities_per_hour) * <estimated_hours_down> as missed_opportunities
   FROM (
     SELECT DATE_TRUNC('hour', timestamp) as hour,
            COUNT(*) as opportunities_per_hour
     FROM executions
     WHERE timestamp > NOW() - INTERVAL '7 days'
     GROUP BY hour
   ) subquery;
   ```

4. **Wait for Sequencer Recovery**

   - Do NOT attempt to resume during outage
   - Do NOT modify bot configuration
   - Keep bot service running (will auto-recover)

5. **Monitor Recovery**
   ```bash
   # Watch for new blocks
   watch -n 5 'cast block-number --rpc-url https://mainnet.base.org'
   ```

#### Scenario B: RPC Provider Issue (Not Sequencer)

**Indicators**: Some RPC providers show stalled blocks, others show progress

**Steps**:

1. **Identify Healthy Provider**

   ```bash
   # Test each provider
   for provider in alchemy quicknode public; do
     echo "Testing $provider..."
     cast block-number --rpc-url <provider-url>
   done
   ```

2. **Update Bot Configuration**

   ```bash
   # Edit config.yaml to prioritize healthy provider
   sudo nano /app/config.yaml

   # Move healthy provider to primary position
   rpc_providers:
     primary: <healthy-provider-url>
     backup: <secondary-provider-url>
   ```

3. **Restart Bot**

   ```bash
   sudo systemctl restart chimera-bot
   ```

4. **Verify Connection**

   ```bash
   tail -f /app/logs/chimera.log | grep "WebSocket connected"
   ```

5. **Contact Failing Provider**
   - Report issue to provider support
   - Request status update
   - Consider alternative provider

#### Scenario C: Temporary Sequencer Hiccup

**Indicators**: Brief stall (<30 seconds), then recovery

**Steps**:

1. **Monitor State Engine Recovery**

   ```bash
   tail -f /app/logs/chimera.log | grep "reconciliation"
   ```

2. **Verify State Consistency**

   ```bash
   # Check for state divergence
   grep "state_divergence" /app/logs/chimera.log | tail -n 10
   ```

3. **If State Divergence Detected**

   - Bot will automatically HALT
   - Follow HALTED State Recovery runbook
   - Clear Redis cache if needed

4. **If No Divergence**
   - Bot should auto-recover to NORMAL
   - Monitor for 15 minutes
   - Verify executions resume

### Post-Outage Recovery

**After sequencer resumes normal operation:**

1. **Verify Block Production**

   ```bash
   # Confirm blocks producing every ~2 seconds
   for i in {1..10}; do
     cast block-number --rpc-url https://mainnet.base.org
     sleep 2
   done
   ```

2. **Check State Consistency**

   ```bash
   # Force state reconciliation
   # Bot will automatically reconcile on next block
   tail -f /app/logs/chimera.log | grep "reconciliation"
   ```

3. **Manual Resume if Needed**

   - If bot remains HALTED after 5 minutes of stable blocks
   - Follow HALTED State Recovery runbook
   - Execute manual_resume()

4. **Monitor Initial Executions**
   - Watch first 5-10 executions closely
   - Verify simulation accuracy
   - Confirm inclusion rates normal

### Validation Steps

- [ ] Sequencer producing blocks normally
- [ ] All RPC providers synchronized
- [ ] Bot state reconciliation successful
- [ ] No state divergence detected
- [ ] First execution post-recovery successful
- [ ] Inclusion rate returns to normal (>60%)
- [ ] Incident documented

### Escalation Criteria

Escalate to Infrastructure Lead if:

- Sequencer outage exceeds 1 hour
- Repeated outages (>3 in 24 hours)
- State corruption detected post-recovery
- Financial losses incurred

### Long-Term Mitigation

- Implement L1 fallback mechanism (future enhancement)
- Diversify to multiple L2s (Arbitrum, Optimism)
- Maintain reserve fund for extended outages
- Negotiate SLA with Base team (if available)

---

## 4. Sustained Losses Response

**Severity**: HIGH  
**Response Time**: 24 hours (for analysis), IMMEDIATE (if critical threshold)  
**Escalation**: Infrastructure Lead + Financial Controller

### Symptoms

- Negative cumulative profit over 7+ days
- Daily losses exceeding $500
- Inclusion rate declining trend
- Simulation accuracy declining trend
- Increasing gas costs eating into profits

### Detection Thresholds

**WARNING** (Yellow Alert):

- 3 consecutive days of losses
- Weekly profit <$100
- Monthly ROI <50%

**CRITICAL** (Red Alert):

- 7 consecutive days of losses
- Weekly loss >$1,000
- Monthly ROI <0% (net negative)
- Reserve fund depleted >50%

### Analysis Steps

1. **Calculate Financial Performance**

   ```sql
   -- Connect to database
   psql -h <rds-endpoint> -U chimera -d chimera_db

   -- Daily profit/loss for last 30 days
   SELECT DATE(timestamp) as date,
          COUNT(*) as executions,
          SUM(actual_profit_usd) as daily_profit,
          AVG(actual_profit_usd) as avg_profit_per_execution
   FROM executions
   WHERE included = true
     AND timestamp > NOW() - INTERVAL '30 days'
   GROUP BY DATE(timestamp)
   ORDER BY date DESC;

   -- Weekly summary
   SELECT DATE_TRUNC('week', timestamp) as week,
          COUNT(*) as executions,
          SUM(actual_profit_usd) as weekly_profit,
          AVG(actual_profit_usd) as avg_profit
   FROM executions
   WHERE included = true
     AND timestamp > NOW() - INTERVAL '90 days'
   GROUP BY week
   ORDER BY week DESC;

   -- Cost breakdown
   SELECT AVG(l2_gas_cost_usd) as avg_l2_gas,
          AVG(l1_data_cost_usd) as avg_l1_data,
          AVG(bribe_usd) as avg_bribe,
          AVG(flash_loan_cost_usd) as avg_flash_loan,
          AVG(slippage_cost_usd) as avg_slippage,
          AVG(total_cost_usd) as avg_total_cost
   FROM executions
   WHERE included = true
     AND timestamp > NOW() - INTERVAL '7 days';
   ```

2. **Identify Root Causes**

   **A. Competition Analysis**

   ```sql
   -- Win rate trend
   SELECT DATE(timestamp) as date,
          COUNT(*) as opportunities,
          SUM(CASE WHEN included THEN 1 ELSE 0 END) as wins,
          (SUM(CASE WHEN included THEN 1 ELSE 0 END)::float / COUNT(*)) * 100 as win_rate
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '30 days'
   GROUP BY DATE(timestamp)
   ORDER BY date DESC;
   ```

   **B. Cost Analysis**

   ```sql
   -- Cost trend over time
   SELECT DATE(timestamp) as date,
          AVG(total_cost_usd) as avg_cost,
          AVG(bribe_usd) as avg_bribe,
          AVG(l2_gas_cost_usd + l1_data_cost_usd) as avg_gas
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '30 days'
   GROUP BY DATE(timestamp)
   ORDER BY date DESC;
   ```

   **C. Opportunity Quality**

   ```sql
   -- Average profit per opportunity
   SELECT DATE(timestamp) as date,
          AVG(simulated_profit_usd) as avg_simulated,
          AVG(actual_profit_usd) as avg_actual,
          AVG(actual_profit_usd / simulated_profit_usd) as accuracy
   FROM executions
   WHERE included = true
     AND timestamp > NOW() - INTERVAL '30 days'
   GROUP BY DATE(timestamp)
   ORDER BY date DESC;
   ```

3. **Market Condition Analysis**
   - Check Base network gas prices (historical trend)
   - Review lending protocol TVL (declining = fewer opportunities)
   - Analyze competitor activity (new bots entering market)
   - Check ETH price volatility (affects liquidation frequency)

### Response Procedures

#### Scenario A: High Competition (Low Win Rate)

**Indicators**: Win rate <15%, bribes increasing, still losing to competitors

**Actions**:

1. **Increase Bribe Aggressiveness**

   ```yaml
   # Edit config.yaml
   execution:
     min_bribe_percentage: 0.20 # Increase from 0.15
     max_bribe_percentage: 0.50 # Increase from 0.40
     bribe_increase_step: 0.07 # Increase from 0.05
   ```

2. **Optimize Latency**

   - Review detection latency (target <500ms)
   - Review simulation latency (target <1000ms)
   - Consider upgrading to faster RPC tier
   - Consider co-location with RPC provider

3. **Explore Alternative Submission Paths**

   - Test private RPC endpoints
   - Explore Base-native builder relationships
   - Consider MEV relay partnerships

4. **Adjust Profitability Threshold**
   ```yaml
   # Edit config.yaml
   execution:
     min_profit_usd: 75 # Increase from 50 to be more selective
   ```

#### Scenario B: Rising Costs (Gas/L1 Data)

**Indicators**: Gas costs up >50%, L1 data costs increasing, profit margins compressed

**Actions**:

1. **Update Cost Calculation Parameters**

   ```yaml
   # Edit config.yaml
   costs:
     l1_scalar_multiplier: 1.2 # Add safety margin
     gas_price_multiplier: 1.15 # Add safety margin
     slippage_percentage: 0.015 # Increase from 0.01
   ```

2. **Increase Minimum Profit Threshold**

   ```yaml
   execution:
     min_profit_usd: 100 # Increase from 50
   ```

3. **Optimize Transaction Size**

   - Review calldata size
   - Minimize unnecessary data
   - Consider batch operations (future)

4. **Wait for Gas Prices to Normalize**
   - If temporary spike, pause operations
   - Monitor gas price trends
   - Resume when costs return to normal

#### Scenario C: Poor Opportunity Quality

**Indicators**: Fewer liquidations, smaller positions, lower profit per execution

**Actions**:

1. **Expand Protocol Coverage**

   - Add new lending protocols (Aave, Compound)
   - Monitor new protocols launching on Base
   - Diversify beyond liquidations (arbitrage, sandwich)

2. **Adjust Opportunity Filters**

   ```yaml
   # Edit config.yaml
   opportunity:
     min_health_factor: 0.95 # Detect earlier (from 1.0)
     confirmation_blocks: 1 # Reduce from 2 for speed
   ```

3. **Geographic Expansion**

   - Deploy to multiple L2s (Arbitrum, Optimism)
   - Consider L1 opportunities
   - Explore other EVM chains

4. **Strategy Diversification**
   - Implement arbitrage detection
   - Add sandwich attack capability
   - Explore JIT liquidity provision

#### Scenario D: Systematic Simulation Errors

**Indicators**: Simulation accuracy <85%, consistent overestimation of profits

**Actions**:

1. **Audit Simulation Logic**

   ```bash
   # Review recent simulation errors
   grep "simulation" /app/logs/chimera.log | tail -n 100
   ```

2. **Update Cost Models**

   - Recalibrate flash loan premium
   - Update DEX slippage estimates
   - Verify L1 data cost calculation

3. **Add Safety Margins**

   ```yaml
   # Edit config.yaml
   simulation:
     profit_safety_margin: 0.20 # Require 20% buffer
     min_profit_multiplier: 1.5 # Require 1.5x minimum
   ```

4. **Implement Profit Verification**
   - Add post-execution profit verification
   - Alert on large discrepancies
   - Halt if accuracy drops below threshold

### Shutdown Decision Framework

**Temporary Pause** (Reversible):

- 7 consecutive days of losses
- Monthly ROI <25%
- Reserve fund depleted >50%
- Market conditions temporarily unfavorable

**Permanent Shutdown** (Final):

- 3 consecutive months of losses
- Cumulative losses >$10,000
- Fundamental strategy invalidated
- Regulatory/legal concerns
- Unrecoverable security incident

### Temporary Pause Procedure

1. **Enter HALTED State**

   ```python
   from bot.src.safety_controller import SafetyController
   safety = SafetyController(config)
   safety.force_halt(reason="Sustained losses - temporary pause")
   ```

2. **Preserve State**

   ```bash
   # Backup database
   pg_dump -h <rds-endpoint> -U chimera chimera_db > backup_$(date +%Y%m%d).sql

   # Backup Redis
   redis-cli -h <elasticache-endpoint> SAVE
   ```

3. **Reduce Infrastructure Costs**

   ```bash
   # Stop bot service
   sudo systemctl stop chimera-bot

   # Downgrade EC2 instance (optional)
   aws ec2 modify-instance-attribute \
     --instance-id <instance-id> \
     --instance-type t3.small
   ```

4. **Set Review Date**
   - Schedule review in 2-4 weeks
   - Monitor market conditions
   - Analyze competitor activity
   - Reassess strategy viability

### Permanent Shutdown Procedure

1. **Pause Smart Contract**

   ```bash
   cast send <CHIMERA_CONTRACT_ADDRESS> \
     "pause()" \
     --private-key <TREASURY_PRIVATE_KEY> \
     --rpc-url https://mainnet.base.org
   ```

2. **Drain All Funds**

   ```bash
   # Drain operator wallet
   cast send <TREASURY_ADDRESS> \
     --value <FULL_BALANCE> \
     --private-key <OPERATOR_PRIVATE_KEY> \
     --rpc-url https://mainnet.base.org

   # Verify treasury balance
   cast balance <TREASURY_ADDRESS> --rpc-url https://mainnet.base.org
   ```

3. **Archive Data**

   ```bash
   # Full database export
   pg_dump -h <rds-endpoint> -U chimera chimera_db > final_backup.sql

   # Export to S3 for long-term storage
   aws s3 cp final_backup.sql s3://chimera-archives/final_backup_$(date +%Y%m%d).sql

   # Export logs
   tar -czf logs_archive.tar.gz /app/logs/
   aws s3 cp logs_archive.tar.gz s3://chimera-archives/
   ```

4. **Decommission Infrastructure**

   ```bash
   # Terminate EC2 instance
   aws ec2 terminate-instances --instance-ids <instance-id>

   # Delete RDS instance (with final snapshot)
   aws rds delete-db-instance \
     --db-instance-identifier chimera-db \
     --final-db-snapshot-identifier chimera-final-snapshot

   # Delete ElastiCache cluster
   aws elasticache delete-cache-cluster --cache-cluster-id chimera-redis
   ```

5. **Financial Reconciliation**

   - Calculate final P&L
   - Document all expenses
   - File final tax documentation
   - Close accounting books

6. **Post-Mortem Report**
   - Document lessons learned
   - Analyze what went wrong
   - Identify improvement opportunities
   - Share findings with team

### Validation Steps

- [ ] Financial analysis completed
- [ ] Root cause identified
- [ ] Corrective actions implemented
- [ ] Performance monitored for 7 days
- [ ] Decision documented (continue/pause/shutdown)
- [ ] Stakeholders notified
- [ ] Financial records updated

### Escalation Criteria

Escalate to Financial Controller if:

- Cumulative losses exceed $5,000
- Monthly ROI negative for 2 consecutive months
- Shutdown decision required
- Legal/tax implications

---

## 5. Database/Redis Outage Recovery

**Severity**: MEDIUM  
**Response Time**: 30 minutes  
**Escalation**: Infrastructure Lead

### Symptoms

**PostgreSQL Outage**:

- Connection errors in bot logs
- Unable to write execution records
- Database queries timing out
- RDS CloudWatch alarms firing

**Redis Outage**:

- Cache connection errors
- Increased RPC calls (no cache hits)
- Slower opportunity detection
- ElastiCache CloudWatch alarms firing

### Diagnosis Steps

1. **Check Database Connectivity**

   ```bash
   # Test PostgreSQL connection
   psql -h <rds-endpoint> -U chimera -d chimera_db -c "SELECT 1;"

   # Check RDS status
   aws rds describe-db-instances \
     --db-instance-identifier chimera-db \
     --query 'DBInstances[0].DBInstanceStatus'
   ```

2. **Check Redis Connectivity**

   ```bash
   # Test Redis connection
   redis-cli -h <elasticache-endpoint> PING

   # Check ElastiCache status
   aws elasticache describe-cache-clusters \
     --cache-cluster-id chimera-redis \
     --query 'CacheClusters[0].CacheClusterStatus'
   ```

3. **Review AWS Service Health**

   ```bash
   # Check for AWS service issues
   aws health describe-events \
     --filter eventTypeCategories=issue \
     --query 'events[?service==`RDS` || service==`ELASTICACHE`]'
   ```

4. **Check Bot Behavior**
   ```bash
   # Check if bot is using fallback mechanisms
   grep -E "fallback|queue|memory" /app/logs/chimera.log | tail -n 50
   ```

### Recovery Procedures

#### Scenario A: PostgreSQL Connection Loss

**Indicators**: Database connection errors, writes failing, reads timing out

**Steps**:

1. **Verify Bot Fallback Active**

   ```bash
   # Bot should queue writes in memory
   grep "Queueing execution record" /app/logs/chimera.log | tail -n 20
   ```

2. **Check RDS Instance Health**

   ```bash
   # Check CPU, memory, connections
   aws cloudwatch get-metric-statistics \
     --namespace AWS/RDS \
     --metric-name CPUUtilization \
     --dimensions Name=DBInstanceIdentifier,Value=chimera-db \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average
   ```

3. **Attempt Connection Recovery**

   ```bash
   # Restart bot to reset connection pool
   sudo systemctl restart chimera-bot

   # Monitor reconnection
   tail -f /app/logs/chimera.log | grep "database"
   ```

4. **If RDS Instance Unresponsive**

   ```bash
   # Reboot RDS instance (last resort)
   aws rds reboot-db-instance --db-instance-identifier chimera-db

   # Wait for available status (5-10 minutes)
   aws rds wait db-instance-available --db-instance-identifier chimera-db
   ```

5. **Verify Data Integrity**

   ```sql
   -- Connect to database
   psql -h <rds-endpoint> -U chimera -d chimera_db

   -- Check for gaps in execution records
   SELECT MIN(timestamp), MAX(timestamp), COUNT(*)
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '2 hours';

   -- Check for queued records that need manual insertion
   -- (Bot will auto-flush queue on reconnection)
   ```

#### Scenario B: Redis Cache Outage

**Indicators**: Cache connection errors, increased RPC calls, slower performance

**Steps**:

1. **Verify Bot Fallback Active**

   ```bash
   # Bot should use in-memory cache
   grep "Using in-memory cache" /app/logs/chimera.log | tail -n 10
   ```

2. **Check ElastiCache Health**

   ```bash
   # Check cache node status
   aws elasticache describe-cache-clusters \
     --cache-cluster-id chimera-redis \
     --show-cache-node-info

   # Check memory usage
   aws cloudwatch get-metric-statistics \
     --namespace AWS/ElastiCache \
     --metric-name DatabaseMemoryUsagePercentage \
     --dimensions Name=CacheClusterId,Value=chimera-redis \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average
   ```

3. **Attempt Reconnection**

   ```bash
   # Restart bot to reset Redis connection
   sudo systemctl restart chimera-bot

   # Monitor reconnection
   tail -f /app/logs/chimera.log | grep "Redis"
   ```

4. **If ElastiCache Unresponsive**

   ```bash
   # Reboot cache cluster
   aws elasticache reboot-cache-cluster \
     --cache-cluster-id chimera-redis \
     --cache-node-ids-to-reboot 0001

   # Wait for available status
   watch -n 10 'aws elasticache describe-cache-clusters \
     --cache-cluster-id chimera-redis \
     --query "CacheClusters[0].CacheClusterStatus"'
   ```

5. **Rebuild Cache from Blockchain**

   ```bash
   # Bot will automatically rebuild on reconnection
   # Monitor rebuild progress
   tail -f /app/logs/chimera.log | grep "cache_rebuild"

   # Verify cache populated
   redis-cli -h <elasticache-endpoint> DBSIZE
   ```

#### Scenario C: Extended Outage (>5 Minutes)

**Indicators**: Database/Redis unavailable for extended period, queue filling up

**Steps**:

1. **Check Queue Status**

   ```bash
   # Monitor queue size in logs
   grep "queue_size" /app/logs/chimera.log | tail -n 20
   ```

2. **If Queue Approaching Limit (>80 items)**

   ```bash
   # Bot will enter HALTED state automatically
   # This prevents memory overflow
   grep "Queue full" /app/logs/chimera.log
   ```

3. **Failover to Backup (If Available)**

   ```bash
   # If Multi-AZ RDS configured
   aws rds failover-db-cluster --db-cluster-identifier chimera-cluster

   # If Redis replica available
   # Update config.yaml with replica endpoint
   sudo nano /app/config.yaml
   sudo systemctl restart chimera-bot
   ```

4. **Consider Temporary Pause**

   - If outage exceeds 15 minutes
   - If data integrity concerns
   - If queue overflow imminent
   - Manually enter HALTED state

5. **Post-Recovery Data Reconciliation**

   ```sql
   -- Check for missing execution records
   -- Compare bot logs with database records

   -- Get execution count from logs
   grep "Bundle submitted" /app/logs/chimera.log | wc -l

   -- Get execution count from database
   SELECT COUNT(*) FROM executions
   WHERE timestamp > '<outage_start_time>';

   -- Identify gaps and manually insert if needed
   ```

### Data Integrity Verification

1. **Verify Execution Records**

   ```sql
   -- Check for duplicate records
   SELECT tx_hash, COUNT(*)
   FROM executions
   GROUP BY tx_hash
   HAVING COUNT(*) > 1;

   -- Check for missing timestamps
   SELECT COUNT(*)
   FROM executions
   WHERE timestamp IS NULL;

   -- Verify profit calculations
   SELECT * FROM executions
   WHERE actual_profit_usd < 0
     AND included = true
   ORDER BY timestamp DESC LIMIT 10;
   ```

2. **Verify State Divergence Records**

   ```sql
   -- Check for anomalies during outage
   SELECT * FROM state_divergences
   WHERE timestamp BETWEEN '<outage_start>' AND '<outage_end>'
   ORDER BY divergence_bps DESC;
   ```

3. **Verify Cache Consistency**
   ```bash
   # Compare cached positions with blockchain
   # Bot does this automatically via reconciliation
   grep "reconciliation" /app/logs/chimera.log | tail -n 50
   ```

### Validation Steps

- [ ] Database/Redis connectivity restored
- [ ] Bot reconnected successfully
- [ ] Queued records flushed to database
- [ ] Cache rebuilt from blockchain
- [ ] No data integrity issues detected
- [ ] Bot resumed normal operation
- [ ] Performance metrics normal
- [ ] Incident documented

### Escalation Criteria

Escalate to Infrastructure Lead if:

- Outage exceeds 30 minutes
- Data integrity issues detected
- Repeated outages (>3 in 24 hours)
- AWS service-wide issue
- Failover unsuccessful

### Prevention Measures

- Enable Multi-AZ deployment for RDS
- Configure Redis replica for failover
- Increase queue size limit
- Implement database connection retry logic
- Set up proactive monitoring and alerts
- Schedule regular maintenance windows
- Test failover procedures quarterly

---

## 6. RPC Provider Failover

**Severity**: MEDIUM  
**Response Time**: 5 minutes (automatic), 15 minutes (manual)  
**Escalation**: Infrastructure Lead (if all providers fail)

### Symptoms

- WebSocket disconnection errors
- RPC request timeouts
- Increased latency (>2 seconds)
- Rate limiting errors (429 status)
- Stale data (old block numbers)

### Automatic Failover

**Bot automatically handles most RPC issues:**

1. **Primary WebSocket Fails**

   - Automatically switches to backup WebSocket
   - Reconnects with exponential backoff
   - Logs failover event

2. **Both WebSockets Fail**

   - Falls back to HTTP polling
   - Polls every 2 seconds
   - Logs degraded mode

3. **All Providers Fail**
   - Enters HALTED state
   - Alerts operators
   - Waits for manual intervention

### Diagnosis Steps

1. **Check RPC Provider Status**

   ```bash
   # Test each provider
   echo "Testing Alchemy..."
   cast block-number --rpc-url https://base-mainnet.g.alchemy.com/v2/<KEY>

   echo "Testing QuickNode..."
   cast block-number --rpc-url https://base-mainnet.quiknode.pro/<KEY>

   echo "Testing Public RPC..."
   cast block-number --rpc-url https://mainnet.base.org
   ```

2. **Check Provider Status Pages**

   - Alchemy: https://status.alchemy.com/
   - QuickNode: https://status.quiknode.com/
   - Base: https://status.base.org/

3. **Review Bot Logs**

   ```bash
   # Check for failover events
   grep -E "WebSocket|RPC|failover" /app/logs/chimera.log | tail -n 50

   # Check current provider
   grep "Connected to RPC" /app/logs/chimera.log | tail -n 5
   ```

4. **Test Latency**
   ```bash
   # Measure response time for each provider
   for provider in alchemy quicknode public; do
     echo "Testing $provider..."
     time cast block-number --rpc-url <provider-url>
   done
   ```

### Manual Failover Procedures

#### Scenario A: Primary Provider Degraded

**Indicators**: High latency (>2s), intermittent failures, rate limiting

**Steps**:

1. **Verify Backup Provider Healthy**

   ```bash
   cast block-number --rpc-url <backup-provider-url>
   ```

2. **Update Configuration**

   ```yaml
   # Edit config.yaml
   rpc_providers:
     primary: <backup-provider-url> # Swap with backup
     backup: <primary-provider-url>
   ```

3. **Restart Bot**

   ```bash
   sudo systemctl restart chimera-bot

   # Verify connection
   tail -f /app/logs/chimera.log | grep "WebSocket connected"
   ```

4. **Monitor Performance**

   ```bash
   # Check latency improved
   grep "latency" /app/logs/chimera.log | tail -n 20
   ```

5. **Contact Provider Support**
   - Report degraded performance
   - Request status update
   - Consider upgrading tier

#### Scenario B: Rate Limiting (429 Errors)

**Indicators**: 429 HTTP status codes, "rate limit exceeded" errors

**Steps**:

1. **Check Current Usage**

   ```bash
   # Count requests in last hour
   grep "RPC request" /app/logs/chimera.log | \
     grep "$(date -u -d '1 hour ago' +%Y-%m-%d)" | wc -l
   ```

2. **Review Provider Limits**

   - Alchemy: Check dashboard for usage
   - QuickNode: Check dashboard for usage
   - Verify current tier limits

3. **Optimize Request Patterns**

   ```yaml
   # Edit config.yaml to reduce polling frequency
   state_engine:
     reconciliation_interval: 2 # Increase from 1 block
     scan_interval: 10 # Increase from 5 seconds
   ```

4. **Upgrade Provider Tier**

   - If consistently hitting limits
   - Calculate ROI of higher tier
   - Upgrade via provider dashboard

5. **Add Additional Provider**
   ```yaml
   # Edit config.yaml
   rpc_providers:
     primary: <provider1-url>
     backup: <provider2-url>
     tertiary: <provider3-url> # Add third provider
   ```

#### Scenario C: All Providers Unavailable

**Indicators**: All RPC requests failing, bot in HALTED state

**Steps**:

1. **Verify Network Connectivity**

   ```bash
   # Test internet connection
   ping -c 5 8.8.8.8

   # Test DNS resolution
   nslookup base-mainnet.g.alchemy.com

   # Test HTTPS connectivity
   curl -I https://mainnet.base.org
   ```

2. **Check AWS Security Groups**

   ```bash
   # Verify outbound HTTPS allowed
   aws ec2 describe-security-groups \
     --group-ids <security-group-id> \
     --query 'SecurityGroups[0].IpPermissionsEgress'
   ```

3. **Check for IP Blocking**

   ```bash
   # Test from different IP
   # Use AWS CloudShell or local machine
   cast block-number --rpc-url <provider-url>
   ```

4. **Use Emergency Public RPC**

   ```yaml
   # Edit config.yaml
   rpc_providers:
     primary: https://mainnet.base.org
     backup: https://base.llamarpc.com
   ```

5. **Contact All Providers**

   - Open support tickets
   - Request immediate assistance
   - Escalate to account manager

6. **Consider Temporary Pause**
   - If outage exceeds 1 hour
   - If no ETA for resolution
   - Preserve capital and wait

### Reconnection Procedures

**After provider recovers:**

1. **Verify Provider Stability**

   ```bash
   # Test for 5 minutes
   for i in {1..30}; do
     cast block-number --rpc-url <provider-url>
     sleep 10
   done
   ```

2. **Update Configuration**

   ```yaml
   # Restore original provider order
   rpc_providers:
     primary: <original-primary-url>
     backup: <original-backup-url>
   ```

3. **Restart Bot**

   ```bash
   sudo systemctl restart chimera-bot
   ```

4. **Monitor Initial Connection**

   ```bash
   tail -f /app/logs/chimera.log | grep -E "WebSocket|RPC|block"
   ```

5. **Verify State Synchronization**

   ```bash
   # Check state reconciliation
   grep "reconciliation" /app/logs/chimera.log | tail -n 20

   # Verify no state divergence
   grep "state_divergence" /app/logs/chimera.log | tail -n 10
   ```

### Validation Steps

- [ ] RPC provider connectivity restored
- [ ] Bot reconnected successfully
- [ ] WebSocket receiving real-time events
- [ ] State reconciliation successful
- [ ] Latency within acceptable range (<1s)
- [ ] No rate limiting errors
- [ ] First execution successful
- [ ] Incident documented

### Escalation Criteria

Escalate to Infrastructure Lead if:

- All providers unavailable >1 hour
- Repeated failovers (>5 in 24 hours)
- Persistent rate limiting despite optimization
- Suspected DDoS or network attack
- Provider contract renegotiation needed

### Prevention Measures

- Maintain minimum 3 RPC providers
- Use different providers (diversify risk)
- Monitor provider status pages proactively
- Set up provider health checks
- Negotiate SLAs with providers
- Keep provider tiers appropriate for usage
- Test failover procedures monthly
- Maintain emergency contact list

---

## Appendix A: Quick Reference Commands

### System Status Checks

```bash
# Check bot service status
sudo systemctl status chimera-bot

# View recent logs
tail -n 100 /app/logs/chimera.log

# Check current system state
grep "state" /app/logs/chimera.log | tail -n 5

# Check operator balance
cast balance <OPERATOR_ADDRESS> --rpc-url https://mainnet.base.org

# Check treasury balance
cast balance <TREASURY_ADDRESS> --rpc-url https://mainnet.base.org
```

### Database Queries

```sql
-- Recent executions
SELECT * FROM executions ORDER BY timestamp DESC LIMIT 10;

-- Today's performance
SELECT COUNT(*) as executions,
       SUM(actual_profit_usd) as profit
FROM executions
WHERE DATE(timestamp) = CURRENT_DATE
  AND included = true;

-- Current system state
SELECT * FROM system_events
WHERE event_type = 'STATE_TRANSITION'
ORDER BY timestamp DESC LIMIT 5;

-- Recent failures
SELECT rejection_reason, COUNT(*)
FROM executions
WHERE included = false
  AND timestamp > NOW() - INTERVAL '1 hour'
GROUP BY rejection_reason;
```

### Emergency Actions

```bash
# Stop bot immediately
sudo systemctl stop chimera-bot

# Pause smart contract
cast send <CHIMERA_CONTRACT_ADDRESS> "pause()" \
  --private-key <TREASURY_PRIVATE_KEY> \
  --rpc-url https://mainnet.base.org

# Force HALT state
python3 -c "
from bot.src.safety_controller import SafetyController
from bot.src.config import load_config
safety = SafetyController(load_config())
safety.force_halt('Manual emergency halt')
"

# Drain operator wallet
cast send <TREASURY_ADDRESS> \
  --value <FULL_BALANCE> \
  --private-key <OPERATOR_PRIVATE_KEY> \
  --rpc-url https://mainnet.base.org
```

---

## Appendix B: Monitoring Dashboard URLs

- **CloudWatch Dashboard**: https://console.aws.amazon.com/cloudwatch/home?region=us-east-1#dashboards:name=Chimera
- **Grafana Dashboard**: http://<grafana-url>:3000/d/chimera
- **RDS Console**: https://console.aws.amazon.com/rds/home?region=us-east-1#database:id=chimera-db
- **ElastiCache Console**: https://console.aws.amazon.com/elasticache/home?region=us-east-1#cache-clusters:id=chimera-redis
- **EC2 Console**: https://console.aws.amazon.com/ec2/home?region=us-east-1#Instances:instanceId=<instance-id>
- **BaseScan Contract**: https://basescan.org/address/<CHIMERA_CONTRACT_ADDRESS>
- **BaseScan Operator**: https://basescan.org/address/<OPERATOR_ADDRESS>

---

## Appendix C: Incident Report Template

```markdown
# Incident Report: [Title]

**Date**: [YYYY-MM-DD]
**Time**: [HH:MM UTC]
**Severity**: [CRITICAL/HIGH/MEDIUM/LOW]
**Duration**: [X hours Y minutes]
**Reported By**: [Name]

## Summary

[Brief description of the incident]

## Timeline

- [HH:MM] - Initial detection
- [HH:MM] - Response initiated
- [HH:MM] - Root cause identified
- [HH:MM] - Mitigation applied
- [HH:MM] - Service restored
- [HH:MM] - Validation completed

## Impact

- Executions affected: [Number]
- Financial impact: $[Amount]
- Downtime: [Duration]
- Data loss: [Yes/No - Details]

## Root Cause

[Detailed explanation of what caused the incident]

## Resolution

[Steps taken to resolve the incident]

## Prevention

[Measures implemented to prevent recurrence]

## Action Items

- [ ] [Action 1] - Owner: [Name] - Due: [Date]
- [ ] [Action 2] - Owner: [Name] - Due: [Date]

## Lessons Learned

[Key takeaways and improvements identified]
```

---

## Appendix D: Escalation Matrix

| Severity | Response Time | Primary Contact | Secondary Contact   | Notification Method     |
| -------- | ------------- | --------------- | ------------------- | ----------------------- |
| CRITICAL | Immediate     | Security Lead   | Infrastructure Lead | Phone + SMS + PagerDuty |
| HIGH     | 15 minutes    | Primary On-Call | Secondary On-Call   | SMS + PagerDuty         |
| MEDIUM   | 30 minutes    | Primary On-Call | Infrastructure Lead | Email + Slack           |
| LOW      | 2 hours       | Primary On-Call | -                   | Email                   |

---

## Document Control

**Version**: 1.0  
**Last Updated**: [Date]  
**Owner**: Infrastructure Team  
**Review Frequency**: Quarterly  
**Next Review**: [Date]

**Change Log**:

- v1.0 - Initial creation - [Date]

---

**END OF RUNBOOKS**
