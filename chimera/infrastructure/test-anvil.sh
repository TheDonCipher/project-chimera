#!/bin/bash
# Test script to verify Anvil local fork is working correctly

set -e

echo "========================================="
echo "Testing Anvil Local Fork Setup"
echo "========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is running
echo "1. Checking Docker..."
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}✗ Docker is not running${NC}"
    echo "Please start Docker Desktop and try again"
    exit 1
fi
echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Check if cast is installed
echo "2. Checking Foundry (cast)..."
if ! command -v cast &> /dev/null; then
    echo -e "${RED}✗ cast command not found${NC}"
    echo "Please install Foundry: curl -L https://foundry.paradigm.xyz | bash && foundryup"
    exit 1
fi
echo -e "${GREEN}✓ Foundry is installed${NC}"
echo "   Version: $(cast --version)"
echo ""

# Start Anvil if not running
echo "3. Starting Anvil..."
if docker ps | grep -q chimera-anvil; then
    echo -e "${YELLOW}⚠ Anvil is already running${NC}"
else
    docker-compose --profile testing up -d anvil
    echo -e "${GREEN}✓ Anvil started${NC}"
fi
echo ""

# Wait for Anvil to be ready
echo "4. Waiting for Anvil to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if cast block-number --rpc-url http://localhost:8545 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ Anvil is ready${NC}"
        break
    fi
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo -e "${RED}✗ Anvil failed to start after ${MAX_RETRIES} seconds${NC}"
        echo "Check logs with: docker-compose --profile testing logs anvil"
        exit 1
    fi
    sleep 1
done
echo ""

# Test RPC connection
echo "5. Testing RPC connection..."
BLOCK_NUMBER=$(cast block-number --rpc-url http://localhost:8545)
echo -e "${GREEN}✓ RPC connection successful${NC}"
echo "   Current block: $BLOCK_NUMBER"
echo ""

# Test chain ID
echo "6. Verifying chain ID..."
CHAIN_ID=$(cast chain-id --rpc-url http://localhost:8545)
if [ "$CHAIN_ID" -eq 8453 ]; then
    echo -e "${GREEN}✓ Chain ID is correct (8453 = Base)${NC}"
else
    echo -e "${RED}✗ Chain ID is incorrect: $CHAIN_ID (expected 8453)${NC}"
    exit 1
fi
echo ""

# Test getting block
echo "7. Testing block retrieval..."
BLOCK_INFO=$(cast block latest --rpc-url http://localhost:8545 --json)
BLOCK_HASH=$(echo $BLOCK_INFO | jq -r .hash)
BLOCK_TIMESTAMP=$(echo $BLOCK_INFO | jq -r .timestamp)
echo -e "${GREEN}✓ Block retrieval successful${NC}"
echo "   Block hash: $BLOCK_HASH"
echo "   Timestamp: $BLOCK_TIMESTAMP"
echo ""

# Test account balance
echo "8. Testing account queries..."
# Use a known Base address (Base bridge)
TEST_ADDRESS="0x4200000000000000000000000000000000000010"
BALANCE=$(cast balance $TEST_ADDRESS --rpc-url http://localhost:8545)
echo -e "${GREEN}✓ Account query successful${NC}"
echo "   Address: $TEST_ADDRESS"
echo "   Balance: $BALANCE wei"
echo ""

# Test state manipulation (Anvil-specific)
echo "9. Testing Anvil-specific features..."
# Set balance for test account
TEST_ACCOUNT="0x1234567890123456789012345678901234567890"
cast rpc anvil_setBalance $TEST_ACCOUNT 0x1000000000000000000 --rpc-url http://localhost:8545 > /dev/null
NEW_BALANCE=$(cast balance $TEST_ACCOUNT --rpc-url http://localhost:8545)
if [ "$NEW_BALANCE" == "1000000000000000000" ]; then
    echo -e "${GREEN}✓ State manipulation successful${NC}"
    echo "   Set balance for $TEST_ACCOUNT"
else
    echo -e "${RED}✗ State manipulation failed${NC}"
    exit 1
fi
echo ""

# Test mining
echo "10. Testing block mining..."
BEFORE_BLOCK=$(cast block-number --rpc-url http://localhost:8545)
cast rpc evm_mine --rpc-url http://localhost:8545 > /dev/null
AFTER_BLOCK=$(cast block-number --rpc-url http://localhost:8545)
if [ $AFTER_BLOCK -gt $BEFORE_BLOCK ]; then
    echo -e "${GREEN}✓ Block mining successful${NC}"
    echo "   Before: $BEFORE_BLOCK, After: $AFTER_BLOCK"
else
    echo -e "${RED}✗ Block mining failed${NC}"
    exit 1
fi
echo ""

# Summary
echo "========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo "========================================="
echo ""
echo "Anvil is ready for use:"
echo "  RPC URL: http://localhost:8545"
echo "  Chain ID: 8453 (Base)"
echo "  Current block: $(cast block-number --rpc-url http://localhost:8545)"
echo ""
echo "Next steps:"
echo "  - Update .env to use Anvil: ALCHEMY_HTTPS=http://localhost:8545"
echo "  - Run tests: make fork-test"
echo "  - View logs: make anvil-logs"
echo "  - Reset state: make anvil-reset"
echo ""
echo "For more information, see:"
echo "  chimera/infrastructure/ANVIL_SETUP.md"
echo "  chimera/infrastructure/ANVIL_QUICK_REFERENCE.md"
echo ""
