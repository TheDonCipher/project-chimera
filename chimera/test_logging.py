"""
Simple test script for logging infrastructure.
Run from chimera/ directory to avoid import conflicts.
"""

import sys
from pathlib import Path

# Add bot/src to path
sys.path.insert(0, str(Path(__file__).parent / "bot" / "src"))

from logging_config import (
    init_logging,
    get_logger,
    log_execution_attempt,
    log_state_transition,
    log_state_divergence,
    log_safety_violation,
    log_performance_metrics
)


def test_basic_logging():
    """Test basic logging functionality"""
    print("\n=== Testing Basic Logging ===\n")
    
    # Initialize logging
    init_logging(
        log_dir=Path("logs"),
        log_level="INFO",
        enable_cloudwatch=False
    )
    
    # Get loggers for different modules
    state_logger = get_logger("state_engine")
    opp_logger = get_logger("opportunity_detector")
    exec_logger = get_logger("execution_planner")
    
    # Log some events
    state_logger.info(
        "websocket_connected",
        context={"provider": "alchemy", "endpoint": "wss://base-mainnet.g.alchemy.com/v2/..."}
    )
    
    opp_logger.info(
        "opportunity_detected",
        context={
            "protocol": "moonwell",
            "user": "0x1234567890123456789012345678901234567890",
            "health_factor": "0.95",
            "estimated_profit_usd": "125.50"
        }
    )
    
    exec_logger.info(
        "simulation_success",
        context={
            "simulated_profit_wei": "100000000000000000",
            "simulated_profit_usd": "120.00",
            "gas_estimate": "350000"
        }
    )
    
    print("✓ Basic logging successful")


def test_execution_logging():
    """Test execution attempt logging"""
    print("\n=== Testing Execution Logging ===\n")
    
    logger = get_logger("execution")
    
    execution_record = {
        "timestamp": "2024-01-15T10:30:45.123456Z",
        "block_number": 12345678,
        "protocol": "moonwell",
        "borrower": "0x1234567890123456789012345678901234567890",
        "health_factor": "0.92",
        "simulation_success": True,
        "simulated_profit_usd": "120.00",
        "tx_hash": "0xabcdef1234567890",
        "status": "pending"
    }
    
    log_execution_attempt(logger, execution_record)
    print("✓ Execution logging successful")


def test_state_transition():
    """Test state transition logging"""
    print("\n=== Testing State Transition ===\n")
    
    logger = get_logger("safety_controller")
    
    log_state_transition(
        logger=logger,
        from_state="NORMAL",
        to_state="THROTTLED",
        reason="Inclusion rate dropped to 55%",
        metrics={"inclusion_rate": "0.55"}
    )
    
    print("✓ State transition logging successful")


def test_state_divergence():
    """Test state divergence logging"""
    print("\n=== Testing State Divergence ===\n")
    
    logger = get_logger("state_engine")
    
    log_state_divergence(
        logger=logger,
        protocol="moonwell",
        user="0x1234567890123456789012345678901234567890",
        field="debt_amount",
        cached_value=1000000000000000000,
        canonical_value=1001500000000000000,
        divergence_bps=150,
        block_number=12345678
    )
    
    print("✓ State divergence logging successful")


def test_safety_violation():
    """Test safety violation logging"""
    print("\n=== Testing Safety Violation ===\n")
    
    logger = get_logger("safety_controller")
    
    log_safety_violation(
        logger=logger,
        violation_type="max_daily_volume",
        current_value="2450.00",
        limit_value="2500.00",
        context={"remaining_capacity_usd": "50.00"}
    )
    
    print("✓ Safety violation logging successful")


def test_performance_metrics():
    """Test performance metrics logging"""
    print("\n=== Testing Performance Metrics ===\n")
    
    logger = get_logger("safety_controller")
    
    metrics = {
        "inclusion_rate": "0.68",
        "simulation_accuracy": "0.94",
        "total_profit_usd": "8450.00"
    }
    
    log_performance_metrics(logger, metrics)
    print("✓ Performance metrics logging successful")


def test_error_logging():
    """Test error logging with stack traces"""
    print("\n=== Testing Error Logging ===\n")
    
    logger = get_logger("execution_planner")
    
    try:
        raise ValueError("Simulation failed: test error")
    except Exception as e:
        logger.error(
            "simulation_failed",
            context={
                "opportunity_id": "opp_12345",
                "error_type": type(e).__name__
            },
            exc_info=True
        )
    
    print("✓ Error logging successful")


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("Chimera Logging Infrastructure Tests")
    print("="*60)
    
    try:
        test_basic_logging()
        test_execution_logging()
        test_state_transition()
        test_state_divergence()
        test_safety_violation()
        test_performance_metrics()
        test_error_logging()
        
        print("\n" + "="*60)
        print("✓ All tests passed!")
        print("\nLog files created:")
        print("  - logs/chimera.log (all logs)")
        print("  - logs/executions.log (execution attempts only)")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
