"""
Unit tests for OpportunityDetector module (Task 4.6)

Tests:
- Health factor calculation with various collateral/debt ratios
- Multi-oracle sanity checks with divergent prices
- Price movement detection (30% threshold)
- Confirmation blocks logic (2-block minimum)
- Profit estimation accuracy
"""

import sys
import asyncio
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.types import Position, Opportunity
from src.config import ChimeraConfig, ProtocolConfig, OracleConfig, SafetyLimits, ExecutionConfig, DEXConfig
from src.state_engine import StateEngine
from src.opportunity_detector import OpportunityDetector
from web3 import Web3


# ============================================================================
# Test Fixtures
# ============================================================================

def create_mock_config():
    """Create mock configuration for testing"""
    config = Mock(spec=ChimeraConfig)
    config.protocols = {
        'moonwell': ProtocolConfig(
            name='moonwell',
            address='0x1234567890123456789012345678901234567890',
            liquidation_threshold=Decimal('0.80'),
            liquidation_bonus=Decimal('0.05')
        )
    }
    config.oracles = OracleConfig(
        chainlink_addresses={
            '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01': '0xOracle1000000000000000000000000000000',
            '0x9876543210987654321098765432109876543210': '0xOracle2000000000000000000000000000000'
        },
        pyth_addresses={},
        max_divergence_percent=Decimal('5.0'),
        max_price_movement_percent=Decimal('30.0')
    )
    config.safety = SafetyLimits(
        min_profit_usd=Decimal('50')
    )
    config.execution = ExecutionConfig(
        operator_address='0xOperator',
        chimera_contract_address='0xChimera',
        aave_v3_pool='0xAave',
        flash_loan_premium_percent=Decimal('0.09')
    )
    config.dex = DEXConfig(
        uniswap_v3_router='0xUniswap',
        uniswap_v3_quoter='0xQuoter',
        max_slippage_percent=Decimal('1.0')
    )
    config.scan_interval_seconds = 5
    config.confirmation_blocks = 2
    return config


def create_mock_position(
    collateral_amount=1000 * 10**18,
    debt_amount=800 * 10**18,
    liquidation_threshold=Decimal('0.80'),
    blocks_unhealthy=0
):
    """Create mock position for testing"""
    return Position(
        protocol='moonwell',
        user='0x1234567890123456789012345678901234567890',
        collateral_asset='0xAbCdEf0123456789AbCdEf0123456789AbCdEf01',
        collateral_amount=collateral_amount,
        debt_asset='0x9876543210987654321098765432109876543210',
        debt_amount=debt_amount,
        liquidation_threshold=liquidation_threshold,
        last_update_block=1000,
        blocks_unhealthy=blocks_unhealthy
    )


# ============================================================================
# Test 1: Health Factor Calculation
# ============================================================================

async def test_health_factor_calculation():
    """Test health factor calculation with various collateral/debt ratios"""
    print("\n" + "=" * 80)
    print("Test 1: Health Factor Calculation")
    print("=" * 80)
    
    config = create_mock_config()
    mock_state_engine = Mock(spec=StateEngine)
    mock_state_engine.current_block = 1000
    mock_web3 = Mock(spec=Web3)
    
    detector = OpportunityDetector(config, mock_state_engine, mock_web3)
    
    # Mock get_chainlink_price to return fixed prices
    async def mock_get_price(asset):
        if asset == '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01':
            return Decimal('2000')  # $2000 per token
        elif asset == '0x9876543210987654321098765432109876543210':
            return Decimal('1')  # $1 per token
        return None
    
    detector.get_chainlink_price = mock_get_price
    
    # Test 1.1: Healthy position (health_factor > 1.0)
    print("\n1.1: Testing healthy position...")
    position = create_mock_position(
        collateral_amount=1000 * 10**18,  # 1000 tokens
        debt_amount=800 * 10**18  # 800 tokens
    )
    # health_factor = (1000 * 2000 * 0.80) / (800 * 1) = 1,600,000 / 800 = 2000
    
    health_factor, collateral_price, debt_price = await detector.calculate_health_factor(position)
    
    assert health_factor is not None, "Health factor should not be None"
    assert health_factor > Decimal('1.0'), f"Expected health_factor > 1.0, got {health_factor}"
    assert collateral_price == Decimal('2000'), f"Expected collateral price 2000, got {collateral_price}"
    assert debt_price == Decimal('1'), f"Expected debt price 1, got {debt_price}"
    print(f"✓ Healthy position: health_factor={health_factor:.4f}")
    
    # Test 1.2: Unhealthy position (health_factor < 1.0)
    print("\n1.2: Testing unhealthy position...")
    position = create_mock_position(
        collateral_amount=100 * 10**18,  # 100 tokens
        debt_amount=200000 * 10**18  # 200,000 tokens
    )
    # health_factor = (100 * 2000 * 0.80) / (200000 * 1) = 160,000 / 200,000 = 0.8
    
    health_factor, collateral_price, debt_price = await detector.calculate_health_factor(position)
    
    assert health_factor is not None, "Health factor should not be None"
    assert health_factor < Decimal('1.0'), f"Expected health_factor < 1.0, got {health_factor}"
    print(f"✓ Unhealthy position: health_factor={health_factor:.4f}")
    
    # Test 1.3: Zero debt (edge case)
    print("\n1.3: Testing zero debt edge case...")
    position = create_mock_position(
        collateral_amount=1000 * 10**18,
        debt_amount=1  # Near zero
    )
    
    health_factor, collateral_price, debt_price = await detector.calculate_health_factor(position)
    
    assert health_factor is not None, "Health factor should not be None"
    assert health_factor > Decimal('1.0'), "Zero debt should result in very high health factor"
    print(f"✓ Zero debt: health_factor={health_factor:.4f}")
    
    print("\n✓ All health factor calculation tests passed!")


