# Chimera Contract Test Setup Script (PowerShell)
# This script helps set up the test environment on Windows

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Chimera Contract Test Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Foundry is installed
$forgeExists = Get-Command forge -ErrorAction SilentlyContinue

if (-not $forgeExists) {
    Write-Host "📦 Foundry not found." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please install Foundry manually:" -ForegroundColor Yellow
    Write-Host "1. Visit: https://book.getfoundry.sh/getting-started/installation" -ForegroundColor White
    Write-Host "2. Follow Windows installation instructions" -ForegroundColor White
    Write-Host "3. Run this script again after installation" -ForegroundColor White
    Write-Host ""
    Write-Host "Quick install (requires Git Bash or WSL):" -ForegroundColor Yellow
    Write-Host "  curl -L https://foundry.paradigm.xyz | bash" -ForegroundColor White
    Write-Host "  foundryup" -ForegroundColor White
    Write-Host ""
    exit 1
} else {
    Write-Host "✅ Foundry already installed" -ForegroundColor Green
    forge --version
}

Write-Host ""
Write-Host "📦 Installing OpenZeppelin contracts..." -ForegroundColor Cyan

# Navigate to contracts directory
$scriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location (Join-Path $scriptPath "..")

# Install OpenZeppelin contracts if not already installed
if (-not (Test-Path "lib/openzeppelin-contracts")) {
    forge install OpenZeppelin/openzeppelin-contracts --no-commit
    Write-Host "✅ OpenZeppelin contracts installed" -ForegroundColor Green
} else {
    Write-Host "✅ OpenZeppelin contracts already installed" -ForegroundColor Green
}

Write-Host ""
Write-Host "🔨 Building contracts..." -ForegroundColor Cyan
forge build

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host "Setup Complete!" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "You can now run tests with:" -ForegroundColor Cyan
    Write-Host "  forge test                                    # Run all tests" -ForegroundColor White
    Write-Host "  forge test -vv                                # Run with verbose output" -ForegroundColor White
    Write-Host "  forge test --match-path test/Chimera.t.sol    # Run specific test file" -ForegroundColor White
    Write-Host "  forge coverage                                # Generate coverage report" -ForegroundColor White
    Write-Host "  forge test --gas-report                       # Generate gas report" -ForegroundColor White
    Write-Host ""
    Write-Host "For fork tests, create a .env file with:" -ForegroundColor Cyan
    Write-Host "  BASE_RPC_URL=https://mainnet.base.org" -ForegroundColor White
    Write-Host ""
} else {
    Write-Host ""
    Write-Host "❌ Build failed. Please check the error messages above." -ForegroundColor Red
    Write-Host ""
    exit 1
}
