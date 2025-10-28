"""
Unit tests for Backtest Engine (Task 8.4)

Tests:
- Detection logic with various health factors
- Latency comparison logic
- Profit calculation with all cost components
- Scenario generation

Requirements: 7.1.1
"""

import sys
from pathlib import Path
from decimal import Decimal
from unittest.mock import Mock, patch

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.backtest_engine import (
    BacktestEngine,
    LiquidationEvent,
    BacktestResult,
    BacktestMetrics
)
from scripts.sensitivity_analysis import SensitivityAnalyzer, Scenario


# ============================================================================
# Test Fixtures
# ============================================================================

def create_mock_liquidation_event(
    block_number=1000,
    tx_index=0,
    collateral_seized=1000 * 10**18,
    debt_amount=800 * 10**18,
    gas_used=500000,
    gas_price_gwei=0.05
):
    """Create mock liquidation event for testing"""
    return LiquidationEvent(
        block_number=block_number,
        block_timestamp=1700000000,
        datetime="2024-01-01 00:00:00",
        tx_hash="0x1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef",
        protocol="moonwell",
        borrower="0xBorrower000000000000000000000000000000",
        liquidator="0xLiquidator00000000000000000000000000000",
        collateral_asset="0xCollateral0000000000000000000000000000",
        debt_asset="0xDebt00000000000000000000000000000000000",
        debt_amount=debt_amount,
        collateral_seized=collateral_seized,
        gas_price_gwei=gas_price_gwei,
        gas_used=gas_used,
        tx_index=tx_index
    )


# ============================================================================
# Test 1: Detection Logic with Various Health Factors
# ============================================================================

def test_detection_logic():
    """Test detection logic with various health factors"""
    print("\n" + "=" * 80)
    print("Test 1: Detection Logic")
    print("=" * 80)
    
    # Create mock engine
    engine = BacktestEngine(
        liquidations_csv=Path("dummy.csv"),
        gas_prices_csv=Path("dummy.csv")
    )
    
    # Test 1.1: Bot should always detect liquidatable positions
    print("\n1.1: Testing bot detection (health_factor < 1.0 implicit)...")
    
    event = create_mock_liquidation_event()
    result = engine._backtest_liquidation(event)
    
    assert result.bot_would_detect == True, "Bot should always detect liquidatable positions"
    print("✓ Bot correctly detects liquidatable position")
    
    # Test 1.2: Detection with various position sizes
    print("\n1.2: Testing detection with various position sizes...")
    
    # Small position
    small_event = create_mock_liquidation_event(
        collateral_seized=1 * 10**18,
        debt_amount=1 * 10**18
    )
    small_result = engine._backtest_liquidation(small_event)
    assert small_result.bot_would_detect == True, "Bot should detect small positions"
    print("✓ Bot detects small position")
    
    # Large position
    large_event = create_mock_liquidation_event(
        collateral_seized=10000 * 10**18,
        debt_amount=8000 * 10**18
    )
    large_result = engine._backtest_liquidation(large_event)
    assert large_result.bot_would_detect == True, "Bot should detect large positions"
    print("✓ Bot detects large position")
    
    print("\n✓ All detection logic tests passed!")


# ============================================================================
# Test 2: Latency Comparison Logic
# ============================================================================

