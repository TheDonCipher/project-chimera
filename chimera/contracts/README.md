# Chimera Smart Contract

The Chimera smart contract executes atomic liquidations on Base L2 lending protocols using flash loans.

## Architecture

The contract implements a secure, atomic liquidation flow:

1. **Flash Loan**: Borrow debt tokens from Aave V3 or Balancer
2. **Liquidate**: Repay borrower's debt and seize collateral
3. **Swap**: Exchange collateral for debt tokens on Uniswap V3 or Aerodrome
4. **Verify**: Ensure profit meets minimum threshold
5. **Repay**: Return flash loan with premium
6. **Profit**: Transfer remaining profit to treasury

## Security Features

- **Ownable2Step**: Two-step ownership transfer prevents accidents
- **Pausable**: Emergency stop mechanism
- **ReentrancyGuard**: Prevents reentrancy attacks
- **SafeERC20**: Handles non-standard token implementations
- **Exact Approvals**: No infinite approvals, reset to 0 after use
- **Stateless**: No token balances stored between transactions

## Setup

### Prerequisites

Install Foundry:

```bash
curl -L https://foundry.paradigm.xyz | bash
foundryup
```

### Install Dependencies

```bash
cd chimera/contracts
forge install OpenZeppelin/openzeppelin-contracts
```

### Configuration

Create a `.env` file:

```bash
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
BASESCAN_API_KEY=your_api_key_here
PRIVATE_KEY=your_private_key_here
```

## Compilation

```bash
forge build
```

## Testing

```bash
# Run all tests
forge test

# Run with verbosity
forge test -vvv

# Run specific test
forge test --match-test testExecuteLiquidation

# Run with gas report
forge test --gas-report

# Run with coverage
forge coverage
```

## Deployment

**📚 Full Documentation**: See [DEPLOYMENT.md](DEPLOYMENT.md) for comprehensive deployment guide.

**⚡ Quick Start**: See [DEPLOYMENT_QUICKSTART.md](DEPLOYMENT_QUICKSTART.md) for quick reference.

### Quick Deployment Commands

#### Testnet (Base Sepolia)

```bash
# Deploy and verify
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base_sepolia \
  --broadcast \
  --verify
```

#### Mainnet (Base)

**⚠️ ONLY after audit, testnet validation, and legal review**

```bash
# Deploy and verify
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base \
  --broadcast \
  --verify \
  --slow
```

### Manual Verification

If automatic verification fails:

```bash
forge script script/Verify.s.sol:Verify --rpc-url <base|base_sepolia>
```

Or use the generated verification command from the deployment output.

## Contract Addresses

### Base Mainnet

- Aave V3 Pool: `0xA238Dd80C259a72e81d7e4664a9801593F98d1c5`
- Balancer Vault: `0xBA12222222228d8Ba445958a75a0704d566BF2C8`
- Uniswap V3 Router: `0x2626664c2603336E57B271c5C0b26F421741e481`
- Aerodrome Router: `0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43`

### Base Sepolia

- Aave V3 Pool: TBD
- Balancer Vault: TBD
- Uniswap V3 Router: TBD
- Aerodrome Router: TBD

## Usage

### Execute Liquidation (Aave Flash Loan)

```solidity
chimera.executeLiquidation(
    lendingProtocol,  // Moonwell or Seamless address
    borrower,         // Borrower address
    collateralAsset,  // Collateral token address
    debtAsset,        // Debt token address
    debtAmount,       // Amount to repay
    minProfit,        // Minimum profit threshold
    isAaveStyle       // true for Seamless, false for Moonwell
);
```

### Execute Liquidation (Balancer Flash Loan)

```solidity
chimera.executeLiquidationWithBalancer(
    lendingProtocol,
    borrower,
    collateralAsset,
    debtAsset,
    debtAmount,
    minProfit,
    isAaveStyle
);
```

### Emergency Functions

```solidity
// Pause contract
chimera.pause();

// Unpause contract
chimera.unpause();

// Update treasury
chimera.setTreasury(newTreasury);

// Rescue stuck tokens
chimera.rescueTokens(token, amount);
```

## Events

```solidity
event LiquidationExecuted(
    address indexed protocol,
    address indexed borrower,
    uint256 profitAmount,
    uint256 gasUsed
);

event TreasuryUpdated(
    address indexed oldTreasury,
    address indexed newTreasury
);
```

## Interfaces

- `IFlashLoanReceiver`: Aave V3 flash loan callback
- `IBalancerFlashLoanRecipient`: Balancer flash loan callback
- `IPool`: Aave V3 Pool interface
- `IBalancerVault`: Balancer Vault interface
- `ISwapRouter`: Uniswap V3 SwapRouter interface
- `IAerodromeRouter`: Aerodrome Router interface
- `ILendingProtocol`: Generic lending protocol interface
- `IAaveV3LendingPool`: Aave V3 style liquidation interface

## Security Considerations

1. **Flash Loan Callbacks**: Only accept callbacks from authorized flash loan providers
2. **Reentrancy**: Protected by ReentrancyGuard on all entry points
3. **Access Control**: Only owner can execute liquidations
4. **Token Approvals**: Always use exact amounts and reset to 0
5. **Profit Verification**: Always verify profit meets minimum threshold
6. **Emergency Stop**: Pausable mechanism for critical situations

## Audit Status

⚠️ **NOT AUDITED** - This contract has not been professionally audited. Do not use in production without a comprehensive security audit.

Recommended auditors:

- Trail of Bits
- OpenZeppelin
- Consensys Diligence
- Certora

## License

MIT
