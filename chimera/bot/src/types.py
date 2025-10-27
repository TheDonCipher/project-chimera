"""
Core Data Models and Types

Defines all core data structures used throughout the system.
"""

from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, Field, validator
from dataclasses import dataclass


# ============================================================================
# Enums
# ============================================================================

class SystemState(str, Enum):
    """System operational state"""
    NORMAL = "NORMAL"          # Full operation (100% execution rate)
    THROTTLED = "THROTTLED"    # Reduced operation (50% execution rate)
    HALTED = "HALTED"          # No execution (manual intervention required)


class SubmissionPath(str, Enum):
    """Transaction submission path"""
    MEMPOOL = "mempool"              # Direct mempool submission
    BUILDER = "builder"              # Base-native builder
    PRIVATE_RPC = "private_rpc"      # Private RPC endpoint


class ExecutionStatus(str, Enum):
    """Execution attempt status"""
    PENDING = "pending"              # Submitted, awaiting inclusion
    INCLUDED = "included"            # Successfully included in block
    FAILED = "failed"                # Failed to execute
    REJECTED = "rejected"            # Rejected before submission
    REVERTED = "reverted"            # Transaction reverted on-chain


# ============================================================================
# Error Types
# ============================================================================

class ChimeraError(Exception):
    """Base exception for all Chimera errors"""
    pass


class ConfigurationError(ChimeraError):
    """Configuration validation or loading error"""
    pass


class StateError(ChimeraError):
    """State synchronization or divergence error"""
    pass


class SimulationError(ChimeraError):
    """Transaction simulation error"""
    pass


class ExecutionError(ChimeraError):
    """Transaction execution error"""
    pass


class SafetyError(ChimeraError):
    """Safety limit or validation error"""
    pass


class DatabaseError(ChimeraError):
    """Database connection or query error"""
    pass


class RPCError(ChimeraError):
    """RPC provider connection or response error"""
    pass


# ============================================================================
# Core Data Models
# ============================================================================

class Position(BaseModel):
    """Lending position data model"""
    protocol: str = Field(..., description="Protocol name (moonwell, seamless)")
    user: str = Field(..., description="User address (checksummed)")
    collateral_asset: str = Field(..., description="Collateral token address")
    collateral_amount: int = Field(..., description="Collateral amount in wei")
    debt_asset: str = Field(..., description="Debt token address")
    debt_amount: int = Field(..., description="Debt amount in wei")
    liquidation_threshold: Decimal = Field(..., description="Protocol liquidation threshold")
    last_update_block: int = Field(..., description="Block number of last update")
    blocks_unhealthy: int = Field(default=0, description="Consecutive blocks with health_factor < 1.0")
    
    @validator('user', 'collateral_asset', 'debt_asset')
    def validate_address(cls, v):
        """Validate Ethereum address format"""
        if not v.startswith('0x') or len(v) != 42:
            raise ValueError(f"Invalid Ethereum address: {v}")
        return v
    
    @validator('collateral_amount', 'debt_amount')
    def validate_positive(cls, v):
        """Validate positive amounts"""
        if v <= 0:
            raise ValueError("Amount must be positive")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return self.dict()
    
    class Config:
        json_encoders = {
            Decimal: str
        }


class Opportunity(BaseModel):
    """Liquidation opportunity data model"""
    position: Position = Field(..., description="Underlying position")
    health_factor: Decimal = Field(..., description="Calculated health factor")
    collateral_price_usd: Decimal = Field(..., description="Collateral price in USD")
    debt_price_usd: Decimal = Field(..., description="Debt price in USD")
    liquidation_bonus: Decimal = Field(..., description="Protocol liquidation bonus")
    estimated_gross_profit_usd: Decimal = Field(..., description="Rough profit estimate")
    estimated_net_profit_usd: Decimal = Field(..., description="Estimated profit after costs")
    detected_at_block: int = Field(..., description="Block number when detected")
    detected_at_timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('health_factor')
    def validate_health_factor(cls, v):
        """Validate health factor is liquidatable"""
        if v >= Decimal("1.0"):
            raise ValueError(f"Health factor {v} is not liquidatable (must be < 1.0)")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = self.dict()
        data['position'] = self.position.to_dict()
        return data
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat()
        }


class Transaction(BaseModel):
    """Transaction data model"""
    to: str = Field(..., description="Contract address")
    data: str = Field(..., description="Encoded function call")
    value: int = Field(default=0, description="ETH value in wei")
    gas_limit: int = Field(..., description="Gas limit")
    max_fee_per_gas: int = Field(..., description="Max fee per gas in wei")
    max_priority_fee_per_gas: int = Field(..., description="Priority fee in wei")
    nonce: int = Field(..., description="Transaction nonce")
    chain_id: int = Field(default=8453, description="Chain ID (Base mainnet)")
    
    class Config:
        json_encoders = {
            int: str
        }


