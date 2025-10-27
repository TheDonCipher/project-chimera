# Development Guide for AI Coding Agents

**Project:** Chimera MEV Liquidation Bot  
**Target:** AI coding agents implementing the system  
**Version:** 1.0

## Overview

This guide provides specific instructions for AI coding agents implementing Project Chimera. It covers development principles, implementation patterns, testing strategies, and common pitfalls to avoid.

## Core Development Principles

### 1. Requirements-Driven Development

**WHAT**: Every implementation decision must map to specific requirements  
**HOW**: Use requirement IDs (e.g., REQ-SE-002) in code comments  
**WHY**: Maintains traceability and ensures all requirements are satisfied

```python
# REQ-SE-002: State reconciliation every 1 block
async def reconcile_state(self) -> bool:
    """Compare cached vs canonical state, trigger HALT if divergence >10 BPS"""
    for position in self.get_all_positions():
        # Implementation...
```

### 2. Start with Read-Only Changes

**WHAT**: Begin phases with analysis and preparation before modifications  
**HOW**: Read existing code, understand patterns, plan changes  
**WHY**: Prevents breaking existing functionality

**Example workflow:**

1. Read related files to understand current implementation
2. Identify integration points and dependencies
3. Plan changes that maintain backward compatibility
4. Implement incrementally with tests

### 3. Maintain Backward Compatibility

**WHAT**: Keep old systems working while new ones are being built  
**HOW**: Use feature flags, gradual rollout, parallel implementations  
**WHY**: Enables safe deployment and quick rollback

```python
# Feature flag for new bribe optimization algorithm
USE_DYNAMIC_BRIBE_V2 = os.getenv('ENABLE_BRIBE_V2', 'false').lower() == 'true'

if USE_DYNAMIC_BRIBE_V2:
    bribe = self.calculate_bribe_v2(gross_profit, path)
else:
    bribe = self.calculate_bribe_v1(gross_profit, path)
```

### 4. Use Feature Toggles

**WHAT**: Allow gradual rollout and quick rollback if needed  
**HOW**: Environment variables, configuration flags, database settings  
**WHY**: Reduces risk and enables A/B testing

### 5. Document Learnings

**WHAT**: Update your plan based on discoveries during implementation  
**HOW**: Add comments, update design docs, create ADRs (Architecture Decision Records)  
**WHY**: Captures institutional knowledge and prevents repeated mistakes

### 6. Test Boundary Conditions

**WHAT**: Focus testing on interfaces between old and new systems  
**HOW**: Write integration tests, test edge cases, validate data flow  
**WHY**: Integration points are where bugs most commonly occur

### 7. Plan for Rollback

**WHAT**: Each phase should be reversible if critical issues are discovered  
**HOW**: Git tags, database migrations with down scripts, feature flags  
**WHY**: Enables quick recovery from production issues

### 8. Communicate Progress

**WHAT**: Keep stakeholders updated with regular progress reports  
**HOW**: Commit messages, PR descriptions, status updates  
**WHY**: Builds trust and enables early feedback

### 9. Always Ask When Stuck

**WHAT**: Request clarification when requirements are ambiguous  
**HOW**: Use userInput tool, ask specific questions, provide context  
**WHY**: Prevents wasted effort on wrong implementations

### 10. Document Code Thoroughly

**WHAT**: Explain WHAT the file does, HOW it achieves it, WHY it's necessary  
**HOW**: Module docstrings, function docstrings, inline comments  
**WHY**: Enables future maintenance and debugging

```python
"""
StateEngine Module

WHAT: Maintains authoritative, real-time view of blockchain state
HOW: WebSocket subscriptions, event parsing, block-level reconciliation
WHY: Accurate state is critical for identifying liquidation opportunities

This module is the foundation of the MEV bot. It ensures that all liquidation
decisions are based on correct, up-to-date blockchain state. State divergence
can lead to wasted gas or missed opportunities, so reconciliation happens
every block (REQ-SE-002).
"""
```

