"""
Unit tests for SafetyController module (Task 6.6)

Tests:
- State machine transitions (all paths)
- Limit enforcement (single, daily, minimum)
- Consecutive failure tracking
- Metrics calculation (inclusion rate, simulation accuracy)
- Throttling logic (50% random skip)
"""

import sys
from decimal import Decimal
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
import random

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.types import (
    Position, Opportunity, Bundle, Transaction, SubmissionPath,
    ExecutionRecord, ExecutionStatus, SystemState, PerformanceMetrics
)
from src.config import ChimeraConfig, SafetyLimits, ExecutionConfig
from src.safety_controller import SafetyController
from src.database import DatabaseManager


def create_mock_config():
    """Create mock configuration for testing"""
    config = Mock(spec=ChimeraConfig)
    config.safety = SafetyLimits(
        max_single_execution_usd=Decimal('500'),
        max_daily_volume_usd=Decimal('2500'),
        min_profit_usd=Decimal('50'),
        max_consecutive_failures=3,
        throttle_inclusion_rate=Decimal('0.60'),
        throttle_accuracy=Decimal('0.90'),
        halt_inclusion_rate=Decimal('0.50'),
        halt_accuracy=Decimal('0.85')
    )
    config.execution = ExecutionConfig(
        operator_address='0x1234567890123456789012345678901234567890',
        chimera_contract_address='0x2234567890123456789012345678901234567890',
        aave_v3_pool='0x3234567890123456789012345678901234567890',
        baseline_bribe_percent=Decimal('15'),
        max_bribe_percent=Decimal('40'),
        bribe_increase_percent=Decimal('5'),
        bribe_decrease_percent=Decimal('2'),
        flash_loan_premium_percent=Decimal('0.09')
    )
    return config


def create_mock_db_manager():
    """Create mock database manager"""
    db_manager = Mock(spec=DatabaseManager)
    session_mock = MagicMock()
    session_mock.__enter__ = Mock(return_value=session_mock)
    session_mock.__exit__ = Mock(return_value=False)
    db_manager.get_session = Mock(return_value=session_mock)
    return db_manager


def create_mock_position():
    """Create mock position"""
    return Position(
        protocol='moonwell',
        user='0x1234567890123456789012345678901234567890',
        collateral_asset='0x4200000000000000000000000000000000000006',
        collateral_amount=1000 * 10**18,
        debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        debt_amount=800 * 10**18,
        liquidation_threshold=Decimal('0.80'),
        last_update_block=1000,
        blocks_unhealthy=2
    )


def create_mock_opportunity():
    """Create mock opportunity"""
    position = create_mock_position()
    return Opportunity(
        position=position,
        health_factor=Decimal('0.95'),
        collateral_price_usd=Decimal('2000'),
        debt_price_usd=Decimal('1'),
        liquidation_bonus=Decimal('0.05'),
        estimated_gross_profit_usd=Decimal('100'),
        estimated_net_profit_usd=Decimal('75'),
        detected_at_block=1001
    )


def create_mock_transaction():
    """Create mock transaction"""
    return Transaction(
        to='0x2234567890123456789012345678901234567890',
        data='0x1234',
        gas_limit=500000,
        max_fee_per_gas=1000000000,
        max_priority_fee_per_gas=1000000000,
        nonce=1
    )


def create_mock_bundle(net_profit_usd=Decimal('100')):
    """Create mock bundle"""
    opportunity = create_mock_opportunity()
    transaction = create_mock_transaction()
    
    return Bundle(
        opportunity=opportunity,
        transaction=transaction,
        simulated_profit_wei=100 * 10**18,
        simulated_profit_usd=Decimal('100'),
        gas_estimate=500000,
        l2_gas_cost_usd=Decimal('10'),
        l1_data_cost_usd=Decimal('5'),
        bribe_usd=Decimal('15'),
        flash_loan_cost_usd=Decimal('0.09'),
        slippage_cost_usd=Decimal('1'),
        total_cost_usd=Decimal('31.09'),
        net_profit_usd=net_profit_usd,
        submission_path=SubmissionPath.MEMPOOL
    )


