"""
Historical Data Collection Script

Collects historical liquidation events from Base mainnet for backtesting.
Scans last 1.3M blocks (~30 days at 2s/block) for liquidation events from
Moonwell and Seamless Protocol.

Requirements: 9.1
"""

import os
import sys
import csv
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from decimal import Decimal
from web3 import Web3
from web3.exceptions import BlockNotFound
from eth_abi import decode

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Liquidation event signatures
LIQUIDATION_EVENT_SIGNATURES = {
    # Common liquidation event signature across Aave-based protocols
    'LiquidationCall': '0xe413a321e8681d831f4dbccbca790d2952b56f977908e45be37335533e005286',
    # Compound-based protocols
    'LiquidateBorrow': '0x298637f684da70674f26509b10f07ec2fbc77a335ab1e7d6215a4b2484d8bb52',
}


class HistoricalDataCollector:
    """Collects historical liquidation data from Base mainnet"""
    
    def __init__(self, rpc_url: str, output_path: Path):
        """
        Initialize collector
        
        Args:
            rpc_url: Base mainnet RPC endpoint
            output_path: Path to save CSV file
        """
        self.w3 = Web3(Web3.HTTPProvider(rpc_url))
        self.output_path = output_path
        
        # Verify connection
        if not self.w3.is_connected():
            raise ConnectionError(f"Failed to connect to RPC: {rpc_url}")
        
        print(f"✓ Connected to Base mainnet (Chain ID: {self.w3.eth.chain_id})")
        
        # Protocol addresses on Base (update with actual addresses)
        self.protocols = {
            'moonwell': {
                'name': 'Moonwell',
                'address': '0x0000000000000000000000000000000000000000',  # Update
            },
            'seamless': {
                'name': 'Seamless Protocol',
                'address': '0x0000000000000000000000000000000000000000',  # Update
            }
        }
    
    def get_block_range(self, days: int = 30) -> tuple[int, int]:
        """
        Calculate block range for specified number of days
        
        Args:
            days: Number of days to scan
            
        Returns:
            Tuple of (start_block, end_block)
        """
        latest_block = self.w3.eth.block_number
        
        # Base L2 produces blocks every ~2 seconds
        blocks_per_day = 24 * 60 * 60 // 2  # ~43,200 blocks/day
        blocks_to_scan = days * blocks_per_day
        
        start_block = max(0, latest_block - blocks_to_scan)
        
        print(f"Block range: {start_block:,} to {latest_block:,} ({blocks_to_scan:,} blocks)")
        print(f"Estimated time period: ~{days} days")
        
        return start_block, latest_block
    
    def collect_liquidations(
        self,
        start_block: int,
        end_block: int,
        batch_size: int = 10000
    ) -> List[Dict[str, Any]]:
        """
        Collect liquidation events from specified block range
        
        Args:
            start_block: Starting block number
            end_block: Ending block number
            batch_size: Number of blocks to query per batch
            
        Returns:
            List of liquidation events
        """
        liquidations = []
        current_block = start_block
        
        print(f"\nScanning for liquidation events...")
        print(f"Batch size: {batch_size:,} blocks")
        
        while current_block <= end_block:
            batch_end = min(current_block + batch_size - 1, end_block)
            
            try:
                # Query logs for liquidation events
                logs = self._get_liquidation_logs(current_block, batch_end)
                
                # Parse logs
                for log in logs:
                    liquidation = self._parse_liquidation_log(log)
                    if liquidation:
                        liquidations.append(liquidation)
                
                # Progress update
                progress = ((current_block - start_block) / (end_block - start_block)) * 100
                print(f"Progress: {progress:.1f}% | Block: {current_block:,} | Found: {len(liquidations)}", end='\r')
                
                current_block = batch_end + 1
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"\nError scanning blocks {current_block}-{batch_end}: {e}")
                print("Retrying with smaller batch...")
                batch_size = max(1000, batch_size // 2)
                continue
        
        print(f"\n✓ Scan complete. Found {len(liquidations)} liquidations")
        return liquidations
    
    def _get_liquidation_logs(self, from_block: int, to_block: int) -> List[Dict]:
        """Get liquidation event logs for block range"""
        # Query for LiquidationCall events (Aave-based)
        liquidation_call_filter = {
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': [LIQUIDATION_EVENT_SIGNATURES['LiquidationCall']]
        }
        
        # Query for LiquidateBorrow events (Compound-based)
        liquidate_borrow_filter = {
            'fromBlock': from_block,
            'toBlock': to_block,
            'topics': [LIQUIDATION_EVENT_SIGNATURES['LiquidateBorrow']]
        }
        
        logs = []
        
        try:
            logs.extend(self.w3.eth.get_logs(liquidation_call_filter))
        except Exception as e:
            print(f"\nWarning: Failed to get LiquidationCall logs: {e}")
        
        try:
            logs.extend(self.w3.eth.get_logs(liquidate_borrow_filter))
        except Exception as e:
            print(f"\nWarning: Failed to get LiquidateBorrow logs: {e}")
        
        return logs
    
    def _parse_liquidation_log(self, log: Dict) -> Optional[Dict[str, Any]]:
        """Parse liquidation event log"""
        try:
            block = self.w3.eth.get_block(log['blockNumber'])
            tx = self.w3.eth.get_transaction(log['transactionHash'])
            receipt = self.w3.eth.get_transaction_receipt(log['transactionHash'])
            
            # Determine protocol
            protocol = self._identify_protocol(log['address'])
            
            # Parse event data based on signature
            event_signature = log['topics'][0].hex()
            
            if event_signature == LIQUIDATION_EVENT_SIGNATURES['LiquidationCall']:
                # Aave-based: LiquidationCall(collateralAsset, debtAsset, user, debtToCover, liquidatedCollateralAmount, liquidator, receiveAToken)
                parsed = self._parse_aave_liquidation(log)
            elif event_signature == LIQUIDATION_EVENT_SIGNATURES['LiquidateBorrow']:
                # Compound-based: LiquidateBorrow(liquidator, borrower, repayAmount, cTokenCollateral, seizeTokens)
                parsed = self._parse_compound_liquidation(log)
            else:
                return None
            
            if not parsed:
                return None
            
            # Get gas price
            gas_price_gwei = self.w3.from_wei(tx['gasPrice'], 'gwei')
            gas_used = receipt['gasUsed']
            
            return {
                'block_number': log['blockNumber'],
                'block_timestamp': block['timestamp'],
                'tx_hash': log['transactionHash'].hex(),
                'protocol': protocol,
                'borrower': parsed['borrower'],
                'liquidator': parsed['liquidator'],
                'collateral_asset': parsed['collateral_asset'],
                'debt_asset': parsed['debt_asset'],
                'debt_amount': parsed['debt_amount'],
                'collateral_seized': parsed['collateral_seized'],
                'gas_price_gwei': float(gas_price_gwei),
                'gas_used': gas_used,
                'tx_index': log['transactionIndex'],
            }
            
        except Exception as e:
            print(f"\nWarning: Failed to parse log: {e}")
            return None
    
    def _identify_protocol(self, address: str) -> str:
        """Identify protocol from contract address"""
        address_lower = address.lower()
        
        for protocol_id, protocol_info in self.protocols.items():
            if protocol_info['address'].lower() == address_lower:
                return protocol_id
        
        return 'unknown'
    
    def _parse_aave_liquidation(self, log: Dict) -> Optional[Dict]:
        """Parse Aave-based liquidation event"""
        try:
            # Topics: [signature, collateralAsset, debtAsset, user]
            collateral_asset = '0x' + log['topics'][1].hex()[-40:]
            debt_asset = '0x' + log['topics'][2].hex()[-40:]
            borrower = '0x' + log['topics'][3].hex()[-40:]
            
            # Data: debtToCover, liquidatedCollateralAmount, liquidator, receiveAToken
            data = bytes.fromhex(log['data'].hex()[2:])
            decoded = decode(['uint256', 'uint256', 'address', 'bool'], data)
            
            return {
                'borrower': Web3.to_checksum_address(borrower),
                'liquidator': Web3.to_checksum_address(decoded[2]),
                'collateral_asset': Web3.to_checksum_address(collateral_asset),
                'debt_asset': Web3.to_checksum_address(debt_asset),
                'debt_amount': decoded[0],
                'collateral_seized': decoded[1],
            }
        except Exception as e:
            print(f"\nWarning: Failed to parse Aave liquidation: {e}")
            return None
    
    def _parse_compound_liquidation(self, log: Dict) -> Optional[Dict]:
        """Parse Compound-based liquidation event"""
        try:
            # Topics: [signature, liquidator, borrower, repayAmount]
            liquidator = '0x' + log['topics'][1].hex()[-40:]
            borrower = '0x' + log['topics'][2].hex()[-40:]
            
            # Data: repayAmount, cTokenCollateral, seizeTokens
            data = bytes.fromhex(log['data'].hex()[2:])
            decoded = decode(['uint256', 'address', 'uint256'], data)
            
            return {
                'borrower': Web3.to_checksum_address(borrower),
                'liquidator': Web3.to_checksum_address(liquidator),
                'collateral_asset': Web3.to_checksum_address(decoded[1]),
                'debt_asset': '0x0000000000000000000000000000000000000000',  # Need to query
                'debt_amount': decoded[0],
                'collateral_seized': decoded[2],
            }
        except Exception as e:
            print(f"\nWarning: Failed to parse Compound liquidation: {e}")
            return None
    
    def save_to_csv(self, liquidations: List[Dict[str, Any]]):
        """Save liquidations to CSV file"""
        if not liquidations:
            print("No liquidations to save")
            return
        
        # Ensure output directory exists
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # CSV headers
        headers = [
            'block_number',
            'block_timestamp',
            'datetime',
            'tx_hash',
            'protocol',
            'borrower',
            'liquidator',
            'collateral_asset',
            'debt_asset',
            'debt_amount',
            'collateral_seized',
            'gas_price_gwei',
            'gas_used',
            'tx_index',
        ]
        
        with open(self.output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for liq in liquidations:
                # Add human-readable datetime
                liq['datetime'] = datetime.fromtimestamp(liq['block_timestamp']).isoformat()
                writer.writerow(liq)
        
        print(f"✓ Saved {len(liquidations)} liquidations to {self.output_path}")
    
    def collect_gas_prices(
        self,
        start_block: int,
        end_block: int,
        sample_interval: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Collect gas price samples from block range
        
        Args:
            start_block: Starting block number
            end_block: Ending block number
            sample_interval: Sample every N blocks
            
        Returns:
            List of gas price samples
        """
        gas_prices = []
        
        print(f"\nCollecting gas price samples (every {sample_interval} blocks)...")
        
        for block_num in range(start_block, end_block + 1, sample_interval):
            try:
                block = self.w3.eth.get_block(block_num)
                
                # Get base fee (EIP-1559)
                base_fee_gwei = self.w3.from_wei(block.get('baseFeePerGas', 0), 'gwei')
                
                gas_prices.append({
                    'block_number': block_num,
                    'timestamp': block['timestamp'],
                    'base_fee_gwei': float(base_fee_gwei),
                })
                
                if len(gas_prices) % 100 == 0:
                    print(f"Collected {len(gas_prices)} samples...", end='\r')
                
            except Exception as e:
                print(f"\nWarning: Failed to get block {block_num}: {e}")
                continue
        
        print(f"\n✓ Collected {len(gas_prices)} gas price samples")
        return gas_prices
    
    def save_gas_prices_to_csv(self, gas_prices: List[Dict[str, Any]], output_path: Path):
        """Save gas prices to CSV file"""
        if not gas_prices:
            print("No gas prices to save")
            return
        
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        headers = ['block_number', 'timestamp', 'datetime', 'base_fee_gwei']
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            
            for price in gas_prices:
                price['datetime'] = datetime.fromtimestamp(price['timestamp']).isoformat()
                writer.writerow(price)
        
        print(f"✓ Saved {len(gas_prices)} gas price samples to {output_path}")


def main():
    """Main execution"""
    # Get RPC URL from environment
    rpc_url = os.getenv('RPC_PRIMARY_HTTP')
    if not rpc_url or 'YOUR_KEY' in rpc_url:
        print("Error: Please set RPC_PRIMARY_HTTP environment variable with valid Alchemy key")
        print("Example: export RPC_PRIMARY_HTTP='https://base-mainnet.g.alchemy.com/v2/YOUR_KEY'")
        sys.exit(1)
    
    # Output paths
    data_dir = Path(__file__).parent.parent / 'data'
    liquidations_csv = data_dir / 'historical_liquidations.csv'
    gas_prices_csv = data_dir / 'historical_gas_prices.csv'
    
    print("=" * 80)
    print("Historical Data Collection for Chimera Backtesting")
    print("=" * 80)
    
    # Initialize collector
    collector = HistoricalDataCollector(rpc_url, liquidations_csv)
    
    # Get block range (30 days)
    start_block, end_block = collector.get_block_range(days=30)
    
    # Collect liquidations
    liquidations = collector.collect_liquidations(start_block, end_block)
    
    # Save liquidations
    collector.save_to_csv(liquidations)
    
    # Collect gas prices
    gas_prices = collector.collect_gas_prices(start_block, end_block, sample_interval=1000)
    
    # Save gas prices
    collector.save_gas_prices_to_csv(gas_prices, gas_prices_csv)
    
    print("\n" + "=" * 80)
    print("Data collection complete!")
    print(f"Liquidations: {liquidations_csv}")
    print(f"Gas prices: {gas_prices_csv}")
    print("=" * 80)


if __name__ == '__main__':
    main()
