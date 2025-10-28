"""
Backtest Engine

Analyzes historical liquidation data to determine bot profitability.
Simulates bot behavior and calculates win rate, profit metrics, and ROI.

Requirements: 9.2, 9.3
"""

import csv
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from dataclasses import dataclass, field
from statistics import mean, median

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


@dataclass
class LiquidationEvent:
    """Historical liquidation event"""
    block_number: int
    block_timestamp: int
    datetime: str
    tx_hash: str
    protocol: str
    borrower: str
    liquidator: str
    collateral_asset: str
    debt_asset: str
    debt_amount: int
    collateral_seized: int
    gas_price_gwei: float
    gas_used: int
    tx_index: int
    
    @property
    def winner_latency_ms(self) -> int:
        """
        Estimate winner's latency based on transaction index
        Earlier tx_index = faster latency
        """
        # Assume first transaction in block had ~200ms latency
        # Each subsequent transaction adds ~50ms
        return 200 + (self.tx_index * 50)


@dataclass
class BacktestResult:
    """Result of backtesting a single liquidation"""
    event: LiquidationEvent
    bot_would_detect: bool
    bot_latency_ms: int
    winner_latency_ms: int
    bot_would_win: bool
    estimated_gross_profit_usd: Decimal
    estimated_costs_usd: Decimal
    estimated_net_profit_usd: Decimal
    profitable: bool
    rejection_reason: Optional[str] = None


@dataclass
class BacktestMetrics:
    """Aggregate backtest metrics"""
    total_liquidations: int = 0
    bot_detected: int = 0
    bot_would_win: int = 0
    bot_profitable: int = 0
    
    total_gross_profit_usd: Decimal = Decimal("0")
    total_costs_usd: Decimal = Decimal("0")
    total_net_profit_usd: Decimal = Decimal("0")
    
    win_rate: Decimal = Decimal("0")
    profitable_rate: Decimal = Decimal("0")
    detection_rate: Decimal = Decimal("0")
    
    average_gross_profit_usd: Decimal = Decimal("0")
    average_net_profit_usd: Decimal = Decimal("0")
    median_net_profit_usd: Decimal = Decimal("0")
    
    profitable_trades: List[Decimal] = field(default_factory=list)
    
    def calculate_derived_metrics(self):
        """Calculate derived metrics"""
        if self.total_liquidations > 0:
            self.detection_rate = Decimal(self.bot_detected) / Decimal(self.total_liquidations)
        
        if self.bot_detected > 0:
            self.win_rate = Decimal(self.bot_would_win) / Decimal(self.bot_detected)
            self.profitable_rate = Decimal(self.bot_profitable) / Decimal(self.bot_detected)
        
        if self.bot_profitable > 0:
            self.average_gross_profit_usd = self.total_gross_profit_usd / Decimal(self.bot_profitable)
            self.average_net_profit_usd = self.total_net_profit_usd / Decimal(self.bot_profitable)
        
        if self.profitable_trades:
            self.median_net_profit_usd = Decimal(str(median([float(p) for p in self.profitable_trades])))


