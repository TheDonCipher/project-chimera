# Chimera Contract Deployment Guide

This guide provides step-by-step instructions for deploying the Chimera MEV liquidation contract to Base L2 networks (testnet and mainnet).

## Table of Contents

- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Pre-Deployment Checklist](#pre-deployment-checklist)
- [Testnet Deployment (Base Sepolia)](#testnet-deployment-base-sepolia)
- [Mainnet Deployment (Base)](#mainnet-deployment-base)
- [Post-Deployment Verification](#post-deployment-verification)
- [Contract Verification on BaseScan](#contract-verification-on-basescan)
- [Operational Procedures](#operational-procedures)
- [Troubleshooting](#troubleshooting)
- [Rollback Procedure](#rollback-procedure)

## Prerequisites

### Required Software

1. **Foundry** - Ethereum development toolkit

   ```bash
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```

2. **Git** - Version control

   ```bash
   git --version
   ```

3. **Node.js** (optional, for additional tooling)
   ```bash
   node --version
   ```

### Required Accounts

1. **Deployer Wallet** - EOA with sufficient ETH for deployment gas

   - Testnet: ~0.01 ETH on Base Sepolia
   - Mainnet: ~0.05 ETH on Base

2. **Treasury Wallet** - Where profits will be sent (recommend hardware wallet for mainnet)

3. **BaseScan API Key** - For contract verification
   - Get from: https://basescan.org/myapikey

### Required Knowledge

- Understanding of smart contract deployment
- Familiarity with Foundry/Forge
- Basic understanding of the Chimera contract functionality
- Access to secure key management (hardware wallet recommended for mainnet)

## Environment Setup

### 1. Clone Repository and Install Dependencies

```bash
cd chimera/contracts
forge install
```

### 2. Create Environment File

Create a `.env` file in the `chimera/contracts` directory:

```bash
# Network RPC URLs
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org

# Deployer private key (NEVER commit this!)
DEPLOYER_PRIVATE_KEY=0x...

# Treasury address (where profits will be sent)
TREASURY_ADDRESS=0x...

# BaseScan API key for contract verification
BASESCAN_API_KEY=...

# Testnet protocol addresses (update these with actual addresses)
SEPOLIA_AAVE_POOL=0x...
SEPOLIA_BALANCER_VAULT=0x...
SEPOLIA_UNISWAP_ROUTER=0x...
SEPOLIA_AERODROME_ROUTER=0x...
```

### 3. Load Environment Variables

```bash
source .env
```

### 4. Verify Compilation

```bash
forge build
```

Expected output: `Compiler run successful!`

## Pre-Deployment Checklist

Before deploying, verify the following:

### Security Checklist

- [ ] Private keys are stored securely (hardware wallet or secure key management)
- [ ] `.env` file is in `.gitignore` and never committed
- [ ] Treasury address is correct and controlled by you
- [ ] Deployer wallet has sufficient ETH for gas
- [ ] Contract has been audited (REQUIRED for mainnet)
- [ ] All tests pass: `forge test`
- [ ] Code coverage is >95%: `forge coverage`

### Configuration Checklist

- [ ] Treasury address is set correctly in `.env`
- [ ] RPC URLs are configured and working
- [ ] BaseScan API key is valid
- [ ] Network-specific protocol addresses are correct
- [ ] Compiler version matches (0.8.20)
- [ ] Optimizer settings are correct (200 runs)

### Testing Checklist

- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] Fork tests pass on target network
- [ ] Gas estimates are acceptable
- [ ] Slither analysis shows no critical issues
- [ ] Manual code review completed

## Testnet Deployment (Base Sepolia)

### Step 1: Update Testnet Addresses

First, research and update the testnet protocol addresses in `script/Deploy.s.sol`:

```solidity
// Base Sepolia testnet addresses
address constant SEPOLIA_AAVE_POOL = 0x...; // Update with actual address
address constant SEPOLIA_BALANCER_VAULT = 0x...; // Update with actual address
address constant SEPOLIA_UNISWAP_ROUTER = 0x...; // Update with actual address
address constant SEPOLIA_AERODROME_ROUTER = 0x...; // Update with actual address
```

### Step 2: Dry Run (Simulation)

Test the deployment without broadcasting:

```bash
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base_sepolia \
  --sender $DEPLOYER_ADDRESS
```

Review the output carefully. Ensure:

- Gas estimates are reasonable
- Constructor parameters are correct
- No errors in simulation

### Step 3: Deploy to Testnet

Deploy and verify in one command:

```bash
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base_sepolia \
  --broadcast \
  --verify \
  --etherscan-api-key $BASESCAN_API_KEY
```

### Step 4: Save Deployment Information

The script automatically saves deployment info to `deployments/testnet-<timestamp>.txt`.

Additionally, manually record:

- Contract address
- Deployment transaction hash
- Block number
- Timestamp
- Gas used
- Deployer address

### Step 5: Verify Deployment

Check the contract on BaseScan:

```
https://sepolia.basescan.org/address/<CONTRACT_ADDRESS>
```

Verify:

- [ ] Contract is verified (green checkmark)
- [ ] Owner is correct
- [ ] Treasury is correct
- [ ] Contract is not paused
- [ ] All immutable variables are set correctly

### Step 6: Test Basic Functions

Test the deployed contract:

```bash
# Check owner
cast call <CONTRACT_ADDRESS> "owner()" --rpc-url base_sepolia

# Check treasury
cast call <CONTRACT_ADDRESS> "treasury()" --rpc-url base_sepolia

# Check paused status
cast call <CONTRACT_ADDRESS> "paused()" --rpc-url base_sepolia
```

### Step 7: Transfer Ownership (Optional)

If using a multisig for operations:

```bash
cast send <CONTRACT_ADDRESS> \
  "transferOwnership(address)" <MULTISIG_ADDRESS> \
  --rpc-url base_sepolia \
  --private-key $DEPLOYER_PRIVATE_KEY
```

Then accept ownership from the multisig.

## Mainnet Deployment (Base)

### ⚠️ CRITICAL: Mainnet Deployment Requirements

**DO NOT deploy to mainnet until:**

1. ✅ Professional security audit completed (Trail of Bits, OpenZeppelin, or Consensys Diligence)
2. ✅ All audit findings resolved
3. ✅ Testnet validation completed (50+ successful liquidations)
4. ✅ Inclusion rate >60% sustained on testnet
5. ✅ Simulation accuracy >90% on testnet
6. ✅ Legal review completed
7. ✅ Insurance coverage secured (if applicable)
8. ✅ Emergency response plan documented
9. ✅ Multisig setup for ownership (Gnosis Safe recommended)
10. ✅ Capital prepared ($1,000-2,000 minimum)

### Step 1: Final Security Review

Before mainnet deployment:

```bash
# Run all tests
forge test -vvv

# Check coverage
forge coverage

# Run Slither
slither src/Chimera.sol

# Run Mythril (if available)
myth analyze src/Chimera.sol
```

### Step 2: Prepare Mainnet Environment

Update `.env` with mainnet values:

```bash
DEPLOYER_PRIVATE_KEY=<HARDWARE_WALLET_OR_SECURE_KEY>
TREASURY_ADDRESS=<HARDWARE_WALLET_ADDRESS>
BASE_RPC_URL=https://mainnet.base.org
```

### Step 3: Dry Run on Mainnet Fork

```bash
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base \
  --sender $DEPLOYER_ADDRESS
```

### Step 4: Deploy to Mainnet

**⚠️ POINT OF NO RETURN - Review everything one last time**

```bash
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base \
  --broadcast \
  --verify \
  --etherscan-api-key $BASESCAN_API_KEY \
  --slow
```

The `--slow` flag adds delays between transactions for better reliability.

### Step 5: Immediate Post-Deployment Actions

1. **Save all deployment information** (contract address, tx hash, block number)
2. **Verify contract on BaseScan** (should be automatic with --verify)
3. **Transfer ownership to multisig** (CRITICAL)
4. **Fund operator wallet** with initial gas (0.1-0.2 ETH)
5. **Update bot configuration** with contract address
6. **Enable monitoring alerts**
7. **Notify team members**

### Step 6: Transfer to Multisig (REQUIRED)

```bash
# Initiate ownership transfer
cast send <CONTRACT_ADDRESS> \
  "transferOwnership(address)" <GNOSIS_SAFE_ADDRESS> \
  --rpc-url base \
  --private-key $DEPLOYER_PRIVATE_KEY

# Accept ownership from Gnosis Safe
# (Use Gnosis Safe UI to call acceptOwnership())
```

### Step 7: Initial Configuration

From the multisig:

1. Verify treasury address is correct
2. Keep contract paused initially
3. Test pause/unpause functionality
4. Test rescueTokens with small amount
5. Verify all access controls

### Step 8: Gradual Activation

1. **Week 1**: Deploy but keep paused, monitor for any issues
2. **Week 2**: Unpause, execute 1-2 test liquidations with small amounts
3. **Week 3**: Gradually increase to Tier 1 limits ($500 single / $2,500 daily)
4. **Monitor continuously** for first 30 days

## Post-Deployment Verification

### Automated Verification

Run the verification script:

```bash
forge script script/Verify.s.sol:Verify \
  --rpc-url <base|base_sepolia>
```

### Manual Verification Checklist

- [ ] Contract address matches deployment record
- [ ] Contract is verified on BaseScan (green checkmark)
- [ ] Owner is correct (multisig for mainnet)
- [ ] Treasury is correct
- [ ] All immutable addresses are correct:
  - [ ] Aave Pool
  - [ ] Balancer Vault
  - [ ] Uniswap Router
  - [ ] Aerodrome Router
- [ ] Contract is paused (for mainnet initial deployment)
- [ ] No unexpected events emitted
- [ ] Deployer wallet balance is as expected

### Integration Testing

Test the contract with the bot:

```bash
# From bot directory
python -m chimera.bot.main --dry-run --contract <CONTRACT_ADDRESS>
```

## Contract Verification on BaseScan

### Automatic Verification

If you used `--verify` flag during deployment, verification should be automatic.

Check status:

```
https://basescan.org/address/<CONTRACT_ADDRESS>#code
```

### Manual Verification

If automatic verification failed:

```bash
forge verify-contract \
  --chain-id <8453|84532> \
  --num-of-optimizations 200 \
  --watch \
  --constructor-args $(cast abi-encode "constructor(address,address,address,address,address)" \
    $TREASURY_ADDRESS \
    <AAVE_POOL> \
    <BALANCER_VAULT> \
    <UNISWAP_ROUTER> \
    <AERODROME_ROUTER>) \
  --etherscan-api-key $BASESCAN_API_KEY \
  --compiler-version v0.8.20+commit.a1b79de6 \
  <CONTRACT_ADDRESS> \
  src/Chimera.sol:Chimera
```

### Verification Troubleshooting

If verification fails:

1. **Check compiler version**: Must be exactly `v0.8.20+commit.a1b79de6`
2. **Check optimizer settings**: Must be 200 runs
3. **Check constructor args**: Must match exactly
4. **Wait 1-2 minutes**: Sometimes BaseScan needs time to index
5. **Try via UI**: Use BaseScan's web interface as fallback

## Operational Procedures

### Pause Contract (Emergency)

```bash
cast send <CONTRACT_ADDRESS> \
  "pause()" \
  --rpc-url base \
  --private-key $OWNER_PRIVATE_KEY
```

Or via Gnosis Safe UI for multisig.

### Unpause Contract

```bash
cast send <CONTRACT_ADDRESS> \
  "unpause()" \
  --rpc-url base \
  --private-key $OWNER_PRIVATE_KEY
```

### Update Treasury Address

```bash
cast send <CONTRACT_ADDRESS> \
  "setTreasury(address)" <NEW_TREASURY> \
  --rpc-url base \
  --private-key $OWNER_PRIVATE_KEY
```

### Rescue Stuck Tokens

```bash
cast send <CONTRACT_ADDRESS> \
  "rescueTokens(address,uint256)" <TOKEN_ADDRESS> <AMOUNT> \
  --rpc-url base \
  --private-key $OWNER_PRIVATE_KEY
```

### Transfer Ownership

```bash
# Step 1: Initiate transfer
cast send <CONTRACT_ADDRESS> \
  "transferOwnership(address)" <NEW_OWNER> \
  --rpc-url base \
  --private-key $CURRENT_OWNER_PRIVATE_KEY

# Step 2: Accept ownership (from new owner)
cast send <CONTRACT_ADDRESS> \
  "acceptOwnership()" \
  --rpc-url base \
  --private-key $NEW_OWNER_PRIVATE_KEY
```

## Troubleshooting

### Deployment Fails with "Insufficient Funds"

**Solution**: Ensure deployer wallet has enough ETH:

- Testnet: 0.01 ETH minimum
- Mainnet: 0.05 ETH minimum

### Verification Fails

**Solution**: Try manual verification with exact parameters. Check:

- Compiler version matches exactly
- Constructor args are correct
- Optimizer settings match (200 runs)

### Contract Deployed but Not Verified

**Solution**: Use the `Verify.s.sol` script to generate verification command:

```bash
forge script script/Verify.s.sol:Verify --rpc-url <network>
```

### RPC Connection Issues

**Solution**:

- Check RPC URL is correct
- Try alternative RPC provider
- Check network connectivity
- Verify API keys are valid

### Transaction Stuck/Pending

**Solution**:

- Check gas price is sufficient
- Wait for network congestion to clear
- Speed up transaction with higher gas price
- Cancel and retry if necessary

## Rollback Procedure

### If Deployment Fails Mid-Process

1. **Do not panic** - Failed deployments don't deploy contracts
2. **Review error message** carefully
3. **Fix the issue** (gas, parameters, etc.)
4. **Retry deployment**

### If Contract Deployed with Wrong Parameters

**⚠️ Cannot rollback - contracts are immutable**

Options:

1. **Deploy new contract** with correct parameters
2. **Update bot configuration** to use new contract
3. **Pause old contract** to prevent accidental use
4. **Document the incident**

### If Critical Bug Found Post-Deployment

1. **Immediately pause contract** via `pause()`
2. **Alert all team members**
3. **Assess severity** and impact
4. **If funds at risk**: Rescue tokens via `rescueTokens()`
5. **Deploy patched version**
6. **Conduct post-mortem**

### Emergency Contact List

Maintain a list of emergency contacts:

- Smart contract auditor
- Blockchain security expert
- Legal counsel
- Insurance provider (if applicable)
- Core team members

## Network Information

### Base Mainnet (Chain ID: 8453)

- **RPC URL**: https://mainnet.base.org
- **Explorer**: https://basescan.org
- **Aave V3 Pool**: `0xA238Dd80C259a72e81d7e4664a9801593F98d1c5`
- **Balancer Vault**: `0xBA12222222228d8Ba445958a75a0704d566BF2C8`
- **Uniswap V3 Router**: `0x2626664c2603336E57B271c5C0b26F421741e481`
- **Aerodrome Router**: `0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43`

### Base Sepolia Testnet (Chain ID: 84532)

- **RPC URL**: https://sepolia.base.org
- **Explorer**: https://sepolia.basescan.org
- **Faucet**: https://www.coinbase.com/faucets/base-ethereum-goerli-faucet
- **Protocol Addresses**: TBD (update in Deploy.s.sol)

## Additional Resources

- **Foundry Book**: https://book.getfoundry.sh/
- **Base Documentation**: https://docs.base.org/
- **OpenZeppelin Contracts**: https://docs.openzeppelin.com/contracts/
- **BaseScan API**: https://docs.basescan.org/

## Support

For deployment issues:

1. Check this documentation first
2. Review Foundry documentation
3. Check Base network status
4. Contact team lead or smart contract developer

---

**Last Updated**: 2025-10-27
**Version**: 1.0.0
**Maintainer**: Project Chimera Team
