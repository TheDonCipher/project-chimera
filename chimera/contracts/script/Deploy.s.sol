// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/Chimera.sol";

/**
 * @title Deploy
 * @notice Foundry deployment script for Chimera contract
 * @dev Supports both testnet (Base Sepolia) and mainnet (Base) deployments
 * 
 * Usage:
 *   Testnet: forge script script/Deploy.s.sol:Deploy --rpc-url base_sepolia --broadcast --verify
 *   Mainnet: forge script script/Deploy.s.sol:Deploy --rpc-url base --broadcast --verify
 */
contract Deploy is Script {
    // Base Mainnet addresses
    address constant BASE_AAVE_POOL = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5;
    address constant BASE_BALANCER_VAULT = 0xBA12222222228d8Ba445958a75a0704d566BF2C8;
    address constant BASE_UNISWAP_ROUTER = 0x2626664c2603336E57B271c5C0b26F421741e481;
    address constant BASE_AERODROME_ROUTER = 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;

    // Base Sepolia testnet addresses (placeholder - update with actual testnet addresses)
    address constant SEPOLIA_AAVE_POOL = 0x0000000000000000000000000000000000000000;
    address constant SEPOLIA_BALANCER_VAULT = 0x0000000000000000000000000000000000000000;
    address constant SEPOLIA_UNISWAP_ROUTER = 0x0000000000000000000000000000000000000000;
    address constant SEPOLIA_AERODROME_ROUTER = 0x0000000000000000000000000000000000000000;

    function run() external {
        // Load environment variables
        uint256 deployerPrivateKey = vm.envUint("DEPLOYER_PRIVATE_KEY");
        address treasury = vm.envAddress("TREASURY_ADDRESS");
        
        // Determine which network we're deploying to
        uint256 chainId = block.chainid;
        bool isMainnet = chainId == 8453; // Base mainnet
        bool isTestnet = chainId == 84532; // Base Sepolia
        
        require(isMainnet || isTestnet, "Unsupported network");
        
        // Select appropriate addresses based on network
        address aavePool;
        address balancerVault;
        address uniswapRouter;
        address aerodromeRouter;
        
        if (isMainnet) {
            console.log("Deploying to Base Mainnet (Chain ID: 8453)");
            aavePool = BASE_AAVE_POOL;
            balancerVault = BASE_BALANCER_VAULT;
            uniswapRouter = BASE_UNISWAP_ROUTER;
            aerodromeRouter = BASE_AERODROME_ROUTER;
        } else {
            console.log("Deploying to Base Sepolia Testnet (Chain ID: 84532)");
            aavePool = SEPOLIA_AAVE_POOL;
            balancerVault = SEPOLIA_BALANCER_VAULT;
            uniswapRouter = SEPOLIA_UNISWAP_ROUTER;
            aerodromeRouter = SEPOLIA_AERODROME_ROUTER;
            
            // Verify testnet addresses are set
            require(aavePool != address(0), "Testnet Aave Pool address not set");
            require(balancerVault != address(0), "Testnet Balancer Vault address not set");
            require(uniswapRouter != address(0), "Testnet Uniswap Router address not set");
            require(aerodromeRouter != address(0), "Testnet Aerodrome Router address not set");
        }
        
        // Validate treasury address
        require(treasury != address(0), "Treasury address not set");
        
        // Log deployment parameters
        console.log("Deployment Parameters:");
        console.log("  Treasury:", treasury);
        console.log("  Aave Pool:", aavePool);
        console.log("  Balancer Vault:", balancerVault);
        console.log("  Uniswap Router:", uniswapRouter);
        console.log("  Aerodrome Router:", aerodromeRouter);
        
        // Start broadcasting transactions
        vm.startBroadcast(deployerPrivateKey);
        
        // Deploy Chimera contract
        Chimera chimera = new Chimera(
            treasury,
            aavePool,
            balancerVault,
            uniswapRouter,
            aerodromeRouter
        );
        
        // Stop broadcasting
        vm.stopBroadcast();
        
        // Log deployment results
        console.log("\n=== Deployment Successful ===");
        console.log("Chimera Contract:", address(chimera));
        console.log("Owner:", chimera.owner());
        console.log("Treasury:", chimera.treasury());
        console.log("Paused:", chimera.paused());
        
        // Save deployment info to file
        string memory deploymentInfo = string.concat(
            "Network: ", isMainnet ? "Base Mainnet" : "Base Sepolia", "\n",
            "Chain ID: ", vm.toString(chainId), "\n",
            "Chimera Contract: ", vm.toString(address(chimera)), "\n",
            "Owner: ", vm.toString(chimera.owner()), "\n",
            "Treasury: ", vm.toString(chimera.treasury()), "\n",
            "Deployed at: ", vm.toString(block.timestamp), "\n",
            "Block Number: ", vm.toString(block.number), "\n"
        );
        
        string memory filename = string.concat(
            "deployments/",
            isMainnet ? "mainnet" : "testnet",
            "-",
            vm.toString(block.timestamp),
            ".txt"
        );
        
        vm.writeFile(filename, deploymentInfo);
        console.log("\nDeployment info saved to:", filename);
        
        // Print verification command
        console.log("\n=== Verification Command ===");
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
        console.log("  ", address(chimera), "\\");
        console.log("  src/Chimera.sol:Chimera");
    }
}