class Bundle(BaseModel):
    """Transaction bundle with simulation results"""
    opportunity: Opportunity = Field(..., description="Underlying opportunity")
    transaction: Transaction = Field(..., description="Transaction data")
    
    # Simulation results
    simulated_profit_wei: int = Field(..., description="Simulated profit in wei")
    simulated_profit_usd: Decimal = Field(..., description="Simulated profit in USD")
    
    # Cost breakdown
    gas_estimate: int = Field(..., description="Estimated gas usage")
    l2_gas_cost_usd: Decimal = Field(..., description="L2 execution cost")
    l1_data_cost_usd: Decimal = Field(..., description="L1 data posting cost")
    bribe_usd: Decimal = Field(..., description="Builder bribe")
    flash_loan_cost_usd: Decimal = Field(..., description="Flash loan premium")
    slippage_cost_usd: Decimal = Field(..., description="DEX slippage cost")
    total_cost_usd: Decimal = Field(..., description="Total cost")
    net_profit_usd: Decimal = Field(..., description="Net profit after all costs")
    
    # Submission details
    submission_path: SubmissionPath = Field(..., description="Submission path")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('net_profit_usd')
    def validate_profitable(cls, v):
        """Validate bundle is profitable"""
        if v <= Decimal("0"):
            raise ValueError(f"Bundle is not profitable: net_profit={v}")
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        data = self.dict()
        data['opportunity'] = self.opportunity.to_dict()
        data['transaction'] = self.transaction.dict()
        return data
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            int: str
        }


class ExecutionRecord(BaseModel):
    """Complete execution record for database storage"""
    # Timing
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    block_number: int = Field(..., description="Block number when executed")
    
    # Position details
    protocol: str
    borrower: str
    collateral_asset: str
    debt_asset: str
    health_factor: Decimal
    
    # Simulation
    simulation_success: bool
    simulated_profit_wei: Optional[int] = None
    simulated_profit_usd: Optional[Decimal] = None
    
    # Submission
    bundle_submitted: bool
    tx_hash: Optional[str] = None
    submission_path: Optional[SubmissionPath] = None
    bribe_wei: Optional[int] = None
    
    # Outcome
    status: ExecutionStatus
    included: bool = False
    inclusion_block: Optional[int] = None
    actual_profit_wei: Optional[int] = None
    actual_profit_usd: Optional[Decimal] = None
    
    # Context
    operator_address: str
    state_at_execution: SystemState
    rejection_reason: Optional[str] = None
    error_message: Optional[str] = None
    
    class Config:
        json_encoders = {
            Decimal: str,
            datetime: lambda v: v.isoformat(),
            int: str
        }


# ============================================================================
# State Tracking Models
# ============================================================================

@dataclass
class StateDivergence:
    """State divergence record"""
    timestamp: datetime
    block_number: int
    protocol: str
    user: str
    field: str  # 'collateral_amount' or 'debt_amount'
    cached_value: int
    canonical_value: int
    divergence_bps: int  # Basis points
    
    def __post_init__(self):
        """Calculate divergence in basis points"""
        if self.canonical_value > 0:
            self.divergence_bps = abs(
                (self.cached_value - self.canonical_value) * 10000 // self.canonical_value
            )
        else:
            self.divergence_bps = 0


@dataclass
class PerformanceMetrics:
    """Performance metrics for safety controller"""
    timestamp: datetime
    window_size: int  # Number of submissions in window
    
    # Inclusion metrics
    total_submissions: int
    successful_inclusions: int
    inclusion_rate: Decimal
    
    # Accuracy metrics
    total_executions: int
    simulation_accuracy: Decimal  # actual_profit / simulated_profit
    
    # Profitability
    total_profit_usd: Decimal
    average_profit_usd: Decimal
    
    # Failures
    consecutive_failures: int
    
    def __post_init__(self):
        """Calculate derived metrics"""
        if self.total_submissions > 0:
            self.inclusion_rate = Decimal(self.successful_inclusions) / Decimal(self.total_submissions)
        else:
            self.inclusion_rate = Decimal("0")


@dataclass
class SystemEvent:
    """System event for logging"""
    timestamp: datetime
    event_type: str  # 'state_transition', 'limit_violation', 'error', etc.
    severity: str  # 'CRITICAL', 'HIGH', 'MEDIUM', 'LOW'
    message: str
    context: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat(),
            'event_type': self.event_type,
            'severity': self.severity,
            'message': self.message,
            'context': self.context
        }