def test_latency_comparison():
    """Test latency comparison logic"""
    print("\n" + "=" * 80)
    print("Test 2: Latency Comparison Logic")
    print("=" * 80)
    
    engine = BacktestEngine(
        liquidations_csv=Path("dummy.csv"),
        gas_prices_csv=Path("dummy.csv")
    )
    
    # Test 2.1: Bot wins (faster than winner)
    print("\n2.1: Testing bot wins scenario...")
    
    # tx_index=10 means winner latency = 200 + (10 * 50) = 700ms
    # Bot latency = 700ms (detection 500ms + build 200ms)
    # Bot should NOT win (equal latency)
    event_equal = create_mock_liquidation_event(tx_index=10)
    result_equal = engine._backtest_liquidation(event_equal)
    
    assert result_equal.bot_latency_ms == 700, f"Expected bot latency 700ms, got {result_equal.bot_latency_ms}"
    assert result_equal.winner_latency_ms == 700, f"Expected winner latency 700ms, got {result_equal.winner_latency_ms}"
    assert result_equal.bot_would_win == False, "Bot should not win with equal latency"
    print(f"✓ Equal latency: bot={result_equal.bot_latency_ms}ms, winner={result_equal.winner_latency_ms}ms, win={result_equal.bot_would_win}")
    
    # Test 2.2: Bot wins (tx_index > 10)
    print("\n2.2: Testing bot wins with slower winner...")
    
    # tx_index=15 means winner latency = 200 + (15 * 50) = 950ms
    event_win = create_mock_liquidation_event(tx_index=15)
    result_win = engine._backtest_liquidation(event_win)
    
    assert result_win.winner_latency_ms == 950, f"Expected winner latency 950ms, got {result_win.winner_latency_ms}"
    assert result_win.bot_would_win == True, "Bot should win against slower winner"
    print(f"✓ Bot wins: bot={result_win.bot_latency_ms}ms, winner={result_win.winner_latency_ms}ms")
    
    # Test 2.3: Bot loses (faster winner)
    print("\n2.3: Testing bot loses to faster winner...")
    
    # tx_index=0 means winner latency = 200ms
    event_lose = create_mock_liquidation_event(tx_index=0)
    result_lose = engine._backtest_liquidation(event_lose)
    
    assert result_lose.winner_latency_ms == 200, f"Expected winner latency 200ms, got {result_lose.winner_latency_ms}"
    assert result_lose.bot_would_win == False, "Bot should lose to faster winner"
    assert result_lose.rejection_reason == "lost_to_faster_bot", "Should have correct rejection reason"
    print(f"✓ Bot loses: bot={result_lose.bot_latency_ms}ms, winner={result_lose.winner_latency_ms}ms")
    
    # Test 2.4: Winner latency calculation
    print("\n2.4: Testing winner latency calculation formula...")
    
    test_cases = [
        (0, 200),   # First tx: 200ms
        (1, 250),   # Second tx: 200 + 50 = 250ms
        (5, 450),   # Sixth tx: 200 + 250 = 450ms
        (20, 1200), # 21st tx: 200 + 1000 = 1200ms
    ]
    
    for tx_index, expected_latency in test_cases:
        event = create_mock_liquidation_event(tx_index=tx_index)
        assert event.winner_latency_ms == expected_latency, \
            f"tx_index={tx_index}: expected {expected_latency}ms, got {event.winner_latency_ms}ms"
        print(f"✓ tx_index={tx_index} -> {expected_latency}ms")
    
    print("\n✓ All latency comparison tests passed!")


# ============================================================================
# Test 3: Profit Calculation with All Cost Components
# ============================================================================

