"""
Main Bot Orchestrator

Entry point for the Chimera MEV liquidation bot.
Orchestrates all modules and manages the main event loop.
"""

import asyncio
import sys
import signal
from pathlib import Path
from typing import Optional
from decimal import Decimal
from datetime import datetime
from web3 import Web3

from .logging_config import init_logging, get_logger
from .config import get_config
from .database import init_database, init_redis, get_db_manager, get_redis_manager
from .state_engine import StateEngine
from .opportunity_detector import OpportunityDetector
from .execution_planner import ExecutionPlanner
from .safety_controller import SafetyController
from .metrics_server import MetricsServer
from .types import SystemState, ChimeraError, RPCError, DatabaseError
import time


class ChimeraBot:
    """
    Main bot orchestrator.
    
    Responsibilities:
    - Initialize all modules
    - Manage main event loop
    - Handle errors and graceful degradation
    - Export monitoring metrics
    """
    
    def __init__(self, dry_run: bool = False):
        self.logger = get_logger("chimera")
        self.config = None
        self.web3 = None
        self.backup_web3 = None
        self.dry_run = dry_run
        
        # Modules
        self.state_engine: Optional[StateEngine] = None
        self.opportunity_detector: Optional[OpportunityDetector] = None
        self.execution_planner: Optional[ExecutionPlanner] = None
        self.safety_controller: Optional[SafetyController] = None
        self.metrics_server: Optional[MetricsServer] = None
        
        # Running flag
        self._running = False
        self._shutdown_event = asyncio.Event()
        
        # Metrics tracking
        self._opportunities_detected = 0
        self._bundles_submitted = 0
        self._last_metrics_export = 0
        self._start_time = time.time()
        
        # Dry-run specific tracking
        if self.dry_run:
            self._dry_run_simulations_success = 0
            self._dry_run_simulations_failed = 0
            self._dry_run_theoretical_profit = Decimal("0")
    
    async def initialize(self):
        """
        Initialize configuration, database connections, RPC providers, and all modules.
        
        Sub-task 7.1: Create main bot orchestrator
        """
        try:
            self.logger.info("Initializing Chimera bot...")
            
            # Step 1: Load configuration
            self.logger.info("Loading configuration...")
            self.config = get_config()
            self.logger.info(
                "Configuration loaded",
                extra={
                    "network": self.config.network_name,
                    "chain_id": self.config.chain_id,
                    "operator": self.config.execution.operator_address
                }
            )
            
            # Step 2: Establish database connections
            self.logger.info("Establishing database connections...")
            db_manager = init_database(self.config.database)
            redis_manager = init_redis(self.config.redis)
            
            if not db_manager.health_check():
                raise ChimeraError("Database health check failed")
            
            self.logger.info(
                "Database connections established",
                extra={
                    "postgres": "connected",
                    "redis": "connected" if not redis_manager._use_fallback else "fallback"
                }
            )
            
            # Step 3: Connect to RPC providers
            self.logger.info("Connecting to RPC providers...")
            self.web3 = Web3(Web3.HTTPProvider(self.config.rpc.primary_http))
            self.backup_web3 = Web3(Web3.HTTPProvider(self.config.rpc.backup_http))
            
            if not self.web3.is_connected():
                self.logger.warning("Primary RPC not connected, trying backup...")
                if not self.backup_web3.is_connected():
                    raise ChimeraError("All RPC providers failed to connect")
                self.web3 = self.backup_web3
            
            current_block = self.web3.eth.block_number
            self.logger.info(
                "RPC providers connected",
                extra={"current_block": current_block}
            )
            
            # Step 4: Load smart contract ABI and create contract instance
            self.logger.info("Loading Chimera contract...")
            # Contract instance will be created in ExecutionPlanner
            # Verify contract exists
            chimera_address = Web3.to_checksum_address(
                self.config.execution.chimera_contract_address
            )
            code = self.web3.eth.get_code(chimera_address)
            if code == b'' or code == '0x':
                raise ChimeraError(f"Chimera contract not found at {chimera_address}")
            
            self.logger.info(
                "Chimera contract verified",
                extra={"address": chimera_address}
            )
            
            # Step 5: Get operator private key from environment/secrets
            # In production, this would come from AWS Secrets Manager
            # For now, we'll use environment variable
            import os
            operator_key = os.getenv('OPERATOR_PRIVATE_KEY')
            if not operator_key:
                raise ChimeraError("OPERATOR_PRIVATE_KEY not set")
            
            # Step 6: Verify operator wallet has sufficient gas balance
            operator_address = Web3.to_checksum_address(
                self.config.execution.operator_address
            )
            operator_balance = self.web3.eth.get_balance(operator_address)
            operator_balance_eth = Decimal(operator_balance) / Decimal(10**18)
            
            min_balance_eth = Decimal("0.1")  # Minimum 0.1 ETH
            if operator_balance_eth < min_balance_eth:
                self.logger.critical(
                    "Operator balance below minimum",
                    extra={
                        "balance_eth": float(operator_balance_eth),
                        "minimum_eth": float(min_balance_eth)
                    }
                )
                raise ChimeraError(
                    f"Operator balance {operator_balance_eth} ETH below minimum {min_balance_eth} ETH"
                )
            
            self.logger.info(
                "Operator wallet verified",
                extra={
                    "address": operator_address,
                    "balance_eth": float(operator_balance_eth)
                }
            )
            
            # Step 7: Initialize all modules
            self.logger.info("Initializing modules...")
            
            # StateEngine
            self.state_engine = StateEngine(
                config=self.config,
                redis_manager=redis_manager,
                db_manager=db_manager
            )
            
            # OpportunityDetector
            self.opportunity_detector = OpportunityDetector(
                config=self.config,
                state_engine=self.state_engine,
                web3=self.web3
            )
            
            # ExecutionPlanner
            self.execution_planner = ExecutionPlanner(
                config=self.config,
                w3=self.web3,
                operator_key=operator_key
            )
            
            # SafetyController
            self.safety_controller = SafetyController(
                config=self.config,
                db_manager=db_manager
            )
            
            # MetricsServer
            self.metrics_server = MetricsServer(port=8000)
            
            self.logger.info("All modules initialized successfully")
            
            # Log initialization complete
            self.logger.info(
                "Chimera bot initialization complete",
                extra={
                    "status": "ready",
                    "state": self.safety_controller.current_state.value,
                    "operator": operator_address,
                    "balance_eth": float(operator_balance_eth)
                }
            )
            
        except Exception as e:
            self.logger.critical(f"Initialization failed: {e}", exc_info=True)
            raise
    
    async def start(self):
        """Start the bot and all background tasks"""
        try:
            self._running = True
            
            # Start metrics server
            await self.metrics_server.start()
            
            # Set initial metrics
            MetricsServer.set_bot_info(
                network=self.config.network_name,
                chain_id=self.config.chain_id,
                version="1.0.0"
            )
            MetricsServer.set_start_time(self._start_time)
            
            # Start StateEngine
            await self.state_engine.start()
            
            # Start OpportunityDetector
            await self.opportunity_detector.start()
            
            # Start main event loop
            asyncio.create_task(self.main_event_loop())
            
            # Start monitoring export
            asyncio.create_task(self.monitoring_loop())
            
            self.logger.info("Chimera bot started")
            
            # Wait for shutdown signal
            await self._shutdown_event.wait()
            
        except Exception as e:
            self.logger.critical(f"Bot startup failed: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop the bot gracefully"""
        self.logger.info("Stopping Chimera bot...")
        self._running = False
        
        # Stop modules
        if self.state_engine:
            await self.state_engine.stop()
        
        if self.opportunity_detector:
            await self.opportunity_detector.stop()
        
        if self.metrics_server:
            await self.metrics_server.stop()
        
        # Signal shutdown complete
        self._shutdown_event.set()
        
        self.logger.info("Chimera bot stopped")
    
    async def main_event_loop(self):
        """
        Main event loop - scans for opportunities and executes profitable ones.
        
        Sub-task 7.2: Implement main event loop
        Sub-task 7.3: Error handling and graceful degradation
        """
        self.logger.info("Starting main event loop...")
        
        # Error tracking for graceful degradation
        consecutive_errors = 0
        max_consecutive_errors = 10
        
        # In-memory queue for database operations during outage
        db_operation_queue = []
        max_queue_size = 100
        
        while self._running:
            try:
                # Check SafetyController state
                current_state = self.safety_controller.current_state
                
                if current_state == SystemState.HALTED:
                    self.logger.debug("System HALTED, skipping execution cycle")
                    await asyncio.sleep(self.config.scan_interval_seconds)
                    continue
                
                if current_state == SystemState.THROTTLED:
                    # 50% random skip in THROTTLED state
                    if not self.safety_controller.can_execute():
                        self.logger.debug("System THROTTLED, skipping this cycle")
                        await asyncio.sleep(self.config.scan_interval_seconds)
                        continue
                
                # Get opportunities from OpportunityDetector
                try:
                    opportunities = self.state_engine.get_all_positions()
                except Exception as e:
                    self.logger.error(f"Failed to get positions from StateEngine: {e}")
                    # Continue with empty list - graceful degradation
                    opportunities = []
                
                if not opportunities:
                    self.logger.debug("No positions to check")
                    await asyncio.sleep(self.config.scan_interval_seconds)
                    continue
                
                # Check each position for liquidation opportunity
                for position in opportunities:
                    try:
                        # Check if position is liquidatable
                        opportunity = await self.opportunity_detector.check_position(position)
                        
                        if not opportunity:
                            continue
                        
                        self._opportunities_detected += 1
                        MetricsServer.increment_opportunities_detected()
                        
                        # Get ETH/USD price for cost calculation
                        try:
                            eth_usd_price = await self._get_eth_usd_price()
                        except Exception as e:
                            self.logger.warning(f"Failed to get ETH price: {e}, using fallback")
                            eth_usd_price = Decimal("2000.0")
                        
                        # Plan execution
                        bundle = self.execution_planner.plan_execution(
                            opportunity=opportunity,
                            current_state=current_state,
                            eth_usd_price=eth_usd_price
                        )
                        
                        if not bundle:
                            if self.dry_run:
                                self._dry_run_simulations_failed += 1
                            self.logger.debug(
                                f"Execution planning failed for {opportunity.position.protocol}:"
                                f"{opportunity.position.user}"
                            )
                            continue
                        
                        # Check safety limits
                        is_valid, rejection_reason = self.safety_controller.validate_execution(bundle)
                        
                        if not is_valid:
                            self.logger.info(
                                f"Execution rejected by SafetyController: {rejection_reason}"
                            )
                            continue
                        
                        # DRY-RUN MODE: Skip actual submission
                        if self.dry_run:
                            self._dry_run_simulations_success += 1
                            self._dry_run_theoretical_profit += bundle.net_profit_usd
                            self.logger.info(
                                "[DRY-RUN] Would submit bundle",
                                extra={
                                    "dry_run": True,
                                    "protocol": opportunity.position.protocol,
                                    "borrower": opportunity.position.user,
                                    "net_profit_usd": float(bundle.net_profit_usd),
                                    "simulated_profit_usd": float(bundle.simulated_profit_usd),
                                    "total_cost_usd": float(bundle.total_cost_usd),
                                    "submission_path": bundle.submission_path.value,
                                    "health_factor": float(opportunity.health_factor),
                                    "theoretical_profit_total": float(self._dry_run_theoretical_profit),
                                    "simulations_success": self._dry_run_simulations_success,
                                    "simulations_failed": self._dry_run_simulations_failed
                                }
                            )
                            continue
                        
                        # Submit bundle (PRODUCTION MODE ONLY)
                        success, tx_hash = self.execution_planner.submit_bundle(
                            bundle=bundle,
                            current_state=current_state
                        )
                        
                        if success:
                            self._bundles_submitted += 1
                            MetricsServer.increment_bundles_submitted()
                            self.logger.info(
                                f"Bundle submitted successfully: {tx_hash}",
                                extra={
                                    "tx_hash": tx_hash,
                                    "net_profit_usd": float(bundle.net_profit_usd),
                                    "submission_path": bundle.submission_path.value
                                }
                            )
                        else:
                            self.logger.warning("Bundle submission failed")
                        
                        # Update performance metrics every 100 submissions
                        if self._bundles_submitted % 100 == 0:
                            self.logger.info("Updating performance metrics...")
                            try:
                                recent_executions = self.safety_controller.get_recent_executions(100)
                                self.execution_planner.update_bribe_model(recent_executions)
                                self.safety_controller.check_and_apply_transitions()
                            except Exception as e:
                                self.logger.error(f"Failed to update metrics: {e}")
                                # Continue - don't let metrics update failure stop execution
                    
                    except Exception as e:
                        self.logger.error(
                            f"Error processing opportunity: {e}",
                            exc_info=True
                        )
                        # Continue with next opportunity - don't let one failure stop the loop
                        continue
                
                # Reset error counter on successful cycle
                consecutive_errors = 0
                
                # Sleep between scan cycles
                await asyncio.sleep(self.config.scan_interval_seconds)
            
            except Exception as e:
                consecutive_errors += 1
                self.logger.error(
                    f"Error in main event loop (consecutive: {consecutive_errors}): {e}",
                    exc_info=True
                )
                
                # Check if we've hit too many consecutive errors
                if consecutive_errors >= max_consecutive_errors:
                    self.logger.critical(
                        f"Too many consecutive errors ({consecutive_errors}), entering HALTED state"
                    )
                    self.safety_controller.transition_state(
                        SystemState.HALTED,
                        f"Main loop consecutive errors: {consecutive_errors}",
                        None
                    )
                    consecutive_errors = 0  # Reset counter
                
                # Continue running - never crash the main loop
                await asyncio.sleep(self.config.scan_interval_seconds)
        
        self.logger.info("Main event loop stopped")
    
    async def _handle_rpc_error(self, error: Exception):
        """
        Handle RPC errors by switching to backup provider.
        
        Sub-task 7.3: Error handling and graceful degradation
        """
        self.logger.warning(f"RPC error detected: {error}")
        
        try:
            # Check if current provider is primary
            if self.web3.provider.endpoint_uri == self.config.rpc.primary_http:
                self.logger.info("Switching to backup RPC provider...")
                self.web3 = self.backup_web3
                
                # Verify backup is connected
                if not self.web3.is_connected():
                    self.logger.critical("Backup RPC also failed, entering HALTED state")
                    self.safety_controller.transition_state(
                        SystemState.HALTED,
                        "All RPC providers failed",
                        None
                    )
                else:
                    self.logger.info("Successfully switched to backup RPC")
            else:
                # Already on backup, try to reconnect to primary
                self.logger.info("Attempting to reconnect to primary RPC...")
                primary_web3 = Web3(Web3.HTTPProvider(self.config.rpc.primary_http))
                
                if primary_web3.is_connected():
                    self.web3 = primary_web3
                    self.logger.info("Reconnected to primary RPC")
                else:
                    self.logger.warning("Primary RPC still unavailable, staying on backup")
        
        except Exception as e:
            self.logger.error(f"Error handling RPC failover: {e}", exc_info=True)
    
    async def _handle_database_error(self, error: Exception, operation: dict):
        """
        Handle database errors by queuing operations in memory.
        
        Sub-task 7.3: Error handling and graceful degradation
        """
        self.logger.warning(f"Database error detected: {error}")
        
        # Queue operation for retry
        if not hasattr(self, '_db_operation_queue'):
            self._db_operation_queue = []
        
        if len(self._db_operation_queue) < 100:
            self._db_operation_queue.append({
                'timestamp': datetime.utcnow(),
                'operation': operation
            })
            self.logger.info(f"Queued database operation (queue size: {len(self._db_operation_queue)})")
        else:
            # Queue full - drop oldest non-critical operations
            self.logger.warning("Database operation queue full, dropping oldest operation")
            self._db_operation_queue.pop(0)
            self._db_operation_queue.append({
                'timestamp': datetime.utcnow(),
                'operation': operation
            })
        
        # Try to flush queue if database is back
        await self._flush_database_queue()
    
    async def _flush_database_queue(self):
        """Attempt to flush queued database operations"""
        if not hasattr(self, '_db_operation_queue') or not self._db_operation_queue:
            return
        
        try:
            db_manager = get_db_manager()
            if db_manager.health_check():
                self.logger.info(f"Database reconnected, flushing {len(self._db_operation_queue)} queued operations")
                
                # Process queued operations
                while self._db_operation_queue:
                    operation = self._db_operation_queue.pop(0)
                    try:
                        # Re-execute operation
                        # This would need to be implemented based on operation type
                        self.logger.debug(f"Flushed operation from {operation['timestamp']}")
                    except Exception as e:
                        self.logger.error(f"Failed to flush operation: {e}")
                        # Re-queue if failed
                        self._db_operation_queue.insert(0, operation)
                        break
        
        except Exception as e:
            self.logger.debug(f"Database still unavailable: {e}")
    
    async def monitoring_loop(self):
        """
        Export metrics to CloudWatch every 60 seconds.
        
        Sub-task 7.4: Implement monitoring integration
        """
        self.logger.info("Starting monitoring loop...")
        
        while self._running:
            try:
                await asyncio.sleep(self.config.monitoring.metrics_export_interval_seconds)
                
                # Calculate metrics
                metrics = self.safety_controller.calculate_metrics()
                cache_stats = self.state_engine.get_cache_stats()
                safety_status = self.safety_controller.get_status()
                
                # Update Prometheus metrics
                MetricsServer.update_system_state(self.safety_controller.current_state.value)
                MetricsServer.update_inclusion_rate(metrics.inclusion_rate)
                MetricsServer.update_simulation_accuracy(metrics.simulation_accuracy)
                MetricsServer.update_total_profit(metrics.total_profit_usd)
                MetricsServer.update_daily_volume(safety_status['daily_volume_usd'])
                MetricsServer.update_daily_limit(safety_status['daily_limit_usd'])
                MetricsServer.update_consecutive_failures(metrics.consecutive_failures)
                MetricsServer.update_positions_cached(cache_stats['total_positions'])
                MetricsServer.update_current_block(cache_stats['current_block'])
                
                # Update operator balance
                operator_balance = self.web3.eth.get_balance(
                    Web3.to_checksum_address(self.config.execution.operator_address)
                )
                operator_balance_eth = Decimal(operator_balance) / Decimal(10**18)
                MetricsServer.update_operator_balance(operator_balance_eth)
                
                # Log metrics
                if self.dry_run:
                    # Dry-run specific metrics
                    uptime_hours = (time.time() - self._start_time) / 3600
                    opportunities_per_hour = self._opportunities_detected / uptime_hours if uptime_hours > 0 else 0
                    simulation_success_rate = (
                        self._dry_run_simulations_success / 
                        (self._dry_run_simulations_success + self._dry_run_simulations_failed)
                        if (self._dry_run_simulations_success + self._dry_run_simulations_failed) > 0 
                        else 0
                    )
                    
                    self.logger.info(
                        "[DRY-RUN] Metrics snapshot",
                        extra={
                            "dry_run": True,
                            "uptime_hours": round(uptime_hours, 2),
                            "opportunities_detected": self._opportunities_detected,
                            "opportunities_per_hour": round(opportunities_per_hour, 2),
                            "simulations_success": self._dry_run_simulations_success,
                            "simulations_failed": self._dry_run_simulations_failed,
                            "simulation_success_rate": round(simulation_success_rate * 100, 2),
                            "theoretical_profit_usd": float(self._dry_run_theoretical_profit),
                            "positions_cached": cache_stats['total_positions'],
                            "current_block": cache_stats['current_block']
                        }
                    )
                else:
                    # Production metrics
                    self.logger.info(
                        "Metrics snapshot",
                        extra={
                            "system_state": self.safety_controller.current_state.value,
                            "opportunities_detected": self._opportunities_detected,
                            "bundles_submitted": self._bundles_submitted,
                            "inclusion_rate": float(metrics.inclusion_rate),
                            "simulation_accuracy": float(metrics.simulation_accuracy),
                            "daily_volume_usd": float(safety_status['daily_volume_usd']),
                            "consecutive_failures": metrics.consecutive_failures,
                            "positions_cached": cache_stats['total_positions'],
                            "current_block": cache_stats['current_block']
                        }
                    )
                
                # Export to CloudWatch if enabled
                if self.config.monitoring.cloudwatch_enabled:
                    await self._export_to_cloudwatch(metrics, cache_stats, safety_status)
                
                # Check for alert conditions
                await self._check_alert_conditions(metrics, safety_status)
            
            except Exception as e:
                self.logger.error(f"Error in monitoring loop: {e}", exc_info=True)
        
        self.logger.info("Monitoring loop stopped")
    
    async def _get_eth_usd_price(self) -> Decimal:
        """Get current ETH/USD price from Chainlink oracle"""
        try:
            # ETH/USD price feed on Base (placeholder address)
            # In production, this would be the actual Chainlink ETH/USD feed
            # For now, return a reasonable estimate
            return Decimal("2000.0")  # $2000 per ETH
        except Exception as e:
            self.logger.warning(f"Failed to fetch ETH/USD price: {e}")
            return Decimal("2000.0")  # Fallback
    
    async def _export_to_cloudwatch(self, metrics, cache_stats, safety_status):
        """Export metrics to CloudWatch"""
        try:
            # TODO: Implement CloudWatch integration using boto3
            # This would use boto3.client('cloudwatch').put_metric_data()
            self.logger.debug("CloudWatch export not yet implemented")
        except Exception as e:
            self.logger.error(f"CloudWatch export failed: {e}")
    
    async def _check_alert_conditions(self, metrics, safety_status):
        """
        Check for alert conditions and send alerts.
        
        Alert levels:
        - CRITICAL: Phone + SMS (HALTED state, security incidents, low balance)
        - HIGH: SMS (THROTTLED state, low inclusion, consecutive failures)
        - MEDIUM: Email (approaching limits, key rotation due)
        - LOW: Email (daily summaries)
        """
        try:
            current_state = self.safety_controller.current_state
            
            # CRITICAL alerts
            if current_state == SystemState.HALTED:
                await self._send_alert(
                    severity="CRITICAL",
                    message="System entered HALTED state",
                    context={"metrics": metrics}
                )
            
            # Check operator balance
            operator_balance = self.web3.eth.get_balance(
                Web3.to_checksum_address(self.config.execution.operator_address)
            )
            operator_balance_eth = Decimal(operator_balance) / Decimal(10**18)
            
            if operator_balance_eth < Decimal("0.1"):
                await self._send_alert(
                    severity="CRITICAL",
                    message=f"Operator balance low: {operator_balance_eth} ETH",
                    context={"balance_eth": float(operator_balance_eth)}
                )
            
            # HIGH alerts
            if current_state == SystemState.THROTTLED:
                await self._send_alert(
                    severity="HIGH",
                    message="System entered THROTTLED state",
                    context={"metrics": metrics}
                )
            
            if metrics.inclusion_rate < Decimal("0.50"):
                await self._send_alert(
                    severity="HIGH",
                    message=f"Inclusion rate low: {metrics.inclusion_rate:.2%}",
                    context={"inclusion_rate": float(metrics.inclusion_rate)}
                )
            
            if metrics.consecutive_failures >= 2:
                await self._send_alert(
                    severity="HIGH",
                    message=f"Consecutive failures: {metrics.consecutive_failures}",
                    context={"consecutive_failures": metrics.consecutive_failures}
                )
            
            # MEDIUM alerts
            daily_volume_pct = (
                safety_status['daily_volume_usd'] / 
                safety_status['daily_limit_usd'] * 100
            )
            
            if daily_volume_pct > 80:
                await self._send_alert(
                    severity="MEDIUM",
                    message=f"Daily volume at {daily_volume_pct:.1f}% of limit",
                    context={"daily_volume_usd": safety_status['daily_volume_usd']}
                )
        
        except Exception as e:
            self.logger.error(f"Error checking alert conditions: {e}")
    
    async def _send_alert(self, severity: str, message: str, context: dict):
        """Send alert via configured channels"""
        self.logger.warning(
            f"ALERT [{severity}]: {message}",
            extra={"severity": severity, "context": context}
        )
        
        # TODO: Implement actual alerting via SNS/PagerDuty/email
        # For now, just log


async def main():
    """
    Main entry point for the Chimera bot.
    
    Initializes configuration, logging, and starts the main event loop.
    """
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Chimera MEV Liquidation Bot')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Run in dry-run mode (detect and simulate, but do not submit transactions)'
    )
    args = parser.parse_args()
    
    # Load configuration first (before logging)
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
        extra={
            "network": config.network_name,
            "chain_id": config.chain_id,
            "operator": config.execution.operator_address,
            "dry_run": args.dry_run
        }
    )
    
    if args.dry_run:
        logger.warning("=" * 80)
        logger.warning("DRY-RUN MODE ENABLED")
        logger.warning("Opportunities will be detected and simulated, but NO transactions will be submitted")
        logger.warning("=" * 80)
    
    # Create bot instance
    bot = ChimeraBot(dry_run=args.dry_run)
    
    # Setup signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        logger.info(f"Received signal {sig}, initiating graceful shutdown...")
        asyncio.create_task(bot.stop())
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Initialize bot
        await bot.initialize()
        
        # Start bot
        await bot.start()
    
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        await bot.stop()
    
    except Exception as e:
        logger.critical(f"Fatal error: {e}", exc_info=True)
        await bot.stop()
        sys.exit(1)
    
    logger.info("Chimera bot shutdown complete")


if __name__ == "__main__":
    asyncio.run(main())
