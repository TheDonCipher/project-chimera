# Deployment Scripts

This directory contains Foundry scripts for deploying and verifying the Chimera contract.

## Scripts

### Deploy.s.sol

Main deployment script that:

- Detects network (Base Mainnet or Base Sepolia)
- Loads configuration from environment variables
- Deploys Chimera contract with correct protocol addresses
- Saves deployment information to `deployments/` directory
- Outputs verification command for manual verification if needed

**Usage:**

```bash
# Testnet deployment
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base_sepolia \
  --broadcast \
  --verify

# Mainnet deployment
forge script script/Deploy.s.sol:Deploy \
  --rpc-url base \
  --broadcast \
  --verify \
  --slow
```

### Verify.s.sol

Helper script to generate verification commands for already deployed contracts.

**Usage:**

```bash
# Set CONTRACT_ADDRESS in .env, then run:
forge script script/Verify.s.sol:Verify --rpc-url base_sepolia
```

## Environment Variables Required

Create a `.env` file in the `chimera/contracts` directory:

```bash
# Deployment
DEPLOYER_PRIVATE_KEY=0x...
TREASURY_ADDRESS=0x...
BASESCAN_API_KEY=...

# RPC URLs
BASE_RPC_URL=https://mainnet.base.org
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org

# Testnet addresses (update before testnet deployment)
SEPOLIA_AAVE_POOL=0x...
SEPOLIA_BALANCER_VAULT=0x...
SEPOLIA_UNISWAP_ROUTER=0x...
SEPOLIA_AERODROME_ROUTER=0x...

# For verification script
CONTRACT_ADDRESS=0x...
```

## Network Configuration

### Base Mainnet (Chain ID: 8453)

Protocol addresses are hardcoded in `Deploy.s.sol`:

- Aave V3 Pool: `0xA238Dd80C259a72e81d7e4664a9801593F98d1c5`
- Balancer Vault: `0xBA12222222228d8Ba445958a75a0704d566BF2C8`
- Uniswap V3 Router: `0x2626664c2603336E57B271c5C0b26F421741e481`
- Aerodrome Router: `0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43`

### Base Sepolia (Chain ID: 84532)

Protocol addresses must be set in `.env` before deployment:

- `SEPOLIA_AAVE_POOL`
- `SEPOLIA_BALANCER_VAULT`
- `SEPOLIA_UNISWAP_ROUTER`
- `SEPOLIA_AERODROME_ROUTER`

## Deployment Output

The deployment script:

1. Validates all parameters
2. Deploys the contract
3. Logs deployment details to console
4. Saves deployment info to `deployments/<network>-<timestamp>.txt`
5. Prints verification command for manual use if needed

## Security Notes

- Never commit `.env` file to version control
- Use hardware wallet for mainnet deployments
- Verify all addresses before deployment
- Transfer ownership to multisig after mainnet deployment
- Keep deployment records for audit trail

## Troubleshooting

**"Treasury address not set"**

- Set `TREASURY_ADDRESS` in `.env`

**"Testnet addresses not set"**

- Update testnet protocol addresses in `.env`

**Verification fails**

- Use `Verify.s.sol` to generate manual verification command
- Check BaseScan API key is valid
- Ensure compiler version matches (0.8.20)

## Documentation

For complete deployment instructions, see:

- [DEPLOYMENT.md](../DEPLOYMENT.md) - Full deployment guide
- [DEPLOYMENT_QUICKSTART.md](../DEPLOYMENT_QUICKSTART.md) - Quick reference

## Support

For issues with deployment scripts:

1. Check environment variables are set correctly
2. Verify network connectivity and RPC endpoints
3. Review Foundry documentation: https://book.getfoundry.sh/
4. Check Base network status: https://status.base.org/