def test_profit_calculation():
    """Test profit calculation with all cost components"""
    print("\n" + "=" * 80)
    print("Test 3: Profit Calculation with All Cost Components")
    print("=" * 80)
    
    engine = BacktestEngine(
        liquidations_csv=Path("dummy.csv"),
        gas_prices_csv=Path("dummy.csv")
    )
    
    # Test 3.1: Gross profit estimation
    print("\n3.1: Testing gross profit estimation...")
    
    event = create_mock_liquidation_event(
        collateral_seized=1000 * 10**18  # 1000 tokens
    )
    
    gross_profit = engine._estimate_gross_profit(event)
    
    # Expected: 1000 tokens * $2000/token * 8% = $160,000
    expected_gross = Decimal("160000")
    assert gross_profit == expected_gross, f"Expected ${expected_gross}, got ${gross_profit}"
    print(f"✓ Gross profit: ${gross_profit:,.2f}")
    
    # Test 3.2: Gas cost calculation (L2 + L1)
    print("\n3.2: Testing gas cost calculation...")
    
    event = create_mock_liquidation_event(
        gas_used=500000,
        gas_price_gwei=0.05
    )
    
    gas_cost = engine._estimate_gas_cost(event)
    
    # L2 cost = 500000 * 0.05 / 10^9 * 2000 = 0.000025 ETH * $2000 = $0.05
    # Total with L1 multiplier = $0.05 * 1.4 = $0.07
    expected_gas_cost = Decimal("0.0700000")
    assert gas_cost == expected_gas_cost, f"Expected ${expected_gas_cost}, got ${gas_cost}"
    print(f"✓ Gas cost (L2 + L1): ${gas_cost:.2f}")
    
    # Test 3.3: Complete cost calculation
    print("\n3.3: Testing complete cost calculation...")
    
    event = create_mock_liquidation_event(
        collateral_seized=1000 * 10**18,
        debt_amount=800 * 10**18,
        gas_used=500000,
        gas_price_gwei=0.05
    )
    
    gross_profit = engine._estimate_gross_profit(event)
    total_costs = engine._estimate_costs(event, gross_profit)
    
    # Verify all cost components are included
    assert total_costs > Decimal("0"), "Total costs should be positive"
    
    # Calculate individual components for verification
    gas_cost = engine._estimate_gas_cost(event)
    bribe_cost = gross_profit * (engine.BASELINE_BRIBE_PERCENT / Decimal("100"))
    
    debt_value_eth = Decimal(event.debt_amount) / Decimal(10**18)
    debt_value_usd = debt_value_eth * engine.ETH_PRICE_USD
    flash_loan_cost = debt_value_usd * (engine.FLASH_LOAN_PREMIUM_PERCENT / Decimal("100"))
    
    collateral_value_eth = Decimal(event.collateral_seized) / Decimal(10**18)
    collateral_value_usd = collateral_value_eth * engine.ETH_PRICE_USD
    slippage_cost = collateral_value_usd * (engine.DEX_SLIPPAGE_PERCENT / Decimal("100"))
    
    expected_total = gas_cost + bribe_cost + flash_loan_cost + slippage_cost
    
    assert total_costs == expected_total, f"Expected ${expected_total:.2f}, got ${total_costs:.2f}"
    
    print(f"  - Gas cost: ${gas_cost:.2f}")
    print(f"  - Bribe (15%): ${bribe_cost:.2f}")
    print(f"  - Flash loan (0.09%): ${flash_loan_cost:.2f}")
    print(f"  - Slippage (1%): ${slippage_cost:.2f}")
    print(f"  - Total costs: ${total_costs:.2f}")
    print(f"✓ All cost components calculated correctly")
    
    # Test 3.4: Net profit calculation
    print("\n3.4: Testing net profit calculation...")
    
    result = engine._backtest_liquidation(event)
    
    expected_net = gross_profit - total_costs
    assert result.estimated_net_profit_usd == expected_net, \
        f"Expected net profit ${expected_net:.2f}, got ${result.estimated_net_profit_usd:.2f}"
    
    print(f"✓ Net profit: ${result.estimated_net_profit_usd:,.2f}")
    
    # Test 3.5: Profitability threshold
    print("\n3.5: Testing profitability threshold ($50 minimum)...")
    
    # Create small position that won't be profitable
    small_event = create_mock_liquidation_event(
        collateral_seized=1 * 10**18,  # 1 token
        debt_amount=1 * 10**18,
        tx_index=15  # Bot would win on latency
    )
    
    small_result = engine._backtest_liquidation(small_event)
    
    # Should be unprofitable due to small size
    if small_result.estimated_net_profit_usd < engine.MIN_PROFIT_USD:
        assert small_result.profitable == False, "Small position should be unprofitable"
        assert "insufficient_profit" in small_result.rejection_reason, "Should have insufficient profit reason"
        print(f"✓ Small position correctly marked unprofitable: ${small_result.estimated_net_profit_usd:.2f} < $50")
    
    print("\n✓ All profit calculation tests passed!")


# ============================================================================
# Test 4: Scenario Generation
# ============================================================================