## Implementation Patterns

### Simulation-First Philosophy (CRITICAL)

**The most important requirement: REQ-EP-002**

```python
async def plan_execution(self, opportunity: Opportunity) -> Optional[Bundle]:
    """
    CRITICAL: NEVER execute without successful simulation

    This is the single most important function in the entire system.
    Off-chain math is always wrong due to slippage, fees, rounding errors.
    """
    # 1. Build transaction
    tx = self.build_transaction(opportunity)

    # 2. Simulate via eth_call (GROUND TRUTH)
    simulation_result = await self.web3.eth.call(tx, block_identifier='latest')

    # 3. Validate simulation succeeded
    if simulation_result.status != 1:
        logger.warning("Simulation failed", extra={"opportunity": opportunity.id})
        return None  # NEVER proceed if simulation fails

    # 4. Parse actual profit
    actual_profit_wei = self.decode_profit(simulation_result)

    if actual_profit_wei <= 0:
        logger.warning("Simulation shows loss", extra={"profit": actual_profit_wei})
        return None  # NEVER proceed if unprofitable

    # 5. Only now proceed with cost calculation and submission
    # ...
```

### Base L2 Cost Calculation (CRITICAL)

**L1 data posting costs are 30-50% of total gas**

```python
def calculate_total_gas_cost(self, tx: Transaction, gas_estimate: int) -> int:
    """
    Calculate complete gas cost for Base L2 transaction

    CRITICAL: Must include both L2 execution and L1 data posting costs.
    L1 costs can be 30-50% of total and vary with Ethereum mainnet gas prices.
    """
    # L2 execution cost
    base_fee = self.web3.eth.get_block('latest')['baseFeePerGas']
    priority_fee = self.calculate_priority_fee()  # 75th percentile
    l2_cost_wei = gas_estimate * (base_fee + priority_fee)

    # L1 data posting cost (Base-specific)
    l1_block_contract = self.web3.eth.contract(
        address="0x4200000000000000000000000000000000000015",
        abi=self.L1_BLOCK_ABI
    )
    l1_gas_price = l1_block_contract.functions.l1GasPrice().call()
    l1_scalar = l1_block_contract.functions.scalar().call()
    calldata_size = len(tx.data)
    l1_cost_wei = calldata_size * l1_gas_price * l1_scalar

    # Total cost
    total_cost_wei = l2_cost_wei + l1_cost_wei

    logger.debug(
        "Gas cost breakdown",
        extra={
            "l2_cost_wei": l2_cost_wei,
            "l1_cost_wei": l1_cost_wei,
            "l1_percentage": (l1_cost_wei / total_cost_wei) * 100
        }
    )

    return total_cost_wei
```

### State Machine Pattern

```python
class SystemState(Enum):
    NORMAL = "NORMAL"
    THROTTLED = "THROTTLED"
    HALTED = "HALTED"

class SafetyController:
    def apply_state_transitions(self) -> None:
        """
        Apply automatic state transitions based on performance metrics

        State machine ensures system automatically responds to degraded
        performance without manual intervention.
        """
        current_state = self.state

        # Check HALT conditions (most severe)
        if (self.inclusion_rate < 0.50 or
            self.simulation_accuracy < 0.85 or
            self.consecutive_failures >= 3):

            if current_state != SystemState.HALTED:
                reason = self._get_halt_reason()
                self._transition_to_halted(reason)
                self._send_critical_alert(reason)
                return

        # Check THROTTLE conditions
        if ((0.50 <= self.inclusion_rate < 0.60) or
            (0.85 <= self.simulation_accuracy < 0.90)):

            if current_state == SystemState.NORMAL:
                reason = self._get_throttle_reason()
                self._transition_to_throttled(reason)
                self._send_high_alert(reason)
                return

        # Check NORMAL conditions
        if (self.inclusion_rate >= 0.60 and
            self.simulation_accuracy >= 0.90 and
            self.consecutive_failures < 3):

            if current_state == SystemState.THROTTLED:
                self._transition_to_normal()
                self._send_info_alert("System recovered to NORMAL")
                return
```

