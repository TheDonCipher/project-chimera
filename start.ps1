# Chimera MEV Bot - Start Script (PowerShell)
# Launches all Docker services for local development

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Chimera MEV Bot - Starting Services" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if Docker is running
try {
    docker info | Out-Null
} catch {
    Write-Host "[ERROR] Docker is not running. Please start Docker Desktop and try again." -ForegroundColor Red
    exit 1
}

# Check if .env file exists
if (-not (Test-Path .env)) {
    Write-Host "[WARNING] .env file not found. Creating from .env.example..." -ForegroundColor Yellow
    Copy-Item .env.example .env
    Write-Host "[INFO] Please edit .env file with your actual configuration before running the bot." -ForegroundColor Yellow
    Write-Host ""
}

# Create logs and data directories if they don't exist
if (-not (Test-Path logs)) {
    New-Item -ItemType Directory -Path logs | Out-Null
}
if (-not (Test-Path data)) {
    New-Item -ItemType Directory -Path data | Out-Null
}

Write-Host "[INFO] Starting Docker Compose services..." -ForegroundColor Green
Write-Host ""

# Start services
docker-compose up -d

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[ERROR] Failed to start services. Check the error messages above." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Services Started Successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "PostgreSQL:      localhost:5432" -ForegroundColor White
Write-Host "Redis:           localhost:6379" -ForegroundColor White
Write-Host "Bot:             Running in container" -ForegroundColor White
Write-Host ""
Write-Host "Management Tools (optional):" -ForegroundColor Yellow
Write-Host "  pgAdmin:       http://localhost:5050" -ForegroundColor White
Write-Host "  Redis Commander: http://localhost:8081" -ForegroundColor White
Write-Host ""
Write-Host "To start management tools:" -ForegroundColor Cyan
Write-Host "  docker-compose --profile tools up -d" -ForegroundColor White
Write-Host ""
Write-Host "To view logs:" -ForegroundColor Cyan
Write-Host "  .\logs.ps1" -ForegroundColor White
Write-Host ""
Write-Host "To stop services:" -ForegroundColor Cyan
Write-Host "  .\stop.ps1" -ForegroundColor White
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
