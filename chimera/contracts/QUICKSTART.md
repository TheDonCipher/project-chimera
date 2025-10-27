# Chimera Smart Contract - Quick Start Guide

## Prerequisites

- [Foundry](https://book.getfoundry.sh/getting-started/installation) installed
- Basic understanding of Solidity and smart contracts
- Access to Base RPC endpoints

## Installation

### 1. Install Foundry

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### 2. Install Dependencies

```bash
cd chimera/contracts
forge install OpenZeppelin/openzeppelin-contracts
```

### 3. Set Up Environment

Create a `.env` file:

```bash
# RPC Endpoints
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org

# API Keys
BASESCAN_API_KEY=your_basescan_api_key

# Deployment
PRIVATE_KEY=your_private_key_here
TREASURY_ADDRESS=your_treasury_address
```

## Compilation

```bash
forge build
```

Expected output:

```
[⠊] Compiling...
[⠒] Compiling 15 files with 0.8.20
[⠢] Solc 0.8.20 finished in 2.34s
Compiler run successful!
```

## Testing (Optional - Task 2.5)

Create test files in `test/` directory:

```bash
forge test
```

## Deployment

### Testnet Deployment (Base Sepolia)

1. Create deployment script at `script/Deploy.s.sol`
2. Run deployment:

```bash
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base_sepolia \
  --broadcast \
  --verify
```

### Mainnet Deployment (Base)

⚠️ **WARNING**: Only deploy to mainnet after:

- Comprehensive testing on testnet
- Professional security audit
- Code review by multiple developers

```bash
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base \
  --broadcast \
  --verify
```

## Contract Interaction

### Using Cast (Foundry CLI)

```bash
# Check treasury address
cast call $CONTRACT_ADDRESS "treasury()" --rpc-url base

# Execute liquidation (owner only)
cast send $CONTRACT_ADDRESS \
  "executeLiquidation(address,address,address,address,uint256,uint256,bool)" \
  $LENDING_PROTOCOL \
  $BORROWER \
  $COLLATERAL_ASSET \
  $DEBT_ASSET \
  $DEBT_AMOUNT \
  $MIN_PROFIT \
  true \
  --private-key $PRIVATE_KEY \
  --rpc-url base

# Pause contract (emergency)
cast send $CONTRACT_ADDRESS "pause()" \
  --private-key $PRIVATE_KEY \
  --rpc-url base
```

### Using Ethers.js

```javascript
const { ethers } = require('ethers');

// Connect to contract
const provider = new ethers.JsonRpcProvider(process.env.BASE_RPC_URL);
const wallet = new ethers.Wallet(process.env.PRIVATE_KEY, provider);
const chimera = new ethers.Contract(contractAddress, abi, wallet);

// Execute liquidation
const tx = await chimera.executeLiquidation(
  lendingProtocol,
  borrower,
  collateralAsset,
  debtAsset,
  debtAmount,
  minProfit,
  isAaveStyle
);

await tx.wait();
console.log('Liquidation executed:', tx.hash);
```

## Contract Addresses

### Constructor Parameters

When deploying, you need these addresses:

**Base Mainnet:**

- Treasury: Your treasury wallet address
- Aave Pool: `0xA238Dd80C259a72e81d7e4664a9801593F98d1c5`
- Balancer Vault: `0xBA12222222228d8Ba445958a75a0704d566BF2C8`
- Uniswap Router: `0x2626664c2603336E57B271c5C0b26F421741e481`
- Aerodrome Router: `0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43`

**Base Sepolia:**

- Research and add testnet addresses

## Common Operations

### Emergency Stop

```bash
# Pause
cast send $CONTRACT_ADDRESS "pause()" --private-key $PRIVATE_KEY --rpc-url base

# Unpause
cast send $CONTRACT_ADDRESS "unpause()" --private-key $PRIVATE_KEY --rpc-url base
```

### Update Treasury

```bash
cast send $CONTRACT_ADDRESS "setTreasury(address)" $NEW_TREASURY \
  --private-key $PRIVATE_KEY \
  --rpc-url base
```

### Rescue Stuck Tokens

```bash
cast send $CONTRACT_ADDRESS "rescueTokens(address,uint256)" \
  $TOKEN_ADDRESS \
  $AMOUNT \
  --private-key $PRIVATE_KEY \
  --rpc-url base
```

## Verification

After deployment, verify on BaseScan:

```bash
forge verify-contract \
  --chain-id 8453 \
  --num-of-optimizations 200 \
  --watch \
  --constructor-args $(cast abi-encode "constructor(address,address,address,address,address)" $TREASURY $AAVE_POOL $BALANCER_VAULT $UNISWAP_ROUTER $AERODROME_ROUTER) \
  --compiler-version v0.8.20 \
  $CONTRACT_ADDRESS \
  src/Chimera.sol:Chimera \
  --etherscan-api-key $BASESCAN_API_KEY
```

## Monitoring

### Watch Events

```bash
# Watch for liquidation events
cast logs --address $CONTRACT_ADDRESS \
  "LiquidationExecuted(address,address,uint256,uint256)" \
  --rpc-url base \
  --follow
```

### Check Contract State

```bash
# Get treasury
cast call $CONTRACT_ADDRESS "treasury()" --rpc-url base

# Check if paused
cast call $CONTRACT_ADDRESS "paused()" --rpc-url base

# Get owner
cast call $CONTRACT_ADDRESS "owner()" --rpc-url base
```

## Troubleshooting

### Compilation Errors

If you get import errors:

```bash
forge install OpenZeppelin/openzeppelin-contracts
forge remappings > remappings.txt
```

### Deployment Fails

- Check you have enough ETH for gas
- Verify all constructor addresses are correct
- Ensure private key has proper permissions

### Transaction Reverts

Common revert reasons:

- `InvalidAddress()`: One or more addresses is zero
- `InvalidAmount()`: Amount is zero
- `InsufficientProfit()`: Profit below minimum threshold
- `UnauthorizedFlashLoan()`: Flash loan callback from wrong address
- `Pausable: paused`: Contract is paused

## Security Checklist

Before mainnet deployment:

- [ ] Professional security audit completed
- [ ] All tests passing with >95% coverage
- [ ] Testnet validation completed (50+ liquidations)
- [ ] Emergency procedures documented
- [ ] Multisig wallet set as owner
- [ ] Treasury address verified
- [ ] All contract addresses verified on BaseScan
- [ ] Monitoring and alerting configured
- [ ] Bug bounty program prepared

## Support

For issues or questions:

1. Check the main README.md
2. Review IMPLEMENTATION_SUMMARY.md
3. Consult the design document at `.kiro/specs/mev-liquidation-bot/design.md`

## License

MIT
