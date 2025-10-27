// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Chimera.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title ChimeraIntegrationTest
 * @notice Integration tests for complete liquidation flow
 * @dev Tests end-to-end liquidation with realistic mock contracts
 */
contract ChimeraIntegrationTest is Test {
    Chimera public chimera;
    
    address public owner;
    address public treasury;
    
    MockERC20 public weth;
    MockERC20 public usdc;
    MockAavePool public aavePool;
    MockBalancerVault public balancerVault;
    MockUniswapRouter public uniswapRouter;
    MockAerodromeRouter public aerodromeRouter;
    MockSeamlessProtocol public seamlessProtocol;
    MockMoonwellProtocol public moonwellProtocol;
    
    address public borrower;
    
    event LiquidationExecuted(
        address indexed protocol,
        address indexed borrower,
        uint256 profitAmount,
        uint256 gasUsed
    );
    
    function setUp() public {
        owner = address(this);
        treasury = makeAddr("treasury");
        borrower = makeAddr("borrower");
        
        // Deploy tokens
        weth = new MockERC20("Wrapped Ether", "WETH", 18);
        usdc = new MockERC20("USD Coin", "USDC", 6);
        
        // Deploy mock protocols
        aavePool = new MockAavePool();
        balancerVault = new MockBalancerVault();
        uniswapRouter = new MockUniswapRouter();
        aerodromeRouter = new MockAerodromeRouter();
        seamlessProtocol = new MockSeamlessProtocol(address(weth), address(usdc));
        moonwellProtocol = new MockMoonwellProtocol(address(weth), address(usdc));
        
        // Deploy Chimera
        chimera = new Chimera(
            treasury,
            address(aavePool),
            address(balancerVault),
            address(uniswapRouter),
            address(aerodromeRouter)
        );
        
        // Setup mock protocols with tokens
        weth.mint(address(seamlessProtocol), 1000 ether);
        weth.mint(address(moonwellProtocol), 1000 ether);
        usdc.mint(address(aavePool), 1000000e6);
        usdc.mint(address(balancerVault), 1000000e6);
        weth.mint(address(uniswapRouter), 1000 ether);
        usdc.mint(address(uniswapRouter), 1000000e6);
    }
    
    /*//////////////////////////////////////////////////////////////
                    COMPLETE LIQUIDATION FLOW TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Integration_CompleteLiquidation_Seamless() public {
        uint256 debtAmount = 1000e6; // 1000 USDC
        uint256 minProfit = 50e6; // 50 USDC
        
        uint256 treasuryBalanceBefore = usdc.balanceOf(treasury);
        
        vm.expectEmit(true, true, false, false);
        emit LiquidationExecuted(
            address(seamlessProtocol),
            borrower,
            0, // We don't check exact profit amount
            0  // We don't check exact gas
        );
        
        chimera.executeLiquidation(
            address(seamlessProtocol),
            borrower,
            address(weth),
            address(usdc),
            debtAmount,
            minProfit,
            true // Aave style
        );
        
        uint256 treasuryBalanceAfter = usdc.balanceOf(treasury);
        uint256 profit = treasuryBalanceAfter - treasuryBalanceBefore;
        
        // Verify profit was transferred to treasury
        assertGt(profit, 0, "Profit should be positive");
        assertGe(profit, minProfit, "Profit should meet minimum");
        
        // Verify contract has no leftover tokens
        assertEq(usdc.balanceOf(address(chimera)), 0, "No USDC should remain");
        assertEq(weth.balanceOf(address(chimera)), 0, "No WETH should remain");
    }
    
    function test_Integration_CompleteLiquidation_Moonwell() public {
        uint256 debtAmount = 1000e6; // 1000 USDC
        uint256 minProfit = 50e6; // 50 USDC
        
        uint256 treasuryBalanceBefore = usdc.balanceOf(treasury);
        
        vm.expectEmit(true, true, false, false);
        emit LiquidationExecuted(
            address(moonwellProtocol),
            borrower,
            0,
            0
        );
        
        chimera.executeLiquidation(
            address(moonwellProtocol),
            borrower,
            address(weth),
            address(usdc),
            debtAmount,
            minProfit,
            false // Compound style
        );
        
        uint256 treasuryBalanceAfter = usdc.balanceOf(treasury);
        uint256 profit = treasuryBalanceAfter - treasuryBalanceBefore;
        
        assertGt(profit, 0, "Profit should be positive");
        assertGe(profit, minProfit, "Profit should meet minimum");
        assertEq(usdc.balanceOf(address(chimera)), 0, "No USDC should remain");
        assertEq(weth.balanceOf(address(chimera)), 0, "No WETH should remain");
    }
    
    function test_Integration_CompleteLiquidation_WithBalancer() public {
        uint256 debtAmount = 1000e6;
        uint256 minProfit = 50e6;
        
        uint256 treasuryBalanceBefore = usdc.balanceOf(treasury);
        
        chimera.executeLiquidationWithBalancer(
            address(seamlessProtocol),
            borrower,
            address(weth),
            address(usdc),
            debtAmount,
            minProfit,
            true
        );
        
        uint256 treasuryBalanceAfter = usdc.balanceOf(treasury);
        uint256 profit = treasuryBalanceAfter - treasuryBalanceBefore;
        
        assertGt(profit, 0, "Profit should be positive");
        assertGe(profit, minProfit, "Profit should meet minimum");
    }
    
    function test_Integration_RevertIf_InsufficientProfit() public {
        uint256 debtAmount = 1000e6;
        uint256 minProfit = 200e6; // Set unrealistically high minimum
        
        vm.expectRevert(Chimera.InsufficientProfit.selector);
        chimera.executeLiquidation(
            address(seamlessProtocol),
            borrower,
            address(weth),
            address(usdc),
            debtAmount,
            minProfit,
            true
        );
    }
    
    function test_Integration_RevertIf_NoCollateralReceived() public {
        // Deploy protocol that doesn't send collateral
        MockBrokenProtocol brokenProtocol = new MockBrokenProtocol();
        
        vm.expectRevert(Chimera.InsufficientProfit.selector);
        chimera.executeLiquidation(
            address(brokenProtocol),
            borrower,
            address(weth),
            address(usdc),
            1000e6,
            50e6,
            true
        );
    }
    
    /*//////////////////////////////////////////////////////////////
                        FLASH LOAN FLOW TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Integration_AaveFlashLoanFlow() public {
        uint256 debtAmount = 1000e6;
        
        uint256 poolBalanceBefore = usdc.balanceOf(address(aavePool));
        
        chimera.executeLiquidation(
            address(seamlessProtocol),
            borrower,
            address(weth),
            address(usdc),
            debtAmount,
            50e6,
            true
        );
        
        uint256 poolBalanceAfter = usdc.balanceOf(address(aavePool));
        
        // Pool should have received repayment + premium
        uint256 premium = (debtAmount * 9) / 10000; // 0.09%
        assertGe(poolBalanceAfter, poolBalanceBefore + premium, "Pool should profit from premium");
    }
    
    function test_Integration_BalancerFlashLoanFlow() public {
        uint256 debtAmount = 1000e6;
        
        uint256 vaultBalanceBefore = usdc.balanceOf(address(balancerVault));
        
        chimera.executeLiquidationWithBalancer(
            address(seamlessProtocol),
            borrower,
            address(weth),
            address(usdc),
            debtAmount,
            50e6,
            true
        );
        
        uint256 vaultBalanceAfter = usdc.balanceOf(address(balancerVault));
        
        // Vault should have received repayment + fee
        uint256 fee = (debtAmount * 5) / 10000; // 0.05%
        assertGe(vaultBalanceAfter, vaultBalanceBefore + fee, "Vault should profit from fee");
    }
    
    /*//////////////////////////////////////////////////////////////
                        SWAP INTEGRATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Integration_UniswapSwap() public {
        // This is tested as part of complete liquidation
        // Verify swap happens correctly
        chimera.executeLiquidation(
            address(seamlessProtocol),
            borrower,
            address(weth),
            address(usdc),
            1000e6,
            50e6,
            true
        );
        
        // If we got here, swap succeeded
        assertTrue(true);
    }
    
    /*//////////////////////////////////////////////////////////////
                        FUZZ INTEGRATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function testFuzz_Integration_CompleteLiquidation(
        uint256 debtAmount,
        uint256 minProfitPercent
    ) public {
        // Bound inputs to realistic ranges
        debtAmount = bound(debtAmount, 100e6, 10000e6); // 100-10000 USDC
        minProfitPercent = bound(minProfitPercent, 1, 8); // 1-8% of debt
        
        uint256 minProfit = (debtAmount * minProfitPercent) / 100;
        
        uint256 treasuryBalanceBefore = usdc.balanceOf(treasury);
        
        try chimera.executeLiquidation(
            address(seamlessProtocol),
            borrower,
            address(weth),
            address(usdc),
            debtAmount,
            minProfit,
            true
        ) {
            uint256 treasuryBalanceAfter = usdc.balanceOf(treasury);
            uint256 profit = treasuryBalanceAfter - treasuryBalanceBefore;
            
            // If execution succeeded, verify profit
            assertGe(profit, minProfit, "Profit should meet minimum");
            assertEq(usdc.balanceOf(address(chimera)), 0, "No tokens should remain");
        } catch (bytes memory reason) {
            // If it reverted, should be due to insufficient profit
            bytes4 selector = bytes4(reason);
            assertEq(selector, Chimera.InsufficientProfit.selector, "Should revert with InsufficientProfit");
        }
    }
    
    function testFuzz_Integration_MultipleExecutions(uint8 executionCount) public {
        executionCount = uint8(bound(executionCount, 1, 10));
        
        uint256 debtAmount = 1000e6;
        uint256 minProfit = 50e6;
        
        for (uint256 i = 0; i < executionCount; i++) {
            uint256 treasuryBalanceBefore = usdc.balanceOf(treasury);
            
            chimera.executeLiquidation(
                address(seamlessProtocol),
                borrower,
                address(weth),
                address(usdc),
                debtAmount,
                minProfit,
                true
            );
            
            uint256 treasuryBalanceAfter = usdc.balanceOf(treasury);
            assertGt(treasuryBalanceAfter, treasuryBalanceBefore, "Each execution should be profitable");
        }
    }
}

