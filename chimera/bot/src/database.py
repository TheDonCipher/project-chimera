"""
Database Schema and Connection Handling

SQLAlchemy models and connection management with automatic reconnection.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from contextlib import contextmanager
import logging

from sqlalchemy import (
    create_engine, Column, Integer, String, DateTime, Boolean, 
    Numeric, Text, Index, Enum as SQLEnum
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import OperationalError, DisconnectionError
import redis
from redis.exceptions import ConnectionError as RedisConnectionError

from .types import SystemState, SubmissionPath, ExecutionStatus, DatabaseError
from .config import DatabaseConfig, RedisConfig

logger = logging.getLogger(__name__)

Base = declarative_base()


# ============================================================================
# SQLAlchemy Models
# ============================================================================

class ExecutionModel(Base):
    """Execution attempts table"""
    __tablename__ = 'executions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Timing
    timestamp = Column(DateTime, nullable=False, index=True)
    block_number = Column(Integer, nullable=False, index=True)
    
    # Position details
    protocol = Column(String(50), nullable=False, index=True)
    borrower = Column(String(42), nullable=False, index=True)
    collateral_asset = Column(String(42), nullable=False)
    debt_asset = Column(String(42), nullable=False)
    health_factor = Column(Numeric(10, 6), nullable=False)
    
    # Simulation
    simulation_success = Column(Boolean, nullable=False)
    simulated_profit_wei = Column(Numeric(78, 0), nullable=True)
    simulated_profit_usd = Column(Numeric(20, 2), nullable=True)
    
    # Submission
    bundle_submitted = Column(Boolean, nullable=False)
    tx_hash = Column(String(66), nullable=True, index=True)
    submission_path = Column(SQLEnum(SubmissionPath), nullable=True)
    bribe_wei = Column(Numeric(78, 0), nullable=True)
    
    # Outcome
    status = Column(SQLEnum(ExecutionStatus), nullable=False, index=True)
    included = Column(Boolean, nullable=False, default=False, index=True)
    inclusion_block = Column(Integer, nullable=True)
    actual_profit_wei = Column(Numeric(78, 0), nullable=True)
    actual_profit_usd = Column(Numeric(20, 2), nullable=True)
    
    # Context
    operator_address = Column(String(42), nullable=False)
    state_at_execution = Column(SQLEnum(SystemState), nullable=False)
    rejection_reason = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_timestamp_status', 'timestamp', 'status'),
        Index('idx_protocol_included', 'protocol', 'included'),
        Index('idx_block_included', 'block_number', 'included'),
    )


class StateDivergenceModel(Base):
    """State divergence events table"""
    __tablename__ = 'state_divergences'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    block_number = Column(Integer, nullable=False, index=True)
    protocol = Column(String(50), nullable=False)
    user = Column(String(42), nullable=False)
    field = Column(String(50), nullable=False)  # 'collateral_amount' or 'debt_amount'
    cached_value = Column(Numeric(78, 0), nullable=False)
    canonical_value = Column(Numeric(78, 0), nullable=False)
    divergence_bps = Column(Integer, nullable=False)  # Basis points
    
    __table_args__ = (
        Index('idx_timestamp_divergence', 'timestamp', 'divergence_bps'),
    )


class PerformanceMetricsModel(Base):
    """Performance metrics snapshots table"""
    __tablename__ = 'performance_metrics'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    window_size = Column(Integer, nullable=False)
    
    # Inclusion metrics
    total_submissions = Column(Integer, nullable=False)
    successful_inclusions = Column(Integer, nullable=False)
    inclusion_rate = Column(Numeric(5, 4), nullable=False)
    
    # Accuracy metrics
    total_executions = Column(Integer, nullable=False)
    simulation_accuracy = Column(Numeric(5, 4), nullable=False)
    
    # Profitability
    total_profit_usd = Column(Numeric(20, 2), nullable=False)
    average_profit_usd = Column(Numeric(20, 2), nullable=False)
    
    # Failures
    consecutive_failures = Column(Integer, nullable=False)


class SystemEventModel(Base):
    """System events table"""
    __tablename__ = 'system_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    context = Column(Text, nullable=True)  # JSON string
    
    __table_args__ = (
        Index('idx_timestamp_severity', 'timestamp', 'severity'),
    )


# ============================================================================
# Database Connection Manager
# ============================================================================

class DatabaseManager:
    """Database connection manager with automatic reconnection"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """Initialize SQLAlchemy engine with connection pooling"""
        connection_string = (
            f"postgresql://{self.config.user}:{self.config.password}"
            f"@{self.config.host}:{self.config.port}/{self.config.database}"
        )
        
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            pool_pre_ping=True,  # Verify connections before using
            pool_recycle=3600,   # Recycle connections after 1 hour
            echo=False
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        logger.info("Database engine initialized")
    
    def create_tables(self):
        """Create all tables if they don't exist"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("Database tables created/verified")
        except Exception as e:
            logger.error(f"Failed to create tables: {e}")
            raise DatabaseError(f"Table creation failed: {e}")
    
    @contextmanager
    def get_session(self) -> Session:
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except (OperationalError, DisconnectionError) as e:
            session.rollback()
            logger.error(f"Database connection error: {e}")
            # Attempt to reconnect
            self._initialize_engine()
            raise DatabaseError(f"Database connection lost: {e}")
        except Exception as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise DatabaseError(f"Database operation failed: {e}")
        finally:
            session.close()
    
    def health_check(self) -> bool:
        """Check database connection health"""
        try:
            with self.get_session() as session:
                session.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


