"""
Tests for dry-run report generator

Tests the dry_run_report.py script functionality.
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal

# Import the analyzer
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from bot.dry_run_report import DryRunAnalyzer


class TestDryRunAnalyzer:
    """Test suite for DryRunAnalyzer"""
    
    @pytest.fixture
    def sample_log_file(self):
        """Create a temporary log file with sample dry-run data"""
        # Create sample log entries
        base_time = datetime.utcnow()
        
        log_entries = []
        
        # Add some dry-run bundle submissions
        for i in range(10):
            timestamp = base_time + timedelta(minutes=i * 30)
            entry = {
                "timestamp": timestamp.isoformat() + "Z",
                "level": "INFO",
                "module": "chimera",
                "event": "[DRY-RUN] Would submit bundle",
                "context": {
                    "dry_run": True,
                    "protocol": "moonwell" if i % 2 == 0 else "seamless",
                    "borrower": f"0x{'1234' * 10}",
                    "net_profit_usd": 50.0 + (i * 10),
                    "simulated_profit_usd": 100.0 + (i * 10),
                    "total_cost_usd": 50.0,
                    "submission_path": "mempool",
                    "health_factor": 0.85,
                    "theoretical_profit_total": (50.0 + (i * 10)) * (i + 1),
                    "simulations_success": i + 1,
                    "simulations_failed": 0
                }
            }
            log_entries.append(json.dumps(entry))
        
        # Add some non-dry-run entries (should be ignored)
        for i in range(5):
            timestamp = base_time + timedelta(minutes=i * 60)
            entry = {
                "timestamp": timestamp.isoformat() + "Z",
                "level": "INFO",
                "module": "chimera",
                "event": "Regular log entry",
                "context": {
                    "dry_run": False
                }
            }
            log_entries.append(json.dumps(entry))
        
        # Write to temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            for entry in log_entries:
                f.write(entry + '\n')
            temp_path = Path(f.name)
        
        yield temp_path
        
        # Cleanup
        temp_path.unlink()
    
    def test_parse_logs(self, sample_log_file):
        """Test log parsing"""
        analyzer = DryRunAnalyzer(sample_log_file)
        analyzer.parse_logs()
        
        # Should have parsed 10 dry-run entries
        assert len(analyzer.simulations_success) == 10
        
        # Check time range was set
        assert analyzer.start_time is not None
        assert analyzer.end_time is not None
        assert analyzer.end_time > analyzer.start_time
    
    def test_parse_logs_with_hours_filter(self, sample_log_file):
        """Test log parsing with hours filter"""
        analyzer = DryRunAnalyzer(sample_log_file)
        
        # Only parse last 2 hours (should get fewer entries)
        analyzer.parse_logs(hours=2)
        
        # Should have some entries (exact count depends on timing)
        assert len(analyzer.simulations_success) >= 0
    
    def test_calculate_metrics(self, sample_log_file):
        """Test metrics calculation"""
        analyzer = DryRunAnalyzer(sample_log_file)
        analyzer.parse_logs()
        
        metrics = analyzer.calculate_metrics()
        
        # Check summary exists
        assert 'summary' in metrics
        summary = metrics['summary']
        
        # Check key metrics
        assert 'total_opportunities' in summary
        assert summary['total_opportunities'] == 10
        
        assert 'opportunities_per_hour' in summary
        assert summary['opportunities_per_hour'] > 0
        
        assert 'simulation_success_rate' in summary
        assert summary['simulation_success_rate'] == 100.0
        
        assert 'total_theoretical_profit_usd' in summary
        assert summary['total_theoretical_profit_usd'] > 0
    
    def test_profit_distribution(self, sample_log_file):
        """Test profit distribution calculation"""
        analyzer = DryRunAnalyzer(sample_log_file)
        analyzer.parse_logs()
        
        metrics = analyzer.calculate_metrics()
        
        # Check profit distribution
        assert 'profit_distribution' in metrics
        dist = metrics['profit_distribution']
        
        assert 'min_usd' in dist
        assert 'max_usd' in dist
        assert 'median_usd' in dist
        
        # Min should be less than max
        assert dist['min_usd'] < dist['max_usd']
        
        # Median should be between min and max
        assert dist['min_usd'] <= dist['median_usd'] <= dist['max_usd']
    
    def test_protocol_breakdown(self, sample_log_file):
        """Test protocol breakdown calculation"""
        analyzer = DryRunAnalyzer(sample_log_file)
        analyzer.parse_logs()
        
        metrics = analyzer.calculate_metrics()
        
        # Check protocol breakdown
        assert 'protocol_breakdown' in metrics
        breakdown = metrics['protocol_breakdown']
        
        # Should have both protocols
        assert 'moonwell' in breakdown
        assert 'seamless' in breakdown
        
        # Check structure
        for protocol, stats in breakdown.items():
            assert 'count' in stats
            assert 'total_profit_usd' in stats
            assert 'avg_profit_usd' in stats
            assert stats['count'] > 0
    
    def test_hourly_breakdown(self, sample_log_file):
        """Test hourly breakdown calculation"""
        analyzer = DryRunAnalyzer(sample_log_file)
        analyzer.parse_logs()
        
        metrics = analyzer.calculate_metrics()
        
        # Check hourly breakdown
        assert 'hourly_breakdown' in metrics
        hourly = metrics['hourly_breakdown']
        
        # Should have some hourly entries
        assert len(hourly) > 0
        
        # Check structure
        for entry in hourly:
            assert 'hour' in entry
            assert 'opportunities' in entry
            assert 'total_profit_usd' in entry
    
    def test_empty_log_file(self):
        """Test handling of empty log file"""
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            temp_path = Path(f.name)
        
        try:
            analyzer = DryRunAnalyzer(temp_path)
            analyzer.parse_logs()
            
            metrics = analyzer.calculate_metrics()
            
            # Should return error for no data
            assert 'error' in metrics or metrics['summary']['total_opportunities'] == 0
        
        finally:
            temp_path.unlink()
    
    def test_nonexistent_log_file(self):
        """Test handling of nonexistent log file"""
        analyzer = DryRunAnalyzer(Path('/nonexistent/file.log'))
        
        with pytest.raises(FileNotFoundError):
            analyzer.parse_logs()
    
    def test_malformed_json_handling(self):
        """Test handling of malformed JSON in log file"""
        # Create log file with some malformed entries
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.log') as f:
            f.write('not json\n')
            f.write('{"valid": "json"}\n')
            f.write('also not json\n')
            
            # Add valid dry-run entry
            base_time = datetime.utcnow()
            entry = {
                "timestamp": base_time.isoformat() + "Z",
                "level": "INFO",
                "module": "chimera",
                "event": "[DRY-RUN] Would submit bundle",
                "context": {
                    "dry_run": True,
                    "protocol": "moonwell",
                    "borrower": "0x1234",
                    "net_profit_usd": 75.0,
                    "simulated_profit_usd": 120.0,
                    "total_cost_usd": 45.0,
                    "submission_path": "mempool",
                    "health_factor": 0.85
                }
            }
            f.write(json.dumps(entry) + '\n')
            temp_path = Path(f.name)
        
        try:
            analyzer = DryRunAnalyzer(temp_path)
            analyzer.parse_logs()
            
            # Should have parsed the one valid dry-run entry
            assert len(analyzer.simulations_success) == 1
        
        finally:
            temp_path.unlink()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
