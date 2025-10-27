"""
StateEngine Module - Real-time blockchain state synchronization

Maintains authoritative, real-time view of blockchain state through:
- WebSocket connections to multiple RPC providers
- Event parsing for lending protocols
- Block-level state reconciliation
- Sequencer health monitoring
- Position cache management
"""

import asyncio
import json
import logging
import time
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
from decimal import Decimal
from web3 import Web3
from websockets import connect, ConnectionClosed
from websockets.client import WebSocketClientProtocol

from .types import Position, StateError, RPCError, SystemState, StateDivergence
from .config import ChimeraConfig
from .database import RedisManager, DatabaseManager, StateDivergenceModel

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connections with automatic reconnection and failover"""
    
    def __init__(
        self,
        primary_ws_url: str,
        backup_ws_url: str,
        on_message: Callable[[Dict[str, Any]], None],
        on_error: Optional[Callable[[Exception], None]] = None
    ):
        self.primary_ws_url = primary_ws_url
        self.backup_ws_url = backup_ws_url
        self.on_message = on_message
        self.on_error = on_error
        
        self.ws: Optional[WebSocketClientProtocol] = None
        self.is_primary = True
        self.is_connected = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 10
        self.base_backoff = 1.0  # seconds
        self.max_backoff = 60.0  # seconds
        
        self._running = False
        self._last_message_time = time.time()
        self._health_check_interval = 30  # seconds

    async def connect(self):
        """Establish WebSocket connection"""
        url = self.primary_ws_url if self.is_primary else self.backup_ws_url
        provider_name = "primary" if self.is_primary else "backup"
        
        try:
            logger.info(f"Connecting to {provider_name} WebSocket: {url}")
            self.ws = await connect(url, ping_interval=20, ping_timeout=10)
            self.is_connected = True
            self.reconnect_attempts = 0
            self._last_message_time = time.time()
            logger.info(f"Connected to {provider_name} WebSocket")
            
            # Subscribe to newHeads
            await self.subscribe_new_heads()
            
        except Exception as e:
            logger.error(f"Failed to connect to {provider_name} WebSocket: {e}")
            self.is_connected = False
            raise RPCError(f"WebSocket connection failed: {e}")
    
    async def subscribe_new_heads(self):
        """Subscribe to newHeads for real-time block monitoring"""
        if not self.ws:
            raise RPCError("WebSocket not connected")
        
        subscription_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": ["newHeads"]
        }
        
        await self.ws.send(json.dumps(subscription_request))
        logger.info("Subscribed to newHeads")
    
    async def disconnect(self):
        """Close WebSocket connection"""
        if self.ws:
            await self.ws.close()
            self.ws = None
            self.is_connected = False
            logger.info("WebSocket disconnected")

    async def reconnect(self):
        """Reconnect with exponential backoff"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Max reconnection attempts reached")
            # Try failover to backup
            if self.is_primary:
                logger.info("Failing over to backup WebSocket")
                self.is_primary = False
                self.reconnect_attempts = 0
            else:
                raise RPCError("All WebSocket providers failed")
        
        # Calculate backoff delay
        backoff = min(
            self.base_backoff * (2 ** self.reconnect_attempts),
            self.max_backoff
        )
        
        logger.info(f"Reconnecting in {backoff:.1f} seconds (attempt {self.reconnect_attempts + 1})")
        await asyncio.sleep(backoff)
        
        self.reconnect_attempts += 1
        
        try:
            await self.disconnect()
            await self.connect()
        except Exception as e:
            logger.error(f"Reconnection failed: {e}")
            await self.reconnect()  # Retry
    
    async def start(self):
        """Start listening for messages"""
        self._running = True
        
        while self._running:
            try:
                if not self.is_connected:
                    await self.connect()
                
                # Listen for messages
                async for message in self.ws:
                    self._last_message_time = time.time()
                    
                    try:
                        data = json.loads(message)
                        await self.on_message(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse WebSocket message: {e}")
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        if self.on_error:
                            self.on_error(e)
                
            except ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self.is_connected = False
                await self.reconnect()
            
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self.is_connected = False
                if self.on_error:
                    self.on_error(e)
                await self.reconnect()
    
    async def stop(self):
        """Stop listening and disconnect"""
        self._running = False
        await self.disconnect()
    
    def check_health(self) -> bool:
        """Check connection health"""
        if not self.is_connected:
            return False
        
        # Check if we've received messages recently
        time_since_last_message = time.time() - self._last_message_time
        if time_since_last_message > self._health_check_interval:
            logger.warning(f"No messages received for {time_since_last_message:.1f} seconds")
            return False
        
        return True
    
    async def failover(self):
        """Manually trigger failover to backup"""
        if self.is_primary:
            logger.info("Manual failover to backup WebSocket")
            self.is_primary = False
            self.reconnect_attempts = 0
            await self.disconnect()
            await self.connect()
        else:
            logger.warning("Already using backup WebSocket")



class StateEngine:
    """Real-time blockchain state synchronization engine"""
    
    def __init__(
        self,
        config: ChimeraConfig,
        redis_manager: RedisManager,
        db_manager: DatabaseManager
    ):
        self.config = config
        self.redis = redis_manager
        self.db = db_manager
        
        # Web3 instances for RPC calls
        self.primary_web3 = Web3(Web3.HTTPProvider(config.rpc.primary_http))
        self.backup_web3 = Web3(Web3.HTTPProvider(config.rpc.backup_http))
        self.archive_web3 = Web3(Web3.HTTPProvider(config.rpc.archive_http))
        self.current_web3 = self.primary_web3
        
        # WebSocket connection manager
        self.ws_manager: Optional[WebSocketConnectionManager] = None
        
        # State tracking
        self.current_block = 0
        self.previous_block = 0
        self.last_block_timestamp = 0
        self.last_block_received_time = time.time()
        self.system_state = SystemState.NORMAL
        
        # Event checkpoints
        self.last_checkpoint_block = 0
        self.checkpoint_interval = 10
        
        # Running flag
        self._running = False
        
        logger.info("StateEngine initialized")
    
    async def start(self):
        """Start the StateEngine"""
        self._running = True
        logger.info("Starting StateEngine...")
        
        # Initialize WebSocket connection
        self.ws_manager = WebSocketConnectionManager(
            primary_ws_url=self.config.rpc.primary_ws,
            backup_ws_url=self.config.rpc.backup_ws,
            on_message=self._handle_ws_message,
            on_error=self._handle_ws_error
        )
        
        # Start WebSocket listener in background
        asyncio.create_task(self.ws_manager.start())
        
        # Start health monitoring
        asyncio.create_task(self._monitor_health())
        
        logger.info("StateEngine started")
    
    async def stop(self):
        """Stop the StateEngine"""
        self._running = False
        if self.ws_manager:
            await self.ws_manager.stop()
        logger.info("StateEngine stopped")

    async def _handle_ws_message(self, data: Dict[str, Any]):
        """Handle incoming WebSocket message"""
        # Check if it's a subscription notification
        if data.get("method") == "eth_subscription":
            params = data.get("params", {})
            result = params.get("result", {})
            
            # New block header
            if "number" in result:
                await self._process_new_block(result)
        
        # Handle subscription confirmation
        elif "result" in data and "id" in data:
            logger.debug(f"Subscription confirmed: {data}")
    
    async def _process_new_block(self, block_header: Dict[str, Any]):
        """Process new block header from WebSocket"""
        start_time = time.time()
        
        try:
            # Extract block data
            block_number = int(block_header.get("number", "0x0"), 16)
            block_timestamp = int(block_header.get("timestamp", "0x0"), 16)
            
            logger.info(f"Processing block {block_number}")
            
            # Update state
            self.previous_block = self.current_block
            self.current_block = block_number
            self.last_block_timestamp = block_timestamp
            self.last_block_received_time = time.time()
            
            # Check sequencer health
            await self._check_sequencer_health(block_number, block_timestamp)
            
            # Process events (will be implemented in subtask 3.2)
            # await self._process_block_events(block_number)
            
            # Reconcile state (will be implemented in subtask 3.3)
            # await self._reconcile_state(block_number)
            
            # Save checkpoint
            if block_number - self.last_checkpoint_block >= self.checkpoint_interval:
                await self._save_checkpoint(block_number)
                self.last_checkpoint_block = block_number
            
            # Log processing time
            processing_time = (time.time() - start_time) * 1000
            logger.info(f"Block {block_number} processed in {processing_time:.1f}ms")
            
            # Check if within 500ms requirement
            if processing_time > 500:
                logger.warning(f"Block processing exceeded 500ms: {processing_time:.1f}ms")
        
        except Exception as e:
            logger.error(f"Error processing block: {e}", exc_info=True)
            raise StateError(f"Block processing failed: {e}")
    
    async def _check_sequencer_health(self, block_number: int, block_timestamp: int):
        """Check sequencer health for anomalies"""
        try:
            # Check 1: Verify sequential block numbers
            if self.previous_block > 0:
                expected_block = self.previous_block + 1
                
                if block_number != expected_block:
                    gap = block_number - self.previous_block
                    
                    if gap > 1:
                        logger.warning(f"Block gap detected: {self.previous_block} -> {block_number} (gap: {gap})")
                        
                        # Small gaps (2-3 blocks) might be normal, but larger gaps are concerning
                        if gap > 3:
                            logger.critical(f"CRITICAL: Large block gap detected ({gap} blocks)")
                            self.set_system_state(SystemState.HALTED)
                            return
                    
                    elif gap < 1:
                        # Reorg detected
                        reorg_depth = self.previous_block - block_number + 1
                        logger.warning(f"Reorg detected: depth {reorg_depth} blocks")
                        
                        if reorg_depth > 3:
                            logger.critical(f"CRITICAL: Unusual reorg depth ({reorg_depth} blocks)")
                            self.set_system_state(SystemState.HALTED)
                            return
            
            # Check 2: Detect timestamp jumps
            if self.last_block_timestamp > 0:
                time_diff = block_timestamp - self.last_block_timestamp
                
                if time_diff > 20:
                    logger.warning(f"Large timestamp jump: {time_diff} seconds")
                    logger.critical(f"CRITICAL: Timestamp jump exceeds 20 seconds")
                    self.set_system_state(SystemState.HALTED)
                    return
                
                elif time_diff < 0:
                    logger.critical(f"CRITICAL: Timestamp went backwards by {abs(time_diff)} seconds")
                    self.set_system_state(SystemState.HALTED)
                    return
            
            # Check 3: Detect block production stalls
            # This is monitored by the health check in _monitor_health()
            # which checks if we haven't received messages in 30 seconds
            
        except Exception as e:
            logger.error(f"Error checking sequencer health: {e}", exc_info=True)
    
    async def _save_checkpoint(self, block_number: int):
        """Save event checkpoint for recovery"""
        checkpoint_key = "checkpoint:last_block"
        self.redis.set(checkpoint_key, str(block_number))
        logger.debug(f"Checkpoint saved at block {block_number}")
    
    async def _monitor_health(self):
        """Monitor WebSocket connection health and block production stalls"""
        while self._running:
            await asyncio.sleep(5)  # Check every 5 seconds
            
            # Check WebSocket connection health
            if self.ws_manager and not self.ws_manager.check_health():
                logger.warning("WebSocket health check failed, triggering failover")
                try:
                    await self.ws_manager.failover()
                except Exception as e:
                    logger.error(f"Failover failed: {e}")
            
            # Check for block production stalls (no new block for >10 seconds)
            if self.last_block_received_time > 0:
                time_since_last_block = time.time() - self.last_block_received_time
                
                if time_since_last_block > 10:
                    logger.critical(
                        f"CRITICAL: Block production stall detected - "
                        f"no new block for {time_since_last_block:.1f} seconds"
                    )
                    self.set_system_state(SystemState.HALTED)
                elif time_since_last_block > 5:
                    logger.warning(
                        f"Block production delay: {time_since_last_block:.1f} seconds since last block"
                    )
    
    def _handle_ws_error(self, error: Exception):
        """Handle WebSocket errors"""
        logger.error(f"WebSocket error: {error}")
        # Errors are handled by reconnection logic in WebSocketConnectionManager
    
    def get_system_state(self) -> SystemState:
        """Get current system state"""
        return self.system_state
    
    def set_system_state(self, state: SystemState):
        """Set system state"""
        if state != self.system_state:
            logger.warning(f"System state changed: {self.system_state} -> {state}")
            self.system_state = state

    async def _process_block_events(self, block_number: int):
        """Process lending protocol events for the block"""
        start_time = time.time()
        
        try:
            # Get block with full transactions
            block = self.current_web3.eth.get_block(block_number, full_transactions=True)
            
            # Get transaction receipts to extract logs
            for tx in block['transactions']:
                try:
                    receipt = self.current_web3.eth.get_transaction_receipt(tx['hash'])
                    
                    # Parse logs for lending protocol events
                    for log in receipt['logs']:
                        await self._parse_event_log(log, block_number)
                
                except Exception as e:
                    logger.error(f"Error processing transaction {tx['hash'].hex()}: {e}")
                    continue
            
            processing_time = (time.time() - start_time) * 1000
            if processing_time > 100:
                logger.warning(f"Event processing took {processing_time:.1f}ms (target: <100ms)")
        
        except Exception as e:
            logger.error(f"Error processing block events: {e}", exc_info=True)
            # Don't raise - continue with next block
    
    async def _parse_event_log(self, log: Dict[str, Any], block_number: int):
        """Parse individual event log"""
        try:
            contract_address = log['address'].lower()
            topics = log['topics']
            
            if not topics:
                return
            
            event_signature = topics[0].hex()
            
            # Borrow event: Borrow(address indexed reserve, address user, address indexed onBehalfOf, uint256 amount, uint256 borrowRate, uint256 borrowRateMode, uint16 indexed referral)
            # Event signature: 0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b
            if event_signature == "0xc6a898309e823ee50bac64e45ca8adba6690e99e7841c45d754e2a38e9019d9b":
                await self._handle_borrow_event(log, contract_address, block_number)
            
            # Repay event: Repay(address indexed reserve, address indexed user, address indexed repayer, uint256 amount)
            # Event signature: 0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa
            elif event_signature == "0x4cdde6e09bb755c9a5589ebaec640bbfedff1362d4b255ebf8339782b9942faa":
                await self._handle_repay_event(log, contract_address, block_number)
            
            # Liquidation event: LiquidationCall(address indexed collateralAsset, address indexed debtAsset, address indexed user, uint256 debtToCover, uint256 liquidatedCollateralAmount, address liquidator, bool receiveAToken)
            # Event signature: 0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286
            elif event_signature == "0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286":
                await self._handle_liquidation_event(log, contract_address, block_number)
            
            # Chainlink oracle price update: AnswerUpdated(int256 indexed current, uint256 indexed roundId, uint256 updatedAt)
            # Event signature: 0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f
            elif event_signature == "0x0559884fd3a460db3073b7fc896cc77986f16e378210ded43186175bf646fc5f":
                await self._handle_price_update_event(log, contract_address, block_number)
        
        except Exception as e:
            logger.error(f"Error parsing event log: {e}")

    async def _handle_borrow_event(self, log: Dict[str, Any], protocol_address: str, block_number: int):
        """Handle Borrow event"""
        try:
            topics = log['topics']
            data = log['data']
            
            # Decode indexed parameters from topics
            reserve = self.current_web3.to_checksum_address('0x' + topics[1].hex()[-40:])
            user = self.current_web3.to_checksum_address('0x' + topics[2].hex()[-40:])
            
            # Decode non-indexed parameters from data
            # amount is the first 32 bytes
            amount = int(data.hex()[2:66], 16)
            
            # Determine protocol name
            protocol = self._get_protocol_name(protocol_address)
            
            if protocol:
                # Update position in cache
                await self._update_position_debt(protocol, user, reserve, amount, block_number, is_increase=True)
                logger.debug(f"Borrow event: {protocol} user={user} asset={reserve} amount={amount}")
        
        except Exception as e:
            logger.error(f"Error handling Borrow event: {e}")
    
    async def _handle_repay_event(self, log: Dict[str, Any], protocol_address: str, block_number: int):
        """Handle Repay event"""
        try:
            topics = log['topics']
            data = log['data']
            
            # Decode indexed parameters
            reserve = self.current_web3.to_checksum_address('0x' + topics[1].hex()[-40:])
            user = self.current_web3.to_checksum_address('0x' + topics[2].hex()[-40:])
            
            # Decode amount from data
            amount = int(data.hex()[2:66], 16)
            
            protocol = self._get_protocol_name(protocol_address)
            
            if protocol:
                # Update position in cache
                await self._update_position_debt(protocol, user, reserve, amount, block_number, is_increase=False)
                logger.debug(f"Repay event: {protocol} user={user} asset={reserve} amount={amount}")
        
        except Exception as e:
            logger.error(f"Error handling Repay event: {e}")
    
    async def _handle_liquidation_event(self, log: Dict[str, Any], protocol_address: str, block_number: int):
        """Handle Liquidation event"""
        try:
            topics = log['topics']
            
            # Decode indexed parameters
            collateral_asset = self.current_web3.to_checksum_address('0x' + topics[1].hex()[-40:])
            debt_asset = self.current_web3.to_checksum_address('0x' + topics[2].hex()[-40:])
            user = self.current_web3.to_checksum_address('0x' + topics[3].hex()[-40:])
            
            protocol = self._get_protocol_name(protocol_address)
            
            if protocol:
                # Remove position from cache (it's been liquidated)
                position_key = f"position:{protocol}:{user}"
                self.redis.delete(position_key)
                logger.info(f"Liquidation event: {protocol} user={user} removed from cache")
        
        except Exception as e:
            logger.error(f"Error handling Liquidation event: {e}")
    
    async def _handle_price_update_event(self, log: Dict[str, Any], oracle_address: str, block_number: int):
        """Handle Chainlink price update event"""
        try:
            data = log['data']
            
            # Decode price from data (first 32 bytes)
            price = int(data.hex()[2:66], 16)
            
            # Store price update in cache
            price_key = f"oracle_price:{oracle_address}"
            self.redis.set(price_key, str(price), ttl=300)  # 5 minute TTL
            
            logger.debug(f"Price update: oracle={oracle_address} price={price}")
        
        except Exception as e:
            logger.error(f"Error handling price update event: {e}")

    async def _update_position_debt(
        self,
        protocol: str,
        user: str,
        debt_asset: str,
        amount: int,
        block_number: int,
        is_increase: bool
    ):
        """Update position debt in cache"""
        start_time = time.time()
        
        try:
            position_key = f"position:{protocol}:{user}"
            
            # Get existing position from cache
            position_data = self.redis.get(position_key)
            
            if position_data:
                # Update existing position
                position_dict = json.loads(position_data)
                
                if is_increase:
                    position_dict['debt_amount'] += amount
                else:
                    position_dict['debt_amount'] = max(0, position_dict['debt_amount'] - amount)
                
                position_dict['last_update_block'] = block_number
                
                # Save back to cache
                self.redis.set(position_key, json.dumps(position_dict), ttl=60)
            else:
                # Fetch full position data from blockchain
                await self._fetch_and_cache_position(protocol, user, block_number)
            
            update_time = (time.time() - start_time) * 1000
            if update_time > 100:
                logger.warning(f"Position update took {update_time:.1f}ms (target: <100ms)")
        
        except Exception as e:
            logger.error(f"Error updating position debt: {e}")
    
    async def _fetch_and_cache_position(self, protocol: str, user: str, block_number: int):
        """Fetch complete position data from blockchain and cache it"""
        try:
            # Get protocol configuration
            protocol_config = self.config.protocols.get(protocol)
            if not protocol_config:
                logger.warning(f"Unknown protocol: {protocol}")
                return
            
            # This would call the lending protocol contract to get position data
            # For now, we'll create a placeholder
            # In a real implementation, this would use Web3 to call getUserAccountData or similar
            
            position_data = {
                'protocol': protocol,
                'user': user,
                'collateral_asset': '0x0000000000000000000000000000000000000000',  # Placeholder
                'collateral_amount': 0,
                'debt_asset': '0x0000000000000000000000000000000000000000',  # Placeholder
                'debt_amount': 0,
                'liquidation_threshold': str(protocol_config.liquidation_threshold),
                'last_update_block': block_number,
                'blocks_unhealthy': 0
            }
            
            position_key = f"position:{protocol}:{user}"
            self.redis.set(position_key, json.dumps(position_data), ttl=60)
            
            logger.debug(f"Fetched and cached position: {protocol}:{user}")
        
        except Exception as e:
            logger.error(f"Error fetching position: {e}")
    
    def _get_protocol_name(self, address: str) -> Optional[str]:
        """Get protocol name from contract address"""
        address_lower = address.lower()
        
        for protocol_name, protocol_config in self.config.protocols.items():
            if protocol_config.address.lower() == address_lower:
                return protocol_name
        
        return None

    async def _reconcile_state(self, block_number: int):
        """Reconcile cached state against canonical blockchain state"""
        try:
            # Get all positions from cache
            position_keys = self.redis.keys("position:*")
            
            if not position_keys:
                logger.debug("No positions to reconcile")
                return
            
            divergences = []
            
            for position_key in position_keys:
                try:
                    # Get cached position
                    position_data = self.redis.get(position_key)
                    if not position_data:
                        continue
                    
                    position_dict = json.loads(position_data)
                    protocol = position_dict['protocol']
                    user = position_dict['user']
                    
                    # Fetch canonical state from blockchain
                    canonical_data = await self._fetch_canonical_position(protocol, user, block_number)
                    
                    if not canonical_data:
                        continue
                    
                    # Calculate divergence for collateral
                    cached_collateral = position_dict.get('collateral_amount', 0)
                    canonical_collateral = canonical_data.get('collateral_amount', 0)
                    
                    if canonical_collateral > 0:
                        collateral_divergence_bps = abs(
                            (cached_collateral - canonical_collateral) * 10000 // canonical_collateral
                        )
                        
                        if collateral_divergence_bps > 0:
                            divergence = StateDivergence(
                                timestamp=datetime.utcnow(),
                                block_number=block_number,
                                protocol=protocol,
                                user=user,
                                field='collateral_amount',
                                cached_value=cached_collateral,
                                canonical_value=canonical_collateral,
                                divergence_bps=collateral_divergence_bps
                            )
                            divergences.append(divergence)
                            
                            # Check if divergence exceeds threshold
                            if collateral_divergence_bps > 10:
                                logger.critical(
                                    f"CRITICAL: Collateral divergence {collateral_divergence_bps} BPS "
                                    f"exceeds 10 BPS threshold for {protocol}:{user}"
                                )
                                self.set_system_state(SystemState.HALTED)
                    
                    # Calculate divergence for debt
                    cached_debt = position_dict.get('debt_amount', 0)
                    canonical_debt = canonical_data.get('debt_amount', 0)
                    
                    if canonical_debt > 0:
                        debt_divergence_bps = abs(
                            (cached_debt - canonical_debt) * 10000 // canonical_debt
                        )
                        
                        if debt_divergence_bps > 0:
                            divergence = StateDivergence(
                                timestamp=datetime.utcnow(),
                                block_number=block_number,
                                protocol=protocol,
                                user=user,
                                field='debt_amount',
                                cached_value=cached_debt,
                                canonical_value=canonical_debt,
                                divergence_bps=debt_divergence_bps
                            )
                            divergences.append(divergence)
                            
                            # Check if divergence exceeds threshold
                            if debt_divergence_bps > 10:
                                logger.critical(
                                    f"CRITICAL: Debt divergence {debt_divergence_bps} BPS "
                                    f"exceeds 10 BPS threshold for {protocol}:{user}"
                                )
                                self.set_system_state(SystemState.HALTED)
                    
                    # Update cache with canonical values
                    position_dict['collateral_amount'] = canonical_collateral
                    position_dict['debt_amount'] = canonical_debt
                    position_dict['last_update_block'] = block_number
                    self.redis.set(position_key, json.dumps(position_dict), ttl=60)
                
                except Exception as e:
                    logger.error(f"Error reconciling position {position_key}: {e}")
                    continue
            
            # Log all divergences to database
            if divergences:
                await self._log_divergences(divergences)
                logger.info(f"Reconciled {len(position_keys)} positions, found {len(divergences)} divergences")
        
        except Exception as e:
            logger.error(f"Error during state reconciliation: {e}", exc_info=True)

    async def _fetch_canonical_position(
        self,
        protocol: str,
        user: str,
        block_number: int
    ) -> Optional[Dict[str, Any]]:
        """Fetch canonical position data from blockchain using archive node"""
        try:
            # Get protocol configuration
            protocol_config = self.config.protocols.get(protocol)
            if not protocol_config:
                return None
            
            # In a real implementation, this would call the lending protocol contract
            # using eth_call to get the canonical position data
            # For example: getUserAccountData(user) on Aave-like protocols
            
            # This is a placeholder that would be replaced with actual contract calls
            # using self.archive_web3.eth.call() with the appropriate contract ABI
            
            canonical_data = {
                'collateral_amount': 0,  # Would come from contract call
                'debt_amount': 0,  # Would come from contract call
            }
            
            return canonical_data
        
        except Exception as e:
            logger.error(f"Error fetching canonical position: {e}")
            return None
    
    async def _log_divergences(self, divergences: List[StateDivergence]):
        """Log state divergences to database"""
        try:
            with self.db.get_session() as session:
                for divergence in divergences:
                    db_divergence = StateDivergenceModel(
                        timestamp=divergence.timestamp,
                        block_number=divergence.block_number,
                        protocol=divergence.protocol,
                        user=divergence.user,
                        field=divergence.field,
                        cached_value=divergence.cached_value,
                        canonical_value=divergence.canonical_value,
                        divergence_bps=divergence.divergence_bps
                    )
                    session.add(db_divergence)
                
                logger.debug(f"Logged {len(divergences)} divergences to database")
        
        except Exception as e:
            logger.error(f"Error logging divergences: {e}")

    # ========================================================================
    # Position Cache Management (Task 3.5)
    # ========================================================================

    def get_position(self, protocol: str, user: str) -> Optional[Position]:
        """
        Get position from cache by protocol and user address.
        
        Args:
            protocol: Protocol name (e.g., 'moonwell', 'seamless')
            user: User address (checksummed)
        
        Returns:
            Position object if found, None otherwise
        """
        try:
            position_key = f"position:{protocol}:{user}"
            position_data = self.redis.get(position_key)
            
            if not position_data:
                logger.debug(f"Position not found in cache: {protocol}:{user}")
                return None
            
            # Parse JSON and create Position object
            position_dict = json.loads(position_data)
            position = Position(**position_dict)
            
            logger.debug(f"Retrieved position from cache: {protocol}:{user}")
            return position
        
        except Exception as e:
            logger.error(f"Error retrieving position from cache: {e}")
            return None
    
    def get_all_positions(self) -> List[Position]:
        """
        Get all positions from cache.
        
        Returns:
            List of Position objects
        """
        try:
            # Get all position keys
            position_keys = self.redis.keys("position:*")
            
            if not position_keys:
                logger.debug("No positions found in cache")
                return []
            
            positions = []
            
            for position_key in position_keys:
                try:
                    position_data = self.redis.get(position_key)
                    
                    if position_data:
                        position_dict = json.loads(position_data)
                        position = Position(**position_dict)
                        positions.append(position)
                
                except Exception as e:
                    logger.error(f"Error parsing position {position_key}: {e}")
                    continue
            
            logger.debug(f"Retrieved {len(positions)} positions from cache")
            return positions
        
        except Exception as e:
            logger.error(f"Error retrieving all positions: {e}")
            return []
    
    def update_position(
        self,
        protocol: str,
        user: str,
        collateral_asset: str,
        collateral_amount: int,
        debt_asset: str,
        debt_amount: int,
        liquidation_threshold: Decimal,
        block_number: int
    ) -> bool:
        """
        Update or create position in cache.
        
        Args:
            protocol: Protocol name
            user: User address (checksummed)
            collateral_asset: Collateral token address
            collateral_amount: Collateral amount in wei
            debt_asset: Debt token address
            debt_amount: Debt amount in wei
            liquidation_threshold: Protocol liquidation threshold
            block_number: Current block number
        
        Returns:
            True if successful, False otherwise
        """
        try:
            position_key = f"position:{protocol}:{user}"
            
            # Get existing position to preserve blocks_unhealthy
            existing_position = self.get_position(protocol, user)
            blocks_unhealthy = existing_position.blocks_unhealthy if existing_position else 0
            
            # Create position data
            position_data = {
                'protocol': protocol,
                'user': user,
                'collateral_asset': collateral_asset,
                'collateral_amount': collateral_amount,
                'debt_asset': debt_asset,
                'debt_amount': debt_amount,
                'liquidation_threshold': str(liquidation_threshold),
                'last_update_block': block_number,
                'blocks_unhealthy': blocks_unhealthy
            }
            
            # Store in cache with 60-second TTL
            self.redis.set(position_key, json.dumps(position_data), ttl=60)
            
            logger.debug(f"Updated position in cache: {protocol}:{user}")
            return True
        
        except Exception as e:
            logger.error(f"Error updating position in cache: {e}")
            return False
    
    def update_position_health(
        self,
        protocol: str,
        user: str,
        is_healthy: bool,
        block_number: int
    ) -> bool:
        """
        Update position health tracking (blocks_unhealthy counter).
        
        Args:
            protocol: Protocol name
            user: User address
            is_healthy: Whether position is healthy (health_factor >= 1.0)
            block_number: Current block number
        
        Returns:
            True if successful, False otherwise
        """
        try:
            position = self.get_position(protocol, user)
            
            if not position:
                logger.warning(f"Cannot update health for non-existent position: {protocol}:{user}")
                return False
            
            # Update blocks_unhealthy counter
            if is_healthy:
                # Reset counter when healthy
                position.blocks_unhealthy = 0
            else:
                # Increment counter when unhealthy
                position.blocks_unhealthy += 1
            
            position.last_update_block = block_number
            
            # Save back to cache
            position_key = f"position:{protocol}:{user}"
            self.redis.set(position_key, json.dumps(position.to_dict()), ttl=60)
            
            logger.debug(
                f"Updated position health: {protocol}:{user} "
                f"blocks_unhealthy={position.blocks_unhealthy}"
            )
            return True
        
        except Exception as e:
            logger.error(f"Error updating position health: {e}")
            return False
    
    def remove_position(self, protocol: str, user: str) -> bool:
        """
        Remove position from cache (e.g., after liquidation).
        
        Args:
            protocol: Protocol name
            user: User address
        
        Returns:
            True if successful, False otherwise
        """
        try:
            position_key = f"position:{protocol}:{user}"
            self.redis.delete(position_key)
            
            logger.debug(f"Removed position from cache: {protocol}:{user}")
            return True
        
        except Exception as e:
            logger.error(f"Error removing position from cache: {e}")
            return False
    
    async def rebuild_cache_from_blockchain(self) -> int:
        """
        Rebuild position cache from blockchain state.
        Called on Redis reconnection or cache invalidation.
        
        Returns:
            Number of positions rebuilt
        """
        logger.info("Rebuilding position cache from blockchain...")
        
        try:
            positions_rebuilt = 0
            
            # Get current block number
            current_block = self.current_web3.eth.block_number
            
            # For each configured protocol
            for protocol_name, protocol_config in self.config.protocols.items():
                try:
                    # In a real implementation, this would:
                    # 1. Query the lending protocol contract for all active positions
                    # 2. For each position, fetch current collateral and debt amounts
                    # 3. Store in cache
                    
                    # This is a placeholder implementation
                    # Real implementation would use contract events or state queries
                    
                    logger.info(f"Scanning {protocol_name} for active positions...")
                    
                    # Example: Query recent Borrow events to find active users
                    # Then call getUserAccountData for each user
                    # This would require the protocol contract ABI
                    
                    # For now, we'll just log that we would rebuild
                    logger.info(f"Would rebuild positions for {protocol_name}")
                
                except Exception as e:
                    logger.error(f"Error rebuilding cache for {protocol_name}: {e}")
                    continue
            
            logger.info(f"Cache rebuild complete: {positions_rebuilt} positions")
            return positions_rebuilt
        
        except Exception as e:
            logger.error(f"Error rebuilding cache from blockchain: {e}", exc_info=True)
            return 0
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            position_keys = self.redis.keys("position:*")
            
            # Count positions by protocol
            protocol_counts = {}
            total_positions = 0
            
            for position_key in position_keys:
                try:
                    position_data = self.redis.get(position_key)
                    if position_data:
                        position_dict = json.loads(position_data)
                        protocol = position_dict.get('protocol', 'unknown')
                        protocol_counts[protocol] = protocol_counts.get(protocol, 0) + 1
                        total_positions += 1
                except Exception:
                    continue
            
            stats = {
                'total_positions': total_positions,
                'positions_by_protocol': protocol_counts,
                'redis_connected': not self.redis._use_fallback,
                'current_block': self.current_block
            }
            
            return stats
        
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                'total_positions': 0,
                'positions_by_protocol': {},
                'redis_connected': False,
                'current_block': self.current_block
            }
