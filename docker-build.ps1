Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Smart Finance Agent - Docker Build" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Docker
try {
    docker --version | Out-Null
    Write-Host "[OK] Docker found" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker is not installed" -ForegroundColor Red
    exit 1
}

# Check Docker Compose
try {
    docker compose version | Out-Null
    Write-Host "[OK] Docker Compose found" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Docker Compose is not available" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "Building Images..." -ForegroundColor Yellow
Write-Host ""

# Build backend
Write-Host "[1/2] Building backend image..." -ForegroundColor Yellow
docker compose build backend
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Backend build failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Backend image built" -ForegroundColor Green

# Build frontend
Write-Host "[2/2] Building frontend image..." -ForegroundColor Yellow
docker compose build frontend
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Frontend build failed" -ForegroundColor Red
    exit 1
}
Write-Host "[OK] Frontend image built" -ForegroundColor Green

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Build Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start services: docker compose up -d" -ForegroundColor Cyan
Write-Host "To view logs:      docker compose logs -f" -ForegroundColor Cyan
Write-Host "To stop services:  docker compose down" -ForegroundColor Cyan
Write-Host ""
