"""
Integrated Backtest Analysis Runner

Runs complete backtest analysis pipeline:
1. Load historical data (assumes already collected)
2. Run backtest engine
3. Generate sensitivity analysis
4. Produce comprehensive report

Usage: python run_backtest_analysis.py
"""

import sys
from pathlib import Path
from decimal import Decimal

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.backtest_engine import BacktestEngine
from scripts.sensitivity_analysis import SensitivityAnalyzer


def main():
    """Run complete backtest analysis"""
    data_dir = Path(__file__).parent.parent / 'data'
    
    # Input files
    liquidations_csv = data_dir / 'historical_liquidations.csv'
    gas_prices_csv = data_dir / 'historical_gas_prices.csv'
    
    # Output files
    backtest_results_csv = data_dir / 'backtest_results.csv'
    sensitivity_report_txt = data_dir / 'sensitivity_analysis.txt'
    
    print("=" * 120)
    print("CHIMERA BACKTEST ANALYSIS - COMPLETE PIPELINE")
    print("=" * 120)
    
    # Verify input files exist
    if not liquidations_csv.exists():
        print(f"\n✗ Error: {liquidations_csv} not found")
        print("Please run: python scripts/collect_historical_data.py")
        sys.exit(1)
    
    if not gas_prices_csv.exists():
        print(f"\n✗ Error: {gas_prices_csv} not found")
        print("Please run: python scripts/collect_historical_data.py")
        sys.exit(1)
    
    # Step 1: Run backtest engine
    print("\n" + "=" * 120)
    print("STEP 1: BACKTEST ENGINE")
    print("=" * 120)
    
    engine = BacktestEngine(liquidations_csv, gas_prices_csv)
    engine.load_data()
    engine.run_backtest()
    engine.print_summary()
    engine.save_results(backtest_results_csv)
    
    # Step 2: Generate sensitivity analysis
    print("\n" + "=" * 120)
    print("STEP 2: SENSITIVITY ANALYSIS")
    print("=" * 120)
    
    # Extract metrics from backtest
    backtest_metrics = {
        'win_rate_percent': engine.metrics.win_rate * Decimal("100"),
        'avg_gross_profit_usd': engine.metrics.average_gross_profit_usd,
        'opportunities_per_day': int(engine.metrics.total_liquidations / 30),  # Assume 30 days
    }
    
    analyzer = SensitivityAnalyzer(backtest_metrics)
    analyzer.generate_scenarios()
    analyzer.print_scenario_table()
    recommendation = analyzer.generate_recommendation()
    analyzer.save_report(sensitivity_report_txt)
    
    # Final summary
    print("\n" + "=" * 120)
    print("ANALYSIS COMPLETE")
    print("=" * 120)
    print(f"\nGenerated files:")
    print(f"  - Backtest results: {backtest_results_csv}")
    print(f"  - Sensitivity report: {sensitivity_report_txt}")
    print(f"\nRecommendation: {recommendation}")
    print("\n" + "=" * 120)


if __name__ == '__main__':
    main()
