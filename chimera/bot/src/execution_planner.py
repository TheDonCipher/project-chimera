"""
ExecutionPlanner Module - Transaction simulation and bundle construction

This module is responsible for:
- Building complete transactions with Chimera contract calls
- Simulating transactions on-chain (CRITICAL - never skip)
- Calculating Base L2 costs (L2 execution + L1 data posting)
- Optimizing builder bribes dynamically
- Selecting optimal submission paths
- Signing and submitting bundles
"""

import logging
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime
import json

from web3 import Web3
from web3.exceptions import ContractLogicError
from eth_account import Account
from eth_abi import encode

from .types import (
    Opportunity, Bundle, Transaction, SubmissionPath, ExecutionRecord,
    ExecutionStatus, SystemState, SimulationError, ExecutionError
)
from .config import ChimeraConfig
from .database import get_db_manager, ExecutionModel

logger = logging.getLogger(__name__)


# Chimera contract ABI (minimal interface for executeLiquidation)
CHIMERA_ABI = [
    {
        "inputs": [
            {"name": "lendingProtocol", "type": "address"},
            {"name": "borrower", "type": "address"},
            {"name": "collateralAsset", "type": "address"},
            {"name": "debtAsset", "type": "address"},
            {"name": "debtAmount", "type": "uint256"},
            {"name": "minProfit", "type": "uint256"},
            {"name": "isAaveStyle", "type": "bool"}
        ],
        "name": "executeLiquidation",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "treasury",
        "outputs": [{"name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Base L1 Gas Oracle ABI
L1_GAS_ORACLE_ABI = [
    {
        "inputs": [],
        "name": "l1BaseFee",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "overhead",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [],
        "name": "scalar",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    },
    {
        "inputs": [{"name": "_data", "type": "bytes"}],
        "name": "getL1Fee",
        "outputs": [{"name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function"
    }
]

# Chainlink ETH/USD Price Feed ABI
CHAINLINK_PRICE_FEED_ABI = [
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
    }
]


class SubmissionPathAdapter:
    """Base class for submission path adapters"""
    
    def __init__(self, w3: Web3, config: ChimeraConfig):
        self.w3 = w3
        self.config = config
        self.submission_count = 0
        self.success_count = 0
    
    @property
    def inclusion_rate(self) -> Decimal:
        """Calculate inclusion rate for this path"""
        if self.submission_count == 0:
            return Decimal("0")
        return Decimal(self.success_count) / Decimal(self.submission_count)
    
    def submit(self, signed_tx: str) -> str:
        """Submit signed transaction, return tx hash"""
        raise NotImplementedError
    
    def update_stats(self, success: bool):
        """Update submission statistics"""
        self.submission_count += 1
        if success:
            self.success_count += 1


class MempoolAdapter(SubmissionPathAdapter):
    """Direct mempool submission adapter"""
    
    def submit(self, signed_tx: str) -> str:
        """Submit to public mempool"""
        try:
            tx_hash = self.w3.eth.send_raw_transaction(signed_tx)
            logger.info(f"Submitted to mempool: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Mempool submission failed: {e}")
            raise ExecutionError(f"Mempool submission failed: {e}")


class BuilderAdapter(SubmissionPathAdapter):
    """Base-native builder submission adapter (placeholder)"""
    
    def submit(self, signed_tx: str) -> str:
        """Submit to builder (not yet implemented)"""
        # TODO: Implement builder submission when Base builders are available
        logger.warning("Builder submission not yet implemented, falling back to mempool")
        return MempoolAdapter(self.w3, self.config).submit(signed_tx)


class PrivateRPCAdapter(SubmissionPathAdapter):
    """Private RPC submission adapter"""
    
    def submit(self, signed_tx: str) -> str:
        """Submit via private RPC"""
        try:
            # Use backup RPC as "private" endpoint
            private_w3 = Web3(Web3.HTTPProvider(self.config.rpc.backup_http))
            tx_hash = private_w3.eth.send_raw_transaction(signed_tx)
            logger.info(f"Submitted via private RPC: {tx_hash.hex()}")
            return tx_hash.hex()
        except Exception as e:
            logger.error(f"Private RPC submission failed: {e}")
            raise ExecutionError(f"Private RPC submission failed: {e}")


class ExecutionPlanner:
    """
    ExecutionPlanner module - Simulates and constructs profitable transaction bundles
    
    CRITICAL: NEVER skip on-chain simulation. Every transaction MUST be simulated
    before submission to ensure profitability.
    """
    
    def __init__(self, config: ChimeraConfig, w3: Web3, operator_key: str):
        self.config = config
        self.w3 = w3
        self.operator_key = operator_key
        self.operator_account = Account.from_key(operator_key)
        
        # Initialize contract instances
        self.chimera_contract = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.execution.chimera_contract_address),
            abi=CHIMERA_ABI
        )
        
        self.l1_gas_oracle = self.w3.eth.contract(
            address=Web3.to_checksum_address(config.execution.base_l1_gas_oracle),
            abi=L1_GAS_ORACLE_ABI
        )
        
        # Initialize submission path adapters
        self.adapters: Dict[SubmissionPath, SubmissionPathAdapter] = {
            SubmissionPath.MEMPOOL: MempoolAdapter(w3, config),
            SubmissionPath.BUILDER: BuilderAdapter(w3, config),
            SubmissionPath.PRIVATE_RPC: PrivateRPCAdapter(w3, config)
        }
        
        # Bribe optimization state
        self.bribe_percent = config.execution.baseline_bribe_percent
        self.bribe_update_counter = 0
        
        logger.info(f"ExecutionPlanner initialized with operator {self.operator_account.address}")
    
    def plan_execution(
        self,
        opportunity: Opportunity,
        current_state: SystemState,
        eth_usd_price: Decimal
    ) -> Optional[Bundle]:
        """
        Plan execution for an opportunity
        
        This is the main entry point that orchestrates:
        1. Transaction construction
        2. On-chain simulation (CRITICAL)
        3. Cost calculation
        4. Profitability validation
        
        Returns Bundle if profitable, None otherwise
        """
        try:
            # Step 1: Build transaction
            transaction = self._build_transaction(opportunity)
            
            # Step 2: Simulate on-chain (CRITICAL - NEVER SKIP)
            simulation_result = self._simulate_transaction(transaction, opportunity)
            if simulation_result is None:
                logger.warning(f"Simulation failed for opportunity {opportunity.position.user}")
                self._log_rejection(opportunity, current_state, "simulation_failed")
                return None
            
            simulated_profit_wei, gas_estimate = simulation_result
            
            # Step 3: Calculate costs
            cost_breakdown = self._calculate_costs(
                transaction=transaction,
                gas_estimate=gas_estimate,
                simulated_profit_wei=simulated_profit_wei,
                eth_usd_price=eth_usd_price,
                opportunity=opportunity
            )
            
            if cost_breakdown is None:
                logger.warning(f"Cost calculation failed for opportunity {opportunity.position.user}")
                self._log_rejection(opportunity, current_state, "cost_calculation_failed")
                return None
            
            # Step 4: Validate profitability
            net_profit_usd = cost_breakdown['net_profit_usd']
            if net_profit_usd < self.config.safety.min_profit_usd:
                logger.info(
                    f"Opportunity rejected: net profit ${net_profit_usd:.2f} "
                    f"< minimum ${self.config.safety.min_profit_usd}"
                )
                self._log_rejection(opportunity, current_state, "insufficient_profit")
                return None
            
            # Step 5: Select submission path
            submission_path = self._select_submission_path(cost_breakdown)
            
            # Step 6: Create bundle
            bundle = Bundle(
                opportunity=opportunity,
                transaction=transaction,
                simulated_profit_wei=simulated_profit_wei,
                simulated_profit_usd=cost_breakdown['simulated_profit_usd'],
                gas_estimate=gas_estimate,
                l2_gas_cost_usd=cost_breakdown['l2_gas_cost_usd'],
                l1_data_cost_usd=cost_breakdown['l1_data_cost_usd'],
                bribe_usd=cost_breakdown['bribe_usd'],
                flash_loan_cost_usd=cost_breakdown['flash_loan_cost_usd'],
                slippage_cost_usd=cost_breakdown['slippage_cost_usd'],
                total_cost_usd=cost_breakdown['total_cost_usd'],
                net_profit_usd=net_profit_usd,
                submission_path=submission_path
            )
            
            logger.info(
                f"Bundle created: net profit ${net_profit_usd:.2f}, "
                f"path={submission_path.value}"
            )
            
            return bundle
            
        except Exception as e:
            logger.error(f"Error planning execution: {e}", exc_info=True)
            self._log_rejection(opportunity, current_state, f"error: {str(e)}")
            return None
    
    def _build_transaction(self, opportunity: Opportunity) -> Transaction:
        """
        Build complete transaction with Chimera contract executeLiquidation call
        
        Sub-task 5.1: Transaction construction
        """
        # Determine if protocol is Aave-style (Seamless) or Compound-style (Moonwell)
        is_aave_style = opportunity.position.protocol.lower() == "seamless"
        
        # Set minProfit to 50% of estimated profit (conservative)
        min_profit_wei = int(
            float(opportunity.estimated_gross_profit_usd) * 0.5 * 1e18 / 
            float(opportunity.debt_price_usd)
        )
        
        # Encode function call
        function_data = self.chimera_contract.encodeABI(
            fn_name='executeLiquidation',
            args=[
                Web3.to_checksum_address(opportunity.position.protocol),
                Web3.to_checksum_address(opportunity.position.user),
                Web3.to_checksum_address(opportunity.position.collateral_asset),
                Web3.to_checksum_address(opportunity.position.debt_asset),
                opportunity.position.debt_amount,
                min_profit_wei,
                is_aave_style
            ]
        )
        
        # Get current gas prices
        latest_block = self.w3.eth.get_block('latest')
        base_fee = latest_block.get('baseFeePerGas', 0)
        
        # Set priority fee (2 gwei for Base L2)
        priority_fee = self.w3.to_wei(2, 'gwei')
        
        # Max fee = base fee * 2 + priority fee (allow for base fee increase)
        max_fee_per_gas = (base_fee * 2) + priority_fee
        
        # Get nonce
        nonce = self.w3.eth.get_transaction_count(self.operator_account.address)
        
        # Estimate gas limit (will be refined during simulation)
        gas_limit = 500000  # Conservative estimate
        
        transaction = Transaction(
            to=self.config.execution.chimera_contract_address,
            data=function_data,
            value=0,
            gas_limit=gas_limit,
            max_fee_per_gas=max_fee_per_gas,
            max_priority_fee_per_gas=priority_fee,
            nonce=nonce,
            chain_id=self.config.chain_id
        )
        
        logger.debug(f"Transaction built: nonce={nonce}, gas_limit={gas_limit}")
        
        return transaction

    
    def _simulate_transaction(
        self,
        transaction: Transaction,
        opportunity: Opportunity
    ) -> Optional[Tuple[int, int]]:
        """
        Execute on-chain simulation (CRITICAL - NEVER SKIP)
        
        Sub-task 5.2: On-chain simulation
        
        Returns: (simulated_profit_wei, gas_estimate) or None if simulation fails
        """
        try:
            # Build transaction dict for eth_call
            tx_dict = {
                'from': self.operator_account.address,
                'to': transaction.to,
                'data': transaction.data,
                'value': transaction.value,
                'gas': transaction.gas_limit,
                'maxFeePerGas': transaction.max_fee_per_gas,
                'maxPriorityFeePerGas': transaction.max_priority_fee_per_gas
            }
            
            # Get treasury address to check profit
            treasury_address = self.chimera_contract.functions.treasury().call()
            
            # Get treasury balance before simulation
            debt_token = Web3.to_checksum_address(opportunity.position.debt_asset)
            debt_token_contract = self.w3.eth.contract(
                address=debt_token,
                abi=[{
                    "inputs": [{"name": "account", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "", "type": "uint256"}],
                    "stateMutability": "view",
                    "type": "function"
                }]
            )
            
            treasury_balance_before = debt_token_contract.functions.balanceOf(treasury_address).call()
            
            # Execute eth_call simulation
            try:
                self.w3.eth.call(tx_dict, 'latest')
            except ContractLogicError as e:
                logger.warning(f"Simulation reverted: {e}")
                self._log_simulation_failure(opportunity, f"revert: {str(e)}")
                return None
            except Exception as e:
                logger.warning(f"Simulation failed: {e}")
                self._log_simulation_failure(opportunity, f"error: {str(e)}")
                return None
            
            # Get treasury balance after simulation
            treasury_balance_after = debt_token_contract.functions.balanceOf(treasury_address).call()
            
            # Calculate profit (difference in treasury balance)
            simulated_profit_wei = treasury_balance_after - treasury_balance_before
            
            # Validate simulation success
            if simulated_profit_wei <= 0:
                logger.warning(f"Simulation shows no profit: {simulated_profit_wei}")
                self._log_simulation_failure(opportunity, "zero_or_negative_profit")
                return None
            
            # Estimate gas usage
            try:
                gas_estimate = self.w3.eth.estimate_gas(tx_dict)
            except Exception as e:
                logger.warning(f"Gas estimation failed: {e}, using conservative estimate")
                gas_estimate = transaction.gas_limit
            
            logger.info(
                f"Simulation successful: profit={simulated_profit_wei} wei, "
                f"gas={gas_estimate}"
            )
            
            return (simulated_profit_wei, gas_estimate)
            
        except Exception as e:
            logger.error(f"Simulation error: {e}", exc_info=True)
            self._log_simulation_failure(opportunity, f"exception: {str(e)}")
            return None
    
    def _calculate_costs(
        self,
        transaction: Transaction,
        gas_estimate: int,
        simulated_profit_wei: int,
        eth_usd_price: Decimal,
        opportunity: Opportunity
    ) -> Optional[Dict[str, Decimal]]:
        """
        Calculate complete cost breakdown including L2 and L1 costs
        
        Sub-tasks 5.3 and 5.4: Base L2 cost calculation and complete cost calculation
        
        Returns: Dictionary with cost breakdown or None if calculation fails
        """
        try:
            # Get current gas prices
            latest_block = self.w3.eth.get_block('latest')
            base_fee = latest_block.get('baseFeePerGas', 0)
            priority_fee = transaction.max_priority_fee_per_gas
            
            # Calculate L2 execution cost
            l2_gas_cost_wei = gas_estimate * (base_fee + priority_fee)
            l2_gas_cost_eth = Decimal(l2_gas_cost_wei) / Decimal(10**18)
            l2_gas_cost_usd = l2_gas_cost_eth * eth_usd_price
            
            # Calculate L1 data posting cost
            l1_data_cost_usd = self._calculate_l1_data_cost(
                transaction.data,
                eth_usd_price
            )
            
            # Total gas cost
            total_gas_cost_usd = l2_gas_cost_usd + l1_data_cost_usd
            
            # Convert simulated profit to USD
            simulated_profit_usd = (
                Decimal(simulated_profit_wei) / Decimal(10**18) *
                opportunity.debt_price_usd
            )
            
            # Calculate builder bribe
            bribe_usd = simulated_profit_usd * (self.bribe_percent / Decimal("100"))
            
            # Check if bribe exceeds cap
            max_bribe_usd = simulated_profit_usd * (
                self.config.execution.max_bribe_percent / Decimal("100")
            )
            if bribe_usd > max_bribe_usd:
                logger.warning(
                    f"Bribe ${bribe_usd:.2f} exceeds cap ${max_bribe_usd:.2f}"
                )
                return None
            
            # Calculate flash loan cost
            flash_loan_amount_usd = (
                Decimal(opportunity.position.debt_amount) / Decimal(10**18) *
                opportunity.debt_price_usd
            )
            flash_loan_cost_usd = flash_loan_amount_usd * (
                self.config.execution.flash_loan_premium_percent / Decimal("100")
            )
            
            # Calculate slippage cost (1% of collateral value)
            collateral_value_usd = (
                Decimal(opportunity.position.collateral_amount) / Decimal(10**18) *
                opportunity.collateral_price_usd
            )
            slippage_cost_usd = collateral_value_usd * (
                self.config.dex.max_slippage_percent / Decimal("100")
            )
            
            # Calculate total cost and net profit
            total_cost_usd = (
                total_gas_cost_usd +
                bribe_usd +
                flash_loan_cost_usd +
                slippage_cost_usd
            )
            
            net_profit_usd = simulated_profit_usd - total_cost_usd
            
            logger.debug(
                f"Cost breakdown: L2=${l2_gas_cost_usd:.2f}, "
                f"L1=${l1_data_cost_usd:.2f}, bribe=${bribe_usd:.2f}, "
                f"flash=${flash_loan_cost_usd:.2f}, slippage=${slippage_cost_usd:.2f}, "
                f"total=${total_cost_usd:.2f}, net=${net_profit_usd:.2f}"
            )
            
            return {
                'simulated_profit_usd': simulated_profit_usd,
                'l2_gas_cost_usd': l2_gas_cost_usd,
                'l1_data_cost_usd': l1_data_cost_usd,
                'bribe_usd': bribe_usd,
                'flash_loan_cost_usd': flash_loan_cost_usd,
                'slippage_cost_usd': slippage_cost_usd,
                'total_cost_usd': total_cost_usd,
                'net_profit_usd': net_profit_usd
            }
            
        except Exception as e:
            logger.error(f"Cost calculation error: {e}", exc_info=True)
            return None
    
    def _calculate_l1_data_cost(
        self,
        calldata: str,
        eth_usd_price: Decimal
    ) -> Decimal:
        """
        Calculate L1 data posting cost for Base L2
        
        Sub-task 5.3: Base L2 cost calculation
        """
        try:
            # Use the L1 gas oracle to get the L1 fee
            calldata_bytes = bytes.fromhex(calldata[2:] if calldata.startswith('0x') else calldata)
            l1_fee_wei = self.l1_gas_oracle.functions.getL1Fee(calldata_bytes).call()
            
            # Convert to USD
            l1_fee_eth = Decimal(l1_fee_wei) / Decimal(10**18)
            l1_fee_usd = l1_fee_eth * eth_usd_price
            
            logger.debug(f"L1 data cost: {l1_fee_wei} wei (${l1_fee_usd:.2f})")
            
            return l1_fee_usd
            
        except Exception as e:
            logger.warning(f"L1 cost calculation failed: {e}, using estimate")
            # Fallback: estimate based on calldata size
            calldata_size = len(calldata) // 2  # Convert hex to bytes
            # Rough estimate: $0.001 per byte
            return Decimal(calldata_size) * Decimal("0.001")
    
    def _select_submission_path(
        self,
        cost_breakdown: Dict[str, Decimal]
    ) -> SubmissionPath:
        """
        Select optimal submission path based on expected value
        
        Sub-task 5.6: Submission path selection
        """
        best_path = SubmissionPath.MEMPOOL
        best_ev = Decimal("-inf")
        
        simulated_profit = cost_breakdown['simulated_profit_usd']
        bribe = cost_breakdown['bribe_usd']
        
        for path, adapter in self.adapters.items():
            # Calculate expected value: EV = (profit * inclusion_rate) - (bribe + fees)
            inclusion_rate = adapter.inclusion_rate
            
            # Use default inclusion rate if no history
            if adapter.submission_count == 0:
                inclusion_rate = Decimal("0.70")  # Assume 70% for new paths
            
            # Bribe only applies to builder path
            path_bribe = bribe if path == SubmissionPath.BUILDER else Decimal("0")
            
            ev = (simulated_profit * inclusion_rate) - path_bribe
            
            logger.debug(
                f"Path {path.value}: EV=${ev:.2f} "
                f"(inclusion={inclusion_rate:.2%}, bribe=${path_bribe:.2f})"
            )
            
            if ev > best_ev:
                best_ev = ev
                best_path = path
        
        logger.info(f"Selected submission path: {best_path.value} (EV=${best_ev:.2f})")
        
        return best_path
    
    def submit_bundle(
        self,
        bundle: Bundle,
        current_state: SystemState
    ) -> Tuple[bool, Optional[str]]:
        """
        Sign and submit bundle to selected submission path
        
        Sub-task 5.7: Bundle signing and submission
        
        Returns: (success, tx_hash)
        """
        try:
            # Sign transaction
            signed_tx = self._sign_transaction(bundle.transaction)
            
            # Get adapter for submission path
            adapter = self.adapters[bundle.submission_path]
            
            # Submit with retry logic
            tx_hash = self._submit_with_retry(adapter, signed_tx, max_retries=3)
            
            if tx_hash is None:
                logger.error("Bundle submission failed after retries")
                self._log_execution(bundle, current_state, False, None, "submission_failed")
                return (False, None)
            
            # Log execution attempt
            self._log_execution(bundle, current_state, True, tx_hash, None)
            
            logger.info(f"Bundle submitted successfully: {tx_hash}")
            
            return (True, tx_hash)
            
        except Exception as e:
            logger.error(f"Bundle submission error: {e}", exc_info=True)
            self._log_execution(bundle, current_state, False, None, f"error: {str(e)}")
            return (False, None)
    
    def _sign_transaction(self, transaction: Transaction) -> str:
        """Sign transaction with operator private key"""
        tx_dict = {
            'nonce': transaction.nonce,
            'to': Web3.to_checksum_address(transaction.to),
            'value': transaction.value,
            'gas': transaction.gas_limit,
            'maxFeePerGas': transaction.max_fee_per_gas,
            'maxPriorityFeePerGas': transaction.max_priority_fee_per_gas,
            'data': transaction.data,
            'chainId': transaction.chain_id,
            'type': 2  # EIP-1559
        }
        
        signed = self.operator_account.sign_transaction(tx_dict)
        return signed.rawTransaction.hex()
    
    def _submit_with_retry(
        self,
        adapter: SubmissionPathAdapter,
        signed_tx: str,
        max_retries: int = 3
    ) -> Optional[str]:
        """Submit transaction with exponential backoff retry"""
        import time
        
        for attempt in range(max_retries):
            try:
                tx_hash = adapter.submit(signed_tx)
                return tx_hash
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.warning(
                        f"Submission attempt {attempt + 1} failed: {e}, "
                        f"retrying in {wait_time}s"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error(f"All {max_retries} submission attempts failed")
                    return None
        
        return None
    
    def update_bribe_model(self, recent_submissions: List[ExecutionRecord]):
        """
        Update bribe optimization model based on recent performance
        
        Sub-task 5.5: Dynamic bribe optimization
        """
        if len(recent_submissions) < 100:
            logger.debug(f"Not enough submissions for bribe update: {len(recent_submissions)}")
            return
        
        # Calculate inclusion rate over last 100 submissions
        included_count = sum(1 for record in recent_submissions if record.included)
        inclusion_rate = Decimal(included_count) / Decimal(len(recent_submissions))
        
        old_bribe = self.bribe_percent
        
        # Adjust bribe based on inclusion rate
        if inclusion_rate < Decimal("0.60"):
            # Increase bribe by 5%
            self.bribe_percent = min(
                self.bribe_percent + self.config.execution.bribe_increase_percent,
                self.config.execution.max_bribe_percent
            )
            logger.info(
                f"Inclusion rate {inclusion_rate:.2%} < 60%, "
                f"increasing bribe {old_bribe:.1f}% -> {self.bribe_percent:.1f}%"
            )
        elif inclusion_rate > Decimal("0.90"):
            # Decrease bribe by 2%
            self.bribe_percent = max(
                self.bribe_percent - self.config.execution.bribe_decrease_percent,
                self.config.execution.baseline_bribe_percent
            )
            logger.info(
                f"Inclusion rate {inclusion_rate:.2%} > 90%, "
                f"decreasing bribe {old_bribe:.1f}% -> {self.bribe_percent:.1f}%"
            )
        else:
            logger.debug(f"Inclusion rate {inclusion_rate:.2%} in target range, bribe unchanged")
        
        self.bribe_update_counter += 1
    
    def _log_simulation_failure(self, opportunity: Opportunity, reason: str):
        """Log simulation failure with opportunity details"""
        logger.warning(
            f"Simulation failed: {reason} | "
            f"protocol={opportunity.position.protocol}, "
            f"borrower={opportunity.position.user}, "
            f"health_factor={opportunity.health_factor}, "
            f"estimated_profit=${opportunity.estimated_gross_profit_usd}"
        )
    
    def _log_rejection(
        self,
        opportunity: Opportunity,
        current_state: SystemState,
        reason: str
    ):
        """Log opportunity rejection to database"""
        try:
            db_manager = get_db_manager()
            
            record = ExecutionModel(
                timestamp=datetime.utcnow(),
                block_number=opportunity.detected_at_block,
                protocol=opportunity.position.protocol,
                borrower=opportunity.position.user,
                collateral_asset=opportunity.position.collateral_asset,
                debt_asset=opportunity.position.debt_asset,
                health_factor=float(opportunity.health_factor),
                simulation_success=False,
                simulated_profit_wei=None,
                simulated_profit_usd=None,
                bundle_submitted=False,
                tx_hash=None,
                submission_path=None,
                bribe_wei=None,
                status=ExecutionStatus.REJECTED,
                included=False,
                inclusion_block=None,
                actual_profit_wei=None,
                actual_profit_usd=None,
                operator_address=self.operator_account.address,
                state_at_execution=current_state,
                rejection_reason=reason,
                error_message=None
            )
            
            with db_manager.get_session() as session:
                session.add(record)
            
        except Exception as e:
            logger.error(f"Failed to log rejection: {e}")
    
    def _log_execution(
        self,
        bundle: Bundle,
        current_state: SystemState,
        submitted: bool,
        tx_hash: Optional[str],
        error: Optional[str]
    ):
        """Log execution attempt to database"""
        try:
            db_manager = get_db_manager()
            
            # Calculate bribe in wei
            bribe_wei = int(
                float(bundle.bribe_usd) * 1e18 /
                float(bundle.opportunity.debt_price_usd)
            ) if bundle.bribe_usd > 0 else None
            
            record = ExecutionModel(
                timestamp=datetime.utcnow(),
                block_number=bundle.opportunity.detected_at_block,
                protocol=bundle.opportunity.position.protocol,
                borrower=bundle.opportunity.position.user,
                collateral_asset=bundle.opportunity.position.collateral_asset,
                debt_asset=bundle.opportunity.position.debt_asset,
                health_factor=float(bundle.opportunity.health_factor),
                simulation_success=True,
                simulated_profit_wei=bundle.simulated_profit_wei,
                simulated_profit_usd=float(bundle.simulated_profit_usd),
                bundle_submitted=submitted,
                tx_hash=tx_hash,
                submission_path=bundle.submission_path if submitted else None,
                bribe_wei=bribe_wei,
                status=ExecutionStatus.PENDING if submitted else ExecutionStatus.REJECTED,
                included=False,
                inclusion_block=None,
                actual_profit_wei=None,
                actual_profit_usd=None,
                operator_address=self.operator_account.address,
                state_at_execution=current_state,
                rejection_reason=error if not submitted else None,
                error_message=error
            )
            
            with db_manager.get_session() as session:
                session.add(record)
            
            logger.debug(f"Execution logged: submitted={submitted}, tx_hash={tx_hash}")
            
        except Exception as e:
            logger.error(f"Failed to log execution: {e}")
