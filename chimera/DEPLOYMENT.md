# Deployment Documentation: Project Chimera

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Mainnet Deployment Steps](#mainnet-deployment-steps)
3. [Rollback Procedures](#rollback-procedures)
4. [Operational Procedures](#operational-procedures)
5. [Emergency Contacts](#emergency-contacts)

---

## Pre-Deployment Checklist

### Phase 1: Code Readiness

- [ ] All unit tests passing (>80% coverage)
- [ ] All integration tests passing
- [ ] Smart contract tests passing (>95% coverage)
- [ ] Foundry fork tests passing on Base mainnet fork
- [ ] Static analysis completed (Slither, Mythril) with no critical issues
- [ ] Code review completed by minimum 2 developers
- [ ] All TODO/FIXME comments resolved or documented
- [ ] Version tagged in Git (e.g., v1.0.0)

### Phase 2: Smart Contract Audit

- [ ] Professional audit completed by reputable firm
- [ ] All HIGH and CRITICAL findings resolved
- [ ] MEDIUM findings documented with risk acceptance
- [ ] Audit report reviewed and approved
- [ ] Final audit sign-off received

### Phase 3: Testnet Validation

- [ ] Contract deployed to Base Sepolia testnet
- [ ] Contract verified on BaseScan Sepolia
- [ ] Bot executed 50+ liquidations on testnet
- [ ] Inclusion rate >60% sustained over 2 weeks
- [ ] Simulation accuracy >90% over 50+ executions
- [ ] System uptime >95% excluding planned maintenance
- [ ] All operational procedures tested (pause, resume, key rotation)

### Phase 4: Infrastructure Preparation

- [ ] AWS account configured with appropriate IAM roles
- [ ] VPC and security groups configured
- [ ] RDS PostgreSQL database provisioned (db.t4g.medium, Multi-AZ)
- [ ] ElastiCache Redis provisioned (cache.t4g.small)
- [ ] EC2 instance provisioned (c7g.xlarge ARM Graviton3)
- [ ] AWS Secrets Manager configured for operator key
- [ ] CloudWatch dashboards created
- [ ] PagerDuty integration configured
- [ ] Backup and recovery procedures tested
- [ ] Database migration scripts tested

### Phase 5: Configuration and Secrets

- [ ] Operator wallet created and funded (minimum 0.5 ETH)
- [ ] Treasury wallet created (hardware wallet recommended)
- [ ] Operator private key stored in AWS Secrets Manager
- [ ] RPC endpoints configured (Alchemy primary, QuickNode backup)
- [ ] config.yaml updated with mainnet addresses
- [ ] Environment variables configured in .env
- [ ] All protocol addresses verified on BaseScan
- [ ] Oracle addresses verified (Chainlink, Pyth)
- [ ] DEX router addresses verified (Uniswap V3, Aerodrome)

### Phase 6: Monitoring and Alerting

- [ ] CloudWatch log groups created
- [ ] CloudWatch alarms configured (CRITICAL, HIGH, MEDIUM, LOW)
- [ ] PagerDuty escalation policies configured
- [ ] SMS alerts configured for CRITICAL events
- [ ] Email alerts configured for MEDIUM/LOW events
- [ ] Grafana dashboards configured (if using)
- [ ] Alert testing completed (trigger test alerts)
- [ ] On-call rotation schedule established

### Phase 7: Documentation and Training

- [ ] Deployment runbook reviewed by operations team
- [ ] Operational procedures documented and reviewed
- [ ] Emergency response procedures documented
- [ ] Team trained on operational procedures
- [ ] Emergency contact list updated
- [ ] Legal and compliance documentation reviewed
- [ ] Insurance coverage confirmed (if applicable)

### Phase 8: Financial Preparation

- [ ] Initial capital allocated ($1,000-$2,000 for Tier 1)
- [ ] Reserve fund established (3 months operating costs)
- [ ] Gas budget allocated (0.5 ETH minimum)
- [ ] Accounting system configured for tracking
- [ ] Tax implications reviewed with accountant
- [ ] Profit distribution plan documented

### Phase 9: Final Verification

- [ ] All checklist items above completed
- [ ] Go/No-Go meeting held with stakeholders
- [ ] Deployment window scheduled (low-traffic period recommended)
- [ ] Rollback plan reviewed and approved
- [ ] Emergency contacts confirmed available during deployment
- [ ] Final backtest results reviewed (Base Case ROI >100%)
- [ ] Risk assessment completed and accepted

---

## Mainnet Deployment Steps

### Step 1: Smart Contract Deployment

**Duration:** 30-60 minutes

1. **Prepare deployment environment:**

   ```bash
   cd chimera/contracts
   source .env  # Load mainnet configuration
   ```

2. **Verify configuration:**

   ```bash
   # Verify deployer wallet has sufficient ETH (0.1 ETH recommended)
   cast balance $DEPLOYER_ADDRESS --rpc-url $BASE_MAINNET_RPC

   # Verify Base mainnet chain ID (8453)
   cast chain-id --rpc-url $BASE_MAINNET_RPC
   ```

3. **Deploy Chimera contract:**

   ```bash
   forge script script/Deploy.s.sol:Deploy \
     --rpc-url $BASE_MAINNET_RPC \
     --broadcast \
     --verify \
     --etherscan-api-key $BASESCAN_API_KEY \
     -vvvv
   ```

4. **Record deployment details:**

   - Contract address: `_____________________`
   - Deployment transaction: `_____________________`
   - Deployment block: `_____________________`
   - Gas used: `_____________________`
   - Deployer address: `_____________________`

5. **Verify contract on BaseScan:**

   - Navigate to https://basescan.org/address/[CONTRACT_ADDRESS]
   - Confirm contract is verified (green checkmark)
   - Confirm source code is visible
   - Confirm constructor arguments are correct

6. **Test contract functions:**

   ```bash
   # Verify owner
   cast call $CHIMERA_ADDRESS "owner()" --rpc-url $BASE_MAINNET_RPC

   # Verify treasury address
   cast call $CHIMERA_ADDRESS "treasury()" --rpc-url $BASE_MAINNET_RPC

   # Verify contract is not paused
   cast call $CHIMERA_ADDRESS "paused()" --rpc-url $BASE_MAINNET_RPC
   ```

### Step 2: Transfer Contract Ownership to Multisig

**Duration:** 15-30 minutes

1. **Deploy Gnosis Safe multisig (if not already deployed):**

   - Use https://app.safe.global/
   - Configure 2-of-3 or 3-of-5 signers
   - Record Safe address: `_____________________`

2. **Initiate ownership transfer:**

   ```bash
   cast send $CHIMERA_ADDRESS \
     "transferOwnership(address)" $SAFE_ADDRESS \
     --rpc-url $BASE_MAINNET_RPC \
     --private-key $DEPLOYER_PRIVATE_KEY
   ```

3. **Accept ownership from Safe:**

   - Navigate to Safe web interface
   - Create transaction to call `acceptOwnership()` on Chimera contract
   - Collect required signatures
   - Execute transaction

4. **Verify ownership transfer:**
   ```bash
   cast call $CHIMERA_ADDRESS "owner()" --rpc-url $BASE_MAINNET_RPC
   # Should return Safe address
   ```

### Step 3: Database Setup

**Duration:** 30-45 minutes

1. **Connect to RDS instance:**

   ```bash
   psql -h $RDS_ENDPOINT -U $DB_USER -d chimera
   ```

2. **Run database migrations:**

   ```bash
   cd chimera/bot
   alembic upgrade head
   ```

3. **Verify schema:**

   ```sql
   \dt  -- List all tables
   SELECT * FROM alembic_version;  -- Verify migration version
   ```

4. **Create initial configuration:**

   ```sql
   -- Insert initial system state
   INSERT INTO system_events (timestamp, event_type, details)
   VALUES (NOW(), 'DEPLOYMENT', '{"version": "1.0.0", "environment": "mainnet"}');
   ```

5. **Test database connectivity from bot:**
   ```bash
   python -c "from bot.src.config import get_db_connection; conn = get_db_connection(); print('Connected:', conn is not None)"
   ```

### Step 4: Bot Configuration

**Duration:** 30-45 minutes

1. **Update config.yaml with mainnet addresses:**

   ```yaml
   network:
     chain_id: 8453
     name: 'base-mainnet'

   contracts:
     chimera: '0x...' # Deployed contract address
     moonwell_comptroller: '0x...'
     seamless_pool: '0x...'
     # ... other addresses

   limits:
     tier: 1
     max_single_execution_usd: 500
     max_daily_volume_usd: 2500
     min_profit_usd: 50
   ```

2. **Configure environment variables:**

   ```bash
   # Copy example and edit
   cp .env.example .env
   nano .env
   ```

   Required variables:

   ```
   ENVIRONMENT=mainnet
   OPERATOR_PRIVATE_KEY_SECRET_NAME=chimera/operator-key
   ALCHEMY_API_KEY=...
   QUICKNODE_API_KEY=...
   DATABASE_URL=postgresql://...
   REDIS_URL=redis://...
   CLOUDWATCH_LOG_GROUP=/chimera/mainnet
   PAGERDUTY_API_KEY=...
   ```

3. **Store operator key in AWS Secrets Manager:**

   ```bash
   aws secretsmanager create-secret \
     --name chimera/operator-key \
     --secret-string '{"private_key":"0x..."}' \
     --region us-east-1
   ```

4. **Verify configuration:**
   ```bash
   python -c "from bot.src.config import load_config; config = load_config(); print('Config loaded:', config.network.name)"
   ```

### Step 5: Deploy Bot Application

**Duration:** 30-45 minutes

1. **SSH into EC2 instance:**

   ```bash
   ssh -i chimera-key.pem ec2-user@$EC2_PUBLIC_IP
   ```

2. **Clone repository:**

   ```bash
   git clone https://github.com/your-org/project-chimera.git
   cd project-chimera/chimera
   git checkout v1.0.0  # Use tagged version
   ```

3. **Install dependencies:**

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Copy configuration files:**

   ```bash
   cp /secure-location/.env .env
   cp /secure-location/config.yaml config.yaml
   ```

5. **Create systemd service:**

   ```bash
   sudo nano /etc/systemd/system/chimera.service
   ```

   Service file content:

   ```ini
   [Unit]
   Description=Chimera MEV Bot
   After=network.target

   [Service]
   Type=simple
   User=ec2-user
   WorkingDirectory=/home/ec2-user/project-chimera/chimera
   Environment="PATH=/home/ec2-user/project-chimera/chimera/venv/bin"
   ExecStart=/home/ec2-user/project-chimera/chimera/venv/bin/python bot/src/main.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

6. **Enable and start service:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable chimera
   sudo systemctl start chimera
   ```

7. **Verify service is running:**
   ```bash
   sudo systemctl status chimera
   journalctl -u chimera -f  # Follow logs
   ```

### Step 6: Monitoring and Validation

**Duration:** 30-60 minutes

1. **Verify CloudWatch logs:**

   - Navigate to AWS CloudWatch Console
   - Open log group `/chimera/mainnet`
   - Verify logs are being received
   - Check for any ERROR or CRITICAL messages

2. **Verify metrics:**

   - Open CloudWatch Metrics
   - Navigate to Custom Namespaces > Chimera
   - Verify metrics are being published:
     - `system_state`
     - `opportunities_detected`
     - `bundles_submitted`
     - `inclusion_rate`

3. **Test alerting:**

   ```bash
   # Trigger a test alert
   python scripts/test_alerts.py --level MEDIUM
   ```

   - Verify email received
   - Verify Slack notification (if configured)

4. **Monitor first hour of operation:**

   - Watch for opportunities detected
   - Watch for state transitions
   - Monitor operator wallet balance
   - Monitor database writes
   - Check for any errors or warnings

5. **Verify first execution (when it occurs):**
   - Check transaction on BaseScan
   - Verify profit calculation
   - Verify database record created
   - Verify metrics updated

### Step 7: Post-Deployment Verification

**Duration:** 24-48 hours

1. **24-Hour Health Check:**

   - [ ] System uptime >99%
   - [ ] No CRITICAL or HIGH alerts
   - [ ] Opportunities being detected
   - [ ] State remains NORMAL or THROTTLED (not HALTED)
   - [ ] Database writes successful
   - [ ] Logs clean (no repeated errors)

2. **First Execution Validation:**

   - [ ] Transaction included successfully
   - [ ] Profit realized matches simulation (within 10%)
   - [ ] Gas costs calculated correctly
   - [ ] Database record accurate
   - [ ] Metrics updated correctly

3. **48-Hour Performance Review:**

   - [ ] Review all executions
   - [ ] Calculate actual inclusion rate
   - [ ] Calculate actual simulation accuracy
   - [ ] Review any rejected opportunities
   - [ ] Analyze any failures or errors
   - [ ] Verify limits are being enforced

4. **Sign-off:**
   - [ ] Technical lead approval
   - [ ] Operations team approval
   - [ ] Stakeholder notification sent
   - [ ] Deployment marked as successful

---

## Rollback Procedures

### Scenario 1: Smart Contract Issue Detected

**Trigger:** Critical bug found in smart contract, exploit detected, or audit finding discovered post-deployment

**Immediate Actions (within 5 minutes):**

1. **Pause the contract:**

   ```bash
   # Via Gnosis Safe
   # Create transaction to call pause() on Chimera contract
   # Collect signatures and execute immediately
   ```

2. **Stop the bot:**

   ```bash
   ssh ec2-user@$EC2_PUBLIC_IP
   sudo systemctl stop chimera
   ```

3. **Verify contract is paused:**

   ```bash
   cast call $CHIMERA_ADDRESS "paused()" --rpc-url $BASE_MAINNET_RPC
   # Should return true
   ```

4. **Send CRITICAL alert:**
   - Notify all stakeholders
   - Explain issue and actions taken
   - Provide timeline for resolution

**Investigation Phase (1-24 hours):**

1. Review contract code and identify issue
2. Assess impact (funds at risk, potential losses)
3. Determine if fix is possible or redeployment needed
4. Consult with auditors if necessary
5. Document findings and remediation plan

**Resolution Options:**

**Option A: Fix and Resume (if issue is minor)**

- Fix identified issue
- Deploy updated contract
- Update bot configuration
- Resume operations with enhanced monitoring

**Option B: Full Rollback (if issue is critical)**

- Keep contract paused indefinitely
- Withdraw any funds from contract using rescueTokens()
- Deploy new contract version
- Follow full deployment procedure
- Migrate to new contract

### Scenario 2: Bot Malfunction

**Trigger:** Bot entering HALTED state repeatedly, unexpected behavior, or data corruption

**Immediate Actions (within 5 minutes):**

1. **Stop the bot service:**

   ```bash
   ssh ec2-user@$EC2_PUBLIC_IP
   sudo systemctl stop chimera
   ```

2. **Verify no pending transactions:**

   ```bash
   # Check operator wallet on BaseScan
   # Verify no pending transactions in mempool
   ```

3. **Capture logs:**

   ```bash
   journalctl -u chimera --since "1 hour ago" > /tmp/chimera-logs.txt
   # Download logs for analysis
   scp ec2-user@$EC2_PUBLIC_IP:/tmp/chimera-logs.txt .
   ```

4. **Assess database state:**
   ```bash
   psql -h $RDS_ENDPOINT -U $DB_USER -d chimera
   SELECT * FROM system_events ORDER BY timestamp DESC LIMIT 20;
   SELECT * FROM executions ORDER BY timestamp DESC LIMIT 10;
   ```

**Investigation Phase (1-4 hours):**

1. Analyze logs for error patterns
2. Check RPC provider status
3. Verify database connectivity
4. Check Redis cache status
5. Review recent code changes
6. Identify root cause

**Resolution Options:**

**Option A: Configuration Fix**

- Update config.yaml or .env
- Restart bot service
- Monitor for 1 hour

**Option B: Code Fix**

- Fix identified bug
- Deploy updated code
- Restart bot service
- Enhanced monitoring for 24 hours

**Option C: Rollback to Previous Version**

```bash
cd /home/ec2-user/project-chimera/chimera
git checkout v1.0.0-previous  # Previous stable version
sudo systemctl restart chimera
```

**Option D: Full System Reset**

- Stop bot
- Clear Redis cache
- Rebuild position cache from blockchain
- Restart bot with fresh state

### Scenario 3: Infrastructure Failure

**Trigger:** AWS outage, database failure, or network issues

**Immediate Actions (within 5 minutes):**

1. **Assess scope of failure:**

   - Check AWS Service Health Dashboard
   - Verify RDS status
   - Verify ElastiCache status
   - Verify EC2 instance status

2. **If EC2 instance failed:**

   ```bash
   # Launch new instance from AMI backup
   aws ec2 run-instances --image-id $AMI_ID --instance-type c7g.xlarge ...

   # Update DNS/configuration to point to new instance
   # Deploy bot to new instance (follow Step 5 above)
   ```

3. **If database failed:**

   ```bash
   # Restore from latest RDS snapshot
   aws rds restore-db-instance-from-db-snapshot \
     --db-instance-identifier chimera-restored \
     --db-snapshot-identifier chimera-snapshot-latest

   # Update bot configuration with new endpoint
   # Restart bot
   ```

4. **If Redis failed:**
   - Redis is cache only, no data loss
   - Provision new ElastiCache instance
   - Update bot configuration
   - Bot will rebuild cache from blockchain

**Recovery Validation:**

1. Verify all services are running
2. Verify bot can connect to all dependencies
3. Verify logs are flowing
4. Monitor for 2 hours before considering resolved

### Scenario 4: Financial Loss Detected

**Trigger:** Unprofitable executions, unexpected losses, or limit breaches

**Immediate Actions (within 5 minutes):**

1. **Stop the bot immediately:**

   ```bash
   sudo systemctl stop chimera
   ```

2. **Pause the contract:**

   ```bash
   # Via Gnosis Safe, call pause()
   ```

3. **Assess financial impact:**

   ```sql
   SELECT
     SUM(actual_profit_usd) as total_profit,
     COUNT(*) as execution_count,
     AVG(actual_profit_usd) as avg_profit
   FROM executions
   WHERE timestamp > NOW() - INTERVAL '24 hours'
     AND included = true;
   ```

4. **Identify cause:**
   - Review recent executions
   - Check for simulation accuracy issues
   - Check for gas price spikes
   - Check for oracle manipulation
   - Check for MEV competition changes

**Investigation Phase (4-24 hours):**

1. Detailed analysis of all losing trades
2. Backtest recent period to validate strategy
3. Review market conditions
4. Assess if issue is temporary or systemic
5. Calculate break-even adjustments needed

**Resolution Options:**

**Option A: Parameter Adjustment**

- Increase MIN_PROFIT_USD threshold
- Adjust bribe optimization parameters
- Tighten simulation accuracy requirements
- Resume with enhanced monitoring

**Option B: Strategy Pause**

- Keep bot stopped
- Conduct thorough strategy review
- Backtest with updated parameters
- Resume only after validation

**Option C: Wind Down**

- If losses are systemic and unfixable
- Withdraw all funds from contract
- Document lessons learned
- Formal project closure

---

## Operational Procedures

### Procedure 1: Pause Operations

**When to Use:**

- Scheduled maintenance
- Market volatility concerns
- Regulatory uncertainty
- Infrastructure upgrades
- Security concerns

**Steps:**

1. **Pause the smart contract:**

   ```bash
   # Via Gnosis Safe web interface
   # Navigate to https://app.safe.global/
   # Select Chimera Safe
   # Create new transaction:
   #   - To: [CHIMERA_CONTRACT_ADDRESS]
   #   - Function: pause()
   #   - Value: 0
   # Collect required signatures
   # Execute transaction
   ```

2. **Verify contract is paused:**

   ```bash
   cast call $CHIMERA_ADDRESS "paused()" --rpc-url $BASE_MAINNET_RPC
   # Should return: true (0x0000...0001)
   ```

3. **Stop the bot service:**

   ```bash
   ssh ec2-user@$EC2_PUBLIC_IP
   sudo systemctl stop chimera
   sudo systemctl status chimera  # Verify stopped
   ```

4. **Verify no pending transactions:**

   - Check operator wallet on BaseScan
   - Verify mempool is clear
   - Check for any stuck transactions

5. **Log the pause event:**

   ```sql
   INSERT INTO system_events (timestamp, event_type, details)
   VALUES (NOW(), 'MANUAL_PAUSE', '{"reason": "scheduled maintenance", "operator": "alice"}');
   ```

6. **Notify stakeholders:**
   - Send notification to team
   - Update status page (if applicable)
   - Document expected resume time

**Expected Duration:** 5-10 minutes

### Procedure 2: Resume Operations

**Prerequisites:**

- Issue that caused pause has been resolved
- All systems verified healthy
- Team approval obtained

**Steps:**

1. **Pre-flight checks:**

   ```bash
   # Verify operator wallet balance
   cast balance $OPERATOR_ADDRESS --rpc-url $BASE_MAINNET_RPC
   # Should have >0.1 ETH

   # Verify RPC connectivity
   curl -X POST $ALCHEMY_RPC_URL \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'

   # Verify database connectivity
   psql -h $RDS_ENDPOINT -U $DB_USER -d chimera -c "SELECT 1;"

   # Verify Redis connectivity
   redis-cli -h $REDIS_ENDPOINT ping
   ```

2. **Unpause the smart contract:**

   ```bash
   # Via Gnosis Safe web interface
   # Create new transaction:
   #   - To: [CHIMERA_CONTRACT_ADDRESS]
   #   - Function: unpause()
   #   - Value: 0
   # Collect required signatures
   # Execute transaction
   ```

3. **Verify contract is unpaused:**

   ```bash
   cast call $CHIMERA_ADDRESS "paused()" --rpc-url $BASE_MAINNET_RPC
   # Should return: false (0x0000...0000)
   ```

4. **Start the bot service:**

   ```bash
   ssh ec2-user@$EC2_PUBLIC_IP
   sudo systemctl start chimera
   sudo systemctl status chimera  # Verify running
   ```

5. **Monitor initial startup:**

   ```bash
   # Watch logs for 5 minutes
   journalctl -u chimera -f

   # Look for:
   # - "StateEngine initialized"
   # - "WebSocket connected"
   # - "Position cache rebuilt"
   # - "System state: NORMAL"
   ```

6. **Verify system health:**

   - Check CloudWatch metrics
   - Verify opportunities being detected
   - Verify no immediate errors
   - Monitor for 30 minutes

7. **Log the resume event:**

   ```sql
   INSERT INTO system_events (timestamp, event_type, details)
   VALUES (NOW(), 'MANUAL_RESUME', '{"operator": "alice", "pause_duration_hours": 2.5}');
   ```

8. **Notify stakeholders:**
   - Send notification that operations resumed
   - Provide initial health status

**Expected Duration:** 10-15 minutes

### Procedure 3: Operator Key Rotation

**When to Use:**

- Scheduled 90-day rotation
- Suspected key compromise
- Team member departure
- Security audit recommendation

**Steps:**

1. **Generate new operator wallet:**

   ```bash
   # Use secure offline machine
   cast wallet new
   # Record new address and private key securely
   ```

2. **Fund new operator wallet:**

   ```bash
   # Transfer 0.5 ETH from treasury to new operator address
   # Verify transaction confirmed
   cast balance $NEW_OPERATOR_ADDRESS --rpc-url $BASE_MAINNET_RPC
   ```

3. **Pause operations (follow Procedure 1)**

4. **Update AWS Secrets Manager:**

   ```bash
   # Create new secret version
   aws secretsmanager update-secret \
     --secret-id chimera/operator-key \
     --secret-string '{"private_key":"0x[NEW_KEY]"}' \
     --region us-east-1

   # Verify new secret
   aws secretsmanager get-secret-value \
     --secret-id chimera/operator-key \
     --region us-east-1
   ```

5. **Update bot configuration:**

   ```bash
   ssh ec2-user@$EC2_PUBLIC_IP
   cd /home/ec2-user/project-chimera/chimera

   # Update .env if operator address is hardcoded
   nano .env
   # Update OPERATOR_ADDRESS=0x[NEW_ADDRESS]
   ```

6. **Test new key:**

   ```bash
   # Test signing a transaction (don't broadcast)
   python -c "
   from bot.src.config import load_config
   from eth_account import Account
   config = load_config()
   account = Account.from_key(config.operator_private_key)
   print(f'New operator address: {account.address}')
   "
   ```

7. **Resume operations (follow Procedure 2)**

8. **Monitor first execution with new key:**

   - Verify transaction signed correctly
   - Verify transaction included
   - Verify no errors

9. **Sweep old operator wallet:**

   ```bash
   # Transfer remaining ETH from old wallet to treasury
   cast send $TREASURY_ADDRESS \
     --value [REMAINING_BALANCE] \
     --rpc-url $BASE_MAINNET_RPC \
     --private-key $OLD_OPERATOR_KEY
   ```

10. **Revoke old key:**

    ```bash
    # Delete old secret version from Secrets Manager
    aws secretsmanager delete-secret \
      --secret-id chimera/operator-key-old \
      --force-delete-without-recovery \
      --region us-east-1

    # Securely delete old key from any local storage
    # Overwrite with random data before deletion
    ```

11. **Document rotation:**
    ```sql
    INSERT INTO system_events (timestamp, event_type, details)
    VALUES (NOW(), 'KEY_ROTATION', '{
      "old_address": "0x...",
      "new_address": "0x...",
      "operator": "alice",
      "reason": "scheduled_90day"
    }');
    ```

**Expected Duration:** 30-45 minutes

**Security Notes:**

- Never log or expose private keys
- Use secure channels for key transmission
- Verify new key works before revoking old key
- Keep old key available for 24 hours in case of issues
- Document rotation in security audit log

### Procedure 4: Treasury Withdrawal

**When to Use:**

- Scheduled profit distribution
- Rebalancing capital allocation
- Emergency fund withdrawal
- Project wind-down

**Steps:**

1. **Calculate available balance:**

   ```bash
   cast balance $CHIMERA_ADDRESS --rpc-url $BASE_MAINNET_RPC
   # Note: This is the contract balance, not treasury wallet
   ```

2. **Determine withdrawal amount:**

   - Review profit history
   - Maintain operational reserve (0.5 ETH minimum)
   - Calculate amount to withdraw

3. **Pause operations (follow Procedure 1)**

4. **Execute withdrawal via Gnosis Safe:**

   ```bash
   # Via Gnosis Safe web interface
   # Create new transaction:
   #   - To: [CHIMERA_CONTRACT_ADDRESS]
   #   - Function: rescueTokens(address token, uint256 amount)
   #   - Parameters:
   #     - token: 0xEeeeeEeeeEeEeeEeEeEeeEEEeeeeEeeeeeeeEEeE (ETH)
   #     - amount: [AMOUNT_IN_WEI]
   #   - Value: 0
   # Collect required signatures
   # Execute transaction
   ```

5. **Verify withdrawal:**

   ```bash
   # Check transaction on BaseScan
   # Verify funds received in treasury wallet
   cast balance $TREASURY_ADDRESS --rpc-url $BASE_MAINNET_RPC
   ```

6. **Log withdrawal:**

   ```sql
   INSERT INTO system_events (timestamp, event_type, details)
   VALUES (NOW(), 'TREASURY_WITHDRAWAL', '{
     "amount_eth": "1.5",
     "amount_usd": "3750",
     "reason": "monthly_profit_distribution",
     "operator": "alice"
   }');
   ```

7. **Resume operations (follow Procedure 2)**

8. **Update accounting records:**
   - Record withdrawal in accounting system
   - Update profit tracking spreadsheet
   - Generate tax documentation if needed

**Expected Duration:** 20-30 minutes

### Procedure 5: Tier Graduation

**When to Use:**

- Graduation criteria met for next tier
- Performance validated over required period
- Stakeholder approval obtained

**Prerequisites:**

- All graduation criteria met (see Requirements 8.2-8.4)
- Minimum time period elapsed
- No critical incidents in period
- Positive cumulative profit

**Steps:**

1. **Generate graduation report:**

   ```bash
   python scripts/generate_tier_report.py --tier 1
   ```

   Report should include:

   - Total executions
   - Cumulative profit
   - Inclusion rate
   - Simulation accuracy
   - Critical incidents
   - Time elapsed

2. **Review and approve:**

   - Technical lead review
   - Risk assessment
   - Stakeholder approval

3. **Pause operations (follow Procedure 1)**

4. **Update configuration:**

   ```bash
   ssh ec2-user@$EC2_PUBLIC_IP
   cd /home/ec2-user/project-chimera/chimera
   nano config.yaml
   ```

   Update limits:

   ```yaml
   limits:
     tier: 2 # Increment tier
     max_single_execution_usd: 1000 # New limit
     max_daily_volume_usd: 5000 # New limit
     min_profit_usd: 50 # Keep same
   ```

5. **Restart bot to load new config:**

   ```bash
   sudo systemctl restart chimera
   ```

6. **Verify new limits loaded:**

   ```bash
   journalctl -u chimera -n 50 | grep "Configuration loaded"
   # Should show new tier and limits
   ```

7. **Log graduation:**

   ```sql
   INSERT INTO system_events (timestamp, event_type, details)
   VALUES (NOW(), 'TIER_GRADUATION', '{
     "from_tier": 1,
     "to_tier": 2,
     "new_single_limit": 1000,
     "new_daily_limit": 5000,
     "operator": "alice"
   }');
   ```

8. **Resume operations (follow Procedure 2)**

9. **Enhanced monitoring for 7 days:**
   - Monitor daily volume closely
   - Verify limits enforced correctly
   - Watch for any issues with larger executions

**Expected Duration:** 30-45 minutes

### Procedure 6: Emergency Shutdown

**When to Use:**

- Critical security vulnerability discovered
- Smart contract exploit detected
- Regulatory action imminent
- Catastrophic financial losses
- Infrastructure compromise

**Steps:**

1. **IMMEDIATE - Stop all operations (within 60 seconds):**

   ```bash
   # Pause contract via Gnosis Safe (if time permits)
   # Otherwise, proceed to step 2 immediately

   # Stop bot service
   ssh ec2-user@$EC2_PUBLIC_IP "sudo systemctl stop chimera"

   # Verify stopped
   ssh ec2-user@$EC2_PUBLIC_IP "sudo systemctl status chimera"
   ```

2. **Secure funds (within 5 minutes):**

   ```bash
   # Via Gnosis Safe, pause contract
   # Via Gnosis Safe, withdraw all funds using rescueTokens()
   # Transfer to secure cold storage wallet
   ```

3. **Assess situation (within 30 minutes):**

   - Identify nature of emergency
   - Assess financial impact
   - Determine if recovery is possible
   - Consult legal counsel if needed

4. **Notify stakeholders (within 1 hour):**

   - Send CRITICAL alert to all team members
   - Notify investors/partners
   - Prepare public statement if needed
   - Contact insurance provider if applicable

5. **Preserve evidence:**

   ```bash
   # Capture all logs
   journalctl -u chimera --since "24 hours ago" > emergency-logs.txt

   # Export database
   pg_dump -h $RDS_ENDPOINT -U $DB_USER chimera > emergency-db-backup.sql

   # Capture system state
   aws ec2 create-snapshot --volume-id $EBS_VOLUME_ID
   ```

6. **Disable access:**

   ```bash
   # Revoke AWS access keys
   aws iam delete-access-key --access-key-id $ACCESS_KEY_ID

   # Disable EC2 instance (don't terminate yet)
   aws ec2 stop-instances --instance-ids $INSTANCE_ID

   # Rotate all secrets
   aws secretsmanager update-secret --secret-id chimera/operator-key --secret-string '{"revoked": true}'
   ```

7. **Incident response:**

   - Conduct thorough investigation
   - Document timeline of events
   - Identify root cause
   - Develop remediation plan
   - Engage external security experts if needed

8. **Recovery or wind-down decision:**
   - Assess if recovery is feasible
   - Calculate cost of recovery vs wind-down
   - Make formal decision with stakeholders
   - Execute chosen path

**Expected Duration:** Immediate action (1 minute), full response (hours to days)

---

## Emergency Contacts

### Primary Contacts

**Technical Lead:**

- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]
- Telegram: [HANDLE]
- Availability: 24/7 for CRITICAL alerts

**Operations Lead:**

- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]
- Telegram: [HANDLE]
- Availability: 24/7 for CRITICAL alerts

**Security Lead:**

- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]
- Telegram: [HANDLE]
- Availability: 24/7 for security incidents

### Secondary Contacts

**DevOps Engineer:**

- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]
- Availability: Business hours + on-call rotation