/*//////////////////////////////////////////////////////////////
                        MOCK CONTRACTS
//////////////////////////////////////////////////////////////*/

contract MockERC20 is ERC20 {
    uint8 private _decimals;
    
    constructor(string memory name, string memory symbol, uint8 decimals_) ERC20(name, symbol) {
        _decimals = decimals_;
    }
    
    function decimals() public view override returns (uint8) {
        return _decimals;
    }
    
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }
}

contract MockSeamlessProtocol {
    address public collateralToken;
    address public debtToken;
    
    constructor(address _collateralToken, address _debtToken) {
        collateralToken = _collateralToken;
        debtToken = _debtToken;
    }
    
    function liquidationCall(
        address collateralAsset,
        address debtAsset,
        address borrower,
        uint256 debtToCover,
        bool receiveAToken
    ) external {
        IERC20(debtAsset).transferFrom(msg.sender, address(this), debtToCover);
        uint256 collateralAmount = (debtToCover * 110) / 100; // 10% bonus
        IERC20(collateralAsset).transfer(msg.sender, collateralAmount);
    }
}

contract MockMoonwellProtocol {
    address public collateralToken;
    address public debtToken;
    
    constructor(address _collateralToken, address _debtToken) {
        collateralToken = _collateralToken;
        debtToken = _debtToken;
    }
    
    function liquidateBorrow(
        address borrower,
        uint256 repayAmount,
        address collateralAsset
    ) external returns (uint256) {
        IERC20(debtToken).transferFrom(msg.sender, address(this), repayAmount);
        uint256 collateralAmount = (repayAmount * 110) / 100; // 10% bonus
        IERC20(collateralAsset).transfer(msg.sender, collateralAmount);
        return 0;
    }
}

