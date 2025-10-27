# Contributing to Project Chimera

Thank you for contributing to Project Chimera! This document provides guidelines for development, testing, and code review.

## Getting Started

1. Read `README.md` for project overview
2. Read `SETUP.md` for environment setup
3. Read `AGENTS.md` for development principles
4. Review the spec files in `.kiro/specs/mev-liquidation-bot/`

## Development Workflow

### 1. Pick a Task

Open `.kiro/specs/mev-liquidation-bot/tasks.md` and select an uncompleted task.

Tasks are organized sequentially - complete them in order for best results.

### 2. Create a Branch

```bash
git checkout -b task-X.Y-description
```

Example: `git checkout -b task-1.1-project-structure`

### 3. Implement the Task

Follow the task description and requirements. See `AGENTS.md` for implementation patterns.

### 4. Write Tests

- Unit tests for all business logic
- Integration tests for component interactions
- Aim for >80% coverage (>95% for critical paths)

### 5. Run Tests

```bash
# Python tests
cd bot
pytest tests/ -v --cov=src

# Smart contract tests
cd contracts
forge test -vvv
forge coverage
```

### 6. Update Documentation

- Add docstrings to all functions
- Update README.md if user-facing changes
- Update design.md if architecture changes

### 7. Commit Changes

```bash
git add .
git commit -m "Implement task X.Y: Description

- Bullet point of what was done
- Reference to requirements satisfied
- Any important notes"
```

### 8. Push and Create PR

```bash
git push origin task-X.Y-description
```

Then create a Pull Request with:

- Clear title: "Task X.Y: Description"
- Description of changes
- Requirements satisfied
- Test results
- Screenshots (if applicable)

## Code Style

### Python

Follow PEP 8 with these specifics:

- **Line length**: 100 characters (not 79)
- **Imports**: Group by standard library, third-party, local
- **Type hints**: Use for all function signatures
- **Docstrings**: Google style

```python
from typing import Optional, List
from decimal import Decimal

async def calculate_health_factor(
    position: Position,
    collateral_price: Decimal,
    debt_price: Decimal
) -> Decimal:
    """
    Calculate health factor for a lending position.

    Args:
        position: The lending position to evaluate
        collateral_price: Current collateral asset price in USD
        debt_price: Current debt asset price in USD

    Returns:
        Health factor as Decimal. Values <1.0 indicate liquidatable position.

    Raises:
        ValueError: If prices are zero or negative

    Example:
        >>> position = Position(collateral_amount=1000e18, debt_amount=900e18, ...)
        >>> health_factor = await calculate_health_factor(position, 1.0, 2000.0)
        >>> print(health_factor)
        0.000444
    """
    if collateral_price <= 0 or debt_price <= 0:
        raise ValueError("Prices must be positive")

    collateral_value = (position.collateral_amount / 10**18) * collateral_price
    debt_value = (position.debt_amount / 10**18) * debt_price

    health_factor = (collateral_value * position.liquidation_threshold) / debt_value

    return health_factor
```

### Solidity

Follow Solidity style guide with these specifics:

- **Solidity version**: ^0.8.24
- **Naming**: PascalCase for contracts, camelCase for functions
- **Comments**: NatSpec for all public functions
- **Security**: Always use OpenZeppelin libraries

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

import "@openzeppelin/contracts/access/Ownable2Step.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";

/**
 * @title Chimera
 * @notice Executes atomic liquidations on Base L2 lending protocols
 * @dev Stateless contract - does not store token balances between transactions
 */
contract Chimera is Ownable2Step, ReentrancyGuard {
    /// @notice Address where profits are sent
    address public treasury;

    /// @notice Emitted when a liquidation is successfully executed
    /// @param protocol The lending protocol address
    /// @param borrower The borrower whose position was liquidated
    /// @param profitAmount The profit amount in wei
    /// @param gasUsed The gas used for the transaction
    event LiquidationExecuted(
        address indexed protocol,
        address indexed borrower,
        uint256 profitAmount,
        uint256 gasUsed
    );

    /**
     * @notice Executes an atomic liquidation
     * @param lendingProtocol The lending protocol to liquidate on
     * @param borrower The borrower to liquidate
     * @param collateralAsset The collateral asset address
     * @param debtAsset The debt asset address
     * @param debtAmount The amount of debt to repay
     * @param minProfit The minimum profit required (reverts if less)
     * @return profit The actual profit amount in wei
     */
    function executeLiquidation(
        address lendingProtocol,
        address borrower,
        address collateralAsset,
        address debtAsset,
        uint256 debtAmount,
        uint256 minProfit
    ) external onlyOwner nonReentrant returns (uint256 profit) {
        // Implementation...
    }
}
```

## Testing Guidelines

### Unit Tests

- Test one function at a time
- Mock external dependencies
- Test happy path and error cases
- Use descriptive test names

```python
def test_calculate_health_factor_with_valid_inputs_returns_correct_ratio():
    """Test that health factor calculation returns correct ratio for valid inputs"""
    # Arrange, Act, Assert pattern
