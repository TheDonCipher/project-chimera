"""
Configuration Management System

Hierarchical configuration loading:
1. Environment variables (highest priority)
2. config.yaml file
3. Database configuration (future)
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path
import yaml
from pydantic import BaseModel, Field, validator
from decimal import Decimal


class RPCConfig(BaseModel):
    """RPC provider configuration"""
    primary_http: str = Field(..., description="Primary HTTP RPC endpoint")
    primary_ws: str = Field(..., description="Primary WebSocket RPC endpoint")
    backup_http: str = Field(..., description="Backup HTTP RPC endpoint")
    backup_ws: str = Field(..., description="Backup WebSocket RPC endpoint")
    archive_http: str = Field(..., description="Archive node HTTP endpoint")


class DatabaseConfig(BaseModel):
    """Database configuration"""
    host: str = Field(default="localhost")
    port: int = Field(default=5432)
    database: str = Field(default="chimera")
    user: str = Field(...)
    password: str = Field(...)
    pool_size: int = Field(default=20)
    max_overflow: int = Field(default=10)


class RedisConfig(BaseModel):
    """Redis cache configuration"""
    host: str = Field(default="localhost")
    port: int = Field(default=6379)
    password: Optional[str] = Field(default=None)
    db: int = Field(default=0)
    ttl_seconds: int = Field(default=60)


class ProtocolConfig(BaseModel):
    """Lending protocol configuration"""
    name: str
    address: str
    liquidation_threshold: Decimal
    liquidation_bonus: Decimal


class OracleConfig(BaseModel):
    """Oracle configuration"""
    chainlink_addresses: Dict[str, str] = Field(default_factory=dict)
    pyth_addresses: Dict[str, str] = Field(default_factory=dict)
    max_divergence_percent: Decimal = Field(default=Decimal("5.0"))
    max_price_movement_percent: Decimal = Field(default=Decimal("30.0"))


class DEXConfig(BaseModel):
    """DEX router configuration"""
    uniswap_v3_router: str
    uniswap_v3_quoter: str
    aerodrome_router: Optional[str] = None
    max_slippage_percent: Decimal = Field(default=Decimal("1.0"))


class SafetyLimits(BaseModel):
    """Safety limit configuration"""
    max_single_execution_usd: Decimal = Field(default=Decimal("500"))
    max_daily_volume_usd: Decimal = Field(default=Decimal("2500"))
    min_profit_usd: Decimal = Field(default=Decimal("50"))
    max_consecutive_failures: int = Field(default=3)
    
    # State transition thresholds
    throttle_inclusion_rate: Decimal = Field(default=Decimal("0.60"))
    throttle_accuracy: Decimal = Field(default=Decimal("0.90"))
    halt_inclusion_rate: Decimal = Field(default=Decimal("0.50"))
    halt_accuracy: Decimal = Field(default=Decimal("0.85"))


class ExecutionConfig(BaseModel):
    """Execution configuration"""
    operator_address: str = Field(...)
    chimera_contract_address: str = Field(...)
    base_l1_gas_oracle: str = Field(default="0x4200000000000000000000000000000000000015")
    
    # Bribe optimization
    baseline_bribe_percent: Decimal = Field(default=Decimal("15.0"))
    bribe_increase_percent: Decimal = Field(default=Decimal("5.0"))
    bribe_decrease_percent: Decimal = Field(default=Decimal("2.0"))
    max_bribe_percent: Decimal = Field(default=Decimal("40.0"))
    
    # Flash loan
    aave_v3_pool: str = Field(...)
    balancer_vault: Optional[str] = None
    flash_loan_premium_percent: Decimal = Field(default=Decimal("0.09"))


class MonitoringConfig(BaseModel):
    """Monitoring and alerting configuration"""
    cloudwatch_enabled: bool = Field(default=False)
    cloudwatch_region: str = Field(default="us-east-1")
    cloudwatch_namespace: str = Field(default="Chimera")
    
    alert_phone: Optional[str] = None
    alert_sms: Optional[str] = None
    alert_email: Optional[str] = None
    
    metrics_export_interval_seconds: int = Field(default=60)


class ChimeraConfig(BaseModel):
    """Main configuration model"""
    # Network
    chain_id: int = Field(default=8453)  # Base mainnet
    network_name: str = Field(default="base")
    
    # Components
    rpc: RPCConfig
    database: DatabaseConfig
    redis: RedisConfig
    protocols: Dict[str, ProtocolConfig]
    oracles: OracleConfig
    dex: DEXConfig
    safety: SafetyLimits
    execution: ExecutionConfig
    monitoring: MonitoringConfig
    
    # Operational
    scan_interval_seconds: int = Field(default=5)
    confirmation_blocks: int = Field(default=2)
    state_reconciliation_interval_blocks: int = Field(default=1)
    
    @validator('protocols')
    def validate_protocols(cls, v):
        if not v:
            raise ValueError("At least one protocol must be configured")
        return v


class ConfigLoader:
    """Configuration loader with hierarchical loading"""
    
    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or Path("config.yaml")
        self._config: Optional[ChimeraConfig] = None
    
    def load(self) -> ChimeraConfig:
        """Load configuration from all sources"""
        # Load from YAML file
        config_data = self._load_yaml()
        
        # Override with environment variables
        config_data = self._apply_env_overrides(config_data)
        
        # Validate and create config object
        self._config = ChimeraConfig(**config_data)
        
        return self._config
    
    def _load_yaml(self) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _apply_env_overrides(self, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides"""
        # Database credentials
        if os.getenv('DB_USER'):
            config_data.setdefault('database', {})['user'] = os.getenv('DB_USER')
        if os.getenv('DB_PASSWORD'):
            config_data.setdefault('database', {})['password'] = os.getenv('DB_PASSWORD')
        if os.getenv('DB_HOST'):
            config_data.setdefault('database', {})['host'] = os.getenv('DB_HOST')
        
        # Redis credentials
        if os.getenv('REDIS_HOST'):
            config_data.setdefault('redis', {})['host'] = os.getenv('REDIS_HOST')
        if os.getenv('REDIS_PASSWORD'):
            config_data.setdefault('redis', {})['password'] = os.getenv('REDIS_PASSWORD')
        
        # RPC endpoints
        if os.getenv('RPC_PRIMARY_HTTP'):
            config_data.setdefault('rpc', {})['primary_http'] = os.getenv('RPC_PRIMARY_HTTP')
        if os.getenv('RPC_PRIMARY_WS'):
            config_data.setdefault('rpc', {})['primary_ws'] = os.getenv('RPC_PRIMARY_WS')
        
        # Operator key (address only, key stored in AWS Secrets Manager)
        if os.getenv('OPERATOR_ADDRESS'):
            config_data.setdefault('execution', {})['operator_address'] = os.getenv('OPERATOR_ADDRESS')
        
        # Contract addresses
        if os.getenv('CHIMERA_CONTRACT'):
            config_data.setdefault('execution', {})['chimera_contract_address'] = os.getenv('CHIMERA_CONTRACT')
        
        # Monitoring
        if os.getenv('ALERT_EMAIL'):
            config_data.setdefault('monitoring', {})['alert_email'] = os.getenv('ALERT_EMAIL')
        
        return config_data
    
    @property
    def config(self) -> ChimeraConfig:
        """Get loaded configuration"""
        if self._config is None:
            raise RuntimeError("Configuration not loaded. Call load() first.")
        return self._config


# Global config instance
_config_loader: Optional[ConfigLoader] = None


def get_config() -> ChimeraConfig:
    """Get global configuration instance"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
        _config_loader.load()
    return _config_loader.config


def init_config(config_path: Optional[Path] = None) -> ChimeraConfig:
    """Initialize configuration with custom path"""
    global _config_loader
    _config_loader = ConfigLoader(config_path)
    return _config_loader.load()