# ============================================================================
# Redis Connection Manager
# ============================================================================

class RedisManager:
    """Redis connection manager with fallback to in-memory cache"""
    
    def __init__(self, config: RedisConfig):
        self.config = config
        self.client: Optional[redis.Redis] = None
        self._in_memory_cache: Dict[str, Any] = {}
        self._use_fallback = False
        self._connect()
    
    def _connect(self):
        """Connect to Redis"""
        try:
            self.client = redis.Redis(
                host=self.config.host,
                port=self.config.port,
                password=self.config.password,
                db=self.config.db,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_keepalive=True,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            self._use_fallback = False
            logger.info("Redis connection established")
        except RedisConnectionError as e:
            logger.warning(f"Redis connection failed, using in-memory fallback: {e}")
            self._use_fallback = True
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """Set key-value with optional TTL"""
        ttl = ttl or self.config.ttl_seconds
        
        if self._use_fallback:
            self._in_memory_cache[key] = (value, datetime.utcnow())
            return True
        
        try:
            self.client.setex(key, ttl, value)
            return True
        except RedisConnectionError:
            logger.warning("Redis set failed, switching to fallback")
            self._use_fallback = True
            self._in_memory_cache[key] = (value, datetime.utcnow())
            return True
    
    def get(self, key: str) -> Optional[str]:
        """Get value by key"""
        if self._use_fallback:
            if key in self._in_memory_cache:
                value, timestamp = self._in_memory_cache[key]
                # Check TTL
                age = (datetime.utcnow() - timestamp).total_seconds()
                if age < self.config.ttl_seconds:
                    return value
                else:
                    del self._in_memory_cache[key]
            return None
        
        try:
            return self.client.get(key)
        except RedisConnectionError:
            logger.warning("Redis get failed, switching to fallback")
            self._use_fallback = True
            return self.get(key)  # Retry with fallback
    
    def delete(self, key: str) -> bool:
        """Delete key"""
        if self._use_fallback:
            if key in self._in_memory_cache:
                del self._in_memory_cache[key]
            return True
        
        try:
            self.client.delete(key)
            return True
        except RedisConnectionError:
            logger.warning("Redis delete failed, switching to fallback")
            self._use_fallback = True
            if key in self._in_memory_cache:
                del self._in_memory_cache[key]
            return True
    
    def keys(self, pattern: str) -> List[str]:
        """Get keys matching pattern"""
        if self._use_fallback:
            import fnmatch
            return [k for k in self._in_memory_cache.keys() if fnmatch.fnmatch(k, pattern)]
        
        try:
            return self.client.keys(pattern)
        except RedisConnectionError:
            logger.warning("Redis keys failed, switching to fallback")
            self._use_fallback = True
            return self.keys(pattern)  # Retry with fallback
    
    def health_check(self) -> bool:
        """Check Redis connection health"""
        if self._use_fallback:
            return False
        
        try:
            self.client.ping()
            return True
        except RedisConnectionError:
            logger.warning("Redis health check failed")
            self._use_fallback = True
            return False
    
    def reconnect(self):
        """Attempt to reconnect to Redis"""
        if self._use_fallback:
            logger.info("Attempting to reconnect to Redis...")
            self._connect()


# ============================================================================
# Global Instances
# ============================================================================

_db_manager: Optional[DatabaseManager] = None
_redis_manager: Optional[RedisManager] = None


def init_database(config: DatabaseConfig) -> DatabaseManager:
    """Initialize database manager"""
    global _db_manager
    _db_manager = DatabaseManager(config)
    _db_manager.create_tables()
    return _db_manager


def init_redis(config: RedisConfig) -> RedisManager:
    """Initialize Redis manager"""
    global _redis_manager
    _redis_manager = RedisManager(config)
    return _redis_manager


def get_db_manager() -> DatabaseManager:
    """Get global database manager"""
    if _db_manager is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _db_manager


def get_redis_manager() -> RedisManager:
    """Get global Redis manager"""
    if _redis_manager is None:
        raise RuntimeError("Redis not initialized. Call init_redis() first.")
    return _redis_manager
