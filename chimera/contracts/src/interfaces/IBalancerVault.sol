// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/**
 * @title IBalancerVault
 * @notice Interface for Balancer V2 Vault flash loans
 */
interface IBalancerVault {
    /**
     * @notice Performs a flash loan
     * @param recipient The address receiving the flash loan
     * @param tokens The addresses of the tokens to flash loan
     * @param amounts The amounts of tokens to flash loan
     * @param userData Additional data to pass to the recipient
     */
    function flashLoan(
        address recipient,
        address[] memory tokens,
        uint256[] memory amounts,
        bytes memory userData
    ) external;
}

/**
 * @title IBalancerFlashLoanRecipient
 * @notice Interface for Balancer flash loan recipient
 */
interface IBalancerFlashLoanRecipient {
    /**
     * @notice Callback for Balancer flash loans
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
    ) external;
}
