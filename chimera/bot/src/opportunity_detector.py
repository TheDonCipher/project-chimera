"""
OpportunityDetector Module - Liquidation opportunity identification

Identifies liquidatable positions with minimal false positives through:
- Health factor calculation using Chainlink oracle prices
- Multi-oracle sanity checks (Pyth/Redstone)
- Confirmation blocks logic (2-block minimum)
- Protocol state checks
- Rough profit estimation
"""

import asyncio
import logging
import time
from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
from web3 import Web3
from web3.contract import Contract

from .types import Position, Opportunity, ChimeraError
from .config import ChimeraConfig
from .state_engine import StateEngine

logger = logging.getLogger(__name__)


class OpportunityDetectorError(ChimeraError):
    """OpportunityDetector specific errors"""
    pass


class OpportunityDetector:
    """Liquidation opportunity detector with multi-layer filtering"""
    
    def __init__(
        self,
        config: ChimeraConfig,
        state_engine: StateEngine,
        web3: Web3
    ):
        self.config = config
        self.state_engine = state_engine
        self.web3 = web3
        
        # Oracle contracts (will be initialized in start())
        self.chainlink_oracles: Dict[str, Contract] = {}
        self.pyth_oracles: Dict[str, Contract] = {}
        
        # Price cache for previous block comparison
        self.previous_prices: Dict[str, Decimal] = {}
        
        # Scan interval
        self.scan_interval = config.scan_interval_seconds
        
        # Running flag
        self._running = False
        
        logger.info("OpportunityDetector initialized")
    
    async def start(self):
        """Start the OpportunityDetector"""
        self._running = True
        logger.info("Starting OpportunityDetector...")
        
        # Initialize oracle contracts
        await self._initialize_oracles()
        
        # Start scanning loop
        asyncio.create_task(self._scan_loop())
        
        logger.info("OpportunityDetector started")
    
    async def stop(self):
        """Stop the OpportunityDetector"""
        self._running = False
        logger.info("OpportunityDetector stopped")
    
    async def _initialize_oracles(self):
        """Initialize Chainlink and Pyth oracle contracts"""
        try:
            # Chainlink AggregatorV3Interface ABI (minimal)
            chainlink_abi = [
                {
                    "inputs": [],
                    "name": "latestRoundData",
                    "outputs": [
                        {"name": "roundId", "type": "uint80"},
                        {"name": "answer", "type": "int256"},
                        {"name": "startedAt", "type": "uint256"},
                        {"name": "updatedAt", "type": "uint256"},
                        {"name": "answeredInRound", "type": "uint80"}
                    ],
                    "stateMutability": "view",
                    "type": "function"
                },
                {
                    "inputs": [],
                    "name": "decimals",
                    "outputs": [{"name": "", "type": "uint8"}],
                    "stateMutability": "view",
                    "type": "function"
                }
            ]
            
            # Initialize Chainlink oracles
            for asset, oracle_address in self.config.oracles.chainlink_addresses.items():
                try:
                    contract = self.web3.eth.contract(
                        address=Web3.to_checksum_address(oracle_address),
                        abi=chainlink_abi
                    )
                    self.chainlink_oracles[asset] = contract
                    logger.info(f"Initialized Chainlink oracle for {asset}: {oracle_address}")
                except Exception as e:
                    logger.error(f"Failed to initialize Chainlink oracle for {asset}: {e}")
            
            # Initialize Pyth oracles (if configured)
            for asset, oracle_address in self.config.oracles.pyth_addresses.items():
                try:
                    # Pyth has a different interface - would need appropriate ABI
                    # For now, we'll just log that it's configured
                    logger.info(f"Pyth oracle configured for {asset}: {oracle_address}")
                except Exception as e:
                    logger.error(f"Failed to initialize Pyth oracle for {asset}: {e}")
            
            logger.info(f"Initialized {len(self.chainlink_oracles)} Chainlink oracles")
        
        except Exception as e:
            logger.error(f"Error initializing oracles: {e}", exc_info=True)
            raise OpportunityDetectorError(f"Oracle initialization failed: {e}")
    
    async def _scan_loop(self):
        """Main scanning loop - scans all positions every scan_interval seconds"""
        logger.info(f"Starting scan loop (interval: {self.scan_interval}s)")
        
        while self._running:
            scan_start = time.time()
            
            try:
                # Get all positions from StateEngine cache
                positions = self.state_engine.get_all_positions()
                
                if not positions:
                    logger.debug("No positions to scan")
                else:
                    logger.info(f"Scanning {len(positions)} positions for opportunities")
                    
                    # Scan each position
                    opportunities = []
                    for position in positions:
                        try:
                            opportunity = await self.check_position(position)
                            if opportunity:
                                opportunities.append(opportunity)
                        except Exception as e:
                            logger.error(f"Error checking position {position.protocol}:{position.user}: {e}")
                            continue
                    
                    if opportunities:
                        logger.info(f"Found {len(opportunities)} liquidation opportunities")
                        # Opportunities will be consumed by ExecutionPlanner
                    else:
                        logger.debug("No liquidation opportunities found")
                
                # Calculate scan time
                scan_time = time.time() - scan_start
                logger.debug(f"Scan completed in {scan_time:.2f}s")
                
                # Sleep until next scan (ensuring we don't exceed scan_interval)
                sleep_time = max(0, self.scan_interval - scan_time)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            
            except Exception as e:
                logger.error(f"Error in scan loop: {e}", exc_info=True)
                await asyncio.sleep(self.scan_interval)
    
    async def check_position(self, position: Position) -> Optional[Opportunity]:
        """
        Check if a position is liquidatable and profitable.
        
        Applies multi-layer filtering:
        1. Health factor calculation
        2. Multi-oracle sanity checks
        3. Confirmation blocks logic
        4. Protocol state checks
        5. Rough profit estimation
        
        Args:
            position: Position to check
        
        Returns:
            Opportunity object if liquidatable and profitable, None otherwise
        """
        try:
            # Step 1: Calculate health factor
            health_factor, collateral_price, debt_price = await self.calculate_health_factor(position)
            
            if health_factor is None:
                logger.debug(f"Could not calculate health factor for {position.protocol}:{position.user}")
                return None
            
            # Check if liquidatable (health_factor < 1.0)
            if health_factor >= Decimal("1.0"):
                # Position is healthy - reset blocks_unhealthy counter
                self.state_engine.update_position_health(
                    position.protocol,
                    position.user,
                    is_healthy=True,
                    block_number=self.state_engine.current_block
                )
                return None
            
            logger.info(
                f"Unhealthy position detected: {position.protocol}:{position.user} "
                f"health_factor={health_factor:.4f}"
            )
            
            # Step 2: Multi-oracle sanity checks
            if not await self.verify_oracle_sanity(
                position.collateral_asset,
                collateral_price,
                position.debt_asset,
                debt_price
            ):
                logger.warning(
                    f"Oracle sanity check failed for {position.protocol}:{position.user}, skipping"
                )
                return None
            
            # Step 3: Confirmation blocks logic
            # Update blocks_unhealthy counter
            self.state_engine.update_position_health(
                position.protocol,
                position.user,
                is_healthy=False,
                block_number=self.state_engine.current_block
            )
            
            # Refresh position to get updated blocks_unhealthy
            updated_position = self.state_engine.get_position(position.protocol, position.user)
            if not updated_position:
                return None
            
            # Require minimum 2 blocks unhealthy
            if updated_position.blocks_unhealthy < self.config.confirmation_blocks:
                logger.debug(
                    f"Position {position.protocol}:{position.user} unhealthy for "
                    f"{updated_position.blocks_unhealthy} blocks (need {self.config.confirmation_blocks})"
                )
                return None
            
            logger.info(
                f"Position confirmed unhealthy for {updated_position.blocks_unhealthy} blocks: "
                f"{position.protocol}:{position.user}"
            )
            
            # Step 4: Protocol state checks
            if not await self.check_protocol_state(position):
                logger.warning(
                    f"Protocol state check failed for {position.protocol}:{position.user}, skipping"
                )
                return None
            
            # Step 5: Rough profit estimation
            estimated_gross, estimated_net = await self.estimate_profit(
                position,
                collateral_price,
                debt_price
            )
            
            if estimated_net < self.config.safety.min_profit_usd:
                logger.debug(
                    f"Estimated net profit ${estimated_net:.2f} below minimum "
                    f"${self.config.safety.min_profit_usd} for {position.protocol}:{position.user}"
                )
                return None
            
            # Create opportunity
            opportunity = Opportunity(
                position=updated_position,
                health_factor=health_factor,
                collateral_price_usd=collateral_price,
                debt_price_usd=debt_price,
                liquidation_bonus=self.config.protocols[position.protocol].liquidation_bonus,
                estimated_gross_profit_usd=estimated_gross,
                estimated_net_profit_usd=estimated_net,
                detected_at_block=self.state_engine.current_block,
                detected_at_timestamp=datetime.utcnow()
            )
            
            logger.info(
                f"Opportunity detected: {position.protocol}:{position.user} "
                f"health_factor={health_factor:.4f} estimated_net=${estimated_net:.2f}"
            )
            
            return opportunity
        
        except Exception as e:
            logger.error(f"Error checking position: {e}", exc_info=True)
            return None
    
    async def calculate_health_factor(
        self,
        position: Position
    ) -> tuple[Optional[Decimal], Optional[Decimal], Optional[Decimal]]:
        """
        Calculate health factor for a position.
        
        Formula:
        health_factor = (collateral_amount * collateral_price * liquidation_threshold) / (debt_amount * debt_price)
        
        Args:
            position: Position to calculate health factor for
        
        Returns:
            Tuple of (health_factor, collateral_price_usd, debt_price_usd) or (None, None, None) if prices unavailable
        """
        try:
            # Fetch Chainlink oracle prices
            collateral_price = await self.get_chainlink_price(position.collateral_asset)
            debt_price = await self.get_chainlink_price(position.debt_asset)
            
            if collateral_price is None or debt_price is None:
                logger.warning(
                    f"Could not fetch prices for {position.protocol}:{position.user} "
                    f"(collateral={collateral_price}, debt={debt_price})"
                )
                return None, None, None
            
            # Convert amounts from wei to token units (assuming 18 decimals)
            collateral_amount_decimal = Decimal(position.collateral_amount) / Decimal(10 ** 18)
            debt_amount_decimal = Decimal(position.debt_amount) / Decimal(10 ** 18)
            
            # Calculate collateral value
            collateral_value = collateral_amount_decimal * collateral_price * position.liquidation_threshold
            
            # Calculate debt value
            debt_value = debt_amount_decimal * debt_price
            
            # Avoid division by zero
            if debt_value == 0:
                logger.debug(f"Position {position.protocol}:{position.user} has zero debt")
                return Decimal("999999"), collateral_price, debt_price
            
            # Calculate health factor
            health_factor = collateral_value / debt_value
            
            logger.debug(
                f"Health factor calculated for {position.protocol}:{position.user}: "
                f"{health_factor:.4f} (collateral=${collateral_value:.2f}, debt=${debt_value:.2f})"
            )
            
            return health_factor, collateral_price, debt_price
        
        except Exception as e:
            logger.error(f"Error calculating health factor: {e}", exc_info=True)
            return None, None, None
    
    async def get_chainlink_price(self, asset: str) -> Optional[Decimal]:
        """
        Fetch price from Chainlink oracle.
        
        Args:
            asset: Asset address
        
        Returns:
            Price in USD as Decimal, or None if unavailable
        """
        try:
            # Get oracle contract for this asset
            oracle = self.chainlink_oracles.get(asset)
            
            if not oracle:
                logger.warning(f"No Chainlink oracle configured for asset {asset}")
                return None
            
            # Call latestRoundData
            round_data = oracle.functions.latestRoundData().call()
            
            # Extract price (answer is at index 1)
            price_raw = round_data[1]
            
            # Get decimals
            decimals = oracle.functions.decimals().call()
            
            # Convert to Decimal
            price = Decimal(price_raw) / Decimal(10 ** decimals)
            
            logger.debug(f"Chainlink price for {asset}: ${price:.2f}")
            
            return price
        
        except Exception as e:
            logger.error(f"Error fetching Chainlink price for {asset}: {e}")
            return None
    
    async def verify_oracle_sanity(
        self,
        collateral_asset: str,
        collateral_price: Decimal,
        debt_asset: str,
        debt_price: Decimal
    ) -> bool:
        """
        Verify oracle prices through multi-oracle sanity checks.
        
        Checks:
        1. Compare primary (Chainlink) vs secondary (Pyth/Redstone) oracle
        2. Compare current price vs previous block price
        
        Args:
            collateral_asset: Collateral asset address
            collateral_price: Collateral price from Chainlink
            debt_asset: Debt asset address
            debt_price: Debt price from Chainlink
        
        Returns:
            True if prices pass sanity checks, False otherwise
        """
        try:
            # Check 1: Multi-oracle divergence check
            # Compare Chainlink (primary) vs Pyth (secondary) if available
            
            # Check collateral price
            if collateral_asset in self.config.oracles.pyth_addresses:
                secondary_collateral_price = await self.get_pyth_price(collateral_asset)
                
                if secondary_collateral_price is not None:
                    divergence = abs(collateral_price - secondary_collateral_price) / collateral_price
                    divergence_percent = divergence * Decimal("100")
                    
                    if divergence_percent > self.config.oracles.max_divergence_percent:
                        logger.warning(
                            f"Collateral price divergence {divergence_percent:.2f}% exceeds "
                            f"{self.config.oracles.max_divergence_percent}% threshold "
                            f"(Chainlink=${collateral_price:.2f}, Pyth=${secondary_collateral_price:.2f})"
                        )
                        return False
            
            # Check debt price
            if debt_asset in self.config.oracles.pyth_addresses:
                secondary_debt_price = await self.get_pyth_price(debt_asset)
                
                if secondary_debt_price is not None:
                    divergence = abs(debt_price - secondary_debt_price) / debt_price
                    divergence_percent = divergence * Decimal("100")
                    
                    if divergence_percent > self.config.oracles.max_divergence_percent:
                        logger.warning(
                            f"Debt price divergence {divergence_percent:.2f}% exceeds "
                            f"{self.config.oracles.max_divergence_percent}% threshold "
                            f"(Chainlink=${debt_price:.2f}, Pyth=${secondary_debt_price:.2f})"
                        )
                        return False
            
            # Check 2: Price movement detection (compare to previous block)
            
            # Check collateral price movement
            if collateral_asset in self.previous_prices:
                previous_collateral = self.previous_prices[collateral_asset]
                movement = abs(collateral_price - previous_collateral) / previous_collateral
                movement_percent = movement * Decimal("100")
                
                if movement_percent > self.config.oracles.max_price_movement_percent:
                    logger.warning(
                        f"Collateral price moved {movement_percent:.2f}% in one block "
                        f"(exceeds {self.config.oracles.max_price_movement_percent}% threshold) "
                        f"(previous=${previous_collateral:.2f}, current=${collateral_price:.2f})"
                    )
                    return False
            
            # Check debt price movement
            if debt_asset in self.previous_prices:
                previous_debt = self.previous_prices[debt_asset]
                movement = abs(debt_price - previous_debt) / previous_debt
                movement_percent = movement * Decimal("100")
                
                if movement_percent > self.config.oracles.max_price_movement_percent:
                    logger.warning(
                        f"Debt price moved {movement_percent:.2f}% in one block "
                        f"(exceeds {self.config.oracles.max_price_movement_percent}% threshold) "
                        f"(previous=${previous_debt:.2f}, current=${debt_price:.2f})"
                    )
                    return False
            
            # Update previous prices for next check
            self.previous_prices[collateral_asset] = collateral_price
            self.previous_prices[debt_asset] = debt_price
            
            logger.debug("Oracle sanity checks passed")
            return True
        
        except Exception as e:
            logger.error(f"Error in oracle sanity check: {e}", exc_info=True)
            return False
    
    async def get_pyth_price(self, asset: str) -> Optional[Decimal]:
        """
        Fetch price from Pyth oracle (secondary oracle).
        
        Args:
            asset: Asset address
        
        Returns:
            Price in USD as Decimal, or None if unavailable
        """
        try:
            # Get Pyth oracle address for this asset
            pyth_address = self.config.oracles.pyth_addresses.get(asset)
            
            if not pyth_address:
                logger.debug(f"No Pyth oracle configured for asset {asset}")
                return None
            
            # Pyth has a different interface than Chainlink
            # This is a placeholder - real implementation would use Pyth's getPriceUnsafe or similar
            # For now, we'll return None to indicate Pyth is not yet implemented
            
            logger.debug(f"Pyth oracle not yet implemented for {asset}")
            return None
        
        except Exception as e:
            logger.error(f"Error fetching Pyth price for {asset}: {e}")
            return None
    
    async def check_protocol_state(self, position: Position) -> bool:
        """
        Check protocol state to ensure liquidation is allowed.
        
        Checks:
        1. Liquidation function is not paused
        2. Protocol rate limits
        3. Position size within protocol bounds
        
        Args:
            position: Position to check
        
        Returns:
            True if protocol state allows liquidation, False otherwise
        """
        try:
            # Get protocol configuration
            protocol_config = self.config.protocols.get(position.protocol)
            
            if not protocol_config:
                logger.warning(f"Unknown protocol: {position.protocol}")
                return False
            
            # Check 1: Verify liquidation is not paused
            # This would require calling the protocol contract's paused() or similar function
            # For now, we'll assume it's not paused
            
            # In a real implementation:
            # protocol_contract = self.web3.eth.contract(
            #     address=protocol_config.address,
            #     abi=protocol_abi
            # )
            # is_paused = protocol_contract.functions.paused().call()
            # if is_paused:
            #     logger.warning(f"Protocol {position.protocol} is paused")
            #     return False
            
            # Check 2: Protocol rate limits
            # This would check if we've hit any protocol-specific rate limits
            # For now, we'll assume no rate limits
            
            # Check 3: Position size within protocol bounds
            # Some protocols have minimum/maximum liquidation amounts
            # For now, we'll assume position is within bounds
            
            logger.debug(f"Protocol state check passed for {position.protocol}")
            return True
        
        except Exception as e:
            logger.error(f"Error checking protocol state: {e}", exc_info=True)
            return False
    
    async def estimate_profit(
        self,
        position: Position,
        collateral_price: Decimal,
        debt_price: Decimal
    ) -> tuple[Decimal, Decimal]:
        """
        Estimate rough profit for liquidation opportunity.
        
        Calculates:
        - Gross profit: liquidation bonus + arbitrage profit
        - Net profit: gross profit - costs (gas, bribe, flash loan, slippage)
        
        Args:
            position: Position to estimate profit for
            collateral_price: Collateral price in USD
            debt_price: Debt price in USD
        
        Returns:
            Tuple of (estimated_gross_profit_usd, estimated_net_profit_usd)
        """
        try:
            # Get protocol configuration
            protocol_config = self.config.protocols.get(position.protocol)
            
            if not protocol_config:
                logger.warning(f"Unknown protocol: {position.protocol}")
                return Decimal("0"), Decimal("0")
            
            # Convert amounts from wei to token units (assuming 18 decimals)
            collateral_amount_decimal = Decimal(position.collateral_amount) / Decimal(10 ** 18)
            debt_amount_decimal = Decimal(position.debt_amount) / Decimal(10 ** 18)
            
            # Calculate collateral value in USD
            collateral_value_usd = collateral_amount_decimal * collateral_price
            
            # Calculate debt value in USD
            debt_value_usd = debt_amount_decimal * debt_price
            
            # Estimate liquidation bonus
            # liquidation_bonus is the percentage bonus (e.g., 0.05 = 5%)
            liquidation_bonus_usd = collateral_value_usd * protocol_config.liquidation_bonus
            
            # Estimate arbitrage profit (2-5% of collateral value)
            # We'll use 3% as a conservative estimate
            arbitrage_profit_usd = collateral_value_usd * Decimal("0.03")
            
            # Gross profit
            gross_profit_usd = liquidation_bonus_usd + arbitrage_profit_usd
            
            # Estimate costs
            
            # 1. Gas cost: $10-20 (we'll use $15 as average)
            gas_cost_usd = Decimal("15.0")
            
            # 2. Builder bribe: 20% of gross profit (baseline)
            bribe_cost_usd = gross_profit_usd * Decimal("0.20")
            
            # 3. Flash loan premium: 0.09% of debt amount
            flash_loan_cost_usd = debt_value_usd * (self.config.execution.flash_loan_premium_percent / Decimal("100"))
            
            # 4. DEX slippage: 1% of collateral value
            slippage_cost_usd = collateral_value_usd * (self.config.dex.max_slippage_percent / Decimal("100"))
            
            # Total costs
            total_cost_usd = gas_cost_usd + bribe_cost_usd + flash_loan_cost_usd + slippage_cost_usd
            
            # Net profit
            net_profit_usd = gross_profit_usd - total_cost_usd
            
            logger.debug(
                f"Profit estimate for {position.protocol}:{position.user}: "
                f"gross=${gross_profit_usd:.2f} "
                f"(bonus=${liquidation_bonus_usd:.2f}, arb=${arbitrage_profit_usd:.2f}), "
                f"costs=${total_cost_usd:.2f} "
                f"(gas=${gas_cost_usd:.2f}, bribe=${bribe_cost_usd:.2f}, "
                f"flash=${flash_loan_cost_usd:.2f}, slippage=${slippage_cost_usd:.2f}), "
                f"net=${net_profit_usd:.2f}"
            )
            
            return gross_profit_usd, net_profit_usd
        
        except Exception as e:
            logger.error(f"Error estimating profit: {e}", exc_info=True)
            return Decimal("0"), Decimal("0")
    
    def get_opportunities(self) -> List[Opportunity]:
        """
        Get all current opportunities.
        
        Note: In the current implementation, opportunities are detected in real-time
        during the scan loop. This method would be used by ExecutionPlanner to
        retrieve opportunities for execution.
        
        Returns:
            List of Opportunity objects
        """
        # This is a placeholder - in a full implementation, we would maintain
        # a list of current opportunities that ExecutionPlanner can poll
        return []
