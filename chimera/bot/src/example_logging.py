"""
Example usage of the logging infrastructure.

This demonstrates how to use the logging system in different modules.
"""

from pathlib import Path
from logging_config import (
    init_logging,
    get_logger,
    log_execution_attempt,
    log_state_transition,
    log_state_divergence,
    log_safety_violation,
    log_performance_metrics
)
from decimal import Decimal


def example_basic_logging():
    """Example: Basic logging from different modules"""
    print("\n=== Example 1: Basic Logging ===\n")
    
    # Initialize logging
    init_logging(
        log_dir=Path("logs"),
        log_level="INFO",
        enable_cloudwatch=False  # Disabled for local testing
    )
    
    # Get loggers for different modules
    state_engine_logger = get_logger("state_engine")
    opportunity_logger = get_logger("opportunity_detector")
    execution_logger = get_logger("execution_planner")
    
    # Log some events
    state_engine_logger.info(
        "websocket_connected",
        context={"provider": "alchemy", "endpoint": "wss://base-mainnet.g.alchemy.com/v2/..."}
    )
    
    opportunity_logger.info(
        "opportunity_detected",
        context={
            "protocol": "moonwell",
            "user": "0x1234567890123456789012345678901234567890",
            "health_factor": "0.95",
            "estimated_profit_usd": "125.50"
        }
    )
    
    execution_logger.info(
        "simulation_success",
        context={
            "simulated_profit_wei": "100000000000000000",
            "simulated_profit_usd": "120.00",
            "gas_estimate": "350000"
        }
    )
    
    print("✓ Basic logging examples written to logs/chimera.log\n")


def example_execution_logging():
    """Example: Logging execution attempts"""
    print("\n=== Example 2: Execution Attempt Logging ===\n")
    
    logger = get_logger("execution")
    
    # Example execution record
    execution_record = {
        "timestamp": "2024-01-15T10:30:45.123456Z",
        "block_number": 12345678,
        "protocol": "moonwell",
        "borrower": "0x1234567890123456789012345678901234567890",
        "collateral_asset": "0xWETH",
        "debt_asset": "0xUSDC",
        "health_factor": "0.92",
        "simulation_success": True,
        "simulated_profit_wei": "100000000000000000",
        "simulated_profit_usd": "120.00",
        "bundle_submitted": True,
        "tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "submission_path": "mempool",
        "bribe_wei": "15000000000000000",
        "status": "pending",
        "operator_address": "0x9876543210987654321098765432109876543210",
        "state_at_execution": "NORMAL"
    }
    
    log_execution_attempt(logger, execution_record)
    
    print("✓ Execution attempt logged to logs/executions.log\n")


def example_state_transition():
    """Example: Logging state transitions"""
    print("\n=== Example 3: State Transition Logging ===\n")
    
    logger = get_logger("safety_controller")
    
    # Example state transition
    log_state_transition(
        logger=logger,
        from_state="NORMAL",
        to_state="THROTTLED",
        reason="Inclusion rate dropped to 55%",
        metrics={
            "inclusion_rate": "0.55",
            "simulation_accuracy": "0.92",
            "consecutive_failures": 0
        }
    )
    
    print("✓ State transition logged\n")


def example_state_divergence():
    """Example: Logging state divergence"""
    print("\n=== Example 4: State Divergence Logging ===\n")
    
    logger = get_logger("state_engine")
    
    # Example divergence
    log_state_divergence(
        logger=logger,
        protocol="moonwell",
        user="0x1234567890123456789012345678901234567890",
        field="debt_amount",
        cached_value=1000000000000000000,
        canonical_value=1001500000000000000,
        divergence_bps=150,  # 1.5%
        block_number=12345678
    )
    
    print("✓ State divergence logged (would trigger HALT if >10 BPS)\n")


def example_safety_violation():
    """Example: Logging safety violations"""
    print("\n=== Example 5: Safety Violation Logging ===\n")
    
    logger = get_logger("safety_controller")
    
    # Example limit violation
    log_safety_violation(
        logger=logger,
        violation_type="max_daily_volume",
        current_value="2450.00",
        limit_value="2500.00",
        context={
            "remaining_capacity_usd": "50.00",
            "opportunity_size_usd": "150.00"
        }
    )
    
    print("✓ Safety violation logged\n")


def example_performance_metrics():
    """Example: Logging performance metrics"""
    print("\n=== Example 6: Performance Metrics Logging ===\n")
    
    logger = get_logger("safety_controller")
    
    # Example metrics
    metrics = {
        "window_size": 100,
        "total_submissions": 100,
        "successful_inclusions": 68,
        "inclusion_rate": "0.68",
        "simulation_accuracy": "0.94",
        "total_profit_usd": "8450.00",
        "average_profit_usd": "124.26",
        "consecutive_failures": 0
    }
    
    log_performance_metrics(logger, metrics)
    
    print("✓ Performance metrics logged\n")


def example_error_logging():
    """Example: Logging errors with stack traces"""
    print("\n=== Example 7: Error Logging ===\n")
    
    logger = get_logger("execution_planner")
    
    try:
        # Simulate an error
        raise ValueError("Simulation failed: insufficient liquidity in DEX pool")
    except Exception as e:
        logger.error(
            "simulation_failed",
            context={
                "opportunity_id": "opp_12345",
                "protocol": "moonwell",
                "error_type": type(e).__name__,
                "error_message": str(e)
            },
            exc_info=True
        )
    
    print("✓ Error logged with stack trace\n")


def main():
    """Run all examples"""
    print("\n" + "="*60)
    print("Chimera Logging Infrastructure Examples")
    print("="*60)
    
    example_basic_logging()
    example_execution_logging()
    example_state_transition()
    example_state_divergence()
    example_safety_violation()
    example_performance_metrics()
    example_error_logging()
    
    print("="*60)
    print("All examples completed!")
    print("Check the logs/ directory for output files:")
    print("  - logs/chimera.log (all logs)")
    print("  - logs/executions.log (execution attempts only)")
    print("="*60 + "\n")


if __name__ == "__main__":
    main()