# ============================================================================
# Test 2: Multi-Oracle Sanity Checks
# ============================================================================

async def test_multi_oracle_sanity_checks():
    """Test multi-oracle sanity checks with divergent prices"""
    print("\n" + "=" * 80)
    print("Test 2: Multi-Oracle Sanity Checks")
    print("=" * 80)
    
    config = create_mock_config()
    mock_state_engine = Mock(spec=StateEngine)
    mock_web3 = Mock(spec=Web3)
    
    detector = OpportunityDetector(config, mock_state_engine, mock_web3)
    
    # Test 2.1: Prices within acceptable divergence
    print("\n2.1: Testing prices within acceptable divergence...")
    
    # Mock Pyth to return similar price (within 5%)
    async def mock_pyth_price_similar(asset):
        if asset == '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01':
            return Decimal('2040')  # 2% divergence from 2000
        return None
    
    detector.get_pyth_price = mock_pyth_price_similar
    
    result = await detector.verify_oracle_sanity(
        '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01', Decimal('2000'),
        '0x9876543210987654321098765432109876543210', Decimal('1')
    )
    
    assert result == True, "Prices within 5% divergence should pass"
    print("✓ Prices within acceptable divergence passed")
    
    # Test 2.2: Prices with excessive divergence
    print("\n2.2: Testing prices with excessive divergence...")
    
    # Mock Pyth to return divergent price (>5%)
    async def mock_pyth_price_divergent(asset):
        if asset == '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01':
            return Decimal('2200')  # 10% divergence from 2000
        return None
    
    detector.get_pyth_price = mock_pyth_price_divergent
    config.oracles.pyth_addresses = {'0xAbCdEf0123456789AbCdEf0123456789AbCdEf01': '0xPythOracle000000000000000000000000000'}
    
    result = await detector.verify_oracle_sanity(
        '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01', Decimal('2000'),
        '0x9876543210987654321098765432109876543210', Decimal('1')
    )
    
    assert result == False, "Prices with >5% divergence should fail"
    print("✓ Excessive divergence correctly rejected")
    
    print("\n✓ All multi-oracle sanity check tests passed!")


# ============================================================================
# Test 3: Price Movement Detection
# ============================================================================

async def test_price_movement_detection():
    """Test price movement detection (30% threshold)"""
    print("\n" + "=" * 80)
    print("Test 3: Price Movement Detection")
    print("=" * 80)
    
    config = create_mock_config()
    mock_state_engine = Mock(spec=StateEngine)
    mock_web3 = Mock(spec=Web3)
    
    detector = OpportunityDetector(config, mock_state_engine, mock_web3)
    detector.get_pyth_price = AsyncMock(return_value=None)  # No secondary oracle
    
    # Test 3.1: Normal price movement (<30%)
    print("\n3.1: Testing normal price movement...")
    
    # Set previous price
    detector.previous_prices['0xAbCdEf0123456789AbCdEf0123456789AbCdEf01'] = Decimal('2000')
    
    # Current price with 10% movement
    result = await detector.verify_oracle_sanity(
        '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01', Decimal('2200'),  # 10% increase
        '0x9876543210987654321098765432109876543210', Decimal('1')
    )
    
    assert result == True, "10% price movement should pass"
    print("✓ Normal price movement passed")
    
    # Test 3.2: Excessive price movement (>30%)
    print("\n3.2: Testing excessive price movement...")
    
    # Set previous price
    detector.previous_prices['0xAbCdEf0123456789AbCdEf0123456789AbCdEf01'] = Decimal('2000')
    
    # Current price with 40% movement
    result = await detector.verify_oracle_sanity(
        '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01', Decimal('2800'),  # 40% increase
        '0x9876543210987654321098765432109876543210', Decimal('1')
    )
    
    assert result == False, "40% price movement should fail"
    print("✓ Excessive price movement correctly rejected")
    
    print("\n✓ All price movement detection tests passed!")


# ============================================================================
# Test 4: Confirmation Blocks Logic
# ============================================================================