# ============================================================================
# Test State Machine Transitions
# ============================================================================

def test_initial_state_is_normal():
    """Test that SafetyController initializes in NORMAL state"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    assert controller.current_state == SystemState.NORMAL
    print("✓ Initial state is NORMAL")


def test_can_execute_in_normal_state():
    """Test that execution is allowed in NORMAL state"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    assert controller.can_execute() == True
    print("✓ Can execute in NORMAL state")


def test_cannot_execute_in_halted_state():
    """Test that execution is blocked in HALTED state"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller.transition_state(SystemState.HALTED, "Test halt")
    
    assert controller.can_execute() == False
    print("✓ Cannot execute in HALTED state")


def test_throttled_state_random_skip():
    """Test that THROTTLED state skips ~50% of executions"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller.transition_state(SystemState.THROTTLED, "Test throttle")
    
    # Test 100 times and check that roughly 50% are allowed
    random.seed(42)  # For reproducibility
    allowed_count = sum(1 for _ in range(100) if controller.can_execute())
    
    # Should be roughly 50% (allow 30-70% range for randomness)
    assert 30 <= allowed_count <= 70
    print(f"✓ THROTTLED state allowed {allowed_count}/100 executions (expected ~50)")


def test_transition_normal_to_throttled():
    """Test transition from NORMAL to THROTTLED"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    assert controller.current_state == SystemState.NORMAL
    
    controller.transition_state(SystemState.THROTTLED, "Performance warning")
    
    assert controller.current_state == SystemState.THROTTLED
    print("✓ Transition NORMAL → THROTTLED")


def test_transition_normal_to_halted():
    """Test transition from NORMAL to HALTED"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    assert controller.current_state == SystemState.NORMAL
    
    controller.transition_state(SystemState.HALTED, "Critical failure")
    
    assert controller.current_state == SystemState.HALTED
    print("✓ Transition NORMAL → HALTED")


def test_transition_throttled_to_normal():
    """Test transition from THROTTLED to NORMAL"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller.transition_state(SystemState.THROTTLED, "Test")
    assert controller.current_state == SystemState.THROTTLED
    
    controller.transition_state(SystemState.NORMAL, "Performance recovered")
    
    assert controller.current_state == SystemState.NORMAL
    print("✓ Transition THROTTLED → NORMAL")


def test_manual_resume_from_halted():
    """Test manual resume from HALTED state"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller.transition_state(SystemState.HALTED, "Test halt")
    controller._consecutive_failures = 3
    
    controller.manual_resume("operator@example.com", "Issue resolved")
    
    assert controller.current_state == SystemState.NORMAL
    assert controller._consecutive_failures == 0
    print("✓ Manual resume from HALTED resets state and failures")


# ============================================================================
# Test Limit Enforcement
# ============================================================================

def test_validate_execution_min_profit():
    """Test minimum profit limit enforcement"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Create bundle below minimum profit ($50)
    bundle = create_mock_bundle(net_profit_usd=Decimal('40'))
    
    is_valid, reason = controller.validate_execution(bundle)
    
    assert is_valid == False
    assert "below minimum" in reason.lower()
    print("✓ Rejects execution below minimum profit")


def test_validate_execution_max_single():
    """Test maximum single execution limit enforcement"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Create bundle above single execution limit ($500)
    bundle = create_mock_bundle(net_profit_usd=Decimal('600'))
    
    is_valid, reason = controller.validate_execution(bundle)
    
    assert is_valid == False
    assert "exceeds single execution limit" in reason.lower()
    print("✓ Rejects execution above single execution limit")


