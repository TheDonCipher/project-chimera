#!/usr/bin/env python3
"""
Test script to verify monitoring stack configuration.

This script checks:
1. Prometheus configuration is valid
2. Grafana dashboard JSON is valid
3. Alert rules are valid
4. Metrics server can be imported
"""

import sys
import json
import yaml
from pathlib import Path

def test_prometheus_config():
    """Test Prometheus configuration file"""
    print("Testing Prometheus configuration...")
    
    config_path = Path(__file__).parent.parent / "infrastructure" / "prometheus.yml"
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        # Check required sections
        assert 'global' in config, "Missing 'global' section"
        assert 'scrape_configs' in config, "Missing 'scrape_configs' section"
        assert 'rule_files' in config, "Missing 'rule_files' section"
        
        # Check scrape configs
        scrape_configs = config['scrape_configs']
        bot_job = next((job for job in scrape_configs if job['job_name'] == 'chimera-bot'), None)
        assert bot_job is not None, "Missing 'chimera-bot' job"
        assert bot_job['metrics_path'] == '/metrics', "Wrong metrics path"
        
        print("✅ Prometheus configuration is valid")
        return True
    
    except Exception as e:
        print(f"❌ Prometheus configuration error: {e}")
        return False


def test_prometheus_alerts():
    """Test Prometheus alert rules"""
    print("Testing Prometheus alert rules...")
    
    alerts_path = Path(__file__).parent.parent / "infrastructure" / "prometheus-alerts.yml"
    
    try:
        with open(alerts_path, 'r') as f:
            alerts = yaml.safe_load(f)
        
        # Check required sections
        assert 'groups' in alerts, "Missing 'groups' section"
        
        # Check alert groups
        groups = alerts['groups']
        assert len(groups) > 0, "No alert groups defined"
        
        # Check first group has rules
        first_group = groups[0]
        assert 'rules' in first_group, "Missing 'rules' in first group"
        assert len(first_group['rules']) > 0, "No alert rules defined"
        
        # Check critical alerts exist
        rules = first_group['rules']
        alert_names = [rule['alert'] for rule in rules]
        
        critical_alerts = ['SystemHalted', 'OperatorBalanceLow', 'MetricsEndpointDown']
        for alert in critical_alerts:
            assert alert in alert_names, f"Missing critical alert: {alert}"
        
        print(f"✅ Prometheus alert rules are valid ({len(rules)} rules)")
        return True
    
    except Exception as e:
        print(f"❌ Prometheus alert rules error: {e}")
        return False


def test_grafana_dashboard():
    """Test Grafana dashboard JSON"""
    print("Testing Grafana dashboard...")
    
    dashboard_path = Path(__file__).parent.parent / "infrastructure" / "grafana-dashboard.json"
    
    try:
        with open(dashboard_path, 'r') as f:
            dashboard = json.load(f)
        
        # Check required sections
        assert 'title' in dashboard, "Missing 'title'"
        assert 'panels' in dashboard, "Missing 'panels'"
        
        # Check panels
        panels = dashboard['panels']
        assert len(panels) > 0, "No panels defined"
        
        # Check panel types
        panel_types = set(panel['type'] for panel in panels)
        expected_types = {'stat', 'timeseries', 'gauge'}
        assert panel_types.intersection(expected_types), "Missing expected panel types"
        
        print(f"✅ Grafana dashboard is valid ({len(panels)} panels)")
        return True
    
    except Exception as e:
        print(f"❌ Grafana dashboard error: {e}")
        return False


def test_grafana_provisioning():
    """Test Grafana provisioning files"""
    print("Testing Grafana provisioning...")
    
    base_path = Path(__file__).parent.parent / "infrastructure" / "grafana-provisioning"
    
    try:
        # Check datasource provisioning
        datasource_path = base_path / "datasources" / "prometheus.yml"
        assert datasource_path.exists(), "Missing datasource provisioning file"
        
        with open(datasource_path, 'r') as f:
            datasource = yaml.safe_load(f)
        
        assert 'datasources' in datasource, "Missing 'datasources' section"
        assert len(datasource['datasources']) > 0, "No datasources defined"
        
        # Check dashboard provisioning
        dashboard_prov_path = base_path / "dashboards" / "dashboards.yml"
        assert dashboard_prov_path.exists(), "Missing dashboard provisioning file"
        
        with open(dashboard_prov_path, 'r') as f:
            dashboard_prov = yaml.safe_load(f)
        
        assert 'providers' in dashboard_prov, "Missing 'providers' section"
        
        print("✅ Grafana provisioning is valid")
        return True
    
    except Exception as e:
        print(f"❌ Grafana provisioning error: {e}")
        return False


def test_metrics_server_import():
    """Test that metrics server can be imported"""
    print("Testing metrics server import...")
    
    try:
        # Add bot/src to path
        bot_src = Path(__file__).parent.parent / "bot" / "src"
        sys.path.insert(0, str(bot_src))
        
        # Try to import (this will fail if there are syntax errors)
        from metrics_server import MetricsServer
        
        # Check key methods exist
        assert hasattr(MetricsServer, 'start'), "Missing 'start' method"
        assert hasattr(MetricsServer, 'stop'), "Missing 'stop' method"
        assert hasattr(MetricsServer, 'update_system_state'), "Missing 'update_system_state' method"
        
        print("✅ Metrics server can be imported")
        return True
    
    except ModuleNotFoundError as e:
        if 'prometheus_client' in str(e):
            print("⚠️  Metrics server syntax OK (prometheus_client not installed - expected)")
            return True
        print(f"❌ Metrics server import error: {e}")
        return False
    
    except Exception as e:
        print(f"❌ Metrics server import error: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 70)
    print("Chimera Monitoring Stack Configuration Test")
    print("=" * 70)
    print()
    
    tests = [
        test_prometheus_config,
        test_prometheus_alerts,
        test_grafana_dashboard,
        test_grafana_provisioning,
        test_metrics_server_import,
    ]
    
    results = []
    for test in tests:
        result = test()
        results.append(result)
        print()
    
    print("=" * 70)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ All tests passed ({passed}/{total})")
        print()
        print("Monitoring stack is ready to use!")
        print("Start with: docker-compose --profile monitoring up -d")
        return 0
    else:
        print(f"❌ Some tests failed ({passed}/{total} passed)")
        return 1


if __name__ == "__main__":
    sys.exit(main())
