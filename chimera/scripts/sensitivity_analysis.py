"""
Sensitivity Analysis

Generates scenario analysis with varying parameters to assess strategy robustness.
Provides GO/STOP/PIVOT recommendation based on Base Case ROI.

Requirements: 9.4
"""

import sys
from pathlib import Path
from typing import Dict, Any, List
from decimal import Decimal
from dataclasses import dataclass
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class Scenario:
    """Scenario parameters and results"""
    name: str
    description: str
    
    # Input parameters
    win_rate_percent: Decimal
    avg_gross_profit_usd: Decimal
    bribe_percent: Decimal
    opportunities_per_day: int
    
    # Calculated results
    avg_costs_usd: Decimal = Decimal("0")
    avg_net_profit_usd: Decimal = Decimal("0")
    daily_profit_usd: Decimal = Decimal("0")
    monthly_profit_usd: Decimal = Decimal("0")
    annual_profit_usd: Decimal = Decimal("0")
    annual_roi_percent: Decimal = Decimal("0")
    
    def calculate_results(self, initial_capital: Decimal = Decimal("2000")):
        """Calculate scenario results"""
        # Calculate costs
        gas_cost = Decimal("15")  # Average gas cost per tx
        bribe_cost = self.avg_gross_profit_usd * (self.bribe_percent / Decimal("100"))
        flash_loan_cost = self.avg_gross_profit_usd * Decimal("0.005")  # ~0.5% of gross
        slippage_cost = self.avg_gross_profit_usd * Decimal("0.01")  # 1% of gross
        
        self.avg_costs_usd = gas_cost + bribe_cost + flash_loan_cost + slippage_cost
        self.avg_net_profit_usd = self.avg_gross_profit_usd - self.avg_costs_usd
        
        # Calculate profitability
        successful_trades_per_day = self.opportunities_per_day * (self.win_rate_percent / Decimal("100"))
        self.daily_profit_usd = successful_trades_per_day * self.avg_net_profit_usd
        self.monthly_profit_usd = self.daily_profit_usd * Decimal("30")
        self.annual_profit_usd = self.daily_profit_usd * Decimal("365")
        
        # Calculate ROI
        if initial_capital > 0:
            self.annual_roi_percent = (self.annual_profit_usd / initial_capital) * Decimal("100")