def test_validate_execution_max_daily():
    """Test maximum daily volume limit enforcement"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Set daily volume to $2400 (limit is $2500)
    controller._daily_volume_usd = Decimal('2400')
    
    # Try to execute $200 bundle (would exceed limit)
    bundle = create_mock_bundle(net_profit_usd=Decimal('200'))
    
    is_valid, reason = controller.validate_execution(bundle)
    
    assert is_valid == False
    assert "exceeds limit" in reason.lower()
    print("✓ Rejects execution that would exceed daily volume limit")


def test_validate_execution_consecutive_failures():
    """Test consecutive failures limit enforcement"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Set consecutive failures to maximum (3)
    controller._consecutive_failures = 3
    
    bundle = create_mock_bundle(net_profit_usd=Decimal('100'))
    
    is_valid, reason = controller.validate_execution(bundle)
    
    assert is_valid == False
    assert "consecutive failures" in reason.lower()
    print("✓ Rejects execution when consecutive failures at maximum")


def test_validate_execution_success():
    """Test successful validation"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    bundle = create_mock_bundle(net_profit_usd=Decimal('100'))
    
    is_valid, reason = controller.validate_execution(bundle)
    
    assert is_valid == True
    assert reason is None
    print("✓ Validates execution that meets all limits")


def test_daily_volume_reset():
    """Test daily volume resets at midnight UTC"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Set daily volume
    controller._daily_volume_usd = Decimal('1000')
    
    # Set reset time to past
    controller._daily_reset_time = datetime.utcnow() - timedelta(hours=1)
    
    # Trigger reset check
    controller._reset_daily_volume_if_needed()
    
    assert controller._daily_volume_usd == Decimal('0')
    assert controller._daily_reset_time > datetime.utcnow()
    print("✓ Daily volume resets at midnight UTC")


# ============================================================================
# Test Consecutive Failure Tracking
# ============================================================================

def test_consecutive_failures_increment_on_failure():
    """Test consecutive failures increment on failed submission"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Create failed execution record
    record = ExecutionRecord(
        timestamp=datetime.utcnow(),
        block_number=1000,
        protocol='moonwell',
        borrower='0x1234567890123456789012345678901234567890',
        collateral_asset='0x4200000000000000000000000000000000000006',
        debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        health_factor=Decimal('0.95'),
        simulation_success=True,
        simulated_profit_usd=Decimal('100'),
        bundle_submitted=True,
        status=ExecutionStatus.FAILED,
        included=False,
        operator_address='0x1234567890123456789012345678901234567890',
        state_at_execution=SystemState.NORMAL
    )
    
    assert controller._consecutive_failures == 0
    
    controller.record_execution(record)
    
    assert controller._consecutive_failures == 1
    print("✓ Consecutive failures increment on failed submission")


def test_consecutive_failures_reset_on_success():
    """Test consecutive failures reset on successful inclusion"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller._consecutive_failures = 2
    
    # Create successful execution record
    record = ExecutionRecord(
        timestamp=datetime.utcnow(),
        block_number=1000,
        protocol='moonwell',
        borrower='0x1234567890123456789012345678901234567890',
        collateral_asset='0x4200000000000000000000000000000000000006',
        debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        health_factor=Decimal('0.95'),
        simulation_success=True,
        simulated_profit_usd=Decimal('100'),
        bundle_submitted=True,
        status=ExecutionStatus.INCLUDED,
        included=True,
        actual_profit_usd=Decimal('95'),
        operator_address='0x1234567890123456789012345678901234567890',
        state_at_execution=SystemState.NORMAL
    )
    
    controller.record_execution(record)
    
    assert controller._consecutive_failures == 0
    print("✓ Consecutive failures reset on successful inclusion")