**Smart Contract Developer:**

- Name: [NAME]
- Phone: [PHONE]
- Email: [EMAIL]
- Availability: Business hours + CRITICAL alerts

### External Contacts

**Smart Contract Auditor:**

- Firm: [AUDIT_FIRM]
- Contact: [NAME]
- Email: [EMAIL]
- Phone: [PHONE]
- Retainer: [YES/NO]

**Legal Counsel:**

- Firm: [LAW_FIRM]
- Contact: [NAME]
- Email: [EMAIL]
- Phone: [PHONE]

**Insurance Provider:**

- Company: [INSURANCE_COMPANY]
- Policy Number: [POLICY_NUMBER]
- Claims Phone: [PHONE]
- Email: [EMAIL]

### Service Providers

**AWS Support:**

- Account ID: [AWS_ACCOUNT_ID]
- Support Plan: [BUSINESS/ENTERPRISE]
- Phone: 1-800-xxx-xxxx
- Support Portal: https://console.aws.amazon.com/support/

**Alchemy:**

- Account: [ACCOUNT_EMAIL]
- Support: https://www.alchemy.com/support
- Emergency: [CONTACT_INFO]

**QuickNode:**

- Account: [ACCOUNT_EMAIL]
- Support: https://www.quicknode.com/support
- Emergency: [CONTACT_INFO]

