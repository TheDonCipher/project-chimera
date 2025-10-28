"""
Pytest configuration and shared fixtures for Project Chimera
Task 10.1: Set up local testing infrastructure

This module provides shared fixtures for:
- Database connections (PostgreSQL)
- Redis connections
- Mock RPC providers
- Test data generators
- Configuration management
"""

import os
import sys
import asyncio
import pytest
from decimal import Decimal
from pathlib import Path
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock, MagicMock
from datetime import datetime, timedelta

# Add bot/src to Python path
bot_src_path = str(Path(__file__).parent / "bot" / "src")
if bot_src_path not in sys.path:
    sys.path.insert(0, bot_src_path)

# Import project modules (with error handling for when modules don't exist yet)
try:
    from types import Position, Opportunity, SystemState, ExecutionRecord
    from config import ChimeraConfig, ProtocolConfig, RPCConfig, OracleConfig, SafetyConfig
    from database import DatabaseManager, RedisManager, RedisConfig
except ImportError:
    # Modules not yet available - tests will need to import directly
    Position = None
    Opportunity = None
    SystemState = None
    ExecutionRecord = None
    ChimeraConfig = None
    ProtocolConfig = None
    RPCConfig = None
    OracleConfig = None
    SafetyConfig = None
    DatabaseManager = None
    RedisManager = None
    RedisConfig = None


# ============================================================================
# Pytest Configuration
# ============================================================================

