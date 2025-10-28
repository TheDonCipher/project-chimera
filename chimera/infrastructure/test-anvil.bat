@echo off
REM Test script to verify Anvil local fork is working correctly

setlocal enabledelayedexpansion

echo =========================================
echo Testing Anvil Local Fork Setup
echo =========================================
echo.

REM Check if Docker is running
echo 1. Checking Docker...
docker info >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Docker is not running
    echo Please start Docker Desktop and try again
    exit /b 1
)
echo [OK] Docker is running
echo.

REM Check if cast is installed
echo 2. Checking Foundry ^(cast^)...
where cast >nul 2>&1
if errorlevel 1 (
    echo [ERROR] cast command not found
    echo Please install Foundry: https://book.getfoundry.sh/getting-started/installation
    exit /b 1
)
echo [OK] Foundry is installed
for /f "tokens=*" %%i in ('cast --version') do echo    Version: %%i
echo.

REM Start Anvil if not running
echo 3. Starting Anvil...
docker ps | findstr chimera-anvil >nul 2>&1
if not errorlevel 1 (
    echo [WARNING] Anvil is already running
) else (
    docker-compose --profile testing up -d anvil
    echo [OK] Anvil started
)
echo.

REM Wait for Anvil to be ready
echo 4. Waiting for Anvil to be ready...
set MAX_RETRIES=30
set RETRY_COUNT=0
:wait_loop
cast block-number --rpc-url http://localhost:8545 >nul 2>&1
if not errorlevel 1 (
    echo [OK] Anvil is ready
    goto anvil_ready
)
set /a RETRY_COUNT+=1
if !RETRY_COUNT! geq %MAX_RETRIES% (
    echo [ERROR] Anvil failed to start after %MAX_RETRIES% seconds
    echo Check logs with: docker-compose --profile testing logs anvil
    exit /b 1
)
timeout /t 1 /nobreak >nul
goto wait_loop
:anvil_ready
echo.

REM Test RPC connection
echo 5. Testing RPC connection...
for /f "tokens=*" %%i in ('cast block-number --rpc-url http://localhost:8545') do set BLOCK_NUMBER=%%i
echo [OK] RPC connection successful
echo    Current block: %BLOCK_NUMBER%
echo.

REM Test chain ID
echo 6. Verifying chain ID...
for /f "tokens=*" %%i in ('cast chain-id --rpc-url http://localhost:8545') do set CHAIN_ID=%%i
if "%CHAIN_ID%"=="8453" (
    echo [OK] Chain ID is correct ^(8453 = Base^)
) else (
    echo [ERROR] Chain ID is incorrect: %CHAIN_ID% ^(expected 8453^)
    exit /b 1
)
echo.

REM Test getting block
echo 7. Testing block retrieval...
cast block latest --rpc-url http://localhost:8545 >nul 2>&1
if not errorlevel 1 (
    echo [OK] Block retrieval successful
) else (
    echo [ERROR] Block retrieval failed
    exit /b 1
)
echo.

REM Test account balance
echo 8. Testing account queries...
set TEST_ADDRESS=0x4200000000000000000000000000000000000010
for /f "tokens=*" %%i in ('cast balance %TEST_ADDRESS% --rpc-url http://localhost:8545') do set BALANCE=%%i
echo [OK] Account query successful
echo    Address: %TEST_ADDRESS%
echo    Balance: %BALANCE% wei
echo.

REM Test state manipulation
echo 9. Testing Anvil-specific features...
set TEST_ACCOUNT=0x1234567890123456789012345678901234567890
cast rpc anvil_setBalance %TEST_ACCOUNT% 0x1000000000000000000 --rpc-url http://localhost:8545 >nul 2>&1
for /f "tokens=*" %%i in ('cast balance %TEST_ACCOUNT% --rpc-url http://localhost:8545') do set NEW_BALANCE=%%i
if "%NEW_BALANCE%"=="1000000000000000000" (
    echo [OK] State manipulation successful
    echo    Set balance for %TEST_ACCOUNT%
) else (
    echo [ERROR] State manipulation failed
    exit /b 1
)
echo.

REM Test mining
echo 10. Testing block mining...
for /f "tokens=*" %%i in ('cast block-number --rpc-url http://localhost:8545') do set BEFORE_BLOCK=%%i
cast rpc evm_mine --rpc-url http://localhost:8545 >nul 2>&1
for /f "tokens=*" %%i in ('cast block-number --rpc-url http://localhost:8545') do set AFTER_BLOCK=%%i
if %AFTER_BLOCK% gtr %BEFORE_BLOCK% (
    echo [OK] Block mining successful
    echo    Before: %BEFORE_BLOCK%, After: %AFTER_BLOCK%
) else (
    echo [ERROR] Block mining failed
    exit /b 1
)
echo.

REM Summary
echo =========================================
echo [SUCCESS] All tests passed!
echo =========================================
echo.
for /f "tokens=*" %%i in ('cast block-number --rpc-url http://localhost:8545') do set CURRENT_BLOCK=%%i
echo Anvil is ready for use:
echo   RPC URL: http://localhost:8545
echo   Chain ID: 8453 ^(Base^)
echo   Current block: %CURRENT_BLOCK%
echo.
echo Next steps:
echo   - Update .env to use Anvil: ALCHEMY_HTTPS=http://localhost:8545
echo   - Run tests: make fork-test
echo   - View logs: make anvil-logs
echo   - Reset state: make anvil-reset
echo.
echo For more information, see:
echo   chimera/infrastructure/ANVIL_SETUP.md
echo   chimera/infrastructure/ANVIL_QUICK_REFERENCE.md
echo.

endlocal
