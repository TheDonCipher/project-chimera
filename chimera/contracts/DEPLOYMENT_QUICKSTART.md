# Chimera Deployment Quick Start

Quick reference for deploying Chimera contract. See [DEPLOYMENT.md](DEPLOYMENT.md) for full documentation.

## Prerequisites

```bash
# Install Foundry
curl -L https://foundry.paradigm.xyz | bash
foundryup

# Install dependencies
cd chimera/contracts
forge install
```

## Environment Setup

Create `.env` file:

```bash
# RPC URLs
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org

# Deployment
DEPLOYER_PRIVATE_KEY=0x...
TREASURY_ADDRESS=0x...
BASESCAN_API_KEY=...

# Testnet addresses (update these)
SEPOLIA_AAVE_POOL=0x...
SEPOLIA_BALANCER_VAULT=0x...
SEPOLIA_UNISWAP_ROUTER=0x...
SEPOLIA_AERODROME_ROUTER=0x...
```

## Testnet Deployment

```bash
# 1. Update testnet addresses in script/Deploy.s.sol

# 2. Dry run
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base_sepolia

# 3. Deploy and verify
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base_sepolia \
  --broadcast \
  --verify

# 4. Test basic functions
cast call <CONTRACT_ADDRESS> "owner()" --rpc-url base_sepolia
cast call <CONTRACT_ADDRESS> "treasury()" --rpc-url base_sepolia
cast call <CONTRACT_ADDRESS> "paused()" --rpc-url base_sepolia
```

## Mainnet Deployment

**⚠️ ONLY after audit, testnet validation, and legal review**

```bash
# 1. Final checks
forge test -vvv
forge coverage
slither src/Chimera.sol

# 2. Dry run
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base

# 3. Deploy and verify
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base \
  --broadcast \
  --verify \
  --slow

# 4. Transfer to multisig (REQUIRED)
cast send <CONTRACT_ADDRESS> \
  "transferOwnership(address)" <GNOSIS_SAFE> \
  --rpc-url base \
  --private-key $DEPLOYER_PRIVATE_KEY

# 5. Accept from multisig (via Gnosis Safe UI)
```

## Manual Verification

If automatic verification fails:

```bash
forge verify-contract \
  --chain-id 8453 \
  --num-of-optimizations 200 \
  --watch \
  --constructor-args $(cast abi-encode "constructor(address,address,address,address,address)" \
    $TREASURY_ADDRESS \
    0xA238Dd80C259a72e81d7e4664a9801593F98d1c5 \
    0xBA12222222228d8Ba445958a75a0704d566BF2C8 \
    0x2626664c2603336E57B271c5C0b26F421741e481 \
    0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43) \
  --etherscan-api-key $BASESCAN_API_KEY \
  --compiler-version v0.8.20+commit.a1b79de6 \
  <CONTRACT_ADDRESS> \
  src/Chimera.sol:Chimera
```

## Common Operations

```bash
# Pause contract
cast send <CONTRACT_ADDRESS> "pause()" --rpc-url base --private-key $OWNER_KEY

# Unpause contract
cast send <CONTRACT_ADDRESS> "unpause()" --rpc-url base --private-key $OWNER_KEY

# Update treasury
cast send <CONTRACT_ADDRESS> "setTreasury(address)" <NEW_TREASURY> --rpc-url base --private-key $OWNER_KEY

# Rescue tokens
cast send <CONTRACT_ADDRESS> "rescueTokens(address,uint256)" <TOKEN> <AMOUNT> --rpc-url base --private-key $OWNER_KEY
```

## Network Info

### Base Mainnet (8453)

- RPC: https://mainnet.base.org
- Explorer: https://basescan.org

### Base Sepolia (84532)

- RPC: https://sepolia.base.org
- Explorer: https://sepolia.basescan.org
- Faucet: https://www.coinbase.com/faucets/base-ethereum-goerli-faucet

## Protocol Addresses (Base Mainnet)

- Aave V3 Pool: `0xA238Dd80C259a72e81d7e4664a9801593F98d1c5`
- Balancer Vault: `0xBA12222222228d8Ba445958a75a0704d566BF2C8`
- Uniswap V3 Router: `0x2626664c2603336E57B271c5C0b26F421741e481`
- Aerodrome Router: `0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43`

## Troubleshooting

| Issue              | Solution                              |
| ------------------ | ------------------------------------- |
| Insufficient funds | Add more ETH to deployer wallet       |
| Verification fails | Use manual verification command       |
| RPC timeout        | Try alternative RPC or wait and retry |
| Wrong parameters   | Deploy new contract (cannot modify)   |

## Pre-Deployment Checklist

- [ ] All tests pass: `forge test`
- [ ] Coverage >95%: `forge coverage`
- [ ] Slither clean: `slither src/Chimera.sol`
- [ ] Audit completed (mainnet only)
- [ ] Treasury address correct
- [ ] Deployer has sufficient ETH
- [ ] `.env` configured correctly
- [ ] Testnet validated (mainnet only)

---

For detailed documentation, see [DEPLOYMENT.md](DEPLOYMENT.md)