def test_scenario_generation():
    """Test scenario generation for sensitivity analysis"""
    print("\n" + "=" * 80)
    print("Test 4: Scenario Generation")
    print("=" * 80)
    
    # Test 4.1: Scenario creation and calculation
    print("\n4.1: Testing scenario creation and calculation...")
    
    scenario = Scenario(
        name="Test Scenario",
        description="Test scenario for validation",
        win_rate_percent=Decimal("20"),
        avg_gross_profit_usd=Decimal("150"),
        bribe_percent=Decimal("15"),
        opportunities_per_day=10
    )
    
    scenario.calculate_results(initial_capital=Decimal("2000"))
    
    # Verify calculations
    assert scenario.avg_costs_usd > Decimal("0"), "Costs should be calculated"
    assert scenario.avg_net_profit_usd > Decimal("0"), "Net profit should be calculated"
    assert scenario.daily_profit_usd > Decimal("0"), "Daily profit should be calculated"
    assert scenario.monthly_profit_usd == scenario.daily_profit_usd * Decimal("30"), \
        "Monthly profit should be daily * 30"
    assert scenario.annual_profit_usd == scenario.daily_profit_usd * Decimal("365"), \
        "Annual profit should be daily * 365"
    assert scenario.annual_roi_percent > Decimal("0"), "ROI should be calculated"
    
    print(f"✓ Scenario calculations:")
    print(f"  - Avg net profit: ${scenario.avg_net_profit_usd:.2f}")
    print(f"  - Daily profit: ${scenario.daily_profit_usd:.2f}")
    print(f"  - Monthly profit: ${scenario.monthly_profit_usd:.2f}")
    print(f"  - Annual profit: ${scenario.annual_profit_usd:,.2f}")
    print(f"  - Annual ROI: {scenario.annual_roi_percent:.1f}%")
    
    # Test 4.2: Multiple scenario generation
    print("\n4.2: Testing multiple scenario generation...")
    
    backtest_metrics = {
        'win_rate_percent': Decimal("20"),
        'avg_gross_profit_usd': Decimal("150"),
        'opportunities_per_day': 10
    }
    
    analyzer = SensitivityAnalyzer(backtest_metrics)
    analyzer.generate_scenarios()
    
    assert len(analyzer.scenarios) == 4, "Should generate 4 scenarios"
    
    scenario_names = [s.name for s in analyzer.scenarios]
    assert "Optimistic" in scenario_names, "Should have Optimistic scenario"
    assert "Base Case" in scenario_names, "Should have Base Case scenario"
    assert "Pessimistic" in scenario_names, "Should have Pessimistic scenario"
    assert "Worst Case" in scenario_names, "Should have Worst Case scenario"
    
    print(f"✓ Generated {len(analyzer.scenarios)} scenarios:")
    for scenario in analyzer.scenarios:
        print(f"  - {scenario.name}: ROI={scenario.annual_roi_percent:.1f}%")
    
    # Test 4.3: Scenario ordering (Optimistic > Base > Pessimistic > Worst)
    print("\n4.3: Testing scenario ROI ordering...")
    
    optimistic = analyzer.scenarios[0]
    base_case = analyzer.scenarios[1]
    pessimistic = analyzer.scenarios[2]
    worst_case = analyzer.scenarios[3]
    
    assert optimistic.annual_roi_percent > base_case.annual_roi_percent, \
        "Optimistic ROI should be higher than Base Case"
    assert base_case.annual_roi_percent > pessimistic.annual_roi_percent, \
        "Base Case ROI should be higher than Pessimistic"
    assert pessimistic.annual_roi_percent > worst_case.annual_roi_percent, \
        "Pessimistic ROI should be higher than Worst Case"
    
    print("✓ Scenario ROI ordering correct:")
    print(f"  Optimistic ({optimistic.annual_roi_percent:.1f}%) > "
          f"Base ({base_case.annual_roi_percent:.1f}%) > "
          f"Pessimistic ({pessimistic.annual_roi_percent:.1f}%) > "
          f"Worst ({worst_case.annual_roi_percent:.1f}%)")
    
    # Test 4.4: Recommendation logic
    print("\n4.4: Testing recommendation logic...")
    
    # Test GO recommendation (high ROI)
    high_roi_metrics = {
        'win_rate_percent': Decimal("30"),
        'avg_gross_profit_usd': Decimal("200"),
        'opportunities_per_day': 15
    }
    high_analyzer = SensitivityAnalyzer(high_roi_metrics)
    high_analyzer.generate_scenarios()
    high_recommendation = high_analyzer.generate_recommendation()
    
    # Base case should have >100% ROI
    if high_analyzer.scenarios[1].annual_roi_percent > Decimal("100"):
        assert high_recommendation == "GO", "High ROI should result in GO recommendation"
        print(f"✓ GO recommendation for high ROI ({high_analyzer.scenarios[1].annual_roi_percent:.1f}%)")
    
    # Test STOP recommendation (low ROI)
    low_roi_metrics = {
        'win_rate_percent': Decimal("5"),
        'avg_gross_profit_usd': Decimal("50"),
        'opportunities_per_day': 3
    }
    low_analyzer = SensitivityAnalyzer(low_roi_metrics)
    low_analyzer.generate_scenarios()
    low_recommendation = low_analyzer.generate_recommendation()
    
    # Base case should have <50% ROI
    if low_analyzer.scenarios[1].annual_roi_percent < Decimal("50"):
        assert low_recommendation == "STOP", "Low ROI should result in STOP recommendation"
        print(f"✓ STOP recommendation for low ROI ({low_analyzer.scenarios[1].annual_roi_percent:.1f}%)")
    
    print("\n✓ All scenario generation tests passed!")


