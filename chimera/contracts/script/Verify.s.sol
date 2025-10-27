// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";

/**
 * @title Verify
 * @notice Helper script to verify Chimera contract on BaseScan
 * @dev This script generates the verification command for an already deployed contract
 * 
 * Usage:
 *   forge script script/Verify.s.sol:Verify --rpc-url base_sepolia
 */
contract Verify is Script {
    function run() external view {
        // Load environment variables
        address contractAddress = vm.envAddress("CONTRACT_ADDRESS");
        address treasury = vm.envAddress("TREASURY_ADDRESS");
        
        // Determine network
        uint256 chainId = block.chainid;
        bool isMainnet = chainId == 8453; // Base mainnet
        bool isTestnet = chainId == 84532; // Base Sepolia
        
        require(isMainnet || isTestnet, "Unsupported network");
        
        // Network-specific addresses
        address aavePool;
        address balancerVault;
        address uniswapRouter;
        address aerodromeRouter;
        
        if (isMainnet) {
            aavePool = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
            balancerVault = 0xBA12222222228d8Ba445958a75a0704d566BF2C8;
            uniswapRouter = 0x2626664c2603336E57B271c5C0b26F421741e481;
            aerodromeRouter = 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;
        } else {
            // Testnet addresses - update these with actual values
            aavePool = vm.envAddress("SEPOLIA_AAVE_POOL");
            balancerVault = vm.envAddress("SEPOLIA_BALANCER_VAULT");
            uniswapRouter = vm.envAddress("SEPOLIA_UNISWAP_ROUTER");
            aerodromeRouter = vm.envAddress("SEPOLIA_AERODROME_ROUTER");
        }
        
        console.log("=== Contract Verification Command ===\n");
        console.log("Network:", isMainnet ? "Base Mainnet" : "Base Sepolia");
        console.log("Chain ID:", chainId);
        console.log("Contract Address:", contractAddress);
        console.log("\nRun the following command:\n");
        
        console.log("forge verify-contract \\");
        console.log("  --chain-id", chainId, "\\");
        console.log("  --num-of-optimizations 200 \\");
        console.log("  --watch \\");
        console.log("  --constructor-args $(cast abi-encode \"constructor(address,address,address,address,address)\" \\");
        console.log("    ", treasury, "\\");
        console.log("    ", aavePool, "\\");
        console.log("    ", balancerVault, "\\");
        console.log("    ", uniswapRouter, "\\");
        console.log("    ", aerodromeRouter, ") \\");
        console.log("  --etherscan-api-key $BASESCAN_API_KEY \\");
        console.log("  --compiler-version v0.8.20+commit.a1b79de6 \\");
        console.log("  ", contractAddress, "\\");
        console.log("  src/Chimera.sol:Chimera");
        
        console.log("\n=== Alternative: Using Foundry's Built-in Verification ===\n");
        console.log("If you deployed with --broadcast, you can verify with:\n");
        console.log("forge script script/Deploy.s.sol:Deploy \\");
        console.log("  --rpc-url", isMainnet ? "base" : "base_sepolia", "\\");
        console.log("  --verify \\");
        console.log("  --resume");
    }
}