### Error Handling Pattern

```python
async def main_loop(self):
    """
    Main event loop with comprehensive error handling

    CRITICAL: Never crash the main loop. Catch exceptions at module
    boundaries and degrade gracefully.
    """
    while True:
        try:
            # Check safety state
            if self.safety.state == SystemState.HALTED:
                await asyncio.sleep(60)
                continue

            # Get opportunities
            try:
                opportunities = self.detector.scan_for_opportunities()
            except RPCError as e:
                logger.warning("RPC error during scan", extra={"error": str(e)})
                self.rpc_manager.switch_to_backup()
                continue
            except Exception as e:
                logger.error("Unexpected error during scan", exc_info=True)
                continue

            # Process each opportunity
            for opp in opportunities:
                try:
                    await self._process_opportunity(opp)
                except Exception as e:
                    logger.error(
                        "Error processing opportunity",
                        extra={"opportunity_id": opp.id},
                        exc_info=True
                    )
                    # Continue to next opportunity
                    continue

            await asyncio.sleep(5)

        except KeyboardInterrupt:
            logger.info("Shutting down gracefully...")
            break
        except Exception as e:
            logger.critical("Critical error in main loop", exc_info=True)
            # Enter HALTED state but don't crash
            self.safety.transition_to_halted("critical_main_loop_error")
            await asyncio.sleep(60)
```

## Testing Strategy

### Unit Test Pattern

```python
import pytest
from decimal import Decimal
from unittest.mock import Mock, patch

class TestOpportunityDetector:
    """
    Unit tests for OpportunityDetector module

    Focus: Test business logic in isolation with mocked dependencies
    """

    @pytest.fixture
    def detector(self):
        """Create detector with mocked dependencies"""
        state_engine = Mock()
        config = Mock()
        config.health_factor_threshold = Decimal('1.0')
        return OpportunityDetector(state_engine, config)

    def test_calculate_health_factor_liquidatable(self, detector):
        """Test health factor calculation for liquidatable position"""
        # Arrange
        position = Position(
            protocol="moonwell",
            user="0x123...",
            collateral_amount=1000 * 10**18,  # 1000 tokens
            collateral_asset="0xUSDC",
            debt_amount=900 * 10**18,  # 900 tokens
            debt_asset="0xETH",
            liquidation_threshold=Decimal('0.80')
        )

        # Mock oracle prices
        detector.get_price = Mock(side_effect=lambda asset: {
            "0xUSDC": Decimal('1.00'),  # $1 per USDC
            "0xETH": Decimal('2000.00')  # $2000 per ETH
        }[asset])

        # Act
        health_factor = detector.calculate_health_factor(position)

        # Assert
        # collateral_value = 1000 * 1.00 = $1000
        # debt_value = 900 * 2000 = $1,800,000
        # health_factor = (1000 * 0.80) / 1,800,000 = 0.000444
        assert health_factor < Decimal('1.0')
        assert position.is_liquidatable()

    def test_multi_oracle_sanity_check_rejects_divergent_prices(self, detector):
        """Test that opportunities are rejected when oracles diverge >5%"""
        # Arrange
        opportunity = Mock()
        opportunity.collateral_asset = "0xUSDC"

        # Primary oracle: $1.00, Secondary oracle: $1.10 (10% divergence)
        detector.get_chainlink_price = Mock(return_value=Decimal('1.00'))
        detector.get_pyth_price = Mock(return_value=Decimal('1.10'))

        # Act
        result = detector.apply_sanity_checks(opportunity)

        # Assert
        assert result is False  # Should reject due to >5% divergence
```

### Integration Test Pattern

