#!/usr/bin/env python3
"""
Dry-Run Report Generator

Analyzes dry-run logs to calculate theoretical performance metrics.

Usage:
    python scripts/dry_run_report.py [--log-file PATH] [--output PATH]

Example:
    python scripts/dry_run_report.py --log-file logs/chimera.log --output dry_run_report.txt
"""

import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
from collections import defaultdict


class DryRunAnalyzer:
    """Analyzes dry-run logs and generates performance report"""
    
    def __init__(self, log_file: Path):
        self.log_file = log_file
        self.opportunities = []
        self.simulations_success = []
        self.simulations_failed = []
        self.metrics_snapshots = []
        self.start_time = None
        self.end_time = None
    
    def parse_logs(self):
        """Parse JSON logs and extract dry-run data"""
        print(f"Parsing log file: {self.log_file}")
        
        if not self.log_file.exists():
            raise FileNotFoundError(f"Log file not found: {self.log_file}")
        
        with open(self.log_file, 'r') as f:
            for line_num, line in enumerate(f, 1):
                try:
                    # Skip empty lines
                    if not line.strip():
                        continue
                    
                    # Parse JSON log entry
                    log_entry = json.loads(line)
                    
                    # Track time range
                    timestamp_str = log_entry.get('timestamp')
                    if timestamp_str:
                        timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                        if self.start_time is None or timestamp < self.start_time:
                            self.start_time = timestamp
                        if self.end_time is None or timestamp > self.end_time:
                            self.end_time = timestamp
                    
                    # Extract dry-run specific entries
                    if log_entry.get('dry_run'):
                        message = log_entry.get('message', '')
                        
                        if 'Would submit bundle' in message:
                            self.simulations_success.append(log_entry)
                        elif 'Metrics snapshot' in message:
                            self.metrics_snapshots.append(log_entry)
                
                except json.JSONDecodeError:
                    # Skip non-JSON lines (e.g., startup messages)
                    continue
                except Exception as e:
                    print(f"Warning: Error parsing line {line_num}: {e}")
                    continue
        
        print(f"Parsed {len(self.simulations_success)} successful simulations")
        print(f"Found {len(self.metrics_snapshots)} metrics snapshots")
    
    def calculate_metrics(self) -> Dict[str, Any]:
        """Calculate performance metrics from parsed data"""
        if not self.simulations_success:
            return {
                'error': 'No successful simulations found in logs',
                'total_simulations': 0
            }
        
        # Calculate time range
        if self.start_time and self.end_time:
            duration = self.end_time - self.start_time
            duration_hours = duration.total_seconds() / 3600
        else:
            duration_hours = 0
        
        # Extract profit data
        profits = []
        protocols = defaultdict(int)
        submission_paths = defaultdict(int)
        
        for sim in self.simulations_success:
            profit = Decimal(str(sim.get('net_profit_usd', 0)))
            profits.append(profit)
            
            protocol = sim.get('protocol', 'unknown')
            protocols[protocol] += 1
            
            path = sim.get('submission_path', 'unknown')
            submission_paths[path] += 1
        
        # Calculate statistics
        total_profit = sum(profits)
        avg_profit = total_profit / len(profits) if profits else Decimal('0')
        min_profit = min(profits) if profits else Decimal('0')
        max_profit = max(profits) if profits else Decimal('0')
        
        # Get final metrics snapshot if available
        final_snapshot = self.metrics_snapshots[-1] if self.metrics_snapshots else {}
        
        opportunities_detected = final_snapshot.get('opportunities_detected', len(self.simulations_success))
        simulations_failed = final_snapshot.get('simulations_failed', 0)
        total_simulations = len(self.simulations_success) + simulations_failed
        
        simulation_success_rate = (
            len(self.simulations_success) / total_simulations * 100
            if total_simulations > 0 else 0
        )
        
        opportunities_per_hour = (
            opportunities_detected / duration_hours
            if duration_hours > 0 else 0
        )
        
        profitable_simulations_per_hour = (
            len(self.simulations_success) / duration_hours
            if duration_hours > 0 else 0
        )
        
        return {
            'time_range': {
                'start': self.start_time.isoformat() if self.start_time else 'unknown',
                'end': self.end_time.isoformat() if self.end_time else 'unknown',
                'duration_hours': round(duration_hours, 2)
            },
            'opportunities': {
                'total_detected': opportunities_detected,
                'per_hour': round(opportunities_per_hour, 2)
            },
            'simulations': {
                'total': total_simulations,
                'successful': len(self.simulations_success),
                'failed': simulations_failed,
                'success_rate_percent': round(simulation_success_rate, 2),
                'profitable_per_hour': round(profitable_simulations_per_hour, 2)
            },
            'theoretical_profit': {
                'total_usd': float(total_profit),
                'average_usd': float(avg_profit),
                'min_usd': float(min_profit),
                'max_usd': float(max_profit),
                'per_hour_usd': float(total_profit / Decimal(str(duration_hours))) if duration_hours > 0 else 0
            },
            'protocols': dict(protocols),
            'submission_paths': dict(submission_paths)
        }
    
    def generate_report(self, output_file: Path = None) -> str:
        """Generate human-readable report"""
        metrics = self.calculate_metrics()
        
        if 'error' in metrics:
            return f"ERROR: {metrics['error']}"
        
        # Build report
        lines = []
        lines.append("=" * 80)
        lines.append("DRY-RUN PERFORMANCE REPORT")
        lines.append("=" * 80)
        lines.append("")
        
        # Time Range
        lines.append("TIME RANGE")
        lines.append("-" * 80)
        lines.append(f"Start:    {metrics['time_range']['start']}")
        lines.append(f"End:      {metrics['time_range']['end']}")
        lines.append(f"Duration: {metrics['time_range']['duration_hours']} hours")
        lines.append("")
        
        # Opportunities
        lines.append("OPPORTUNITIES DETECTED")
        lines.append("-" * 80)
        lines.append(f"Total:    {metrics['opportunities']['total_detected']}")
        lines.append(f"Per Hour: {metrics['opportunities']['per_hour']}")
        lines.append("")
        
        # Simulations
        lines.append("SIMULATIONS")
        lines.append("-" * 80)
        lines.append(f"Total:        {metrics['simulations']['total']}")
        lines.append(f"Successful:   {metrics['simulations']['successful']}")
        lines.append(f"Failed:       {metrics['simulations']['failed']}")
        lines.append(f"Success Rate: {metrics['simulations']['success_rate_percent']}%")
        lines.append(f"Profitable/Hour: {metrics['simulations']['profitable_per_hour']}")
        lines.append("")
        
        # Theoretical Profit
        lines.append("THEORETICAL PROFIT (if all simulations were executed)")
        lines.append("-" * 80)
        lines.append(f"Total:    ${metrics['theoretical_profit']['total_usd']:.2f}")
        lines.append(f"Average:  ${metrics['theoretical_profit']['average_usd']:.2f}")
        lines.append(f"Min:      ${metrics['theoretical_profit']['min_usd']:.2f}")
        lines.append(f"Max:      ${metrics['theoretical_profit']['max_usd']:.2f}")
        lines.append(f"Per Hour: ${metrics['theoretical_profit']['per_hour_usd']:.2f}")
        lines.append("")
        
        # Protocols
        lines.append("PROTOCOLS")
        lines.append("-" * 80)
        for protocol, count in metrics['protocols'].items():
            pct = count / metrics['simulations']['successful'] * 100
            lines.append(f"{protocol:20s} {count:5d} ({pct:5.1f}%)")
        lines.append("")
        
        # Submission Paths
        lines.append("SUBMISSION PATHS")
        lines.append("-" * 80)
        for path, count in metrics['submission_paths'].items():
            pct = count / metrics['simulations']['successful'] * 100
            lines.append(f"{path:20s} {count:5d} ({pct:5.1f}%)")
        lines.append("")
        
        # Projections
        lines.append("PROJECTIONS (assuming 100% inclusion rate)")
        lines.append("-" * 80)
        daily_profit = metrics['theoretical_profit']['per_hour_usd'] * 24
        monthly_profit = daily_profit * 30
        annual_profit = daily_profit * 365
        lines.append(f"Daily:   ${daily_profit:.2f}")
        lines.append(f"Monthly: ${monthly_profit:.2f}")
        lines.append(f"Annual:  ${annual_profit:.2f}")
        lines.append("")
        
        # Recommendations
        lines.append("RECOMMENDATIONS")
        lines.append("-" * 80)
        
        if metrics['simulations']['success_rate_percent'] < 50:
            lines.append("⚠️  LOW SIMULATION SUCCESS RATE (<50%)")
            lines.append("    - Review opportunity detection filters")
            lines.append("    - Check oracle price accuracy")
            lines.append("")
        
        if metrics['opportunities']['per_hour'] < 1:
            lines.append("⚠️  LOW OPPORTUNITY DETECTION RATE (<1/hour)")
            lines.append("    - Verify state engine is processing blocks correctly")
            lines.append("    - Check position cache is populated")
            lines.append("    - Consider expanding protocol coverage")
            lines.append("")
        
        if metrics['theoretical_profit']['average_usd'] < 50:
            lines.append("⚠️  LOW AVERAGE PROFIT (<$50)")
            lines.append("    - Opportunities may not be profitable after real costs")
            lines.append("    - Review cost calculation parameters")
            lines.append("")
        
        if monthly_profit < 1000:
            lines.append("⚠️  LOW PROJECTED MONTHLY PROFIT (<$1000)")
            lines.append("    - Strategy may not be viable at current scale")
            lines.append("    - Consider: more protocols, better latency, or different strategy")
            lines.append("")
        else:
            lines.append("✅ Projected monthly profit looks promising")
            lines.append(f"   Continue monitoring for at least 24 hours for reliable data")
            lines.append("")
        
        lines.append("=" * 80)
        lines.append("NOTE: These are theoretical projections based on simulations only.")
        lines.append("Actual results will be lower due to:")
        lines.append("  - Competition from other MEV bots")
        lines.append("  - Transaction inclusion rate (<100%)")
        lines.append("  - Actual vs simulated profit variance")
        lines.append("  - Network conditions and gas price volatility")
        lines.append("=" * 80)
        
        report = "\n".join(lines)
        
        # Write to file if specified
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report)
            print(f"\nReport written to: {output_file}")
        
        return report


def main():
    parser = argparse.ArgumentParser(
        description='Analyze dry-run logs and generate performance report'
    )
    parser.add_argument(
        '--log-file',
        type=Path,
        default=Path('logs/chimera.log'),
        help='Path to log file (default: logs/chimera.log)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=None,
        help='Output file path (default: print to stdout)'
    )
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output metrics as JSON instead of formatted report'
    )
    
    args = parser.parse_args()
    
    # Create analyzer
    analyzer = DryRunAnalyzer(args.log_file)
    
    # Parse logs
    analyzer.parse_logs()
    
    # Generate output
    if args.json:
        metrics = analyzer.calculate_metrics()
        output = json.dumps(metrics, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(output)
            print(f"JSON metrics written to: {args.output}")
        else:
            print(output)
    else:
        report = analyzer.generate_report(args.output)
        
        if not args.output:
            print(report)


if __name__ == '__main__':
    main()