class BacktestEngine:
    """Backtest engine for historical liquidation analysis"""
    
    # Bot performance parameters
    DETECTION_LATENCY_MS = 500  # Time to detect opportunity
    BUILD_LATENCY_MS = 200      # Time to build and submit transaction
    TOTAL_BOT_LATENCY_MS = DETECTION_LATENCY_MS + BUILD_LATENCY_MS  # 700ms total
    
    # Cost parameters
    MIN_PROFIT_USD = Decimal("50")
    FLASH_LOAN_PREMIUM_PERCENT = Decimal("0.09")  # 0.09%
    DEX_SLIPPAGE_PERCENT = Decimal("1.0")         # 1%
    BASELINE_BRIBE_PERCENT = Decimal("15.0")      # 15% of gross profit
    
    # Gas cost parameters (Base L2)
    ETH_PRICE_USD = Decimal("2000")  # Approximate ETH price
    L1_DATA_COST_MULTIPLIER = Decimal("1.4")  # L1 data adds ~40% to gas cost
    
    def __init__(self, liquidations_csv: Path, gas_prices_csv: Path):
        """
        Initialize backtest engine
        
        Args:
            liquidations_csv: Path to historical liquidations CSV
            gas_prices_csv: Path to historical gas prices CSV
        """
        self.liquidations_csv = liquidations_csv
        self.gas_prices_csv = gas_prices_csv
        
        self.liquidations: List[LiquidationEvent] = []
        self.gas_prices: Dict[int, Decimal] = {}  # block_number -> base_fee_gwei
        
        self.results: List[BacktestResult] = []
        self.metrics = BacktestMetrics()
    
    def load_data(self):
        """Load historical data from CSV files"""
        print("Loading historical data...")
        
        # Load liquidations
        with open(self.liquidations_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                event = LiquidationEvent(
                    block_number=int(row['block_number']),
                    block_timestamp=int(row['block_timestamp']),
                    datetime=row['datetime'],
                    tx_hash=row['tx_hash'],
                    protocol=row['protocol'],
                    borrower=row['borrower'],
                    liquidator=row['liquidator'],
                    collateral_asset=row['collateral_asset'],
                    debt_asset=row['debt_asset'],
                    debt_amount=int(row['debt_amount']),
                    collateral_seized=int(row['collateral_seized']),
                    gas_price_gwei=float(row['gas_price_gwei']),
                    gas_used=int(row['gas_used']),
                    tx_index=int(row['tx_index']),
                )
                self.liquidations.append(event)
        
        print(f"✓ Loaded {len(self.liquidations)} liquidations")
        
        # Load gas prices
        with open(self.gas_prices_csv, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                block_num = int(row['block_number'])
                base_fee = Decimal(str(row['base_fee_gwei']))
                self.gas_prices[block_num] = base_fee
        
        print(f"✓ Loaded {len(self.gas_prices)} gas price samples")
    
    def run_backtest(self):
        """Run backtest on all liquidations"""
        print("\nRunning backtest...")
        print(f"Bot latency: {self.TOTAL_BOT_LATENCY_MS}ms (detection: {self.DETECTION_LATENCY_MS}ms + build: {self.BUILD_LATENCY_MS}ms)")
        
        for i, event in enumerate(self.liquidations):
            result = self._backtest_liquidation(event)
            self.results.append(result)
            
            # Update metrics
            self._update_metrics(result)
            
            # Progress
            if (i + 1) % 10 == 0:
                progress = ((i + 1) / len(self.liquidations)) * 100
                print(f"Progress: {progress:.1f}% | Wins: {self.metrics.bot_would_win} | Profitable: {self.metrics.bot_profitable}", end='\r')
        
        print(f"\n✓ Backtest complete")
        
        # Calculate derived metrics
        self.metrics.calculate_derived_metrics()
    
    def _backtest_liquidation(self, event: LiquidationEvent) -> BacktestResult:
        """
        Backtest a single liquidation event
        
        Args:
            event: Historical liquidation event
            
        Returns:
            Backtest result
        """
        # Assume bot would always detect liquidatable positions
        # (health_factor < 1.0 is implicit since liquidation occurred)
        bot_would_detect = True
        
        # Bot latency
        bot_latency_ms = self.TOTAL_BOT_LATENCY_MS
        
        # Winner latency (from tx_index)
        winner_latency_ms = event.winner_latency_ms
        
        # Would bot win?
        bot_would_win = bot_latency_ms < winner_latency_ms
        
        # Estimate profit and costs
        gross_profit = self._estimate_gross_profit(event)
        costs = self._estimate_costs(event, gross_profit)
        net_profit = gross_profit - costs
        
        # Is it profitable?
        profitable = net_profit >= self.MIN_PROFIT_USD
        
        # Rejection reason
        rejection_reason = None
        if not bot_would_win:
            rejection_reason = "lost_to_faster_bot"
        elif not profitable:
            rejection_reason = f"insufficient_profit (${net_profit:.2f} < ${self.MIN_PROFIT_USD})"
        
        return BacktestResult(
            event=event,
            bot_would_detect=bot_would_detect,
            bot_latency_ms=bot_latency_ms,
            winner_latency_ms=winner_latency_ms,
            bot_would_win=bot_would_win,
            estimated_gross_profit_usd=gross_profit,
            estimated_costs_usd=costs,
            estimated_net_profit_usd=net_profit,
            profitable=profitable,
            rejection_reason=rejection_reason,
        )
    
    def _estimate_gross_profit(self, event: LiquidationEvent) -> Decimal:
        """
        Estimate gross profit from liquidation
        
        Simplified calculation:
        - Liquidation bonus: 5-10% of collateral value
        - Arbitrage opportunity: ~2-5% of collateral value
        - Total: ~7-15% of collateral value
        
        We'll use conservative 8% estimate
        """
        # Estimate collateral value in USD
        # Simplified: assume collateral_seized is in 18 decimals and worth ~$2000 (ETH-like)
        collateral_value_eth = Decimal(event.collateral_seized) / Decimal(10**18)
        collateral_value_usd = collateral_value_eth * self.ETH_PRICE_USD
        
        # Liquidation bonus + arbitrage (conservative 8%)
        gross_profit = collateral_value_usd * Decimal("0.08")
        
        return gross_profit
    
    def _estimate_costs(self, event: LiquidationEvent, gross_profit: Decimal) -> Decimal:
        """
        Estimate total costs for liquidation
        
        Costs include:
        1. Gas (L2 execution + L1 data posting)
        2. Builder bribe (% of gross profit)
        3. Flash loan premium
        4. DEX slippage
        """
        # 1. Gas costs
        gas_cost_usd = self._estimate_gas_cost(event)
        
        # 2. Builder bribe (15% of gross profit)
        bribe_usd = gross_profit * (self.BASELINE_BRIBE_PERCENT / Decimal("100"))
        
        # 3. Flash loan premium (0.09% of debt amount)
        debt_value_eth = Decimal(event.debt_amount) / Decimal(10**18)
        debt_value_usd = debt_value_eth * self.ETH_PRICE_USD
        flash_loan_cost = debt_value_usd * (self.FLASH_LOAN_PREMIUM_PERCENT / Decimal("100"))
        
        # 4. DEX slippage (1% of collateral value)
        collateral_value_eth = Decimal(event.collateral_seized) / Decimal(10**18)
        collateral_value_usd = collateral_value_eth * self.ETH_PRICE_USD
        slippage_cost = collateral_value_usd * (self.DEX_SLIPPAGE_PERCENT / Decimal("100"))
        
        total_costs = gas_cost_usd + bribe_usd + flash_loan_cost + slippage_cost
        
        return total_costs
    
    def _estimate_gas_cost(self, event: LiquidationEvent) -> Decimal:
        """
        Estimate gas cost including L1 data posting
        
        Base L2 gas cost = gas_used * gas_price * ETH_price
        L1 data cost adds ~40% to total
        """
        # Get gas price for block (or use event gas price)
        gas_price_gwei = self.gas_prices.get(
            event.block_number,
            Decimal(str(event.gas_price_gwei))
        )
        
        # L2 execution cost
        gas_cost_eth = (Decimal(event.gas_used) * gas_price_gwei) / Decimal(10**9)
        l2_cost_usd = gas_cost_eth * self.ETH_PRICE_USD
        
        # Total cost including L1 data posting
        total_gas_cost_usd = l2_cost_usd * self.L1_DATA_COST_MULTIPLIER
        
        return total_gas_cost_usd
    
    def _update_metrics(self, result: BacktestResult):
        """Update aggregate metrics with result"""
        self.metrics.total_liquidations += 1
        
        if result.bot_would_detect:
            self.metrics.bot_detected += 1
        
        if result.bot_would_win:
            self.metrics.bot_would_win += 1
        
        if result.bot_would_win and result.profitable:
            self.metrics.bot_profitable += 1
            self.metrics.total_gross_profit_usd += result.estimated_gross_profit_usd
            self.metrics.total_costs_usd += result.estimated_costs_usd
            self.metrics.total_net_profit_usd += result.estimated_net_profit_usd
            self.metrics.profitable_trades.append(result.estimated_net_profit_usd)
    
    def print_summary(self):
        """Print backtest summary"""
        m = self.metrics
        
        print("\n" + "=" * 80)
        print("BACKTEST SUMMARY")
        print("=" * 80)
        
        print(f"\nTotal Liquidations Analyzed: {m.total_liquidations:,}")
        print(f"Bot Would Detect: {m.bot_detected:,} ({m.detection_rate * 100:.1f}%)")
        print(f"Bot Would Win (latency): {m.bot_would_win:,} ({m.win_rate * 100:.1f}%)")
        print(f"Bot Profitable Executions: {m.bot_profitable:,} ({m.profitable_rate * 100:.1f}%)")
        
        print(f"\n--- Profitability ---")
        print(f"Total Gross Profit: ${m.total_gross_profit_usd:,.2f}")
        print(f"Total Costs: ${m.total_costs_usd:,.2f}")
        print(f"Total Net Profit: ${m.total_net_profit_usd:,.2f}")
        
        print(f"\n--- Per-Trade Metrics ---")
        print(f"Average Gross Profit: ${m.average_gross_profit_usd:,.2f}")
        print(f"Average Net Profit: ${m.average_net_profit_usd:,.2f}")
        print(f"Median Net Profit: ${m.median_net_profit_usd:,.2f}")
        
        # Monthly and annual projections
        if m.bot_profitable > 0:
            # Assume 30 days of data
            daily_profit = m.total_net_profit_usd / Decimal("30")
            monthly_profit = daily_profit * Decimal("30")
            annual_profit = daily_profit * Decimal("365")
            
            print(f"\n--- Projections (30-day sample) ---")
            print(f"Daily Profit: ${daily_profit:,.2f}")
            print(f"Monthly Profit: ${monthly_profit:,.2f}")
            print(f"Annual Profit: ${annual_profit:,.2f}")
            
            # ROI calculation (assume $2000 initial capital)
            initial_capital = Decimal("2000")
            annual_roi = (annual_profit / initial_capital) * Decimal("100")
            print(f"Annual ROI: {annual_roi:,.1f}% (on ${initial_capital:,.0f} capital)")
        
        print("\n" + "=" * 80)
    
    def save_results(self, output_path: Path):
        """Save detailed results to CSV"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        headers = [
            'block_number',
            'datetime',
            'tx_hash',
            'protocol',
            'borrower',
            'bot_would_detect',
            'bot_would_win',
            'bot_latency_ms',
            'winner_latency_ms',
            'estimated_gross_profit_usd',
            'estimated_costs_usd',
            'estimated_net_profit_usd',
            'profitable',
            'rejection_reason',
        ]
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for result in self.results:
                writer.writerow({
                    'block_number': result.event.block_number,
                    'datetime': result.event.datetime,
                    'tx_hash': result.event.tx_hash,
                    'protocol': result.event.protocol,
                    'borrower': result.event.borrower,
                    'bot_would_detect': result.bot_would_detect,
                    'bot_would_win': result.bot_would_win,
                    'bot_latency_ms': result.bot_latency_ms,
                    'winner_latency_ms': result.winner_latency_ms,
                    'estimated_gross_profit_usd': f"{result.estimated_gross_profit_usd:.2f}",
                    'estimated_costs_usd': f"{result.estimated_costs_usd:.2f}",
                    'estimated_net_profit_usd': f"{result.estimated_net_profit_usd:.2f}",
                    'profitable': result.profitable,
                    'rejection_reason': result.rejection_reason or '',
                })
        
        print(f"✓ Saved detailed results to {output_path}")


def main():
    """Main execution"""
    # Input paths
    data_dir = Path(__file__).parent.parent / 'data'
    liquidations_csv = data_dir / 'historical_liquidations.csv'
    gas_prices_csv = data_dir / 'historical_gas_prices.csv'
    results_csv = data_dir / 'backtest_results.csv'
    
    # Verify files exist
    if not liquidations_csv.exists():
        print(f"Error: {liquidations_csv} not found")
        print("Run collect_historical_data.py first")
        sys.exit(1)
    
    if not gas_prices_csv.exists():
        print(f"Error: {gas_prices_csv} not found")
        print("Run collect_historical_data.py first")
        sys.exit(1)
    
    print("=" * 80)
    print("Chimera Backtest Engine")
    print("=" * 80)
    
    # Initialize engine
    engine = BacktestEngine(liquidations_csv, gas_prices_csv)
    
    # Load data
    engine.load_data()
    
    # Run backtest
    engine.run_backtest()
    
    # Print summary
    engine.print_summary()
    
    # Save results
    engine.save_results(results_csv)
    
    print(f"\nResults saved to: {results_csv}")


if __name__ == '__main__':
    main()
