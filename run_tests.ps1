Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Smart Finance Agent - Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/4] Installing backend test dependencies..." -ForegroundColor Yellow
Set-Location backend
pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "Failed to install backend dependencies" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "[2/4] Running backend tests with coverage..." -ForegroundColor Yellow
Set-Location backend
python -m pytest tests/ -v --cov=app --cov-report=html:../coverage/backend/html --cov-report=json:../coverage/backend/coverage.json --cov-report=term-missing
if ($LASTEXITCODE -ne 0) {
    Write-Host "Backend tests failed" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "[3/4] Running frontend tests with coverage..." -ForegroundColor Yellow
Set-Location frontend
npm run test:coverage
if ($LASTEXITCODE -ne 0) {
    Write-Host "Frontend tests failed" -ForegroundColor Red
    exit 1
}
Set-Location ..

Write-Host ""
Write-Host "[4/4] Test summary..." -ForegroundColor Yellow
Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Tests completed successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Coverage reports:" -ForegroundColor Cyan
Write-Host "  - Backend:  coverage/backend/html/index.html" -ForegroundColor White
Write-Host "  - Frontend: frontend/coverage/index.html" -ForegroundColor White
Write-Host ""
Write-Host "To view reports, open the HTML files in your browser." -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
