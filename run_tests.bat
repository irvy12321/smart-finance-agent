@echo off
echo ========================================
echo Smart Finance Agent - Test Runner
echo ========================================
echo.

echo [1/4] Installing backend test dependencies...
cd backend
pip install -r requirements.txt -q
if %errorlevel% neq 0 (
    echo Failed to install backend dependencies
    exit /b 1
)
cd ..

echo.
echo [2/4] Running backend tests with coverage...
cd backend
python -m pytest tests/ -v --cov=app --cov-report=html:../coverage/backend/html --cov-report=json:../coverage/backend/coverage.json --cov-report=term-missing
if %errorlevel% neq 0 (
    echo Backend tests failed
    exit /b 1
)
cd ..

echo.
echo [3/4] Running frontend tests with coverage...
cd frontend
call npm run test:coverage
if %errorlevel% neq 0 (
    echo Frontend tests failed
    exit /b 1
)
cd ..

echo.
echo [4/4] Test summary...
echo.
echo ========================================
echo Tests completed successfully!
echo ========================================
echo.
echo Coverage reports:
echo   - Backend:  coverage/backend/html/index.html
echo   - Frontend: frontend/coverage/index.html
echo.
echo To view reports, open the HTML files in your browser.
echo ========================================
