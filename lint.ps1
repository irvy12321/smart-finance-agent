Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Smart Finance Agent - Lint Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Installing backend lint dependencies..." -ForegroundColor Yellow
Set-Location backend
pip install ruff -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install ruff" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "[2/4] Running backend lint..." -ForegroundColor Yellow
Set-Location backend
ruff check .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend lint failed" -ForegroundColor Red
    exit 1
}

ruff format --check .
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend format check failed" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "[3/4] Installing frontend lint dependencies..." -ForegroundColor Yellow
Set-Location frontend
npm ci --silent
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install frontend dependencies" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "[4/4] Running frontend lint..." -ForegroundColor Yellow
Set-Location frontend
npm run lint
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend lint failed" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Lint passed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