def test_consecutive_failures_multiple():
    """Test multiple consecutive failures"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Record 3 failures
    for i in range(3):
        record = ExecutionRecord(
            timestamp=datetime.utcnow(),
            block_number=1000 + i,
            protocol='moonwell',
            borrower='0x1234567890123456789012345678901234567890',
            collateral_asset='0x4200000000000000000000000000000000000006',
            debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            health_factor=Decimal('0.95'),
            simulation_success=True,
            bundle_submitted=True,
            status=ExecutionStatus.FAILED,
            included=False,
            operator_address='0x1234567890123456789012345678901234567890',
            state_at_execution=SystemState.NORMAL
        )
        controller.record_execution(record)
    
    assert controller._consecutive_failures == 3
    print("✓ Multiple consecutive failures tracked correctly")


# ============================================================================
# Test Metrics Calculation
# ============================================================================

def test_calculate_metrics_inclusion_rate():
    """Test inclusion rate calculation"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add 10 submissions: 7 included, 3 failed
    for i in range(10):
        included = i < 7
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': included,
            'tx_hash': f'0x{i:064x}'
        })
    
    metrics = controller.calculate_metrics(force=True)
    
    assert metrics.total_submissions == 10
    assert metrics.successful_inclusions == 7
    assert metrics.inclusion_rate == Decimal('0.7')
    print("✓ Inclusion rate calculated correctly (70%)")


def test_calculate_metrics_simulation_accuracy():
    """Test simulation accuracy calculation"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add 5 executions with varying accuracy
    test_data = [
        (100, 95),   # 95% accuracy
        (100, 90),   # 90% accuracy
        (100, 100),  # 100% accuracy
        (100, 85),   # 85% accuracy
        (100, 80),   # 80% accuracy
    ]
    
    for simulated, actual in test_data:
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': simulated,
            'actual_profit_usd': actual
        })
    
    metrics = controller.calculate_metrics(force=True)
    
    # Average accuracy: (0.95 + 0.90 + 1.00 + 0.85 + 0.80) / 5 = 0.90
    assert metrics.total_executions == 5
    assert metrics.simulation_accuracy == Decimal('0.90')
    print("✓ Simulation accuracy calculated correctly (90%)")


def test_calculate_metrics_profitability():
    """Test profitability metrics calculation"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add 4 executions with profits
    profits = [100, 150, 80, 120]
    for profit in profits:
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': profit,
            'actual_profit_usd': profit
        })
    
    metrics = controller.calculate_metrics(force=True)
    
    assert metrics.total_profit_usd == Decimal('450')
    assert metrics.average_profit_usd == Decimal('112.5')
    print("✓ Profitability metrics calculated correctly")


def test_calculate_metrics_empty_history():
    """Test metrics calculation with empty history"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    metrics = controller.calculate_metrics(force=True)
    
    assert metrics.total_submissions == 0
    assert metrics.inclusion_rate == Decimal('0')
    assert metrics.total_executions == 0
    assert metrics.simulation_accuracy == Decimal('0')
    print("✓ Metrics calculation handles empty history")


def test_calculate_metrics_caching():
    """Test metrics caching (10 minute window)"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add some data
    controller._submission_history.append({
        'timestamp': datetime.utcnow(),
        'included': True,
        'tx_hash': '0x123'
    })
    
    # First calculation
    metrics1 = controller.calculate_metrics(force=True)
    
    # Second calculation (should use cache)
    metrics2 = controller.calculate_metrics(force=False)
    
    assert metrics1.timestamp == metrics2.timestamp
    print("✓ Metrics caching works correctly")


# ============================================================================
# Test Automatic State Transitions
# ============================================================================

def test_auto_transition_normal_to_throttled_low_inclusion():
    """Test automatic transition to THROTTLED on low inclusion rate"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add 20 submissions with 55% inclusion (between 50-60%)
    for i in range(20):
        included = i < 11  # 11/20 = 55%
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': included,
            'tx_hash': f'0x{i:064x}'
        })
    
    # Add some execution history to avoid empty accuracy
    for i in range(15):
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': 100,
            'actual_profit_usd': 95
        })
    
    controller.check_and_apply_transitions()
    
    assert controller.current_state == SystemState.THROTTLED
    print("✓ Auto-transition NORMAL → THROTTLED on low inclusion (55%)")


def test_auto_transition_normal_to_throttled_low_accuracy():
    """Test automatic transition to THROTTLED on low accuracy"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add good inclusion rate
    for i in range(20):
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': True,
            'tx_hash': f'0x{i:064x}'
        })
    
    # Add 20 executions with 87% accuracy (between 85-90%)
    for i in range(20):
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': 100,
            'actual_profit_usd': 87
        })
    
    controller.check_and_apply_transitions()
    
    assert controller.current_state == SystemState.THROTTLED
    print("✓ Auto-transition NORMAL → THROTTLED on low accuracy (87%)")


