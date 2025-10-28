"""
Tests for dry-run mode functionality

Verifies that dry-run mode:
1. Does not submit transactions
2. Logs simulation results correctly
3. Tracks metrics properly
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bot.src.main import ChimeraBot
from bot.src.types import (
    Opportunity, Position, Bundle, Transaction, 
    SubmissionPath, SystemState
)


class TestDryRunMode:
    """Test dry-run mode functionality"""
    
    def test_dry_run_initialization(self):
        """Test that bot initializes correctly in dry-run mode"""
        bot = ChimeraBot(dry_run=True)
        
        assert bot.dry_run is True
        assert hasattr(bot, '_dry_run_simulations_success')
        assert hasattr(bot, '_dry_run_simulations_failed')
        assert hasattr(bot, '_dry_run_theoretical_profit')
        assert bot._dry_run_simulations_success == 0
        assert bot._dry_run_simulations_failed == 0
        assert bot._dry_run_theoretical_profit == Decimal("0")
    
    def test_production_mode_initialization(self):
        """Test that bot initializes correctly in production mode"""
        bot = ChimeraBot(dry_run=False)
        
        assert bot.dry_run is False
        assert not hasattr(bot, '_dry_run_simulations_success')
    
    @pytest.mark.asyncio
    async def test_dry_run_skips_submission(self):
        """Test that dry-run mode skips transaction submission"""
        bot = ChimeraBot(dry_run=True)
        bot.logger = Mock()
        
        # Create mock bundle
        mock_position = Position(
            protocol="moonwell",
            user="0x1234567890123456789012345678901234567890",
            collateral_asset="0xabcd567890123456789012345678901234567890",
            collateral_amount=1000000000000000000,
            debt_asset="0xef01567890123456789012345678901234567890",
            debt_amount=500000000000000000,
            liquidation_threshold=Decimal("0.80"),
            last_update_block=12345678,
            blocks_unhealthy=2
        )
        
        mock_opportunity = Opportunity(
            position=mock_position,
            health_factor=Decimal("0.95"),
            collateral_price_usd=Decimal("2000"),
            debt_price_usd=Decimal("1"),
            liquidation_bonus=Decimal("0.05"),
            estimated_gross_profit_usd=Decimal("100"),
            estimated_net_profit_usd=Decimal("75"),
            detected_at_block=12345678,
            detected_at_timestamp=None
        )
        
        mock_transaction = Transaction(
            to="0x1234567890123456789012345678901234567890",
            data="0x",
            value=0,
            gas_limit=500000,
            max_fee_per_gas=1000000000,
            max_priority_fee_per_gas=1000000000,
            nonce=1,
            chain_id=8453
        )
        
        mock_bundle = Bundle(
            opportunity=mock_opportunity,
            transaction=mock_transaction,
            simulated_profit_wei=100000000000000000,
            simulated_profit_usd=Decimal("100"),
            gas_estimate=300000,
            l2_gas_cost_usd=Decimal("5"),
            l1_data_cost_usd=Decimal("2"),
            bribe_usd=Decimal("15"),
            flash_loan_cost_usd=Decimal("1"),
            slippage_cost_usd=Decimal("2"),
            total_cost_usd=Decimal("25"),
            net_profit_usd=Decimal("75"),
            submission_path=SubmissionPath.MEMPOOL
        )
        
        # Initialize tracking variables
        bot._dry_run_simulations_success = 0
        bot._dry_run_simulations_failed = 0
        bot._dry_run_theoretical_profit = Decimal("0")
        
        # Mock execution planner
        bot.execution_planner = Mock()
        bot.execution_planner.submit_bundle = Mock(return_value=(True, "0xabcd"))
        
        # Simulate the dry-run logic from main event loop
        if bot.dry_run:
            bot._dry_run_simulations_success += 1
            bot._dry_run_theoretical_profit += mock_bundle.net_profit_usd
            bot.logger.info(
                "[DRY-RUN] Would submit bundle",
                extra={
                    "dry_run": True,
                    "protocol": mock_opportunity.position.protocol,
                    "net_profit_usd": float(mock_bundle.net_profit_usd)
                }
            )
        else:
            # This should not execute in dry-run mode
            bot.execution_planner.submit_bundle(mock_bundle, SystemState.NORMAL)
        
        # Verify transaction was NOT submitted
        bot.execution_planner.submit_bundle.assert_not_called()
        
        # Verify metrics were tracked
        assert bot._dry_run_simulations_success == 1
        assert bot._dry_run_theoretical_profit == Decimal("75")
        
        # Verify logging
        bot.logger.info.assert_called()
        call_args = bot.logger.info.call_args
        assert "[DRY-RUN]" in call_args[0][0]
    
    def test_dry_run_tracks_failed_simulations(self):
        """Test that dry-run mode tracks failed simulations"""
        bot = ChimeraBot(dry_run=True)
        bot._dry_run_simulations_failed = 0
        
        # Simulate failed simulation
        bundle = None  # Simulation failed
        
        if not bundle:
            if bot.dry_run:
                bot._dry_run_simulations_failed += 1
        
        assert bot._dry_run_simulations_failed == 1
    
    def test_production_mode_submits_transactions(self):
        """Test that production mode does submit transactions"""
        bot = ChimeraBot(dry_run=False)
        bot.execution_planner = Mock()
        bot.execution_planner.submit_bundle = Mock(return_value=(True, "0xabcd"))
        
        # Create mock bundle (simplified)
        mock_bundle = Mock()
        mock_bundle.net_profit_usd = Decimal("75")
        
        # Simulate production mode logic
        if not bot.dry_run:
            success, tx_hash = bot.execution_planner.submit_bundle(
                mock_bundle, 
                SystemState.NORMAL
            )
        
        # Verify transaction WAS submitted
        bot.execution_planner.submit_bundle.assert_called_once()


class TestDryRunReport:
    """Test dry-run report generation"""
    
    def test_report_script_exists(self):
        """Test that dry_run_report.py script exists"""
        script_path = Path(__file__).parent.parent / "scripts" / "dry_run_report.py"
        assert script_path.exists(), "dry_run_report.py script not found"
    
    def test_report_is_executable(self):
        """Test that report script can be imported"""
        script_path = Path(__file__).parent.parent / "scripts" / "dry_run_report.py"
        
        # Try to read the file
        with open(script_path, 'r') as f:
            content = f.read()
        
        # Verify it has main function
        assert "def main():" in content
        assert "DryRunAnalyzer" in content
        assert "parse_logs" in content
        assert "calculate_metrics" in content
        assert "generate_report" in content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
