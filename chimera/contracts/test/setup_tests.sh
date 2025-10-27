#!/bin/bash

# Chimera Contract Test Setup Script
# This script installs Foundry and dependencies needed to run tests

set -e

echo "=========================================="
echo "Chimera Contract Test Setup"
echo "=========================================="
echo ""

# Check if Foundry is installed
if ! command -v forge &> /dev/null; then
    echo "📦 Foundry not found. Installing..."
    curl -L https://foundry.paradigm.xyz | bash
    
    # Source the foundry environment
    export PATH="$HOME/.foundry/bin:$PATH"
    
    # Run foundryup
    foundryup
    
    echo "✅ Foundry installed successfully"
else
    echo "✅ Foundry already installed"
    forge --version
fi

echo ""
echo "📦 Installing OpenZeppelin contracts..."

# Navigate to contracts directory
cd "$(dirname "$0")/.."

# Install OpenZeppelin contracts if not already installed
if [ ! -d "lib/openzeppelin-contracts" ]; then
    forge install OpenZeppelin/openzeppelin-contracts --no-commit
    echo "✅ OpenZeppelin contracts installed"
else
    echo "✅ OpenZeppelin contracts already installed"
fi

echo ""
echo "🔨 Building contracts..."
forge build

echo ""
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "You can now run tests with:"
echo "  forge test                          # Run all tests"
echo "  forge test -vv                      # Run with verbose output"
echo "  forge test --match-path test/Chimera.t.sol  # Run specific test file"
echo "  forge coverage                      # Generate coverage report"
echo "  forge test --gas-report             # Generate gas report"
echo ""
echo "For fork tests, set BASE_RPC_URL in .env:"
echo "  BASE_RPC_URL=https://mainnet.base.org"
echo ""