def test_auto_transition_normal_to_halted_very_low_inclusion():
    """Test automatic transition to HALTED on very low inclusion rate"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add 20 submissions with 40% inclusion (<50%)
    for i in range(20):
        included = i < 8  # 8/20 = 40%
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': included,
            'tx_hash': f'0x{i:064x}'
        })
    
    # Add some execution history
    for i in range(15):
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': 100,
            'actual_profit_usd': 95
        })
    
    controller.check_and_apply_transitions()
    
    assert controller.current_state == SystemState.HALTED
    print("✓ Auto-transition NORMAL → HALTED on very low inclusion (40%)")


def test_auto_transition_normal_to_halted_very_low_accuracy():
    """Test automatic transition to HALTED on very low accuracy"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Add good inclusion rate
    for i in range(20):
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': True,
            'tx_hash': f'0x{i:064x}'
        })
    
    # Add 20 executions with 80% accuracy (<85%)
    for i in range(20):
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': 100,
            'actual_profit_usd': 80
        })
    
    controller.check_and_apply_transitions()
    
    assert controller.current_state == SystemState.HALTED
    print("✓ Auto-transition NORMAL → HALTED on very low accuracy (80%)")


def test_auto_transition_normal_to_halted_consecutive_failures():
    """Test automatic transition to HALTED on consecutive failures"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller._consecutive_failures = 3
    
    # Add some history to avoid empty metrics
    for i in range(15):
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': True,
            'tx_hash': f'0x{i:064x}'
        })
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': 100,
            'actual_profit_usd': 95
        })
    
    controller.check_and_apply_transitions()
    
    assert controller.current_state == SystemState.HALTED
    print("✓ Auto-transition NORMAL → HALTED on consecutive failures (3)")


def test_auto_transition_throttled_to_normal():
    """Test automatic transition from THROTTLED to NORMAL on recovery"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller.transition_state(SystemState.THROTTLED, "Test")
    
    # Add 20 submissions with 70% inclusion (>60%)
    for i in range(20):
        included = i < 14  # 14/20 = 70%
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': included,
            'tx_hash': f'0x{i:064x}'
        })
    
    # Add 20 executions with 95% accuracy (>90%)
    for i in range(20):
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': 100,
            'actual_profit_usd': 95
        })
    
    controller.check_and_apply_transitions()
    
    assert controller.current_state == SystemState.NORMAL
    print("✓ Auto-transition THROTTLED → NORMAL on recovery (70% inclusion, 95% accuracy)")


def test_halted_requires_manual_intervention():
    """Test that HALTED state requires manual intervention"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    controller.transition_state(SystemState.HALTED, "Test")
    
    # Add excellent metrics
    for i in range(20):
        controller._submission_history.append({
            'timestamp': datetime.utcnow(),
            'included': True,
            'tx_hash': f'0x{i:064x}'
        })
        controller._execution_history.append({
            'timestamp': datetime.utcnow(),
            'simulated_profit_usd': 100,
            'actual_profit_usd': 100
        })
    
    # Should NOT auto-transition from HALTED
    controller.check_and_apply_transitions()
    
    assert controller.current_state == SystemState.HALTED
    print("✓ HALTED state requires manual intervention (no auto-recovery)")


# ============================================================================
# Test Execution Tracking
# ============================================================================

def test_record_execution_updates_daily_volume():
    """Test that successful executions update daily volume"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    record = ExecutionRecord(
        timestamp=datetime.utcnow(),
        block_number=1000,
        protocol='moonwell',
        borrower='0x1234567890123456789012345678901234567890',
        collateral_asset='0x4200000000000000000000000000000000000006',
        debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        health_factor=Decimal('0.95'),
        simulation_success=True,
        bundle_submitted=True,
        status=ExecutionStatus.INCLUDED,
        included=True,
        actual_profit_usd=Decimal('100'),
        operator_address='0x1234567890123456789012345678901234567890',
        state_at_execution=SystemState.NORMAL
    )
    
    controller.record_execution(record)
    
    assert controller._daily_volume_usd == Decimal('100')
    print("✓ Successful execution updates daily volume")