### Escalation Path

1. **CRITICAL Alert** → Technical Lead (immediate)
2. **If no response in 5 minutes** → Operations Lead
3. **If no response in 10 minutes** → Security Lead
4. **If no response in 15 minutes** → All secondary contacts
5. **If security incident** → Security Lead + Legal Counsel immediately

### Communication Channels

- **Primary:** PagerDuty
- **Secondary:** Telegram group "Chimera Ops"
- **Tertiary:** Phone calls
- **Documentation:** Slack channel #chimera-incidents

---

## Appendix

### Useful Commands Reference

**Check system status:**

```bash
# Bot service status
sudo systemctl status chimera

# View recent logs
journalctl -u chimera -n 100

# Follow logs in real-time
journalctl -u chimera -f

# Check operator balance
cast balance $OPERATOR_ADDRESS --rpc-url $BASE_MAINNET_RPC

# Check contract paused status
cast call $CHIMERA_ADDRESS "paused()" --rpc-url $BASE_MAINNET_RPC

# Check contract owner
cast call $CHIMERA_ADDRESS "owner()" --rpc-url $BASE_MAINNET_RPC
```

**Database queries:**

```sql
-- Recent executions
SELECT * FROM executions ORDER BY timestamp DESC LIMIT 10;

-- System state history
SELECT * FROM system_events ORDER BY timestamp DESC LIMIT 20;

-- Performance metrics
SELECT
  DATE(timestamp) as date,
  COUNT(*) as executions,
  SUM(CASE WHEN included THEN 1 ELSE 0 END) as successful,
  AVG(actual_profit_usd) as avg_profit
FROM executions
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp);

-- Current state
SELECT state, COUNT(*)
FROM executions
WHERE timestamp > NOW() - INTERVAL '1 hour'
GROUP BY state;
```

**AWS commands:**

```bash
# View CloudWatch logs
aws logs tail /chimera/mainnet --follow

# Check EC2 instance status
aws ec2 describe-instances --instance-ids $INSTANCE_ID

# Check RDS status
aws rds describe-db-instances --db-instance-identifier chimera

# Check secrets
aws secretsmanager list-secrets --filters Key=name,Values=chimera
```

### Version History

- **v1.0.0** (2025-01-XX): Initial deployment documentation
- **v1.0.1** (TBD): Updates based on deployment experience

### Document Maintenance

- **Owner:** Technical Lead
- **Review Frequency:** Quarterly
- **Last Reviewed:** [DATE]
- **Next Review:** [DATE]

---

**END OF DEPLOYMENT DOCUMENTATION**
