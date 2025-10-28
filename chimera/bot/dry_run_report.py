#!/usr/bin/env python3
"""
Dry-Run Report Generator

Analyzes dry-run logs to calculate theoretical performance metrics.

Usage:
    python dry_run_report.py [--log-file LOGFILE] [--hours HOURS]

Example:
    python dry_run_report.py --log-file logs/chimera.log --hours 24
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from collections import defaultdict


class DryRunAnalyzer:
    """Analyzes dry-run logs and generates performance report"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.opportunities = []
        self.simulations_success = []
        self.simulations_failed = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
    
    def parse_logs(self, hours: Optional[int] = None):
        """
        Parse log file and extract dry-run events.
        
        Args:
            hours: Only analyze logs from last N hours (None = all logs)
        """
        if not self.log_file.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file}")
        
        cutoff_time = None
        if hours:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        print(f"Parsing log file: {self.log_file}")
        if cutoff_time:
            print(f"Analyzing logs from last {hours} hours (since {cutoff_time.isoformat()})")
        
        with open(self.log_file, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    # Parse JSON log entry
                    log_entry = json.loads(line.strip())
                    
                    # Extract timestamp
                    timestamp_str = log_entry.get('timestamp', '')
                    if not timestamp_str:
                        continue
                    
                    # Parse timestamp (ISO 8601 format with Z suffix)
                    timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    
                    # Skip if before cutoff
                    if cutoff_time and timestamp < cutoff_time:
                        continue
                    
                    # Track time range
                    if self.start_time is None or timestamp < self.start_time:
                        self.start_time = timestamp
                    if self.end_time is None or timestamp > self.end_time:
                        self.end_time = timestamp
                    
                    # Extract dry-run events
                    event = log_entry.get('event', '')
                    context = log_entry.get('context', {})
                    
                    # Check if this is a dry-run log entry
                    if not context.get('dry_run', False):
                        continue
                    
                    # Extract dry-run bundle submission
                    if '[DRY-RUN] Would submit bundle' in event or 'Would submit bundle' in event:
                        self.simulations_success.append({
                            'timestamp': timestamp,
                            'protocol': context.get('protocol'),
                            'borrower': context.get('borrower'),
                            'net_profit_usd': Decimal(str(context.get('net_profit_usd', 0))),
                            'simulated_profit_usd': Decimal(str(context.get('simulated_profit_usd', 0))),
                            'total_cost_usd': Decimal(str(context.get('total_cost_usd', 0))),
                            'submission_path': context.get('submission_path'),
                            'health_factor': Decimal(str(context.get('health_factor', 0)))
                        })
                    
                    # Extract dry-run metrics snapshots
                    if 'Metrics snapshot' in event and context.get('dry_run'):
                        # This gives us aggregate stats
                        pass
                
                except json.JSONDecodeError:
                    # Skip non-JSON lines
                    continue
                except Exception as e:
                    print(f"Warning: Error parsing line {line_num}: {e}")
                    continue
        
        print(f"Parsed {len(self.simulations_success)} successful simulations")
        print(f"Time range: {self.start_time} to {self.end_time}")
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from parsed data"""
        if not self.start_time or not self.end_time:
            return {
                'error': 'No data found in logs'
            }
        
        # Calculate duration
        duration = self.end_time - self.start_time
        duration_hours = duration.total_seconds() / 3600
        
        # Opportunities detected per hour
        total_opportunities = len(self.simulations_success)
        opportunities_per_hour = total_opportunities / duration_hours if duration_hours > 0 else 0
        
        # Simulation success rate (in dry-run mode, all detected opportunities are simulated)
        simulation_success_rate = 1.0  # 100% since we only log successful simulations
        
        # Theoretical profit
        total_profit = sum(s['net_profit_usd'] for s in self.simulations_success)
        average_profit = total_profit / total_opportunities if total_opportunities > 0 else Decimal('0')
        
        # Profit distribution
        profit_distribution = self._calculate_profit_distribution()
        
        # Protocol breakdown
        protocol_breakdown = self._calculate_protocol_breakdown()
        
        # Hourly breakdown
        hourly_breakdown = self._calculate_hourly_breakdown()
        
        return {
            'summary': {
                'start_time': self.start_time.isoformat(),
                'end_time': self.end_time.isoformat(),
                'duration_hours': round(duration_hours, 2),
                'total_opportunities': total_opportunities,
                'opportunities_per_hour': round(opportunities_per_hour, 2),
                'simulation_success_rate': round(simulation_success_rate * 100, 2),
                'total_theoretical_profit_usd': float(total_profit),
                'average_profit_per_opportunity_usd': float(average_profit),
                'theoretical_hourly_profit_usd': float(total_profit / Decimal(str(duration_hours))) if duration_hours > 0 else 0,
                'theoretical_daily_profit_usd': float(total_profit / Decimal(str(duration_hours)) * Decimal('24')) if duration_hours > 0 else 0,
                'theoretical_monthly_profit_usd': float(total_profit / Decimal(str(duration_hours)) * Decimal('24') * Decimal('30')) if duration_hours > 0 else 0
            },
            'profit_distribution': profit_distribution,
            'protocol_breakdown': protocol_breakdown,
            'hourly_breakdown': hourly_breakdown
        }
    
    def _calculate_profit_distribution(self) -> Dict[str, Any]:
        """Calculate profit distribution statistics"""
        if not self.simulations_success:
            return {}
        
        profits = sorted([s['net_profit_usd'] for s in self.simulations_success])
        
        return {
            'min_usd': float(profits[0]),
            'max_usd': float(profits[-1]),
            'median_usd': float(profits[len(profits) // 2]),
            'p25_usd': float(profits[len(profits) // 4]),
            'p75_usd': float(profits[3 * len(profits) // 4]),
            'p90_usd': float(profits[9 * len(profits) // 10]) if len(profits) >= 10 else float(profits[-1]),
            'p99_usd': float(profits[99 * len(profits) // 100]) if len(profits) >= 100 else float(profits[-1])
        }
    
    def _calculate_protocol_breakdown(self) -> Dict[str, Dict[str, Any]]:
        """Calculate metrics by protocol"""
        protocol_stats = defaultdict(lambda: {
            'count': 0,
            'total_profit': Decimal('0'),
            'avg_profit': Decimal('0')
        })
        
        for sim in self.simulations_success:
            protocol = sim['protocol'] or 'unknown'
            protocol_stats[protocol]['count'] += 1
            protocol_stats[protocol]['total_profit'] += sim['net_profit_usd']
        
        # Calculate averages
        for protocol, stats in protocol_stats.items():
            if stats['count'] > 0:
                stats['avg_profit'] = stats['total_profit'] / stats['count']
        
        # Convert to regular dict with float values
        return {
            protocol: {
                'count': stats['count'],
                'total_profit_usd': float(stats['total_profit']),
                'avg_profit_usd': float(stats['avg_profit'])
            }
            for protocol, stats in protocol_stats.items()
        }
    
    def _calculate_hourly_breakdown(self) -> List[Dict[str, Any]]:
        """Calculate metrics by hour"""
        if not self.start_time or not self.end_time:
            return []
        
        hourly_stats = defaultdict(lambda: {
            'count': 0,
            'total_profit': Decimal('0')
        })
        
        for sim in self.simulations_success:
            # Round down to hour
            hour = sim['timestamp'].replace(minute=0, second=0, microsecond=0)
            hourly_stats[hour]['count'] += 1
            hourly_stats[hour]['total_profit'] += sim['net_profit_usd']
        
        # Convert to sorted list
        hourly_list = []
        for hour in sorted(hourly_stats.keys()):
            stats = hourly_stats[hour]
            hourly_list.append({
                'hour': hour.isoformat(),
                'opportunities': stats['count'],
                'total_profit_usd': float(stats['total_profit'])
            })
        
        return hourly_list
    
    def generate_report(self, output_file: Optional[Path] = None):
        """Generate and print/save report"""
        metrics = self.calculate_metrics()
        
        if 'error' in metrics:
            print(f"\nError: {metrics['error']}")
            return
        
        # Print report to console
        self._print_report(metrics)
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                json.dump(metrics, f, indent=2)
            print(f"\nDetailed report saved to: {output_file}")
    
    def _print_report(self, metrics: Dict[str, Any]):
        """Print formatted report to console"""
        summary = metrics['summary']
        
        print("\n" + "=" * 80)
        print("DRY-RUN PERFORMANCE REPORT")
        print("=" * 80)
        
        print("\n📊 SUMMARY")
        print("-" * 80)
        print(f"  Time Period:              {summary['start_time']} to {summary['end_time']}")
        print(f"  Duration:                 {summary['duration_hours']:.2f} hours")
        print(f"  Total Opportunities:      {summary['total_opportunities']}")
        print(f"  Opportunities/Hour:       {summary['opportunities_per_hour']:.2f}")
        print(f"  Simulation Success Rate:  {summary['simulation_success_rate']:.2f}%")
        
        print("\n💰 THEORETICAL PROFITABILITY")
        print("-" * 80)
        print(f"  Total Profit:             ${summary['total_theoretical_profit_usd']:.2f}")
        print(f"  Average/Opportunity:      ${summary['average_profit_per_opportunity_usd']:.2f}")
        print(f"  Hourly Rate:              ${summary['theoretical_hourly_profit_usd']:.2f}/hour")
        print(f"  Daily Projection:         ${summary['theoretical_daily_profit_usd']:.2f}/day")
        print(f"  Monthly Projection:       ${summary['theoretical_monthly_profit_usd']:.2f}/month")
        
        # Profit distribution
        if 'profit_distribution' in metrics and metrics['profit_distribution']:
            dist = metrics['profit_distribution']
            print("\n📈 PROFIT DISTRIBUTION")
            print("-" * 80)
            print(f"  Minimum:                  ${dist['min_usd']:.2f}")
            print(f"  25th Percentile:          ${dist['p25_usd']:.2f}")
            print(f"  Median:                   ${dist['median_usd']:.2f}")
            print(f"  75th Percentile:          ${dist['p75_usd']:.2f}")
            print(f"  90th Percentile:          ${dist['p90_usd']:.2f}")
            print(f"  Maximum:                  ${dist['max_usd']:.2f}")
        
        # Protocol breakdown
        if 'protocol_breakdown' in metrics and metrics['protocol_breakdown']:
            print("\n🏦 PROTOCOL BREAKDOWN")
            print("-" * 80)
            for protocol, stats in metrics['protocol_breakdown'].items():
                print(f"  {protocol.upper()}:")
                print(f"    Opportunities:          {stats['count']}")
                print(f"    Total Profit:           ${stats['total_profit_usd']:.2f}")
                print(f"    Average Profit:         ${stats['avg_profit_usd']:.2f}")
        
        # Hourly breakdown (show first and last few hours)
        if 'hourly_breakdown' in metrics and metrics['hourly_breakdown']:
            hourly = metrics['hourly_breakdown']
            print("\n⏰ HOURLY BREAKDOWN (First 5 and Last 5 hours)")
            print("-" * 80)
            
            # Show first 5
            for entry in hourly[:5]:
                print(f"  {entry['hour']}: {entry['opportunities']} opportunities, ${entry['total_profit_usd']:.2f}")
            
            if len(hourly) > 10:
                print("  ...")
            
            # Show last 5
            for entry in hourly[-5:]:
                print(f"  {entry['hour']}: {entry['opportunities']} opportunities, ${entry['total_profit_usd']:.2f}")
        
        print("\n" + "=" * 80)
        print("\n⚠️  NOTE: These are THEORETICAL projections based on simulation results.")
        print("   Actual results will vary based on:")
        print("   - Competition from other MEV bots")
        print("   - Transaction inclusion rates")
        print("   - Gas price volatility")
        print("   - Market conditions")
        print("=" * 80 + "\n")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Analyze dry-run logs and generate performance report',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Analyze all logs
  python dry_run_report.py

  # Analyze last 24 hours
  python dry_run_report.py --hours 24

  # Analyze specific log file
  python dry_run_report.py --log-file logs/chimera.log

  # Save detailed report to JSON
  python dry_run_report.py --hours 24 --output report.json
        """
    )
    
    parser.add_argument(
        '--log-file',
        type=Path,
        default=Path('logs/chimera.log'),
        help='Path to log file (default: logs/chimera.log)'
    )
    
    parser.add_argument(
        '--hours',
        type=int,
        default=None,
        help='Only analyze logs from last N hours (default: all logs)'
    )
    
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Save detailed report to JSON file (optional)'
    )
    
    args = parser.parse_args()
    
    try:
        # Create analyzer
        analyzer = DryRunAnalyzer(args.log_file)
        
        # Parse logs
        analyzer.parse_logs(hours=args.hours)
        
        # Generate report
        analyzer.generate_report(output_file=args.output)
    
    except FileNotFoundError as e:
        print(f"Error: {e}")
        print("\nMake sure the bot has been run in dry-run mode first:")
        print("  python -m chimera.bot.src.main --dry-run")
        return 1
    
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    exit(main())