def test_record_execution_adds_to_history():
    """Test that executions are added to history"""
    config = create_mock_config()
    db_manager = create_mock_db_manager()
    
    controller = SafetyController(config, db_manager)
    
    # Submission that was included
    record = ExecutionRecord(
        timestamp=datetime.utcnow(),
        block_number=1000,
        protocol='moonwell',
        borrower='0x1234567890123456789012345678901234567890',
        collateral_asset='0x4200000000000000000000000000000000000006',
        debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
        health_factor=Decimal('0.95'),
        simulation_success=True,
        simulated_profit_usd=Decimal('100'),
        bundle_submitted=True,
        tx_hash='0x123',
        status=ExecutionStatus.INCLUDED,
        included=True,
        actual_profit_usd=Decimal('95'),
        operator_address='0x1234567890123456789012345678901234567890',
        state_at_execution=SystemState.NORMAL
    )
    
    controller.record_execution(record)
    
    assert len(controller._submission_history) == 1
    assert len(controller._execution_history) == 1
    assert controller._submission_history[0]['included'] == True
    assert controller._execution_history[0]['actual_profit_usd'] == Decimal('95')
    print("✓ Execution added to submission and execution history")


# ============================================================================
# Run All Tests
# ============================================================================

def run_all_tests():
    """Run all SafetyController tests"""
    print("\n" + "="*70)
    print("SafetyController Unit Tests (Task 6.6)")
    print("="*70 + "\n")
    
    print("State Machine Transitions:")
    print("-" * 70)
    test_initial_state_is_normal()
    test_can_execute_in_normal_state()
    test_cannot_execute_in_halted_state()
    test_throttled_state_random_skip()
    test_transition_normal_to_throttled()
    test_transition_normal_to_halted()
    test_transition_throttled_to_normal()
    test_manual_resume_from_halted()
    
    print("\nLimit Enforcement:")
    print("-" * 70)
    test_validate_execution_min_profit()
    test_validate_execution_max_single()
    test_validate_execution_max_daily()
    test_validate_execution_consecutive_failures()
    test_validate_execution_success()
    test_daily_volume_reset()
    
    print("\nConsecutive Failure Tracking:")
    print("-" * 70)
    test_consecutive_failures_increment_on_failure()
    test_consecutive_failures_reset_on_success()
    test_consecutive_failures_multiple()
    
    print("\nMetrics Calculation:")
    print("-" * 70)
    test_calculate_metrics_inclusion_rate()
    test_calculate_metrics_simulation_accuracy()
    test_calculate_metrics_profitability()
    test_calculate_metrics_empty_history()
    test_calculate_metrics_caching()
    
    print("\nAutomatic State Transitions:")
    print("-" * 70)
    test_auto_transition_normal_to_throttled_low_inclusion()
    test_auto_transition_normal_to_throttled_low_accuracy()
    test_auto_transition_normal_to_halted_very_low_inclusion()
    test_auto_transition_normal_to_halted_very_low_accuracy()
    test_auto_transition_normal_to_halted_consecutive_failures()
    test_auto_transition_throttled_to_normal()
    test_halted_requires_manual_intervention()
    
    print("\nExecution Tracking:")
    print("-" * 70)
    test_record_execution_updates_daily_volume()
    test_record_execution_adds_to_history()
    
    print("\n" + "="*70)
    print("All SafetyController tests passed! ✓")
    print("="*70 + "\n")


if __name__ == "__main__":
    run_all_tests()
