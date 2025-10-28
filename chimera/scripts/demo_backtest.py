"""
Demo Backtest with Sample Data

Demonstrates backtest functionality with synthetic data.
Useful for testing without collecting real historical data.
"""

import csv
from pathlib import Path
from decimal import Decimal
from datetime import datetime, timedelta
import random

# Generate sample liquidation data
def generate_sample_data():
    """Generate sample liquidation and gas price data for demo"""
    data_dir = Path(__file__).parent.parent / 'data'
    data_dir.mkdir(exist_ok=True)
    
    liquidations_csv = data_dir / 'sample_liquidations.csv'
    gas_prices_csv = data_dir / 'sample_gas_prices.csv'
    
    # Generate 100 sample liquidations over 30 days
    print("Generating sample liquidation data...")
    
    base_timestamp = int((datetime.now() - timedelta(days=30)).timestamp())
    base_block = 10_000_000
    
    liquidations = []
    for i in range(100):
        block_offset = i * 13000  # ~30 days / 100 liquidations
        liquidations.append({
            'block_number': base_block + block_offset,
            'block_timestamp': base_timestamp + (block_offset * 2),  # 2s per block
            'datetime': datetime.fromtimestamp(base_timestamp + (block_offset * 2)).isoformat(),
            'tx_hash': f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
            'protocol': random.choice(['moonwell', 'seamless']),
            'borrower': f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
            'liquidator': f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
            'collateral_asset': '0x4200000000000000000000000000000000000006',  # WETH
            'debt_asset': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  # USDC
            'debt_amount': random.randint(1000, 50000) * 10**6,  # USDC (6 decimals)
            'collateral_seized': random.randint(1, 20) * 10**17,  # 0.1-2 ETH
            'gas_price_gwei': random.uniform(0.001, 0.01),  # Base L2 gas prices
            'gas_used': random.randint(300000, 500000),
            'tx_index': random.randint(0, 20),  # Position in block
        })
    
    # Save liquidations
    with open(liquidations_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=liquidations[0].keys())
        writer.writeheader()
        writer.writerows(liquidations)
    
    print(f"✓ Generated {len(liquidations)} sample liquidations")
    
    # Generate gas price samples
    print("Generating sample gas price data...")
    
    gas_prices = []
    for i in range(0, 1_300_000, 1000):  # Sample every 1000 blocks
        gas_prices.append({
            'block_number': base_block + i,
            'timestamp': base_timestamp + (i * 2),
            'datetime': datetime.fromtimestamp(base_timestamp + (i * 2)).isoformat(),
            'base_fee_gwei': random.uniform(0.001, 0.01),
        })
    
    with open(gas_prices_csv, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=gas_prices[0].keys())
        writer.writeheader()
        writer.writerows(gas_prices)
    
    print(f"✓ Generated {len(gas_prices)} gas price samples")
    
    return liquidations_csv, gas_prices_csv


def main():
    """Run demo backtest"""
    print("=" * 80)
    print("CHIMERA BACKTEST DEMO")
    print("=" * 80)
    print("\nThis demo generates synthetic data and runs the backtest pipeline.")
    print("For real analysis, use collect_historical_data.py to get actual data.\n")
    
    # Generate sample data
    liquidations_csv, gas_prices_csv = generate_sample_data()
    
    # Import and run backtest
    try:
        from backtest_engine import BacktestEngine
        from sensitivity_analysis import SensitivityAnalyzer
        
        print("\n" + "=" * 80)
        print("RUNNING BACKTEST ENGINE")
        print("=" * 80)
        
        engine = BacktestEngine(liquidations_csv, gas_prices_csv)
        engine.load_data()
        engine.run_backtest()
        engine.print_summary()
        
        # Save results
        results_csv = Path(__file__).parent.parent / 'data' / 'demo_backtest_results.csv'
        engine.save_results(results_csv)
        
        print("\n" + "=" * 80)
        print("RUNNING SENSITIVITY ANALYSIS")
        print("=" * 80)
        
        # Extract metrics
        backtest_metrics = {
            'win_rate_percent': engine.metrics.win_rate * Decimal("100"),
            'avg_gross_profit_usd': engine.metrics.average_gross_profit_usd,
            'opportunities_per_day': int(engine.metrics.total_liquidations / 30),
        }
        
        analyzer = SensitivityAnalyzer(backtest_metrics)
        analyzer.generate_scenarios()
        analyzer.print_scenario_table()
        recommendation = analyzer.generate_recommendation()
        
        # Save report
        report_path = Path(__file__).parent.parent / 'data' / 'demo_sensitivity_analysis.txt'
        analyzer.save_report(report_path)
        
        print("\n" + "=" * 80)
        print("DEMO COMPLETE")
        print("=" * 80)
        print(f"\nNote: This used synthetic data. Results are for demonstration only.")
        print(f"For real analysis, collect actual historical data from Base mainnet.")
        
    except ImportError as e:
        print(f"\nError importing modules: {e}")
        print("Make sure you're running from the chimera directory")


if __name__ == '__main__':
    main()
