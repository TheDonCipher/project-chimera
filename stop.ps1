# Chimera MEV Bot - Stop Script (PowerShell)
# Gracefully shuts down all Docker services

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Chimera MEV Bot - Stopping Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not running." -ForegroundColor Red
    exit 1
}

Write-Host "[INFO] Stopping Docker Compose services..." -ForegroundColor Green
Write-Host ""

# Stop services gracefully
docker-compose down

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Failed to stop services. Check the error messages above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Services Stopped Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Data is preserved in Docker volumes." -ForegroundColor White
Write-Host ""
Write-Host "To start services again:" -ForegroundColor Cyan
Write-Host "  .\start.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To remove all data and reset:" -ForegroundColor Cyan
Write-Host "  .\reset.ps1" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
