"""
Main Bot Orchestrator

Entry point for the Chimera MEV liquidation bot.
"""

from pathlib import Path
from logging_config import init_logging, get_logger
from config import get_config


def main():
    """
    Main entry point for the Chimera bot.
    
    Initializes configuration, logging, and starts the main event loop.
    """
    # Load configuration
    config = get_config()
    
    # Initialize logging
    init_logging(
        log_dir=Path("logs"),
        log_level="INFO",
        enable_cloudwatch=config.monitoring.cloudwatch_enabled,
        cloudwatch_region=config.monitoring.cloudwatch_region,
        cloudwatch_log_group=config.monitoring.cloudwatch_namespace,
    )
    
    logger = get_logger("main")
    logger.info(
        "chimera_starting",
        context={
            "network": config.network_name,
            "chain_id": config.chain_id,
            "operator": config.execution.operator_address
        }
    )
    
    # TODO: Initialize modules and start event loop
    # This will be implemented in future tasks
    
    logger.info("chimera_initialized", context={"status": "ready"})


if __name__ == "__main__":
    main()