contract MockAavePool {
    function flashLoan(
        address receiverAddress,
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata interestRateModes,
        address onBehalfOf,
        bytes calldata params,
        uint16 referralCode
    ) external {
        for (uint256 i = 0; i < assets.length; i++) {
            IERC20(assets[i]).transfer(receiverAddress, amounts[i]);
        }
        
        uint256[] memory premiums = new uint256[](amounts.length);
        for (uint256 i = 0; i < amounts.length; i++) {
            premiums[i] = (amounts[i] * 9) / 10000; // 0.09%
        }
        
        IFlashLoanReceiver(receiverAddress).executeOperation(
            assets,
            amounts,
            premiums,
            receiverAddress,
            params
        );
        
        for (uint256 i = 0; i < assets.length; i++) {
            IERC20(assets[i]).transferFrom(
                receiverAddress,
                address(this),
                amounts[i] + premiums[i]
            );
        }
    }
}

contract MockBalancerVault {
    function flashLoan(
        address recipient,
        address[] memory tokens,
        uint256[] memory amounts,
        bytes memory userData
    ) external {
        for (uint256 i = 0; i < tokens.length; i++) {
            IERC20(tokens[i]).transfer(recipient, amounts[i]);
        }
        
        uint256[] memory feeAmounts = new uint256[](amounts.length);
        for (uint256 i = 0; i < amounts.length; i++) {
            feeAmounts[i] = (amounts[i] * 5) / 10000; // 0.05%
        }
        
        IBalancerFlashLoanRecipient(recipient).receiveFlashLoan(
            tokens,
            amounts,
            feeAmounts,
            userData
        );
        
        for (uint256 i = 0; i < tokens.length; i++) {
            require(
                IERC20(tokens[i]).balanceOf(address(this)) >= amounts[i] + feeAmounts[i],
                "Not repaid"
            );
        }
    }
}

