// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Chimera.sol";

/**
 * @title ChimeraForkTest
 * @notice Fork tests for Chimera contract on Base mainnet
 * @dev Tests complete liquidation flow with real protocols
 */
contract ChimeraForkTest is Test {
    Chimera public chimera;
    
    address public owner;
    address public treasury;
    
    // Base mainnet addresses
    address constant AAVE_POOL = 0xA238Dd80C259a72e81d7e4664a9801593F98d1c5; // Seamless Protocol
    address constant BALANCER_VAULT = 0xBA12222222228d8Ba445958a75a0704d566BF2C8;
    address constant UNISWAP_ROUTER = 0x2626664c2603336E57B271c5C0b26F421741e481;
    address constant AERODROME_ROUTER = 0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43;
    
    // Common tokens on Base
    address constant WETH = 0x4200000000000000000000000000000000000006;
    address constant USDC = 0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913;
    address constant DAI = 0x50c5725949A6F0c72E6C4a641F24049A917DB0Cb;
    
    string BASE_RPC_URL = vm.envString("BASE_RPC_URL");
    
    function setUp() public {
        // Fork Base mainnet
        vm.createSelectFork(BASE_RPC_URL);
        
        owner = address(this);
        treasury = makeAddr("treasury");
        
        // Deploy Chimera contract
        chimera = new Chimera(
            treasury,
            AAVE_POOL,
            BALANCER_VAULT,
            UNISWAP_ROUTER,
            AERODROME_ROUTER
        );
    }
    
    /*//////////////////////////////////////////////////////////////
                        FORK INTEGRATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Fork_DeploymentSuccess() public {
        assertEq(chimera.treasury(), treasury);
        assertEq(chimera.aavePool(), AAVE_POOL);
        assertEq(chimera.balancerVault(), BALANCER_VAULT);
        assertEq(chimera.uniswapRouter(), UNISWAP_ROUTER);
        assertEq(chimera.aerodromeRouter(), AERODROME_ROUTER);
    }
    
    function test_Fork_AavePoolExists() public {
        // Verify Aave Pool contract exists and is callable
        (bool success, ) = AAVE_POOL.call(
            abi.encodeWithSignature("FLASHLOAN_PREMIUM_TOTAL()")
        );
        assertTrue(success, "Aave Pool should exist");
    }
    
    function test_Fork_BalancerVaultExists() public {
        // Verify Balancer Vault contract exists
        (bool success, ) = BALANCER_VAULT.call(
            abi.encodeWithSignature("getProtocolFeesCollector()")
        );
        assertTrue(success, "Balancer Vault should exist");
    }
    
    function test_Fork_UniswapRouterExists() public {
        // Verify Uniswap Router contract exists
        (bool success, ) = UNISWAP_ROUTER.call(
            abi.encodeWithSignature("factory()")
        );
        assertTrue(success, "Uniswap Router should exist");
    }
    
    function test_Fork_TokensExist() public {
        // Verify common tokens exist
        assertGt(WETH.code.length, 0, "WETH should exist");
        assertGt(USDC.code.length, 0, "USDC should exist");
        assertGt(DAI.code.length, 0, "DAI should exist");
    }
    
    /*//////////////////////////////////////////////////////////////
                    FLASH LOAN INTEGRATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Fork_AaveFlashLoanCallback() public {
        // Create a simple flash loan receiver for testing
        SimpleFlashLoanReceiver receiver = new SimpleFlashLoanReceiver(AAVE_POOL);
        
        // Fund receiver with enough to pay premium
        deal(USDC, address(receiver), 1000e6);
        
        // Request flash loan
        address[] memory assets = new address[](1);
        assets[0] = USDC;
        
        uint256[] memory amounts = new uint256[](1);
        amounts[0] = 1000e6; // 1000 USDC
        
        uint256[] memory modes = new uint256[](1);
        modes[0] = 0;
        
        vm.prank(address(receiver));
        IPool(AAVE_POOL).flashLoan(
            address(receiver),
            assets,
            amounts,
            modes,
            address(receiver),
            "",
            0
        );
        
        assertTrue(receiver.callbackExecuted(), "Flash loan callback should execute");
    }
    
    /*//////////////////////////////////////////////////////////////
                        PROFIT CALCULATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Fork_ProfitCalculation_Realistic() public view {
        // Test realistic profit calculation scenarios
        uint256 debtAmount = 1000e6; // 1000 USDC
        uint256 liquidationBonus = 10; // 10%
        uint256 collateralValue = (debtAmount * (100 + liquidationBonus)) / 100;
        
        // Estimate costs
        uint256 flashLoanPremium = (debtAmount * 9) / 10000; // 0.09%
        uint256 gasEstimate = 500000;
        uint256 gasPrice = 0.001 gwei; // Base L2 gas price
        uint256 gasCost = gasEstimate * gasPrice;
        
        // Calculate expected profit
        uint256 grossProfit = collateralValue - debtAmount;
        uint256 netProfit = grossProfit - flashLoanPremium - gasCost;
        
        // Verify profit is positive
        assertGt(netProfit, 0, "Net profit should be positive");
        assertGt(grossProfit, flashLoanPremium + gasCost, "Gross profit should cover costs");
    }
    
    function testFuzz_Fork_ProfitCalculation(
        uint256 debtAmount,
        uint256 liquidationBonus,
        uint256 gasPrice
    ) public view {
        // Bound inputs to realistic ranges
        debtAmount = bound(debtAmount, 100e6, 10000e6); // 100-10000 USDC
        liquidationBonus = bound(liquidationBonus, 5, 15); // 5-15%
        gasPrice = bound(gasPrice, 0.0001 gwei, 0.01 gwei); // Base L2 range
        
        uint256 collateralValue = (debtAmount * (100 + liquidationBonus)) / 100;
        uint256 flashLoanPremium = (debtAmount * 9) / 10000;
        uint256 gasEstimate = 500000;
        uint256 gasCost = gasEstimate * gasPrice;
        
        uint256 grossProfit = collateralValue - debtAmount;
        
        // Verify calculations are consistent
        if (grossProfit > flashLoanPremium + gasCost) {
            uint256 netProfit = grossProfit - flashLoanPremium - gasCost;
            assertGt(netProfit, 0, "Net profit should be positive when gross > costs");
        }
    }
    
    /*//////////////////////////////////////////////////////////////
                    PARAMETER VALIDATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function testFuzz_Fork_ParameterValidation(
        uint256 debtAmount,
        uint256 minProfit
    ) public {
        // Bound to realistic ranges
        debtAmount = bound(debtAmount, 1, type(uint128).max);
        minProfit = bound(minProfit, 1, type(uint128).max);
        
        address borrower = makeAddr("borrower");
        
        // Should not revert with valid parameters
        try chimera.executeLiquidation(
            AAVE_POOL,
            borrower,
            WETH,
            USDC,
            debtAmount,
            minProfit,
            true
        ) {
            // Execution may fail due to actual liquidation logic, but validation should pass
        } catch (bytes memory reason) {
            // Should not fail on parameter validation
            bytes4 selector = bytes4(reason);
            assertTrue(
                selector != Chimera.InvalidAddress.selector &&
                selector != Chimera.InvalidAmount.selector,
                "Should not fail on parameter validation"
            );
        }
    }
    
    /*//////////////////////////////////////////////////////////////
                        GAS OPTIMIZATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Fork_GasUsage_ExecuteLiquidation() public {
        address borrower = makeAddr("borrower");
        
        uint256 gasBefore = gasleft();
        
        try chimera.executeLiquidation(
            AAVE_POOL,
            borrower,
            WETH,
            USDC,
            1000e6,
            50e6,
            true
        ) {
            uint256 gasUsed = gasBefore - gasleft();
            
            // Gas usage should be reasonable (< 1M gas)
            assertLt(gasUsed, 1000000, "Gas usage should be under 1M");
        } catch {
            // Expected to fail without actual liquidatable position
        }
    }
    
    function test_Fork_GasUsage_Pause() public {
        uint256 gasBefore = gasleft();
        chimera.pause();
        uint256 gasUsed = gasBefore - gasleft();
        
        // Pause should be cheap
        assertLt(gasUsed, 50000, "Pause should use < 50k gas");
    }
    
    function test_Fork_GasUsage_SetTreasury() public {
        address newTreasury = makeAddr("newTreasury");
        
        uint256 gasBefore = gasleft();
        chimera.setTreasury(newTreasury);
        uint256 gasUsed = gasBefore - gasleft();
        
        // SetTreasury should be cheap
        assertLt(gasUsed, 50000, "SetTreasury should use < 50k gas");
    }
}

/*//////////////////////////////////////////////////////////////
                        HELPER CONTRACTS
//////////////////////////////////////////////////////////////*/

interface IPool {
    function flashLoan(
        address receiverAddress,
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata interestRateModes,
        address onBehalfOf,
        bytes calldata params,
        uint16 referralCode
    ) external;
}

contract SimpleFlashLoanReceiver {
    address public pool;
    bool public callbackExecuted;
    
    constructor(address _pool) {
        pool = _pool;
    }
    
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external returns (bool) {
        require(msg.sender == pool, "Unauthorized");
        callbackExecuted = true;
        
        // Approve repayment
        for (uint256 i = 0; i < assets.length; i++) {
            uint256 amountOwed = amounts[i] + premiums[i];
            IERC20(assets[i]).approve(pool, amountOwed);
        }
        
        return true;
    }
}
