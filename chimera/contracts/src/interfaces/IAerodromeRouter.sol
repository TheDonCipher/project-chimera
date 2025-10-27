// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IAerodromeRouter
 * @notice Interface for Aerodrome Router (Base L2 DEX)
 */
interface IAerodromeRouter {
    struct Route {
        address from;
        address to;
        bool stable;
    }

    /**
     * @notice Swap tokens with exact input amount
     * @param amountIn The amount of input tokens
     * @param amountOutMin The minimum amount of output tokens
     * @param routes The swap routes
     * @param to The recipient address
     * @param deadline The deadline timestamp
     * @return amounts The amounts of tokens at each step
     */
    function swapExactTokensForTokens(
        uint256 amountIn,
        uint256 amountOutMin,
        Route[] calldata routes,
        address to,
        uint256 deadline
    ) external returns (uint256[] memory amounts);
}
