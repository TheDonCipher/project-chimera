// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/security/Pausable.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "./interfaces/IFlashLoanReceiver.sol";
import "./interfaces/IPool.sol";
import "./interfaces/IBalancerVault.sol";
import "./interfaces/ISwapRouter.sol";
import "./interfaces/IAerodromeRouter.sol";
import "./interfaces/ILendingProtocol.sol";

/**
 * @title Chimera
 * @notice MEV liquidation bot contract for Base L2 lending protocols
 * @dev Executes atomic liquidations: flash loan → liquidate → swap → repay → profit
 */
contract Chimera is Ownable2Step, Pausable, ReentrancyGuard, IFlashLoanReceiver, IBalancerFlashLoanRecipient {
    using SafeERC20 for IERC20;

    /// @notice Treasury address where profits are sent
    address public treasury;

    /// @notice Aave V3 Pool address for flash loans
    address public immutable aavePool;

    /// @notice Balancer Vault address for backup flash loans
    address public immutable balancerVault;

    /// @notice Uniswap V3 SwapRouter address
    address public immutable uniswapRouter;

    /// @notice Aerodrome Router address (Base L2 DEX)
    address public immutable aerodromeRouter;

    /// @notice Uniswap V3 pool fee (0.3% = 3000)
    uint24 public constant UNISWAP_POOL_FEE = 3000;

    /// @notice Tracks if we're currently in a flash loan callback
    bool private _inFlashLoan;

    /// @notice Stores liquidation parameters during flash loan execution
    struct LiquidationParams {
        address lendingProtocol;
        address borrower;
        address collateralAsset;
        address debtAsset;
        uint256 debtAmount;
        uint256 minProfit;
        bool useBalancer;
        bool isAaveStyle; // true for Seamless (Aave V3), false for Moonwell (Compound)
    }

    LiquidationParams private _currentLiquidation;

    /// @notice Emitted when a liquidation is successfully executed
    /// @param protocol The lending protocol address
    /// @param borrower The borrower's address
    /// @param profitAmount The profit amount in wei
    /// @param gasUsed The gas used for the transaction
    event LiquidationExecuted(
        address indexed protocol,
        address indexed borrower,
        uint256 profitAmount,
        uint256 gasUsed
    );

    /// @notice Emitted when the treasury address is updated
    /// @param oldTreasury The previous treasury address
    /// @param newTreasury The new treasury address
    event TreasuryUpdated(address indexed oldTreasury, address indexed newTreasury);

    /// @notice Error thrown when an invalid address is provided
    error InvalidAddress();

    /// @notice Error thrown when an invalid amount is provided
    error InvalidAmount();

    /// @notice Error thrown when profit is below minimum threshold
    error InsufficientProfit();

    /// @notice Error thrown when flash loan callback is called by unauthorized address
    error UnauthorizedFlashLoan();

    /// @notice Error thrown when not in flash loan context
    error NotInFlashLoan();

    /**
     * @notice Constructor
     * @param _treasury The treasury address where profits will be sent
     * @param _aavePool The Aave V3 Pool address for flash loans
     * @param _balancerVault The Balancer Vault address for backup flash loans
     * @param _uniswapRouter The Uniswap V3 SwapRouter address
     * @param _aerodromeRouter The Aerodrome Router address
     */
    constructor(
        address _treasury,
        address _aavePool,
        address _balancerVault,
        address _uniswapRouter,
        address _aerodromeRouter
    ) {
        if (_treasury == address(0)) revert InvalidAddress();
        if (_aavePool == address(0)) revert InvalidAddress();
        if (_balancerVault == address(0)) revert InvalidAddress();
        if (_uniswapRouter == address(0)) revert InvalidAddress();
        if (_aerodromeRouter == address(0)) revert InvalidAddress();
        
        treasury = _treasury;
        aavePool = _aavePool;
        balancerVault = _balancerVault;
        uniswapRouter = _uniswapRouter;
        aerodromeRouter = _aerodromeRouter;
    }

    /**
     * @notice Execute a liquidation with flash loan
     * @param lendingProtocol The lending protocol contract address
     * @param borrower The borrower's address to liquidate
     * @param collateralAsset The collateral token address
     * @param debtAsset The debt token address
     * @param debtAmount The amount of debt to repay
     * @param minProfit The minimum profit required (in debt asset)
     * @param isAaveStyle True for Aave V3 style (Seamless), false for Compound style (Moonwell)
     */
    function executeLiquidation(
        address lendingProtocol,
        address borrower,
        address collateralAsset,
        address debtAsset,
        uint256 debtAmount,
        uint256 minProfit,
        bool isAaveStyle
    ) external onlyOwner whenNotPaused nonReentrant {
        // Input validation
        if (lendingProtocol == address(0)) revert InvalidAddress();
        if (borrower == address(0)) revert InvalidAddress();
        if (collateralAsset == address(0)) revert InvalidAddress();
        if (debtAsset == address(0)) revert InvalidAddress();
        if (debtAmount == 0) revert InvalidAmount();
        if (minProfit == 0) revert InvalidAmount();

        // Store liquidation parameters for callback
        _currentLiquidation = LiquidationParams({
            lendingProtocol: lendingProtocol,
            borrower: borrower,
            collateralAsset: collateralAsset,
            debtAsset: debtAsset,
            debtAmount: debtAmount,
            minProfit: minProfit,
            useBalancer: false,
            isAaveStyle: isAaveStyle
        });

        // Request flash loan from Aave V3
        _requestAaveFlashLoan(debtAsset, debtAmount);
    }

    /**
     * @notice Execute a liquidation with Balancer flash loan (backup)
     * @param lendingProtocol The lending protocol contract address
     * @param borrower The borrower's address to liquidate
     * @param collateralAsset The collateral token address
     * @param debtAsset The debt token address
     * @param debtAmount The amount of debt to repay
     * @param minProfit The minimum profit required (in debt asset)
     * @param isAaveStyle True for Aave V3 style (Seamless), false for Compound style (Moonwell)
     */
    function executeLiquidationWithBalancer(
        address lendingProtocol,
        address borrower,
        address collateralAsset,
        address debtAsset,
        uint256 debtAmount,
        uint256 minProfit,
        bool isAaveStyle
    ) external onlyOwner whenNotPaused nonReentrant {
        // Input validation
        if (lendingProtocol == address(0)) revert InvalidAddress();
        if (borrower == address(0)) revert InvalidAddress();
        if (collateralAsset == address(0)) revert InvalidAddress();
        if (debtAsset == address(0)) revert InvalidAddress();
        if (debtAmount == 0) revert InvalidAmount();
        if (minProfit == 0) revert InvalidAmount();

        // Store liquidation parameters for callback
        _currentLiquidation = LiquidationParams({
            lendingProtocol: lendingProtocol,
            borrower: borrower,
            collateralAsset: collateralAsset,
            debtAsset: debtAsset,
            debtAmount: debtAmount,
            minProfit: minProfit,
            useBalancer: true,
            isAaveStyle: isAaveStyle
        });

        // Request flash loan from Balancer
        _requestBalancerFlashLoan(debtAsset, debtAmount);
    }

    /**
     * @notice Request flash loan from Aave V3
     * @param asset The asset to borrow
     * @param amount The amount to borrow
     */
    function _requestAaveFlashLoan(address asset, uint256 amount) private {
        address[] memory assets = new address[](1);
        assets[0] = asset;

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;

        uint256[] memory interestRateModes = new uint256[](1);
        interestRateModes[0] = 0; // 0 = no debt, flash loan must be repaid

        _inFlashLoan = true;
        IPool(aavePool).flashLoan(
            address(this),
            assets,
            amounts,
            interestRateModes,
            address(this),
            "",
            0
        );
        _inFlashLoan = false;
    }

    /**
     * @notice Request flash loan from Balancer
     * @param asset The asset to borrow
     * @param amount The amount to borrow
     */
    function _requestBalancerFlashLoan(address asset, uint256 amount) private {
        address[] memory tokens = new address[](1);
        tokens[0] = asset;

        uint256[] memory amounts = new uint256[](1);
        amounts[0] = amount;

        _inFlashLoan = true;
        IBalancerVault(balancerVault).flashLoan(
            address(this),
            tokens,
            amounts,
            ""
        );
        _inFlashLoan = false;
    }

    /**
     * @notice Aave V3 flash loan callback
     * @param assets The addresses of the flash-borrowed assets
     * @param amounts The amounts of the flash-borrowed assets
     * @param premiums The fee of each flash-borrowed asset
     * @param initiator The address of the flashloan initiator
     * @param params The byte-encoded params passed when initiating the flashloan
     * @return True if the execution succeeds
     */
    function executeOperation(
        address[] calldata assets,
        uint256[] calldata amounts,
        uint256[] calldata premiums,
        address initiator,
        bytes calldata params
    ) external override returns (bool) {
        // Verify caller is Aave Pool
        if (msg.sender != aavePool) revert UnauthorizedFlashLoan();
        if (initiator != address(this)) revert UnauthorizedFlashLoan();
        if (!_inFlashLoan) revert NotInFlashLoan();

        // Execute liquidation logic
        _executeLiquidationLogic(assets[0], amounts[0]);

        // Calculate repayment amount (borrowed + premium)
        uint256 amountOwed = amounts[0] + premiums[0];

        // Approve Aave Pool to pull the repayment
        IERC20(assets[0]).safeApprove(aavePool, amountOwed);

        return true;
    }

    /**
     * @notice Balancer flash loan callback
     * @param tokens The addresses of the tokens flash loaned
     * @param amounts The amounts of tokens flash loaned
     * @param feeAmounts The fee amounts for each token
     * @param userData Additional data passed from the flash loan call
     */
    function receiveFlashLoan(
        address[] memory tokens,
        uint256[] memory amounts,
        uint256[] memory feeAmounts,
        bytes memory userData
    ) external override {
        // Verify caller is Balancer Vault
        if (msg.sender != balancerVault) revert UnauthorizedFlashLoan();
        if (!_inFlashLoan) revert NotInFlashLoan();

        // Execute liquidation logic
        _executeLiquidationLogic(tokens[0], amounts[0]);

        // Calculate repayment amount (borrowed + fee)
        uint256 amountOwed = amounts[0] + feeAmounts[0];

        // Transfer repayment to Balancer Vault
        IERC20(tokens[0]).safeTransfer(balancerVault, amountOwed);
    }

    /**
     * @notice Internal function to execute liquidation logic
     * @param debtAsset The debt asset address
     * @param debtAmount The debt amount borrowed
     */
    function _executeLiquidationLogic(address debtAsset, uint256 debtAmount) private {
        uint256 gasStart = gasleft();
        LiquidationParams memory params = _currentLiquidation;

        // Step 1: Approve lending protocol to spend debt tokens (exact amount only)
        IERC20(debtAsset).safeApprove(params.lendingProtocol, debtAmount);

        // Step 2: Call liquidation function on lending protocol
        if (params.isAaveStyle) {
            // Aave V3 style (Seamless Protocol)
            IAaveV3LendingPool(params.lendingProtocol).liquidationCall(
                params.collateralAsset,
                debtAsset,
                params.borrower,
                debtAmount,
                false // Receive underlying tokens, not aTokens
            );
        } else {
            // Compound style (Moonwell)
            ILendingProtocol(params.lendingProtocol).liquidateBorrow(
                params.borrower,
                debtAmount,
                params.collateralAsset
            );
        }

        // Reset approval to 0 for security
        IERC20(debtAsset).safeApprove(params.lendingProtocol, 0);

        // Step 3: Check received collateral tokens
        uint256 collateralBalance = IERC20(params.collateralAsset).balanceOf(address(this));
        if (collateralBalance == 0) revert InsufficientProfit();

        // Step 4: Swap collateral for debt asset on DEX
        uint256 debtBalanceBefore = IERC20(debtAsset).balanceOf(address(this));
        
        _swapTokens(
            params.collateralAsset,
            debtAsset,
            collateralBalance,
            debtAmount // Minimum output to cover flash loan repayment
        );

        uint256 debtBalanceAfter = IERC20(debtAsset).balanceOf(address(this));

        // Step 5: Verify profit meets minimum threshold
        // Calculate profit: (debt received from swap) - (debt borrowed)
        uint256 profit = debtBalanceAfter - debtBalanceBefore;
        
        if (profit < params.minProfit) revert InsufficientProfit();

        // Step 6: Transfer profit to treasury
        IERC20(debtAsset).safeTransfer(treasury, profit);

        // Step 7: Emit event with execution details
        uint256 gasUsed = gasStart - gasleft();
        emit LiquidationExecuted(
            params.lendingProtocol,
            params.borrower,
            profit,
            gasUsed
        );
    }

    /**
     * @notice Swap tokens using Uniswap V3 with Aerodrome as backup
     * @param tokenIn The input token address
     * @param tokenOut The output token address
     * @param amountIn The input token amount
     * @param amountOutMinimum The minimum output token amount
     * @return amountOut The actual output token amount
     */
    function _swapTokens(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOutMinimum
    ) private returns (uint256 amountOut) {
        // Try Uniswap V3 first
        try this._swapOnUniswap(tokenIn, tokenOut, amountIn, amountOutMinimum) returns (uint256 amount) {
            return amount;
        } catch {
            // Fallback to Aerodrome if Uniswap fails
            return _swapOnAerodrome(tokenIn, tokenOut, amountIn, amountOutMinimum);
        }
    }

    /**
     * @notice Swap tokens on Uniswap V3
     * @param tokenIn The input token address
     * @param tokenOut The output token address
     * @param amountIn The input token amount
     * @param amountOutMinimum The minimum output token amount
     * @return amountOut The actual output token amount
     */
    function _swapOnUniswap(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOutMinimum
    ) external returns (uint256 amountOut) {
        // Only callable by this contract
        require(msg.sender == address(this), "Only self");

        // Approve Uniswap router to spend exact amount (no infinite approvals)
        IERC20(tokenIn).safeApprove(uniswapRouter, amountIn);

        ISwapRouter.ExactInputSingleParams memory params = ISwapRouter.ExactInputSingleParams({
            tokenIn: tokenIn,
            tokenOut: tokenOut,
            fee: UNISWAP_POOL_FEE,
            recipient: address(this),
            deadline: block.timestamp,
            amountIn: amountIn,
            amountOutMinimum: amountOutMinimum,
            sqrtPriceLimitX96: 0
        });

        amountOut = ISwapRouter(uniswapRouter).exactInputSingle(params);

        // Reset approval to 0 for security
        IERC20(tokenIn).safeApprove(uniswapRouter, 0);
    }

    /**
     * @notice Swap tokens on Aerodrome
     * @param tokenIn The input token address
     * @param tokenOut The output token address
     * @param amountIn The input token amount
     * @param amountOutMinimum The minimum output token amount
     * @return amountOut The actual output token amount
     */
    function _swapOnAerodrome(
        address tokenIn,
        address tokenOut,
        uint256 amountIn,
        uint256 amountOutMinimum
    ) private returns (uint256 amountOut) {
        // Approve Aerodrome router to spend exact amount (no infinite approvals)
        IERC20(tokenIn).safeApprove(aerodromeRouter, amountIn);

        // Create route (try stable pool first, then volatile)
        IAerodromeRouter.Route[] memory routes = new IAerodromeRouter.Route[](1);
        routes[0] = IAerodromeRouter.Route({
            from: tokenIn,
            to: tokenOut,
            stable: false // Use volatile pool by default
        });

        uint256[] memory amounts = IAerodromeRouter(aerodromeRouter).swapExactTokensForTokens(
            amountIn,
            amountOutMinimum,
            routes,
            address(this),
            block.timestamp
        );

        amountOut = amounts[amounts.length - 1];

        // Reset approval to 0 for security
        IERC20(tokenIn).safeApprove(aerodromeRouter, 0);
    }

    /**
     * @notice Pause the contract (emergency stop)
     * @dev Only callable by owner
     */
    function pause() external onlyOwner {
        _pause();
    }

    /**
     * @notice Unpause the contract
     * @dev Only callable by owner
     */
    function unpause() external onlyOwner {
        _unpause();
    }

    /**
     * @notice Update the treasury address
     * @param _newTreasury The new treasury address
     * @dev Only callable by owner
     */
    function setTreasury(address _newTreasury) external onlyOwner {
        if (_newTreasury == address(0)) revert InvalidAddress();
        
        address oldTreasury = treasury;
        treasury = _newTreasury;
        
        emit TreasuryUpdated(oldTreasury, _newTreasury);
    }

    /**
     * @notice Rescue tokens accidentally sent to the contract
     * @param token The token address to rescue
     * @param amount The amount to rescue
     * @dev Only callable by owner. Sends tokens to treasury.
     */
    function rescueTokens(address token, uint256 amount) external onlyOwner {
        if (token == address(0)) revert InvalidAddress();
        if (amount == 0) revert InvalidAmount();
        
        IERC20(token).safeTransfer(treasury, amount);
    }
}