# ============================================================================
# Test 5: Metrics Calculation
# ============================================================================

def test_metrics_calculation():
    """Test backtest metrics calculation"""
    print("\n" + "=" * 80)
    print("Test 5: Metrics Calculation")
    print("=" * 80)
    
    # Test 5.1: Metrics initialization
    print("\n5.1: Testing metrics initialization...")
    
    metrics = BacktestMetrics()
    
    assert metrics.total_liquidations == 0, "Should initialize to 0"
    assert metrics.bot_detected == 0, "Should initialize to 0"
    assert metrics.bot_would_win == 0, "Should initialize to 0"
    assert metrics.bot_profitable == 0, "Should initialize to 0"
    assert metrics.total_net_profit_usd == Decimal("0"), "Should initialize to 0"
    
    print("✓ Metrics initialized correctly")
    
    # Test 5.2: Metrics update
    print("\n5.2: Testing metrics update...")
    
    engine = BacktestEngine(
        liquidations_csv=Path("dummy.csv"),
        gas_prices_csv=Path("dummy.csv")
    )
    
    # Create profitable result
    event = create_mock_liquidation_event(
        collateral_seized=1000 * 10**18,
        debt_amount=800 * 10**18,
        tx_index=15  # Bot wins
    )
    result = engine._backtest_liquidation(event)
    
    # Update metrics
    engine._update_metrics(result)
    
    assert engine.metrics.total_liquidations == 1, "Should count liquidation"
    assert engine.metrics.bot_detected == 1, "Should count detection"
    
    if result.bot_would_win and result.profitable:
        assert engine.metrics.bot_would_win == 1, "Should count win"
        assert engine.metrics.bot_profitable == 1, "Should count profitable"
        assert engine.metrics.total_net_profit_usd > Decimal("0"), "Should accumulate profit"
        print(f"✓ Metrics updated: wins={engine.metrics.bot_would_win}, profitable={engine.metrics.bot_profitable}")
    
    # Test 5.3: Derived metrics calculation
    print("\n5.3: Testing derived metrics calculation...")
    
    # Add more results
    for i in range(9):
        event = create_mock_liquidation_event(
            tx_index=15 if i < 5 else 0  # 5 wins, 5 losses
        )
        result = engine._backtest_liquidation(event)
        engine._update_metrics(result)
    
    engine.metrics.calculate_derived_metrics()
    
    assert engine.metrics.detection_rate > Decimal("0"), "Detection rate should be calculated"
    assert engine.metrics.win_rate > Decimal("0"), "Win rate should be calculated"
    
    print(f"✓ Derived metrics:")
    print(f"  - Detection rate: {engine.metrics.detection_rate * 100:.1f}%")
    print(f"  - Win rate: {engine.metrics.win_rate * 100:.1f}%")
    print(f"  - Profitable rate: {engine.metrics.profitable_rate * 100:.1f}%")
    
    print("\n✓ All metrics calculation tests passed!")


# ============================================================================
# Main Test Runner
# ============================================================================

def run_all_tests():
    """Run all backtest engine tests"""
    print("\n" + "=" * 80)
    print("BACKTEST ENGINE UNIT TESTS")
    print("=" * 80)
    
    try:
        test_detection_logic()
        test_latency_comparison()
        test_profit_calculation()
        test_scenario_generation()
        test_metrics_calculation()
        
        print("\n" + "=" * 80)
        print("ALL TESTS PASSED ✓")
        print("=" * 80)
        return True
    
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