class SensitivityAnalyzer:
    """Sensitivity analysis for strategy validation"""
    
    def __init__(self, backtest_metrics: Dict[str, Any]):
        """
        Initialize analyzer with backtest results
        
        Args:
            backtest_metrics: Dictionary of backtest metrics
        """
        self.backtest_metrics = backtest_metrics
        self.scenarios: List[Scenario] = []
        self.initial_capital = Decimal("2000")  # Tier 1 starting capital
    
    def generate_scenarios(self):
        """Generate scenario analysis"""
        print("\nGenerating scenario analysis...")
        
        # Extract base case parameters from backtest
        base_win_rate = self.backtest_metrics.get('win_rate_percent', Decimal("20"))
        base_gross_profit = self.backtest_metrics.get('avg_gross_profit_usd', Decimal("150"))
        base_opportunities = self.backtest_metrics.get('opportunities_per_day', 10)
        
        # Scenario 1: Optimistic
        optimistic = Scenario(
            name="Optimistic",
            description="Best case: High win rate, good profits, competitive bribes",
            win_rate_percent=Decimal("30"),  # 50% better than base
            avg_gross_profit_usd=Decimal("200"),  # 33% higher
            bribe_percent=Decimal("12"),  # Lower competition
            opportunities_per_day=int(base_opportunities * 1.2),  # 20% more opportunities
        )
        optimistic.calculate_results(self.initial_capital)
        self.scenarios.append(optimistic)
        
        # Scenario 2: Base Case
        base_case = Scenario(
            name="Base Case",
            description="Expected case: Moderate win rate and profits",
            win_rate_percent=base_win_rate,
            avg_gross_profit_usd=base_gross_profit,
            bribe_percent=Decimal("15"),  # Baseline
            opportunities_per_day=base_opportunities,
        )
        base_case.calculate_results(self.initial_capital)
        self.scenarios.append(base_case)
        
        # Scenario 3: Pessimistic
        pessimistic = Scenario(
            name="Pessimistic",
            description="Challenging case: Lower win rate, higher competition",
            win_rate_percent=base_win_rate * Decimal("0.7"),  # 30% lower
            avg_gross_profit_usd=base_gross_profit * Decimal("0.8"),  # 20% lower
            bribe_percent=Decimal("20"),  # Higher competition
            opportunities_per_day=int(base_opportunities * 0.8),  # 20% fewer
        )
        pessimistic.calculate_results(self.initial_capital)
        self.scenarios.append(pessimistic)
        
        # Scenario 4: Worst Case
        worst_case = Scenario(
            name="Worst Case",
            description="Severe case: Very low win rate, high costs",
            win_rate_percent=base_win_rate * Decimal("0.5"),  # 50% lower
            avg_gross_profit_usd=base_gross_profit * Decimal("0.6"),  # 40% lower
            bribe_percent=Decimal("25"),  # Very high competition
            opportunities_per_day=int(base_opportunities * 0.6),  # 40% fewer
        )
        worst_case.calculate_results(self.initial_capital)
        self.scenarios.append(worst_case)
        
        print(f"✓ Generated {len(self.scenarios)} scenarios")
    
    def print_scenario_table(self):
        """Print formatted scenario comparison table"""
        print("\n" + "=" * 120)
        print("SENSITIVITY ANALYSIS - SCENARIO COMPARISON")
        print("=" * 120)
        
        # Header
        print(f"\n{'Metric':<35} {'Optimistic':>15} {'Base Case':>15} {'Pessimistic':>15} {'Worst Case':>15}")
        print("-" * 120)
        
        # Input parameters
        print("\n--- Input Parameters ---")
        self._print_row("Win Rate", [f"{s.win_rate_percent:.1f}%" for s in self.scenarios])
        self._print_row("Avg Gross Profit", [f"${s.avg_gross_profit_usd:.0f}" for s in self.scenarios])
        self._print_row("Bribe %", [f"{s.bribe_percent:.0f}%" for s in self.scenarios])
        self._print_row("Opportunities/Day", [f"{s.opportunities_per_day}" for s in self.scenarios])
        
        # Calculated results
        print("\n--- Calculated Results ---")
        self._print_row("Avg Costs", [f"${s.avg_costs_usd:.2f}" for s in self.scenarios])
        self._print_row("Avg Net Profit", [f"${s.avg_net_profit_usd:.2f}" for s in self.scenarios])
        self._print_row("Daily Profit", [f"${s.daily_profit_usd:.2f}" for s in self.scenarios])
        self._print_row("Monthly Profit", [f"${s.monthly_profit_usd:.2f}" for s in self.scenarios])
        self._print_row("Annual Profit", [f"${s.annual_profit_usd:,.0f}" for s in self.scenarios])
        self._print_row("Annual ROI", [f"{s.annual_roi_percent:.1f}%" for s in self.scenarios])
        
        print("\n" + "=" * 120)
    
    def _print_row(self, label: str, values: List[str]):
        """Print a formatted table row"""
        print(f"{label:<35} {values[0]:>15} {values[1]:>15} {values[2]:>15} {values[3]:>15}")
    
    def generate_recommendation(self) -> str:
        """
        Generate GO/STOP/PIVOT recommendation
        
        Decision criteria:
        - GO: Base Case ROI > 100% AND Pessimistic ROI > 50%
        - PIVOT: Base Case ROI 50-100% OR Pessimistic ROI 0-50%
        - STOP: Base Case ROI < 50% OR Pessimistic ROI < 0%
        """
        base_case = self.scenarios[1]  # Base Case is second scenario
        pessimistic = self.scenarios[2]  # Pessimistic is third scenario
        
        base_roi = base_case.annual_roi_percent
        pess_roi = pessimistic.annual_roi_percent
        
        print("\n" + "=" * 120)
        print("RECOMMENDATION")
        print("=" * 120)
        
        print(f"\nBase Case Annual ROI: {base_roi:.1f}%")
        print(f"Pessimistic Annual ROI: {pess_roi:.1f}%")
        
        # Decision logic
        if base_roi > Decimal("100") and pess_roi > Decimal("50"):
            recommendation = "GO"
            reasoning = [
                "✓ Base Case ROI exceeds 100% target",
                "✓ Pessimistic scenario remains profitable (>50% ROI)",
                "✓ Strategy shows strong risk-adjusted returns",
                "",
                "Next Steps:",
                "1. Complete smart contract audit",
                "2. Deploy to Base Sepolia testnet",
                "3. Execute 50+ test liquidations",
                "4. Validate inclusion rate >60%",
                "5. Proceed to mainnet with Tier 1 limits"
            ]
        elif base_roi >= Decimal("50") or (base_roi < Decimal("100") and pess_roi >= Decimal("0")):
            recommendation = "PIVOT"
            reasoning = [
                "⚠ Base Case ROI below 100% target OR Pessimistic ROI marginal",
                "⚠ Strategy may be profitable but requires optimization",
                "",
                "Recommended Pivots:",
                "1. Optimize latency (consider Rust rewrite for 10x improvement)",
                "2. Reduce costs (negotiate better RPC rates, optimize gas)",
                "3. Expand to additional protocols (Aave, Compound)",
                "4. Consider alternative MEV strategies (arbitrage, sandwich)",
                "5. Re-run backtest after optimizations"
            ]
        else:
            recommendation = "STOP"
            reasoning = [
                "✗ Base Case ROI below 50% minimum threshold",
                "✗ Pessimistic scenario shows losses",
                "✗ Strategy not viable with current parameters",
                "",
                "Analysis:",
                "- Liquidation competition on Base may be too intense",
                "- Python latency disadvantage too significant",
                "- Consider alternative chains with less competition",
                "- Or pivot to different MEV strategy entirely"
            ]
        
        print(f"\n{'=' * 50}")
        print(f"RECOMMENDATION: {recommendation}")
        print(f"{'=' * 50}")
        
        for line in reasoning:
            print(line)
        
        print("\n" + "=" * 120)
        
        return recommendation
    
    def save_report(self, output_path: Path):
        """Save sensitivity analysis report to file"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write("=" * 120 + "\n")
            f.write("CHIMERA MEV BOT - SENSITIVITY ANALYSIS REPORT\n")
            f.write(f"Generated: {datetime.now().isoformat()}\n")
            f.write("=" * 120 + "\n\n")
            
            # Scenario table
            f.write("SCENARIO COMPARISON\n")
            f.write("-" * 120 + "\n\n")
            
            f.write(f"{'Metric':<35} {'Optimistic':>15} {'Base Case':>15} {'Pessimistic':>15} {'Worst Case':>15}\n")
            f.write("-" * 120 + "\n")
            
            # Input parameters
            f.write("\nInput Parameters:\n")
            f.write(f"{'Win Rate':<35} {self.scenarios[0].win_rate_percent:>14.1f}% {self.scenarios[1].win_rate_percent:>14.1f}% {self.scenarios[2].win_rate_percent:>14.1f}% {self.scenarios[3].win_rate_percent:>14.1f}%\n")
            f.write(f"{'Avg Gross Profit':<35} ${self.scenarios[0].avg_gross_profit_usd:>13.0f} ${self.scenarios[1].avg_gross_profit_usd:>13.0f} ${self.scenarios[2].avg_gross_profit_usd:>13.0f} ${self.scenarios[3].avg_gross_profit_usd:>13.0f}\n")
            f.write(f"{'Bribe %':<35} {self.scenarios[0].bribe_percent:>14.0f}% {self.scenarios[1].bribe_percent:>14.0f}% {self.scenarios[2].bribe_percent:>14.0f}% {self.scenarios[3].bribe_percent:>14.0f}%\n")
            f.write(f"{'Opportunities/Day':<35} {self.scenarios[0].opportunities_per_day:>15} {self.scenarios[1].opportunities_per_day:>15} {self.scenarios[2].opportunities_per_day:>15} {self.scenarios[3].opportunities_per_day:>15}\n")
            
            # Results
            f.write("\nCalculated Results:\n")
            f.write(f"{'Avg Net Profit':<35} ${self.scenarios[0].avg_net_profit_usd:>13.2f} ${self.scenarios[1].avg_net_profit_usd:>13.2f} ${self.scenarios[2].avg_net_profit_usd:>13.2f} ${self.scenarios[3].avg_net_profit_usd:>13.2f}\n")
            f.write(f"{'Daily Profit':<35} ${self.scenarios[0].daily_profit_usd:>13.2f} ${self.scenarios[1].daily_profit_usd:>13.2f} ${self.scenarios[2].daily_profit_usd:>13.2f} ${self.scenarios[3].daily_profit_usd:>13.2f}\n")
            f.write(f"{'Monthly Profit':<35} ${self.scenarios[0].monthly_profit_usd:>13.2f} ${self.scenarios[1].monthly_profit_usd:>13.2f} ${self.scenarios[2].monthly_profit_usd:>13.2f} ${self.scenarios[3].monthly_profit_usd:>13.2f}\n")
            f.write(f"{'Annual Profit':<35} ${self.scenarios[0].annual_profit_usd:>13,.0f} ${self.scenarios[1].annual_profit_usd:>13,.0f} ${self.scenarios[2].annual_profit_usd:>13,.0f} ${self.scenarios[3].annual_profit_usd:>13,.0f}\n")
            f.write(f"{'Annual ROI':<35} {self.scenarios[0].annual_roi_percent:>14.1f}% {self.scenarios[1].annual_roi_percent:>14.1f}% {self.scenarios[2].annual_roi_percent:>14.1f}% {self.scenarios[3].annual_roi_percent:>14.1f}%\n")
            
            f.write("\n" + "=" * 120 + "\n\n")
            
            # Recommendation
            base_case = self.scenarios[1]
            pessimistic = self.scenarios[2]
            
            f.write("RECOMMENDATION\n")
            f.write("-" * 120 + "\n\n")
            f.write(f"Base Case Annual ROI: {base_case.annual_roi_percent:.1f}%\n")
            f.write(f"Pessimistic Annual ROI: {pessimistic.annual_roi_percent:.1f}%\n\n")
            
            # Determine recommendation
            if base_case.annual_roi_percent > Decimal("100") and pessimistic.annual_roi_percent > Decimal("50"):
                f.write("RECOMMENDATION: GO\n\n")
                f.write("Strategy shows strong risk-adjusted returns. Proceed to testnet validation.\n")
            elif base_case.annual_roi_percent >= Decimal("50"):
                f.write("RECOMMENDATION: PIVOT\n\n")
                f.write("Strategy may be profitable but requires optimization before deployment.\n")
            else:
                f.write("RECOMMENDATION: STOP\n\n")
                f.write("Strategy not viable with current parameters. Consider alternative approaches.\n")
            
            f.write("\n" + "=" * 120 + "\n")
        
        print(f"✓ Saved report to {output_path}")


def main():
    """Main execution"""
    # For demonstration, use sample backtest metrics
    # In production, this would load from backtest_engine.py results
    
    sample_metrics = {
        'win_rate_percent': Decimal("20"),  # 20% win rate
        'avg_gross_profit_usd': Decimal("150"),  # $150 average gross
        'opportunities_per_day': 10,  # 10 opportunities per day
    }
    
    print("=" * 120)
    print("Chimera Sensitivity Analysis")
    print("=" * 120)
    
    # Initialize analyzer
    analyzer = SensitivityAnalyzer(sample_metrics)
    
    # Generate scenarios
    analyzer.generate_scenarios()
    
    # Print scenario table
    analyzer.print_scenario_table()
    
    # Generate recommendation
    recommendation = analyzer.generate_recommendation()
    
    # Save report
    output_path = Path(__file__).parent.parent / 'data' / 'sensitivity_analysis.txt'
    analyzer.save_report(output_path)
    
    print(f"\nReport saved to: {output_path}")


if __name__ == '__main__':
    main()
