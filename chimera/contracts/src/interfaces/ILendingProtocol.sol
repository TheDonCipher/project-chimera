// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title ILendingProtocol
 * @notice Generic interface for lending protocols (Moonwell, Seamless, etc.)
 * @dev Based on Compound V2/V3 style liquidation interface
 */
interface ILendingProtocol {
    /**
     * @notice Liquidate a borrower's position
     * @param borrower The borrower's address
     * @param repayAmount The amount of debt to repay
     * @param cTokenCollateral The collateral cToken address
     * @return The actual amount of collateral seized
     */
    function liquidateBorrow(
        address borrower,
        uint256 repayAmount,
        address cTokenCollateral
    ) external returns (uint256);
}

/**
 * @title IAaveV3LendingPool
 * @notice Interface for Aave V3 style lending pools (Seamless Protocol)
 */
interface IAaveV3LendingPool {
    /**
     * @notice Liquidate a borrower's position
     * @param collateralAsset The collateral asset address
     * @param debtAsset The debt asset address
     * @param user The borrower's address
     * @param debtToCover The amount of debt to cover
     * @param receiveAToken Whether to receive aTokens or underlying
     */
    function liquidationCall(
        address collateralAsset,
        address debtAsset,
        address user,
        uint256 debtToCover,
        bool receiveAToken
    ) external;
}