async def test_confirmation_blocks_logic():
    """Test confirmation blocks logic (2-block minimum)"""
    print("\n" + "=" * 80)
    print("Test 4: Confirmation Blocks Logic")
    print("=" * 80)
    
    config = create_mock_config()
    mock_state_engine = Mock(spec=StateEngine)
    mock_state_engine.current_block = 1000
    mock_state_engine.update_position_health = Mock(return_value=True)
    mock_web3 = Mock(spec=Web3)
    
    detector = OpportunityDetector(config, mock_state_engine, mock_web3)
    
    # Mock oracle prices
    async def mock_get_price(asset):
        return Decimal('2000') if asset == '0xAbCdEf0123456789AbCdEf0123456789AbCdEf01' else Decimal('1')
    detector.get_chainlink_price = mock_get_price
    detector.verify_oracle_sanity = AsyncMock(return_value=True)
    detector.check_protocol_state = AsyncMock(return_value=True)
    detector.estimate_profit = AsyncMock(return_value=(Decimal('100'), Decimal('60')))
    
    # Test 4.1: Position unhealthy for only 1 block (should be rejected)
    print("\n4.1: Testing position unhealthy for 1 block...")
    
    position = create_mock_position(
        collateral_amount=100 * 10**18,
        debt_amount=200000 * 10**18,
        blocks_unhealthy=1
    )
    
    # Mock get_position to return position with blocks_unhealthy=1
    mock_state_engine.get_position = Mock(return_value=position)
    
    opportunity = await detector.check_position(position)
    
    assert opportunity is None, "Position unhealthy for only 1 block should be rejected"
    print("✓ Position with 1 unhealthy block correctly rejected")
    
    # Test 4.2: Position unhealthy for 2 blocks (should pass)
    print("\n4.2: Testing position unhealthy for 2 blocks...")
    
    position = create_mock_position(
        collateral_amount=100 * 10**18,
        debt_amount=200000 * 10**18,
        blocks_unhealthy=2
    )
    
    # Mock get_position to return position with blocks_unhealthy=2
    mock_state_engine.get_position = Mock(return_value=position)
    
    opportunity = await detector.check_position(position)
    
    assert opportunity is not None, "Position unhealthy for 2 blocks should pass"
    assert isinstance(opportunity, Opportunity), "Should return Opportunity object"
    print("✓ Position with 2 unhealthy blocks correctly accepted")
    
    print("\n✓ All confirmation blocks logic tests passed!")


# ============================================================================
# Test 5: Profit Estimation Accuracy
# ============================================================================

async def test_profit_estimation():
    """Test profit estimation accuracy"""
    print("\n" + "=" * 80)
    print("Test 5: Profit Estimation Accuracy")
    print("=" * 80)
    
    config = create_mock_config()
    mock_state_engine = Mock(spec=StateEngine)
    mock_web3 = Mock(spec=Web3)
    
    detector = OpportunityDetector(config, mock_state_engine, mock_web3)
    
    # Test 5.1: Profitable opportunity
    print("\n5.1: Testing profitable opportunity...")
    
    position = create_mock_position(
        collateral_amount=1000 * 10**18,  # 1000 tokens
        debt_amount=800 * 10**18  # 800 tokens
    )
    
    collateral_price = Decimal('2000')  # $2000 per token
    debt_price = Decimal('1')  # $1 per token
    
    gross_profit, net_profit = await detector.estimate_profit(position, collateral_price, debt_price)
    
    assert gross_profit > Decimal('0'), "Gross profit should be positive"
    assert net_profit > Decimal('0'), "Net profit should be positive"
    assert net_profit < gross_profit, "Net profit should be less than gross profit"
    print(f"✓ Profitable opportunity: gross=${gross_profit:.2f}, net=${net_profit:.2f}")
    
    # Test 5.2: Unprofitable opportunity (small position)
    print("\n5.2: Testing unprofitable opportunity...")
    
    position = create_mock_position(
        collateral_amount=1 * 10**18,  # 1 token
        debt_amount=1 * 10**18  # 1 token
    )
    
    gross_profit, net_profit = await detector.estimate_profit(position, collateral_price, debt_price)
    
    # With small position, costs likely exceed profit
    print(f"✓ Small position: gross=${gross_profit:.2f}, net=${net_profit:.2f}")
    
    print("\n✓ All profit estimation tests passed!")


# ============================================================================
# Main Test Runner
# ============================================================================

async def run_all_tests():
    """Run all OpportunityDetector tests"""
    print("\n" + "=" * 80)
    print("OPPORTUNITYDETECTOR MODULE UNIT TESTS")
    print("=" * 80)
    
    try:
        await test_health_factor_calculation()
        await test_multi_oracle_sanity_checks()
        await test_price_movement_detection()
        await test_confirmation_blocks_logic()
        await test_profit_estimation()
        
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        return True
    
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    sys.exit(0 if success else 1)