def pytest_configure(config):
    """Configure pytest with custom settings"""
    # Set test environment
    os.environ['ENVIRONMENT'] = 'test'
    os.environ['LOG_LEVEL'] = 'DEBUG'
    
    # Disable actual execution in tests
    os.environ['ENABLE_EXECUTION'] = 'false'
    os.environ['DRY_RUN'] = 'true'


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically"""
    for item in items:
        # Add markers based on test file location
        if "test_state_engine" in item.nodeid:
            item.add_marker(pytest.mark.state_engine)
        elif "test_opportunity_detector" in item.nodeid:
            item.add_marker(pytest.mark.opportunity_detector)
        elif "test_execution_planner" in item.nodeid:
            item.add_marker(pytest.mark.execution_planner)
        elif "test_safety_controller" in item.nodeid:
            item.add_marker(pytest.mark.safety_controller)
        elif "test_backtest" in item.nodeid:
            item.add_marker(pytest.mark.backtest)
        
        # Add markers based on test name patterns
        if "integration" in item.nodeid:
            item.add_marker(pytest.mark.integration)
        elif "e2e" in item.nodeid:
            item.add_marker(pytest.mark.e2e)
        else:
            item.add_marker(pytest.mark.unit)


# ============================================================================
# Event Loop Fixtures
# ============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Configuration Fixtures
# ============================================================================

@pytest.fixture
def test_config():
    """Create a test configuration with safe defaults"""
    config = Mock(spec=ChimeraConfig if ChimeraConfig else object)
    
    # Protocol configurations
    config.protocols = {
        'moonwell': ProtocolConfig(
            name='moonwell',
            address='0x1234567890123456789012345678901234567890',
            liquidation_threshold=Decimal('0.80'),
            liquidation_bonus=Decimal('0.05')
        ),
        'seamless': ProtocolConfig(
            name='seamless',
            address='0x0987654321098765432109876543210987654321',
            liquidation_threshold=Decimal('0.75'),
            liquidation_bonus=Decimal('0.08')
        )
    }
    
    # RPC configuration
    config.rpc = RPCConfig(
        primary_http='http://localhost:8545',
        backup_http='http://localhost:8546',
        archive_http='http://localhost:8547',
        primary_ws='ws://localhost:8545',
        backup_ws='ws://localhost:8546'
    )
    
    # Oracle configuration
    config.oracles = {
        'chainlink': OracleConfig(
            name='chainlink',
            address='0x71041dddad3595F9CEd3DcCFBe3D1F4b0a16Bb70',
            type='chainlink'
        ),
        'pyth': OracleConfig(
            name='pyth',
            address='0x8250f4aF4B972684F7b336503E2D6dFeDeB1487a',
            type='pyth'
        )
    }
    
    # Safety configuration
    config.safety = SafetyConfig(
        max_single_execution_usd=Decimal('500'),
        max_daily_volume_usd=Decimal('2500'),
        min_profit_usd=Decimal('50'),
        max_consecutive_failures=3,
        state_divergence_threshold_bps=10,
        confirmation_blocks=2
    )
    
    # Contract addresses
    config.chimera_contract = '0xChimeraContractAddress123456789012345678'
    config.operator_address = '0xOperatorAddress1234567890123456789012345'
    config.treasury_address = '0xTreasuryAddress1234567890123456789012345'
    
    return config


@pytest.fixture
def redis_config():
    """Create Redis configuration for testing"""
    if not RedisConfig:
        return None
    return RedisConfig(
        host=os.getenv('REDIS_HOST', 'localhost'),
        port=int(os.getenv('REDIS_PORT', '6379')),
        password=os.getenv('REDIS_PASSWORD'),
        db=int(os.getenv('REDIS_TEST_DB', '1')),  # Use separate DB for tests
        ttl_seconds=60
    )


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture
def mock_db_manager():
    """Create a mock database manager for testing"""
    db_manager = Mock(spec=DatabaseManager if DatabaseManager else object)
    db_manager.get_session = Mock()
    db_manager.execute = AsyncMock()
    db_manager.fetch_one = AsyncMock()
    db_manager.fetch_all = AsyncMock()
    db_manager.close = AsyncMock()
    return db_manager


@pytest.fixture
async def redis_manager(redis_config):
    """Create a Redis manager for testing (uses in-memory fallback if Redis unavailable)"""
    if not RedisManager or not redis_config:
        yield None
        return
    manager = RedisManager(redis_config)
    yield manager
    # Cleanup: clear test data
    try:
        manager.clear()
    except:
        pass


@pytest.fixture
def db_session(mock_db_manager):
    """Create a database session for testing"""
    session = MagicMock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    mock_db_manager.get_session.return_value = session
    return session


# ============================================================================
# Mock RPC Provider Fixtures
# ============================================================================

@pytest.fixture
def mock_web3():
    """Create a mock Web3 instance with realistic Base mainnet responses"""
    web3 = Mock()
    
    # Mock eth module
    web3.eth = Mock()
    web3.eth.chain_id = 8453  # Base mainnet
    web3.eth.block_number = 10000000
    web3.eth.gas_price = 1000000  # 0.001 gwei
    
    # Mock get_block
    def mock_get_block(block_identifier, full_transactions=False):
        if isinstance(block_identifier, str) and block_identifier == 'latest':
            block_num = 10000000
        else:
            block_num = block_identifier
        
        return {
            'number': block_num,
            'hash': f'0x{block_num:064x}',
            'timestamp': 1700000000 + block_num * 2,
            'gasLimit': 30000000,
            'gasUsed': 15000000,
            'baseFeePerGas': 1000000,
            'transactions': []
        }
    
    web3.eth.get_block = Mock(side_effect=mock_get_block)
    
    # Mock call (for eth_call simulations)
    web3.eth.call = AsyncMock(return_value=b'\x00' * 32)
    
    # Mock estimate_gas
    web3.eth.estimate_gas = AsyncMock(return_value=300000)
    
    # Mock get_transaction_count (for nonce)
    web3.eth.get_transaction_count = AsyncMock(return_value=42)
    
    # Mock send_raw_transaction
    web3.eth.send_raw_transaction = AsyncMock(
        return_value=b'\x12\x34\x56\x78' * 8
    )
    
    # Mock get_transaction_receipt
    web3.eth.get_transaction_receipt = AsyncMock(return_value={
        'status': 1,
        'blockNumber': 10000001,
        'gasUsed': 300000,
        'effectiveGasPrice': 1000000,
        'logs': []
    })
    
    # Mock contract
    def mock_contract(address, abi):
        contract = Mock()
        contract.address = address
        contract.functions = Mock()
        return contract
    
    web3.eth.contract = Mock(side_effect=mock_contract)
    
    return web3


@pytest.fixture
def mock_rpc_responses():
    """Create realistic mock RPC responses for Base mainnet"""
    return {
        # Block responses
        'eth_blockNumber': '0x989680',  # 10000000
        'eth_getBlockByNumber': {
            'number': '0x989680',
            'hash': '0xabc123def456',
            'timestamp': '0x6563e5c0',
            'gasLimit': '0x1c9c380',
            'gasUsed': '0xe4e1c0',
            'baseFeePerGas': '0xf4240',
            'transactions': []
        },
        
        # Transaction responses
        'eth_call': '0x' + '00' * 32,
        'eth_estimateGas': '0x493e0',  # 300000
        'eth_getTransactionCount': '0x2a',  # 42
        'eth_sendRawTransaction': '0x1234567890abcdef' * 4,
        'eth_getTransactionReceipt': {
            'status': '0x1',
            'blockNumber': '0x989681',
            'gasUsed': '0x493e0',
            'effectiveGasPrice': '0xf4240',
            'logs': []
        },
        
        # Oracle price responses (Chainlink format)
        'latestRoundData': {
            'roundId': 1000,
            'answer': 2500_00000000,  # $2500 with 8 decimals
            'startedAt': 1700000000,
            'updatedAt': 1700000000,
            'answeredInRound': 1000
        },
        
        # Lending protocol responses
        'getUserAccountData': {
            'totalCollateralETH': 1000000000000000000,  # 1 ETH
            'totalDebtETH': 600000000000000000,  # 0.6 ETH
            'availableBorrowsETH': 400000000000000000,  # 0.4 ETH
            'currentLiquidationThreshold': 8000,  # 80%
            'ltv': 7500,  # 75%
            'healthFactor': 1333333333333333333  # 1.33
        },
        
        # Base L1 data cost parameters
        'l1GasPrice': '0x3b9aca00',  # 1 gwei
        'l1Scalar': '0x0000000000000000000000000000000000000000000000000000000000000684',  # 1668
        'overhead': '0x0000000000000000000000000000000000000000000000000000000000000834'  # 2100
    }


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection"""
    ws = AsyncMock()
    ws.send = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    ws.closed = False
    
    # Mock subscription responses
    async def mock_recv():
        return '{"jsonrpc":"2.0","id":1,"result":"0x123"}'
    
    ws.recv.side_effect = mock_recv
    
    return ws