```python
import pytest
from web3 import Web3
from eth_account import Account

@pytest.mark.integration
class TestEndToEndFlow:
    """
    Integration tests using local fork of Base mainnet

    Focus: Test complete flow from detection through execution
    """

    @pytest.fixture(scope="class")
    def forked_web3(self):
        """Create Web3 instance connected to local Anvil fork"""
        # Start Anvil fork in background
        process = subprocess.Popen([
            "anvil",
            "--fork-url", os.getenv("ALCHEMY_HTTPS"),
            "--fork-block-number", "12345678"
        ])

        # Wait for Anvil to start
        time.sleep(2)

        web3 = Web3(Web3.HTTPProvider("http://localhost:8545"))

        yield web3

        # Cleanup
        process.terminate()

    async def test_complete_liquidation_flow(self, forked_web3):
        """Test complete flow: detect → simulate → execute → verify"""
        # Arrange: Deploy Chimera contract
        chimera = deploy_chimera_contract(forked_web3)

        # Arrange: Create unhealthy position
        position = create_unhealthy_position(forked_web3)

        # Arrange: Initialize bot components
        state_engine = StateEngine(forked_web3, config)
        detector = OpportunityDetector(state_engine, config)
        planner = ExecutionPlanner(forked_web3, chimera, config)
        safety = SafetyController(config)

        # Act: Detect opportunity
        opportunities = detector.scan_for_opportunities()
        assert len(opportunities) > 0

        opp = opportunities[0]
        assert opp.health_factor < Decimal('1.0')

        # Act: Plan execution (includes simulation)
        bundle = await planner.plan_execution(opp)
        assert bundle is not None
        assert bundle.net_profit_usd >= 50

        # Act: Check safety
        allowed, reason = safety.check_execution_allowed(opp, bundle)
        assert allowed is True

        # Act: Submit bundle
        tx_hash = await planner.submit_bundle(bundle)

        # Assert: Transaction succeeded
        receipt = forked_web3.eth.wait_for_transaction_receipt(tx_hash)
        assert receipt['status'] == 1

        # Assert: Profit was transferred to treasury
        treasury_balance_after = get_token_balance(
            forked_web3,
            bundle.opportunity.debt_asset,
            chimera.treasury
        )
        assert treasury_balance_after > 0
```

## Common Pitfalls to Avoid

### 1. Skipping Simulation (NEVER DO THIS)

**❌ Wrong:**

```python
# Estimation looks good, skip expensive eth_call
if estimated_profit > 50:
    return self.build_bundle(opportunity)
```

**✅ Correct:**

```python
# Always simulate (REQ-EP-002 is non-negotiable)
simulation_result = await self.web3.eth.call(tx)
if simulation_result.status != 1:
    return None  # NEVER execute without successful simulation
```

### 2. Ignoring L1 Data Costs

**❌ Wrong:**

```python
# L2 gas is so cheap, that's the only cost
gas_cost = gas_estimate * gas_price
```

**✅ Correct:**

```python
# L1 data posting is 30-50% of total gas cost
l2_cost = gas_estimate * (base_fee + priority_fee)
l1_cost = calldata_size * l1_gas_price * l1_scalar
total_cost = l2_cost + l1_cost
```

### 3. Using Single RPC Provider

**❌ Wrong:**

```python
# One provider is simpler
web3 = Web3(Web3.WebsocketProvider(alchemy_wss))
```

**✅ Correct:**

```python
# Multi-provider redundancy (REQ-SE-005)
primary_ws = Web3(Web3.WebsocketProvider(alchemy_wss))
backup_ws = Web3(Web3.WebsocketProvider(quicknode_wss))
archive_http = Web3(Web3.HTTPProvider(alchemy_https))
```

### 4. Reconciling Every 5 Blocks

**❌ Wrong:**

```python
# Reconcile every 5 blocks to reduce load
if block_number % 5 == 0:
    await self.reconcile_state()
```

**✅ Correct:**

```python
# Reconcile EVERY block (REQ-SE-002)
# A 5-block lag (10 seconds) means 5+ invalid bundles submitted
await self.reconcile_state()
```

### 5. Hardcoding Configuration

**❌ Wrong:**