```

### Integration Tests

- Test component interactions
- Use real dependencies where possible
- Test against local fork for blockchain interactions
- Mark with `@pytest.mark.integration`

### Smart Contract Tests

- Test all functions (success and failure)
- Test access control
- Test reentrancy protection
- Use fork tests for real protocol interactions
- Fuzz test numerical calculations

```solidity
function testExecuteLiquidation_RevertsWhen_CallerNotOwner() public {
    vm.prank(address(0x123));  // Impersonate non-owner

    vm.expectRevert("Ownable: caller is not the owner");
    chimera.executeLiquidation(
        address(protocol),
        address(borrower),
        address(collateral),
        address(debt),
        1000e18,
        50e18
    );
}
```

## Code Review Checklist

Before submitting PR, verify:

- [ ] All tests pass
- [ ] Code coverage meets requirements (>80% overall, >95% critical)
- [ ] All functions have docstrings
- [ ] Complex logic has inline comments
- [ ] No hardcoded values (use configuration)
- [ ] Error handling is comprehensive
- [ ] Logging provides sufficient context
- [ ] No sensitive data in code or commits
- [ ] Requirements are satisfied (reference REQ-XX-NNN)
- [ ] Design is followed (consistent with design.md)

## Security Guidelines

### Never Commit

- Private keys
- API keys
- Passwords
- AWS credentials
- Any sensitive data

### Always

- Use environment variables for secrets
- Validate all inputs
- Handle errors gracefully
- Log security-relevant events
- Use parameterized queries (prevent SQL injection)
- Use SafeERC20 for token operations
- Test access control thoroughly

### Code Review Focus

- Input validation
- Error handling
- Access control
- Reentrancy protection
- Integer overflow/underflow
- External call safety

## Performance Guidelines

### Latency Requirements

- Detection: <500ms
- Simulation: <1000ms
- Build: <200ms
- Total: <700ms (excluding simulation)

### Optimization Tips

- Use async/await for I/O operations
- Cache frequently accessed data
- Batch RPC calls where possible
- Use connection pooling
- Profile before optimizing

### Memory Guidelines

- Keep memory usage <4GB average
- Monitor for memory leaks
- Limit cache sizes
- Clean up resources properly

## Documentation Standards

### Module Docstrings

```python
"""
Module Name

WHAT: Brief description of what this module does
HOW: High-level description of how it works
WHY: Why this module is necessary

Detailed description with examples if needed.

Requirements: REQ-XX-NNN, REQ-YY-MMM
"""
```

### Function Docstrings

```python
def function_name(param1: Type1, param2: Type2) -> ReturnType:
    """
    Brief description of what the function does.

    Longer description if needed, explaining the algorithm,
    edge cases, or important considerations.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ExceptionType: When this exception is raised

    Requirements: REQ-XX-NNN
    """
```

### Inline Comments

```python
# Calculate divergence in basis points (0.01%)
# REQ-SE-002: Must trigger HALT if >10 BPS
divergence_bps = abs(cached - canonical) / canonical * 10000

if divergence_bps > 10:
    # Critical: State is wrong, stop all executions
    self.safety.transition_to_halted("state_divergence")
```

## Git Commit Messages

### Format

```
Type: Brief description (50 chars or less)

Longer description if needed (wrap at 72 chars).
Explain WHAT changed and WHY, not HOW (code shows how).

- Bullet points for multiple changes
- Reference requirements: REQ-XX-NNN
- Reference issues: Fixes #123

Task: X.Y
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `test`: Adding or updating tests
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `chore`: Maintenance tasks

### Examples

```
feat: Implement state reconciliation

Implement block-level state reconciliation that compares cached
position data against canonical chain state every block.

- Add reconcile_state() method to StateEngine
- Calculate divergence in basis points
- Trigger HALT if divergence >10 BPS
- Log all divergences to database

Requirements: REQ-SE-002
Task: 3.3
```

## Questions?

If you have questions:

1. Check existing documentation first
2. Search for similar issues in code comments
3. Ask specific questions with context
4. Provide error messages and logs

## Thank You!

Your contributions help make Project Chimera robust, secure, and profitable. Execute with discipline, scale with patience, optimize continuously.