# ============================================================================
# Test Data Generator Fixtures
# ============================================================================

@pytest.fixture
def position_generator():
    """Generate test Position objects"""
    def generate(
        protocol: str = 'moonwell',
        user: str = '0xAbCdEf1234567890123456789012345678901234',
        collateral_amount: int = 1000000000000000000,  # 1 ETH
        debt_amount: int = 1500000000,  # 1500 USDC
        block_number: int = 10000000
    ):
        if not Position:
            return None
        return Position(
            protocol=protocol,
            user=user,
            collateral_asset='0x4200000000000000000000000000000000000006',  # WETH
            collateral_amount=collateral_amount,
            debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',  # USDC
            debt_amount=debt_amount,
            liquidation_threshold=Decimal('0.80'),
            last_update_block=block_number,
            blocks_unhealthy=0
        )
    
    return generate


@pytest.fixture
def opportunity_generator(position_generator):
    """Generate test Opportunity objects"""
    def generate(
        health_factor: Decimal = Decimal('0.95'),
        estimated_profit: Decimal = Decimal('100.0'),
        block_number: int = 10000000
    ):
        if not Opportunity:
            return None
        position = position_generator(block_number=block_number)
        
        return Opportunity(
            position=position,
            health_factor=health_factor,
            collateral_price_usd=Decimal('2500.0'),
            debt_price_usd=Decimal('1.0'),
            liquidation_bonus=Decimal('0.05'),
            estimated_gross_profit_usd=estimated_profit,
            estimated_net_profit_usd=estimated_profit * Decimal('0.7'),  # After costs
            detected_at_block=block_number,
            detected_at_timestamp=datetime.now()
        )
    
    return generate


