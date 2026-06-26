Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Smart Finance Agent - Code Formatter" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[1/3] Installing dependencies..." -ForegroundColor Yellow
Set-Location backend
pip install ruff -q
Set-Location ..
Set-Location frontend
npm ci --silent
Set-Location ..

Write-Host ""
Write-Host "[2/3] Formatting backend code..." -ForegroundColor Yellow
Set-Location backend
ruff check --fix .
ruff format .
Set-Location ..

Write-Host ""
Write-Host "[3/3] Formatting frontend code..." -ForegroundColor Yellow
Set-Location frontend
npm run lint -- --fix
Set-Location ..

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "Code formatted successfully!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
