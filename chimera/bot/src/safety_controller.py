"""
SafetyController Module - Limit enforcement and state management

Enforces operational limits and manages system state transitions based on
performance metrics. Implements three-state machine: NORMAL, THROTTLED, HALTED.
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
from collections import deque
import random

from .types import (
    SystemState, ExecutionRecord, ExecutionStatus, PerformanceMetrics,
    SystemEvent, SafetyError, Bundle, Opportunity
)
from .config import ChimeraConfig, SafetyLimits
from .database import DatabaseManager, ExecutionModel, PerformanceMetricsModel, SystemEventModel

logger = logging.getLogger(__name__)


class SafetyController:
    """
    Safety controller for limit enforcement and state management.
    
    Responsibilities:
    - Maintain three-state machine (NORMAL/THROTTLED/HALTED)
    - Enforce execution limits (single, daily, minimum profit)
    - Track performance metrics (inclusion rate, simulation accuracy)
    - Trigger automatic state transitions
    - Record execution attempts
    """
    
    def __init__(self, config: ChimeraConfig, db_manager: DatabaseManager):
        self.config = config
        self.db_manager = db_manager
        self.limits = config.safety
        
        # State management
        self._current_state = SystemState.NORMAL
        self._state_lock_until: Optional[datetime] = None
        
        # Execution tracking
        self._consecutive_failures = 0
        self._daily_volume_usd = Decimal("0")
        self._daily_reset_time = self._get_next_midnight_utc()
        
        # Performance tracking (last 100 submissions)
        self._submission_history: deque = deque(maxlen=100)
        self._execution_history: deque = deque(maxlen=100)
        
        # Metrics cache
        self._last_metrics_calculation = datetime.utcnow()
        self._cached_metrics: Optional[PerformanceMetrics] = None
        
        logger.info(f"SafetyController initialized in {self._current_state} state")
    
    # ========================================================================
    # State Machine Management (Task 6.1)
    # ========================================================================
    
    @property
    def current_state(self) -> SystemState:
        """Get current system state"""
        return self._current_state
    
    def can_execute(self) -> bool:
        """
        Check if execution is allowed in current state.
        
        Returns:
            True if execution allowed, False otherwise
        """
        if self._current_state == SystemState.HALTED:
            return False
        
        if self._current_state == SystemState.THROTTLED:
            # 50% random skip in THROTTLED state
            return random.random() > 0.5
        
        return True  # NORMAL state

    def transition_state(
        self,
        new_state: SystemState,
        reason: str,
        metrics: Optional[PerformanceMetrics] = None
    ):
        """
        Transition to new system state.
        
        Args:
            new_state: Target state
            reason: Reason for transition
            metrics: Optional performance metrics context
        """
        if new_state == self._current_state:
            return
        
        old_state = self._current_state
        self._current_state = new_state
        
        # Log state transition
        event = SystemEvent(
            timestamp=datetime.utcnow(),
            event_type='state_transition',
            severity='CRITICAL' if new_state == SystemState.HALTED else 'HIGH',
            message=f"State transition: {old_state} → {new_state}",
            context={
                'old_state': old_state.value,
                'new_state': new_state.value,
                'reason': reason,
                'metrics': self._metrics_to_dict(metrics) if metrics else None
            }
        )
        
        self._log_system_event(event)
        
        logger.warning(
            f"STATE TRANSITION: {old_state} → {new_state}",
            extra={
                'reason': reason,
                'metrics': self._metrics_to_dict(metrics) if metrics else None
            }
        )
        
        # Send alerts for THROTTLED or HALTED
        if new_state in [SystemState.THROTTLED, SystemState.HALTED]:
            self._send_alert(event)
    
    def manual_resume(self, operator: str, reason: str):
        """
        Manually resume from HALTED state (operator intervention).
        
        Args:
            operator: Operator identifier
            reason: Reason for manual resume
        """
        if self._current_state != SystemState.HALTED:
            logger.warning(f"Manual resume called but state is {self._current_state}")
            return
        
        # Reset consecutive failures
        self._consecutive_failures = 0
        
        # Transition to NORMAL
        event = SystemEvent(
            timestamp=datetime.utcnow(),
            event_type='manual_resume',
            severity='HIGH',
            message=f"Manual resume by {operator}",
            context={
                'operator': operator,
                'reason': reason,
                'previous_state': SystemState.HALTED.value
            }
        )
        
        self._log_system_event(event)
        self._current_state = SystemState.NORMAL
        
        logger.info(f"System manually resumed by {operator}: {reason}")
    
    # ========================================================================
    # Limit Enforcement (Task 6.2)
    # ========================================================================
    
    def validate_execution(self, bundle: Bundle) -> tuple[bool, Optional[str]]:
        """
        Validate execution against all safety limits.
        
        Args:
            bundle: Bundle to validate
            
        Returns:
            (is_valid, rejection_reason)
        """
        # Check minimum profit
        if bundle.net_profit_usd < self.limits.min_profit_usd:
            reason = f"Net profit ${bundle.net_profit_usd} below minimum ${self.limits.min_profit_usd}"
            self._log_limit_violation('min_profit', bundle.opportunity, reason)
            return False, reason
        
        # Check single execution limit
        if bundle.net_profit_usd > self.limits.max_single_execution_usd:
            reason = f"Net profit ${bundle.net_profit_usd} exceeds single execution limit ${self.limits.max_single_execution_usd}"
            self._log_limit_violation('max_single_execution', bundle.opportunity, reason)
            return False, reason
        
        # Check daily volume limit
        self._reset_daily_volume_if_needed()
        
        projected_daily = self._daily_volume_usd + bundle.net_profit_usd
        if projected_daily > self.limits.max_daily_volume_usd:
            reason = f"Projected daily volume ${projected_daily} exceeds limit ${self.limits.max_daily_volume_usd}"
            self._log_limit_violation('max_daily_volume', bundle.opportunity, reason)
            return False, reason
        
        # Check consecutive failures
        if self._consecutive_failures >= self.limits.max_consecutive_failures:
            reason = f"Consecutive failures ({self._consecutive_failures}) at maximum"
            self._log_limit_violation('max_consecutive_failures', bundle.opportunity, reason)
            return False, reason
        
        return True, None
    
    def _reset_daily_volume_if_needed(self):
        """Reset daily volume counter at midnight UTC"""
        now = datetime.utcnow()
        if now >= self._daily_reset_time:
            logger.info(f"Resetting daily volume from ${self._daily_volume_usd} to $0")
            self._daily_volume_usd = Decimal("0")
            self._daily_reset_time = self._get_next_midnight_utc()
    
    def _get_next_midnight_utc(self) -> datetime:
        """Get next midnight UTC timestamp"""
        now = datetime.utcnow()
        tomorrow = now.date() + timedelta(days=1)
        return datetime.combine(tomorrow, datetime.min.time())
    
    def _log_limit_violation(self, limit_type: str, opportunity: Opportunity, reason: str):
        """Log limit violation event"""
        event = SystemEvent(
            timestamp=datetime.utcnow(),
            event_type='limit_violation',
            severity='MEDIUM',
            message=f"Limit violation: {limit_type}",
            context={
                'limit_type': limit_type,
                'reason': reason,
                'opportunity': {
                    'protocol': opportunity.position.protocol,
                    'user': opportunity.position.user,
                    'health_factor': str(opportunity.health_factor),
                    'estimated_profit': str(opportunity.estimated_net_profit_usd)
                }
            }
        )
        
        self._log_system_event(event)
        logger.info(f"Limit violation: {reason}")

    # ========================================================================
    # Performance Metrics Calculation (Task 6.3)
    # ========================================================================
    
    def calculate_metrics(self, force: bool = False) -> PerformanceMetrics:
        """
        Calculate performance metrics from recent execution history.
        
        Args:
            force: Force recalculation even if cached
            
        Returns:
            PerformanceMetrics object
        """
        now = datetime.utcnow()
        
        # Return cached metrics if recent (within 10 minutes)
        if not force and self._cached_metrics:
            age = (now - self._last_metrics_calculation).total_seconds()
            if age < 600:  # 10 minutes
                return self._cached_metrics
        
        # Calculate inclusion rate
        total_submissions = len(self._submission_history)
        successful_inclusions = sum(
            1 for record in self._submission_history
            if record.get('included', False)
        )
        
        inclusion_rate = (
            Decimal(successful_inclusions) / Decimal(total_submissions)
            if total_submissions > 0
            else Decimal("0")
        )
        
        # Calculate simulation accuracy
        total_executions = len(self._execution_history)
        accuracy_sum = Decimal("0")
        
        for record in self._execution_history:
            simulated = record.get('simulated_profit_usd', 0)
            actual = record.get('actual_profit_usd', 0)
            
            if simulated and simulated > 0:
                accuracy = Decimal(str(actual)) / Decimal(str(simulated))
                accuracy_sum += accuracy
        
        simulation_accuracy = (
            accuracy_sum / Decimal(total_executions)
            if total_executions > 0
            else Decimal("0")
        )
        
        # Calculate profitability
        total_profit = sum(
            Decimal(str(record.get('actual_profit_usd', 0)))
            for record in self._execution_history
        )
        
        average_profit = (
            total_profit / Decimal(total_executions)
            if total_executions > 0
            else Decimal("0")
        )
        
        # Create metrics object
        metrics = PerformanceMetrics(
            timestamp=now,
            window_size=100,
            total_submissions=total_submissions,
            successful_inclusions=successful_inclusions,
            inclusion_rate=inclusion_rate,
            total_executions=total_executions,
            simulation_accuracy=simulation_accuracy,
            total_profit_usd=total_profit,
            average_profit_usd=average_profit,
            consecutive_failures=self._consecutive_failures
        )
        
        # Cache metrics
        self._cached_metrics = metrics
        self._last_metrics_calculation = now
        
        # Persist to database
        self._persist_metrics(metrics)
        
        logger.info(
            f"Metrics calculated: inclusion={inclusion_rate:.2%}, "
            f"accuracy={simulation_accuracy:.2%}, "
            f"failures={self._consecutive_failures}"
        )
        
        return metrics
    
    def _persist_metrics(self, metrics: PerformanceMetrics):
        """Persist metrics to database"""
        try:
            with self.db_manager.get_session() as session:
                model = PerformanceMetricsModel(
                    timestamp=metrics.timestamp,
                    window_size=metrics.window_size,
                    total_submissions=metrics.total_submissions,
                    successful_inclusions=metrics.successful_inclusions,
                    inclusion_rate=metrics.inclusion_rate,
                    total_executions=metrics.total_executions,
                    simulation_accuracy=metrics.simulation_accuracy,
                    total_profit_usd=metrics.total_profit_usd,
                    average_profit_usd=metrics.average_profit_usd,
                    consecutive_failures=metrics.consecutive_failures
                )
                session.add(model)
        except Exception as e:
            logger.error(f"Failed to persist metrics: {e}")

    # ========================================================================
    # Automatic State Transitions (Task 6.4)
    # ========================================================================
    
    def check_and_apply_transitions(self):
        """
        Check performance metrics and apply state transitions if needed.
        
        State transition rules:
        - NORMAL → THROTTLED: inclusion 50-60% OR accuracy 85-90%
        - NORMAL → HALTED: inclusion <50% OR accuracy <85% OR failures ≥3
        - THROTTLED → NORMAL: inclusion >60% AND accuracy >90%
        - HALTED → NORMAL: Manual operator intervention only
        """
        # Calculate current metrics
        metrics = self.calculate_metrics()
        
        current = self._current_state
        
        # HALTED state requires manual intervention
        if current == SystemState.HALTED:
            return
        
        # Check for HALT conditions (highest priority)
        if self._should_halt(metrics):
            reason = self._get_halt_reason(metrics)
            self.transition_state(SystemState.HALTED, reason, metrics)
            return
        
        # Check for THROTTLE conditions
        if current == SystemState.NORMAL:
            if self._should_throttle(metrics):
                reason = self._get_throttle_reason(metrics)
                self.transition_state(SystemState.THROTTLED, reason, metrics)
                return
        
        # Check for NORMAL recovery from THROTTLED
        if current == SystemState.THROTTLED:
            if self._should_recover_to_normal(metrics):
                reason = "Performance recovered: inclusion >60% AND accuracy >90%"
                self.transition_state(SystemState.NORMAL, reason, metrics)
                return
    
    def _should_halt(self, metrics: PerformanceMetrics) -> bool:
        """Check if system should enter HALTED state"""
        # Consecutive failures
        if metrics.consecutive_failures >= self.limits.max_consecutive_failures:
            return True
        
        # Low inclusion rate
        if metrics.total_submissions >= 10:  # Minimum sample size
            if metrics.inclusion_rate < self.limits.halt_inclusion_rate:
                return True
        
        # Low simulation accuracy
        if metrics.total_executions >= 10:  # Minimum sample size
            if metrics.simulation_accuracy < self.limits.halt_accuracy:
                return True
        
        return False
    
    def _should_throttle(self, metrics: PerformanceMetrics) -> bool:
        """Check if system should enter THROTTLED state"""
        # Moderate inclusion rate
        if metrics.total_submissions >= 10:
            if (self.limits.halt_inclusion_rate <= metrics.inclusion_rate < 
                self.limits.throttle_inclusion_rate):
                return True
        
        # Moderate simulation accuracy
        if metrics.total_executions >= 10:
            if (self.limits.halt_accuracy <= metrics.simulation_accuracy < 
                self.limits.throttle_accuracy):
                return True
        
        return False
    
    def _should_recover_to_normal(self, metrics: PerformanceMetrics) -> bool:
        """Check if system should recover to NORMAL from THROTTLED"""
        if metrics.total_submissions < 10 or metrics.total_executions < 10:
            return False
        
        # Both conditions must be met
        inclusion_ok = metrics.inclusion_rate > self.limits.throttle_inclusion_rate
        accuracy_ok = metrics.simulation_accuracy > self.limits.throttle_accuracy
        
        return inclusion_ok and accuracy_ok
    
    def _get_halt_reason(self, metrics: PerformanceMetrics) -> str:
        """Get reason for HALT transition"""
        reasons = []
        
        if metrics.consecutive_failures >= self.limits.max_consecutive_failures:
            reasons.append(f"consecutive failures = {metrics.consecutive_failures}")
        
        if metrics.total_submissions >= 10:
            if metrics.inclusion_rate < self.limits.halt_inclusion_rate:
                reasons.append(f"inclusion rate = {metrics.inclusion_rate:.2%}")
        
        if metrics.total_executions >= 10:
            if metrics.simulation_accuracy < self.limits.halt_accuracy:
                reasons.append(f"simulation accuracy = {metrics.simulation_accuracy:.2%}")
        
        return "Performance degraded: " + ", ".join(reasons)
    
    def _get_throttle_reason(self, metrics: PerformanceMetrics) -> str:
        """Get reason for THROTTLE transition"""
        reasons = []
        
        if metrics.total_submissions >= 10:
            if (self.limits.halt_inclusion_rate <= metrics.inclusion_rate < 
                self.limits.throttle_inclusion_rate):
                reasons.append(f"inclusion rate = {metrics.inclusion_rate:.2%}")
        
        if metrics.total_executions >= 10:
            if (self.limits.halt_accuracy <= metrics.simulation_accuracy < 
                self.limits.throttle_accuracy):
                reasons.append(f"simulation accuracy = {metrics.simulation_accuracy:.2%}")
        
        return "Performance warning: " + ", ".join(reasons)

    # ========================================================================
    # Execution Tracking (Task 6.5)
    # ========================================================================
    
    def record_execution(self, record: ExecutionRecord):
        """
        Record execution attempt to database and update tracking.
        
        Args:
            record: ExecutionRecord to persist
        """
        # Update consecutive failures
        if record.included:
            self._consecutive_failures = 0
        elif record.bundle_submitted:
            self._consecutive_failures += 1
        
        # Update daily volume
        if record.included and record.actual_profit_usd:
            self._daily_volume_usd += record.actual_profit_usd
        
        # Add to submission history
        if record.bundle_submitted:
            self._submission_history.append({
                'timestamp': record.timestamp,
                'included': record.included,
                'tx_hash': record.tx_hash
            })
        
        # Add to execution history (only successful inclusions)
        if record.included:
            self._execution_history.append({
                'timestamp': record.timestamp,
                'simulated_profit_usd': record.simulated_profit_usd,
                'actual_profit_usd': record.actual_profit_usd
            })
        
        # Persist to database
        self._persist_execution(record)
        
        logger.info(
            f"Execution recorded: {record.status.value}, "
            f"included={record.included}, "
            f"consecutive_failures={self._consecutive_failures}"
        )
    
    def _persist_execution(self, record: ExecutionRecord):
        """Persist execution record to database within 1 second"""
        try:
            with self.db_manager.get_session() as session:
                model = ExecutionModel(
                    timestamp=record.timestamp,
                    block_number=record.block_number,
                    protocol=record.protocol,
                    borrower=record.borrower,
                    collateral_asset=record.collateral_asset,
                    debt_asset=record.debt_asset,
                    health_factor=record.health_factor,
                    simulation_success=record.simulation_success,
                    simulated_profit_wei=record.simulated_profit_wei,
                    simulated_profit_usd=record.simulated_profit_usd,
                    bundle_submitted=record.bundle_submitted,
                    tx_hash=record.tx_hash,
                    submission_path=record.submission_path,
                    bribe_wei=record.bribe_wei,
                    status=record.status,
                    included=record.included,
                    inclusion_block=record.inclusion_block,
                    actual_profit_wei=record.actual_profit_wei,
                    actual_profit_usd=record.actual_profit_usd,
                    operator_address=record.operator_address,
                    state_at_execution=record.state_at_execution,
                    rejection_reason=record.rejection_reason,
                    error_message=record.error_message
                )
                session.add(model)
                
            logger.debug(f"Execution persisted to database: {record.tx_hash or 'no_tx'}")
            
        except Exception as e:
            logger.error(f"Failed to persist execution record: {e}")
            # Don't raise - logging failure shouldn't stop execution
    
    def get_recent_executions(self, limit: int = 100) -> List[ExecutionRecord]:
        """
        Get recent execution records from database.
        
        Args:
            limit: Maximum number of records to return
            
        Returns:
            List of ExecutionRecord objects
        """
        try:
            with self.db_manager.get_session() as session:
                models = (
                    session.query(ExecutionModel)
                    .order_by(ExecutionModel.timestamp.desc())
                    .limit(limit)
                    .all()
                )
                
                return [self._model_to_record(m) for m in models]
                
        except Exception as e:
            logger.error(f"Failed to fetch execution records: {e}")
            return []
    
    def _model_to_record(self, model: ExecutionModel) -> ExecutionRecord:
        """Convert database model to ExecutionRecord"""
        return ExecutionRecord(
            timestamp=model.timestamp,
            block_number=model.block_number,
            protocol=model.protocol,
            borrower=model.borrower,
            collateral_asset=model.collateral_asset,
            debt_asset=model.debt_asset,
            health_factor=model.health_factor,
            simulation_success=model.simulation_success,
            simulated_profit_wei=model.simulated_profit_wei,
            simulated_profit_usd=model.simulated_profit_usd,
            bundle_submitted=model.bundle_submitted,
            tx_hash=model.tx_hash,
            submission_path=model.submission_path,
            bribe_wei=model.bribe_wei,
            status=model.status,
            included=model.included,
            inclusion_block=model.inclusion_block,
            actual_profit_wei=model.actual_profit_wei,
            actual_profit_usd=model.actual_profit_usd,
            operator_address=model.operator_address,
            state_at_execution=model.state_at_execution,
            rejection_reason=model.rejection_reason,
            error_message=model.error_message
        )
    
    # ========================================================================
    # Helper Methods
    # ========================================================================
    
    def _log_system_event(self, event: SystemEvent):
        """Log system event to database"""
        try:
            import json
            
            with self.db_manager.get_session() as session:
                model = SystemEventModel(
                    timestamp=event.timestamp,
                    event_type=event.event_type,
                    severity=event.severity,
                    message=event.message,
                    context=json.dumps(event.context) if event.context else None
                )
                session.add(model)
                
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    def _send_alert(self, event: SystemEvent):
        """Send alert for critical events"""
        # TODO: Integrate with CloudWatch/PagerDuty/SNS
        logger.critical(
            f"ALERT: {event.message}",
            extra={'event': event.to_dict()}
        )
    
    def _metrics_to_dict(self, metrics: Optional[PerformanceMetrics]) -> Optional[Dict[str, Any]]:
        """Convert metrics to dictionary"""
        if not metrics:
            return None
        
        return {
            'inclusion_rate': float(metrics.inclusion_rate),
            'simulation_accuracy': float(metrics.simulation_accuracy),
            'total_submissions': metrics.total_submissions,
            'total_executions': metrics.total_executions,
            'consecutive_failures': metrics.consecutive_failures,
            'total_profit_usd': float(metrics.total_profit_usd),
            'average_profit_usd': float(metrics.average_profit_usd)
        }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current safety controller status"""
        metrics = self.calculate_metrics()
        
        return {
            'state': self._current_state.value,
            'consecutive_failures': self._consecutive_failures,
            'daily_volume_usd': float(self._daily_volume_usd),
            'daily_limit_usd': float(self.limits.max_daily_volume_usd),
            'daily_reset_time': self._daily_reset_time.isoformat(),
            'metrics': self._metrics_to_dict(metrics),
            'limits': {
                'max_single_execution_usd': float(self.limits.max_single_execution_usd),
                'max_daily_volume_usd': float(self.limits.max_daily_volume_usd),
                'min_profit_usd': float(self.limits.min_profit_usd),
                'max_consecutive_failures': self.limits.max_consecutive_failures
            }
        }