@pytest.fixture
def execution_record_generator():
    """Generate test ExecutionRecord objects"""
    def generate(
        protocol: str = 'moonwell',
        success: bool = True,
        profit_usd: Decimal = Decimal('75.0'),
        block_number: int = 10000000
    ):
        if not ExecutionRecord:
            return None
        return ExecutionRecord(
            timestamp=datetime.now(),
            block_number=block_number,
            protocol=protocol,
            borrower='0xBorrower1234567890123456789012345678901',
            collateral_asset='0x4200000000000000000000000000000000000006',
            debt_asset='0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913',
            health_factor=Decimal('0.95'),
            simulation_success=True,
            simulated_profit_wei=75000000000000000000,  # 75 ETH worth
            simulated_profit_usd=profit_usd,
            bundle_submitted=True,
            tx_hash='0x' + '12' * 32 if success else None,
            submission_path='mempool',
            bribe_wei=15000000000000000000,  # 15 ETH worth
            included=success,
            inclusion_block=block_number + 1 if success else None,
            actual_profit_wei=70000000000000000000 if success else 0,
            actual_profit_usd=profit_usd * Decimal('0.93') if success else Decimal('0'),
            operator_address='0xOperator1234567890123456789012345678901',
            state_at_execution=SystemState.NORMAL,
            rejection_reason=None if success else 'Simulation failed'
        )
    
    return generate


@pytest.fixture
def batch_position_generator(position_generator):
    """Generate multiple test positions"""
    def generate(count: int = 10, start_block: int = 10000000):
        positions = []
        for i in range(count):
            user_suffix = f"{i:040d}"
            position = position_generator(
                user=f'0x{user_suffix}',
                collateral_amount=1000000000000000000 + i * 100000000000000000,
                debt_amount=1500000000 + i * 100000000,
                block_number=start_block + i
            )
            positions.append(position)
        return positions
    
    return generate


# ============================================================================
# Mock Oracle Fixtures
# ============================================================================

@pytest.fixture
def mock_chainlink_oracle():
    """Create a mock Chainlink oracle"""
    oracle = Mock()
    
    # Mock latestRoundData
    def mock_latest_round_data():
        return (
            1000,  # roundId
            2500_00000000,  # answer ($2500 with 8 decimals)
            1700000000,  # startedAt
            1700000000,  # updatedAt
            1000  # answeredInRound
        )
    
    oracle.functions.latestRoundData = Mock(
        return_value=Mock(call=Mock(return_value=mock_latest_round_data()))
    )
    
    oracle.functions.decimals = Mock(
        return_value=Mock(call=Mock(return_value=8))
    )
    
    return oracle


@pytest.fixture
def mock_lending_protocol():
    """Create a mock lending protocol contract"""
    protocol = Mock()
    
    # Mock getUserAccountData
    def mock_get_user_account_data(user_address):
        return (
            1000000000000000000,  # totalCollateralETH
            600000000000000000,  # totalDebtETH
            400000000000000000,  # availableBorrowsETH
            8000,  # currentLiquidationThreshold (80%)
            7500,  # ltv (75%)
            1333333333333333333  # healthFactor (1.33)
        )
    
    protocol.functions.getUserAccountData = Mock(
        return_value=Mock(call=Mock(side_effect=mock_get_user_account_data))
    )
    
    # Mock liquidationCall
    protocol.functions.liquidationCall = Mock(
        return_value=Mock(buildTransaction=Mock(return_value={
            'to': '0x1234567890123456789012345678901234567890',
            'data': '0xabcdef',
            'gas': 300000,
            'gasPrice': 1000000,
            'nonce': 42,
            'chainId': 8453
        }))
    )
    
    return protocol


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_time():
    """Mock time.time() for deterministic testing"""
    with pytest.MonkeyPatch.context() as m:
        current_time = 1700000000.0
        m.setattr('time.time', lambda: current_time)
        yield current_time


@pytest.fixture
def temp_log_file(tmp_path):
    """Create a temporary log file for testing"""
    log_file = tmp_path / "test.log"
    return str(log_file)


@pytest.fixture(autouse=True)
def reset_environment():
    """Reset environment variables after each test"""
    original_env = os.environ.copy()
    yield
    os.environ.clear()
    os.environ.update(original_env)


# ============================================================================
# Cleanup Fixtures
# ============================================================================

@pytest.fixture(scope="function", autouse=True)
async def cleanup_after_test(redis_manager):
    """Cleanup resources after each test"""
    yield
    # Clear Redis test data
    try:
        if redis_manager:
            redis_manager.clear()
    except:
        pass


@pytest.fixture(scope="session", autouse=True)
def cleanup_after_session():
    """Cleanup resources after test session"""
    yield
    # Clean up any remaining resources
    pass
