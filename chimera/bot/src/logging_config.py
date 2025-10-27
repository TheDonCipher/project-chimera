"""
Logging Infrastructure

Structured JSON logging with CloudWatch integration, log rotation, and retention policies.
Implements Requirement 7.7: Comprehensive audit trail and performance monitoring.
"""

import logging
import logging.handlers
import json
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime
import structlog
from structlog.types import EventDict, Processor
import boto3
from botocore.exceptions import ClientError


# ============================================================================
# Custom Processors
# ============================================================================

def add_module_name(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add module name to log record"""
    event_dict["module"] = logger.name
    return event_dict


def add_timestamp(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add ISO 8601 timestamp to log record"""
    event_dict["timestamp"] = datetime.utcnow().isoformat() + "Z"
    return event_dict


def add_log_level(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Add log level to log record"""
    event_dict["level"] = method_name.upper()
    return event_dict


def add_context(logger: logging.Logger, method_name: str, event_dict: EventDict) -> EventDict:
    """Ensure context field exists"""
    if "context" not in event_dict:
        event_dict["context"] = {}
    return event_dict


# ============================================================================
# CloudWatch Handler
# ============================================================================

class CloudWatchHandler(logging.Handler):
    """
    Custom handler for sending logs to AWS CloudWatch Logs.
    
    Batches log events and sends them periodically to reduce API calls.
    """
    
    def __init__(
        self,
        log_group: str,
        log_stream: str,
        region: str = "us-east-1",
        batch_size: int = 100,
        batch_interval: float = 5.0
    ):
        super().__init__()
        self.log_group = log_group
        self.log_stream = log_stream
        self.region = region
        self.batch_size = batch_size
        self.batch_interval = batch_interval
        
        # Initialize CloudWatch client
        try:
            self.client = boto3.client('logs', region_name=region)
            self._ensure_log_group_exists()
            self._ensure_log_stream_exists()
            self.sequence_token: Optional[str] = None
            self.batch: list = []
            self.enabled = True
        except Exception as e:
            # Fail gracefully if CloudWatch is not available
            print(f"CloudWatch initialization failed: {e}", file=sys.stderr)
            self.enabled = False
    
    def _ensure_log_group_exists(self):
        """Create log group if it doesn't exist"""
        try:
            self.client.create_log_group(logGroupName=self.log_group)
            # Set retention policy to 30 days for hot logs
            self.client.put_retention_policy(
                logGroupName=self.log_group,
                retentionInDays=30
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def _ensure_log_stream_exists(self):
        """Create log stream if it doesn't exist"""
        try:
            self.client.create_log_stream(
                logGroupName=self.log_group,
                logStreamName=self.log_stream
            )
        except ClientError as e:
            if e.response['Error']['Code'] != 'ResourceAlreadyExistsException':
                raise
    
    def emit(self, record: logging.LogRecord):
        """Add log record to batch"""
        if not self.enabled:
            return
        
        try:
            # Format the log record
            log_entry = self.format(record)
            
            # Add to batch
            self.batch.append({
                'timestamp': int(datetime.utcnow().timestamp() * 1000),
                'message': log_entry
            })
            
            # Send batch if size threshold reached
            if len(self.batch) >= self.batch_size:
                self.flush()
        
        except Exception as e:
            # Don't let logging errors crash the application
            print(f"CloudWatch emit error: {e}", file=sys.stderr)
    
    def flush(self):
        """Send batched logs to CloudWatch"""
        if not self.enabled or not self.batch:
            return
        
        try:
            # Sort by timestamp (required by CloudWatch)
            self.batch.sort(key=lambda x: x['timestamp'])
            
            # Prepare request
            kwargs = {
                'logGroupName': self.log_group,
                'logStreamName': self.log_stream,
                'logEvents': self.batch
            }
            
            if self.sequence_token:
                kwargs['sequenceToken'] = self.sequence_token
            
            # Send to CloudWatch
            response = self.client.put_log_events(**kwargs)
            self.sequence_token = response.get('nextSequenceToken')
            
            # Clear batch
            self.batch = []
        
        except Exception as e:
            print(f"CloudWatch flush error: {e}", file=sys.stderr)
            # Clear batch to prevent memory buildup
            self.batch = []
    
    def close(self):
        """Flush remaining logs before closing"""
        self.flush()
        super().close()


# ============================================================================
# Logging Configuration
# ============================================================================

class LoggingConfig:
    """
    Centralized logging configuration for the Chimera system.
    
    Features:
    - Structured JSON logging
    - Multiple output handlers (console, file, CloudWatch)
    - Log rotation and retention
    - Module-specific loggers
    """
    
    def __init__(
        self,
        log_dir: Path = Path("logs"),
        log_level: str = "INFO",
        enable_cloudwatch: bool = False,
        cloudwatch_region: str = "us-east-1",
        cloudwatch_log_group: str = "Chimera",
        cloudwatch_log_stream: Optional[str] = None
    ):
        self.log_dir = log_dir
        self.log_level = log_level.upper()
        self.enable_cloudwatch = enable_cloudwatch
        self.cloudwatch_region = cloudwatch_region
        self.cloudwatch_log_group = cloudwatch_log_group
        self.cloudwatch_log_stream = cloudwatch_log_stream or f"bot-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}"
        
        # Ensure log directory exists
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure structlog
        self._configure_structlog()
        
        # Configure standard library logging
        self._configure_stdlib_logging()
    
    def _configure_structlog(self):
        """Configure structlog with custom processors"""
        processors: list[Processor] = [
            structlog.contextvars.merge_contextvars,
            add_module_name,
            add_timestamp,
            add_log_level,
            add_context,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer()
        ]
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.make_filtering_bound_logger(
                logging.getLevelName(self.log_level)
            ),
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    
    def _configure_stdlib_logging(self):
        """Configure standard library logging handlers"""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Remove existing handlers
        root_logger.handlers.clear()
        
        # Console handler (JSON format)
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(self.log_level)
        console_handler.setFormatter(logging.Formatter('%(message)s'))
        root_logger.addHandler(console_handler)
        
        # File handler with rotation (JSON format)
        file_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "chimera.log",
            maxBytes=100 * 1024 * 1024,  # 100 MB
            backupCount=10,  # Keep 10 backup files
            encoding='utf-8'
        )
        file_handler.setLevel(self.log_level)
        file_handler.setFormatter(logging.Formatter('%(message)s'))
        root_logger.addHandler(file_handler)
        
        # Execution log handler (separate file for audit trail)
        execution_handler = logging.handlers.RotatingFileHandler(
            filename=self.log_dir / "executions.log",
            maxBytes=100 * 1024 * 1024,  # 100 MB
            backupCount=50,  # Keep more backups for audit trail
            encoding='utf-8'
        )
        execution_handler.setLevel(logging.INFO)
        execution_handler.setFormatter(logging.Formatter('%(message)s'))
        execution_handler.addFilter(lambda record: 'execution' in record.name.lower())
        root_logger.addHandler(execution_handler)
        
        # CloudWatch handler (if enabled)
        if self.enable_cloudwatch:
            cloudwatch_handler = CloudWatchHandler(
                log_group=self.cloudwatch_log_group,
                log_stream=self.cloudwatch_log_stream,
                region=self.cloudwatch_region,
                batch_size=100,
                batch_interval=5.0
            )
            cloudwatch_handler.setLevel(logging.INFO)
            cloudwatch_handler.setFormatter(logging.Formatter('%(message)s'))
            root_logger.addHandler(cloudwatch_handler)
    
    def get_logger(self, name: str) -> structlog.stdlib.BoundLogger:
        """
        Get a logger instance for a specific module.
        
        Args:
            name: Module name (e.g., 'state_engine', 'opportunity_detector')
        
        Returns:
            Configured structlog logger
        """
        return structlog.get_logger(name)


# ============================================================================
# Global Logger Instance
# ============================================================================

_logging_config: Optional[LoggingConfig] = None


def init_logging(
    log_dir: Path = Path("logs"),
    log_level: str = "INFO",
    enable_cloudwatch: bool = False,
    cloudwatch_region: str = "us-east-1",
    cloudwatch_log_group: str = "Chimera",
    cloudwatch_log_stream: Optional[str] = None
) -> LoggingConfig:
    """
    Initialize global logging configuration.
    
    Args:
        log_dir: Directory for log files
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_cloudwatch: Enable CloudWatch integration
        cloudwatch_region: AWS region for CloudWatch
        cloudwatch_log_group: CloudWatch log group name
        cloudwatch_log_stream: CloudWatch log stream name (auto-generated if None)
    
    Returns:
        LoggingConfig instance
    """
    global _logging_config
    _logging_config = LoggingConfig(
        log_dir=log_dir,
        log_level=log_level,
        enable_cloudwatch=enable_cloudwatch,
        cloudwatch_region=cloudwatch_region,
        cloudwatch_log_group=cloudwatch_log_group,
        cloudwatch_log_stream=cloudwatch_log_stream
    )
    return _logging_config


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Get a logger instance for a specific module.
    
    Args:
        name: Module name
    
    Returns:
        Configured structlog logger
    
    Raises:
        RuntimeError: If logging not initialized
    """
    global _logging_config
    if _logging_config is None:
        # Auto-initialize with defaults if not explicitly initialized
        init_logging()
    return _logging_config.get_logger(name)


# ============================================================================
# Convenience Functions
# ============================================================================

def log_execution_attempt(
    logger: structlog.stdlib.BoundLogger,
    execution_record: Dict[str, Any]
):
    """
    Log an execution attempt with complete context.
    
    This creates an immutable audit trail entry as required by Requirement 7.7.
    
    Args:
        logger: Logger instance
        execution_record: Complete execution record dictionary
    """
    logger.info(
        "execution_attempt",
        context={
            "event_type": "execution_attempt",
            "execution_record": execution_record
        }
    )


def log_state_transition(
    logger: structlog.stdlib.BoundLogger,
    from_state: str,
    to_state: str,
    reason: str,
    metrics: Optional[Dict[str, Any]] = None
):
    """
    Log a system state transition.
    
    Args:
        logger: Logger instance
        from_state: Previous state
        to_state: New state
        reason: Reason for transition
        metrics: Optional performance metrics
    """
    logger.warning(
        "state_transition",
        context={
            "event_type": "state_transition",
            "from_state": from_state,
            "to_state": to_state,
            "reason": reason,
            "metrics": metrics or {}
        }
    )


def log_state_divergence(
    logger: structlog.stdlib.BoundLogger,
    protocol: str,
    user: str,
    field: str,
    cached_value: int,
    canonical_value: int,
    divergence_bps: int,
    block_number: int
):
    """
    Log a state divergence event.
    
    Args:
        logger: Logger instance
        protocol: Protocol name
        user: User address
        field: Field name (collateral_amount, debt_amount)
        cached_value: Cached value
        canonical_value: Canonical value from blockchain
        divergence_bps: Divergence in basis points
        block_number: Block number
    """
    logger.error(
        "state_divergence",
        context={
            "event_type": "state_divergence",
            "protocol": protocol,
            "user": user,
            "field": field,
            "cached_value": cached_value,
            "canonical_value": canonical_value,
            "divergence_bps": divergence_bps,
            "block_number": block_number
        }
    )


def log_safety_violation(
    logger: structlog.stdlib.BoundLogger,
    violation_type: str,
    current_value: Any,
    limit_value: Any,
    context: Optional[Dict[str, Any]] = None
):
    """
    Log a safety limit violation.
    
    Args:
        logger: Logger instance
        violation_type: Type of violation (e.g., 'max_single_execution', 'max_daily_volume')
        current_value: Current value that violated the limit
        limit_value: Limit that was violated
        context: Additional context
    """
    logger.warning(
        "safety_violation",
        context={
            "event_type": "safety_violation",
            "violation_type": violation_type,
            "current_value": current_value,
            "limit_value": limit_value,
            **(context or {})
        }
    )


def log_performance_metrics(
    logger: structlog.stdlib.BoundLogger,
    metrics: Dict[str, Any]
):
    """
    Log performance metrics.
    
    Args:
        logger: Logger instance
        metrics: Performance metrics dictionary
    """
    logger.info(
        "performance_metrics",
        context={
            "event_type": "performance_metrics",
            "metrics": metrics
        }
    )