```python
# Hardcoded values
MAX_SINGLE_EXECUTION_USD = 500
BRIBE_PERCENTAGE = 0.15
```

**✅ Correct:**

```python
# Load from configuration for flexibility
self.max_single_execution_usd = config.limits.max_single_execution_usd
self.bribe_percentage = config.bribe.base_percentage
```

### 6. Swallowing Exceptions

**❌ Wrong:**

```python
try:
    result = await risky_operation()
except Exception:
    pass  # Silent failure
```

**✅ Correct:**

```python
try:
    result = await risky_operation()
except RPCError as e:
    logger.warning("RPC error, switching provider", extra={"error": str(e)})
    self.switch_to_backup_rpc()
except Exception as e:
    logger.error("Unexpected error", exc_info=True)
    self.safety.transition_to_halted("unexpected_error")
```

### 7. Not Logging Context

**❌ Wrong:**

```python
logger.error("Simulation failed")
```

**✅ Correct:**

```python
logger.error(
    "Simulation failed",
    extra={
        "opportunity_id": opportunity.id,
        "protocol": opportunity.protocol,
        "borrower": opportunity.borrower,
        "health_factor": str(opportunity.health_factor),
        "block_number": opportunity.detected_at_block
    }
)
```

## Development Workflow

### 1. Read the Spec

Before implementing any task:

1. Read the requirement in `requirements.md`
2. Read the design in `design.md`
3. Read the task details in `tasks.md`
4. Understand WHY the feature is needed

### 2. Plan the Implementation

1. Identify files that need to be created/modified
2. Identify dependencies and integration points
3. Plan test strategy
4. Consider error cases and edge conditions

### 3. Implement Incrementally

1. Start with data models and types
2. Implement core logic
3. Add error handling
4. Add logging
5. Write tests
6. Update documentation

### 4. Test Thoroughly

1. Write unit tests for business logic
2. Write integration tests for component interactions
3. Test error cases and edge conditions
4. Verify against requirements

### 5. Document Changes

1. Add docstrings to all functions
2. Add inline comments for complex logic
3. Update README if user-facing changes
4. Update design doc if architecture changes

## Debugging Tips

### Enable Verbose Logging

```python
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Use Interactive Debugger

```python
import pdb; pdb.set_trace()  # Set breakpoint
```

### Test Against Local Fork

```bash
# Start Anvil fork
anvil --fork-url $ALCHEMY_HTTPS --fork-block-number 12345678

# Run bot against local fork
export WEB3_PROVIDER_URI=http://localhost:8545
python bot/src/main.py
```

### Monitor Metrics in Real-Time

```python
# Add temporary metrics logging
logger.info(
    "Performance snapshot",
    extra={
        "inclusion_rate": self.safety.inclusion_rate,
        "simulation_accuracy": self.safety.simulation_accuracy,
        "consecutive_failures": self.safety.consecutive_failures,
        "daily_volume": self.safety.get_daily_volume()
    }
)
```

## Questions to Ask

When stuck or uncertain, ask:

1. **Requirements**: "Does this implementation satisfy REQ-XX-NNN?"
2. **Design**: "Is this consistent with the architecture in design.md?"
3. **Testing**: "How can I test this in isolation?"
4. **Error Handling**: "What can go wrong and how should I handle it?"
5. **Performance**: "Will this meet the latency requirements?"
6. **Security**: "Are there any security implications?"
7. **Observability**: "How will I debug this in production?"

## Success Criteria

Your implementation is successful when:

- [ ] All requirements are satisfied
- [ ] All tests pass with >80% coverage (>95% for critical paths)
- [ ] Code is well-documented with clear comments
- [ ] Error handling is comprehensive
- [ ] Logging provides sufficient context for debugging
- [ ] Performance meets latency requirements
- [ ] Security best practices are followed
- [ ] Code review feedback is addressed

---

**Remember**: This is a marathon, not a sprint. Execute with discipline, scale with patience, optimize continuously.
