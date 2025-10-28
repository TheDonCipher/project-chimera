"""
Prometheus Metrics Server

Exposes bot metrics via HTTP endpoint for Prometheus scraping.
"""

import asyncio
from typing import Optional
from aiohttp import web
from prometheus_client import (
    Counter, Gauge, Histogram, Info,
    generate_latest, CONTENT_TYPE_LATEST
)
from decimal import Decimal

from .logging_config import get_logger


# Define Prometheus metrics
# System state (0=NORMAL, 1=THROTTLED, 2=HALTED)
system_state_gauge = Gauge(
    'chimera_system_state',
    'Current system state (0=NORMAL, 1=THROTTLED, 2=HALTED)'
)

# Opportunities and submissions
opportunities_detected_counter = Counter(
    'chimera_opportunities_detected_total',
    'Total number of liquidation opportunities detected'
)

bundles_submitted_counter = Counter(
    'chimera_bundles_submitted_total',
    'Total number of transaction bundles submitted'
)

# Performance metrics
inclusion_rate_gauge = Gauge(
    'chimera_inclusion_rate',
    'Transaction inclusion rate (0.0 to 1.0)'
)

simulation_accuracy_gauge = Gauge(
    'chimera_simulation_accuracy',
    'Simulation accuracy rate (0.0 to 1.0)'
)

# Profitability
total_profit_gauge = Gauge(
    'chimera_total_profit_usd',
    'Total profit in USD'
)

daily_volume_gauge = Gauge(
    'chimera_daily_volume_usd',
    'Daily execution volume in USD'
)

daily_limit_gauge = Gauge(
    'chimera_daily_limit_usd',
    'Daily execution limit in USD'
)

# Safety metrics
consecutive_failures_gauge = Gauge(
    'chimera_consecutive_failures',
    'Number of consecutive execution failures'
)

# Wallet balance
operator_balance_gauge = Gauge(
    'chimera_operator_balance_eth',
    'Operator wallet balance in ETH'
)

# State engine metrics
positions_cached_gauge = Gauge(
    'chimera_positions_cached',
    'Number of positions currently cached'
)

current_block_gauge = Gauge(
    'chimera_current_block',
    'Current blockchain block number'
)

state_divergence_counter = Counter(
    'chimera_state_divergence_events_total',
    'Total number of state divergence events detected'
)

# Bot info
bot_info = Info(
    'chimera_bot',
    'Information about the Chimera bot'
)

# Start time
start_time_gauge = Gauge(
    'chimera_start_time_seconds',
    'Unix timestamp when the bot started'
)


class MetricsServer:
    """
    HTTP server that exposes Prometheus metrics.
    
    Runs on port 8000 and serves metrics at /metrics endpoint.
    """
    
    def __init__(self, port: int = 8000):
        self.port = port
        self.logger = get_logger("metrics_server")
        self.app: Optional[web.Application] = None
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        self._running = False
    
    async def start(self):
        """Start the metrics HTTP server"""
        try:
            self.logger.info(f"Starting metrics server on port {self.port}...")
            
            # Create aiohttp application
            self.app = web.Application()
            self.app.router.add_get('/metrics', self.handle_metrics)
            self.app.router.add_get('/health', self.handle_health)
            
            # Start server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, '0.0.0.0', self.port)
            await self.site.start()
            
            self._running = True
            self.logger.info(f"Metrics server started on http://0.0.0.0:{self.port}/metrics")
        
        except Exception as e:
            self.logger.error(f"Failed to start metrics server: {e}", exc_info=True)
            raise
    
    async def stop(self):
        """Stop the metrics HTTP server"""
        try:
            self.logger.info("Stopping metrics server...")
            self._running = False
            
            if self.site:
                await self.site.stop()
            
            if self.runner:
                await self.runner.cleanup()
            
            self.logger.info("Metrics server stopped")
        
        except Exception as e:
            self.logger.error(f"Error stopping metrics server: {e}", exc_info=True)
    
    async def handle_metrics(self, request: web.Request) -> web.Response:
        """Handle /metrics endpoint - return Prometheus metrics"""
        try:
            # Generate Prometheus metrics in text format
            metrics_output = generate_latest()
            
            return web.Response(
                body=metrics_output,
                content_type=CONTENT_TYPE_LATEST
            )
        
        except Exception as e:
            self.logger.error(f"Error generating metrics: {e}", exc_info=True)
            return web.Response(
                text=f"Error generating metrics: {e}",
                status=500
            )
    
    async def handle_health(self, request: web.Request) -> web.Response:
        """Handle /health endpoint - simple health check"""
        return web.Response(
            text="OK",
            status=200
        )
    
    @staticmethod
    def update_system_state(state_value: int):
        """Update system state metric (0=NORMAL, 1=THROTTLED, 2=HALTED)"""
        system_state_gauge.set(state_value)
    
    @staticmethod
    def increment_opportunities_detected():
        """Increment opportunities detected counter"""
        opportunities_detected_counter.inc()
    
    @staticmethod
    def increment_bundles_submitted():
        """Increment bundles submitted counter"""
        bundles_submitted_counter.inc()
    
    @staticmethod
    def update_inclusion_rate(rate: Decimal):
        """Update inclusion rate gauge"""
        inclusion_rate_gauge.set(float(rate))
    
    @staticmethod
    def update_simulation_accuracy(accuracy: Decimal):
        """Update simulation accuracy gauge"""
        simulation_accuracy_gauge.set(float(accuracy))
    
    @staticmethod
    def update_total_profit(profit_usd: Decimal):
        """Update total profit gauge"""
        total_profit_gauge.set(float(profit_usd))
    
    @staticmethod
    def update_daily_volume(volume_usd: Decimal):
        """Update daily volume gauge"""
        daily_volume_gauge.set(float(volume_usd))
    
    @staticmethod
    def update_daily_limit(limit_usd: Decimal):
        """Update daily limit gauge"""
        daily_limit_gauge.set(float(limit_usd))
    
    @staticmethod
    def update_consecutive_failures(count: int):
        """Update consecutive failures gauge"""
        consecutive_failures_gauge.set(count)
    
    @staticmethod
    def update_operator_balance(balance_eth: Decimal):
        """Update operator balance gauge"""
        operator_balance_gauge.set(float(balance_eth))
    
    @staticmethod
    def update_positions_cached(count: int):
        """Update positions cached gauge"""
        positions_cached_gauge.set(count)
    
    @staticmethod
    def update_current_block(block_number: int):
        """Update current block gauge"""
        current_block_gauge.set(block_number)
    
    @staticmethod
    def increment_state_divergence():
        """Increment state divergence counter"""
        state_divergence_counter.inc()
    
    @staticmethod
    def set_bot_info(network: str, chain_id: int, version: str):
        """Set bot information"""
        bot_info.info({
            'network': network,
            'chain_id': str(chain_id),
            'version': version
        })
    
    @staticmethod
    def set_start_time(timestamp: float):
        """Set bot start time"""
        start_time_gauge.set(timestamp)
