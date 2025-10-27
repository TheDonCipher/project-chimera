// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Chimera.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/**
 * @title ChimeraTest
 * @notice Comprehensive test suite for Chimera contract
 * @dev Tests cover unit tests, access control, reentrancy, fork tests, and fuzz tests
 */
contract ChimeraTest is Test {
    Chimera public chimera;
    
    address public owner;
    address public treasury;
    address public nonOwner;
    
    address public aavePool;
    address public balancerVault;
    address public uniswapRouter;
    address public aerodromeRouter;
    
    MockERC20 public collateralToken;
    MockERC20 public debtToken;
    MockLendingProtocol public lendingProtocol;
    MockAavePool public mockAavePool;
    MockBalancerVault public mockBalancerVault;
    MockUniswapRouter public mockUniswapRouter;
    
    event LiquidationExecuted(
        address indexed protocol,
        address indexed borrower,
        uint256 profitAmount,
        uint256 gasUsed
    );
    
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);
    
    function setUp() public {
        owner = address(this);
        treasury = makeAddr("treasury");
        nonOwner = makeAddr("nonOwner");
        
        // Deploy mock contracts
        collateralToken = new MockERC20("Collateral", "COLL", 18);
        debtToken = new MockERC20("Debt", "DEBT", 18);
        lendingProtocol = new MockLendingProtocol(address(collateralToken), address(debtToken));
        mockAavePool = new MockAavePool();
        mockBalancerVault = new MockBalancerVault();
        mockUniswapRouter = new MockUniswapRouter();
        
        aavePool = address(mockAavePool);
        balancerVault = address(mockBalancerVault);
        uniswapRouter = address(mockUniswapRouter);
        aerodromeRouter = makeAddr("aerodromeRouter");
        
        // Deploy Chimera contract
        chimera = new Chimera(
            treasury,
            aavePool,
            balancerVault,
            uniswapRouter,
            aerodromeRouter
        );
    }
    
    /*//////////////////////////////////////////////////////////////
                        CONSTRUCTOR TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Constructor_Success() public {
        assertEq(chimera.treasury(), treasury);
        assertEq(chimera.aavePool(), aavePool);
        assertEq(chimera.balancerVault(), balancerVault);
        assertEq(chimera.uniswapRouter(), uniswapRouter);
        assertEq(chimera.aerodromeRouter(), aerodromeRouter);
        assertEq(chimera.owner(), owner);
    }
    
    function test_Constructor_RevertIf_InvalidTreasury() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        new Chimera(
            address(0),
            aavePool,
            balancerVault,
            uniswapRouter,
            aerodromeRouter
        );
    }
    
    function test_Constructor_RevertIf_InvalidAavePool() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        new Chimera(
            treasury,
            address(0),
            balancerVault,
            uniswapRouter,
            aerodromeRouter
        );
    }
    
    /*//////////////////////////////////////////////////////////////
                        PAUSE/UNPAUSE TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_Pause_Success() public {
        assertFalse(chimera.paused());
        
        chimera.pause();
        
        assertTrue(chimera.paused());
    }
    
    function test_Unpause_Success() public {
        chimera.pause();
        assertTrue(chimera.paused());
        
        chimera.unpause();
        
        assertFalse(chimera.paused());
    }
    
    function test_Pause_RevertIf_NotOwner() public {
        vm.prank(nonOwner);
        vm.expectRevert("Ownable: caller is not the owner");
        chimera.pause();
    }
    
    function test_Unpause_RevertIf_NotOwner() public {
        chimera.pause();
        
        vm.prank(nonOwner);
        vm.expectRevert("Ownable: caller is not the owner");
        chimera.unpause();
    }
    
    function test_ExecuteLiquidation_RevertIf_Paused() public {
        chimera.pause();
        
        vm.expectRevert("Pausable: paused");
        chimera.executeLiquidation(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(collateralToken),
            address(debtToken),
            1000e18,
            50e18,
            true
        );
    }
    
    /*//////////////////////////////////////////////////////////////
                        SET TREASURY TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_SetTreasury_Success() public {
        address newTreasury = makeAddr("newTreasury");
        
        vm.expectEmit(true, true, false, true);
        emit TreasuryUpdated(treasury, newTreasury);
        
        chimera.setTreasury(newTreasury);
        
        assertEq(chimera.treasury(), newTreasury);
    }
    
    function test_SetTreasury_RevertIf_InvalidAddress() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        chimera.setTreasury(address(0));
    }
    
    function test_SetTreasury_RevertIf_NotOwner() public {
        address newTreasury = makeAddr("newTreasury");
        
        vm.prank(nonOwner);
        vm.expectRevert("Ownable: caller is not the owner");
        chimera.setTreasury(newTreasury);
    }
    
    /*//////////////////////////////////////////////////////////////
                        RESCUE TOKENS TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_RescueTokens_Success() public {
        uint256 amount = 100e18;
        MockERC20 token = new MockERC20("Test", "TEST", 18);
        token.mint(address(chimera), amount);
        
        uint256 treasuryBalanceBefore = token.balanceOf(treasury);
        
        chimera.rescueTokens(address(token), amount);
        
        assertEq(token.balanceOf(treasury), treasuryBalanceBefore + amount);
        assertEq(token.balanceOf(address(chimera)), 0);
    }
    
    function test_RescueTokens_RevertIf_InvalidAddress() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        chimera.rescueTokens(address(0), 100e18);
    }
    
    function test_RescueTokens_RevertIf_InvalidAmount() public {
        MockERC20 token = new MockERC20("Test", "TEST", 18);
        
        vm.expectRevert(Chimera.InvalidAmount.selector);
        chimera.rescueTokens(address(token), 0);
    }
    
    function test_RescueTokens_RevertIf_NotOwner() public {
        MockERC20 token = new MockERC20("Test", "TEST", 18);
        
        vm.prank(nonOwner);
        vm.expectRevert("Ownable: caller is not the owner");
        chimera.rescueTokens(address(token), 100e18);
    }
    
    /*//////////////////////////////////////////////////////////////
                        ACCESS CONTROL TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_ExecuteLiquidation_RevertIf_NotOwner() public {
        vm.prank(nonOwner);
        vm.expectRevert("Ownable: caller is not the owner");
        chimera.executeLiquidation(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(collateralToken),
            address(debtToken),
            1000e18,
            50e18,
            true
        );
    }
    
    function test_ExecuteLiquidationWithBalancer_RevertIf_NotOwner() public {
        vm.prank(nonOwner);
        vm.expectRevert("Ownable: caller is not the owner");
        chimera.executeLiquidationWithBalancer(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(collateralToken),
            address(debtToken),
            1000e18,
            50e18,
            true
        );
    }
    
    function test_OwnershipTransfer_TwoStep() public {
        address newOwner = makeAddr("newOwner");
        
        // Step 1: Transfer ownership
        chimera.transferOwnership(newOwner);
        assertEq(chimera.owner(), owner); // Still old owner
        assertEq(chimera.pendingOwner(), newOwner);
        
        // Step 2: Accept ownership
        vm.prank(newOwner);
        chimera.acceptOwnership();
        assertEq(chimera.owner(), newOwner);
        assertEq(chimera.pendingOwner(), address(0));
    }
    
    /*//////////////////////////////////////////////////////////////
                        INPUT VALIDATION TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_ExecuteLiquidation_RevertIf_InvalidLendingProtocol() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        chimera.executeLiquidation(
            address(0),
            makeAddr("borrower"),
            address(collateralToken),
            address(debtToken),
            1000e18,
            50e18,
            true
        );
    }
    
    function test_ExecuteLiquidation_RevertIf_InvalidBorrower() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        chimera.executeLiquidation(
            address(lendingProtocol),
            address(0),
            address(collateralToken),
            address(debtToken),
            1000e18,
            50e18,
            true
        );
    }
    
    function test_ExecuteLiquidation_RevertIf_InvalidCollateralAsset() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        chimera.executeLiquidation(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(0),
            address(debtToken),
            1000e18,
            50e18,
            true
        );
    }
    
    function test_ExecuteLiquidation_RevertIf_InvalidDebtAsset() public {
        vm.expectRevert(Chimera.InvalidAddress.selector);
        chimera.executeLiquidation(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(collateralToken),
            address(0),
            1000e18,
            50e18,
            true
        );
    }
    
    function test_ExecuteLiquidation_RevertIf_ZeroDebtAmount() public {
        vm.expectRevert(Chimera.InvalidAmount.selector);
        chimera.executeLiquidation(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(collateralToken),
            address(debtToken),
            0,
            50e18,
            true
        );
    }
    
    function test_ExecuteLiquidation_RevertIf_ZeroMinProfit() public {
        vm.expectRevert(Chimera.InvalidAmount.selector);
        chimera.executeLiquidation(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(collateralToken),
            address(debtToken),
            1000e18,
            0,
            true
        );
    }
    
    /*//////////////////////////////////////////////////////////////
                        REENTRANCY TESTS
    //////////////////////////////////////////////////////////////*/
    
    function test_ExecuteLiquidation_ReentrancyProtection() public {
        // Deploy malicious contract that attempts reentrancy
        MaliciousReentrancy malicious = new MaliciousReentrancy(address(chimera));
        
        // Transfer ownership to malicious contract
        chimera.transferOwnership(address(malicious));
        vm.prank(address(malicious));
        chimera.acceptOwnership();
        
        // Attempt reentrancy attack
        vm.prank(address(malicious));
        vm.expectRevert("ReentrancyGuard: reentrant call");
        malicious.attack(
            address(lendingProtocol),
            makeAddr("borrower"),
            address(collateralToken),
            address(debtToken)
        );
    }
    
    /*//////////////////////////////////////////////////////////////
                        FUZZ TESTS
    //////////////////////////////////////////////////////////////*/
    
    function testFuzz_SetTreasury(address newTreasury) public {
        vm.assume(newTreasury != address(0));
        
        chimera.setTreasury(newTreasury);
        assertEq(chimera.treasury(), newTreasury);
    }
    
    function testFuzz_RescueTokens(uint256 amount) public {
        vm.assume(amount > 0 && amount < type(uint128).max);
        
        MockERC20 token = new MockERC20("Test", "TEST", 18);
        token.mint(address(chimera), amount);
        
        chimera.rescueTokens(address(token), amount);
        assertEq(token.balanceOf(treasury), amount);
    }
    
    function testFuzz_ExecuteLiquidation_InputValidation(
        address lendingProtocol_,
        address borrower_,
        address collateralAsset_,
        address debtAsset_,
        uint256 debtAmount_,
        uint256 minProfit_
    ) public {
        // Test that invalid inputs are properly rejected
        bool shouldRevert = (
            lendingProtocol_ == address(0) ||
            borrower_ == address(0) ||
            collateralAsset_ == address(0) ||
            debtAsset_ == address(0) ||
            debtAmount_ == 0 ||
            minProfit_ == 0
        );
        
        if (shouldRevert) {
            vm.expectRevert();
            chimera.executeLiquidation(
                lendingProtocol_,
                borrower_,
                collateralAsset_,
                debtAsset_,
                debtAmount_,
                minProfit_,
                true
            );
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

contract MockLendingProtocol {
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
        // Transfer debt tokens from liquidator
        IERC20(debtToken).transferFrom(msg.sender, address(this), repayAmount);
        
        // Transfer collateral tokens to liquidator (with 10% bonus)
        uint256 collateralAmount = (repayAmount * 110) / 100;
        MockERC20(collateralToken).mint(msg.sender, collateralAmount);
        
        return 0;
    }
    
    function liquidationCall(
        address collateralAsset,
        address debtAsset,
        address borrower,
        uint256 debtToCover,
        bool receiveAToken
    ) external {
        // Transfer debt tokens from liquidator
        IERC20(debtAsset).transferFrom(msg.sender, address(this), debtToCover);
        
        // Transfer collateral tokens to liquidator (with 10% bonus)
        uint256 collateralAmount = (debtToCover * 110) / 100;
        MockERC20(collateralAsset).mint(msg.sender, collateralAmount);
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
        // Mint flash loan amount to receiver
        for (uint256 i = 0; i < assets.length; i++) {
            MockERC20(assets[i]).mint(receiverAddress, amounts[i]);
        }
        
        // Calculate premiums (0.09%)
        uint256[] memory premiums = new uint256[](amounts.length);
        for (uint256 i = 0; i < amounts.length; i++) {
            premiums[i] = (amounts[i] * 9) / 10000;
        }
        
        // Call receiver's executeOperation
        IFlashLoanReceiver(receiverAddress).executeOperation(
            assets,
            amounts,
            premiums,
            receiverAddress,
            params
        );
        
        // Pull back loan + premium
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
        // Mint flash loan amount to recipient
        for (uint256 i = 0; i < tokens.length; i++) {
            MockERC20(tokens[i]).mint(recipient, amounts[i]);
        }
        
        // Calculate fees (0.05%)
        uint256[] memory feeAmounts = new uint256[](amounts.length);
        for (uint256 i = 0; i < amounts.length; i++) {
            feeAmounts[i] = (amounts[i] * 5) / 10000;
        }
        
        // Call recipient's receiveFlashLoan
        IBalancerFlashLoanRecipient(recipient).receiveFlashLoan(
            tokens,
            amounts,
            feeAmounts,
            userData
        );
        
        // Verify repayment
        for (uint256 i = 0; i < tokens.length; i++) {
            require(
                IERC20(tokens[i]).balanceOf(address(this)) >= amounts[i] + feeAmounts[i],
                "Flash loan not repaid"
            );
        }
    }
}

contract MockUniswapRouter {
    function exactInputSingle(ISwapRouter.ExactInputSingleParams calldata params)
        external
        returns (uint256 amountOut)
    {
        // Transfer input tokens from sender
        IERC20(params.tokenIn).transferFrom(msg.sender, address(this), params.amountIn);
        
        // Mint output tokens to recipient (simulate 1:1 swap with 1% slippage)
        amountOut = (params.amountIn * 99) / 100;
        require(amountOut >= params.amountOutMinimum, "Insufficient output");
        MockERC20(params.tokenOut).mint(params.recipient, amountOut);
        
        return amountOut;
    }
}

contract MaliciousReentrancy {
    Chimera public chimera;
    bool public attacking;
    
    constructor(address _chimera) {
        chimera = Chimera(_chimera);
    }
    
    function attack(
        address lendingProtocol,
        address borrower,
        address collateralAsset,
        address debtAsset
    ) external {
        attacking = true;
        chimera.executeLiquidation(
            lendingProtocol,
            borrower,
            collateralAsset,
            debtAsset,
            1000e18,
            50e18,
            true
        );
    }
    
    // Attempt reentrancy during execution
    fallback() external {
        if (attacking) {
            chimera.executeLiquidation(
                address(0x1),
                address(0x2),
                address(0x3),
                address(0x4),
                1000e18,
                50e18,
                true
            );
        }
    }
}
