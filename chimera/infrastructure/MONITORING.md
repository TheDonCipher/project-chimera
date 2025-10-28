# Chimera Monitoring Stack

This directory contains the configuration for the local monitoring stack using Prometheus and Grafana.

## Overview

The monitoring stack provides real-time visibility into the Chimera bot's performance and health:

- **Prometheus**: Collects and stores time-series metrics from the bot
- **Grafana**: Visualizes metrics through interactive dashboards
- **Alerting**: Console-based alerts for local development (no SMS/email)

## Quick Start

### Start the monitoring stack

```bash
# Start bot with monitoring services
docker-compose --profile monitoring up -d

# Or start all services including tools
docker-compose --profile monitoring --profile tools up -d
```

### Access the dashboards

- **Grafana Dashboard**: http://localhost:3000

  - Username: `admin`
  - Password: `admin`
  - Dashboard: "Chimera MEV Bot Dashboard"

- **Prometheus UI**: http://localhost:9090

  - Query metrics directly
  - View alerting rules and their status

- **Bot Metrics Endpoint**: http://localhost:8000/metrics

  - Raw Prometheus metrics in text format

- **Bot Health Check**: http://localhost:8000/health
  - Simple health check endpoint

## Metrics Exposed

### System Metrics

- `chimera_system_state`: Current system state (0=NORMAL, 1=THROTTLED, 2=HALTED)
- `chimera_start_time_seconds`: Unix timestamp when the bot started
- `chimera_bot_info`: Bot information (network, chain_id, version)

### Opportunity & Execution Metrics

- `chimera_opportunities_detected_total`: Total liquidation opportunities detected
- `chimera_bundles_submitted_total`: Total transaction bundles submitted

### Performance Metrics

- `chimera_inclusion_rate`: Transaction inclusion rate (0.0 to 1.0)
- `chimera_simulation_accuracy`: Simulation accuracy rate (0.0 to 1.0)

### Profitability Metrics

- `chimera_total_profit_usd`: Total profit in USD
- `chimera_daily_volume_usd`: Daily execution volume in USD
- `chimera_daily_limit_usd`: Daily execution limit in USD

### Safety Metrics

- `chimera_consecutive_failures`: Number of consecutive execution failures

### Wallet & State Metrics

- `chimera_operator_balance_eth`: Operator wallet balance in ETH
- `chimera_positions_cached`: Number of positions currently cached
- `chimera_current_block`: Current blockchain block number
- `chimera_state_divergence_events_total`: Total state divergence events

## Dashboard Panels

The Grafana dashboard includes:

1. **System State**: Current operational state (NORMAL/THROTTLED/HALTED)
2. **Opportunities Detected**: Total count of liquidation opportunities
3. **Bundles Submitted**: Total count of submitted transactions
4. **Inclusion Rate**: Gauge showing transaction inclusion percentage
5. **Opportunity Detection Rate**: Time-series of opportunities/sec and submissions/sec
6. **Performance Metrics**: Inclusion rate and simulation accuracy over time
7. **Profitability**: Total profit and daily volume trends
8. **Consecutive Failures**: Tracking of execution failures
9. **Operator Balance**: Current ETH balance in operator wallet
10. **Positions Cached**: Number of positions being monitored
11. **Current Block**: Latest blockchain block processed
12. **Uptime**: Time since bot started

## Alerting Rules

Alerts are configured in `prometheus-alerts.yml` and log to console for local development:

### CRITICAL Alerts (🚨)

- System entered HALTED state
- Operator balance below 0.1 ETH
- Metrics endpoint down (bot may have crashed)

### HIGH Alerts (⚠️)

- System entered THROTTLED state
- Inclusion rate below 50%
- Simulation accuracy below 85%
- 2+ consecutive failures

### MEDIUM Alerts (ℹ️)

- Daily volume approaching limit (>80%)
- No opportunities detected for 30 minutes
- High rate of state divergence events

### LOW Alerts (ℹ️)

- Bot recently restarted

## Configuration Files

### `prometheus.yml`

Main Prometheus configuration:

- Scrape interval: 15 seconds
- Bot metrics scraped every 10 seconds from `bot:8000/metrics`
- Loads alerting rules from `prometheus-alerts.yml`

### `prometheus-alerts.yml`

Alerting rules for local development:

- All alerts log to console instead of sending notifications
- Alert evaluation interval: 30 seconds
- Thresholds match production requirements

### `grafana-dashboard.json`

Pre-configured dashboard with all key metrics:

- Auto-refresh every 10 seconds
- 1-hour time window by default
- Color-coded thresholds for quick status assessment

### `grafana-provisioning/`

Automatic Grafana configuration:

- `datasources/prometheus.yml`: Auto-configures Prometheus datasource
- `dashboards/dashboards.yml`: Auto-loads dashboard on startup

## Customization

### Modify Scrape Interval

Edit `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'chimera-bot'
    scrape_interval: 5s # Change from 10s to 5s
```

### Add Custom Metrics

1. Add metric definition in `bot/src/metrics_server.py`:

```python
custom_metric = Gauge('chimera_custom_metric', 'Description')
```

2. Update metric in bot code:

```python
MetricsServer.update_custom_metric(value)
```

3. Add panel to Grafana dashboard or create new dashboard

### Modify Alert Thresholds

Edit `prometheus-alerts.yml`:

```yaml
- alert: LowInclusionRate
  expr: chimera_inclusion_rate < 0.40 # Change from 0.50 to 0.40
```

## Troubleshooting

### Prometheus can't scrape bot metrics

**Symptom**: Alert "MetricsEndpointDown" firing

**Solutions**:

1. Check bot is running: `docker ps | grep chimera-bot`
2. Check metrics endpoint: `curl http://localhost:8000/metrics`
3. Check bot logs: `docker logs chimera-bot`
4. Verify bot container is on chimera-network: `docker network inspect chimera-network`

### Grafana dashboard shows "No Data"

**Solutions**:

1. Check Prometheus is scraping: http://localhost:9090/targets
2. Verify datasource connection in Grafana: Configuration → Data Sources
3. Check Prometheus has data: http://localhost:9090/graph (query: `chimera_system_state`)
4. Restart Grafana: `docker restart chimera-grafana`

### Alerts not appearing in Prometheus

**Solutions**:

1. Check alert rules loaded: http://localhost:9090/rules
2. Verify alerts.yml syntax: `docker logs chimera-prometheus`
3. Check alert evaluation: http://localhost:9090/alerts
4. Reload Prometheus config: `curl -X POST http://localhost:9090/-/reload`

### Dashboard not loading automatically

**Solutions**:

1. Check provisioning directory mounted: `docker inspect chimera-grafana`
2. Verify dashboard JSON syntax is valid
3. Check Grafana logs: `docker logs chimera-grafana`
4. Manually import dashboard: Grafana UI → Dashboards → Import → Upload JSON

## Production Considerations

For production deployment, replace console logging with real alerting:

1. **Set up Alertmanager**:

   - Configure SNS for SMS alerts
   - Configure PagerDuty for critical alerts
   - Configure email for medium/low alerts

2. **Use CloudWatch**:

   - Enable CloudWatch integration in bot config
   - Export metrics to CloudWatch for long-term storage
   - Set up CloudWatch alarms

3. **Secure Grafana**:

   - Change default admin password
   - Enable HTTPS
   - Configure authentication (OAuth, LDAP)
   - Restrict network access

4. **Scale Prometheus**:
   - Increase retention period
   - Configure remote storage (Thanos, Cortex)
   - Set up high availability

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Documentation](https://grafana.com/docs/)
- [Prometheus Best Practices](https://prometheus.io/docs/practices/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
