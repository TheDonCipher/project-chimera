# Logging Infrastructure

## Overview

The Chimera logging infrastructure provides structured JSON logging with multiple output handlers, log rotation, retention policies, and optional CloudWatch integration. This implements Requirement 7.7 for comprehensive audit trail and performance monitoring.

## Features

- **Structured JSON Logging**: All logs are in JSON format with consistent fields (timestamp, level, module, context)
- **Multiple Handlers**: Console, file, execution-specific file, and CloudWatch
- **Log Rotation**: Automatic rotation when files reach 100 MB
- **Retention Policies**:
  - Local files: 10 backups for general logs, 50 for execution logs
  - CloudWatch: 30 days hot storage
  - Database: 3 years (per requirements)
- **Module-Specific Loggers**: Each module gets its own logger with proper context
- **CloudWatch Integration**: Optional real-time log aggregation to AWS CloudWatch

## Log Structure

Every log entry contains:

```json
{
  "timestamp": "2024-01-15T10:30:45.123456Z",
  "level": "INFO",
  "module": "state_engine",
  "event": "websocket_connected",
  "context": {
    "provider": "alchemy",
    "endpoint": "wss://..."
  }
}
```

## Usage

### Initialization

Initialize logging at application startup:

```python
from logging_config import init_logging
from pathlib import Path

# Basic initialization (local only)
init_logging(
    log_dir=Path("logs"),
    log_level="INFO"
)

# With CloudWatch integration
init_logging(
    log_dir=Path("logs"),
    log_level="INFO",
    enable_cloudwatch=True,
    cloudwatch_region="us-east-1",
    cloudwatch_log_group="Chimera",
    cloudwatch_log_stream="bot-production"
)
```

### Getting a Logger

Each module should get its own logger:

```python
from logging_config import get_logger

logger = get_logger("state_engine")
```

### Basic Logging

```python
# Info level
logger.info(
    "websocket_connected",
    context={"provider": "alchemy", "endpoint": "wss://..."}
)

# Warning level
logger.warning(
    "high_gas_price",
    context={"gas_price_gwei": "150", "threshold_gwei": "100"}
)

# Error level
logger.error(
    "rpc_connection_failed",
    context={"provider": "quicknode", "error": "timeout"}
)

# With exception info
try:
    # some code
    pass
except Exception as e:
    logger.error(
        "unexpected_error",
        context={"operation": "fetch_position"},
        exc_info=True
    )
```

### Specialized Logging Functions

#### Execution Attempts

```python
from logging_config import log_execution_attempt

execution_record = {
    "timestamp": "2024-01-15T10:30:45.123456Z",
    "block_number": 12345678,
    "protocol": "moonwell",
    "borrower": "0x...",
    "simulation_success": True,
    "simulated_profit_usd": "120.00",
    "tx_hash": "0x...",
    "status": "pending"
}

log_execution_attempt(logger, execution_record)
```

#### State Transitions

```python
from logging_config import log_state_transition

log_state_transition(
    logger=logger,
    from_state="NORMAL",
    to_state="THROTTLED",
    reason="Inclusion rate dropped to 55%",
    metrics={"inclusion_rate": "0.55"}
)
```

#### State Divergence

```python
from logging_config import log_state_divergence

log_state_divergence(
    logger=logger,
    protocol="moonwell",
    user="0x...",
    field="debt_amount",
    cached_value=1000000000000000000,
    canonical_value=1001500000000000000,
    divergence_bps=150,
    block_number=12345678
)
```

#### Safety Violations

```python
from logging_config import log_safety_violation

log_safety_violation(
    logger=logger,
    violation_type="max_daily_volume",
    current_value="2450.00",
    limit_value="2500.00",
    context={"remaining_capacity_usd": "50.00"}
)
```

#### Performance Metrics

```python
from logging_config import log_performance_metrics

metrics = {
    "inclusion_rate": "0.68",
    "simulation_accuracy": "0.94",
    "total_profit_usd": "8450.00"
}

log_performance_metrics(logger, metrics)
```

## Log Files

### Local Files

- **logs/chimera.log**: All logs from all modules
  - Rotation: 100 MB per file
  - Retention: 10 backup files (~1 GB total)
- **logs/executions.log**: Execution attempts only (audit trail)
  - Rotation: 100 MB per file
  - Retention: 50 backup files (~5 GB total)
  - Filtered to only include execution-related logs

### CloudWatch Logs

When enabled, logs are sent to AWS CloudWatch Logs:

- **Log Group**: Configurable (default: "Chimera")
- **Log Stream**: Auto-generated with timestamp or custom
- **Retention**: 30 days (configurable)
- **Batching**: Logs are batched (100 events or 5 seconds) to reduce API calls

## Log Levels

- **DEBUG**: Detailed diagnostic information (not used in production)
- **INFO**: General informational messages (normal operations)
- **WARNING**: Warning messages (degraded performance, approaching limits)
- **ERROR**: Error messages (failures, exceptions)
- **CRITICAL**: Critical errors (system halt, security incidents)

## CloudWatch Integration

### Setup

1. Ensure AWS credentials are configured (IAM role or environment variables)
2. Grant CloudWatch Logs permissions:
   ```json
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "logs:CreateLogGroup",
           "logs:CreateLogStream",
           "logs:PutLogEvents",
           "logs:PutRetentionPolicy"
         ],
         "Resource": "arn:aws:logs:*:*:log-group:Chimera:*"
       }
     ]
   }
   ```
3. Enable in configuration:
   ```python
   init_logging(enable_cloudwatch=True)
   ```

### Graceful Degradation

If CloudWatch is unavailable:

- Logs continue to console and file
- Error message printed to stderr
- Application continues normally

## Performance Considerations

- **Async Logging**: Handlers use buffering to minimize I/O blocking
- **Batch CloudWatch**: Events are batched to reduce API calls
- **Rotation**: Automatic rotation prevents disk space issues
- **Filtering**: Execution logs are filtered to separate file for audit trail

## Testing

Run the example script to verify logging:

```bash
cd chimera/bot/src
python example_logging.py
```

This will create sample logs demonstrating all features.

## Monitoring Log Health

Monitor these metrics:

- Log file sizes (should rotate at 100 MB)
- CloudWatch API errors (check stderr)
- Disk space usage (logs directory)
- Log write latency (should be <10ms)

## Troubleshooting

### Logs not appearing

1. Check log level configuration
2. Verify log directory permissions
3. Check disk space

### CloudWatch errors

1. Verify AWS credentials
2. Check IAM permissions
3. Verify network connectivity
4. Check CloudWatch service status

### High disk usage

1. Verify rotation is working (check backup files)
2. Adjust retention policy (reduce backup count)
3. Consider archiving old logs to S3

## Compliance

The logging infrastructure meets these requirements:

- **Requirement 7.7**: Complete audit trail with 3-year retention
- **Immutable Records**: Append-only log files
- **Structured Format**: JSON for easy parsing and analysis
- **Comprehensive Context**: All execution attempts logged with full details
- **Real-time Monitoring**: CloudWatch integration for live monitoring