contract MockUniswapRouter {
    function exactInputSingle(ISwapRouter.ExactInputSingleParams calldata params)
        external
        returns (uint256 amountOut)
    {
        IERC20(params.tokenIn).transferFrom(msg.sender, address(this), params.amountIn);
        
        // Simulate realistic swap: 1 WETH = 2500 USDC with 0.5% slippage
        if (params.tokenIn < params.tokenOut) {
            // WETH to USDC
            amountOut = (params.amountIn * 2500 * 995) / (1e18 * 1000); // 0.5% slippage
        } else {
            // USDC to WETH
            amountOut = (params.amountIn * 1e18 * 995) / (2500 * 1e6 * 1000);
        }
        
        require(amountOut >= params.amountOutMinimum, "Insufficient output");
        IERC20(params.tokenOut).transfer(params.recipient, amountOut);
    }
}

contract MockAerodromeRouter {
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        IAerodromeRouter.Route[] calldata routes,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts) {
        require(routes.length > 0, "Invalid route");
        
        IERC20(routes[0].from).transferFrom(msg.sender, address(this), amountIn);
        
        uint256 amountOut = (amountIn * 995) / 1000; // 0.5% slippage
        require(amountOut >= amountOutMin, "Insufficient output");
        
        IERC20(routes[routes.length - 1].to).transfer(to, amountOut);
        
        amounts = new uint256[](2);
        amounts[0] = amountIn;
        amounts[1] = amountOut;
    }
}

contract MockBrokenProtocol {
    function liquidationCall(
        address collateralAsset,
        address debtAsset,
        address borrower,
        uint256 debtToCover,
        bool receiveAToken
    ) external {
        // Take debt but don't send collateral
        IERC20(debtAsset).transferFrom(msg.sender, address(this), debtToCover);
        // Don't send any collateral back
    }
}
